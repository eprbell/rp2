# Copyright 2021 eprbell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cProfile
import os
import sys
from argparse import SUPPRESS, ArgumentParser, Namespace, RawTextHelpFormatter
from datetime import date
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from types import ModuleType
from typing import Dict, List, Optional, Set

from prezzemolo.avl_tree import AVLTree

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.abstract_country import AbstractCountry
from rp2.abstract_report_generator import AbstractReportGenerator
from rp2.accounting_engine import AccountingEngine
from rp2.computed_data import ComputedData
from rp2.configuration import (
    MAX_DATE,
    MIN_DATE,
    REPORT_GENERATOR_PACKAGE,
    Configuration,
)
from rp2.input_data import InputData
from rp2.localization import set_generation_language
from rp2.logger import LOG_FILE, LOGGER
from rp2.ods_parser import open_ods, parse_ods
from rp2.rp2_error import RP2RuntimeError, RP2ValueError
from rp2.tax_engine import compute_tax, compute_tax_per_wallet

_VERSION: str = "1.7.2"

_ACCOUNTING_METHOD_PACKAGE = "rp2.plugin.accounting_method"


def rp2_main(country: AbstractCountry) -> None:
    if "RP2_ENABLE_PROFILER" in os.environ:
        cProfile.runctx("_rp2_main_internal(country)", globals(), locals())
    else:
        _rp2_main_internal(country)


def _rp2_main_internal(country: AbstractCountry) -> None:  # pylint: disable=too-many-branches
    args: Namespace
    assets: List[str]
    parser: ArgumentParser

    AbstractCountry.type_check("country", country)

    parser = _setup_argument_parser(country)
    args = parser.parse_args()

    set_generation_language(args.generation_language)

    _setup_paths(parser=parser, configuration_file=args.configuration_file, input_file=args.input_file, output_dir=args.output_dir)

    # On certain platforms the mpdecimal system library is missing (see details at: https://github.com/eprbell/rp2/issues/25).
    try:
        import _decimal as _  # pylint: disable=import-outside-toplevel
    except ImportError:
        LOGGER.error("The `mpdecimal` library is a required system dependency for RP2, but Python was not able to locate it.")
        sys.exit(1)

    try:
        LOGGER.info("Country: %s", country.country_iso_code)
        LOGGER.info("Generation Language: %s", args.generation_language)

        configuration: Configuration = Configuration(
            configuration_path=args.configuration_file,
            country=country,
            from_date=args.from_date,
            to_date=args.to_date,
            allow_negative_balances=args.allow_negative_balances,
        )
        LOGGER.debug("Configuration object: %s", configuration)

        years_2_accounting_method_names: Dict[int, str] = configuration.years_2_accounting_method_names
        if args.method and configuration.years_2_accounting_method_names:
            LOGGER.error(
                "Accounting method cannot be defined both via -m command line option and 'accounting_methods' section in configuration file: "
                "use only one of them."
            )
            sys.exit(1)
        elif not args.method and configuration.years_2_accounting_method_names:
            years_2_accounting_method_names = configuration.years_2_accounting_method_names
        elif args.method and not configuration.years_2_accounting_method_names:
            years_2_accounting_method_names = {MIN_DATE.year: args.method}
        else:  # neither is defined
            years_2_accounting_method_names = {MIN_DATE.year: country.get_default_accounting_method()}

        old_year: int = MIN_DATE.year
        years_2_accounting_methods: AVLTree[int, AbstractAccountingMethod] = AVLTree()
        for year, accounting_method_name in years_2_accounting_method_names.items():
            accounting_method: AbstractAccountingMethod = _load_accounting_method(accounting_method_name)
            if len(years_2_accounting_method_names) == 1:
                LOGGER.info("Accounting method: %s", accounting_method_name)
            else:
                if year - old_year > 1:
                    LOGGER.info("Accounting method for %s->%s: %s", old_year, year, accounting_method_name)
                else:
                    LOGGER.info("Accounting method for %s: %s", year, accounting_method_name)
            years_2_accounting_methods.insert_node(year, accounting_method)
            old_year = year

        accounting_engine: AccountingEngine = AccountingEngine(years_2_methods=years_2_accounting_methods)

        allocation_method_name_2_method = _load_allocation_methods(configuration, country)

        LOGGER.info("Configuration file: %s", args.configuration_file)

        if args.plugin:
            LOGGER.error("Command line option '-l' or '--plugin' has been deprecated: use the 'generators' section in the configuration file instead.")
            sys.exit(1)

        if args.asset:
            assets = [args.asset]
        else:
            assets = list(configuration.assets)
        assets.sort()

        asset_to_computed_data: Dict[str, ComputedData] = {}
        asset: str

        LOGGER.info("Input file: %s", args.input_file)
        input_file_handle: object = open_ods(configuration=configuration, input_file_path=args.input_file)
        # The application mode of every asset is resolved (and the configuration checked against it) before any computation starts.
        asset_2_input_data: Dict[str, InputData] = {}
        asset_2_per_wallet_start_year: Dict[str, Optional[int]] = {}
        for asset in assets:
            input_data: InputData = parse_ods(configuration=configuration, asset=asset, input_file_handle=input_file_handle)
            LOGGER.debug("InputData object: %s", input_data)
            asset_2_input_data[asset] = input_data
            asset_2_per_wallet_start_year[asset] = _get_per_wallet_start_year(configuration, country, input_data)

        for asset in assets:
            LOGGER.info("Processing %s", asset)
            input_data = asset_2_input_data[asset]
            per_wallet_start_year = asset_2_per_wallet_start_year[asset]
            computed_data: ComputedData
            per_wallet_configuration = configuration.per_wallet_configuration
            if per_wallet_start_year is not None:
                if per_wallet_configuration is None:
                    raise RP2RuntimeError(f"Internal error: per-wallet application of {asset} without per-wallet configuration")
                allocation_method_name = per_wallet_configuration.get_unused_basis_allocation_method(asset)
                computed_data = compute_tax_per_wallet(
                    configuration=configuration,
                    accounting_engine=accounting_engine,
                    input_data=input_data,
                    per_wallet_configuration=per_wallet_configuration,
                    allocation_method=allocation_method_name_2_method[allocation_method_name] if allocation_method_name else None,
                    per_wallet_start_year=per_wallet_start_year,
                )
            else:
                computed_data = compute_tax(configuration=configuration, accounting_engine=accounting_engine, input_data=input_data)
            LOGGER.debug("ComputedData object: %s", computed_data)

            asset_to_computed_data[asset] = computed_data

        # Run report generators (both country-specific and non-country-specific)
        _find_and_run_report_generators(
            configuration=configuration,
            package_paths=[REPORT_GENERATOR_PACKAGE, f"{REPORT_GENERATOR_PACKAGE}.{country.country_iso_code}"],
            args=args,
            country=country,
            years_2_accounting_method_names=years_2_accounting_method_names,
            asset_to_computed_data=asset_to_computed_data,
            from_date=configuration.from_date,
            to_date=configuration.to_date,
        )
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("Fatal exception occurred:")
        sys.exit(1)

    LOGGER.info("Log file: %s", LOG_FILE)
    LOGGER.info("Generated output directory: %s", args.output_dir)
    LOGGER.info("Done")


# Loads the unused basis allocation methods of the per-wallet settings in the country section (by name, e.g. "fifo").
def _load_allocation_methods(configuration: Configuration, country: AbstractCountry) -> Dict[str, AbstractAccountingMethod]:
    result: Dict[str, AbstractAccountingMethod] = {}
    if configuration.per_wallet_configuration is None:
        return result
    for method_name in sorted(configuration.per_wallet_configuration.unused_basis_allocation_method_names):
        if method_name not in country.get_accounting_methods():
            LOGGER.error("Invalid/unsupported unused basis allocation method: %s", method_name)
            sys.exit(1)
        result[method_name] = _load_accounting_method(method_name)
    return result


# First year of per-wallet application of an asset, or None if all its years use universal application. The application mode of each year
# with transactions comes from the country's policy and the user's choice (application_mode in the country section, if any): a choice
# that a year doesn't allow is an error. Per-wallet application needs the per-wallet settings of the country section (at least the
# timezone): if they are missing it's an error, never a silent fallback to universal application.
def _get_per_wallet_start_year(configuration: Configuration, country: AbstractCountry, input_data: InputData) -> Optional[int]:
    policy = country.get_application_policy()
    try:
        year_2_mode = policy.get_year_2_mode(_get_transaction_years(input_data), configuration.application_mode)
        result = policy.get_per_wallet_start_year(year_2_mode)
    except RP2ValueError as exc:
        raise RP2ValueError(f"{input_data.asset}: {exc}") from exc
    if result is None:
        return None
    if configuration.per_wallet_configuration is None:
        raise RP2ValueError(
            f"{input_data.asset} has transactions in {result} or later, when {country.country_iso_code.upper()} requires per-wallet application: "
            f"add a 'country.{country.country_iso_code}' section with at least the 'timezone' field to the configuration file "
            "(see docs/input_files.md)"
        )
    LOGGER.info(
        "%s: universal application before %d, per-wallet application from %d (timezone %s)",
        input_data.asset,
        result,
        result,
        configuration.per_wallet_configuration.timezone_name,
    )
    return result


# Loads an accounting method plugin by name (e.g. "fifo"), exiting with an error if it doesn't exist.
def _load_accounting_method(accounting_method_name: str) -> AbstractAccountingMethod:
    try:
        accounting_method_module: ModuleType = import_module(f"{_ACCOUNTING_METHOD_PACKAGE}.{accounting_method_name}", package=_ACCOUNTING_METHOD_PACKAGE)
    except ModuleNotFoundError:
        LOGGER.error("Invalid/unsupported accounting method: %s", accounting_method_name)
        sys.exit(1)
    if not hasattr(accounting_method_module, "AccountingMethod"):
        LOGGER.error("Accounting method plugin %s doesn't have an AccountingMethod class", accounting_method_name)
        sys.exit(1)
    result: AbstractAccountingMethod = accounting_method_module.AccountingMethod()
    return result


# Tax years in which the input has transactions (the year of each timestamp, in its own timezone).
def _get_transaction_years(input_data: InputData) -> Set[int]:
    return {
        transaction.timestamp.year
        for transaction_set in (
            input_data.unfiltered_in_transaction_set,
            input_data.unfiltered_out_transaction_set,
            input_data.unfiltered_intra_transaction_set,
        )
        for transaction in transaction_set
    }


def _find_and_run_report_generators(
    configuration: Configuration,
    package_paths: List[str],
    args: Namespace,
    country: AbstractCountry,
    years_2_accounting_method_names: Dict[int, str],
    asset_to_computed_data: Dict[str, ComputedData],
    from_date: date,
    to_date: date,
) -> None:
    generators = configuration.generators.copy()
    for package_path in package_paths:
        # Load report generator plugins and call their generate() method
        try:
            package: ModuleType = import_module(package_path)
        except ModuleNotFoundError:
            # Path not found
            continue
        plugin_name: str
        is_package: bool
        for *_, plugin_name, is_package in iter_modules(package.__path__, package.__name__ + "."):
            if is_package:
                continue
            if plugin_name not in generators:
                continue
            generators.remove(plugin_name)
            output_module: ModuleType = import_module(plugin_name, package=REPORT_GENERATOR_PACKAGE)
            if hasattr(output_module, "Generator"):
                generator: AbstractReportGenerator = output_module.Generator()
                LOGGER.debug("Generator object: '%s'", generator)
                LOGGER.info("Generating output for plugin '%s'", plugin_name)
                if not hasattr(generator, "generate"):
                    LOGGER.error("Plugin '%s' has no 'generate' method. Exiting...", plugin_name)
                    sys.exit(1)
                generator.generate(
                    country=country,
                    years_2_accounting_method_names=years_2_accounting_method_names,
                    asset_to_computed_data=asset_to_computed_data,
                    output_dir_path=args.output_dir,
                    output_file_prefix=args.prefix,
                    from_date=from_date,
                    to_date=to_date,
                    generation_language=args.generation_language,
                )

    if generators:
        LOGGER.error("Report generator plugins %s not found. Exiting...", ", ".join(generators))
        sys.exit(1)


def _validate_accounting_methods(country: AbstractCountry) -> List[str]:
    # Load accounting method plugins
    package: ModuleType = import_module(_ACCOUNTING_METHOD_PACKAGE)
    plugin_name: str
    is_package: bool
    result: List[str] = []
    accounting_methods: Set[str] = country.get_accounting_methods()

    if not country.get_default_accounting_method():
        LOGGER.error("No default accounting method defined in the country plugin. Exiting...")
        sys.exit(1)

    if not country.get_accounting_methods():
        LOGGER.error("No accounting methods defined in the country plugin. Exiting...")
        sys.exit(1)

    for *_, plugin_name, is_package in iter_modules(package.__path__, package.__name__ + "."):
        if is_package:
            continue
        normalized_plugin_name = plugin_name.rsplit(".", 1)[1]
        if normalized_plugin_name in accounting_methods:
            result.append(normalized_plugin_name)

    if not result:
        LOGGER.error("No accounting method plugins found. Exiting...")
        sys.exit(1)

    return sorted(result)


def _setup_argument_parser(country: AbstractCountry) -> ArgumentParser:
    accounting_methods = _validate_accounting_methods(country)

    parser: ArgumentParser = ArgumentParser(
        description=(
            "Generate capital gain/loss report and balances for crypto holdings. Links:\n"
            "- documentation: https://github.com/eprbell/rp2/blob/main/README.md\n"
            "- FAQ: https://github.com/eprbell/rp2/blob/main/docs/user_faq.md\n"
            "- support RP2 by leaving a star on Github: https://github.com/eprbell/rp2"
        ),
        formatter_class=RawTextHelpFormatter,
    )

    parser.add_argument(
        "-a",
        "--asset",
        action="store",
        help="Generate report only for the given ASSET",
        metavar="ASSET",
        type=str,
    )
    parser.add_argument(
        "-f",
        "--from_date",
        action="store",
        default=MIN_DATE,
        help="Generate report from the given date (in ISO 8601 format: e.g. YYYY-MM-DD)",
        metavar="DATE",
        type=date.fromisoformat,
    )
    parser.add_argument(
        "-g",
        "--generation-language",
        action="store",
        default=country.get_default_generation_language(),
        help="Language to use during generation (in ISO 639-1 format)",
        metavar="GENERATION_LANGUAGE",
        type=str,
    )
    parser.add_argument(
        "-l",
        "--plugin",
        action="store",
        help=SUPPRESS,
        metavar="PLUGIN",
        type=str,
    )
    parser.add_argument(
        "-m",
        "--method",
        default="",
        choices=accounting_methods,
        help=f"accounting method (default: '%(default)s'). Supported values: {', '.join(accounting_methods)}",
        metavar="METHOD",
        type=str,
    )
    parser.add_argument(
        "-n",
        "--allow_negative_balances",
        action="store_true",
        help="allow exchange balances to be negative (default: '%(default)s').",
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        action="store",
        default="output/",
        help="Write output to OUTPUT_DIR  (default: '%(default)s')",
        metavar="OUTPUT_DIR",
        type=str,
    )
    parser.add_argument(
        "-p",
        "--prefix",
        action="store",
        default="",
        help="Prepend output file names with PREFIX",
        metavar="PREFIX",
        type=str,
    )
    parser.add_argument(
        "-t",
        "--to_date",
        action="store",
        default=MAX_DATE,
        help="Generate report up to the given date (in ISO 8601 format: e.g. YYYY-MM-DD)",
        metavar="DATE",
        type=date.fromisoformat,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"RP2 {_VERSION} (https://github.com/eprbell/rp2)",
        help="Print RP2 version",
    )
    parser.add_argument(
        "configuration_file",
        action="store",
        help="Configuration file",
        metavar="CONFIGURATION",
        type=str,
    )
    parser.add_argument(
        "input_file",
        action="store",
        help="ODS file containing input transactions",
        metavar="INPUT",
        type=str,
    )

    return parser


def _setup_paths(parser: ArgumentParser, configuration_file: str, input_file: str, output_dir: str) -> None:
    if not Path(configuration_file).exists():
        print(f"Configuration file '{configuration_file}' not found")
        parser.print_help()
        sys.exit(1)

    if not input_file.endswith(".ods"):
        print(f"Input file '{input_file}' does not end with '.ods'")
        parser.print_help()
        sys.exit(1)

    if not Path(input_file).exists():
        print(f"Input file '{input_file}' not found")
        parser.print_help()
        sys.exit(1)

    output_dir_path: Path = Path(output_dir)
    if not output_dir_path.exists():
        output_dir_path.mkdir(parents=True)
    if not output_dir_path.is_dir():
        print(f"output_dir '{output_dir}' exists but it's not a directory")
        parser.print_help()
        sys.exit(1)

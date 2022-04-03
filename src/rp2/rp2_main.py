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
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter
from datetime import date
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from types import ModuleType
from typing import Dict, List

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.abstract_country import AbstractCountry
from rp2.abstract_report_generator import AbstractReportGenerator
from rp2.computed_data import ComputedData
from rp2.configuration import MAX_DATE, MIN_DATE, Configuration
from rp2.input_data import InputData
from rp2.logger import LOG_FILE, LOGGER
from rp2.ods_parser import open_ods, parse_ods
from rp2.tax_engine import compute_tax

_VERSION: str = "0.9.27"

_ACCOUNTING_METHOD_PACKAGE = "rp2.plugin.accounting_method"
_REPORT_GENERATOR_PACKAGE = "rp2.plugin.report"


def rp2_main(country: AbstractCountry) -> None:
    if "RP2_ENABLE_PROFILER" in os.environ:
        cProfile.runctx("_rp2_main_internal(country)", globals(), locals())
    else:
        _rp2_main_internal(country)


def _rp2_main_internal(country: AbstractCountry) -> None:
    args: Namespace
    assets: List[str]
    parser: ArgumentParser

    AbstractCountry.type_check("country", country)

    accounting_methods: List[str] = _find_accounting_methods()

    parser = _setup_argument_parser(accounting_methods)
    args = parser.parse_args()

    _setup_paths(parser=parser, configuration_file=args.configuration_file, input_file=args.input_file, output_dir=args.output_dir)

    try:
        LOGGER.info("Country: %s", country.country_iso_code)

        accounting_method_module: ModuleType = import_module(f"{_ACCOUNTING_METHOD_PACKAGE}.{args.method}", package=_ACCOUNTING_METHOD_PACKAGE)
        if not hasattr(accounting_method_module, "AccountingMethod"):
            LOGGER.error("Accounting method plugin %s doesn't have an AccountingMethod class")
            sys.exit(1)
        accounting_method: AbstractAccountingMethod = accounting_method_module.AccountingMethod()
        LOGGER.info("Accounting Method: %s", args.method)

        configuration: Configuration = Configuration(
            configuration_path=args.configuration_file, country=country, from_date=args.from_date, to_date=args.to_date
        )
        LOGGER.info("Configuration file: %s", args.configuration_file)
        LOGGER.debug("Configuration object: %s", configuration)

        if args.asset:
            assets = [args.asset]
        else:
            assets = list(configuration.assets)
        assets.sort()

        asset_to_computed_data: Dict[str, ComputedData] = {}
        asset: str

        LOGGER.info("Input file: %s", args.input_file)
        input_file_handle: object = open_ods(configuration=configuration, input_file_path=args.input_file)
        for asset in assets:
            LOGGER.info("Processing %s", asset)

            input_data: InputData = parse_ods(configuration=configuration, asset=asset, input_file_handle=input_file_handle)
            LOGGER.debug("InputData object: %s", input_data)

            computed_data: ComputedData = compute_tax(configuration=configuration, accounting_method=accounting_method, input_data=input_data)
            LOGGER.debug("ComputedData object: %s", computed_data)

            asset_to_computed_data[asset] = computed_data

        # Run non-country-specific report generators
        _find_and_run_report_generators(
            package_path=_REPORT_GENERATOR_PACKAGE,
            args=args,
            country=country,
            accounting_method=accounting_method,
            asset_to_computed_data=asset_to_computed_data,
            from_date=configuration.from_date,
            to_date=configuration.to_date,
        )
        # Run country-specific report generators
        _find_and_run_report_generators(
            package_path=f"{_REPORT_GENERATOR_PACKAGE}.{country.country_iso_code}",
            args=args,
            country=country,
            accounting_method=accounting_method,
            asset_to_computed_data=asset_to_computed_data,
            from_date=configuration.from_date,
            to_date=configuration.to_date,
        )
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("Fatal exception occurred:")

    LOGGER.info("Log file: %s", LOG_FILE)
    LOGGER.info("Generated output directory: %s", args.output_dir)
    LOGGER.info("Done")


def _find_and_run_report_generators(
    package_path: str,
    args: Namespace,
    country: AbstractCountry,
    accounting_method: AbstractAccountingMethod,
    asset_to_computed_data: Dict[str, ComputedData],
    from_date: date,
    to_date: date,
) -> None:
    # Load report generator plugins and call their generate() method
    package: ModuleType = import_module(package_path)
    plugin_name: str
    is_package: bool
    package_found: bool = False
    for *_, plugin_name, is_package in iter_modules(package.__path__, package.__name__ + "."):
        if is_package:
            continue
        if args.plugin and plugin_name != f"{_REPORT_GENERATOR_PACKAGE}.{args.plugin}":
            continue
        output_module: ModuleType = import_module(plugin_name, package=_REPORT_GENERATOR_PACKAGE)
        if hasattr(output_module, "Generator"):
            generator: AbstractReportGenerator = output_module.Generator()
            LOGGER.debug("Generator object: '%s'", generator)
            LOGGER.info("Generating output for plugin '%s'", plugin_name)
            if not hasattr(generator, "generate"):
                LOGGER.error("Plugin '%s' has no 'generate' method. Exiting...", plugin_name)
                sys.exit(1)
            generator.generate(
                country=country,
                accounting_method=repr(accounting_method),
                asset_to_computed_data=asset_to_computed_data,
                output_dir_path=args.output_dir,
                output_file_prefix=args.prefix,
                from_date=from_date,
                to_date=to_date,
            )
        package_found = True

    if not package_found:
        if args.plugin:
            LOGGER.error("Report Generator plugin '%s' not found. Exiting...", args.plugin)
        else:
            LOGGER.error("No report generator plugin found. Exiting...")
        sys.exit(1)


def _find_accounting_methods() -> List[str]:
    # Load accounting method plugins
    package: ModuleType = import_module(_ACCOUNTING_METHOD_PACKAGE)
    plugin_name: str
    is_package: bool
    result: List[str] = []

    for *_, plugin_name, is_package in iter_modules(package.__path__, package.__name__ + "."):
        if is_package:
            continue
        result.append(plugin_name.rsplit(".", 1)[1])

    if not result:
        LOGGER.error("No accounting method plugins found. Exiting...")

    return result


def _setup_argument_parser(accounting_methods: List[str]) -> ArgumentParser:
    parser: ArgumentParser = ArgumentParser(
        description=(
            "Generate capital gain/loss report and balances for crypto holdings. Links:\n"
            "- documentation: https://github.com/eprbell/rp2/blob/main/README.md\n"
            "- FAQ: https://github.com/eprbell/rp2/blob/main/docs/user_faq.md\n"
            "- leave a star on Github: https://github.com/eprbell/rp2"
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
        "-l",
        "--plugin",
        action="store",
        help="Generate report only using the given PLUGIN",
        metavar="PLUGIN",
        type=str,
    )
    parser.add_argument(
        "-m",
        "--method",
        default="fifo",
        choices=accounting_methods,
        help=f"accounting method (default: '%(default)s'). Supported values: {', '.join(accounting_methods)}",
        metavar="METHOD",
        type=str,
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
        version=f"RP2 {_VERSION} (https://pypi.org/project/rp2/)",
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

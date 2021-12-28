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

import sys
from argparse import ArgumentParser, Namespace
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from types import ModuleType
from typing import Dict, List

from rp2.abstract_country import AbstractCountry
from rp2.abstract_report_generator import AbstractReportGenerator
from rp2.computed_data import ComputedData
from rp2.configuration import VERSION, Configuration
from rp2.input_data import InputData
from rp2.logger import LOG_FILE, LOGGER
from rp2.ods_parser import open_ods, parse_ods
from rp2.tax_engine import compute_tax

_OUTPUT_PACKAGE = "rp2.plugin.report"


def rp2_main(country: AbstractCountry) -> None:

    args: Namespace
    assets: List[str]
    parser: ArgumentParser

    AbstractCountry.type_check("country", country)

    parser = _setup_argument_parser()
    args = parser.parse_args()

    _setup_paths(parser=parser, configuration_file=args.configuration_file, input_file=args.input_file, output_dir=args.output_dir)

    try:
        configuration: Configuration = Configuration(
            country=country, configuration_path=args.configuration_file, from_year=args.from_year, to_year=args.to_year
        )
        LOGGER.debug("Configuration object: %s", configuration)

        if args.asset:
            assets = [args.asset]
        else:
            assets = list(configuration.assets)
        assets.sort()

        asset_to_computed_data: Dict[str, ComputedData] = {}
        asset: str

        input_file_handle: object = open_ods(configuration=configuration, input_file_path=args.input_file)
        for asset in assets:
            LOGGER.info("Processing %s", asset)

            input_data: InputData = parse_ods(configuration=configuration, asset=asset, input_file_handle=input_file_handle)
            LOGGER.debug("InputData object: %s", input_data)

            computed_data: ComputedData = compute_tax(configuration=configuration, input_data=input_data)
            LOGGER.debug("ComputedData object: %s", computed_data)

            asset_to_computed_data[asset] = computed_data

        # Run plugins in the top reports directory
        _find_and_run_plugins(
            package_path=_OUTPUT_PACKAGE,
            args=args,
            country=country,
            asset_to_computed_data=asset_to_computed_data,
        )
        # Run plugins in the country-specific reports directory
        _find_and_run_plugins(
            package_path=f"{_OUTPUT_PACKAGE}.{country.country_iso_code}",
            args=args,
            country=country,
            asset_to_computed_data=asset_to_computed_data,
        )
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("Fatal exception occurred:")

    LOGGER.info("Log file: %s", LOG_FILE)
    LOGGER.info("Generated output directory: %s", args.output_dir)
    LOGGER.info("Done")


def _find_and_run_plugins(package_path: str, args: Namespace, country: AbstractCountry, asset_to_computed_data: Dict[str, ComputedData]) -> None:
    # Load output plugins and call their generate() method
    package: ModuleType = import_module(package_path)
    plugin_name: str
    is_package: bool
    package_found: bool = False
    for *_, plugin_name, is_package in iter_modules(package.__path__, package.__name__ + "."):
        if is_package:
            continue
        if args.plugin and plugin_name != f"{_OUTPUT_PACKAGE}.{args.plugin}":
            continue
        output_module: ModuleType = import_module(plugin_name, package=_OUTPUT_PACKAGE)
        if hasattr(output_module, "Generator"):
            generator: AbstractReportGenerator = output_module.Generator()
            LOGGER.debug("Generator object: '%s'", generator)
            LOGGER.info("Generating output for plugin '%s'", plugin_name)
            if not hasattr(generator, "generate"):
                LOGGER.error("Plugin '%s' has no 'generate' method. Exiting...", plugin_name)
                sys.exit(1)
            generator.generate(country=country, asset_to_computed_data=asset_to_computed_data, output_dir_path=args.output_dir, output_file_prefix=args.prefix)
        package_found = True

    if not package_found:
        if args.plugin:
            LOGGER.error("Plugin '%s' not found. Exiting...", args.plugin)
        else:
            LOGGER.error("No plugin found. Exiting...")
        sys.exit(1)


def _setup_argument_parser() -> ArgumentParser:
    parser: ArgumentParser = ArgumentParser(
        description=(
            "Generate yearly capital gain/loss report and account balances for crypto holdings. "
            "If this software is useful to you, consider leaving a star on its Github page: "
            "https://github.com/eprbell/rp2"
        )
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
        "--from_year",
        action="store",
        default=None,
        help="Generate report from the given YEAR",
        metavar="YEAR",
        type=int,
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
        "-o",
        "--output_dir",
        action="store",
        default="output/",
        help="Write output to OUTPUT_DIR",
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
        "--to_year",
        action="store",
        default=None,
        help="Generate report up to the given YEAR",
        metavar="YEAR",
        type=int,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"RP2 {VERSION} (https://pypi.org/project/rp2/)",
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

# Copyright 2022 eprbell
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

import json
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter
from configparser import ConfigParser
from pathlib import Path
from typing import Any

from jsonschema import validate

from rp2.configuration import Keyword
from rp2.configuration_schema import CONFIGURATION_SCHEMA
from rp2.logger import LOGGER

_VERSION: str = "0.1.0"


def rp2_configuration_translator() -> None:
    args: Namespace
    parser: ArgumentParser

    parser = _setup_argument_parser()
    args = parser.parse_args()

    json_file_name: str = args.json_file
    ini_file_name: str = args.output_file if args.output_file else f"{str(Path(json_file_name).parent/Path(json_file_name).stem)}.ini"

    if not Path(json_file_name).exists():
        print(f"Configuration file '{json_file_name}' not found")
        parser.print_help()
        sys.exit(1)

    if Path(ini_file_name).exists() and not args.force_overwrite:
        print(f"Output file '{ini_file_name}' exists")
        parser.print_help()
        sys.exit(1)

    try:
        json_configuration: Any
        with open(json_file_name, encoding="utf-8") as json_file:
            # This json_configuration is validated by jsonschema, so we can disable static type checking for it:
            # it adds complexity but not much value over jsonschema checks
            json_configuration = json.load(json_file)
            validate(instance=json_configuration, schema=CONFIGURATION_SCHEMA)

        ini_object = ConfigParser()

        ini_object[Keyword.GENERAL.value] = {
            Keyword.ASSETS.value: ", ".join(json_configuration[Keyword.ASSETS.value]),
            Keyword.EXCHANGES.value: ", ".join(json_configuration[Keyword.EXCHANGES.value]),
            Keyword.HOLDERS.value: ", ".join(json_configuration[Keyword.HOLDERS.value]),
        }
        if Keyword.GENERATORS.value in json_configuration:
            ini_object[Keyword.GENERAL.value][Keyword.GENERATORS.value] = json_configuration[Keyword.GENERATORS.value]
        if Keyword.ACCOUNTING_METHODS.value in json_configuration:
            ini_object[Keyword.ACCOUNTING_METHODS.value] = json_configuration[Keyword.ACCOUNTING_METHODS.value]
        ini_object[Keyword.IN_HEADER.value] = json_configuration[Keyword.IN_HEADER.value]
        ini_object[Keyword.OUT_HEADER.value] = json_configuration[Keyword.OUT_HEADER.value]
        ini_object[Keyword.INTRA_HEADER.value] = json_configuration[Keyword.INTRA_HEADER.value]

        with open(ini_file_name, "w", encoding="utf-8") as ini_file:
            ini_object.write(ini_file)

    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("Fatal exception occurred:")
        sys.exit(1)

    LOGGER.info("Input JSON configuration file: %s", json_file_name)
    LOGGER.info("Output INI configuration file: %s", ini_file_name)
    LOGGER.info("Done")


def _setup_argument_parser() -> ArgumentParser:

    parser: ArgumentParser = ArgumentParser(
        description=("Convert a JSON-format RP2 configuration file to INI format"),
        formatter_class=RawTextHelpFormatter,
    )

    parser.add_argument(
        "-f",
        "--force-overwrite",
        action="store_true",
        help="Write the output file even if it already exists",
    )
    parser.add_argument(
        "-o",
        "--output_file",
        action="store",
        default="",
        help="Write INI format configuration to OUTPUT_FILE",
        metavar="OUTPUT_FILE",
        type=str,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"RP2 configuration translator {_VERSION} (https://github.com/eprbell/rp2)",
        help="Print version",
    )
    parser.add_argument(
        "json_file",
        action="store",
        help="JSON configuration file",
        metavar="JSON_FILE",
        type=str,
    )

    return parser

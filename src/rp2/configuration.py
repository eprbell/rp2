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

import json
from configparser import ConfigParser, SectionProxy
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Set

from dateutil.parser import parse
from jsonschema import validate

from rp2.abstract_country import AbstractCountry
from rp2.configuration_schema import CONFIGURATION_SCHEMA
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError

MIN_DATE: date = date(1970, 1, 1)
MAX_DATE: date = date(9999, 12, 31)

REPORT_GENERATOR_PACKAGE = "rp2.plugin.report"


class Keyword(Enum):
    ACCOUNTING_METHODS: str = "accounting_methods"
    ASSET: str = "asset"
    ASSETS: str = "assets"
    CRYPTO_FEE: str = "crypto_fee"
    CRYPTO_IN: str = "crypto_in"
    CRYPTO_OUT_NO_FEE: str = "crypto_out_no_fee"
    CRYPTO_OUT_WITH_FEE: str = "crypto_out_with_fee"
    CRYPTO_RECEIVED: str = "crypto_received"
    CRYPTO_SENT: str = "crypto_sent"
    EXCHANGE: str = "exchange"
    EXCHANGES: str = "exchanges"
    FIAT_FEE: str = "fiat_fee"
    FIAT_IN_NO_FEE: str = "fiat_in_no_fee"
    FIAT_IN_WITH_FEE: str = "fiat_in_with_fee"
    FIAT_OUT_NO_FEE: str = "fiat_out_no_fee"
    FROM_EXCHANGE: str = "from_exchange"
    FROM_HOLDER: str = "from_holder"
    GENERAL: str = "general"
    GENERATORS: str = "generators"
    HOLDER: str = "holder"
    HOLDERS: str = "holders"
    IN_HEADER: str = "in_header"
    INTRA_HEADER: str = "intra_header"
    NOTES: str = "notes"
    OUT_HEADER: str = "out_header"
    SPOT_PRICE: str = "spot_price"
    TIMESTAMP: str = "timestamp"
    TO_EXCHANGE: str = "to_exchange"
    TO_HOLDER: str = "to_holder"
    TRANSACTION_TYPE: str = "transaction_type"
    UNIQUE_ID: str = "unique_id"


_HEADER_COLUMNS: Dict[str, Set[str]] = {
    Keyword.IN_HEADER.value: {
        Keyword.TIMESTAMP.value,
        Keyword.ASSET.value,
        Keyword.EXCHANGE.value,
        Keyword.HOLDER.value,
        Keyword.TRANSACTION_TYPE.value,
        Keyword.SPOT_PRICE.value,
        Keyword.CRYPTO_IN.value,
        Keyword.CRYPTO_FEE.value,
        Keyword.FIAT_IN_NO_FEE.value,
        Keyword.FIAT_IN_WITH_FEE.value,
        Keyword.FIAT_FEE.value,
        Keyword.UNIQUE_ID.value,
        Keyword.NOTES.value,
    },
    Keyword.OUT_HEADER.value: {
        Keyword.TIMESTAMP.value,
        Keyword.ASSET.value,
        Keyword.EXCHANGE.value,
        Keyword.HOLDER.value,
        Keyword.TRANSACTION_TYPE.value,
        Keyword.SPOT_PRICE.value,
        Keyword.CRYPTO_OUT_NO_FEE.value,
        Keyword.CRYPTO_FEE.value,
        Keyword.CRYPTO_OUT_WITH_FEE.value,
        Keyword.FIAT_OUT_NO_FEE.value,
        Keyword.FIAT_FEE.value,
        Keyword.UNIQUE_ID.value,
        Keyword.NOTES.value,
    },
    Keyword.INTRA_HEADER.value: {
        Keyword.TIMESTAMP.value,
        Keyword.ASSET.value,
        Keyword.FROM_EXCHANGE.value,
        Keyword.FROM_HOLDER.value,
        Keyword.TO_EXCHANGE.value,
        Keyword.TO_HOLDER.value,
        Keyword.SPOT_PRICE.value,
        Keyword.CRYPTO_SENT.value,
        Keyword.CRYPTO_RECEIVED.value,
        Keyword.UNIQUE_ID.value,
        Keyword.NOTES.value,
    },
}


class Configuration:  # pylint: disable=too-many-public-methods
    @classmethod
    def type_check(cls, name: str, instance: "Configuration") -> "Configuration":
        cls.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __init__(  # pylint: disable=too-many-branches
        self,
        configuration_path: str,
        country: AbstractCountry,
        from_date: date = MIN_DATE,
        to_date: date = MAX_DATE,
    ) -> None:
        self.__configuration_path: str = self.type_check_string("configuration_path", configuration_path)
        self.__country = AbstractCountry.type_check("country", country)
        if not isinstance(from_date, date):
            raise RP2TypeError("Parameter 'from_date' is not of type date")
        self.__from_date: date = from_date
        if not isinstance(to_date, date):
            raise RP2TypeError("Parameter 'to_date' is not of type date")
        self.__to_date: date = to_date

        if self.__from_date > self.__to_date:
            raise RP2ValueError("Parameter from_date cannot be greater than to_date")

        self.__in_header: Dict[str, int] = {}
        self.__out_header: Dict[str, int] = {}
        self.__intra_header: Dict[str, int] = {}
        self.__assets: Set[str] = set()
        self.__exchanges: Set[str] = set()
        self.__holders: Set[str] = set()
        self.__generators: Set[str] = {f"{REPORT_GENERATOR_PACKAGE}.{generator}" for generator in country.get_report_generators()}
        self.__years_2_accounting_method_names: Dict[int, str] = {}

        if not Path(configuration_path).exists():
            raise RP2ValueError(f"Error: {configuration_path} does not exist")

        with open(configuration_path, encoding="utf-8") as configuration_file:
            try:
                # JSON configuration is deprecated: if JSON is detected, raise an exception
                json_configuration: Any = json.load(configuration_file)
                validate(instance=json_configuration, schema=CONFIGURATION_SCHEMA)
                raise RP2ValueError(
                    "Configuration file uses the deprecated JSON-format, instead of the INI format. "
                    f"To convert the JSON configuration to INI use: rp2_config {configuration_path}"
                )
            except json.JSONDecodeError:
                pass

            ini_configuration: ConfigParser = ConfigParser()
            ini_configuration.read(configuration_path)

            for section_name in ini_configuration.sections():
                section_name = section_name.strip()
                normalized_section_name: str = section_name.split(" ", 1)[0].strip()
                if normalized_section_name == Keyword.GENERAL.value:
                    if self.__assets or self.__exchanges or self.__holders:
                        raise RP2ValueError(f"{configuration_path}: section '{normalized_section_name}' found multiple times in configuration file")
                    self.__assets = self._validate_string_set(Keyword.ASSETS.value, ini_configuration[section_name], configuration_path)
                    self.__exchanges = self._validate_string_set(Keyword.EXCHANGES.value, ini_configuration[section_name], configuration_path)
                    self.__holders = self._validate_string_set(Keyword.HOLDERS.value, ini_configuration[section_name], configuration_path)
                    if Keyword.GENERATORS.value in ini_configuration:
                        self.__generators = self._validate_string_set(Keyword.GENERATORS.value, ini_configuration[section_name], configuration_path)
                elif normalized_section_name == Keyword.IN_HEADER.value:
                    if self.__in_header:
                        raise RP2ValueError(f"{configuration_path}: section '{normalized_section_name}' found multiple times in configuration file")
                    self.__in_header = self._validate_header_section(ini_configuration[section_name], normalized_section_name, configuration_path)
                elif normalized_section_name == Keyword.OUT_HEADER.value:
                    if self.__out_header:
                        raise RP2ValueError(f"{configuration_path}: section '{normalized_section_name}' found multiple times in configuration file")
                    self.__out_header = self._validate_header_section(ini_configuration[section_name], normalized_section_name, configuration_path)
                elif normalized_section_name == Keyword.INTRA_HEADER.value:
                    if self.__intra_header:
                        raise RP2ValueError(f"{configuration_path}: section '{normalized_section_name}' found multiple times in configuration file")
                    self.__intra_header = self._validate_header_section(ini_configuration[section_name], normalized_section_name, configuration_path)
                elif normalized_section_name == Keyword.ACCOUNTING_METHODS.value:
                    if self.__years_2_accounting_method_names:
                        raise RP2ValueError(f"{configuration_path}: section '{normalized_section_name}' found multiple times in configuration file")
                    self.__years_2_accounting_method_names = self._validate_accounting_method_section(ini_configuration[section_name], configuration_path)
                else:
                    raise RP2ValueError(f"{configuration_path}: invalid section '{section_name}' found")

        if not self.__assets:
            raise RP2ValueError(f"{configuration_path}: no '{Keyword.ASSETS.value}' field defined in {Keyword.GENERAL.value} section")
        if not self.__exchanges:
            raise RP2ValueError(f"{configuration_path}: no '{Keyword.EXCHANGES.value}' field defined in {Keyword.GENERAL.value} section")
        if not self.__holders:
            raise RP2ValueError(f"{configuration_path}: no '{Keyword.HOLDERS.value}' field defined in {Keyword.GENERAL.value} section")
        if not self.__in_header:
            raise RP2ValueError(f"{configuration_path}: empty '{Keyword.IN_HEADER.value}' section")
        if not self.__out_header:
            raise RP2ValueError(f"{configuration_path}: empty '{Keyword.OUT_HEADER.value}' section")
        if not self.__intra_header:
            raise RP2ValueError(f"{configuration_path}: empty '{Keyword.INTRA_HEADER.value}' section")

        # Used by __repr__()
        self.__sorted_assets: List[str] = sorted(self.__assets)
        self.__sorted_exchanges: List[str] = sorted(self.__exchanges)
        self.__sorted_holders: List[str] = sorted(self.__holders)

    def _validate_string_set(self, field_name: str, section: SectionProxy, configuration_path: str) -> Set[str]:
        if field_name not in section:
            raise RP2ValueError(f"{configuration_path}: section '{section.name}' doesn't contain mandatory field '{field_name}'")
        list_as_string = section[field_name]
        if not list_as_string or not list_as_string.strip():
            raise RP2ValueError(f"{configuration_path}: field '{field_name}' in section '{section.name}' cannot be empty")
        list_as_values: List[str] = [value.strip() for value in list_as_string.split(",")]
        if not list_as_values:
            raise RP2ValueError(f"{configuration_path}: field '{field_name}' in section '{section.name}' cannot be empty")
        result: Set[str] = set()
        for element in list_as_values:
            if not element:
                raise RP2ValueError(f"{configuration_path}: field '{field_name}' in section '{section.name}' cannot contain empty elements")
            if not isinstance(element, str):
                raise RP2ValueError(f"{configuration_path}: field '{field_name}' in section '{section.name}' cannot contain non-string elements")
            if element in result:
                raise RP2ValueError(f"{configuration_path}: field '{field_name}' in section '{section.name}' contains duplicate elements: {element}")
            result.add(element)
        return set(list_as_values)

    def _validate_header_section(self, section: SectionProxy, normalized_section_name: str, configuration_path: str) -> Dict[str, int]:
        if not section:
            raise RP2ValueError(f"{configuration_path}: section '{section.name}' cannot be empty")
        header_2_column: Dict[str, int] = {}
        column_to_header: Dict[int, str] = {}
        for header, column in section.items():
            try:
                column_value: int = int(column.strip())
                if column_value < 0:
                    raise RP2ValueError(
                        f"{configuration_path}: invalid column value for field '{header}' in section '{section.name}' (positive integer was expected): {column}"
                    )
                if column_value in column_to_header:
                    raise RP2ValueError(
                        f"{configuration_path}: fields '{column_to_header[column_value]}' and "
                        f"'{header}' have the same value in section '{section.name}': {column_value}"
                    )
                if header not in _HEADER_COLUMNS[normalized_section_name]:
                    raise RP2ValueError(f"{configuration_path}: invalid column header in section '{section.name}': {header}")
                header_2_column[header.strip()] = column_value
                column_to_header[column_value] = header
            except ValueError as exc:
                raise RP2ValueError(
                    f"{configuration_path}: invalid column value for field '{header}' in section '{section.name}' (integer was expected): {column}"
                ) from exc
            except TypeError as exc:
                raise RP2ValueError(
                    f"{configuration_path}: invalid value type for field '{header}' in section '{section.name}' (integer was expected): {column}"
                ) from exc
        return header_2_column

    def _validate_accounting_method_section(self, section: SectionProxy, configuration_path: str) -> Dict[int, str]:
        if not section:
            raise RP2ValueError(f"{configuration_path}: section '{section.name}' cannot be empty")
        result: Dict[int, str] = {}
        for year, method in section.items():
            try:
                numeric_year: int = int(year.strip())
                if numeric_year < MIN_DATE.year:
                    raise RP2ValueError(
                        f"{configuration_path}: invalid year value in accounting method section (integer > {MIN_DATE.year} was expected): {year}"
                    )
                result[numeric_year] = method.strip()
            except ValueError as exc:
                raise RP2ValueError(f"{configuration_path}: invalid year value in accounting method section (integer was expected): {year}") from exc
            except TypeError as exc:
                raise RP2ValueError(f"{configuration_path}: invalid year type in accounting method section (integer was expected): {year}") from exc
        return result

    def __repr__(self) -> str:
        return (
            f"Configuration(configuration_path={self.configuration_path}, "
            f"country={repr(self.country)}, "
            f"from_date={self.from_date if self.from_date > MIN_DATE else 'non-specified'}, "
            f"to_date={self.to_date if self.to_date < MAX_DATE else 'non-specified'}, "
            f"in_header={self.__in_header}, "
            f"out_header={self.__out_header}, "
            f"intra_header={self.__intra_header}, "
            f"assets={self.__sorted_assets}, "
            f"exchanges={self.__sorted_exchanges}, "
            f"holders={self.__sorted_holders})"
        )

    @property
    def configuration_path(self) -> str:
        return self.__configuration_path

    @property
    def country(self) -> AbstractCountry:
        return self.__country

    @property
    def from_date(self) -> date:
        return self.__from_date

    @property
    def to_date(self) -> date:
        return self.__to_date

    @property
    def assets(self) -> Set[str]:
        return self.__assets

    @property
    def generators(self) -> Set[str]:
        return self.__generators

    @property
    def years_2_accounting_method_names(self) -> Dict[int, str]:
        return self.__years_2_accounting_method_names

    def __get_table_constructor_argument_pack(self, data: List[Any], table_type: str, header: Dict[str, int]) -> Dict[str, Any]:
        if not isinstance(data, List):
            raise RP2TypeError(f"Parameter 'data' value is not a List: {data}")
        max_column: int = header[max(header, key=header.get)]  # type: ignore
        if len(data) <= max_column:
            raise RP2ValueError(
                f"Parameter 'data' has length {len(data)}, but required minimum from {table_type}-table headers in "
                f"{self.__configuration_path} is {max_column + 1}: {data}"
            )
        pack: Dict[str, Any] = {argument: data[position] for argument, position in header.items()}

        return pack

    def get_in_table_constructor_argument_pack(self, data: List[Any]) -> Dict[str, Any]:
        return self.__get_table_constructor_argument_pack(data, "in", self.__in_header)

    def get_out_table_constructor_argument_pack(self, data: List[Any]) -> Dict[str, Any]:
        return self.__get_table_constructor_argument_pack(data, "out", self.__out_header)

    def get_intra_table_constructor_argument_pack(self, data: List[Any]) -> Dict[str, Any]:
        return self.__get_table_constructor_argument_pack(data, "intra", self.__intra_header)

    def get_in_table_column_position(self, input_parameter: str) -> int:
        self.type_check_string("input_parameter", input_parameter)
        if input_parameter not in self.__in_header:
            raise RP2ValueError(f"Unknown 'input_parameter' {input_parameter}")
        return self.__in_header[input_parameter]

    def get_out_table_column_position(self, input_parameter: str) -> int:
        self.type_check_string("input_parameter", input_parameter)
        if input_parameter not in self.__out_header:
            raise RP2ValueError(f"Unknown 'input_parameter' {input_parameter}")
        return self.__out_header[input_parameter]

    def get_intra_table_column_position(self, input_parameter: str) -> int:
        self.type_check_string("input_parameter", input_parameter)
        if input_parameter not in self.__intra_header:
            raise RP2ValueError(f"Unknown 'input_parameter' {input_parameter}")
        return self.__intra_header[input_parameter]

    @classmethod
    def type_check_internal_id(cls, name: str, value: int) -> int:
        return cls.type_check_int(name, value)

    @classmethod
    def type_check_timestamp_from_string(cls, name: str, value: str) -> datetime:
        cls.type_check_string(name, value)
        try:
            result: datetime = parse(value)
        except Exception as exc:
            raise RP2ValueError(f"Error parsing parameter '{name}': {str(exc)}") from exc
        if result.tzinfo is None:
            raise RP2ValueError(f"Parameter '{name}' value has no timezone info: {value}")
        return result

    def type_check_exchange(self, name: str, value: str) -> str:
        self.type_check_string(name, value)
        if value not in self.__exchanges:
            raise RP2ValueError(f"Parameter '{name}' value is not known: {value}")
        return value

    def type_check_holder(self, name: str, value: str) -> str:
        self.type_check_string(name, value)
        if value not in self.__holders:
            raise RP2ValueError(f"Parameter '{name}' value is not known: {value}")
        return value

    def type_check_asset(self, name: str, value: str) -> str:
        self.type_check_string(name, value)
        if value not in self.__assets:
            raise RP2ValueError(f"Parameter '{name}' value is not known: {value}")
        return value

    @classmethod
    def type_check_parameter_name(cls, name: str) -> str:
        if not isinstance(name, str):
            raise RP2TypeError(f"Parameter name is not a string: {name}")
        return name

    @classmethod
    def type_check_string_or_integer(cls, name: str, value: str) -> str:
        cls.type_check_parameter_name(name)
        if not isinstance(value, (str, int, float)):
            raise RP2TypeError(f"Parameter '{name}' has non-string value {repr(value)}")
        return str(value)

    @classmethod
    def type_check_string(cls, name: str, value: str) -> str:
        cls.type_check_parameter_name(name)
        if not isinstance(value, str):
            raise RP2TypeError(f"Parameter '{name}' has non-string value {repr(value)}")
        return value

    @classmethod
    def type_check_positive_int(cls, name: str, value: int, non_zero: bool = False) -> int:
        result: int = cls.type_check_int(name, value)
        if result < 0:
            raise RP2ValueError(f"Parameter '{name}' has non-positive value {value}")
        if non_zero and result == 0:
            raise RP2ValueError(f"Parameter '{name}' has zero value")
        return result

    @classmethod
    def type_check_int(cls, name: str, value: int) -> int:
        cls.type_check_parameter_name(name)
        if not isinstance(value, int):
            raise RP2TypeError(f"Parameter '{name}' has non-integer value {repr(value)}")
        return value

    @classmethod
    def type_check_positive_float(cls, name: str, value: float, non_zero: bool = False) -> float:
        result: float = cls.type_check_float(name, value)
        if result < 0:
            raise RP2ValueError(f"Parameter '{name}' has non-positive value {value}")
        if non_zero and result == 0:
            raise RP2ValueError(f"Parameter '{name}' has zero value")
        return result

    @classmethod
    def type_check_float(cls, name: str, value: float) -> float:
        cls.type_check_parameter_name(name)
        if not isinstance(value, (int, float)):
            raise RP2TypeError(f"Parameter '{name}' has non-numeric value {repr(value)}")
        return value

    @classmethod
    def type_check_bool(cls, name: str, value: bool) -> bool:
        cls.type_check_parameter_name(name)
        if not isinstance(value, bool):
            raise RP2TypeError(f"Parameter '{name}' has non-bool value {repr(value)}")
        return value

    @classmethod
    def type_check_positive_decimal(cls, name: str, value: RP2Decimal, non_zero: bool = False) -> RP2Decimal:
        result: RP2Decimal = cls.type_check_decimal(name, value)
        if result < ZERO:
            raise RP2ValueError(f"Parameter '{name}' has non-positive value {value}")
        if non_zero and result == ZERO:
            raise RP2ValueError(f"Parameter '{name}' has zero value")
        return result

    @classmethod
    def type_check_decimal(cls, name: str, value: RP2Decimal) -> RP2Decimal:
        cls.type_check_parameter_name(name)
        if not isinstance(value, RP2Decimal):
            raise RP2TypeError(f"Parameter '{name}' has non-RP2Decimal value {repr(value)}")
        return value

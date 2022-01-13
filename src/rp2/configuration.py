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
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from dateutil.parser import parse
from jsonschema import validate  # type: ignore
from rp2.abstract_country import AbstractCountry
from rp2.configuration_schema import CONFIGURATION_SCHEMA
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError

VERSION: str = "0.9.6"
MAX_YEAR: int = sys.maxsize


class Configuration:  # pylint: disable=too-many-public-methods
    @classmethod
    def type_check(cls, name: str, instance: "Configuration") -> "Configuration":
        cls.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __init__(
        self,
        configuration_path: str,
        country: AbstractCountry,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
    ) -> None:
        self.__configuration_path: str = self.type_check_string("configuration_path", configuration_path)
        self.__country = AbstractCountry.type_check("country", country)
        self.__from_year: int = self.type_check_positive_int("from_year", from_year) if from_year is not None else 0
        self.__to_year: int = self.type_check_positive_int("to_year", to_year, non_zero=True) if to_year is not None else MAX_YEAR

        if self.__from_year > self.__to_year:
            raise RP2ValueError("Parameter from_year cannot be greater than to_year")

        self.__in_header: Dict[str, int]
        self.__out_header: Dict[str, int]
        self.__intra_header: Dict[str, int]
        self.__assets: Set[str]
        self.__exchanges: Set[str]
        self.__holders: Set[str]

        if not Path(configuration_path).exists():
            raise RP2ValueError(f"Error: {configuration_path} does not exist")

        with open(configuration_path, encoding="utf-8") as configuration_file:
            # This json_configuration is validated by jsonschema, so we can disable static type checking for it:
            # it adds complexity but not much value over jsonschema checks
            json_configuration: Any = json.load(configuration_file)
            validate(instance=json_configuration, schema=CONFIGURATION_SCHEMA)

            self.__in_header = json_configuration["in_header"]
            self.__out_header = json_configuration["out_header"]
            self.__intra_header = json_configuration["intra_header"]
            self.__assets = set(json_configuration["assets"])
            self.__exchanges = set(json_configuration["exchanges"])
            self.__holders = set(json_configuration["holders"])

        # Used by __repr__()
        self.__sorted_assets: List[str] = sorted(self.__assets)
        self.__sorted_exchanges: List[str] = sorted(self.__exchanges)
        self.__sorted_holders: List[str] = sorted(self.__holders)

    def __repr__(self) -> str:
        return (
            f"Configuration(configuration_path={self.configuration_path}, "
            f"country={repr(self.country)}, "
            f"from_year={self.from_year if self.from_year > 0 else 'non-specified'}, "
            f"to_year={self.to_year if self.to_year < MAX_YEAR else 'non-specified'}, "
            f"in_header={self.__in_header}, "
            f"out_header={self.__out_header}, "
            f"intra_header={self.__intra_header}, "
            f"assets={self.__sorted_assets}, "
            f"exchanges={self.__sorted_exchanges}, "
            f"holders={self.__sorted_holders})"
        )

    # Parametrized and extensible method to generate string representation
    @staticmethod
    def to_string(indent: int = 0, repr_format: bool = True, data: Optional[List[str]] = None) -> str:
        padding: str
        output: List[str] = []
        separator: str
        if not data:
            return ""

        if repr_format:
            padding = ""
            separator = ", "
            data[0] = f"{'  ' * indent}{data[0]}"
        else:
            padding = "  " * indent
            separator = "\n  "

        if data:
            for line in data:
                output.append(f"{padding}{line}")

        if repr_format:
            output[-1] += ")"

        # Joining by separator adds one level of indentation to internal fields (like id) in str mode, which is correct.
        return separator.join(output)

    @property
    def configuration_path(self) -> str:
        return self.__configuration_path

    @property
    def country(self) -> AbstractCountry:
        return self.__country

    @property
    def from_year(self) -> int:
        return self.__from_year

    @property
    def to_year(self) -> int:
        return self.__to_year

    @property
    def assets(self) -> Set[str]:
        return self.__assets

    def __get_table_constructor_argument_pack(self, data: List[Any], table_type: str, header: Dict[str, int]) -> Dict[str, Any]:
        if not isinstance(data, List):
            raise RP2TypeError(f"Parameter 'data' value is not a List: {data}")
        max_column: int = header[max(header, key=header.get)]  # type: ignore
        if len(data) <= max_column:
            raise RP2ValueError(
                f"Parameter 'data' has length {len(data)}, but required minimum from {table_type}-table headers in "
                f"{self.__configuration_path} is {max_column + 1}"
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
    def type_check_unique_id(cls, name: str, value: int) -> int:
        return cls.type_check_positive_int(name, value)

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

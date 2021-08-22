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

from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, List, Optional

from abstract_entry import AbstractEntry
from configuration import Configuration
from entry_types import TransactionType
from rp2_error import RP2TypeError


class AbstractTransaction(AbstractEntry):
    def __init__(
        self,
        configuration: Configuration,
        line: int,
        timestamp: str,
        asset: str,
        transaction_type: str,
        spot_price: Decimal,
        notes: Optional[str] = None,
    ) -> None:
        super().__init__(configuration, asset)

        self.__line: int = configuration.type_check_line("line", line)
        self.__timestamp: datetime = configuration.type_check_timestamp_from_string("timestamp", timestamp)
        self.__transaction_type: TransactionType = TransactionType.type_check_from_string("transaction_type", transaction_type)
        self.__spot_price: Decimal = configuration.type_check_positive_decimal("spot_price", spot_price)
        self.__notes = configuration.type_check_string("notes", notes) if notes else ""

    @classmethod
    def type_check(cls, name: str, instance: "AbstractEntry") -> "AbstractEntry":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    # Experimental hash implementation
    def __eq__(self, other: object) -> bool:
        if not other:
            return False
        if not isinstance(other, AbstractTransaction):
            raise RP2TypeError(f"Operand has non-AbstractTransaction value {repr(other)}")
        # Since there are no cross-asset transactions, line is enough to uniquely identify a transaction
        result: bool = self.line == other.line
        return result

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        # Since there are no cross-asset transactions, line is enough to uniquely identify a transaction
        return hash(self.line)

    def to_string(self, indent: int = 0, repr_format: bool = True, extra_data: Optional[List[str]] = None) -> str:
        padding: str
        output: List[str] = []
        separator: str
        stringify: Callable[[Any], str]

        if repr_format:
            padding = ""
            separator = ", "
            stringify = repr
            output.append(f"{'  ' * indent}{type(self).__name__}(line={stringify(self.line)}")
        else:
            padding = "  " * (indent)
            separator = "\n  "
            stringify = str
            output.append(f"{padding}{type(self).__name__}:")
            output.append(f"{padding}line={stringify(self.line)}")  # type: ignore

        output.append(f"{padding}timestamp={stringify(self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f %z'))}")
        output.append(f"{padding}asset={stringify(self.asset)}")

        if extra_data:
            for line in extra_data:
                output.append(f"{padding}{line}")

        if repr_format:
            output[-1] += ")"

        return separator.join(output)

    @property
    def identifier(self) -> str:
        return str(self.line)

    @property
    def line(self) -> int:
        return self.__line

    @property
    def timestamp(self) -> datetime:
        return self.__timestamp

    @property
    def transaction_type(self) -> TransactionType:
        return self.__transaction_type

    @property
    def spot_price(self) -> Decimal:
        return self.__spot_price

    @property
    def notes(self) -> str:
        return self.__notes

    @property
    def crypto_taxable_amount(self) -> Decimal:
        raise NotImplementedError("Abstract property")

    @property
    def usd_taxable_amount(self) -> Decimal:
        raise NotImplementedError("Abstract property")

    def is_taxable(self) -> bool:
        raise NotImplementedError("Abstract method")

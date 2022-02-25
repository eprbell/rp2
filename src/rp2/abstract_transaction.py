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
from typing import Callable, List, Optional

from rp2.abstract_entry import AbstractEntry
from rp2.configuration import Configuration
from rp2.entry_types import TransactionType
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError


class AbstractTransaction(AbstractEntry):
    def __init__(
        self,
        configuration: Configuration,
        timestamp: str,
        asset: str,
        transaction_type: str,
        spot_price: RP2Decimal,
        internal_id: Optional[int] = None,
        unique_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        super().__init__(configuration, asset)

        self.__timestamp: datetime = configuration.type_check_timestamp_from_string("timestamp", timestamp)
        self.__transaction_type: TransactionType = TransactionType.type_check_from_string("transaction_type", transaction_type)
        self.__spot_price: RP2Decimal = configuration.type_check_positive_decimal("spot_price", spot_price)
        self.__internal_id: int = configuration.type_check_internal_id("internal_id", internal_id) if internal_id is not None else id(self)
        self.__unique_id: str = configuration.type_check_string("unique_id", unique_id) if unique_id is not None else ""
        self.__notes = configuration.type_check_string("notes", notes) if notes else ""

    @classmethod
    def type_check(cls, name: str, instance: "AbstractEntry") -> "AbstractEntry":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __eq__(self, other: object) -> bool:
        if not other:
            return False
        if not isinstance(other, AbstractTransaction):
            raise RP2TypeError(f"Operand has non-AbstractTransaction value {repr(other)}")
        # By definition, internal_id can uniquely identify a transaction: this works even if it's the ODS line from the spreadsheet,
        # since there are no cross-asset transactions (so a spreadsheet line points to a unique transaction for that asset).
        result: bool = self.internal_id == other.internal_id
        return result

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        # By definition, internal_id can uniquely identify a transaction: this works even if it's the ODS line from the spreadsheet,
        # since there are no cross-asset transactions (so a spreadsheet line points to a unique transaction for that asset).
        return hash(self.internal_id)

    def to_string(self, indent: int = 0, repr_format: bool = True, extra_data: Optional[List[str]] = None) -> str:
        class_specific_data: List[str] = []
        stringify: Callable[[object], str] = repr
        if not repr_format:
            stringify = str

        class_specific_data.append(f"timestamp={stringify(self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f %z'))}")
        class_specific_data.append(f"asset={stringify(self.asset)}")

        if extra_data:
            class_specific_data.extend(extra_data)

        return super().to_string(indent=indent, repr_format=repr_format, extra_data=class_specific_data)

    @property
    def internal_id(self) -> str:
        return str(self.__internal_id)

    @property
    def timestamp(self) -> datetime:
        return self.__timestamp

    @property
    def transaction_type(self) -> TransactionType:
        return self.__transaction_type

    @property
    def spot_price(self) -> RP2Decimal:
        return self.__spot_price

    @property
    def unique_id(self) -> str:
        return str(self.__unique_id)

    @property
    def notes(self) -> str:
        return self.__notes

    # Crypto amount that is taxed
    @property
    def crypto_taxable_amount(self) -> RP2Decimal:
        raise NotImplementedError("Abstract property")

    # Fiat amount that is taxed
    @property
    def fiat_taxable_amount(self) -> RP2Decimal:
        raise NotImplementedError("Abstract property")

    # Crypto amount that is not taxed
    @property
    def crypto_deduction(self) -> RP2Decimal:
        raise NotImplementedError("Abstract property")

    # Fiat amount that is not taxed
    @property
    def fiat_deduction(self) -> RP2Decimal:
        raise NotImplementedError("Abstract property")

    def is_taxable(self) -> bool:
        raise NotImplementedError("Abstract method")

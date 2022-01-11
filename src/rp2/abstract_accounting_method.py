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

from typing import Iterator, NamedTuple, Optional

from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError


class TaxableEventAndFromLot(NamedTuple):
    taxable_event: AbstractTransaction
    from_lot: Optional[InTransaction]
    taxable_event_amount: RP2Decimal
    from_lot_amount: RP2Decimal


class TaxableEventsExhaustedException(Exception):
    def __init__(self, message: str = "") -> None:
        self.__message = message
        super().__init__(self.__message)

    def __repr__(self) -> str:
        return self.message

    @property
    def message(self) -> str:
        return self.__message


class FromLotsExhaustedException(Exception):
    def __init__(self, message: str = "") -> None:
        self.__message = message
        super().__init__(self.__message)

    def __repr__(self) -> str:
        return self.message

    @property
    def message(self) -> str:
        return self.__message


class AbstractAccountingMethod:
    @classmethod
    def type_check(cls, name: str, instance: "AbstractAccountingMethod") -> "AbstractAccountingMethod":
        if not isinstance(name, str):
            raise RP2TypeError(f"Parameter name is not a string: {repr(name)}")
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    # Iterators yield transactions in ascending chronological order
    def initialize(self, taxable_event_iterator: Iterator[AbstractTransaction], from_lot_iterator: Iterator[InTransaction]) -> None:
        raise NotImplementedError("Abstract function")

    def get_next_taxable_event_and_amount(
        self, taxable_event: Optional[AbstractTransaction], from_lot: Optional[InTransaction], taxable_event_amount: RP2Decimal, from_lot_amount: RP2Decimal
    ) -> TaxableEventAndFromLot:
        raise NotImplementedError("Abstract function")

    def get_from_lot_for_taxable_event(
        self, taxable_event: AbstractTransaction, from_lot: Optional[InTransaction], taxable_event_amount: RP2Decimal, from_lot_amount: RP2Decimal
    ) -> TaxableEventAndFromLot:
        raise NotImplementedError("Abstract function")

    def validate_from_lot_ancestor_timestamp(self, from_lot: InTransaction, from_lot_parent: InTransaction) -> bool:
        raise NotImplementedError("Abstract function")

    @property
    def name(self) -> str:
        return f"{self.__class__.__module__.rsplit('.', 1)[1]}"

    def __repr__(self) -> str:
        return self.name

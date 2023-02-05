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


from enum import Enum
from typing import Dict, List, NamedTuple, Optional

from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError


class AcquiredLotAndAmount(NamedTuple):
    acquired_lot: InTransaction
    amount: RP2Decimal


class AcquiredLotCandidatesOrder(Enum):
    OLDER_TO_NEWER: str = "older_to_newer"
    NEWER_TO_OLDER: str = "newer_to_older"


class AcquiredLotCandidates:
    def __init__(
        self,
        accounting_method: "AbstractAccountingMethod",
        acquired_lot_list: List[InTransaction],
        acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal],
        up_to_index: int,
    ) -> None:
        self.__accounting_method: AbstractAccountingMethod = accounting_method
        self.__acquired_lot_list = acquired_lot_list
        self.__acquired_lot_2_partial_amount = acquired_lot_2_partial_amount
        self.__up_to_index = up_to_index

    def has_partial_amount(self, acquired_lot: InTransaction) -> bool:
        return acquired_lot in self.__acquired_lot_2_partial_amount

    def get_partial_amount(self, acquired_lot: InTransaction) -> RP2Decimal:
        if not self.has_partial_amount(acquired_lot):
            raise RP2RuntimeError(f"Internal error: acquired lot has no partial amount: {acquired_lot}")
        return self.__acquired_lot_2_partial_amount[acquired_lot]

    def set_partial_amount(self, acquired_lot: InTransaction, amount: RP2Decimal) -> None:
        self.__acquired_lot_2_partial_amount[acquired_lot] = amount

    def clear_partial_amount(self, acquired_lot: InTransaction) -> None:
        self.set_partial_amount(acquired_lot, ZERO)

    def __iter__(self) -> "AccountingMethodIterator":
        return AccountingMethodIterator(self.__acquired_lot_list, self.__up_to_index, self.__accounting_method.lot_candidates_order())


class AccountingMethodIterator:
    def __init__(self, acquired_lot_list: List[InTransaction], up_to_index: int, order_type: AcquiredLotCandidatesOrder) -> None:
        self.__acquired_lot_list = acquired_lot_list
        self.__start_index = 0 if order_type == AcquiredLotCandidatesOrder.OLDER_TO_NEWER else up_to_index
        self.__end_index = up_to_index if order_type == AcquiredLotCandidatesOrder.OLDER_TO_NEWER else 0
        self.__step = 1 if order_type == AcquiredLotCandidatesOrder.OLDER_TO_NEWER else -1
        self.__index = self.__start_index
        self.__order_type = order_type

    def _check_index(self) -> bool:
        if self.__order_type == AcquiredLotCandidatesOrder.OLDER_TO_NEWER:
            return self.__index <= self.__end_index
        return self.__index >= self.__end_index

    def __next__(self) -> InTransaction:
        result: Optional[InTransaction] = None
        while self._check_index():
            result = self.__acquired_lot_list[self.__index]
            self.__index += self.__step
            return result
        raise StopIteration(self)


class AbstractAccountingMethod:
    def seek_non_exhausted_acquired_lot(
        self,
        lot_candidates: AcquiredLotCandidates,
        taxable_event: Optional[AbstractTransaction],
        taxable_event_amount: RP2Decimal,
    ) -> Optional[AcquiredLotAndAmount]:
        raise NotImplementedError("Abstract function")

    def lot_candidates_order(self) -> AcquiredLotCandidatesOrder:
        raise NotImplementedError("Abstract function")

    @property
    def name(self) -> str:
        return f"{self.__class__.__module__.rsplit('.', 1)[1]}"

    def __repr__(self) -> str:
        return self.name

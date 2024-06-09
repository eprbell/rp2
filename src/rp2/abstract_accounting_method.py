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
from heapq import heappop, heappush
from typing import Dict, List, NamedTuple, Optional, Tuple

from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2TypeError


class AbstractAccountingMethodIterator:
    def __next__(self) -> InTransaction:
        raise NotImplementedError("abstract function")


class AcquiredLotAndAmount(NamedTuple):
    acquired_lot: InTransaction
    amount: RP2Decimal


class AcquiredLotCandidatesOrder(Enum):
    OLDER_TO_NEWER: str = "older_to_newer"
    NEWER_TO_OLDER: str = "newer_to_older"


class AcquiredLotHeapSortKey(NamedTuple):
    spot_price: RP2Decimal
    timestamp: float
    internal_id_int: int


class AbstractAcquiredLotCandidates:
    def __init__(
        self,
        accounting_method: "AbstractAccountingMethod",
        acquired_lot_list: List[InTransaction],
        acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal],
    ) -> None:
        self._accounting_method: AbstractAccountingMethod = accounting_method
        self.__acquired_lot_list = acquired_lot_list
        self.__acquired_lot_2_partial_amount = acquired_lot_2_partial_amount
        self._to_index = 0
        self.__from_index = 0

    def set_from_index(self, from_index: int) -> None:
        self.__from_index = from_index

    def set_to_index(self, to_index: int) -> None:
        raise NotImplementedError("abstract")

    @property
    def from_index(self) -> int:
        return self.__from_index

    @property
    def to_index(self) -> int:
        return self._to_index

    @property
    def acquired_lot_list(self) -> List[InTransaction]:
        return self.__acquired_lot_list

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

    def __iter__(self) -> AbstractAccountingMethodIterator:
        return self._accounting_method._get_accounting_method_iterator(self)


class ListAccountingMethodIterator(AbstractAccountingMethodIterator):
    def __init__(self, acquired_lot_list: List[InTransaction], from_index: int, to_index: int, order_type: AcquiredLotCandidatesOrder) -> None:
        self.__acquired_lot_list = acquired_lot_list
        self.__start_index = from_index if order_type == AcquiredLotCandidatesOrder.OLDER_TO_NEWER else to_index
        self.__end_index = to_index if order_type == AcquiredLotCandidatesOrder.OLDER_TO_NEWER else from_index
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


class HeapAccountingMethodIterator(AbstractAccountingMethodIterator):
    def __init__(self, acquired_lot_heap: List[Tuple[AcquiredLotHeapSortKey, InTransaction]]) -> None:
        self.__acquired_lot_heap = acquired_lot_heap

    def __next__(self) -> InTransaction:
        while len(self.__acquired_lot_heap) > 0:
            _, result = heappop(self.__acquired_lot_heap)
            return result
        raise StopIteration(self)


class ListAcquiredLotCandidates(AbstractAcquiredLotCandidates):
    def set_to_index(self, to_index: int) -> None:
        self._to_index = to_index  # pylint: disable=unused-private-member


class HeapAcquiredLotCandidates(AbstractAcquiredLotCandidates):
    _accounting_method: "AbstractHeapAccountingMethod"

    def __init__(
        self,
        accounting_method: "AbstractAccountingMethod",
        acquired_lot_list: List[InTransaction],
        acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal],
    ) -> None:
        super().__init__(accounting_method, acquired_lot_list, acquired_lot_2_partial_amount)
        self.__acquired_lot_heap: List[Tuple[AcquiredLotHeapSortKey, InTransaction]] = []

    def set_to_index(self, to_index: int) -> None:
        # Control how far to advance the iterator, caller is responsible for updating
        for i in range(self.to_index, to_index + 1):
            lot = self.acquired_lot_list[i]
            self._accounting_method.add_selected_lot_to_heap(self.acquired_lot_heap, lot)
        self._to_index = to_index

    @property
    def acquired_lot_heap(self) -> List[Tuple[AcquiredLotHeapSortKey, InTransaction]]:
        return self.__acquired_lot_heap


class AbstractAccountingMethod:
    def create_lot_candidates(
        self, acquired_lot_list: List[InTransaction], acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal]
    ) -> AbstractAcquiredLotCandidates:
        raise NotImplementedError("abstract")

    def seek_non_exhausted_acquired_lot(
        self,
        lot_candidates: AbstractAcquiredLotCandidates,
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

    def _get_accounting_method_iterator(self, lot_candidates: AbstractAcquiredLotCandidates) -> AbstractAccountingMethodIterator:
        raise NotImplementedError("Abstract function")


class AbstractListAccountingMethod(AbstractAccountingMethod):
    def create_lot_candidates(
        self, acquired_lot_list: List[InTransaction], acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal]
    ) -> ListAcquiredLotCandidates:
        return ListAcquiredLotCandidates(self, acquired_lot_list, acquired_lot_2_partial_amount)

    def lot_candidates_order(self) -> AcquiredLotCandidatesOrder:
        raise NotImplementedError("Abstract function")

    def _get_accounting_method_iterator(self, lot_candidates: AbstractAcquiredLotCandidates) -> ListAccountingMethodIterator:
        return ListAccountingMethodIterator(lot_candidates.acquired_lot_list, lot_candidates.from_index, lot_candidates.to_index, self.lot_candidates_order())


class AbstractHeapAccountingMethod(AbstractAccountingMethod):
    def create_lot_candidates(
        self, acquired_lot_list: List[InTransaction], acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal]
    ) -> HeapAcquiredLotCandidates:
        return HeapAcquiredLotCandidates(self, acquired_lot_list, acquired_lot_2_partial_amount)

    def add_selected_lot_to_heap(self, heap: List[Tuple[AcquiredLotHeapSortKey, InTransaction]], lot: InTransaction) -> None:
        heap_item = (self.heap_key(lot), lot)
        heappush(heap, heap_item)

    def heap_key(self, lot: InTransaction) -> AcquiredLotHeapSortKey:
        raise NotImplementedError("Abstract function")

    def _get_accounting_method_iterator(self, lot_candidates: AbstractAcquiredLotCandidates) -> HeapAccountingMethodIterator:
        if not isinstance(lot_candidates, HeapAcquiredLotCandidates):
            raise RP2TypeError(f"Internal error: lot_candidates is not of type HeapAcquiredLotCandidates, but of type {type(lot_candidates)}")
        return HeapAccountingMethodIterator(lot_candidates.acquired_lot_heap)

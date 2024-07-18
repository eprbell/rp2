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


class AcquiredLotAndAmount(NamedTuple):
    acquired_lot: InTransaction
    amount: RP2Decimal


class AcquiredLotCandidatesOrder(Enum):
    OLDER_TO_NEWER: str = "older_to_newer"
    NEWER_TO_OLDER: str = "newer_to_older"


class AcquiredLotSortKey(NamedTuple):
    spot_price: RP2Decimal
    timestamp: float
    internal_id_int: int


class AbstractAccountingMethodIterator:
    def __next__(self) -> InTransaction:
        raise NotImplementedError("abstract function")


class ChronologicalAccountingMethodIterator(AbstractAccountingMethodIterator):
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


class FeatureBasedAccountingMethodIterator(AbstractAccountingMethodIterator):
    def __init__(self, acquired_lot_heap: List[Tuple[AcquiredLotSortKey, InTransaction]]) -> None:
        self.__acquired_lot_heap = acquired_lot_heap

    def __next__(self) -> InTransaction:
        while len(self.__acquired_lot_heap) > 0:
            _, result = heappop(self.__acquired_lot_heap)
            return result
        raise StopIteration(self)


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
        self.__to_index = 0
        self.__from_index = 0

    def set_from_index(self, from_index: int) -> None:
        self.__from_index = from_index

    def set_to_index(self, to_index: int) -> None:
        self.__to_index = to_index  # pylint: disable=unused-private-member

    @property
    def from_index(self) -> int:
        return self.__from_index

    @property
    def to_index(self) -> int:
        return self.__to_index

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
        return self._accounting_method._create_accounting_method_iterator(self)


class ChronologicalAcquiredLotCandidates(AbstractAcquiredLotCandidates):
    pass


class FeatureBasedAcquiredLotCandidates(AbstractAcquiredLotCandidates):
    _accounting_method: "AbstractFeatureBasedAccountingMethod"

    def __init__(
        self,
        accounting_method: "AbstractAccountingMethod",
        acquired_lot_list: List[InTransaction],
        acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal],
    ) -> None:
        super().__init__(accounting_method, acquired_lot_list, acquired_lot_2_partial_amount)
        self.__acquired_lot_heap: List[Tuple[AcquiredLotSortKey, InTransaction]] = []

    def set_to_index(self, to_index: int) -> None:
        # Control how far to advance the iterator, caller is responsible for updating
        for i in range(self.to_index, to_index + 1):
            lot = self.acquired_lot_list[i]
            self._accounting_method.add_selected_lot_to_heap(self.acquired_lot_heap, lot)
        super().set_to_index(to_index)

    @property
    def acquired_lot_heap(self) -> List[Tuple[AcquiredLotSortKey, InTransaction]]:
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

    @property
    def name(self) -> str:
        return f"{self.__class__.__module__.rsplit('.', 1)[1]}"

    def __repr__(self) -> str:
        return self.name

    def _create_accounting_method_iterator(self, lot_candidates: AbstractAcquiredLotCandidates) -> AbstractAccountingMethodIterator:
        raise NotImplementedError("Abstract function")


class AbstractChronologicalAccountingMethod(AbstractAccountingMethod):
    def create_lot_candidates(
        self, acquired_lot_list: List[InTransaction], acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal]
    ) -> ChronologicalAcquiredLotCandidates:
        return ChronologicalAcquiredLotCandidates(self, acquired_lot_list, acquired_lot_2_partial_amount)

    def lot_candidates_order(self) -> AcquiredLotCandidatesOrder:
        raise NotImplementedError("Abstract function")

    def _create_accounting_method_iterator(self, lot_candidates: AbstractAcquiredLotCandidates) -> ChronologicalAccountingMethodIterator:
        return ChronologicalAccountingMethodIterator(
            lot_candidates.acquired_lot_list, lot_candidates.from_index, lot_candidates.to_index, self.lot_candidates_order()
        )

    def seek_non_exhausted_acquired_lot(
        self,
        lot_candidates: AbstractAcquiredLotCandidates,
        taxable_event: Optional[AbstractTransaction],
        taxable_event_amount: RP2Decimal,
    ) -> Optional[AcquiredLotAndAmount]:
        selected_acquired_lot_amount: RP2Decimal = ZERO
        selected_acquired_lot: Optional[InTransaction] = None
        acquired_lot: InTransaction
        # The FIFO plugin features linear complexity by setting lot_candidates from_index to the first non-exhausted lot (to_index is set in the caller).
        # As FIFO ensures no non-exhausted lots can exist to the left of this index, this approach is O(n).
        for acquired_lot in lot_candidates:
            acquired_lot_amount: RP2Decimal = ZERO

            if not lot_candidates.has_partial_amount(acquired_lot):
                acquired_lot_amount = acquired_lot.crypto_in
            elif lot_candidates.get_partial_amount(acquired_lot) > ZERO:
                acquired_lot_amount = lot_candidates.get_partial_amount(acquired_lot)
            else:
                # The acquired lot has zero partial amount, so we can advance our start offset
                lot_candidates.set_from_index(lot_candidates.from_index + 1)
                continue

            selected_acquired_lot_amount = acquired_lot_amount
            selected_acquired_lot = acquired_lot
            break

        if selected_acquired_lot_amount > ZERO and selected_acquired_lot:
            lot_candidates.clear_partial_amount(selected_acquired_lot)
            return AcquiredLotAndAmount(acquired_lot=selected_acquired_lot, amount=selected_acquired_lot_amount)
        return None


class AbstractFeatureBasedAccountingMethod(AbstractAccountingMethod):
    def create_lot_candidates(
        self, acquired_lot_list: List[InTransaction], acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal]
    ) -> FeatureBasedAcquiredLotCandidates:
        return FeatureBasedAcquiredLotCandidates(self, acquired_lot_list, acquired_lot_2_partial_amount)

    def add_selected_lot_to_heap(self, heap: List[Tuple[AcquiredLotSortKey, InTransaction]], lot: InTransaction) -> None:
        heap_item = (self.sort_key(lot), lot)
        heappush(heap, heap_item)

    def sort_key(self, lot: InTransaction) -> AcquiredLotSortKey:
        raise NotImplementedError("Abstract function")

    def _create_accounting_method_iterator(self, lot_candidates: AbstractAcquiredLotCandidates) -> FeatureBasedAccountingMethodIterator:
        if not isinstance(lot_candidates, FeatureBasedAcquiredLotCandidates):
            raise RP2TypeError(f"Internal error: lot_candidates is not of type FeatureBasedAcquiredLotCandidates, but of type {type(lot_candidates)}")
        return FeatureBasedAccountingMethodIterator(lot_candidates.acquired_lot_heap)

    def seek_non_exhausted_acquired_lot(
        self,
        lot_candidates: AbstractAcquiredLotCandidates,
        taxable_event: Optional[AbstractTransaction],
        taxable_event_amount: RP2Decimal,
    ) -> Optional[AcquiredLotAndAmount]:
        selected_acquired_lot_amount: RP2Decimal = ZERO
        selected_acquired_lot: Optional[InTransaction] = None
        acquired_lot: InTransaction
        if not isinstance(lot_candidates, FeatureBasedAcquiredLotCandidates):
            raise RP2TypeError(f"Internal error: lot_candidates is not of type FeatureBasedAcquiredLotCandidates, but of type {type(lot_candidates)}")
        # This plugin features O(n * log(m)) complexity, where n is the number
        # of transactions and m is the number of unexhausted acquistion lots
        for acquired_lot in lot_candidates:
            acquired_lot_amount: RP2Decimal = ZERO

            if not lot_candidates.has_partial_amount(acquired_lot):
                acquired_lot_amount = acquired_lot.crypto_in
            elif lot_candidates.get_partial_amount(acquired_lot) > ZERO:
                acquired_lot_amount = lot_candidates.get_partial_amount(acquired_lot)
            else:
                # The acquired lot has zero partial amount
                continue

            selected_acquired_lot_amount = acquired_lot_amount
            selected_acquired_lot = acquired_lot
            break

        if selected_acquired_lot_amount > ZERO and selected_acquired_lot:
            lot_candidates.clear_partial_amount(selected_acquired_lot)
            if selected_acquired_lot_amount > taxable_event_amount:
                self.add_selected_lot_to_heap(lot_candidates.acquired_lot_heap, selected_acquired_lot)
            return AcquiredLotAndAmount(acquired_lot=selected_acquired_lot, amount=selected_acquired_lot_amount)
        return None

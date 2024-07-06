# Copyright 2022 ninideol
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

from typing import Optional

from rp2.abstract_accounting_method import (
    AbstractAcquiredLotCandidates,
    AbstractHeapAccountingMethod,
    AcquiredLotAndAmount,
    AcquiredLotHeapSortKey,
    HeapAcquiredLotCandidates,
)
from rp2.abstract_transaction import AbstractTransaction
from rp2.rp2_error import RP2TypeError
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal


# HIFO (Highest In, First Out) plugin. See https://www.investopedia.com/terms/h/hifo.asp. This plugin uses universal application, not per-wallet application:
# this means there is one queue for each coin across every wallet and exchange and the accounting method is applied to each such queue.
# More on this at https://www.forbes.com/sites/shehanchandrasekera/2020/09/17/what-crypto-taxpayers-need-to-know-about-fifo-lifo-hifo-specific-id/
class AccountingMethod(AbstractHeapAccountingMethod):
    def seek_non_exhausted_acquired_lot(
        self,
        lot_candidates: AbstractAcquiredLotCandidates,
        taxable_event: Optional[AbstractTransaction],
        taxable_event_amount: RP2Decimal,
    ) -> Optional[AcquiredLotAndAmount]:
        selected_acquired_lot_amount: RP2Decimal = ZERO
        selected_acquired_lot: Optional[InTransaction] = None
        acquired_lot: InTransaction
        if not isinstance(lot_candidates, HeapAcquiredLotCandidates):
            raise RP2TypeError(f"Internal error: lot_candidates is not of type HeapAcquiredLotCandidates, but of type {type(lot_candidates)}")
        # The HIFO plugin features O(n * log(m)) complexity where n is the number
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

    def heap_key(self, lot: InTransaction) -> AcquiredLotHeapSortKey:
        return AcquiredLotHeapSortKey(-lot.spot_price, lot.timestamp.timestamp(), lot.row)

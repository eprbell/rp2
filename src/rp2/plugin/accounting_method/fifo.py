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

from typing import Optional

from rp2.abstract_accounting_method import (
    AbstractAccountingMethod,
    AcquiredLotAndAmount,
    AcquiredLotCandidates,
    AcquiredLotCandidatesOrder,
)
from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal


# FIFO (First In, First Out) plugin. See https://www.investopedia.com/terms/l/fifo.asp. This plugin uses universal application, not per-wallet application:
# this means there is one queue for each coin across every wallet and exchange and the accounting method is applied to each such queue.
# More on this at https://www.forbes.com/sites/shehanchandrasekera/2020/09/17/what-crypto-taxpayers-need-to-know-about-fifo-lifo-hifo-specific-id/
class AccountingMethod(AbstractAccountingMethod):
    def seek_non_exhausted_acquired_lot(
        self,
        lot_candidates: AcquiredLotCandidates,
        taxable_event: Optional[AbstractTransaction],
        taxable_event_amount: RP2Decimal,
    ) -> Optional[AcquiredLotAndAmount]:
        selected_acquired_lot_amount: RP2Decimal = ZERO
        selected_acquired_lot: Optional[InTransaction] = None
        acquired_lot: InTransaction
        # This loop avoids O(m*n) complexity by keeping track of the index of the most recently exhausted lot.
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

    def lot_candidates_order(self) -> AcquiredLotCandidatesOrder:
        return AcquiredLotCandidatesOrder.OLDER_TO_NEWER

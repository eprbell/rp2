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


# LIFO plugin. See https://www.investopedia.com/terms/l/lifo.asp. Note that under LIFO the date acquired must still be before or on the date sold:
# see this discussion for details,
# https://ttlc.intuit.com/community/investments-and-rental-properties/discussion/using-lifo-method-for-cryptocurrency-or-even-stock-cost-basis/00/1433542
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
        # This loop causes O(m*n) complexity, where m is the number of acquired lots and n in the number of taxable events. The taxable
        # event loop is in the caller. Non-trivial optimizations are possible using different data structures but they need to be researched.
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
            return AcquiredLotAndAmount(acquired_lot=selected_acquired_lot, amount=selected_acquired_lot_amount)
        return None

    def lot_candidates_order(self) -> AcquiredLotCandidatesOrder:
        return AcquiredLotCandidatesOrder.NEWER_TO_OLDER

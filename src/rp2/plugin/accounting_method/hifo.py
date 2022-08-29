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

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.abstract_accounting_method import AcquiredLotCandidates, AcquiredLotCandidatesOrder, AcquiredLotAndAmount
from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal


# HIFO plugin. See https://www.investopedia.com/terms/h/hifo.asp
class AccountingMethod(AbstractAccountingMethod):
    def seek_non_exhausted_acquired_lot(
        self,
        lot_candidates: AcquiredLotCandidates,
        taxable_event: Optional[AbstractTransaction],
        taxable_event_amount: RP2Decimal,
    ) -> Optional[AcquiredLotAndAmount]:
        # This loop causes O(m*n) complexity, where m is the number of acquired lots and n in the number of taxable events. The taxable
        # event loop is in the caller. Non-trivial optimizations are possible using different data structures but they need to be
        # researched (and they are likely to have expensive space/time tradeoff): e.g. a dict mapping timestamp to list of transactions
        # before that timestamp, ordered by spot price. Note that such a dict would have to have a new copy of the list for each
        # timestamp: i.e. we can't just use a single list tracking what's the next highest-priced transaction before a timestamp. This
        # is because the "next highest-priced" transaction can vary, depending on what is the initial transaction: in other words the
        # order is not global, it's relative to the initial transaction. For example:
        # * 2020-08-10, 1 BTC, $20000
        # * 2020-09-10, 1 BTC, $10000
        # * 2020-10-10, 1 BTC, $15000
        # * 2020-11-10, 1 BTC, $5000
        # If the initial timestamp is 2020-08-10, the list is: 2020-08-10, 2020-10-10, 2020-09-10, 2020-11-10.
        # If the initial timestamp is 2020-10-10, the list is: 2020-10-10, 2020-11-10.
        # The second list is not a slice of the first, so we couldn't use a single list to cover all transactions: we would have to
        # have separate list for each transaction. This would mean trading off O(n^2) time for O(n^2) space. This may cause users with
        # lots of transactions (e.g. high frequency traders) to run out of memory. There may be more complex solutions that are faster
        # without needing quadratic memory, but they need to be researched.
        selected_acquired_lot_amount: RP2Decimal = ZERO
        selected_acquired_lot: Optional[InTransaction] = None
        acquired_lot: InTransaction
        for acquired_lot in lot_candidates:
            acquired_lot_amount: RP2Decimal = ZERO

            if not lot_candidates.has_partial_amount(acquired_lot):
                acquired_lot_amount = acquired_lot.crypto_in
            elif lot_candidates.get_partial_amount(acquired_lot) > ZERO:
                acquired_lot_amount = lot_candidates.get_partial_amount(acquired_lot)
            else:
                # The acquired lot has zero partial amount
                continue

            if selected_acquired_lot is None or selected_acquired_lot.spot_price < acquired_lot.spot_price:
                selected_acquired_lot_amount = acquired_lot_amount
                selected_acquired_lot = acquired_lot

        if selected_acquired_lot_amount > ZERO and selected_acquired_lot:
            lot_candidates.clear_partial_amount(selected_acquired_lot)
            return AcquiredLotAndAmount(acquired_lot=selected_acquired_lot, amount=selected_acquired_lot_amount)
        return None

    def lot_candidates_order(self) -> AcquiredLotCandidatesOrder:
        return AcquiredLotCandidatesOrder.OLDER_TO_NEWER

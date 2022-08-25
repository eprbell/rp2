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

from typing import List, Optional

from rp2.abstract_specific_id import AbstractSpecificId, AcquiredLotAndAmount
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal


# LIFO plugin. See https://www.investopedia.com/terms/l/lifo.asp. Note that under LIFO the date acquired must still be before or on the date sold:
# see this discussion for details,
# https://ttlc.intuit.com/community/investments-and-rental-properties/discussion/using-lifo-method-for-cryptocurrency-or-even-stock-cost-basis/00/1433542
class AccountingMethod(AbstractSpecificId):

    def _seek_non_exhausted_acquired_lot_before_index(self, acquired_lot_list: List[InTransaction], last_valid_index: int) -> Optional[AcquiredLotAndAmount]:
        # This loop causes O(n^2) complexity, where n is the number of acquired lots. As a potential optimization we can consider removing
        # exhausted lots from the list.
        selected_acquired_lot_amount: RP2Decimal = ZERO
        selected_acquired_lot: Optional[InTransaction] = None
        for index in range(last_valid_index, -1, -1):
            acquired_lot_amount: RP2Decimal = ZERO
            acquired_lot: InTransaction = acquired_lot_list[index]

            if not self._has_partial_amount(acquired_lot):
                acquired_lot_amount = acquired_lot.crypto_in
            elif self._get_partial_amount(acquired_lot) > ZERO:
                acquired_lot_amount = self._get_partial_amount(acquired_lot)
            else:
                # The acquired lot has zero partial amount
                continue

            if selected_acquired_lot is None or selected_acquired_lot.timestamp > acquired_lot.timestamp:
                selected_acquired_lot_amount = acquired_lot_amount
                selected_acquired_lot = acquired_lot
                break

        if selected_acquired_lot_amount > ZERO and selected_acquired_lot:
            self._clear_partial_amount(selected_acquired_lot)
            return AcquiredLotAndAmount(acquired_lot=selected_acquired_lot, amount=selected_acquired_lot_amount)
        return None

    def validate_acquired_lot_ancestor_timestamp(self, acquired_lot: InTransaction, acquired_lot_parent: InTransaction) -> bool:
        # In LIFO the acquired_lot chain can have non-monotonic timestamps, so no validation is possible. Returning True means the validation never fails.
        return True

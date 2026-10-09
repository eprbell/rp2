# Copyright 2025 eprbell
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

from rp2.abstract_accounting_method import (
    AbstractFeatureBasedAccountingMethod,
    AcquiredLotSortKey,
)
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import RP2Decimal


# FIFO variant used only in per-wallet application. The chronological FIFO plugin orders lots by their position in the lot list,
# which in a wallet is the order of arrival: a lot transferred into a wallet would then be treated as newer than the lots already
# there, even when it was acquired earlier. Treas. Reg. §1.1012-1(j) orders units "from the earliest date on which units ... were
# acquired by the taxpayer" and adds that "the date any units were transferred into the taxpayer's wallet is disregarded" ((j)(1) and
# (j)(3)(i)), so this variant orders lots by cost_basis_timestamp (the original acquisition date, preserved across transfers). Ties
# are broken by arrival timestamp in the wallet, then by row, so that the order is deterministic.
class AcquisitionDateFifo(AbstractFeatureBasedAccountingMethod):
    def sort_key(self, lot: InTransaction) -> AcquiredLotSortKey:
        # The first field of the key is the primary sort criterion (spot price for HIFO/LOFO): here it's the acquisition timestamp. RP2Decimal
        # doesn't accept floats (to avoid precision loss in tax math), so the timestamp goes through its exact repr().
        return AcquiredLotSortKey(RP2Decimal(repr(lot.cost_basis_timestamp.timestamp())), lot.timestamp.timestamp(), lot.row)

    @property
    def name(self) -> str:
        return "fifo"

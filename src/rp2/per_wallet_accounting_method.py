# Copyright 2024 eprbell
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
    AbstractAccountingMethod,
    AbstractChronologicalAccountingMethod,
    AbstractFeatureBasedAccountingMethod,
    AcquiredLotCandidatesOrder,
)
from rp2.acquisition_date_fifo import AcquisitionDateFifo
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.rp2_error import RP2TypeError


# The accounting method that per-wallet application uses for a configured (user-facing) one. Both users of per-wallet lot ordering call it:
# the transfer analyzer (transfers and disposals after the switch) and the unused basis allocator (the order of the unused lots at the switch).
# Chronological methods select lots by their position in the lot list. In a wallet that's the order of arrival, not of acquisition: a lot
# transferred into a wallet would count as newer than the lots already there, even if it was acquired earlier. So they are replaced by
# feature-based equivalents that sort lots by their original acquisition date (cost_basis_timestamp). Example: FIFO in a wallet that received
# a coin bought in 2023 after buying one in 2024 sells the 2023 coin first. Feature-based methods (e.g. HIFO, LOFO and the LIFO plugin)
# already sort lots by a feature of the lot, so they are used as they are.
def get_per_wallet_accounting_method(accounting_method: AbstractAccountingMethod) -> AbstractFeatureBasedAccountingMethod:
    if isinstance(accounting_method, AbstractFeatureBasedAccountingMethod):
        return accounting_method
    if isinstance(accounting_method, AbstractChronologicalAccountingMethod):
        if accounting_method.lot_candidates_order() == AcquiredLotCandidatesOrder.OLDER_TO_NEWER:
            return AcquisitionDateFifo()
        return AccountingMethodLIFO()
    raise RP2TypeError(f"Unsupported accounting method for per-wallet application: {accounting_method}")

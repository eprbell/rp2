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

from rp2.abstract_accounting_method import (
    AbstractChronologicalAccountingMethod,
    AcquiredLotCandidatesOrder,
)


# FIFO (First In, First Out) plugin. See https://www.investopedia.com/terms/l/fifo.asp. This plugin uses universal application, not per-wallet application:
# this means there is one queue for each coin across every wallet and exchange and the accounting method is applied to each such queue.
# More on this at https://www.forbes.com/sites/shehanchandrasekera/2020/09/17/what-crypto-taxpayers-need-to-know-about-fifo-lifo-hifo-specific-id/
class AccountingMethod(AbstractChronologicalAccountingMethod):

    def lot_candidates_order(self) -> AcquiredLotCandidatesOrder:
        return AcquiredLotCandidatesOrder.OLDER_TO_NEWER

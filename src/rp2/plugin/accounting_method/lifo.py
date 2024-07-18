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
    AbstractFeatureBasedAccountingMethod,
    AcquiredLotSortKey,
)
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO


# LIFO (Last In, First Out) plugin. See https://www.investopedia.com/terms/l/lifo.asp.
# Note that under LIFO the date acquired must still be before or on the date sold: for details see
# https://ttlc.intuit.com/community/investments-and-rental-properties/discussion/using-lifo-method-for-cryptocurrency-or-even-stock-cost-basis/00/1433542
class AccountingMethod(AbstractFeatureBasedAccountingMethod):
    def sort_key(self, lot: InTransaction) -> AcquiredLotSortKey:
        return AcquiredLotSortKey(ZERO, -lot.timestamp.timestamp(), -lot.row)

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

from rp2.abstract_accounting_method import (
    AbstractFeatureBasedAccountingMethod,
    AcquiredLotSortKey,
)
from rp2.in_transaction import InTransaction


# HIFO (Highest In, First Out) plugin. See https://www.investopedia.com/terms/h/hifo.asp.
class AccountingMethod(AbstractFeatureBasedAccountingMethod):
    def sort_key(self, lot: InTransaction) -> AcquiredLotSortKey:
        return AcquiredLotSortKey(-lot.spot_price, lot.timestamp.timestamp(), lot.row)

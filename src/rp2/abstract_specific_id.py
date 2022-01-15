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


from typing import Iterator, Optional

from rp2.abstract_accounting_method import (
    AbstractAccountingMethod,
    TaxableEventAndFromLot,
)
from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import RP2Decimal


class AbstractSpecificId(AbstractAccountingMethod):
    def initialize(self, taxable_event_iterator: Iterator[AbstractTransaction], from_lot_iterator: Iterator[InTransaction]) -> None:
        raise NotImplementedError("Abstract function")

    def get_next_taxable_event_and_amount(
        self, taxable_event: Optional[AbstractTransaction], from_lot: Optional[InTransaction], taxable_event_amount: RP2Decimal, from_lot_amount: RP2Decimal
    ) -> TaxableEventAndFromLot:
        raise NotImplementedError("Abstract function")

    def get_from_lot_for_taxable_event(
        self, taxable_event: AbstractTransaction, from_lot: Optional[InTransaction], taxable_event_amount: RP2Decimal, from_lot_amount: RP2Decimal
    ) -> TaxableEventAndFromLot:
        raise NotImplementedError("Abstract function")

    def validate_from_lot_ancestor_timestamp(self, from_lot: InTransaction, from_lot_parent: InTransaction) -> bool:
        raise NotImplementedError("Abstract function")

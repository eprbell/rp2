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
    DisposedOfLotsExhaustedException,
    TaxableEventAndDisposedOfLot,
    TaxableEventsExhaustedException,
)
from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import RP2Decimal


# FIFO accounting method. See https://www.investopedia.com/terms/f/fifo.asp.
class AccountingMethod(AbstractAccountingMethod):

    __taxable_event_iterator: Iterator[AbstractTransaction]
    __disposed_of_lot_iterator: Iterator[InTransaction]

    # Iterators yield transactions in ascending chronological order
    def initialize(self, taxable_event_iterator: Iterator[AbstractTransaction], disposed_of_lot_iterator: Iterator[InTransaction]) -> None:
        self.__taxable_event_iterator = taxable_event_iterator
        self.__disposed_of_lot_iterator = disposed_of_lot_iterator

    def get_next_taxable_event_and_amount(
        self,
        taxable_event: Optional[AbstractTransaction],
        disposed_of_lot: Optional[InTransaction],
        taxable_event_amount: RP2Decimal,
        disposed_of_lot_amount: RP2Decimal,
    ) -> TaxableEventAndDisposedOfLot:
        try:
            new_taxable_event: AbstractTransaction = next(self.__taxable_event_iterator)
        except StopIteration:
            raise TaxableEventsExhaustedException() from None
        return TaxableEventAndDisposedOfLot(
            taxable_event=new_taxable_event,
            disposed_of_lot=disposed_of_lot,
            taxable_event_amount=new_taxable_event.crypto_taxable_amount,
            disposed_of_lot_amount=disposed_of_lot_amount - taxable_event_amount,
        )

    def get_disposed_of_lot_for_taxable_event(
        self, taxable_event: AbstractTransaction, disposed_of_lot: Optional[InTransaction], taxable_event_amount: RP2Decimal, disposed_of_lot_amount: RP2Decimal
    ) -> TaxableEventAndDisposedOfLot:
        try:
            new_disposed_of_lot: InTransaction = next(self.__disposed_of_lot_iterator)
        except StopIteration:
            raise DisposedOfLotsExhaustedException() from None
        return TaxableEventAndDisposedOfLot(
            taxable_event=taxable_event,
            disposed_of_lot=new_disposed_of_lot,
            taxable_event_amount=taxable_event_amount - disposed_of_lot_amount,
            disposed_of_lot_amount=new_disposed_of_lot.crypto_in,
        )

    def validate_disposed_of_lot_ancestor_timestamp(self, disposed_of_lot: InTransaction, disposed_of_lot_parent: InTransaction) -> bool:
        return disposed_of_lot.timestamp >= disposed_of_lot_parent.timestamp

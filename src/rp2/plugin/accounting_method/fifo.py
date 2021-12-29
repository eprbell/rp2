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

from typing import Iterable, Iterator, cast

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import MAX_YEAR, Configuration
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2ValueError
from rp2.transaction_set import TransactionSet


# FIFO accounting method
class AccountingMethod(AbstractAccountingMethod):
    def map_in_to_out_lots(
        self, configuration: Configuration, asset: str, from_lot_set: TransactionSet, unfiltered_taxable_event_set: TransactionSet
    ) -> GainLossSet:

        gain_loss_set: GainLossSet = GainLossSet(configuration, asset, 0, MAX_YEAR)

        taxable_event_iterator: Iterator[AbstractTransaction] = iter(cast(Iterable[AbstractTransaction], unfiltered_taxable_event_set))
        from_lot_iterator: Iterator[InTransaction] = iter(cast(Iterable[InTransaction], from_lot_set))

        try:
            gain_loss: GainLoss
            taxable_event: AbstractTransaction = next(taxable_event_iterator)
            taxable_event_amount: RP2Decimal = taxable_event.crypto_taxable_amount
            from_lot: InTransaction = next(from_lot_iterator)
            from_lot_amount: RP2Decimal = from_lot.crypto_in

            while True:
                if taxable_event.transaction_type.is_earn_type():
                    # Handle earn-typed transactions first: they have no from-lot
                    gain_loss = GainLoss(configuration, taxable_event_amount, taxable_event, None)
                    gain_loss_set.add_entry(gain_loss)
                    taxable_event = next(taxable_event_iterator)
                    taxable_event_amount = taxable_event.crypto_taxable_amount
                    continue

                if taxable_event_amount == from_lot_amount:
                    gain_loss = GainLoss(configuration, taxable_event_amount, taxable_event, from_lot)
                    gain_loss_set.add_entry(gain_loss)
                    taxable_event = next(taxable_event_iterator)
                    taxable_event_amount = taxable_event.crypto_taxable_amount
                    from_lot = next(from_lot_iterator)
                    from_lot_amount = from_lot.crypto_in
                elif taxable_event_amount < from_lot_amount:
                    gain_loss = GainLoss(configuration, taxable_event_amount, taxable_event, from_lot)
                    gain_loss_set.add_entry(gain_loss)
                    from_lot_amount = from_lot_amount - taxable_event_amount
                    taxable_event = next(taxable_event_iterator)
                    taxable_event_amount = taxable_event.crypto_taxable_amount
                else:  # taxable_amount > from_lot_amount
                    gain_loss = GainLoss(configuration, from_lot_amount, taxable_event, from_lot)
                    gain_loss_set.add_entry(gain_loss)
                    taxable_event_amount = taxable_event_amount - from_lot_amount
                    from_lot = next(from_lot_iterator)
                    from_lot_amount = from_lot.crypto_in
        except StopIteration as exception:
            if cast(Iterator[InTransaction], exception.value) == from_lot_iterator:
                raise RP2ValueError("Total in-transaction value < total taxable entries") from None

        return gain_loss_set

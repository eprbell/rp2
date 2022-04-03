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

from typing import Iterable, Iterator, Optional, cast

from rp2.abstract_accounting_method import (
    AbstractAccountingMethod,
    AcquiredLotsExhaustedException,
    TaxableEventAndAcquiredLot,
    TaxableEventsExhaustedException,
)
from rp2.abstract_entry import AbstractEntry
from rp2.abstract_transaction import AbstractTransaction
from rp2.computed_data import ComputedData
from rp2.configuration import MAX_DATE, MIN_DATE, Configuration
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.logger import LOGGER
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2ValueError
from rp2.transaction_set import TransactionSet


def compute_tax(configuration: Configuration, accounting_method: AbstractAccountingMethod, input_data: InputData) -> ComputedData:
    Configuration.type_check("configuration", configuration)
    AbstractAccountingMethod.type_check("accounting_method", accounting_method)
    InputData.type_check("input_data", input_data)

    unfiltered_taxable_event_set: TransactionSet = _create_unfiltered_taxable_event_set(configuration, input_data)
    LOGGER.debug("%s: Created taxable event set", input_data.asset)
    unfiltered_gain_loss_set: GainLossSet = _create_unfiltered_gain_and_loss_set(configuration, accounting_method, input_data, unfiltered_taxable_event_set)
    LOGGER.debug("%s: Created gain-loss set", input_data.asset)

    return ComputedData(
        input_data.asset,
        unfiltered_taxable_event_set,
        unfiltered_gain_loss_set,
        input_data,
        configuration.from_date,
        configuration.to_date,
    )


def _create_unfiltered_taxable_event_set(configuration: Configuration, input_data: InputData) -> TransactionSet:
    transaction_set: TransactionSet
    entry: AbstractEntry
    transaction: AbstractTransaction
    taxable_event_set: TransactionSet = TransactionSet(configuration, "MIXED", input_data.asset, MIN_DATE, MAX_DATE)
    for transaction_set in [
        input_data.unfiltered_in_transaction_set,
        input_data.unfiltered_out_transaction_set,
        input_data.unfiltered_intra_transaction_set,
    ]:
        for entry in transaction_set:
            transaction = cast(AbstractTransaction, entry)
            if transaction.is_taxable():
                taxable_event_set.add_entry(transaction)

    return taxable_event_set


def _get_next_taxable_event_and_acquired_lot(
    accounting_method: AbstractAccountingMethod,
    taxable_event: Optional[AbstractTransaction],
    acquired_lot: Optional[InTransaction],
    taxable_event_amount: RP2Decimal,
    acquired_lot_amount: RP2Decimal,
) -> TaxableEventAndAcquiredLot:
    new_taxable_event: AbstractTransaction
    new_acquired_lot: Optional[InTransaction]
    new_taxable_event_amount: RP2Decimal
    new_acquired_lot_amount: RP2Decimal
    (new_taxable_event, new_acquired_lot, new_taxable_event_amount, new_acquired_lot_amount) = accounting_method.get_next_taxable_event_and_amount(
        taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount
    )
    if acquired_lot == new_acquired_lot:
        (_, new_acquired_lot, _, new_acquired_lot_amount) = accounting_method.get_acquired_lot_for_taxable_event(
            new_taxable_event, new_acquired_lot, new_taxable_event_amount, new_acquired_lot_amount
        )
    return TaxableEventAndAcquiredLot(new_taxable_event, new_acquired_lot, new_taxable_event_amount, new_acquired_lot_amount)


def _create_unfiltered_gain_and_loss_set(
    configuration: Configuration, accounting_method: AbstractAccountingMethod, input_data: InputData, unfiltered_taxable_event_set: TransactionSet
) -> GainLossSet:
    gain_loss_set: GainLossSet = GainLossSet(configuration, accounting_method, input_data.asset, MIN_DATE, MAX_DATE)
    # Create a fresh instance of accounting method
    method: AbstractAccountingMethod = accounting_method.__class__()
    taxable_event_iterator: Iterator[AbstractTransaction] = iter(cast(Iterable[AbstractTransaction], unfiltered_taxable_event_set))
    acquired_lot_iterator: Iterator[InTransaction] = iter(cast(Iterable[InTransaction], input_data.unfiltered_in_transaction_set))

    method.initialize(taxable_event_iterator, acquired_lot_iterator)

    try:
        gain_loss: GainLoss
        taxable_event: AbstractTransaction
        acquired_lot: Optional[InTransaction]
        taxable_event_amount: RP2Decimal
        acquired_lot_amount: RP2Decimal

        # Retrieve first taxable event and acquired lot
        (taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount) = _get_next_taxable_event_and_acquired_lot(method, None, None, ZERO, ZERO)

        while taxable_event:
            # Type check values returned by accounting method plugin
            AbstractTransaction.type_check("taxable_event", taxable_event)
            if acquired_lot is None:
                # There must always be at least one acquired_lot
                raise Exception("Parameter 'acquired_lot' is None")
            InTransaction.type_check("acquired_lot", acquired_lot)
            Configuration.type_check_positive_decimal("taxable_event_amount", taxable_event_amount)
            Configuration.type_check_positive_decimal("acquired_lot_amount", acquired_lot_amount)

            if taxable_event.transaction_type.is_earn_type():
                # Handle earn-typed transactions first: they have no acquired-lot
                gain_loss = GainLoss(configuration, method, taxable_event_amount, taxable_event, None)
                gain_loss_set.add_entry(gain_loss)
                (taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount) = method.get_next_taxable_event_and_amount(
                    taxable_event, acquired_lot, ZERO, acquired_lot_amount
                )
                continue
            if taxable_event_amount == acquired_lot_amount:
                gain_loss = GainLoss(configuration, method, taxable_event_amount, taxable_event, acquired_lot)
                gain_loss_set.add_entry(gain_loss)
                (taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount) = _get_next_taxable_event_and_acquired_lot(
                    method, taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount
                )
            elif taxable_event_amount < acquired_lot_amount:
                gain_loss = GainLoss(configuration, method, taxable_event_amount, taxable_event, acquired_lot)
                gain_loss_set.add_entry(gain_loss)
                (taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount) = method.get_next_taxable_event_and_amount(
                    taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount
                )
            else:  # taxable_amount > acquired_lot_amount
                gain_loss = GainLoss(configuration, method, acquired_lot_amount, taxable_event, acquired_lot)
                gain_loss_set.add_entry(gain_loss)
                (taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount) = method.get_acquired_lot_for_taxable_event(
                    taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount
                )

    except AcquiredLotsExhaustedException:
        raise RP2ValueError("Total in-transaction crypto value < total taxable crypto value") from None
    except TaxableEventsExhaustedException:
        pass

    return gain_loss_set

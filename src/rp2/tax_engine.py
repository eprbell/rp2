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

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional, Set, cast

from rp2.abstract_accounting_method import (
    AbstractAccountingMethod,
    FromLotsExhaustedException,
    TaxableEventAndFromLot,
    TaxableEventsExhaustedException,
)
from rp2.abstract_entry import AbstractEntry
from rp2.abstract_transaction import AbstractTransaction
from rp2.computed_data import ComputedData, YearlyGainLoss
from rp2.configuration import MAX_YEAR, Configuration
from rp2.entry_types import TransactionType
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.logger import LOGGER
from rp2.out_transaction import OutTransaction
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
    unfiltered_yearly_gain_loss_list: List[YearlyGainLoss] = _create_unfiltered_yearly_gain_loss_list(accounting_method, input_data, unfiltered_gain_loss_set)
    LOGGER.debug("%s: Created yearly gain-loss list", input_data.asset)

    return ComputedData(
        input_data.asset,
        unfiltered_taxable_event_set,
        unfiltered_gain_loss_set,
        unfiltered_yearly_gain_loss_list,
        input_data,
        configuration.from_year,
        configuration.to_year,
    )


def _create_unfiltered_taxable_event_set(configuration: Configuration, input_data: InputData) -> TransactionSet:
    transaction_set: TransactionSet
    entry: AbstractEntry
    transaction: AbstractTransaction
    taxable_event_set: TransactionSet = TransactionSet(configuration, "MIXED", input_data.asset, 0, MAX_YEAR)
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


def _get_next_taxable_event_and_from_lot(
    accounting_method: AbstractAccountingMethod,
    taxable_event: Optional[AbstractTransaction],
    from_lot: Optional[InTransaction],
    taxable_event_amount: RP2Decimal,
    from_lot_amount: RP2Decimal,
) -> TaxableEventAndFromLot:
    new_taxable_event: AbstractTransaction
    new_from_lot: Optional[InTransaction]
    new_taxable_event_amount: RP2Decimal
    new_from_lot_amount: RP2Decimal
    (new_taxable_event, new_from_lot, new_taxable_event_amount, new_from_lot_amount) = accounting_method.get_next_taxable_event_and_amount(
        taxable_event, from_lot, taxable_event_amount, from_lot_amount
    )
    if from_lot == new_from_lot:
        (_, new_from_lot, _, new_from_lot_amount) = accounting_method.get_from_lot_for_taxable_event(
            new_taxable_event, new_from_lot, new_taxable_event_amount, new_from_lot_amount
        )
    return TaxableEventAndFromLot(new_taxable_event, new_from_lot, new_taxable_event_amount, new_from_lot_amount)


def _create_unfiltered_gain_and_loss_set(
    configuration: Configuration, accounting_method: AbstractAccountingMethod, input_data: InputData, unfiltered_taxable_event_set: TransactionSet
) -> GainLossSet:
    gain_loss_set: GainLossSet = GainLossSet(configuration, accounting_method, input_data.asset, 0, MAX_YEAR)
    # Create a fresh instance of accounting method
    method: AbstractAccountingMethod = accounting_method.__class__()
    taxable_event_iterator: Iterator[AbstractTransaction] = iter(cast(Iterable[AbstractTransaction], unfiltered_taxable_event_set))
    from_lot_iterator: Iterator[InTransaction] = iter(cast(Iterable[InTransaction], input_data.unfiltered_in_transaction_set))

    method.initialize(taxable_event_iterator, from_lot_iterator)

    try:
        gain_loss: GainLoss
        taxable_event: AbstractTransaction
        from_lot: Optional[InTransaction]
        taxable_event_amount: RP2Decimal
        from_lot_amount: RP2Decimal

        # Retrieve first taxable event and from lot
        (taxable_event, from_lot, taxable_event_amount, from_lot_amount) = _get_next_taxable_event_and_from_lot(method, None, None, ZERO, ZERO)

        while taxable_event:
            # Type check values returned by accounting method plugin
            AbstractTransaction.type_check("taxable_event", taxable_event)
            if from_lot is None:
                # There must always be at least one from_lot
                raise Exception("Parameter 'from_lot' is None")
            InTransaction.type_check("from_lot", from_lot)
            Configuration.type_check_positive_decimal("taxable_event_amount", taxable_event_amount)
            Configuration.type_check_positive_decimal("from_lot_amount", from_lot_amount)

            if taxable_event.transaction_type.is_earn_type():
                # Handle earn-typed transactions first: they have no from-lot
                gain_loss = GainLoss(configuration, method, taxable_event_amount, taxable_event, None)
                gain_loss_set.add_entry(gain_loss)
                (taxable_event, from_lot, taxable_event_amount, from_lot_amount) = method.get_next_taxable_event_and_amount(
                    taxable_event, from_lot, ZERO, from_lot_amount
                )
                continue
            if taxable_event_amount == from_lot_amount:
                gain_loss = GainLoss(configuration, method, taxable_event_amount, taxable_event, from_lot)
                gain_loss_set.add_entry(gain_loss)
                (taxable_event, from_lot, taxable_event_amount, from_lot_amount) = _get_next_taxable_event_and_from_lot(
                    method, taxable_event, from_lot, taxable_event_amount, from_lot_amount
                )
            elif taxable_event_amount < from_lot_amount:
                gain_loss = GainLoss(configuration, method, taxable_event_amount, taxable_event, from_lot)
                gain_loss_set.add_entry(gain_loss)
                (taxable_event, from_lot, taxable_event_amount, from_lot_amount) = method.get_next_taxable_event_and_amount(
                    taxable_event, from_lot, taxable_event_amount, from_lot_amount
                )
            else:  # taxable_amount > from_lot_amount
                gain_loss = GainLoss(configuration, method, from_lot_amount, taxable_event, from_lot)
                gain_loss_set.add_entry(gain_loss)
                (taxable_event, from_lot, taxable_event_amount, from_lot_amount) = method.get_from_lot_for_taxable_event(
                    taxable_event, from_lot, taxable_event_amount, from_lot_amount
                )

    except FromLotsExhaustedException:
        raise RP2ValueError("Total in-transaction value < total taxable entries") from None
    except TaxableEventsExhaustedException:
        pass

    return gain_loss_set


@dataclass(frozen=True, eq=True)
class _YearlyGainLossId:
    year: int
    asset: str
    transaction_type: TransactionType
    is_long_term_capital_gains: bool


# Frozen and eq are not set because we don't need to hash instances and we need to modify fields (see _create_yearly_gain_loss_list)
@dataclass(frozen=True, eq=True)
class _YearlyGainLossAmounts:
    crypto_amount: RP2Decimal
    fiat_amount: RP2Decimal
    fiat_cost_basis: RP2Decimal
    fiat_gain_loss: RP2Decimal


def _create_unfiltered_yearly_gain_loss_list(
    accounting_method: AbstractAccountingMethod, input_data: InputData, unfiltered_gain_loss_set: GainLossSet
) -> List[YearlyGainLoss]:
    summaries: Dict[_YearlyGainLossId, _YearlyGainLossAmounts] = {}
    entry: AbstractEntry
    key: _YearlyGainLossId
    value: _YearlyGainLossAmounts
    for entry in unfiltered_gain_loss_set:
        gain_loss: GainLoss = cast(GainLoss, entry)
        key = _YearlyGainLossId(
            gain_loss.taxable_event.timestamp.year,
            gain_loss.asset,
            gain_loss.taxable_event.transaction_type,
            gain_loss.is_long_term_capital_gains(),
        )
        value = summaries.setdefault(key, _YearlyGainLossAmounts(ZERO, ZERO, ZERO, ZERO))
        crypto_amount: RP2Decimal = value.crypto_amount + gain_loss.crypto_amount
        fiat_amount: RP2Decimal = value.fiat_amount + gain_loss.taxable_event_fiat_amount_with_fee_fraction
        fiat_cost_basis: RP2Decimal = value.fiat_cost_basis + gain_loss.fiat_cost_basis
        fiat_gain_loss: RP2Decimal = value.fiat_gain_loss + gain_loss.fiat_gain
        summaries[key] = _YearlyGainLossAmounts(
            crypto_amount=crypto_amount, fiat_amount=fiat_amount, fiat_cost_basis=fiat_cost_basis, fiat_gain_loss=fiat_gain_loss
        )

    yearly_gain_loss_set: Set[YearlyGainLoss] = set()
    crypto_taxable_amount_total: RP2Decimal = ZERO
    fiat_taxable_amount_total: RP2Decimal = ZERO
    cost_basis_total: RP2Decimal = ZERO
    gain_loss_total: RP2Decimal = ZERO
    for (key, value) in summaries.items():
        yearly_gain_loss: YearlyGainLoss = YearlyGainLoss(
            year=key.year,
            asset=key.asset,
            transaction_type=key.transaction_type,
            is_long_term_capital_gains=key.is_long_term_capital_gains,
            crypto_amount=value.crypto_amount,
            fiat_amount=value.fiat_amount,
            fiat_cost_basis=value.fiat_cost_basis,
            fiat_gain_loss=value.fiat_gain_loss,
        )
        yearly_gain_loss_set.add(yearly_gain_loss)
        crypto_taxable_amount_total += yearly_gain_loss.crypto_amount
        fiat_taxable_amount_total += yearly_gain_loss.fiat_amount
        cost_basis_total += yearly_gain_loss.fiat_cost_basis
        gain_loss_total += yearly_gain_loss.fiat_gain_loss

    # This code double-checks the results, assuming LIFO accounting: it's a vestige of the past, when there was
    # no plugin architecture for accounting methods (there was only built-in LIFO). The new accounting method
    # plugin architecture makes the _verify_computation function hacky: it will be deleted at some point in the future.
    if repr(accounting_method) == "fifo":
        _verify_computation(input_data, crypto_taxable_amount_total, fiat_taxable_amount_total, cost_basis_total, gain_loss_total)

    return list(sorted(yearly_gain_loss_set, key=_yearly_gain_loss_sort_criteria, reverse=True))


def _yearly_gain_loss_sort_criteria(yearly_gain_loss: YearlyGainLoss) -> str:
    return (
        f"{yearly_gain_loss.asset}"
        f" {yearly_gain_loss.year}"
        f" {'LONG' if yearly_gain_loss.is_long_term_capital_gains else 'SHORT'}"
        f" {yearly_gain_loss.transaction_type.value}"
    )


# Internal sanity check: ensure the sum total of gains and losses from taxable flows matches the one from taxable events and InTransactions
def _verify_computation(
    input_data: InputData,
    crypto_taxable_amount_total: RP2Decimal,
    fiat_taxable_amount_total: RP2Decimal,
    cost_basis_total: RP2Decimal,
    gain_loss_total: RP2Decimal,
) -> None:
    fiat_taxable_amount_total_verify: RP2Decimal = ZERO
    crypto_earned_amount_total_verify: RP2Decimal = ZERO
    crypto_sold_amount_total_verify: RP2Decimal = ZERO
    crypto_taxable_amount_total_verify: RP2Decimal = ZERO
    cost_basis_total_verify: RP2Decimal = ZERO
    crypto_in_amount_total: RP2Decimal = ZERO
    gain_loss_total_verify: RP2Decimal = ZERO

    # Compute fiat and crypto total taxable amount
    for entry in input_data.unfiltered_in_transaction_set:
        in_transaction: InTransaction = cast(InTransaction, entry)
        fiat_taxable_amount_total_verify += in_transaction.fiat_taxable_amount
        crypto_earned_amount_total_verify += in_transaction.crypto_taxable_amount
    for entry in input_data.unfiltered_out_transaction_set:
        out_transaction: OutTransaction = cast(OutTransaction, entry)
        fiat_taxable_amount_total_verify += out_transaction.fiat_taxable_amount
        crypto_sold_amount_total_verify += out_transaction.crypto_taxable_amount
    for entry in input_data.unfiltered_intra_transaction_set:
        intra_transaction: IntraTransaction = cast(IntraTransaction, entry)
        fiat_taxable_amount_total_verify += intra_transaction.fiat_taxable_amount
        crypto_sold_amount_total_verify += intra_transaction.crypto_taxable_amount

    crypto_taxable_amount_total_verify = crypto_sold_amount_total_verify + crypto_earned_amount_total_verify

    # Compute cost basis
    for entry in input_data.unfiltered_in_transaction_set:
        in_transaction = cast(InTransaction, entry)
        if crypto_in_amount_total + in_transaction.crypto_in > crypto_sold_amount_total_verify:
            # End of loop: last in transaction covering the amount sold needs to be fractioned
            crypto_in_amount: RP2Decimal = crypto_sold_amount_total_verify - crypto_in_amount_total
            crypto_in_amount_total += crypto_in_amount
            cost_basis_total_verify += (crypto_in_amount / in_transaction.crypto_in) * in_transaction.fiat_in_with_fee
            break
        crypto_in_amount_total += in_transaction.crypto_in
        cost_basis_total_verify += in_transaction.fiat_in_with_fee

    gain_loss_total_verify = fiat_taxable_amount_total_verify - cost_basis_total_verify

    if crypto_taxable_amount_total != crypto_taxable_amount_total_verify:
        raise Exception(
            f"{input_data.asset}: total crypto taxable amount incongruence detected: " f"{crypto_taxable_amount_total} != {crypto_taxable_amount_total_verify}",
        )
    if fiat_taxable_amount_total != fiat_taxable_amount_total_verify:
        raise Exception(
            f"{input_data.asset}: total fiat taxable amount incongruence detected: " f"{fiat_taxable_amount_total} != {fiat_taxable_amount_total_verify}",
        )
    if cost_basis_total != cost_basis_total_verify:
        raise Exception(f"{input_data.asset}: cost basis incongruence detected: {cost_basis_total} != {cost_basis_total_verify}")
    if gain_loss_total != gain_loss_total_verify:
        raise Exception(f"{input_data.asset}: total gain/loss incongruence detected: {gain_loss_total} != {gain_loss_total_verify}")

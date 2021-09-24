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
from typing import Dict, Iterable, Iterator, List, Set, cast

from rp2.abstract_entry import AbstractEntry
from rp2.abstract_transaction import AbstractTransaction
from rp2.computed_data import ComputedData, YearlyGainLoss
from rp2.configuration import Configuration
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


def compute_tax(configuration: Configuration, input_data: InputData) -> ComputedData:
    Configuration.type_check("configuration", configuration)
    InputData.type_check("input_data", input_data)

    taxable_event_set: TransactionSet = _create_taxable_event_set(configuration, input_data)
    LOGGER.debug("%s: Created taxable event set", input_data.asset)
    gain_loss_set: GainLossSet = _create_gain_and_loss_set(configuration, input_data, taxable_event_set)
    LOGGER.debug("%s: Created gain-loss set", input_data.asset)
    yearly_gain_loss_list: List[YearlyGainLoss] = _create_yearly_gain_loss_list(input_data, gain_loss_set)
    LOGGER.debug("%s: Created yearly gain-loss list", input_data.asset)

    return ComputedData(
        input_data.asset,
        taxable_event_set,
        gain_loss_set,
        yearly_gain_loss_list,
        input_data,
        configuration.from_year,
        configuration.to_year,
    )


def _create_taxable_event_set(configuration: Configuration, input_data: InputData) -> TransactionSet:
    transaction_set: TransactionSet
    entry: AbstractEntry
    transaction: AbstractTransaction
    taxable_event_set: TransactionSet = TransactionSet(configuration, "MIXED", input_data.asset, configuration.from_year, configuration.to_year)
    for transaction_set in [
        input_data.in_transaction_set,
        input_data.out_transaction_set,
        input_data.intra_transaction_set,
    ]:
        for entry in transaction_set:
            transaction = cast(AbstractTransaction, entry)
            if transaction.is_taxable():
                taxable_event_set.add_entry(transaction)

    return taxable_event_set


def _create_gain_and_loss_set(configuration: Configuration, input_data: InputData, taxable_event_set: TransactionSet) -> GainLossSet:

    gain_loss_set: GainLossSet = GainLossSet(configuration, input_data.asset, from_year=configuration.from_year, to_year=configuration.to_year)

    taxable_event_iterator: Iterator[AbstractTransaction] = iter(cast(Iterable[AbstractTransaction], taxable_event_set))
    from_lot_iterator: Iterator[InTransaction] = iter(cast(Iterable[InTransaction], input_data.in_transaction_set))

    try:
        gain_loss: GainLoss
        taxable_event: AbstractTransaction = next(taxable_event_iterator)
        taxable_event_amount: RP2Decimal = taxable_event.crypto_taxable_amount
        from_lot: InTransaction = next(from_lot_iterator)
        from_lot_amount: RP2Decimal = from_lot.crypto_in

        while True:
            if taxable_event.transaction_type.is_earn_type():
                # Handle earn-typed transactions first
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
    usd_amount: RP2Decimal
    usd_cost_basis: RP2Decimal
    usd_gain_loss: RP2Decimal


def _create_yearly_gain_loss_list(input_data: InputData, gain_loss_set: GainLossSet) -> List[YearlyGainLoss]:
    summaries: Dict[_YearlyGainLossId, _YearlyGainLossAmounts] = {}
    entry: AbstractEntry
    key: _YearlyGainLossId
    value: _YearlyGainLossAmounts
    for entry in gain_loss_set:
        gain_loss: GainLoss = cast(GainLoss, entry)
        key = _YearlyGainLossId(
            gain_loss.taxable_event.timestamp.year,
            gain_loss.asset,
            gain_loss.taxable_event.transaction_type,
            gain_loss.is_long_term_capital_gains(),
        )
        value = summaries.setdefault(key, _YearlyGainLossAmounts(ZERO, ZERO, ZERO, ZERO))
        crypto_amount: RP2Decimal = value.crypto_amount + gain_loss.crypto_amount
        usd_amount: RP2Decimal = value.usd_amount + gain_loss.taxable_event_usd_amount_with_fee_fraction
        usd_cost_basis: RP2Decimal = value.usd_cost_basis + gain_loss.usd_cost_basis
        usd_gain_loss: RP2Decimal = value.usd_gain_loss + gain_loss.usd_gain
        summaries[key] = _YearlyGainLossAmounts(crypto_amount=crypto_amount, usd_amount=usd_amount, usd_cost_basis=usd_cost_basis, usd_gain_loss=usd_gain_loss)

    yearly_gain_loss_set: Set[YearlyGainLoss] = set()
    crypto_taxable_amount_total: RP2Decimal = ZERO
    usd_taxable_amount_total: RP2Decimal = ZERO
    cost_basis_total: RP2Decimal = ZERO
    gain_loss_total: RP2Decimal = ZERO
    for (key, value) in summaries.items():
        yearly_gain_loss: YearlyGainLoss = YearlyGainLoss(
            year=key.year,
            asset=key.asset,
            transaction_type=key.transaction_type,
            is_long_term_capital_gains=key.is_long_term_capital_gains,
            crypto_amount=value.crypto_amount,
            usd_amount=value.usd_amount,
            usd_cost_basis=value.usd_cost_basis,
            usd_gain_loss=value.usd_gain_loss,
        )
        yearly_gain_loss_set.add(yearly_gain_loss)
        crypto_taxable_amount_total += yearly_gain_loss.crypto_amount
        usd_taxable_amount_total += yearly_gain_loss.usd_amount
        cost_basis_total += yearly_gain_loss.usd_cost_basis
        gain_loss_total += yearly_gain_loss.usd_gain_loss

    _verify_computation(input_data, crypto_taxable_amount_total, usd_taxable_amount_total, cost_basis_total, gain_loss_total)

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
    usd_taxable_amount_total: RP2Decimal,
    cost_basis_total: RP2Decimal,
    gain_loss_total: RP2Decimal,
) -> None:
    usd_taxable_amount_total_verify: RP2Decimal = ZERO
    crypto_earned_amount_total_verify: RP2Decimal = ZERO
    crypto_sold_amount_total_verify: RP2Decimal = ZERO
    crypto_taxable_amount_total_verify: RP2Decimal = ZERO
    cost_basis_total_verify: RP2Decimal = ZERO
    crypto_in_amount_total: RP2Decimal = ZERO
    gain_loss_total_verify: RP2Decimal = ZERO

    # Compute USD and crypto total taxable amount
    for entry in input_data.in_transaction_set:
        in_transaction: InTransaction = cast(InTransaction, entry)
        usd_taxable_amount_total_verify += in_transaction.usd_taxable_amount
        crypto_earned_amount_total_verify += in_transaction.crypto_taxable_amount
    for entry in input_data.out_transaction_set:
        out_transaction: OutTransaction = cast(OutTransaction, entry)
        usd_taxable_amount_total_verify += out_transaction.usd_taxable_amount
        crypto_sold_amount_total_verify += out_transaction.crypto_taxable_amount
    for entry in input_data.intra_transaction_set:
        intra_transaction: IntraTransaction = cast(IntraTransaction, entry)
        usd_taxable_amount_total_verify += intra_transaction.usd_taxable_amount
        crypto_sold_amount_total_verify += intra_transaction.crypto_taxable_amount

    crypto_taxable_amount_total_verify = crypto_sold_amount_total_verify + crypto_earned_amount_total_verify

    # Compute cost basis
    for entry in input_data.in_transaction_set:
        in_transaction = cast(InTransaction, entry)
        if crypto_in_amount_total + in_transaction.crypto_in > crypto_sold_amount_total_verify:
            # End of loop: last in transaction covering the amount sold needs to be fractioned
            crypto_in_amount: RP2Decimal = crypto_sold_amount_total_verify - crypto_in_amount_total
            crypto_in_amount_total += crypto_in_amount
            cost_basis_total_verify += (crypto_in_amount / in_transaction.crypto_in) * in_transaction.usd_in_with_fee
            break
        crypto_in_amount_total += in_transaction.crypto_in
        cost_basis_total_verify += in_transaction.usd_in_with_fee

    gain_loss_total_verify = usd_taxable_amount_total_verify - cost_basis_total_verify

    if crypto_taxable_amount_total != crypto_taxable_amount_total_verify:
        raise Exception(
            f"{input_data.asset}: total crypto taxable amount incongruence detected: " f"{crypto_taxable_amount_total} != {crypto_taxable_amount_total_verify}",
        )
    if usd_taxable_amount_total != usd_taxable_amount_total_verify:
        raise Exception(
            f"{input_data.asset}: total usd taxable amount incongruence detected: " f"{usd_taxable_amount_total} != {usd_taxable_amount_total_verify}",
        )
    if cost_basis_total != cost_basis_total_verify:
        raise Exception(f"{input_data.asset}: cost basis incongruence detected: {cost_basis_total} != {cost_basis_total_verify}")
    if gain_loss_total != gain_loss_total_verify:
        raise Exception(f"{input_data.asset}: total gain/loss incongruence detected: {gain_loss_total} != {gain_loss_total_verify}")

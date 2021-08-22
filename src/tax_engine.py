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

from decimal import Decimal
from typing import Dict, Iterable, Iterator, List, Set, Tuple, cast

from abstract_entry import AbstractEntry
from abstract_transaction import AbstractTransaction
from balance import BalanceSet
from computed_data import ComputedData, YearlyGainLoss
from configuration import Configuration
from entry_types import TransactionType
from gain_loss import GainLoss
from gain_loss_set import GainLossSet
from in_transaction import InTransaction
from input_data import InputData
from intra_transaction import IntraTransaction
from logger import LOGGER
from out_transaction import OutTransaction
from rp2_decimal import ZERO
from rp2_error import RP2ValueError
from transaction_set import TransactionSet


def compute_tax(configuration: Configuration, input_data: InputData) -> ComputedData:
    Configuration.type_check("configuration", configuration)
    InputData.type_check("input_data", input_data)

    gain_loss_set: GainLossSet = GainLossSet(configuration, input_data.asset)
    taxable_event_set: TransactionSet = _create_taxable_event_set(configuration, input_data)
    _populate_gain_and_loss(configuration, input_data, taxable_event_set, gain_loss_set)

    balance_set: BalanceSet = BalanceSet(configuration, input_data)

    yearly_gain_loss_list: List[YearlyGainLoss] = _populate_yearly_gain_loss_list(input_data, gain_loss_set)

    crypto_in_running_sum: Decimal = ZERO
    usd_in_with_fee_running_sum: Decimal = ZERO
    for entry in input_data.in_transaction_set:
        transaction: InTransaction = cast(InTransaction, entry)
        crypto_in_running_sum += transaction.crypto_in
        usd_in_with_fee_running_sum += transaction.usd_in_with_fee
    price_per_unit: Decimal = usd_in_with_fee_running_sum / crypto_in_running_sum

    return ComputedData(
        input_data.asset,
        taxable_event_set,
        gain_loss_set,
        balance_set,
        yearly_gain_loss_list,
        price_per_unit,
        input_data,
    )


def _create_taxable_event_set(configuration: Configuration, input_data: InputData) -> TransactionSet:
    transaction_set: TransactionSet
    entry: AbstractEntry
    transaction: AbstractTransaction
    taxable_event_set: TransactionSet = TransactionSet(configuration, "MIXED", input_data.asset)
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


def _populate_gain_and_loss(configuration: Configuration, input_data: InputData, taxable_event_set: TransactionSet, gain_loss_set: GainLossSet) -> None:

    taxable_event_iterator: Iterator[AbstractTransaction] = iter(
        cast(Iterable[AbstractTransaction], taxable_event_set)
    )  # pylint disable=unsubscriptable-object
    from_lot_iterator: Iterator[InTransaction] = iter(cast(Iterable[InTransaction], input_data.in_transaction_set))  # pylint disable=E1136

    try:
        gain_loss: GainLoss
        taxable_event: AbstractTransaction = next(taxable_event_iterator)
        taxable_event_amount: Decimal = taxable_event.crypto_taxable_amount
        from_lot: InTransaction = next(from_lot_iterator)
        from_lot_amount: Decimal = from_lot.crypto_in

        while True:
            if taxable_event.transaction_type == TransactionType.EARN:
                gain_loss = GainLoss(
                    configuration,
                    taxable_event_amount,
                    taxable_event,
                    None,
                )
                gain_loss_set.add_entry(gain_loss)
                taxable_event = next(taxable_event_iterator)
                taxable_event_amount = taxable_event.crypto_taxable_amount
                continue

            if taxable_event_amount == from_lot_amount:
                gain_loss = GainLoss(
                    configuration,
                    taxable_event_amount,
                    taxable_event,
                    from_lot,
                )
                gain_loss_set.add_entry(gain_loss)
                taxable_event = next(taxable_event_iterator)
                taxable_event_amount = taxable_event.crypto_taxable_amount
                from_lot = next(from_lot_iterator)
                from_lot_amount = from_lot.crypto_in
            elif taxable_event_amount < from_lot_amount:
                gain_loss = GainLoss(
                    configuration,
                    taxable_event_amount,
                    taxable_event,
                    from_lot,
                )
                gain_loss_set.add_entry(gain_loss)
                from_lot_amount = from_lot_amount - taxable_event_amount
                taxable_event = next(taxable_event_iterator)
                taxable_event_amount = taxable_event.crypto_taxable_amount
            else:  # taxable_amount > from_lot_amount
                gain_loss = GainLoss(
                    configuration,
                    from_lot_amount,
                    taxable_event,
                    from_lot,
                )
                gain_loss_set.add_entry(gain_loss)
                taxable_event_amount = taxable_event_amount - from_lot_amount
                from_lot = next(from_lot_iterator)
                from_lot_amount = from_lot.crypto_in
    except StopIteration as exception:
        if cast(Iterator[InTransaction], exception.value) == from_lot_iterator:
            raise RP2ValueError("Total in-transaction value < total taxable entries") from None


def _populate_yearly_gain_loss_list(input_data: InputData, gain_loss_set: GainLossSet) -> List[YearlyGainLoss]:
    # TODO: use data structures instead of tuples
    summaries: Dict[Tuple[int, str, TransactionType, bool], Tuple[Decimal, Decimal, Decimal, Decimal]] = dict()
    entry: AbstractEntry
    key: Tuple[int, str, TransactionType, bool]  # year, asset, transaction_type, capitaly gains type
    for entry in gain_loss_set:
        gain_loss: GainLoss = cast(GainLoss, entry)
        crypto_amount: Decimal
        usd_amount: Decimal
        usd_cost_basis: Decimal
        usd_gain_loss: Decimal
        key = (
            gain_loss.taxable_event.timestamp.year,
            gain_loss.asset,
            gain_loss.taxable_event.transaction_type,
            gain_loss.is_long_term_capital_gains(),
        )
        (crypto_amount, usd_amount, usd_cost_basis, usd_gain_loss) = summaries.setdefault(key, (ZERO, ZERO, ZERO, ZERO))
        crypto_amount += gain_loss.crypto_amount
        usd_amount += gain_loss.taxable_event_usd_amount_with_fee_fraction
        usd_cost_basis += gain_loss.usd_cost_basis
        usd_gain_loss += gain_loss.usd_gain
        summaries[key] = (crypto_amount, usd_amount, usd_cost_basis, usd_gain_loss)

    yearly_gain_loss_set: Set[YearlyGainLoss] = set()
    value: Tuple[Decimal, Decimal, Decimal, Decimal]  # crypto_amount, usd_amount, usd_cost_basis, usd_gain_loss
    crypto_taxable_amount_total: Decimal = ZERO
    usd_taxable_amount_total: Decimal = ZERO
    cost_basis_total: Decimal = ZERO
    gain_loss_total: Decimal = ZERO
    for (key, value) in summaries.items():
        yearly_gain_loss: YearlyGainLoss = YearlyGainLoss(
            year=key[0],
            asset=key[1],
            transaction_type=key[2],
            is_long_term=key[3],
            crypto_amount=value[0],
            usd_amount=value[1],
            usd_cost_basis=value[2],
            usd_gain_loss=value[3],
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
        f" {'LONG' if yearly_gain_loss.is_long_term else 'SHORT'}"
        f" {yearly_gain_loss.transaction_type.value}"
    )


# Internal sanity check
def _verify_computation(
    input_data: InputData,
    crypto_taxable_amount_total: Decimal,
    usd_taxable_amount_total: Decimal,
    cost_basis_total: Decimal,
    gain_loss_total: Decimal,
) -> None:
    # Internal sanity check: ensure the sum total of gains and losses from taxable flows matches the one
    # from taxable events and InTransactions
    usd_taxable_amount_total_verify: Decimal = ZERO
    cost_basis_total_verify: Decimal = ZERO
    crypto_sold_amount_total_verify: Decimal = ZERO
    crypto_earned_amount_total_verify: Decimal = ZERO
    crypto_taxable_amount_total_verify: Decimal = ZERO
    gain_loss_total_verify: Decimal = ZERO
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
    crypto_in_amount_total: Decimal = ZERO
    for entry in input_data.in_transaction_set:
        in_transaction = cast(InTransaction, entry)
        if crypto_in_amount_total + in_transaction.crypto_in > crypto_sold_amount_total_verify:
            crypto_in_amount: Decimal = crypto_sold_amount_total_verify - crypto_in_amount_total
            crypto_in_amount_total += crypto_in_amount
            cost_basis_total_verify += (crypto_in_amount / in_transaction.crypto_in) * in_transaction.usd_in_with_fee
            break
        crypto_in_amount_total += in_transaction.crypto_in
        cost_basis_total_verify += in_transaction.usd_in_with_fee

    gain_loss_total_verify = usd_taxable_amount_total_verify - cost_basis_total_verify

    if crypto_taxable_amount_total != crypto_taxable_amount_total_verify:
        LOGGER.warning(
            "%s: total crypto taxable amount incongruence detected: %f != %f",
            input_data.asset,
            crypto_taxable_amount_total,
            crypto_taxable_amount_total_verify,
        )
    if usd_taxable_amount_total != usd_taxable_amount_total_verify:
        LOGGER.warning(
            "%s: total usd taxable amount incongruence detected: %f != %f",
            input_data.asset,
            usd_taxable_amount_total,
            usd_taxable_amount_total_verify,
        )
    if cost_basis_total != cost_basis_total_verify:
        LOGGER.warning(
            "%s: cost basis incongruence detected: %f != %f",
            input_data.asset,
            cost_basis_total,
            cost_basis_total_verify,
        )
    if gain_loss_total != gain_loss_total_verify:
        LOGGER.warning(
            "%s: total gain/loss incongruence detected: %f != %f",
            input_data.asset,
            gain_loss_total,
            gain_loss_total_verify,
        )

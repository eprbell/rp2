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

from datetime import datetime
from typing import Dict, Iterable, Iterator, List, NamedTuple, Optional, cast

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.abstract_country import AbstractCountry
from rp2.abstract_transaction import AbstractTransaction
from rp2.account import Account
from rp2.accounting_engine import (
    AccountingEngine,
    AcquiredLotsExhaustedException,
    TaxableEventAndAcquiredLot,
    TaxableEventsExhaustedException,
)
from rp2.application_policy import ApplicationMode, ApplicationPolicy
from rp2.balance import CRYPTO_BALANCE_DECIMAL_MASK
from rp2.computed_data import ComputedData
from rp2.configuration import MAX_DATE, MIN_DATE, Configuration
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.logger import LOGGER
from rp2.out_transaction import OutTransaction
from rp2.per_wallet_configuration import PerWalletConfiguration
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2ValueError
from rp2.transaction_set import TransactionSet
from rp2.transfer_analyzer import TransferAnalyzer
from rp2.unused_basis_allocator import UnusedBasisAllocator, UnusedLot
from rp2.wallet_lot import WalletLot


def compute_tax(configuration: Configuration, accounting_engine: AccountingEngine, input_data: InputData) -> ComputedData:
    Configuration.type_check("configuration", configuration)
    AccountingEngine.type_check("accounting_engine", accounting_engine)
    InputData.type_check("input_data", input_data)

    unfiltered_taxable_event_set: TransactionSet = input_data.create_unfiltered_taxable_event_set(configuration)
    LOGGER.debug("%s: Created taxable event set", input_data.asset)
    unfiltered_gain_loss_set: GainLossSet = _create_unfiltered_gain_and_loss_set(configuration, accounting_engine, input_data, unfiltered_taxable_event_set)
    LOGGER.debug("%s: Created gain-loss set", input_data.asset)

    return ComputedData(
        input_data.asset,
        unfiltered_taxable_event_set,
        unfiltered_gain_loss_set,
        input_data,
        configuration.from_date,
        configuration.to_date,
    )


def _get_next_taxable_event_and_acquired_lot(
    accounting_engine: AccountingEngine,
    taxable_event: Optional[AbstractTransaction],
    acquired_lot: Optional[InTransaction],
    taxable_event_amount: RP2Decimal,
    acquired_lot_amount: RP2Decimal,
) -> TaxableEventAndAcquiredLot:
    new_taxable_event: AbstractTransaction
    new_acquired_lot: Optional[InTransaction]
    new_taxable_event_amount: RP2Decimal
    new_acquired_lot_amount: RP2Decimal
    new_taxable_event, new_acquired_lot, new_taxable_event_amount, new_acquired_lot_amount = accounting_engine.get_next_taxable_event_and_amount(
        taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount
    )
    if acquired_lot == new_acquired_lot:
        _, new_acquired_lot, _, new_acquired_lot_amount = accounting_engine.get_acquired_lot_for_taxable_event(
            new_taxable_event, new_acquired_lot, new_taxable_event_amount, new_acquired_lot_amount
        )
    return TaxableEventAndAcquiredLot(new_taxable_event, new_acquired_lot, new_taxable_event_amount, new_acquired_lot_amount)


def _create_unfiltered_gain_and_loss_set(
    configuration: Configuration, accounting_engine: AccountingEngine, input_data: InputData, unfiltered_taxable_event_set: TransactionSet
) -> GainLossSet:
    gain_loss_set: GainLossSet = GainLossSet(configuration, input_data.asset, MIN_DATE, MAX_DATE)
    # Create a fresh instance of accounting engine
    new_accounting_engine: AccountingEngine = accounting_engine.__class__(accounting_engine.years_2_methods)
    taxable_event_iterator: Iterator[AbstractTransaction] = iter(cast(Iterable[AbstractTransaction], unfiltered_taxable_event_set))
    acquired_lot_iterator: Iterator[InTransaction] = iter(cast(Iterable[InTransaction], input_data.unfiltered_in_transaction_set))

    partial_amounts = input_data.in_transaction_2_actual_amount
    new_accounting_engine.initialize(taxable_event_iterator, acquired_lot_iterator, partial_amounts if partial_amounts else None)

    try:
        gain_loss: GainLoss
        taxable_event: AbstractTransaction
        acquired_lot: Optional[InTransaction]
        taxable_event_amount: RP2Decimal
        acquired_lot_amount: RP2Decimal
        total_amount: RP2Decimal = ZERO

        # Retrieve first taxable event and acquired lot
        taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount = _get_next_taxable_event_and_acquired_lot(
            new_accounting_engine, None, None, ZERO, ZERO
        )

        while taxable_event:
            # Type check values returned by accounting method plugin
            AbstractTransaction.type_check("taxable_event", taxable_event)
            if acquired_lot is None:
                # There must always be at least one acquired_lot
                raise RP2RuntimeError("Parameter 'acquired_lot' is None")
            InTransaction.type_check("acquired_lot", acquired_lot)
            Configuration.type_check_positive_decimal("taxable_event_amount", taxable_event_amount)
            Configuration.type_check_positive_decimal("acquired_lot_amount", acquired_lot_amount)

            if taxable_event.is_earning():
                # Handle earnings first: they have no acquired-lot
                gain_loss = GainLoss(configuration, taxable_event_amount, taxable_event, None)
                LOGGER.debug(
                    "tax_engine: taxable is earn: %s / %s + %s = %s: %s",
                    taxable_event_amount,
                    total_amount,
                    taxable_event_amount,
                    total_amount + taxable_event_amount,
                    gain_loss,
                )
                total_amount += taxable_event_amount
                gain_loss_set.add_entry(gain_loss)
                taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount = new_accounting_engine.get_next_taxable_event_and_amount(
                    taxable_event, acquired_lot, ZERO, acquired_lot_amount
                )
                continue
            if taxable_event_amount == acquired_lot_amount:
                gain_loss = GainLoss(configuration, taxable_event_amount, taxable_event, acquired_lot)
                LOGGER.debug(
                    "tax_engine: taxable == acquired: %s == %s / %s + %s = %s: %s",
                    taxable_event_amount,
                    acquired_lot_amount,
                    total_amount,
                    taxable_event_amount,
                    total_amount + taxable_event_amount,
                    gain_loss,
                )
                total_amount += taxable_event_amount
                gain_loss_set.add_entry(gain_loss)
                taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount = _get_next_taxable_event_and_acquired_lot(
                    new_accounting_engine, taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount
                )
            elif taxable_event_amount < acquired_lot_amount:
                gain_loss = GainLoss(configuration, taxable_event_amount, taxable_event, acquired_lot)
                LOGGER.debug(
                    "tax_engine: taxable < acquired: %s < %s / %s + %s = %s: %s",
                    taxable_event_amount,
                    acquired_lot_amount,
                    total_amount,
                    taxable_event_amount,
                    total_amount + taxable_event_amount,
                    gain_loss,
                )
                total_amount += taxable_event_amount
                gain_loss_set.add_entry(gain_loss)
                taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount = new_accounting_engine.get_next_taxable_event_and_amount(
                    taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount
                )
            else:  # taxable_amount > acquired_lot_amount
                gain_loss = GainLoss(configuration, acquired_lot_amount, taxable_event, acquired_lot)
                LOGGER.debug(
                    "tax_engine: taxable > acquired: %s > %s / %s + %s = %s: %s",
                    taxable_event_amount,
                    acquired_lot_amount,
                    total_amount,
                    acquired_lot_amount,
                    total_amount + acquired_lot_amount,
                    gain_loss,
                )
                total_amount += acquired_lot_amount
                gain_loss_set.add_entry(gain_loss)
                taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount = new_accounting_engine.get_acquired_lot_for_taxable_event(
                    taxable_event, acquired_lot, taxable_event_amount, acquired_lot_amount
                )

    except AcquiredLotsExhaustedException:
        raise RP2ValueError("Total in-transaction crypto value < total taxable crypto value") from None
    except TaxableEventsExhaustedException:
        pass

    return gain_loss_set


# Taxable events and their gain/loss pairings for a part of the transaction history (and, in per-wallet application, what each wallet holds
# at the end of the report's to_date).
class _TaxResult(NamedTuple):
    taxable_events: List[AbstractTransaction]
    gain_loss_list: List[GainLoss]
    wallet_lots: Optional[List[WalletLot]] = None


# Per-wallet application (e.g. US from 2025, Treas. Reg. §1.1012-1(j)). The computation has three phases:
# 1) before the switch (January 1 of the country's per-wallet start year, in the configured timezone): universal application, exactly as
#    compute_tax() does;
# 2) at the switch: the lots that are still unused under universal application are allocated to the wallets that hold funds (Rev. Proc.
#    2024-28 global allocation, see UnusedBasisAllocator);
# 3) after the switch: TransferAnalyzer tracks lots per wallet and pairs every taxable event with lots of its own wallet.
# Reports also get what each wallet holds at the end of the configuration's to_date (ComputedData.wallet_lots), so that they can show each
# wallet's actual cost basis. If to_date is before the switch, the holdings at that date come from universal application, and reports
# show them like compute_tax() does (wallet_lots is None).
# allocation_method is the unused basis allocation method of this asset (see PerWalletConfiguration.get_unused_basis_allocation_method()).
# per_wallet_start_year is the first year of per-wallet application: it must be the start of a period of the country's application policy
# that allows per-wallet application. If it's None, the first such period whose default mode is per-wallet is used.
# The returned ComputedData refers to the original (universal) input data, so that reports show the user's transactions.
def compute_tax_per_wallet(
    configuration: Configuration,
    accounting_engine: AccountingEngine,
    input_data: InputData,
    per_wallet_configuration: PerWalletConfiguration,
    allocation_method: Optional[AbstractAccountingMethod] = None,
    per_wallet_start_year: Optional[int] = None,
) -> ComputedData:
    Configuration.type_check("configuration", configuration)
    AccountingEngine.type_check("accounting_engine", accounting_engine)
    InputData.type_check("input_data", input_data)
    PerWalletConfiguration.type_check("per_wallet_configuration", per_wallet_configuration)

    start_year = _get_per_wallet_start_year(configuration.country.get_application_policy(), configuration.country, per_wallet_start_year)
    switch_timestamp = datetime(start_year, 1, 1, tzinfo=per_wallet_configuration.timezone)

    all_transactions = list(cast(Iterable[AbstractTransaction], input_data.create_all_transaction_set(configuration)))
    _check_tax_year_boundary(all_transactions, switch_timestamp, start_year, per_wallet_configuration.timezone_name)
    universal_transactions = [transaction for transaction in all_transactions if transaction.timestamp < switch_timestamp]
    per_wallet_transactions = [transaction for transaction in all_transactions if transaction.timestamp >= switch_timestamp]

    # Phase 1: universal application before the switch.
    universal_input_data: Optional[InputData] = None
    universal_result = _TaxResult([], [])
    if universal_transactions:
        universal_input_data = _create_input_data(configuration, input_data.asset, universal_transactions)
        universal_result = _compute_universal_tax(configuration, accounting_engine, universal_input_data)

    per_wallet_result = _TaxResult([], [])
    if per_wallet_transactions:
        # Phase 2: allocation of unused basis at the switch (nothing to allocate if there were no transactions before it).
        allocated_lots: List[InTransaction] = []
        if universal_input_data is not None:
            unused_lots = _get_unused_lots(universal_input_data, universal_result.gain_loss_list)
            account_2_balance = _get_account_balances(universal_transactions)
            _check_balances_match_unused_lots(account_2_balance, unused_lots)
            allocated_lots = UnusedBasisAllocator(
                configuration,
                switch_timestamp,
                unused_lots,
                account_2_balance,
                allocation_method,
                list(per_wallet_configuration.get_unused_basis_allocation_wallet_order(input_data.asset)),
            ).allocate()
        # Phase 3: per-wallet application after the switch.
        LOGGER.info("%s: per-wallet application from %s (%d transactions)", input_data.asset, switch_timestamp, len(per_wallet_transactions))
        per_wallet_result = _compute_per_wallet_tax(configuration, accounting_engine, input_data.asset, start_year, per_wallet_transactions, allocated_lots)
    # The wallet holdings at to_date are only meaningful if to_date is on or after the switch.
    wallet_lots = per_wallet_result.wallet_lots if configuration.to_date >= switch_timestamp.date() else None

    taxable_event_set = TransactionSet(configuration, "MIXED", input_data.asset, MIN_DATE, MAX_DATE)
    for transaction in universal_result.taxable_events + per_wallet_result.taxable_events:
        taxable_event_set.add_entry(transaction)
    gain_loss_set = GainLossSet(configuration, input_data.asset, MIN_DATE, MAX_DATE)
    for gain_loss in universal_result.gain_loss_list + per_wallet_result.gain_loss_list:
        gain_loss_set.add_entry(gain_loss)

    return ComputedData(
        input_data.asset,
        taxable_event_set,
        gain_loss_set,
        input_data,
        configuration.from_date,
        configuration.to_date,
        wallet_lots=wallet_lots,
    )


# Checks (or, if None, finds) the first year of per-wallet application against the country's application policy.
def _get_per_wallet_start_year(policy: ApplicationPolicy, country: AbstractCountry, per_wallet_start_year: Optional[int]) -> int:
    if per_wallet_start_year is None:
        for period in policy.periods:
            if period.default_mode == ApplicationMode.PER_WALLET:
                return period.start_year
        raise RP2ValueError(f"Per-wallet application is not supported for country '{country.country_iso_code}'")
    Configuration.type_check_positive_int("per_wallet_start_year", per_wallet_start_year)
    period = policy.get_period(per_wallet_start_year)
    if period.start_year != per_wallet_start_year or ApplicationMode.PER_WALLET not in period.allowed_modes:
        raise RP2ValueError(f"Per-wallet application can't start in {per_wallet_start_year} for country '{country.country_iso_code}'")
    return per_wallet_start_year


# Universal application: the same computation as compute_tax(), restricted to the given input data.
def _compute_universal_tax(configuration: Configuration, accounting_engine: AccountingEngine, input_data: InputData) -> _TaxResult:
    taxable_event_set = input_data.create_unfiltered_taxable_event_set(configuration)
    gain_loss_set = _create_unfiltered_gain_and_loss_set(configuration, accounting_engine, input_data, taxable_event_set)
    return _TaxResult(list(cast(Iterable[AbstractTransaction], taxable_event_set)), list(cast(Iterable[GainLoss], gain_loss_set)))


# Per-wallet application of the transactions after the switch, starting from the lots allocated at the switch. Transfers and disposals use
# the accounting method of their year (the same map used by the accounting engine).
def _compute_per_wallet_tax(
    configuration: Configuration,
    accounting_engine: AccountingEngine,
    asset: str,
    start_year: int,
    transactions: List[AbstractTransaction],
    allocated_lots: List[InTransaction],
) -> _TaxResult:
    input_data = _create_input_data(configuration, asset, transactions + cast(List[AbstractTransaction], allocated_lots))
    start_year_accounting_method = accounting_engine.years_2_methods.find_max_value_less_than(start_year)
    if start_year_accounting_method is None:
        raise RP2RuntimeError(f"Internal error: no accounting method assigned for year {start_year}")
    transfer_analysis_result = TransferAnalyzer(
        configuration,
        start_year_accounting_method,
        input_data,
        years_2_accounting_methods=accounting_engine.years_2_methods,
    ).analyze_and_pair(holdings_date=configuration.to_date)
    LOGGER.info("%s: per-wallet application: found %d wallets", asset, len(transfer_analysis_result.wallet_2_input_data))
    taxable_events = [transaction for transaction in transactions if transaction.is_taxable()]
    return _TaxResult(taxable_events, transfer_analysis_result.gain_loss_list, transfer_analysis_result.wallet_lots)


# The tax year of a transaction is the year of its timestamp (in the timezone of the timestamp itself). A transaction whose tax year is on
# one side of the switch while its instant is on the other side is ambiguous: rather than silently picking one, raise an error.
def _check_tax_year_boundary(transactions: List[AbstractTransaction], switch_timestamp: datetime, start_year: int, timezone_name: str) -> None:
    ambiguous_transactions = [
        transaction for transaction in transactions if (transaction.timestamp < switch_timestamp) != (transaction.timestamp.year < start_year)
    ]
    if ambiguous_transactions:
        raise RP2ValueError(
            f"{len(ambiguous_transactions)} transaction(s) fall in tax year {start_year} (or later) by their own timestamp but before the switch to "
            f"per-wallet application ({switch_timestamp}, timezone '{timezone_name}'), or vice versa: express their timestamps in timezone "
            f"'{timezone_name}' or change the timezone in the country section of the configuration file (e.g. country.us). "
            f"First one: {ambiguous_transactions[0]}"
        )


# Builds an InputData from a list of mixed transactions (InputData requires at least one acquisition).
def _create_input_data(configuration: Configuration, asset: str, transactions: List[AbstractTransaction]) -> InputData:
    in_transaction_set = TransactionSet(configuration, "IN", asset, MIN_DATE, MAX_DATE)
    out_transaction_set = TransactionSet(configuration, "OUT", asset, MIN_DATE, MAX_DATE)
    intra_transaction_set = TransactionSet(configuration, "INTRA", asset, MIN_DATE, MAX_DATE)
    for transaction in transactions:
        if isinstance(transaction, InTransaction):
            in_transaction_set.add_entry(transaction)
        elif isinstance(transaction, OutTransaction):
            out_transaction_set.add_entry(transaction)
        elif isinstance(transaction, IntraTransaction):
            intra_transaction_set.add_entry(transaction)
        else:
            raise RP2RuntimeError(f"Internal error: invalid transaction class: {transaction}")
    if in_transaction_set.is_empty():
        raise RP2ValueError(f"{asset}: insufficient balance: there are disposals or transfers, but no acquisitions, before them: {transactions[0]}")
    return InputData(asset, in_transaction_set, out_transaction_set, intra_transaction_set)


# Lots (and amounts) not disposed of under universal application: the "unused basis" of Rev. Proc. 2024-28.
def _get_unused_lots(universal_input_data: InputData, gain_loss_list: List[GainLoss]) -> List[UnusedLot]:
    lot_2_used_amount: Dict[InTransaction, RP2Decimal] = {}
    for gain_loss in gain_loss_list:
        if gain_loss.acquired_lot is not None:
            lot_2_used_amount[gain_loss.acquired_lot] = lot_2_used_amount.get(gain_loss.acquired_lot, ZERO) + gain_loss.crypto_amount
    result: List[UnusedLot] = []
    for entry in universal_input_data.unfiltered_in_transaction_set:
        lot = cast(InTransaction, entry)
        amount = lot.crypto_in - lot_2_used_amount.get(lot, ZERO)
        if amount > ZERO:
            result.append(UnusedLot(lot, amount))
    return result


# Balance of each wallet after the given transactions.
def _get_account_balances(transactions: List[AbstractTransaction]) -> Dict[Account, RP2Decimal]:
    result: Dict[Account, RP2Decimal] = {}
    for transaction in transactions:
        if isinstance(transaction, InTransaction):
            account = Account(transaction.exchange, transaction.holder)
            result[account] = result.get(account, ZERO) + transaction.crypto_in
        elif isinstance(transaction, OutTransaction):
            account = Account(transaction.exchange, transaction.holder)
            result[account] = result.get(account, ZERO) - transaction.crypto_out_with_fee
        elif isinstance(transaction, IntraTransaction):
            from_account = Account(transaction.from_exchange, transaction.from_holder)
            to_account = Account(transaction.to_exchange, transaction.to_holder)
            result[from_account] = result.get(from_account, ZERO) - transaction.crypto_sent
            result[to_account] = result.get(to_account, ZERO) + transaction.crypto_received
    return result


# At the switch the wallets must hold exactly the units of the unused lots (Rev. Proc. 2024-28 allocates unused basis to "the same number of
# remaining digital asset units"): a mismatch means the input is inconsistent (e.g. a wallet with a negative balance).
def _check_balances_match_unused_lots(account_2_balance: Dict[Account, RP2Decimal], unused_lots: List[UnusedLot]) -> None:
    for account, balance in account_2_balance.items():
        if balance < ZERO and not RP2Decimal.is_equal_within_precision(balance, ZERO, CRYPTO_BALANCE_DECIMAL_MASK):
            raise RP2ValueError(f"Balance of {account.exchange}/{account.holder} is negative ({balance}) at the switch to per-wallet application")
    total_balance = RP2Decimal(sum((balance for balance in account_2_balance.values() if balance > ZERO), ZERO))
    total_unused = RP2Decimal(sum((unused_lot.amount for unused_lot in unused_lots), ZERO))
    if not RP2Decimal.is_equal_within_precision(total_balance, total_unused, CRYPTO_BALANCE_DECIMAL_MASK):
        raise RP2ValueError(f"Total wallet balance ({total_balance}) doesn't match unused lot amount ({total_unused}) at the switch to per-wallet application")

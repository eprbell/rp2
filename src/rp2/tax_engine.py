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

from datetime import date, datetime
from typing import Container, Dict, Iterable, Iterator, List, NamedTuple, Optional, cast

from rp2.abstract_country import AbstractCountry
from rp2.abstract_transaction import AbstractTransaction
from rp2.account import Account
from rp2.accounting_method_loader import load_accounting_method
from rp2.accounting_engine import (
    AccountingEngine,
    AcquiredLotsExhaustedException,
    TaxableEventAndAcquiredLot,
    TaxableEventsExhaustedException,
)
from rp2.application_policy import ApplicationMode, ApplicationPolicy
from rp2.balance import CRYPTO_BALANCE_DECIMAL_MASK, BalanceSet
from rp2.computed_data import ComputedData
from rp2.configuration import MAX_DATE, MIN_DATE, Configuration, Keyword
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.logger import LOGGER
from rp2.opening_allocation import OpeningAllocation, UnusedLot
from rp2.out_transaction import OutTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2ValueError
from rp2.transaction_set import TransactionSet
from rp2.transfer_analyzer import TransferAnalyzer
from rp2.unused_basis_allocator import UnusedBasisAllocator
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
# 1) before the switch (the start of January 1st of the country's per-wallet start year, in the tax time zone: see
#    Configuration.tax_timezone): universal application, exactly as compute_tax() does;
# 2) at the switch: the lots that are still unused under universal application are allocated to the wallets that hold funds (Rev. Proc.
#    2024-28 global allocation, see UnusedBasisAllocator). This happens whenever there are funds at the switch, even if nothing happens
#    after it: e.g. a coin bought in 2024 and never sold or moved is still allocated to the wallet holding it at the start of 2025;
# 3) after the switch: TransferAnalyzer tracks lots per wallet and pairs every taxable event with lots of its own wallet.
# Reports also get what each wallet holds at the end of the configuration's to_date (ComputedData.wallet_lots), so that they can show each
# wallet's actual cost basis, and the record of the allocation at the switch (ComputedData.opening_allocation), for the opening allocation
# report.
# If to_date is before the switch, the report only covers years of universal application: the result is the one of compute_tax() (the
# holdings at to_date come from universal application and wallet_lots is None), and the per-wallet settings are not needed. Example: a US
# report with to_date 2024-12-31 doesn't need them, even if the input has transactions in 2025.
# Otherwise the per-wallet settings (time zone and unused basis allocation rule) come from the country section of the configuration (e.g.
# [country.us]): it's an error if the configuration doesn't have them.
# The unused basis allocation rule of the asset (method and wallet order) comes only from the per-wallet settings of the configuration (see
# PerWalletConfiguration.get_unused_basis_allocation_method()): the method name is turned into a method here, once per asset, so the method
# that sorts the unused lots is always the one named in the configuration and in the opening allocation report.
# per_wallet_start_year is the first year of per-wallet application: it must be the start of a period of the country's application policy
# that allows per-wallet application. If it's None, the first such period whose default mode is per-wallet is used.
# The returned ComputedData refers to the original (universal) input data, so that reports show the user's transactions.
def compute_tax_per_wallet(
    configuration: Configuration,
    accounting_engine: AccountingEngine,
    input_data: InputData,
    per_wallet_start_year: Optional[int] = None,
) -> ComputedData:
    Configuration.type_check("configuration", configuration)
    AccountingEngine.type_check("accounting_engine", accounting_engine)
    InputData.type_check("input_data", input_data)

    start_year = _get_per_wallet_start_year(configuration.country.get_application_policy(), configuration.country, per_wallet_start_year)
    # to_date is a tax date (a date in the tax time zone), so it's before the switch exactly when it's before January 1st of start_year.
    if configuration.to_date < date(start_year, 1, 1):
        return compute_tax(configuration, accounting_engine, input_data)
    per_wallet_configuration = configuration.per_wallet_configuration
    # The tax time zone is the time zone of the per-wallet settings: it's None exactly when they are missing.
    tax_timezone = configuration.tax_timezone
    if per_wallet_configuration is None or tax_timezone is None:
        raise RP2ValueError(
            f"{input_data.asset}: per-wallet application needs the per-wallet settings (at least 'timezone') in the "
            f"'country.{configuration.country.country_iso_code}' section of the configuration file"
        )
    # The switch is the first instant of start_year in the tax time zone, the one in which tax years are computed: so a transaction is
    # after the switch exactly when its tax year is start_year or later, and both phases use the accounting method of its tax year.
    # Example with America/New_York and start year 2025: the switch is 2025-01-01T00:00:00-05:00, and 2025-01-01T03:00:00+09:00 (3 AM in
    # Tokyo) is still December 31st, 2024 in New York, so it's before the switch.
    switch_timestamp = datetime(start_year, 1, 1, tzinfo=tax_timezone)

    all_transactions = list(cast(Iterable[AbstractTransaction], input_data.create_all_transaction_set(configuration)))
    universal_transactions = [transaction for transaction in all_transactions if transaction.timestamp < switch_timestamp]
    per_wallet_transactions = [transaction for transaction in all_transactions if transaction.timestamp >= switch_timestamp]

    # Phase 1: universal application before the switch.
    universal_input_data: Optional[InputData] = None
    universal_result = _TaxResult([], [])
    if universal_transactions:
        universal_input_data = _create_input_data(configuration, input_data.asset, universal_transactions)
        universal_result = _compute_universal_tax(configuration, accounting_engine, universal_input_data)

    # Phase 2: allocation of unused basis at the switch (nothing to allocate if there were no transactions before it). It doesn't depend on
    # the transactions after the switch: they may not exist at all.
    opening_allocation: Optional[OpeningAllocation] = None
    if universal_input_data is not None:
        unused_lots = _get_unused_lots(universal_input_data, universal_result.gain_loss_list)
        # The balance of each wallet at the switch (the end of the last day before it, in the tax time zone), computed by BalanceSet like the
        # balances of the reports: same arithmetic, same date limit, and the same check that no wallet goes negative (unless -n allows it).
        balance_set = BalanceSet(configuration, universal_input_data, date(start_year - 1, 12, 31))
        account_2_balance = {Account(balance.exchange, balance.holder): balance.final_balance for balance in balance_set}
        _check_balances_match_unused_lots(account_2_balance, unused_lots)
        allocation_method_name = per_wallet_configuration.get_unused_basis_allocation_method(input_data.asset)
        opening_allocation = UnusedBasisAllocator(
            configuration,
            input_data.asset,
            switch_timestamp,
            unused_lots,
            account_2_balance,
            load_accounting_method(allocation_method_name) if allocation_method_name else None,
            list(per_wallet_configuration.get_unused_basis_allocation_wallet_order(input_data.asset)),
            allocation_method_field=_get_allocation_field(
                Keyword.UNUSED_BASIS_ALLOCATION_METHOD,
                input_data.asset,
                per_wallet_configuration.asset_2_unused_basis_allocation_method,
                bool(per_wallet_configuration.unused_basis_allocation_method),
            ),
            wallet_order_field=_get_allocation_field(
                Keyword.UNUSED_BASIS_ALLOCATION_WALLET_ORDER,
                input_data.asset,
                per_wallet_configuration.asset_2_unused_basis_allocation_wallet_order,
                bool(per_wallet_configuration.unused_basis_allocation_wallet_order),
            ),
        ).allocate()
    allocated_lots: List[InTransaction] = opening_allocation.allocated_lots if opening_allocation is not None else []

    # Phase 3: per-wallet application after the switch, starting from the allocated lots. If there are neither allocated lots nor transactions
    # after the switch, the wallets hold nothing.
    per_wallet_result = _TaxResult([], [], [])
    if allocated_lots or per_wallet_transactions:
        LOGGER.info(
            "%s: per-wallet application from %s (start of %d in %s): %d lot pieces allocated at the switch, %d transactions after it",
            input_data.asset,
            switch_timestamp.isoformat(),
            start_year,
            tax_timezone.key,
            len(allocated_lots),
            len(per_wallet_transactions),
        )
        per_wallet_result = _compute_per_wallet_tax(configuration, accounting_engine, input_data.asset, start_year, per_wallet_transactions, allocated_lots)

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
        wallet_lots=per_wallet_result.wallet_lots,
        opening_allocation=opening_allocation,
    )


# Name of the configuration field that the allocation method (or wallet order) of the asset comes from: the asset's override (e.g.
# unused_basis_allocation_method.BTC), if any, otherwise the default field, if set. None if neither is set.
def _get_allocation_field(field: Keyword, asset: str, overridden_assets: Container[str], has_default: bool) -> Optional[str]:
    if asset in overridden_assets:
        return f"{field.value}.{asset}"
    return field.value if has_default else None


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


# At the switch the wallets must hold exactly the units of the unused lots (Rev. Proc. 2024-28 allocates unused basis to "the same number of
# remaining digital asset units"): a mismatch means the input is inconsistent. A negative balance is also an error here, even when -n allows
# negative balances: per-wallet application can't start from a wallet that holds less than nothing.
def _check_balances_match_unused_lots(account_2_balance: Dict[Account, RP2Decimal], unused_lots: List[UnusedLot]) -> None:
    for account, balance in account_2_balance.items():
        if balance < ZERO and not RP2Decimal.is_equal_within_precision(balance, ZERO, CRYPTO_BALANCE_DECIMAL_MASK):
            raise RP2ValueError(f"Balance of {account.exchange}/{account.holder} is negative ({balance}) at the switch to per-wallet application")
    total_balance = RP2Decimal(sum((balance for balance in account_2_balance.values() if balance > ZERO), ZERO))
    total_unused = RP2Decimal(sum((unused_lot.amount for unused_lot in unused_lots), ZERO))
    if not RP2Decimal.is_equal_within_precision(total_balance, total_unused, CRYPTO_BALANCE_DECIMAL_MASK):
        raise RP2ValueError(f"Total wallet balance ({total_balance}) doesn't match unused lot amount ({total_unused}) at the switch to per-wallet application")

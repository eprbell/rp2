# Copyright 2025 eprbell
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

# R11 from the review of eprbell/rp2#155: generated histories run end to end through compute_tax_per_wallet() and the reports, compared
# with an independent model of the rules.
#
# The histories start in late 2024 (universal application), cross the switch (January 1st, 2025, in the tax time zone) and the start of
# 2026, and use a different accounting method in each year. They include transactions at the same instant, purchase fees, income, sales of
# part or all of a wallet, transfers with fees (also of everything sent) and transfers back to where the coins came from.
#
# The model below is a direct, simple simulation of the documented rules (docs/user_faq.md, "How Do I Use Per-Wallet Application?"):
# - before the switch, one pool of lots: every disposal (a sale with its fee, the fee of a transfer) takes coins from the lots acquired up to
#   its time, in the order of the method of its tax year: FIFO oldest first, LIFO newest first, HIFO highest price first, LOFO lowest price
#   first. Transactions at the same instant are taken in this order: acquisitions, sales, transfers, then input row;
# - at the switch, the lots not yet used are sorted with the allocation method and assigned to the wallets in the configured order, each
#   wallet up to the coins it holds then (all to the one wallet that holds coins, if there's only one);
# - after the switch, each wallet has its own lots: a sale takes coins from its own wallet; a transfer takes the coins it sends from its
#   own wallet, pays the fee with the first of them and moves the rest, with their lots (cost and date), to the destination. Transactions at
#   the same instant are taken in this order: acquisitions, transfers, sales, then input row.
# It doesn't share code with RP2's engine: it uses lists and dictionaries instead of heaps, artificial transactions and accounting method
# plugins. Lots never tie in the order of a method (purchases have distinct timestamps and prices), so the model needs no tie-breaking rule.
#
# What is compared (always up to the report's to date):
# - every disposal: how many coins of which lot it used, and their cost basis;
# - every income: its coins;
# - what each wallet holds (coins, cost basis and acquisition date of each lot);
# - the opening allocation: unused lots in the order of the method and allocated pieces in order;
# - the reports: open positions (each wallet's coins and cost basis), opening allocation (Summary and Allocation sheets) and the US tax
#   report (coins, cost basis, acquisition date and holding period of every disposal and income).
# Example of a history: buy 2 coins on Coinbase on December 20th, 2024 (FIFO year), move 1 to Kraken on December 31st, sell 1 on Kraken on
# March 3rd, 2025 (HIFO year) at the same instant as a purchase on Kraken: the sale can use the coin bought at that instant, or the one
# allocated to Kraken at the switch, whichever has the highest price.

import shutil
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple
from zoneinfo import ZoneInfo

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from ods_diff import read_sheet_rows
from per_wallet_common import _create_configuration
from prezzemolo.avl_tree import AVLTree

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.account import Account
from rp2.accounting_engine import AccountingEngine
from rp2.computed_data import ComputedData
from rp2.configuration import MAX_DATE, Configuration
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.localization import set_generation_language
from rp2.out_transaction import OutTransaction
from rp2.per_wallet_configuration import PerWalletConfiguration
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO
from rp2.plugin.country.us import US
from rp2.plugin.report.open_positions import Generator as OpenPositionsGenerator
from rp2.plugin.report.opening_allocation import Generator as OpeningAllocationGenerator
from rp2.plugin.report.us.tax_report_us import Generator as TaxReportUSGenerator
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.tax_engine import compute_tax_per_wallet
from rp2.transaction_set import TransactionSet

_ASSET = "B1"
_COINBASE = Account("Coinbase", "Bob")
_KRAKEN = Account("Kraken", "Bob")
_BLOCKFI = Account("BlockFi", "Bob")
# A known wallet that never has transactions: it can be in the wallet order, and gets nothing.
_COINBASE_PRO = Account("Coinbase Pro", "Bob")
_ACCOUNTS = [_COINBASE, _KRAKEN, _BLOCKFI]
_METHODS: Dict[str, AbstractAccountingMethod] = {
    "fifo": AccountingMethodFIFO(),
    "lifo": AccountingMethodLIFO(),
    "hifo": AccountingMethodHIFO(),
    "lofo": AccountingMethodLOFO(),
}
_EARN_TYPES = {"Income", "Staking"}
# Amounts are multiples of 0.001, to exercise lot splitting with non-integer amounts.
_QUANTUM = RP2Decimal("0.001")
# Cost basis is computed in a different order by the model (coins times cost per coin) and RP2 (cost times coins divided by lot coins).
_TOLERANCE = RP2Decimal("1e-9")
# Histories run between these two instants (UTC), across the start of 2025 and of 2026.
_FIRST_INSTANT = datetime(2024, 11, 15, tzinfo=timezone.utc)
_LAST_INSTANT = datetime(2026, 2, 15, tzinfo=timezone.utc)
_SWITCH_YEAR = 2025


class _Step(NamedTuple):
    kind: str  # "in", "out" or "intra"
    timestamp: datetime
    account: Account
    to_account: Account
    amount: RP2Decimal  # in: coins acquired; out: coins sold (without the fee); intra: coins sent
    fee: RP2Decimal  # out: coins paid as fee; intra: coins sent but not received
    price: RP2Decimal
    fiat_fee: RP2Decimal  # in: purchase fee in fiat (part of the cost basis)
    transaction_type: str


class _History(NamedTuple):
    steps: List[_Step]
    zone: str
    # Accounting method of 2024 (universal application), 2025 and 2026, and allocation method.
    year_2_method: Dict[int, str]
    allocation_method: str
    wallet_order: Tuple[Account, ...]
    # Last day of the report (a tax date), or None for no date filter.
    to_date: Optional[date]


# Order of same-instant transactions: universal application (InputData.create_unfiltered_taxable_event_set(): acquisitions, then sales,
# then transfers) and per-wallet application (TransferAnalyzer: acquisitions, then transfers, then sales).
_UNIVERSAL_RANK = {"in": 0, "out": 1, "intra": 2}
_PER_WALLET_RANK = {"in": 0, "intra": 1, "out": 2}


def _amount(draw: st.DrawFn, maximum: RP2Decimal) -> RP2Decimal:
    return RP2Decimal(draw(st.integers(min_value=1, max_value=int(maximum / _QUANTUM)))) * _QUANTUM


# Random valid histories: no wallet ever goes negative, in the order in which transactions are processed after the switch. Instants are
# distinct and increasing, except that a transfer or sale can happen at the same instant as the previous transaction, if it comes after
# it in the per-wallet order (e.g. a purchase and a sale, a transfer and a sale): so generation order and processing order are the same.
# Purchases always have their own instant and a distinct price, so that no two lots tie in the order of any method.
@st.composite
def _histories(draw: st.DrawFn, report_after_switch: bool = False) -> _History:  # pylint: disable=too-many-locals,too-many-statements
    step_count = draw(st.integers(min_value=3, max_value=20))
    hours = (_LAST_INSTANT - _FIRST_INSTANT) // timedelta(hours=1)
    offsets = sorted(draw(st.lists(st.integers(min_value=0, max_value=hours), min_size=step_count, max_size=step_count, unique=True)))
    balances: Dict[Account, RP2Decimal] = {account: ZERO for account in _ACCOUNTS}
    last_sender: Dict[Account, Account] = {}
    steps: List[_Step] = []
    for index, offset in enumerate(offsets):
        funded = [account for account in _ACCOUNTS if balances[account] >= _QUANTUM * RP2Decimal("2")]
        kind = draw(st.sampled_from(["in", "in", "out", "intra", "intra"])) if funded else "in"
        timestamp = _FIRST_INSTANT + timedelta(hours=offset)
        if kind != "in" and steps and _PER_WALLET_RANK[kind] >= _PER_WALLET_RANK[steps[-1].kind] and draw(st.integers(0, 3)) == 0:
            timestamp = steps[-1].timestamp
        price = RP2Decimal(draw(st.integers(min_value=1, max_value=500))) + RP2Decimal(index) / RP2Decimal("1000")
        if kind == "in":
            account = draw(st.sampled_from(_ACCOUNTS))
            amount = _amount(draw, RP2Decimal("10"))
            transaction_type = draw(st.sampled_from(["Buy", "Buy", "Buy", "Income", "Staking"]))
            fiat_fee = (
                RP2Decimal(draw(st.integers(min_value=1, max_value=50))) / RP2Decimal("10") if transaction_type == "Buy" and draw(st.booleans()) else ZERO
            )
            steps.append(_Step("in", timestamp, account, account, amount, ZERO, price, fiat_fee, transaction_type))
            balances[account] += amount
        elif kind == "out":
            account = draw(st.sampled_from(funded))
            # Sometimes the whole balance is sold, to use up lots completely.
            total = balances[account] if draw(st.integers(0, 3)) == 0 else _amount(draw, balances[account])
            fee = _amount(draw, total - _QUANTUM) if total > _QUANTUM and draw(st.booleans()) else ZERO
            steps.append(_Step("out", timestamp, account, account, total - fee, fee, price, ZERO, "Sell"))
            balances[account] -= total
        else:
            account = draw(st.sampled_from(funded))
            to_account = draw(st.sampled_from(_ACCOUNTS))
            if account in last_sender and draw(st.booleans()):
                to_account = last_sender[account]
            last_sender[to_account] = account
            sent = balances[account] if draw(st.integers(0, 3)) == 0 else _amount(draw, balances[account])
            fee_kind = draw(st.sampled_from(["none", "part", "part", "all"]))
            fee = ZERO
            if fee_kind == "part" and sent > _QUANTUM:
                fee = _amount(draw, sent - _QUANTUM)
            elif fee_kind == "all":
                fee = sent
            steps.append(_Step("intra", timestamp, account, to_account, sent, fee, price, ZERO, "Move"))
            balances[account] -= sent
            balances[to_account] += sent - fee

    zone = draw(st.sampled_from(["UTC", "America/New_York", "Asia/Tokyo"]))
    year_2_method = {year: draw(st.sampled_from(sorted(_METHODS))) for year in (2024, 2025, 2026)}
    wallet_order = list(draw(st.permutations(_ACCOUNTS)))
    if draw(st.booleans()):
        wallet_order.insert(draw(st.integers(min_value=0, max_value=len(wallet_order))), _COINBASE_PRO)
    first_day = date(_SWITCH_YEAR, 1, 1) if report_after_switch else date(2024, 12, 20)
    days = (date(2026, 1, 20) - first_day).days
    to_date = first_day + timedelta(days=draw(st.integers(min_value=0, max_value=days)))
    if draw(st.booleans()):
        to_date = MAX_DATE
    return _History(steps, zone, year_2_method, draw(st.sampled_from(sorted(_METHODS))), tuple(wallet_order), to_date)


# The model.


# A lot of the model: its coins, cost per coin (purchase fee included) and attributes used to order lots.
class _Lot(NamedTuple):
    unique_id: str
    row: int
    timestamp: datetime
    price: RP2Decimal
    amount: RP2Decimal
    cost_per_coin: RP2Decimal


# A taxable event of the model and the lot it used: the lot unique id is "" for income, which uses no lot.
class _PairingKey(NamedTuple):
    taxable_event_id: str
    lot_id: str


# A wallet of the model and a lot it holds.
class _HoldingKey(NamedTuple):
    wallet: Account
    lot_id: str


# Coins taken from a lot (see _take()), or the coins of a lot left unused at the switch.
class _ModelPiece(NamedTuple):
    lot_id: str
    coins: RP2Decimal


# Coins of an unused lot allocated to a wallet at the switch.
class _ModelAllocatedPiece(NamedTuple):
    wallet: Account
    lot_id: str
    coins: RP2Decimal


# Disposal and income of the model: coins of each lot used by each taxable event.
_Pairings = Dict[_PairingKey, RP2Decimal]
# What the wallets hold: coins of each lot in each wallet.
_Holdings = Dict[_HoldingKey, RP2Decimal]


class _ModelResult(NamedTuple):
    lots: Dict[str, _Lot]
    pairings: _Pairings
    holdings: Optional[_Holdings]
    # Unused lots in the order of the allocation method and allocated pieces in the order they are allocated, if there is an opening
    # allocation.
    unused_lots: Optional[List[_ModelPiece]]
    pieces: Optional[List[_ModelAllocatedPiece]]
    automatic: bool
    wallet_balances: Dict[Account, RP2Decimal]


# Order of lots for a method: the lot with the smallest key is used first (lots with the same key keep their order).
def _lot_order(method: str, lot: _Lot) -> RP2Decimal:
    instant = RP2Decimal(repr(lot.timestamp.timestamp()))
    if method == "fifo":
        return instant
    if method == "lifo":
        return -instant
    if method == "hifo":
        return -lot.price
    return lot.price


def _unique_id(row: int) -> str:
    return f"s{row}"


# Takes coins from lots (lot unique id -> coins), in the order of the method: returns the pieces taken, in order.
def _take(lots: Dict[str, _Lot], available: Dict[str, RP2Decimal], method: str, amount: RP2Decimal) -> List[_ModelPiece]:
    result: List[_ModelPiece] = []
    for unique_id in sorted((unique_id for unique_id, coins in available.items() if coins > ZERO), key=lambda unique_id: _lot_order(method, lots[unique_id])):
        if amount <= ZERO:
            break
        piece = min(amount, available[unique_id])
        available[unique_id] -= piece
        amount -= piece
        result.append(_ModelPiece(unique_id, piece))
    if amount > ZERO:
        raise ValueError(f"Model error: {amount} coins missing")
    return result


def _add_pairings(pairings: _Pairings, event_id: str, pieces: List[_ModelPiece]) -> None:
    for piece in pieces:
        key = _PairingKey(event_id, piece.lot_id)
        pairings[key] = pairings.get(key, ZERO) + piece.coins


def _run_model(history: _History) -> _ModelResult:  # pylint: disable=too-many-locals,too-many-branches
    zone = ZoneInfo(history.zone)
    switch = datetime(_SWITCH_YEAR, 1, 1, tzinfo=zone)
    to_date = history.to_date or MAX_DATE
    rows = [(row, step) for row, step in enumerate(history.steps, start=1) if step.timestamp.astimezone(zone).date() <= to_date]
    lots: Dict[str, _Lot] = {}
    for row, step in rows:
        if step.kind == "in":
            lots[_unique_id(row)] = _Lot(
                _unique_id(row), row, step.timestamp, step.price, step.amount, (step.price * step.amount + step.fiat_fee) / step.amount
            )
    pairings: _Pairings = {}

    # Before the switch: one pool of lots.
    pool: Dict[str, RP2Decimal] = {}
    balances: Dict[Account, RP2Decimal] = {}
    for row, step in sorted(
        (item for item in rows if item[1].timestamp < switch), key=lambda item: (item[1].timestamp, _UNIVERSAL_RANK[item[1].kind], item[0])
    ):
        method = history.year_2_method[2024]
        event_id = _unique_id(row)
        if step.kind == "in":
            pool[event_id] = step.amount
            balances[step.account] = balances.get(step.account, ZERO) + step.amount
            if step.transaction_type in _EARN_TYPES:
                pairings[_PairingKey(event_id, "")] = step.amount
        elif step.kind == "out":
            _add_pairings(pairings, event_id, _take(lots, pool, method, step.amount + step.fee))
            # Balances only matter at the switch: in this order a sale can come before the transfer that funded it at the same instant.
            balances[step.account] = balances.get(step.account, ZERO) - step.amount - step.fee
        else:
            if step.fee > ZERO:
                _add_pairings(pairings, event_id, _take(lots, pool, method, step.fee))
            balances[step.account] = balances.get(step.account, ZERO) - step.amount
            balances[step.to_account] = balances.get(step.to_account, ZERO) + step.amount - step.fee
    if to_date < switch.date():
        return _ModelResult(lots, pairings, None, None, None, False, balances)

    # At the switch: the unused lots go to the wallets that hold coins, in the wallet order (or all to the only one).
    wallets: Dict[Account, Dict[str, RP2Decimal]] = {}
    unused_lots: Optional[List[_ModelPiece]] = None
    pieces: Optional[List[_ModelAllocatedPiece]] = None
    funded = [account for account in history.wallet_order if balances.get(account, ZERO) > ZERO]
    automatic = len(funded) == 1
    if funded:
        unused = {unique_id: coins for unique_id, coins in pool.items() if coins > ZERO}
        unused_lots = [
            _ModelPiece(unique_id, unused[unique_id])
            for unique_id in sorted(unused, key=lambda unique_id: _lot_order(history.allocation_method, lots[unique_id]))
        ]
        pieces = []
        for account in funded:
            for unique_id, coins in _take(lots, unused, history.allocation_method, balances[account]):
                pieces.append(_ModelAllocatedPiece(account, unique_id, coins))
                wallets.setdefault(account, {})[unique_id] = wallets.get(account, {}).get(unique_id, ZERO) + coins

    # After the switch: each wallet has its own lots.
    for row, step in sorted(
        (item for item in rows if item[1].timestamp >= switch), key=lambda item: (item[1].timestamp, _PER_WALLET_RANK[item[1].kind], item[0])
    ):
        method = history.year_2_method[step.timestamp.astimezone(zone).year]
        event_id = _unique_id(row)
        if step.kind == "in":
            wallets.setdefault(step.account, {})[event_id] = step.amount
            if step.transaction_type in _EARN_TYPES:
                pairings[_PairingKey(event_id, "")] = step.amount
        elif step.kind == "out":
            _add_pairings(pairings, event_id, _take(lots, wallets[step.account], method, step.amount + step.fee))
        else:
            taken = _take(lots, wallets[step.account], method, step.amount)
            fee_left = step.fee
            for unique_id, coins in taken:
                fee_piece = min(fee_left, coins)
                if fee_piece > ZERO:
                    _add_pairings(pairings, event_id, [_ModelPiece(unique_id, fee_piece)])
                    fee_left -= fee_piece
                if coins > fee_piece:
                    destination = wallets.setdefault(step.to_account, {})
                    destination[unique_id] = destination.get(unique_id, ZERO) + coins - fee_piece
    holdings: _Holdings = {
        _HoldingKey(account, unique_id): coins for account, lot_coins in wallets.items() for unique_id, coins in lot_coins.items() if coins > ZERO
    }
    return _ModelResult(lots, pairings, holdings, unused_lots, pieces, automatic, balances)


# RP2's side.


def _create_input_data(configuration: Configuration, steps: List[_Step]) -> InputData:
    sets = {name: TransactionSet(configuration, name, _ASSET) for name in ("IN", "OUT", "INTRA")}
    for row, step in enumerate(steps, start=1):
        timestamp = step.timestamp.isoformat()
        unique_id = _unique_id(row)
        if step.kind == "in":
            sets["IN"].add_entry(
                InTransaction(
                    configuration,
                    timestamp,
                    _ASSET,
                    step.account.exchange,
                    step.account.holder,
                    step.transaction_type,
                    step.price,
                    step.amount,
                    fiat_fee=step.fiat_fee if step.fiat_fee > ZERO else None,
                    row=row,
                    unique_id=unique_id,
                )
            )
        elif step.kind == "out":
            sets["OUT"].add_entry(
                OutTransaction(
                    configuration,
                    timestamp,
                    _ASSET,
                    step.account.exchange,
                    step.account.holder,
                    "Sell",
                    step.price,
                    step.amount,
                    step.fee,
                    row=row,
                    unique_id=unique_id,
                )
            )
        else:
            sets["INTRA"].add_entry(
                IntraTransaction(
                    configuration,
                    timestamp,
                    _ASSET,
                    step.account.exchange,
                    step.account.holder,
                    step.to_account.exchange,
                    step.to_account.holder,
                    step.price,
                    step.amount,
                    step.amount - step.fee,
                    row=row,
                    unique_id=unique_id,
                )
            )
    return InputData(_ASSET, sets["IN"], sets["OUT"], sets["INTRA"], from_date=configuration.from_date, to_date=configuration.to_date)


# RP2's results for a history, and the configuration they were computed with.
class _ComputedHistory(NamedTuple):
    configuration: Configuration
    computed_data: ComputedData


def _compute(history: _History) -> _ComputedHistory:
    per_wallet_configuration = PerWalletConfiguration(
        timezone_name=history.zone, unused_basis_allocation_method=history.allocation_method, unused_basis_allocation_wallet_order=history.wallet_order
    )
    configuration = _create_configuration(per_wallet_configuration, to_date=history.to_date or MAX_DATE)
    tree: AVLTree[int, AbstractAccountingMethod] = AVLTree()
    for year, method in ((1970, history.year_2_method[2024]), (2025, history.year_2_method[2025]), (2026, history.year_2_method[2026])):
        tree.insert_node(year, _METHODS[method])
    input_data = _create_input_data(configuration, history.steps)
    return _ComputedHistory(configuration, compute_tax_per_wallet(configuration, AccountingEngine(tree), input_data))


def _close(first: RP2Decimal, second: RP2Decimal) -> bool:
    return abs(first - second) <= _TOLERANCE


_SETTINGS = settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
_REPORT_SETTINGS = settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])


class TestPerWalletModel(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    # Disposals, income, holdings and the opening allocation computed by RP2 are the ones of the model.
    @_SETTINGS
    @given(history=_histories())
    def test_engine_matches_the_model(self, history: _History) -> None:  # pylint: disable=too-many-locals
        model = _run_model(history)
        _, computed_data = _compute(history)

        # Disposals and income: coins and cost basis of each lot used by each taxable event.
        got_coins: _Pairings = {}
        got_basis: Dict[_PairingKey, RP2Decimal] = {}
        for gain_loss in computed_data.gain_loss_set:
            assert isinstance(gain_loss, GainLoss)
            key = _PairingKey(gain_loss.taxable_event.unique_id, gain_loss.acquired_lot.original_lot.unique_id if gain_loss.acquired_lot else "")
            got_coins[key] = got_coins.get(key, ZERO) + gain_loss.crypto_amount
            got_basis[key] = got_basis.get(key, ZERO) + (gain_loss.fiat_cost_basis if gain_loss.acquired_lot else ZERO)
        self.assertEqual(got_coins, model.pairings)
        for key, coins in model.pairings.items():
            want_basis = coins * model.lots[key.lot_id].cost_per_coin if key.lot_id else ZERO
            self.assertTrue(_close(got_basis[key], want_basis), msg=f"{key}: {got_basis[key]} != {want_basis}")

        # Holdings: RP2 has none (universal application) if the report ends before the switch.
        wallet_lots = computed_data.wallet_lots
        if model.holdings is None:
            self.assertIsNone(wallet_lots)
            self.assertIsNone(computed_data.opening_allocation)
            return
        assert wallet_lots is not None
        got_holdings: _Holdings = {}
        for wallet_lot in wallet_lots:
            key2 = _HoldingKey(wallet_lot.account, wallet_lot.original_lot.unique_id)
            got_holdings[key2] = got_holdings.get(key2, ZERO) + wallet_lot.amount
            # A held piece keeps the cost per coin and the acquisition date of its lot.
            lot = model.lots[wallet_lot.original_lot.unique_id]
            self.assertTrue(_close(wallet_lot.cost_basis, wallet_lot.amount * lot.cost_per_coin))
            self.assertEqual(wallet_lot.acquisition_timestamp, lot.timestamp)
        self.assertEqual(got_holdings, model.holdings)

        # The opening allocation: unused lots in the order of the allocation method and pieces in the order they were allocated.
        opening_allocation = computed_data.opening_allocation
        if model.pieces is None:
            self.assertIsNone(opening_allocation)
            return
        assert opening_allocation is not None
        got_unused_lots: List[_ModelPiece] = [_ModelPiece(lot.acquired_lot.unique_id, lot.amount) for lot in opening_allocation.unused_lots]
        self.assertEqual(got_unused_lots, model.unused_lots)
        got_pieces: List[_ModelAllocatedPiece] = [
            _ModelAllocatedPiece(Account(piece.exchange, piece.holder), piece.original_lot.unique_id, piece.crypto_in)
            for piece in opening_allocation.allocated_lots
        ]
        self.assertEqual(got_pieces, model.pieces)
        self.assertEqual(opening_allocation.is_automatic, model.automatic)
        for piece in opening_allocation.allocated_lots:
            self.assertEqual(piece.cost_basis_timestamp, model.lots[piece.original_lot.unique_id].timestamp)

    # The reports show the model's results: each wallet's holdings (open positions), the opening allocation, and every disposal and income
    # with its coins, cost basis, acquisition date and holding period (US tax report).
    @_REPORT_SETTINGS
    @given(history=_histories(report_after_switch=True))
    def test_reports_match_the_model(self, history: _History) -> None:  # pylint: disable=too-many-locals
        model = _run_model(history)
        configuration, computed_data = _compute(history)
        assert model.holdings is not None
        output_dir = Path("output") / Path("test_per_wallet_model")
        shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True)
        set_generation_language("en")
        to_date = history.to_date or MAX_DATE
        for generator in (OpenPositionsGenerator(), OpeningAllocationGenerator(), TaxReportUSGenerator()):
            generator.generate(US(), {1970: "fifo"}, {_ASSET: computed_data}, str(output_dir), "", configuration.from_date, to_date, "en")

        # Open positions: coins and cost basis of each wallet (Asset - Exchange sheet: holder, exchange, coins, ..., cost basis).
        want_wallets: Dict[Tuple[str, str], Tuple[RP2Decimal, RP2Decimal]] = {}
        for (account, unique_id), coins in model.holdings.items():
            held_coins, held_basis = want_wallets.get((account.holder, account.exchange), (ZERO, ZERO))
            want_wallets[(account.holder, account.exchange)] = (held_coins + coins, held_basis + coins * model.lots[unique_id].cost_per_coin)
        exchange_rows = [row for row in read_sheet_rows(output_dir / Path("fifo_open_positions.ods"), "Asset - Exchange") or [] if row[:1] == [_ASSET]]
        got_wallets = {(row[1], row[2]): (RP2Decimal(row[3]), RP2Decimal(row[5])) for row in exchange_rows}
        self.assertEqual(sorted(got_wallets), sorted(want_wallets))
        for wallet, (coins, basis) in want_wallets.items():
            self.assertTrue(abs(got_wallets[wallet][0] - coins) <= RP2Decimal("1e-8"), msg=f"{wallet} coins")
            self.assertTrue(abs(got_wallets[wallet][1] - basis) <= RP2Decimal("1e-6"), msg=f"{wallet} basis")

        # Opening allocation report: the Allocation sheet lists the model's pieces in order (asset, exchange, holder, lot, input row, date,
        # coins, cost per coin, cost basis), and the Summary reconciles the totals.
        allocation_path = output_dir / Path("fifo_opening_allocation.ods")
        if model.pieces is None:
            self.assertFalse(allocation_path.exists())
        else:
            allocation_rows = [row for row in read_sheet_rows(allocation_path, "Allocation") or [] if row[:1] == [_ASSET]]
            got_pieces: List[Tuple[str, str, str, RP2Decimal]] = [(row[1], row[2], row[3], RP2Decimal(row[6])) for row in allocation_rows]
            want_pieces: List[Tuple[str, str, str, RP2Decimal]] = [
                (account.exchange, account.holder, unique_id, coins) for account, unique_id, coins in model.pieces
            ]
            self.assertEqual(len(got_pieces), len(want_pieces))
            for got, want in zip(got_pieces, want_pieces):
                self.assertEqual(got[:3], want[:3])
                self.assertTrue(abs(got[3] - want[3]) <= RP2Decimal("1e-8"))
            summary_rows = [row for row in read_sheet_rows(allocation_path, "Summary") or [] if row[:1] == [_ASSET]]
            self.assertEqual(len(summary_rows), 1)
            unused_coins = RP2Decimal(sum((coins for _, coins in model.unused_lots or []), ZERO))
            unused_basis = RP2Decimal(sum((coins * model.lots[unique_id].cost_per_coin for unique_id, coins in model.unused_lots or []), ZERO))
            balance = RP2Decimal(sum((coins for coins in model.wallet_balances.values() if coins > ZERO), ZERO))
            for column, want_value, tolerance in [
                (8, unused_coins, "1e-8"),
                (9, unused_coins, "1e-8"),
                (10, balance, "1e-8"),
                (11, unused_basis, "1e-6"),
                (12, unused_basis, "1e-6"),
            ]:
                self.assertTrue(abs(RP2Decimal(summary_rows[0][column]) - want_value) <= RP2Decimal(tolerance), msg=f"Summary column {column}")
            self.assertEqual(summary_rows[0][3], "Automatic" if model.automatic else "Configured")

        # US tax report: every row is a piece of a disposal or an income, with the taxable event's unique id (column 13). Rows are merged by
        # taxable event, acquisition date (column 2) and holding period (column 14): coins (column 0) and cost basis (column 5).
        zone = ZoneInfo(history.zone)
        want_rows: Dict[Tuple[str, str, str], Tuple[RP2Decimal, RP2Decimal]] = {}
        event_2_date = {_unique_id(row): step.timestamp.astimezone(zone).date() for row, step in enumerate(history.steps, start=1)}
        for (event_id, unique_id), coins in model.pairings.items():
            acquired = model.lots[unique_id].timestamp.astimezone(zone).date() if unique_id else None
            disposed = event_2_date[event_id]
            # US holding period: long term if sold after the first anniversary of the acquisition date.
            term = "LONG" if acquired is not None and disposed > acquired.replace(year=acquired.year + 1) else "SHORT"
            key3 = (event_id, acquired.strftime("%m/%d/%Y") if acquired else "", term)
            held_coins, held_basis = want_rows.get(key3, (ZERO, ZERO))
            want_rows[key3] = (held_coins + coins, held_basis + (coins * model.lots[unique_id].cost_per_coin if unique_id else ZERO))
        got_rows: Dict[Tuple[str, str, str], Tuple[RP2Decimal, RP2Decimal]] = {}
        tax_report_path = output_dir / Path("fifo_tax_report_us.ods")
        for sheet in ("Capital Gains", "Investment Expenses", "Income", "Staking"):
            for row in read_sheet_rows(tax_report_path, sheet) or []:
                if len(row) < 15 or row[1] != _ASSET:
                    continue
                key3 = (row[13], row[2], row[14])
                held_coins, held_basis = got_rows.get(key3, (ZERO, ZERO))
                got_rows[key3] = (held_coins + RP2Decimal(row[0]), held_basis + (RP2Decimal(row[5]) if row[5] else ZERO))
        self.assertEqual(sorted(got_rows), sorted(want_rows))
        for key3, (coins, basis) in want_rows.items():
            self.assertTrue(abs(got_rows[key3][0] - coins) <= RP2Decimal("1e-8"), msg=f"{key3} coins")
            self.assertTrue(abs(got_rows[key3][1] - basis) <= RP2Decimal("1e-6"), msg=f"{key3} basis")


if __name__ == "__main__":
    unittest.main()

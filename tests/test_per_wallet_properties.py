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

# Property-based tests of per-wallet application: random, valid transaction histories across several wallets are generated and the
# following invariants are checked:
# - the lots of each wallet always add up to the wallet balance (checked after every transaction);
# - cost basis is conserved: basis acquired = basis disposed of + basis still held (with either transfer fee treatment);
# - no lot fraction is consumed twice: for every input lot, amount disposed of + amount still held (+ transfer fees, if carried over) equals
#   the lot amount;
# - the same three invariants for histories that start before the switch to per-wallet application and continue after it (unused basis
#   allocation at the switch, then transfers that often go back and forth between wallets);
# - with a single wallet, per-wallet and universal application produce the same gain/losses;
# - universal (e.g. JP) results are not affected by running the per-wallet code on the same input.

import unittest
from datetime import datetime, timedelta, timezone
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from prezzemolo.avl_tree import AVLTree

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.account import Account
from rp2.accounting_engine import AccountingEngine
from rp2.configuration import MAX_DATE, Configuration
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.per_wallet_configuration import PerWalletConfiguration
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO
from rp2.plugin.country.jp import JP
from rp2.plugin.country.us import US
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2ValueError
from rp2.tax_engine import compute_tax, compute_tax_per_wallet
from rp2.transaction_set import TransactionSet
from rp2.transfer_analyzer import TransferAnalyzer

_ASSET = "B1"
_CONFIGURATION_PATH = "./config/test_data.ini"
_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
_ACCOUNTS = [Account("Coinbase", "Bob"), Account("Kraken", "Bob"), Account("BlockFi", "Bob")]
_METHODS: Dict[str, AbstractAccountingMethod] = {
    "fifo": AccountingMethodFIFO(),
    "lifo": AccountingMethodLIFO(),
    "hifo": AccountingMethodHIFO(),
    "lofo": AccountingMethodLOFO(),
}
# Amounts are multiples of 0.001, to exercise lot splitting with non-integer amounts.
_QUANTUM = RP2Decimal("0.001")
_TOLERANCE = RP2Decimal("1e-12")


class _Step(NamedTuple):
    kind: str
    account: Account
    to_account: Account
    amount: RP2Decimal
    fee: RP2Decimal
    price: RP2Decimal
    transaction_type: str


def _amount(draw: st.DrawFn, maximum: RP2Decimal) -> RP2Decimal:
    return RP2Decimal(draw(st.integers(min_value=1, max_value=int(maximum / _QUANTUM)))) * _QUANTUM


# Random valid histories (no wallet ever goes negative). With round_trips, a transfer often sends funds back to the wallet they last came
# from (e.g. A -> B, then B -> A), to exercise the code that returns them to the lot they left from.
@st.composite
def _histories(draw: st.DrawFn, accounts: List[Account], round_trips: bool = False, min_steps: int = 1) -> List[_Step]:
    balances: Dict[Account, RP2Decimal] = {account: ZERO for account in accounts}
    # The wallet that last sent funds to each wallet.
    last_sender: Dict[Account, Account] = {}
    steps: List[_Step] = []
    for _ in range(draw(st.integers(min_value=min_steps, max_value=18))):
        funded = [account for account in accounts if balances[account] >= _QUANTUM * RP2Decimal("2")]
        kind = draw(st.sampled_from(["in", "out", "intra"])) if funded else "in"
        price = RP2Decimal(draw(st.integers(min_value=1, max_value=500)))
        if kind == "in":
            account = draw(st.sampled_from(accounts))
            amount = _amount(draw, RP2Decimal("10"))
            steps.append(_Step("in", account, account, amount, ZERO, price, draw(st.sampled_from(["Buy", "Buy", "Income", "Staking"]))))
            balances[account] += amount
        elif kind == "out":
            account = draw(st.sampled_from(funded))
            total = _amount(draw, balances[account])
            fee = _amount(draw, total) - _QUANTUM if total > _QUANTUM and draw(st.booleans()) else ZERO
            if fee >= total:
                fee = ZERO
            steps.append(_Step("out", account, account, total - fee, fee, price, "Sell"))
            balances[account] -= total
        else:
            account = draw(st.sampled_from(funded))
            to_account = draw(st.sampled_from(accounts))
            if round_trips and account in last_sender and draw(st.booleans()):
                to_account = last_sender[account]
            last_sender[to_account] = account
            sent = _amount(draw, balances[account])
            fee = ZERO
            if draw(st.booleans()) and sent > _QUANTUM:
                fee = _amount(draw, sent - _QUANTUM)
            steps.append(_Step("intra", account, to_account, sent, fee, price, "Move"))
            balances[account] -= sent
            balances[to_account] += sent - fee
    return steps


# A history that crosses the switch to per-wallet application, how many of its steps happen before the switch (at least one step happens
# after it) and the step whose date is the date of the report (None: no date filter). The report date is never earlier than the last step
# before the switch (December 31st), so that most examples check the per-wallet holdings, and a few check that a report ending before the
# switch has none.
class _HistoryCrossingTheSwitch(NamedTuple):
    steps: List[_Step]
    steps_before_switch: int
    report_step: Optional[int]


@st.composite
def _histories_crossing_the_switch(draw: st.DrawFn) -> _HistoryCrossingTheSwitch:
    steps = draw(_histories(_ACCOUNTS, round_trips=True, min_steps=2))
    steps_before_switch = draw(st.integers(min_value=1, max_value=len(steps) - 1))
    report_step = draw(st.one_of(st.none(), st.integers(min_value=steps_before_switch - 1, max_value=len(steps) - 1)))
    return _HistoryCrossingTheSwitch(steps, steps_before_switch, report_step)


# Steps are one day apart (at noon UTC), starting the day after _START. If steps_before_switch is given, that many steps happen in 2024
# instead (one day apart, ending on December 31st), so that the history crosses the switch to per-wallet application (January 1st, 2025).
def _get_step_timestamp(index: int, steps_before_switch: int) -> datetime:
    days = index - steps_before_switch if index < steps_before_switch else index - steps_before_switch + 1
    return _START + timedelta(days=days, hours=12)


def _create_input_data(configuration: Configuration, steps: List[_Step], steps_before_switch: int = 0) -> InputData:
    sets = {name: TransactionSet(configuration, name, _ASSET) for name in ("IN", "OUT", "INTRA")}
    for row, step in enumerate(steps, start=1):
        timestamp = _get_step_timestamp(row - 1, steps_before_switch).isoformat()
        if step.kind == "in":
            sets["IN"].add_entry(
                InTransaction(
                    configuration, timestamp, _ASSET, step.account.exchange, step.account.holder, step.transaction_type, step.price, step.amount, row=row
                )
            )
        elif step.kind == "out":
            sets["OUT"].add_entry(
                OutTransaction(configuration, timestamp, _ASSET, step.account.exchange, step.account.holder, "Sell", step.price, step.amount, step.fee, row=row)
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
                )
            )
    # Like the input parser, the input data is filtered with the dates of the configuration.
    return InputData(_ASSET, sets["IN"], sets["OUT"], sets["INTRA"], from_date=configuration.from_date, to_date=configuration.to_date)


def _accounting_engine(method: AbstractAccountingMethod) -> AccountingEngine:
    tree: AVLTree[int, AbstractAccountingMethod] = AVLTree()
    tree.insert_node(1970, method)
    return AccountingEngine(tree)


def _balances(steps: List[_Step]) -> Dict[Account, RP2Decimal]:
    result: Dict[Account, RP2Decimal] = {}
    for step in steps:
        if step.kind == "in":
            result[step.account] = result.get(step.account, ZERO) + step.amount
        elif step.kind == "out":
            result[step.account] = result.get(step.account, ZERO) - step.amount - step.fee
        else:
            result[step.account] = result.get(step.account, ZERO) - step.amount
            result[step.to_account] = result.get(step.to_account, ZERO) + step.amount - step.fee
    return result


def _get_actual_amount(input_data: InputData, lot: object) -> RP2Decimal:
    assert isinstance(lot, InTransaction)
    return input_data.in_transaction_2_actual_amount.get(lot, lot.crypto_in)


def _universal_gain_losses(configuration: Configuration, input_data: InputData) -> List[Tuple[str, str, RP2Decimal, RP2Decimal]]:
    computed_data = compute_tax(configuration, _accounting_engine(AccountingMethodFIFO()), input_data)
    return sorted(_gain_loss_key(gain_loss) for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss))


def _gain_loss_key(gain_loss: GainLoss) -> Tuple[str, str, RP2Decimal, RP2Decimal]:
    return (
        gain_loss.taxable_event.internal_id,
        gain_loss.acquired_lot.original_lot.internal_id if gain_loss.acquired_lot else "",
        gain_loss.crypto_amount,
        gain_loss.fiat_cost_basis,
    )


def _merge_gain_losses(gain_losses: List[GainLoss]) -> Dict[Tuple[str, str], Tuple[RP2Decimal, RP2Decimal]]:
    # Per-wallet may split a pairing in several pieces (one per artificial lot): merge them by (taxable event, original lot).
    result: Dict[Tuple[str, str], Tuple[RP2Decimal, RP2Decimal]] = {}
    for gain_loss in gain_losses:
        key = (gain_loss.taxable_event.internal_id, gain_loss.acquired_lot.original_lot.internal_id if gain_loss.acquired_lot else "")
        amount, basis = result.get(key, (ZERO, ZERO))
        result[key] = (amount + gain_loss.crypto_amount, basis + gain_loss.fiat_cost_basis)
    return result


_SETTINGS = settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])


class TestPerWalletProperties(unittest.TestCase):
    @_SETTINGS
    @given(steps=_histories(_ACCOUNTS), method_name=st.sampled_from(sorted(_METHODS)))
    def test_wallet_lots_add_up_to_wallet_balance_after_every_transaction(self, steps: List[_Step], method_name: str) -> None:
        configuration = Configuration(_CONFIGURATION_PATH, US())
        for length in range(1, len(steps) + 1):
            prefix = steps[:length]
            if all(step.kind != "in" for step in prefix):
                continue
            result = TransferAnalyzer(configuration, _METHODS[method_name], _create_input_data(configuration, prefix)).analyze_and_pair()
            balances = _balances(prefix)
            for account, input_data in result.wallet_2_input_data.items():
                held = RP2Decimal(sum((_get_actual_amount(input_data, lot) for lot in input_data.unfiltered_in_transaction_set), ZERO))
                self.assertEqual(held, balances.get(account, ZERO), msg=f"{account} after {length} transactions")

    @_SETTINGS
    @given(steps=_histories(_ACCOUNTS), method_name=st.sampled_from(sorted(_METHODS)))
    def test_basis_and_lot_amounts_are_conserved(self, steps: List[_Step], method_name: str) -> None:
        configuration = Configuration(_CONFIGURATION_PATH, US())
        input_data = _create_input_data(configuration, steps)
        result = TransferAnalyzer(configuration, _METHODS[method_name], input_data).analyze_and_pair()

        # Amounts and basis still held, per original lot.
        held_amount: Dict[InTransaction, RP2Decimal] = {}
        held_basis = ZERO
        for per_wallet_input_data in result.wallet_2_input_data.values():
            for entry in per_wallet_input_data.unfiltered_in_transaction_set:
                lot = entry
                assert isinstance(lot, InTransaction)
                amount = per_wallet_input_data.in_transaction_2_actual_amount.get(lot, lot.crypto_in)
                held_amount[lot.original_lot] = held_amount.get(lot.original_lot, ZERO) + amount
                held_basis += lot.fiat_in_with_fee * amount / lot.crypto_in

        disposed_amount: Dict[InTransaction, RP2Decimal] = {}
        disposed_basis = ZERO
        # A taxable event is paired with a given lot at most once (GainLoss.internal_id is "<taxable event id>-><lot id>").
        seen_gain_loss_ids: Set[str] = set()
        for gain_loss in result.gain_loss_list:
            self.assertNotIn(gain_loss.internal_id, seen_gain_loss_ids)
            seen_gain_loss_ids.add(gain_loss.internal_id)
            if gain_loss.acquired_lot is None:
                continue
            original_lot = gain_loss.acquired_lot.original_lot
            disposed_amount[original_lot] = disposed_amount.get(original_lot, ZERO) + gain_loss.crypto_amount
            disposed_basis += gain_loss.fiat_cost_basis

        acquired_basis = RP2Decimal(sum((lot.fiat_in_with_fee for lot in input_data.unfiltered_in_transaction_set), ZERO))  # type: ignore
        self.assertLess(abs(acquired_basis - disposed_basis - held_basis), _TOLERANCE * max(acquired_basis, RP2Decimal("1")))

        # Every unit of every input lot is either still held or disposed of with a gain/loss (transfer fees included: they are disposals).
        for entry in input_data.unfiltered_in_transaction_set:
            lot = entry
            assert isinstance(lot, InTransaction)
            accounted = disposed_amount.get(lot, ZERO) + held_amount.get(lot, ZERO)
            self.assertEqual(accounted, lot.crypto_in, msg=f"lot {lot.internal_id}")

    # R03 from the review of eprbell/rp2#155: the lots allocated at the switch must survive transfers back and forth between wallets. Checks
    # the invariants above on histories that start in 2024 (universal application), get their unused basis allocated to the wallets at the
    # switch, and continue in 2025 (per-wallet application), often sending funds back where they came from.
    # Example of what used to fail: buy 10 units in A in 2024, move 4 A -> B and back in 2025: "returned amount exceeds its crypto_in".
    # R04: the invariants are checked on what the wallets hold at the date of the report (ComputedData.wallet_lots, used by reports), which
    # is often in the middle of the history: the holdings must be the ones at that date, not the final ones.
    # Example: buy in January, sell in May, report up to April: the wallet still holds the January lot.
    @_SETTINGS
    @given(history=_histories_crossing_the_switch(), method_name=st.sampled_from(sorted(_METHODS)))
    def test_invariants_hold_across_the_switch(self, history: _HistoryCrossingTheSwitch, method_name: str) -> None:
        steps, steps_before_switch, report_step = history
        to_date = MAX_DATE if report_step is None else _get_step_timestamp(report_step, steps_before_switch).date()
        configuration = Configuration(_CONFIGURATION_PATH, US(), to_date=to_date)
        input_data = _create_input_data(configuration, steps, steps_before_switch)
        per_wallet_configuration = PerWalletConfiguration(
            timezone_name="UTC", unused_basis_allocation_method="fifo", unused_basis_allocation_wallet_order=tuple(_ACCOUNTS)
        )
        computed_data = compute_tax_per_wallet(
            configuration, _accounting_engine(_METHODS[method_name]), input_data, per_wallet_configuration, AccountingMethodFIFO()
        )
        wallet_lots = computed_data.wallet_lots
        if to_date < _START.date():
            # The report date is before the switch: there are no per-wallet holdings yet (reports use universal application).
            self.assertIsNone(wallet_lots)
            return
        assert wallet_lots is not None
        reported_steps = steps if report_step is None else steps[: report_step + 1]

        # Each wallet holds exactly its balance at the report date, and remember what is held per input lot. Held units keep the acquisition
        # date of their input lot.
        balances = _balances(reported_steps)
        wallet_amounts: Dict[Account, RP2Decimal] = {}
        held_amount: Dict[InTransaction, RP2Decimal] = {}
        held_basis = ZERO
        for wallet_lot in wallet_lots:
            wallet_amounts[wallet_lot.account] = wallet_amounts.get(wallet_lot.account, ZERO) + wallet_lot.amount
            held_amount[wallet_lot.original_lot] = held_amount.get(wallet_lot.original_lot, ZERO) + wallet_lot.amount
            held_basis += wallet_lot.cost_basis
            self.assertEqual(wallet_lot.acquisition_timestamp, wallet_lot.original_lot.timestamp)
        for account in _ACCOUNTS:
            self.assertEqual(wallet_amounts.get(account, ZERO), balances.get(account, ZERO), msg=f"{account}")

        # Every unit of every input lot acquired by the report date is either still held or was disposed of by then (before or after the
        # switch), and so is its basis.
        disposed_amount: Dict[InTransaction, RP2Decimal] = {}
        disposed_basis = ZERO
        for gain_loss in computed_data.gain_loss_set:
            assert isinstance(gain_loss, GainLoss)
            if gain_loss.acquired_lot is None:
                continue
            original_lot = gain_loss.acquired_lot.original_lot
            disposed_amount[original_lot] = disposed_amount.get(original_lot, ZERO) + gain_loss.crypto_amount
            disposed_basis += gain_loss.fiat_cost_basis
        acquired_lots = [lot for lot in input_data.unfiltered_in_transaction_set if isinstance(lot, InTransaction) and lot.timestamp.date() <= to_date]
        for lot in acquired_lots:
            self.assertEqual(disposed_amount.get(lot, ZERO) + held_amount.get(lot, ZERO), lot.crypto_in, msg=f"lot {lot.internal_id}")
        acquired_basis = ZERO
        for lot in acquired_lots:
            acquired_basis += lot.fiat_in_with_fee
        self.assertLess(abs(acquired_basis - disposed_basis - held_basis), _TOLERANCE * max(acquired_basis, RP2Decimal("1")))

    @_SETTINGS
    @given(steps=_histories([_ACCOUNTS[0]]), method_name=st.sampled_from(sorted(_METHODS)))
    def test_single_wallet_per_wallet_equals_universal(self, steps: List[_Step], method_name: str) -> None:
        configuration = Configuration(_CONFIGURATION_PATH, US())
        input_data = _create_input_data(configuration, steps)
        per_wallet_configuration = PerWalletConfiguration(timezone_name="UTC")
        per_wallet = compute_tax_per_wallet(configuration, _accounting_engine(_METHODS[method_name]), input_data, per_wallet_configuration)
        universal = compute_tax(configuration, _accounting_engine(_METHODS[method_name]), input_data)
        per_wallet_gain_losses = [gain_loss for gain_loss in per_wallet.gain_loss_set if isinstance(gain_loss, GainLoss)]
        universal_gain_losses = [gain_loss for gain_loss in universal.gain_loss_set if isinstance(gain_loss, GainLoss)]
        self.assertEqual(_merge_gain_losses(per_wallet_gain_losses), _merge_gain_losses(universal_gain_losses))
        self.assertEqual(
            [(y.year, y.transaction_type, y.is_long_term_capital_gains, y.crypto_amount, y.fiat_gain_loss) for y in per_wallet.yearly_gain_loss_list],
            [(y.year, y.transaction_type, y.is_long_term_capital_gains, y.crypto_amount, y.fiat_gain_loss) for y in universal.yearly_gain_loss_list],
        )

    @_SETTINGS
    @given(steps=_histories(_ACCOUNTS))
    def test_universal_jp_results_are_not_affected_by_per_wallet_code(self, steps: List[_Step]) -> None:
        jp_configuration = Configuration(_CONFIGURATION_PATH, JP())
        input_data = _create_input_data(jp_configuration, steps)
        before = _universal_gain_losses(jp_configuration, input_data)
        # Per-wallet code must refuse to run for JP...
        with self.assertRaisesRegex(RP2ValueError, "not supported for country 'jp'"):
            compute_tax_per_wallet(jp_configuration, _accounting_engine(AccountingMethodFIFO()), input_data, PerWalletConfiguration(timezone_name="Asia/Tokyo"))
        # ... and running it anyway on the same objects (it mutates to_lots of the input lots) must not change universal results.
        TransferAnalyzer(jp_configuration, AccountingMethodFIFO(), input_data).analyze_and_pair()
        self.assertEqual(before, _universal_gain_losses(jp_configuration, input_data))


if __name__ == "__main__":
    unittest.main()

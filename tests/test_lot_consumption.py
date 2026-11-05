# Copyright 2026 eprbell
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

# How universal and per-wallet application take coins from lots (R13 of the review of eprbell/rp2#155): they follow the same rules, the
# shared take_lots() and pair_with_lots() of lot_consumption.py, so they give the same results when they can choose from the same lots, and
# the wallet restriction must change the results when they can't. The tests check the rules themselves, that both applications use them,
# and their results through both applications.

import unittest
from types import ModuleType
from typing import Dict, Iterable, List, NamedTuple, Optional, cast

from per_wallet_common import AbstractPerWalletTest, _create_configuration, _In, _Intra, _Out

import rp2.accounting_engine
import rp2.per_wallet_transactions
import rp2.tax_engine
import rp2.transfer_analyzer
from rp2.abstract_accounting_method import AbstractAccountingMethod, AbstractAcquiredLotCandidates
from rp2.abstract_transaction import AbstractTransaction
from rp2.accounting_engine import AccountingEngine
from rp2.computed_data import ComputedData
from rp2.configuration import Configuration
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.lot_consumption import LotPiece, TakeResult, pair_with_lots, take_lots
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2ValueError
from rp2.tax_engine import compute_tax, compute_tax_per_wallet


# A gain/loss reduced to what the rules decide: the taxable event, the original lot it took coins from, the coins and their cost basis.
class _Pairing(NamedTuple):
    taxable_event: str
    lot: Optional[str]
    crypto_amount: RP2Decimal
    fiat_cost_basis: RP2Decimal


def _pairings(computed_data: ComputedData) -> List[_Pairing]:
    result: List[_Pairing] = []
    for entry in computed_data.gain_loss_set:
        gain_loss = cast(GainLoss, entry)
        lot = gain_loss.acquired_lot
        result.append(
            _Pairing(gain_loss.taxable_event.unique_id, lot.original_lot.unique_id if lot else None, gain_loss.crypto_amount, gain_loss.fiat_cost_basis)
        )
    return sorted(result, key=str)


# Coins left in each input lot. Universal application: what the gain/losses didn't take. Per-wallet application: what the wallets hold.
def _universal_remaining(computed_data: ComputedData) -> Dict[str, RP2Decimal]:
    result: Dict[str, RP2Decimal] = {}
    for entry in computed_data.in_transaction_set:
        lot = cast(InTransaction, entry)
        result[lot.unique_id] = lot.crypto_in
    for entry in computed_data.gain_loss_set:
        gain_loss = cast(GainLoss, entry)
        if gain_loss.acquired_lot is not None:
            unique_id = gain_loss.acquired_lot.original_lot.unique_id
            result[unique_id] = result[unique_id] - gain_loss.crypto_amount
    return result


def _per_wallet_remaining(computed_data: ComputedData) -> Dict[str, RP2Decimal]:
    result: Dict[str, RP2Decimal] = {}
    for entry in computed_data.in_transaction_set:
        result[cast(InTransaction, entry).unique_id] = ZERO
    for wallet_lot in computed_data.wallet_lots or []:
        unique_id = wallet_lot.original_lot.unique_id
        result[unique_id] = result[unique_id] + wallet_lot.amount
    return result


def _get_unique_id(lot: InTransaction) -> str:
    return lot.unique_id


# What the wallets hold at the end, by wallet and original lot ("Coinbase/A": coins).
def _holdings(computed_data: ComputedData) -> Dict[str, RP2Decimal]:
    result: Dict[str, RP2Decimal] = {}
    for wallet_lot in computed_data.wallet_lots or []:
        key = f"{wallet_lot.account.exchange}/{wallet_lot.original_lot.unique_id}"
        result[key] = result.get(key, ZERO) + wallet_lot.amount
    return result


class TestLotConsumption(AbstractPerWalletTest):
    # Replaces take_lots() in module (which imported it) with a spy that counts its calls: the original is put back when the test ends.
    def _spy_take_lots(self, module: ModuleType) -> List[int]:
        calls: List[int] = []

        def spy(accounting_method: AbstractAccountingMethod, lot_candidates: AbstractAcquiredLotCandidates, amount: RP2Decimal) -> TakeResult:
            calls.append(1)
            return take_lots(accounting_method, lot_candidates, amount)

        def restore() -> None:
            setattr(module, "take_lots", take_lots)

        setattr(module, "take_lots", spy)
        self.addCleanup(restore)
        return calls

    # Same as _spy_take_lots(), for pair_with_lots().
    def _spy_pair_with_lots(self, module: ModuleType) -> List[int]:
        calls: List[int] = []

        def spy(configuration: Configuration, taxable_event: AbstractTransaction, pieces: List[LotPiece]) -> List[GainLoss]:
            calls.append(1)
            return pair_with_lots(configuration, taxable_event, pieces)

        def restore() -> None:
            setattr(module, "pair_with_lots", pair_with_lots)

        setattr(module, "pair_with_lots", spy)
        self.addCleanup(restore)
        return calls

    # Lots of one wallet, all in 2025: A (2 coins at $100), B (5 coins at $300) and C (1 coin at $200).
    def _create_lots(self, configuration: Configuration) -> List[InTransaction]:
        input_data = self._create_input_data(
            configuration,
            [
                _In("A", "2025-01-01T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                _In("B", "2025-02-01T00:00:00+00:00", "Coinbase", "Buy", "300", "5"),
                _In("C", "2025-03-01T00:00:00+00:00", "Coinbase", "Buy", "200", "1"),
            ],
        )
        return sorted((cast(InTransaction, lot) for lot in input_data.unfiltered_in_transaction_set), key=_get_unique_id)

    @staticmethod
    def _create_lot_candidates(method: AbstractAccountingMethod, lots: List[InTransaction]) -> AbstractAcquiredLotCandidates:
        result = method.create_lot_candidates(list(lots), {})
        result.set_to_index(len(lots) - 1)
        return result

    # The rules of take_lots(), on FIFO lot candidates of lots A (2 coins), B (5) and C (1).
    def test_take_lots(self) -> None:
        configuration = _create_configuration()
        lot_a, lot_b, lot_c = self._create_lots(configuration)
        fifo = AccountingMethodFIFO()
        lot_candidates = self._create_lot_candidates(fifo, [lot_a, lot_b, lot_c])

        # Partial consumption: 1 coin of A, which keeps the other.
        want: TakeResult = TakeResult([LotPiece(lot_a, RP2Decimal("1"))], ZERO)
        self.assertEqual(take_lots(fifo, lot_candidates, RP2Decimal("1")), want)
        self.assertEqual(lot_candidates.get_partial_amount(lot_a), RP2Decimal("1"))

        # Exhausted lot and multiple lots: the last coin of A (now exhausted), then 2 coins of B, which keeps 3.
        want = TakeResult([LotPiece(lot_a, RP2Decimal("1")), LotPiece(lot_b, RP2Decimal("2"))], ZERO)
        self.assertEqual(take_lots(fifo, lot_candidates, RP2Decimal("3")), want)
        self.assertEqual(lot_candidates.get_partial_amount(lot_a), ZERO)
        self.assertEqual(lot_candidates.get_partial_amount(lot_b), RP2Decimal("3"))

        # Nothing to take: no pieces, nothing missing.
        want = TakeResult([], ZERO)
        self.assertEqual(take_lots(fifo, lot_candidates, ZERO), want)

        # Not enough coins: everything left is taken (3 of B, 1 of C) and the rest is missing.
        want = TakeResult([LotPiece(lot_b, RP2Decimal("3")), LotPiece(lot_c, RP2Decimal("1"))], RP2Decimal("6"))
        self.assertEqual(take_lots(fifo, lot_candidates, RP2Decimal("10")), want)
        want = TakeResult([], RP2Decimal("1"))
        self.assertEqual(take_lots(fifo, lot_candidates, RP2Decimal("1")), want)

    # Coins are compared with RP2Decimal's precision (13 decimals): a lot with 2 coins covers a need of 2.00000000000001 coins, the piece is
    # the amount needed and the lot keeps the difference, which counts as zero.
    def test_take_lots_within_precision(self) -> None:
        configuration = _create_configuration()
        lot_a, lot_b, lot_c = self._create_lots(configuration)
        fifo = AccountingMethodFIFO()
        lot_candidates = self._create_lot_candidates(fifo, [lot_a, lot_b, lot_c])
        pieces, missing_amount = take_lots(fifo, lot_candidates, RP2Decimal("2.00000000000001"))
        # The amounts are compared as text: RP2Decimal's == would also accept the lot's 2 coins.
        got: List[str] = [f"{piece.acquired_lot.unique_id}: {piece.amount}" for piece in pieces]
        want: List[str] = ["A: 2.00000000000001"]
        self.assertEqual(got, want)
        self.assertEqual(missing_amount, ZERO)
        # A is exhausted: the next coin comes from B.
        want_result: TakeResult = TakeResult([LotPiece(lot_b, RP2Decimal("1"))], ZERO)
        self.assertEqual(take_lots(fifo, lot_candidates, RP2Decimal("1")), want_result)

    # The lot candidates are ordered by the method that created them: taking from them with a method of another class is an internal error.
    def test_take_lots_checks_its_parameters(self) -> None:
        configuration = _create_configuration()
        lot_candidates = self._create_lot_candidates(AccountingMethodFIFO(), self._create_lots(configuration))
        with self.assertRaisesRegex(RP2RuntimeError, "lot candidates of fifo used with accounting method hifo"):
            take_lots(AccountingMethodHIFO(), lot_candidates, RP2Decimal("1"))
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'amount' has non-positive value"):
            take_lots(AccountingMethodFIFO(), lot_candidates, RP2Decimal("-1"))

    # The lot pool of universal application, through AccountingEngine.take(): the lots acquired up to the taxable event (including the ones
    # acquired at the same instant), in any wallet, with the coins each one has left, in the order of the accounting method. R14 of the
    # review removes get_acquired_lot_for_timestamp(), which chose lots from the same pool for GlobalAllocator: universal application uses
    # take(), so the pool is checked here. test_tax_dates.py (test_accounting_method_of_the_tax_year) checks the method of each tax year.
    # Example, with LIFO: lots A (Coinbase, January), B (Kraken, March 1st at midnight) and C (Coinbase, June). A sale on Coinbase on March
    # 1st at midnight takes B and then A: B is in another wallet, and it's acquired at the instant of the sale. C is newer than both, but
    # it's acquired after the sale, so it's not in the pool.
    def test_universal_lot_pool(self) -> None:
        configuration = _create_configuration()
        input_data = self._create_input_data(
            configuration,
            [
                _In("A", "2024-01-01T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                _In("B", "2024-03-01T00:00:00+00:00", "Kraken", "Buy", "200", "1"),
                _In("C", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "300", "4"),
                _Out("before", "2023-12-31T00:00:00+00:00", "Coinbase", "400", "1"),
                _Out("o1", "2024-03-01T00:00:00+00:00", "Coinbase", "400", "2"),
                _Out("o2", "2024-03-02T00:00:00+00:00", "Coinbase", "400", "5"),
            ],
        )
        lots: Dict[str, InTransaction] = {}
        for entry in input_data.unfiltered_in_transaction_set:
            lot = cast(InTransaction, entry)
            lots[lot.unique_id] = lot
        sales: Dict[str, AbstractTransaction] = {}
        for entry in input_data.unfiltered_out_transaction_set:
            sale = cast(AbstractTransaction, entry)
            sales[sale.unique_id] = sale

        # A universal application engine with one accounting method, and the coins each lot has left at the start, if given.
        def create_engine(method: AbstractAccountingMethod, lot_2_coins_left: Optional[Dict[InTransaction, RP2Decimal]] = None) -> AccountingEngine:
            engine = self._create_accounting_engine({1970: method})
            engine.initialize(iter(cast(Iterable[InTransaction], input_data.unfiltered_in_transaction_set)), lot_2_coins_left)
            return engine

        engine = create_engine(AccountingMethodLIFO())
        # No lot is acquired before the sale: nothing is taken and all the coins are missing.
        want = TakeResult([], RP2Decimal("1"))
        self.assertEqual(engine.take(sales["before"], RP2Decimal("1")), want)
        # B (acquired at the instant of the sale, in another wallet), then A. C is acquired after the sale.
        want = TakeResult([LotPiece(lots["B"], RP2Decimal("1")), LotPiece(lots["A"], RP2Decimal("1"))], ZERO)
        self.assertEqual(engine.take(sales["o1"], RP2Decimal("2")), want)
        # The coins left carry over to the next sale: B has none and A has 1. C is still acquired after the sale, so 4 coins are missing.
        want = TakeResult([LotPiece(lots["A"], RP2Decimal("1"))], RP2Decimal("4"))
        self.assertEqual(engine.take(sales["o2"], RP2Decimal("5")), want)

        # The coins each lot has left at the start (e.g. InputData.in_transaction_2_actual_amount) are given to initialize(). With FIFO and
        # 0.5 coins left in A, a sale of 2 coins takes those 0.5 coins and B's coin, and 0.5 coins are missing.
        engine = create_engine(AccountingMethodFIFO(), {lots["A"]: RP2Decimal("0.5")})
        want = TakeResult([LotPiece(lots["A"], RP2Decimal("0.5")), LotPiece(lots["B"], RP2Decimal("1"))], RP2Decimal("0.5"))
        self.assertEqual(engine.take(sales["o1"], RP2Decimal("2")), want)

    # Each piece becomes a gain/loss with the piece's coins and lot.
    def test_pair_with_lots(self) -> None:
        configuration = _create_configuration()
        input_data = self._create_input_data(
            configuration,
            [
                _In("A", "2025-01-01T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                _In("B", "2025-02-01T00:00:00+00:00", "Coinbase", "Buy", "300", "5"),
                _Out("o1", "2025-04-01T00:00:00+00:00", "Coinbase", "400", "3"),
            ],
        )
        lot_a, lot_b = sorted((cast(InTransaction, lot) for lot in input_data.unfiltered_in_transaction_set), key=_get_unique_id)
        sale = cast(AbstractTransaction, next(iter(input_data.unfiltered_out_transaction_set)))
        gain_losses = pair_with_lots(configuration, sale, [LotPiece(lot_a, RP2Decimal("2")), LotPiece(lot_b, RP2Decimal("1"))])
        got: List[_Pairing] = [
            _Pairing(
                gain_loss.taxable_event.unique_id,
                gain_loss.acquired_lot.unique_id if gain_loss.acquired_lot else None,
                gain_loss.crypto_amount,
                gain_loss.fiat_cost_basis,
            )
            for gain_loss in gain_losses
        ]
        want: List[_Pairing] = [_Pairing("o1", "A", RP2Decimal("2"), RP2Decimal("200")), _Pairing("o1", "B", RP2Decimal("1"), RP2Decimal("300"))]
        self.assertEqual(got, want)

    # Both applications go through the shared rules: universal application takes lots with take_lots() via AccountingEngine and pairs them
    # with pair_with_lots() in the tax engine, per-wallet application via PerWalletTransactions and TransferAnalyzer.
    def test_both_applications_use_the_shared_rules(self) -> None:
        configuration = _create_configuration()
        transactions: List[object] = [
            _In("A", "2025-01-01T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
            _Out("o1", "2025-04-01T00:00:00+00:00", "Coinbase", "400", "1"),
        ]
        calls: Dict[str, List[int]] = {
            "universal take_lots": self._spy_take_lots(rp2.accounting_engine),
            "universal pair_with_lots": self._spy_pair_with_lots(rp2.tax_engine),
            "per-wallet take_lots": self._spy_take_lots(rp2.per_wallet_transactions),
            "per-wallet pair_with_lots": self._spy_pair_with_lots(rp2.transfer_analyzer),
        }

        compute_tax(configuration, self._create_accounting_engine(None), self._create_input_data(configuration, transactions))
        got: Dict[str, int] = {name: len(call_list) for name, call_list in calls.items()}
        want: Dict[str, int] = {"universal take_lots": 1, "universal pair_with_lots": 1, "per-wallet take_lots": 0, "per-wallet pair_with_lots": 0}
        self.assertEqual(got, want)
        compute_tax_per_wallet(configuration, self._create_accounting_engine(None), self._create_input_data(configuration, transactions))
        got = {name: len(call_list) for name, call_list in calls.items()}
        want = {"universal take_lots": 1, "universal pair_with_lots": 1, "per-wallet take_lots": 1, "per-wallet pair_with_lots": 1}
        self.assertEqual(got, want)

    # When all lots are in one wallet, both applications can choose from the same lots: they must take the same coins with the same basis
    # and leave the same coins in each lot. The history covers partial lots, exhausted lots, multiple lots, fees (of a sale and of a
    # transfer) and a method change (FIFO in 2025, HIFO in 2026).
    def test_same_lots_give_the_same_results(self) -> None:
        configuration = _create_configuration()
        transactions: List[object] = [
            _In("A", "2025-01-01T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
            _In("B", "2025-02-01T00:00:00+00:00", "Coinbase", "Buy", "300", "5"),
            _In("C", "2025-03-01T00:00:00+00:00", "Coinbase", "Buy", "200", "1"),
            # FIFO: 1 coin of A, which keeps 1 (partial lot).
            _Out("o1", "2025-04-01T00:00:00+00:00", "Coinbase", "400", "1"),
            # FIFO: 3 coins plus a 0.5 coin fee: the last coin of A (exhausted) and 2.5 coins of B (multiple lots).
            _Out("o2", "2025-05-01T00:00:00+00:00", "Coinbase", "400", "3", crypto_fee="0.5"),
            # FIFO: a transfer within the wallet with a 0.25 coin fee, paid with 0.25 coin of B.
            _Intra("t1", "2025-06-01T00:00:00+00:00", "Coinbase", "Coinbase", "400", "1", "0.75"),
            # HIFO from 2026: 2 coins of B (the highest price, $300), which keeps 0.25. C ($200) is untouched.
            _Out("o3", "2026-02-01T00:00:00+00:00", "Coinbase", "500", "2"),
        ]
        years_2_methods: Dict[int, AbstractAccountingMethod] = {1970: AccountingMethodFIFO(), 2026: AccountingMethodHIFO()}
        universal = compute_tax(configuration, self._create_accounting_engine(years_2_methods), self._create_input_data(configuration, transactions))
        per_wallet = compute_tax_per_wallet(
            configuration, self._create_accounting_engine(years_2_methods), self._create_input_data(configuration, transactions)
        )

        want_pairings: List[_Pairing] = sorted(
            [
                _Pairing("o1", "A", RP2Decimal("1"), RP2Decimal("100")),
                _Pairing("o2", "A", RP2Decimal("1"), RP2Decimal("100")),
                _Pairing("o2", "B", RP2Decimal("2.5"), RP2Decimal("750")),
                _Pairing("t1", "B", RP2Decimal("0.25"), RP2Decimal("75")),
                _Pairing("o3", "B", RP2Decimal("2"), RP2Decimal("600")),
            ],
            key=str,
        )
        self.assertEqual(_pairings(universal), want_pairings)
        self.assertEqual(_pairings(per_wallet), want_pairings)
        want_remaining: Dict[str, RP2Decimal] = {"A": ZERO, "B": RP2Decimal("0.25"), "C": RP2Decimal("1")}
        self.assertEqual(_universal_remaining(universal), want_remaining)
        self.assertEqual(_per_wallet_remaining(per_wallet), want_remaining)

    # Amounts are compared with RP2Decimal's precision (13 decimals): selling 2.00000000000001 coins from a lot of 2 coins takes the whole
    # sale from the lot. Both applications record the amount sold, 2.00000000000001 coins, exactly (per-wallet application recorded the
    # lot's 2 coins before R13), and leave the next lot untouched.
    def test_same_piece_at_the_precision_boundary(self) -> None:
        configuration = _create_configuration()
        transactions: List[object] = [
            _In("A", "2025-01-01T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
            _In("B", "2025-02-01T00:00:00+00:00", "Coinbase", "Buy", "300", "1"),
            _Out("o1", "2025-04-01T00:00:00+00:00", "Coinbase", "400", "2.00000000000001"),
        ]
        universal = compute_tax(configuration, self._create_accounting_engine(None), self._create_input_data(configuration, transactions))
        per_wallet = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), self._create_input_data(configuration, transactions))
        for computed_data in (universal, per_wallet):
            pairings = _pairings(computed_data)
            got: List[str] = [f"{pairing.taxable_event}/{pairing.lot}: {pairing.crypto_amount}" for pairing in pairings]
            want: List[str] = ["o1/A: 2.00000000000001"]
            self.assertEqual(got, want)
        want_remaining: Dict[str, RP2Decimal] = {"A": ZERO, "B": RP2Decimal("1")}
        self.assertEqual(_per_wallet_remaining(per_wallet), want_remaining)

    # A transfer fee worth less than RP2Decimal's precision (13 decimals) in fiat counts as worth nothing, so the transfer isn't taxable:
    # universal application doesn't pair the fee, and neither does per-wallet application, which still takes the fee coins out of the
    # wallet. Example: a fee of 0.00000001 coins of a token priced at $0.000001 is worth $0.00000000000001. Per-wallet application stopped
    # with "Parameter 'taxable_event' of class IntraTransaction is not taxable" before.
    def test_fee_worth_nothing_is_not_paired(self) -> None:
        configuration = _create_configuration()
        transactions: List[object] = [
            _In("A", "2025-01-01T00:00:00+00:00", "Coinbase", "Buy", "0.000001", "1000"),
            _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "0.000001", "10", "9.99999999"),
        ]
        universal = compute_tax(configuration, self._create_accounting_engine(None), self._create_input_data(configuration, transactions))
        per_wallet = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), self._create_input_data(configuration, transactions))
        no_pairings: List[_Pairing] = []
        self.assertEqual(_pairings(universal), no_pairings)
        self.assertEqual(_pairings(per_wallet), no_pairings)
        # The fee coins are spent: Coinbase sent 10 coins, Kraken received 9.99999999.
        want_holdings: Dict[str, RP2Decimal] = {"Coinbase/A": RP2Decimal("990"), "Kraken/A": RP2Decimal("9.99999999")}
        self.assertEqual(_holdings(per_wallet), want_holdings)

    # Coins that come back to a wallet they were in return to their lot there, which can't end up with more coins than it was acquired
    # with. Each transfer can send up to 0.00000000000005 coins more than the wallet holds (RP2Decimal's precision is 13 decimals): along a
    # round trip the excess adds up, and past the precision the transfer amounts don't add up. That's an input error, which names the
    # transfer (it was reported as an internal error before). Universal application doesn't move lots between wallets, so it accepts the
    # history. Example: buy 1 coin, then send it Coinbase -> Kraken -> BlockFi -> Coinbase, each time 0.00000000000004 coins more than the
    # wallet holds: the lot would get back 1.00000000000008 coins.
    def test_round_trip_beyond_precision_is_an_input_error(self) -> None:
        configuration = _create_configuration()
        transactions: List[object] = [
            _In("X", "2025-01-01T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
            _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "100", "1.00000000000004", "1.00000000000004"),
            _Intra("t2", "2025-03-01T00:00:00+00:00", "Kraken", "BlockFi", "100", "1.00000000000008", "1.00000000000008"),
            _Intra("t3", "2025-04-01T00:00:00+00:00", "BlockFi", "Coinbase", "100", "1.00000000000012", "1.00000000000012"),
        ]
        with self.assertRaisesRegex(
            RP2ValueError,
            r"^Transfer t3 returns 1\.00000000000012 B1 to lot X of Coinbase/Bob, which would then hold 1\.00000000000008 B1: more than the 1 B1 it was",
        ):
            compute_tax_per_wallet(configuration, self._create_accounting_engine(None), self._create_input_data(configuration, transactions))
        universal = compute_tax(configuration, self._create_accounting_engine(None), self._create_input_data(configuration, transactions))
        no_pairings: List[_Pairing] = []
        self.assertEqual(_pairings(universal), no_pairings)

    # When the lots are in different wallets, per-wallet application can only take the lots of the wallet that sells or sends, so the
    # results differ from universal application, which takes from any wallet.
    def test_wallet_restriction_changes_the_results(self) -> None:
        configuration = _create_configuration()
        years_2_methods: Dict[int, AbstractAccountingMethod] = {1970: AccountingMethodFIFO(), 2026: AccountingMethodHIFO()}

        class _Case(NamedTuple):
            description: str
            transactions: List[object]
            want_universal: List[_Pairing]
            want_per_wallet: List[_Pairing]
            want_holdings: Dict[str, RP2Decimal]

        cases: List[_Case] = [
            _Case(
                # FIFO: universal application sells A, the oldest lot of all; per-wallet application sells B, the only lot Kraken holds.
                description="A sale",
                transactions=[
                    _In("A", "2025-01-01T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _In("B", "2025-02-01T00:00:00+00:00", "Kraken", "Buy", "300", "1"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "400", "1"),
                ],
                want_universal=[_Pairing("o1", "A", RP2Decimal("1"), RP2Decimal("100"))],
                want_per_wallet=[_Pairing("o1", "B", RP2Decimal("1"), RP2Decimal("300"))],
                want_holdings={"Coinbase/A": RP2Decimal("1")},
            ),
            _Case(
                # HIFO in 2026: the fee of a transfer from Kraken is paid with A ($300, in Coinbase) in universal application and with B
                # ($100, the only lot Kraken holds) in per-wallet application, where the rest of B's coin goes to Coinbase.
                description="A transfer fee after a method change",
                transactions=[
                    _In("A", "2025-01-01T00:00:00+00:00", "Coinbase", "Buy", "300", "1"),
                    _In("B", "2025-02-01T00:00:00+00:00", "Kraken", "Buy", "100", "1"),
                    _Intra("t1", "2026-01-10T00:00:00+00:00", "Kraken", "Coinbase", "400", "1", "0.9"),
                ],
                want_universal=[_Pairing("t1", "A", RP2Decimal("0.1"), RP2Decimal("30"))],
                want_per_wallet=[_Pairing("t1", "B", RP2Decimal("0.1"), RP2Decimal("10"))],
                want_holdings={"Coinbase/A": RP2Decimal("1"), "Coinbase/B": RP2Decimal("0.9")},
            ),
        ]
        for case in cases:
            with self.subTest(case=case.description):
                universal = compute_tax(
                    configuration, self._create_accounting_engine(years_2_methods), self._create_input_data(configuration, case.transactions)
                )
                per_wallet = compute_tax_per_wallet(
                    configuration, self._create_accounting_engine(years_2_methods), self._create_input_data(configuration, case.transactions)
                )
                self.assertEqual(_pairings(universal), case.want_universal)
                self.assertEqual(_pairings(per_wallet), case.want_per_wallet)
                self.assertEqual(_holdings(per_wallet), case.want_holdings)

    # A negative STAKING amount is not supported (R18 of the review): universal application reports the amount, whatever the accounting
    # method. Before, methods that select the STAKING lot first (e.g. LIFO) reported "Total in-transaction crypto value < total taxable crypto
    # value" instead. The history is the example of R18: ten coins bought, then a STAKING of minus one coin.
    def test_negative_staking_is_reported_with_every_method(self) -> None:
        configuration = _create_configuration()
        transactions: List[object] = [
            _In("i1", "2024-01-01T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
            _In("s1", "2024-02-01T00:00:00+00:00", "Coinbase", "Staking", "100", "-1"),
        ]
        methods: List[AbstractAccountingMethod] = [AccountingMethodFIFO(), AccountingMethodLIFO(), AccountingMethodHIFO(), AccountingMethodLOFO()]
        for method in methods:
            with self.subTest(method=method.name):
                with self.assertRaisesRegex(RP2ValueError, "Parameter 'taxable_event_amount' has non-positive value -1"):
                    compute_tax(configuration, self._create_accounting_engine({1970: method}), self._create_input_data(configuration, transactions))


if __name__ == "__main__":
    unittest.main()

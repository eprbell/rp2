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

# How universal and per-wallet application take coins from lots (R13 of the review of eprbell/rp2#155): they must follow the same rules, so
# they give the same results when they can choose from the same lots, and the wallet restriction must change the results when they can't.

import unittest
from typing import Dict, List, NamedTuple, Optional, cast

from per_wallet_common import AbstractPerWalletTest, _create_configuration, _In, _Intra, _Out

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.computed_data import ComputedData
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2ValueError
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


# What the wallets hold at the end, by wallet and original lot ("Coinbase/A": coins).
def _holdings(computed_data: ComputedData) -> Dict[str, RP2Decimal]:
    result: Dict[str, RP2Decimal] = {}
    for wallet_lot in computed_data.wallet_lots or []:
        key = f"{wallet_lot.account.exchange}/{wallet_lot.original_lot.unique_id}"
        result[key] = result.get(key, ZERO) + wallet_lot.amount
    return result


class TestLotConsumption(AbstractPerWalletTest):
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

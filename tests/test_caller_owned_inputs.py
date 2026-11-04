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

# Objects that receive a list, dictionary or map from their caller keep a private copy: changing the caller's object afterwards must not change
# them (R13). Each test changes the caller's object after construction and checks that the behavior doesn't change. They also check that
# public inputs are type-checked at construction.

import unittest
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, cast

from per_wallet_common import AbstractPerWalletTest, _create_configuration, _In, _Out
from prezzemolo.avl_tree import AVLTree

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.account import Account
from rp2.accounting_engine import AccountingEngine
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.opening_allocation import OpeningAllocation, UnusedLot
from rp2.per_wallet_configuration import PerWalletConfiguration
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2TypeError, RP2ValueError
from rp2.tax_engine import compute_tax
from rp2.unused_basis_allocator import UnusedBasisAllocator

_KRAKEN = Account("Kraken", "Bob")
_COINBASE = Account("Coinbase", "Bob")


class TestCallerOwnedInputs(AbstractPerWalletTest):
    # PerWalletConfiguration is a frozen dataclass, but frozen only prevents assigning its fields: before R13 a caller could still change the
    # dictionaries it passed, and the configuration changed with them, skipping its checks.
    def test_per_wallet_configuration_keeps_its_own_copies(self) -> None:
        method_overrides = {"BTC": "hifo"}
        wallet_order = [_KRAKEN, _COINBASE]
        order_overrides = {"BTC": [_COINBASE, _KRAKEN]}
        configuration = PerWalletConfiguration(
            "UTC", "fifo", cast(Tuple[Account, ...], wallet_order), method_overrides, cast(Dict[str, Tuple[Account, ...]], order_overrides)
        )

        method_overrides["BTC"] = "lifo"
        method_overrides["ETH"] = ""
        wallet_order.reverse()
        order_overrides["BTC"].append(Account("BlockFi", "Bob"))

        self.assertEqual(configuration.get_unused_basis_allocation_method("BTC"), "hifo")
        self.assertEqual(configuration.get_unused_basis_allocation_method("ETH"), "fifo")
        self.assertEqual(configuration.unused_basis_allocation_wallet_order, (_KRAKEN, _COINBASE))
        self.assertEqual(configuration.get_unused_basis_allocation_wallet_order("BTC"), (_COINBASE, _KRAKEN))
        # The maps are read-only views.
        with self.assertRaises(TypeError):
            cast(Dict[str, str], configuration.asset_2_unused_basis_allocation_method)["BTC"] = "lofo"
        # Copies don't change equality.
        self.assertEqual(configuration, PerWalletConfiguration("UTC", "fifo", (_KRAKEN, _COINBASE), {"BTC": "hifo"}, {"BTC": (_COINBASE, _KRAKEN)}))

    def test_per_wallet_configuration_checks_its_inputs(self) -> None:
        with self.assertRaisesRegex(RP2ValueError, "must be the name of an accounting method"):
            PerWalletConfiguration("UTC", cast(str, 1), (_KRAKEN,))
        with self.assertRaisesRegex(RP2ValueError, r"'unused_basis_allocation_method\.BTC' must be the name of an accounting method"):
            PerWalletConfiguration("UTC", "fifo", (_KRAKEN,), {"BTC": " "})
        with self.assertRaisesRegex(RP2TypeError, "is not a mapping"):
            PerWalletConfiguration("UTC", "fifo", (_KRAKEN,), cast(Dict[str, str], [("BTC", "hifo")]))
        with self.assertRaisesRegex(RP2TypeError, "invalid asset name"):
            PerWalletConfiguration("UTC", "fifo", (_KRAKEN,), {cast(str, 1): "hifo"})
        with self.assertRaisesRegex(RP2TypeError, "not a sequence of wallets"):
            PerWalletConfiguration("UTC", "fifo", cast(Tuple[Account, ...], "Kraken/Bob"))
        with self.assertRaisesRegex(RP2TypeError, "non-Account element"):
            PerWalletConfiguration("UTC", "fifo", cast(Tuple[Account, ...], ("Kraken/Bob",)))
        with self.assertRaisesRegex(RP2ValueError, "duplicates"):
            PerWalletConfiguration("UTC", "fifo", (_KRAKEN,), asset_2_unused_basis_allocation_wallet_order={"BTC": (_KRAKEN, _KRAKEN)})

    def test_account_checks_its_fields(self) -> None:
        self.assertEqual(Account("Kraken", "Bob").exchange, "Kraken")
        with self.assertRaisesRegex(RP2TypeError, "'exchange' of Account is not a string"):
            Account(cast(str, 1), "Bob")
        with self.assertRaisesRegex(RP2ValueError, "'holder' of Account is empty"):
            Account("Kraken", " ")
        with self.assertRaisesRegex(RP2TypeError, "is not of type Account"):
            Account.type_check("wallet", cast(Account, "Kraken/Bob"))

    # In per-wallet input data, in_transaction_2_actual_amount says how much of a lot is still in the wallet. Before R13, InputData kept the
    # caller's dictionary and compute_tax() updated it while pairing lots: computing twice gave different results. Example: lot i1 of 10 coins
    # with 4 left; selling 3 leaves 1 in the engine's copy, and the input data must still say 4.
    def test_input_data_actual_amounts_are_a_private_copy(self) -> None:
        configuration = _create_configuration()
        input_data = self._create_input_data(
            configuration,
            [
                _In("i1", "2024-01-01T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                _In("i2", "2024-02-01T00:00:00+00:00", "Coinbase", "Buy", "200", "10"),
                _Out("o1", "2024-03-01T00:00:00+00:00", "Coinbase", "300", "3"),
            ],
        )
        i1 = cast(InTransaction, next(iter(input_data.unfiltered_in_transaction_set)))
        actual_amounts = {i1: RP2Decimal("4")}
        per_wallet_input_data = InputData(
            input_data.asset,
            input_data.unfiltered_in_transaction_set,
            input_data.unfiltered_out_transaction_set,
            input_data.unfiltered_intra_transaction_set,
            in_transaction_2_actual_amount=actual_amounts,
        )
        actual_amounts[i1] = RP2Decimal("0")
        want_actual_amounts: Dict[InTransaction, RP2Decimal] = {i1: RP2Decimal("4")}
        actual_amounts_after: Dict[InTransaction, RP2Decimal] = dict(per_wallet_input_data.in_transaction_2_actual_amount.items())
        self.assertEqual(actual_amounts_after, want_actual_amounts)
        with self.assertRaises(TypeError):
            cast(Dict[InTransaction, RP2Decimal], per_wallet_input_data.in_transaction_2_actual_amount)[i1] = RP2Decimal("1")

        # FIFO: the sale takes the 3 coins from the 4 left in i1, twice in a row.
        for _ in range(2):
            gain_losses = list(compute_tax(configuration, self._create_accounting_engine(None), per_wallet_input_data).gain_loss_set)
            pairings: List[Tuple[Optional[InTransaction], RP2Decimal]] = [
                (cast(GainLoss, gain_loss).acquired_lot, cast(GainLoss, gain_loss).crypto_amount) for gain_loss in gain_losses
            ]
            want_pairings: List[Tuple[Optional[InTransaction], RP2Decimal]] = [(i1, RP2Decimal("3"))]
            self.assertEqual(pairings, want_pairings)
            actual_amounts_after = dict(per_wallet_input_data.in_transaction_2_actual_amount.items())
            self.assertEqual(actual_amounts_after, want_actual_amounts)

        with self.assertRaisesRegex(RP2TypeError, "is not a mapping"):
            InputData(
                input_data.asset,
                input_data.unfiltered_in_transaction_set,
                input_data.unfiltered_out_transaction_set,
                input_data.unfiltered_intra_transaction_set,
                in_transaction_2_actual_amount=cast(Dict[InTransaction, RP2Decimal], [(i1, RP2Decimal("4"))]),
            )
        with self.assertRaisesRegex(RP2ValueError, "non-positive value"):
            InputData(
                input_data.asset,
                input_data.unfiltered_in_transaction_set,
                input_data.unfiltered_out_transaction_set,
                input_data.unfiltered_intra_transaction_set,
                in_transaction_2_actual_amount={i1: RP2Decimal("-1")},
            )

    # The accounting engine keeps a copy of the year-to-method map: inserting a year in the caller's map, or in the map returned by
    # years_2_methods, doesn't change the methods it uses.
    def test_accounting_engine_keeps_its_own_method_map(self) -> None:
        years_2_methods: AVLTree[int, AbstractAccountingMethod] = AVLTree()
        years_2_methods.insert_node(2024, AccountingMethodFIFO())
        engine = AccountingEngine(years_2_methods)
        years_2_methods.insert_node(2025, AccountingMethodHIFO())
        engine.years_2_methods.insert_node(2026, AccountingMethodLIFO())
        method_2027 = engine.years_2_methods.find_max_value_less_than(2027)
        self.assertIsNotNone(method_2027)
        self.assertEqual(cast(AbstractAccountingMethod, method_2027).name, "fifo")
        with self.assertRaisesRegex(RP2RuntimeError, "no accounting method defined"):
            AccountingEngine(AVLTree())

    # The allocator copies its lists and balances.
    def test_unused_basis_allocator_keeps_its_own_copies(self) -> None:
        configuration = _create_configuration()
        input_data = self._create_input_data(configuration, [_In("i1", "2024-01-01T00:00:00+00:00", "Kraken", "Buy", "100", "2")])
        i1 = cast(InTransaction, next(iter(input_data.unfiltered_in_transaction_set)))
        unused_lots: List[UnusedLot] = [UnusedLot(i1, RP2Decimal("2"))]
        balances: Dict[Account, RP2Decimal] = {_KRAKEN: RP2Decimal("2")}
        wallet_order = [_KRAKEN]
        allocator = UnusedBasisAllocator(
            configuration, input_data.asset, datetime(2025, 1, 1, tzinfo=timezone.utc), unused_lots, balances, AccountingMethodFIFO(), wallet_order
        )
        unused_lots.clear()
        balances[_KRAKEN] = RP2Decimal("5")
        wallet_order.clear()
        opening_allocation = allocator.allocate()
        self.assertIsInstance(opening_allocation, OpeningAllocation)
        allocated_lots = cast(OpeningAllocation, opening_allocation).allocated_lots
        exchanges_and_amounts: List[Tuple[str, RP2Decimal]] = [(lot.exchange, lot.crypto_in) for lot in allocated_lots]
        want_exchanges_and_amounts: List[Tuple[str, RP2Decimal]] = [("Kraken", RP2Decimal("2"))]
        self.assertEqual(exchanges_and_amounts, want_exchanges_and_amounts)
        with self.assertRaisesRegex(RP2TypeError, "is not of type Account"):
            UnusedBasisAllocator(
                configuration,
                input_data.asset,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                [],
                {cast(Account, "Kraken/Bob"): RP2Decimal("2")},
                None,
                [],
            )


if __name__ == "__main__":
    unittest.main()

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

# PerWalletTransactions, the lots and transactions of one wallet during transfer analysis (R13): it identifies accounting methods by name, not
# by object identity, and it doesn't hand out its internal collections.

import unittest
from typing import Dict, List, NamedTuple, cast

from per_wallet_common import AbstractPerWalletTest, _create_configuration, _In, _Out

from rp2.abstract_accounting_method import AbstractFeatureBasedAccountingMethod, AcquiredLotSortKey
from rp2.acquisition_date_fifo import AcquisitionDateFifo
from rp2.in_transaction import InTransaction
from rp2.lot_consumption import LotPiece
from rp2.out_transaction import OutTransaction
from rp2.per_wallet_transactions import PerWalletTransactions
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2TypeError, RP2ValueError


# Two feature-based methods with the same name and different lot orders.
class _NewestFirst(AbstractFeatureBasedAccountingMethod):
    def sort_key(self, lot: InTransaction) -> AcquiredLotSortKey:
        return AcquiredLotSortKey(ZERO, -lot.timestamp.timestamp(), -lot.row)

    @property
    def name(self) -> str:
        return "by_date"


class _OldestFirst(AbstractFeatureBasedAccountingMethod):
    def sort_key(self, lot: InTransaction) -> AcquiredLotSortKey:
        return AcquiredLotSortKey(ZERO, lot.timestamp.timestamp(), lot.row)

    @property
    def name(self) -> str:
        return "by_date"


# A wallet with lots i1 (10 coins at $100) and i2 (10 coins at $300), and a sale o1 of 3 coins not yet added to the wallet.
class _Wallet(NamedTuple):
    wallet: PerWalletTransactions
    lots: List[InTransaction]
    out_transaction: OutTransaction


class TestPerWalletTransactions(AbstractPerWalletTest):
    def _create(self) -> _Wallet:
        configuration = _create_configuration()
        input_data = self._create_input_data(
            configuration,
            [
                _In("i1", "2024-01-01T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                _In("i2", "2024-02-01T00:00:00+00:00", "Coinbase", "Buy", "300", "10"),
                _Out("o1", "2024-03-01T00:00:00+00:00", "Coinbase", "400", "3"),
            ],
        )
        lots = [cast(InTransaction, lot) for lot in input_data.unfiltered_in_transaction_set]
        out_transaction = cast(OutTransaction, next(iter(input_data.unfiltered_out_transaction_set)))
        wallet = PerWalletTransactions(configuration, "B1", [AcquisitionDateFifo(), AccountingMethodHIFO()])
        for lot in lots:
            wallet.add_acquired_lot(lot)
        return _Wallet(wallet, lots, out_transaction)

    # Before R13 the lot candidates were keyed by the method object: taking funds with another object of the same method failed (KeyError).
    # Example: the wallet was created with one HIFO object, and a sale used a new one.
    def test_methods_are_identified_by_name(self) -> None:
        wallet, lots, _ = self._create()
        pieces, missing_amount = wallet.take(AccountingMethodHIFO(), RP2Decimal("3"))
        self.assertEqual(missing_amount, ZERO)
        want: List[LotPiece] = [LotPiece(lots[1], RP2Decimal("3"))]
        self.assertEqual(pieces, want)
        # Per-wallet FIFO and HIFO share the amounts left in each lot: FIFO now takes from i1, untouched, then from what's left of i2.
        pieces, _ = wallet.take(AcquisitionDateFifo(), RP2Decimal("11"))
        want = [LotPiece(lots[0], RP2Decimal("10")), LotPiece(lots[1], RP2Decimal("1"))]
        self.assertEqual(pieces, want)

    # A method with the same name but a different class orders lots differently: it's rejected rather than given the other method's lots.
    def test_same_name_different_class_is_rejected(self) -> None:
        configuration = _create_configuration()
        wallet = PerWalletTransactions(configuration, "B1", [_NewestFirst()])
        with self.assertRaisesRegex(RP2RuntimeError, "was not given to PerWalletTransactions"):
            wallet.take(_OldestFirst(), RP2Decimal("1"))
        with self.assertRaisesRegex(RP2ValueError, "two methods named"):
            PerWalletTransactions(configuration, "B1", [_NewestFirst(), _OldestFirst()])
        with self.assertRaisesRegex(RP2ValueError, "is empty"):
            PerWalletTransactions(configuration, "B1", [])
        with self.assertRaisesRegex(RP2TypeError, "not feature-based"):
            PerWalletTransactions(configuration, "B1", [cast(AbstractFeatureBasedAccountingMethod, object())])

    # The wallet's collections change only through its methods: what it returns are copies, read-only views or snapshots.
    def test_collections_are_not_exposed(self) -> None:
        wallet, lots, out_transaction = self._create()
        wallet.add_out_transaction(out_transaction)
        wallet.take(AcquisitionDateFifo(), RP2Decimal("3"))
        snapshot = wallet.to_input_data()

        lot_list = wallet.acquired_lot_list
        self.assertIsInstance(lot_list, tuple)
        with self.assertRaises(TypeError):
            cast(Dict[InTransaction, RP2Decimal], wallet.acquired_lot_2_actual_amount)[lots[0]] = RP2Decimal("10")

        # Later changes to the wallet don't change the snapshot.
        wallet.take(AcquisitionDateFifo(), RP2Decimal("7"))
        wallet.restore_actual_amount(lots[0], RP2Decimal("5"))
        want_amounts: Dict[InTransaction, RP2Decimal] = {lots[0]: RP2Decimal("7")}
        got_amounts: Dict[InTransaction, RP2Decimal] = dict(snapshot.in_transaction_2_actual_amount.items())
        self.assertEqual(got_amounts, want_amounts)
        self.assertEqual(len(list(snapshot.unfiltered_out_transaction_set)), 1)
        self.assertEqual(wallet.get_actual_amount(lots[0]), RP2Decimal("5"))

        with self.assertRaisesRegex(RP2TypeError, "is not an OutTransaction of B1"):
            wallet.add_out_transaction(cast(OutTransaction, lots[0]))


if __name__ == "__main__":
    unittest.main()

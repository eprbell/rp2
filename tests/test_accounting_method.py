# Copyright 2024 eprbell
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

import unittest

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.configuration import Configuration
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.in_transaction import InTransaction


@dataclass(frozen=True, eq=True)
class SeekLotResult:
    amount: int
    row: int


@dataclass(frozen=True, eq=True)
class InTransactionSpec:
    spot_price: int
    amount: int


class TestAccountingMethod(unittest.TestCase):
    _configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        TestAccountingMethod._configuration = Configuration("./config/test_data.ini", US())

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def _initialize_acquired_lots(self, in_transaction_spec_list: List[InTransactionSpec]) -> List[InTransaction]:
        date = datetime.strptime("2021-01-01", "%Y-%m-%d")
        in_transactions: List[InTransaction] = []
        for i, in_transaction_spec in enumerate(in_transaction_spec_list):
            in_transactions.append(
                InTransaction(
                    self._configuration,
                    f"{date.isoformat()}Z",
                    "B1",
                    "Coinbase",
                    "Bob",
                    "Buy",
                    RP2Decimal(in_transaction_spec.spot_price),
                    RP2Decimal(in_transaction_spec.amount),
                    row=1 + i,
                )
            )
            date += timedelta(days=1)
        return in_transactions

    # This function adds all acquired lots at first and then does amount pairings.
    def _test_fixed_lot_candidates(
        self, lot_selection_method: AbstractAccountingMethod, in_transactions: List[InTransaction], amounts_to_match: List[int], want: List[SeekLotResult]
    ) -> None:
        acquired_lot_candidates = lot_selection_method.create_lot_candidates(in_transactions, {})
        acquired_lot_candidates.set_to_index(len(in_transactions) - 1)
        print(in_transactions)
        i = 0
        for int_amount in amounts_to_match:
            amount = RP2Decimal(int_amount)
            while True:
                result = lot_selection_method.seek_non_exhausted_acquired_lot(acquired_lot_candidates, amount)
                if result is None:
                    break
                if result.amount >= amount:
                    acquired_lot_candidates.set_partial_amount(result.acquired_lot, result.amount - amount)
                    print(i, want[i], amount, result)
                    self.assertEqual(result.amount, RP2Decimal(want[i].amount))
                    self.assertEqual(result.acquired_lot.row, want[i].row)
                    i += 1
                    break
                acquired_lot_candidates.clear_partial_amount(result.acquired_lot)
                amount -= result.amount
                print(i, want[i], amount, result)
                self.assertEqual(result.amount, RP2Decimal(want[i].amount))
                self.assertEqual(result.acquired_lot.row, want[i].row)
                i += 1

    # This function grows lot_candidates dynamically: it adds an acquired lot, does an amount pairing and repeats.
    def _test_dynamic_lot_candidates(
        self, lot_selection_method: AbstractAccountingMethod, in_transactions: List[InTransaction], amounts_to_match: List[int], want: List[SeekLotResult]
    ) -> None:
        acquired_lot_candidates = lot_selection_method.create_lot_candidates([], {})
        i = 0
        for int_amount in amounts_to_match:
            amount = RP2Decimal(int_amount)
            while True:
                if i < len(in_transactions):
                    acquired_lot_candidates.add_acquired_lot(in_transactions[i])
                    acquired_lot_candidates.set_to_index(i)
                result = lot_selection_method.seek_non_exhausted_acquired_lot(acquired_lot_candidates, amount)
                if result is None:
                    break
                if result.amount >= amount:
                    acquired_lot_candidates.set_partial_amount(result.acquired_lot, result.amount - amount)
                    print(i, want[i], amount, result)
                    self.assertEqual(result.amount, RP2Decimal(want[i].amount))
                    self.assertEqual(result.acquired_lot.row, want[i].row)
                    i += 1
                    break
                acquired_lot_candidates.clear_partial_amount(result.acquired_lot)
                amount -= result.amount
                print(i, want[i], amount, result)
                self.assertEqual(result.amount, RP2Decimal(want[i].amount))
                self.assertEqual(result.acquired_lot.row, want[i].row)
                i += 1

    def test_lot_candidates_with_fifo(self) -> None:
        lot_selection_method = AccountingMethodFIFO()

        # Simple test.
        self._test_fixed_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(10, 10), InTransactionSpec(11, 20), InTransactionSpec(12, 30)]),
            amounts_to_match=[6, 4, 2, 18, 3],
            want=[SeekLotResult(10, 1), SeekLotResult(4, 1), SeekLotResult(20, 2), SeekLotResult(18, 2), SeekLotResult(30, 3)],
        )

        # Test with requested amount greater than acquired lot.
        self._test_fixed_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(10, 10), InTransactionSpec(11, 20), InTransactionSpec(12, 30)]),
            amounts_to_match=[15, 10, 5],
            want=[SeekLotResult(10, 1), SeekLotResult(20, 2), SeekLotResult(15, 2), SeekLotResult(5, 2)],
        )

        # Test with dynamic lot candidates
        self._test_dynamic_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(10, 10), InTransactionSpec(11, 20), InTransactionSpec(12, 30)]),
            amounts_to_match=[6, 4, 2, 18, 3],
            want=[SeekLotResult(10, 1), SeekLotResult(4, 1), SeekLotResult(20, 2), SeekLotResult(18, 2), SeekLotResult(30, 3)],
        )

    def test_lot_candidates_with_lifo(self) -> None:
        lot_selection_method = AccountingMethodLIFO()

        # Simple test.
        self._test_fixed_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(10, 10), InTransactionSpec(11, 20), InTransactionSpec(12, 30)]),
            amounts_to_match=[7, 23, 19, 1, 9],
            want=[SeekLotResult(30, 3), SeekLotResult(23, 3), SeekLotResult(20, 2), SeekLotResult(1, 2), SeekLotResult(10, 1)],
        )

        # Test with requested amount greater than acquired lot.
        self._test_fixed_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(10, 10), InTransactionSpec(11, 20), InTransactionSpec(12, 30)]),
            amounts_to_match=[55, 5],
            want=[SeekLotResult(30, 3), SeekLotResult(20, 2), SeekLotResult(10, 1), SeekLotResult(5, 1)],
        )

        # Test with dynamic lot candidates
        self._test_dynamic_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(10, 10), InTransactionSpec(11, 20), InTransactionSpec(12, 30)]),
            amounts_to_match=[4, 15, 27, 14],
            want=[SeekLotResult(10, 1), SeekLotResult(20, 2), SeekLotResult(30, 3), SeekLotResult(3, 3), SeekLotResult(5, 2), SeekLotResult(6, 1)],
        )

    def test_fixed_lot_candidates_with_hifo(self) -> None:
        lot_selection_method = AccountingMethodHIFO()

        # Simple test.
        self._test_fixed_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(10, 10), InTransactionSpec(12, 20), InTransactionSpec(11, 30)]),
            amounts_to_match=[15, 5, 20, 10, 7],
            want=[SeekLotResult(20, 2), SeekLotResult(5, 2), SeekLotResult(30, 3), SeekLotResult(10, 3), SeekLotResult(10, 1)],
        )

        # Test with requested amount greater than acquired lot.
        self._test_fixed_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(10, 10), InTransactionSpec(12, 20), InTransactionSpec(11, 30)]),
            amounts_to_match=[15, 5, 35, 5],
            want=[SeekLotResult(20, 2), SeekLotResult(5, 2), SeekLotResult(30, 3), SeekLotResult(10, 1), SeekLotResult(5, 1)],
        )

        # Test with dynamic lot candidates
        self._test_dynamic_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(10, 10), InTransactionSpec(12, 20), InTransactionSpec(11, 30)]),
            amounts_to_match=[4, 16, 40],
            want=[SeekLotResult(10, 1), SeekLotResult(20, 2), SeekLotResult(4, 2), SeekLotResult(30, 3), SeekLotResult(6, 1)],
        )

    def test_fixed_lot_candidates_with_lofo(self) -> None:
        lot_selection_method = AccountingMethodLOFO()

        # Simple test.
        self._test_fixed_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(12, 10), InTransactionSpec(10, 20), InTransactionSpec(11, 30)]),
            amounts_to_match=[15, 5, 20, 10, 7],
            want=[SeekLotResult(20, 2), SeekLotResult(5, 2), SeekLotResult(30, 3), SeekLotResult(10, 3), SeekLotResult(10, 1)],
        )

        # Test with requested amount greater than acquired lot.
        self._test_fixed_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(12, 10), InTransactionSpec(10, 20), InTransactionSpec(11, 30)]),
            amounts_to_match=[15, 5, 35, 5],
            want=[SeekLotResult(20, 2), SeekLotResult(5, 2), SeekLotResult(30, 3), SeekLotResult(10, 1), SeekLotResult(5, 1)],
        )

        # Test with dynamic lot candidates
        self._test_dynamic_lot_candidates(
            lot_selection_method=lot_selection_method,
            in_transactions=self._initialize_acquired_lots([InTransactionSpec(12, 10), InTransactionSpec(10, 20), InTransactionSpec(11, 30)]),
            amounts_to_match=[4, 16, 40],
            want=[SeekLotResult(10, 1), SeekLotResult(20, 2), SeekLotResult(4, 2), SeekLotResult(30, 3), SeekLotResult(6, 1)],
        )


if __name__ == "__main__":
    unittest.main()

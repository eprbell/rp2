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
class InTransactionDescriptor:
    spot_price: int
    amount: int

@dataclass(frozen=True, eq=True)
class _Test:
    description: str
    lot_selection_method: AbstractAccountingMethod
    in_transactions: List[InTransactionDescriptor]
    amounts_to_match: List[int]
    want: List[SeekLotResult]


class TestAccountingMethod(unittest.TestCase):
    _configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        TestAccountingMethod._configuration = Configuration("./config/test_data.ini", US())

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def _initialize_acquired_lots(self, in_transaction_descriptors: List[InTransactionDescriptor]) -> List[InTransaction]:
        date = datetime.strptime("2021-01-01", "%Y-%m-%d")
        in_transactions: List[InTransaction] = []
        for i, in_transaction_descriptor in enumerate(in_transaction_descriptors):
            in_transactions.append(
                InTransaction(
                    self._configuration,
                    f"{date.isoformat()}Z",
                    "B1",
                    "Coinbase",
                    "Bob",
                    "Buy",
                    RP2Decimal(in_transaction_descriptor.spot_price),
                    RP2Decimal(in_transaction_descriptor.amount),
                    row=1 + i,
                )
            )
            date += timedelta(days=1)
        return in_transactions

    # This function adds all acquired lots at first and then does amount pairings.
    def _run_test_fixed_lot_candidates(self, lot_selection_method: AbstractAccountingMethod, test: _Test) -> None:
        print(f"\nDescription: {test.description:}")
        in_transactions = self._initialize_acquired_lots(test.in_transactions)
        acquired_lot_candidates = lot_selection_method.create_lot_candidates(in_transactions, {})
        acquired_lot_candidates.set_to_index(len(in_transactions) - 1)
        i = 0
        for int_amount in test.amounts_to_match:
            amount = RP2Decimal(int_amount)
            while True:
                result = lot_selection_method.seek_non_exhausted_acquired_lot(acquired_lot_candidates, amount)
                if result is None:
                    break
                if result.amount >= amount:
                    acquired_lot_candidates.set_partial_amount(result.acquired_lot, result.amount - amount)
                    self.assertEqual(result.amount, RP2Decimal(test.want[i].amount))
                    self.assertEqual(result.acquired_lot.row, test.want[i].row)
                    i += 1
                    break
                acquired_lot_candidates.clear_partial_amount(result.acquired_lot)
                amount -= result.amount
                self.assertEqual(result.amount, RP2Decimal(test.want[i].amount))
                self.assertEqual(result.acquired_lot.row, test.want[i].row)
                i += 1

    # This function grows lot_candidates dynamically: it adds an acquired lot, does an amount pairing and repeats.
    def _run_test_dynamic_lot_candidates(self, lot_selection_method: AbstractAccountingMethod, test: _Test) -> None:
        print(f"\nDescription: {test.description:}")
        in_transactions = self._initialize_acquired_lots(test.in_transactions)
        acquired_lot_candidates = lot_selection_method.create_lot_candidates([], {})
        i = 0
        for int_amount in test.amounts_to_match:
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
                    self.assertEqual(result.amount, RP2Decimal(test.want[i].amount))
                    self.assertEqual(result.acquired_lot.row, test.want[i].row)
                    i += 1
                    break
                acquired_lot_candidates.clear_partial_amount(result.acquired_lot)
                amount -= result.amount
                self.assertEqual(result.amount, RP2Decimal(test.want[i].amount))
                self.assertEqual(result.acquired_lot.row, test.want[i].row)
                i += 1

    def test_with_fixed_lot_candidates(self) -> None:
        # Go-style, table-based tests. The want field contains the expected results.
        tests: List[_Test] = [
            _Test(
                description="Simple test (FIFO)",
                lot_selection_method=AccountingMethodFIFO(),
                in_transactions=[InTransactionDescriptor(10, 10), InTransactionDescriptor(11, 20), InTransactionDescriptor(12, 30)],
                amounts_to_match=[6, 4, 2, 18, 3],
                want=[SeekLotResult(10, 1), SeekLotResult(4, 1), SeekLotResult(20, 2), SeekLotResult(18, 2), SeekLotResult(30, 3)],
            ),
            _Test(
                description="Requested amount greater than acquired lot (FIFO)",
                lot_selection_method=AccountingMethodFIFO(),
                in_transactions=[InTransactionDescriptor(10, 10), InTransactionDescriptor(11, 20), InTransactionDescriptor(12, 30)],
                amounts_to_match=[15, 10, 5],
                want=[SeekLotResult(10, 1), SeekLotResult(20, 2), SeekLotResult(15, 2), SeekLotResult(5, 2)],
            ),
            _Test(
                description="Simple test (LIFO)",
                lot_selection_method=AccountingMethodLIFO(),
                in_transactions=[InTransactionDescriptor(10, 10), InTransactionDescriptor(11, 20), InTransactionDescriptor(12, 30)],
                amounts_to_match=[7, 23, 19, 1, 9],
                want=[SeekLotResult(30, 3), SeekLotResult(23, 3), SeekLotResult(20, 2), SeekLotResult(1, 2), SeekLotResult(10, 1)],
            ),
            _Test(
                description="Requested amount greater than acquired lot (LIFO)",
                lot_selection_method=AccountingMethodLIFO(),
                in_transactions=[InTransactionDescriptor(10, 10), InTransactionDescriptor(11, 20), InTransactionDescriptor(12, 30)],
                amounts_to_match=[55, 5],
                want=[SeekLotResult(30, 3), SeekLotResult(20, 2), SeekLotResult(10, 1), SeekLotResult(5, 1)],
            ),
            _Test(
                description="Simple test (HIFO)",
                lot_selection_method=AccountingMethodHIFO(),
                in_transactions=[InTransactionDescriptor(10, 10), InTransactionDescriptor(12, 20), InTransactionDescriptor(11, 30)],
                amounts_to_match=[15, 5, 20, 10, 7],
                want=[SeekLotResult(20, 2), SeekLotResult(5, 2), SeekLotResult(30, 3), SeekLotResult(10, 3), SeekLotResult(10, 1)],
            ),
            _Test(
                description="Requested amount greater than acquired lot (HIFO)",
                lot_selection_method=AccountingMethodHIFO(),
                in_transactions=[InTransactionDescriptor(10, 10), InTransactionDescriptor(12, 20), InTransactionDescriptor(11, 30)],
                amounts_to_match=[15, 5, 35, 5],
                want=[SeekLotResult(20, 2), SeekLotResult(5, 2), SeekLotResult(30, 3), SeekLotResult(10, 1), SeekLotResult(5, 1)],
            ),
            _Test(
                description="Simple test (LOFO)",
                lot_selection_method=AccountingMethodLOFO(),
                in_transactions=[InTransactionDescriptor(12, 10), InTransactionDescriptor(10, 20), InTransactionDescriptor(11, 30)],
                amounts_to_match=[15, 5, 20, 10, 7],
                want=[SeekLotResult(20, 2), SeekLotResult(5, 2), SeekLotResult(30, 3), SeekLotResult(10, 3), SeekLotResult(10, 1)],
            ),
            _Test(
                description="Requested amount greater than acquired lot (LOFO)",
                lot_selection_method=AccountingMethodLOFO(),
                in_transactions=[InTransactionDescriptor(12, 10), InTransactionDescriptor(10, 20), InTransactionDescriptor(11, 30)],
                amounts_to_match=[15, 5, 35, 5],
                want=[SeekLotResult(20, 2), SeekLotResult(5, 2), SeekLotResult(30, 3), SeekLotResult(10, 1), SeekLotResult(5, 1)],
            )

        ]
        for test in tests:
            with self.subTest(name=f"{test.description}"):
                self._run_test_fixed_lot_candidates(lot_selection_method=test.lot_selection_method, test=test)


    def test_with_dynamic_lot_candidates(self) -> None:
        # Go-style, table-based tests. The want field contains the expected results.
        tests: List[_Test] = [
            _Test(
                description="Dynamic test (FIFO)",
                lot_selection_method=AccountingMethodFIFO(),
                in_transactions=[InTransactionDescriptor(10, 10), InTransactionDescriptor(11, 20), InTransactionDescriptor(12, 30)],
                amounts_to_match=[6, 4, 2, 18, 3],
                want=[SeekLotResult(10, 1), SeekLotResult(4, 1), SeekLotResult(20, 2), SeekLotResult(18, 2), SeekLotResult(30, 3)],
            ),
            _Test(
                description="Dynamic test (LIFO)",
                lot_selection_method=AccountingMethodLIFO(),
                in_transactions=[InTransactionDescriptor(10, 10), InTransactionDescriptor(11, 20), InTransactionDescriptor(12, 30)],
                amounts_to_match=[4, 15, 27, 14],
                want=[SeekLotResult(10, 1), SeekLotResult(20, 2), SeekLotResult(30, 3), SeekLotResult(3, 3), SeekLotResult(5, 2), SeekLotResult(6, 1)],
            ),
            _Test(
                description="Dynamic test (HIFO)",
                lot_selection_method=AccountingMethodHIFO(),
                in_transactions=[InTransactionDescriptor(10, 10), InTransactionDescriptor(12, 20), InTransactionDescriptor(11, 30)],
                amounts_to_match=[4, 16, 40],
                want=[SeekLotResult(10, 1), SeekLotResult(20, 2), SeekLotResult(4, 2), SeekLotResult(30, 3), SeekLotResult(6, 1)],
            ),
            _Test(
                description="Dynamic test (LOFO)",
                lot_selection_method=AccountingMethodLOFO(),
                in_transactions=[InTransactionDescriptor(12, 10), InTransactionDescriptor(10, 20), InTransactionDescriptor(11, 30)],
                amounts_to_match=[4, 16, 40],
                want=[SeekLotResult(10, 1), SeekLotResult(20, 2), SeekLotResult(4, 2), SeekLotResult(30, 3), SeekLotResult(6, 1)],
            )
        ]
        for test in tests:
            with self.subTest(name=f"{test.description}"):
                self._run_test_dynamic_lot_candidates(lot_selection_method=test.lot_selection_method, test=test)


if __name__ == "__main__":
    unittest.main()

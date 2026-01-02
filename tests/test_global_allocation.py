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

# pylint: disable=too-many-lines

import unittest

from typing import List

from global_allocation_common import _Test, AbstractGlobalAllocation
from rp2.in_transaction import Account
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO

from transaction_processing_common import InTransactionDescriptor, IntraTransactionDescriptor, OutTransactionDescriptor


# These tests are independent of the accounting method, so they are repeated for all accounting methods.
class TestGlobalAllocation(AbstractGlobalAllocation):

    # Global allocation failure tests. These tests are independent of allocation method, so the code repeats each test with all allocation methods.
    def test_global_allocation_failure_all_allocation_methods(self) -> None:

        # Go-style, table-based tests. The input field contains test input and the want field contains the expected result.
        tests: List[_Test] = [
            _Test(
                description="Empty input_per_wallet_transactions.",
                input_per_wallet_transactions={
                },
                input_account_order=[Account("Coinbase", "Bob"), Account("BlockFi", "Bob")],
                input_actual_amounts = {},
                want_intra_transactions = [],
                want_error=r"Parameter 'wallet_2_per_wallet_input_data' is empty.",
            ),
            _Test(
                description="Missing account from account order list.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 20),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3", 3, 3, "BlockFi", "Bob", 130, 30),
                    ],
                },
                input_account_order=[Account("Coinbase", "Bob"), Account("BlockFi", "Bob")],
                input_actual_amounts = {},
                want_intra_transactions = [],
                want_error=r"Account order list is incomplete. Missing accounts: {Account\(exchange='Kraken', holder='Bob'\)}",
            ),
            _Test(
                description=("Extra account in account order list."),
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 20),
                    ],
                },
                input_account_order=[Account("Coinbase", "Bob"), Account("BlockFi", "Bob"), Account("Kraken", "Bob")],
                input_actual_amounts = {},
                want_intra_transactions = [],
                want_error=r"Account order list has extra account Account\(exchange='BlockFi', holder='Bob'\) that is not referenced in the transaction set.",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                for allocation_method in self._accounting_methods:
                    self._run_test(test, allocation_method)

    def test_global_allocation_using_fifo(self) -> None:
        # Go-style, table-based tests. The input field contains test input and the want field contains the expected result.
        tests: List[_Test] = [
            _Test(
                description="Simple test.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 20),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3", 3, 3, "BlockFi", "Bob", 130, 30),
                    ],
                },
                input_account_order=[Account("Coinbase", "Bob"), Account("Kraken", "Bob"), Account("BlockFi", "Bob")],
                input_actual_amounts={},
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Coinbase", "Bob", "Coinbase", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Kraken", "Bob", 1, 20, 20),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "BlockFi", "Bob", "BlockFi", "Bob", 1, 30, 30),
                ],
                want_error="",
            ),
            _Test(
                description="Simple test with unsorted values.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 120, 30),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 130, 10),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3", 3, 3, "BlockFi", "Bob", 110, 20),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={},
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Coinbase", "Bob", "BlockFi", "Bob", 1, 20, 20),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Coinbase", "Bob", "Kraken", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Coinbase", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "BlockFi", "Bob", "Coinbase", "Bob", 1, 20, 20),
                ],
                want_error="",
            ),
            _Test(
                description="Mixed test with in, intra, out transactions.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                       InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 20),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 5, 4),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor('3/-1', 3, -1, 'BlockFi', 'Bob', 120, 4, from_lot_unique_id="2", cost_basis_day=2),
                        OutTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", 140, 2),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='BlockFi', holder='Bob'): {"3/-1": 2},
                    Account(exchange='Kraken', holder='Bob'): {"2": 15},
                    Account(exchange='Coinbase', holder='Bob'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Coinbase", "Bob", "BlockFi", "Bob", 1, 2, 2),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Coinbase", "Bob", "Kraken", "Bob", 1, 8, 8),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Kraken", "Bob", 1, 7, 7),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Bob", "Coinbase", "Bob", 1, 8, 8),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "BlockFi", "Bob", "Coinbase", "Bob", 1, 2, 2),
                ],
                want_error="",
            ),
            _Test(
                description="Larger test with in, intra, out transactions.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 130, 10),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "BlockFi", "Bob", 130, 5, 3),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 15),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "BlockFi", "Bob", 130, 17, 16),
                        InTransactionDescriptor('9/-5', 9, -5, 'Coinbase', 'Bob', 130, 1, from_lot_unique_id="2/-1", cost_basis_day=1),
                        InTransactionDescriptor('9/-6', 9, -6, 'Coinbase', 'Bob', 130, 3, from_lot_unique_id="4/-2", cost_basis_day=1),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor('2/-1', 2, -1, 'BlockFi', 'Bob', 130, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-2', 4, -2, 'BlockFi', 'Bob', 130, 5, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-3', 4, -3, 'BlockFi', 'Bob', 120, 11, from_lot_unique_id="3", cost_basis_day=3),
                        InTransactionDescriptor('6/-4', 6, -4, 'BlockFi', 'Bob', 110, 14, from_lot_unique_id="5", cost_basis_day=5),
                        OutTransactionDescriptor("8", 8, 8, "BlockFi", "Bob", 140, 2),
                        IntraTransactionDescriptor("9", 9, 9, "BlockFi", "Bob", "Coinbase", "Bob", 130, 5, 4),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("5", 5, 5, "Kraken", "Bob", 110, 20),
                        IntraTransactionDescriptor("6", 6, 6, "Kraken", "Bob", "BlockFi", "Bob", 130, 15, 14),
                        InTransactionDescriptor("7", 7, 7, "Kraken", "Bob", 140, 25),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Coinbase", "Bob"), Account("Kraken", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {
                        '1': 0,
                        '3': 3,
                    },
                    Account(exchange='BlockFi', holder='Bob'): {
                        '2/-1': 0,
                        '4/-2': 1,
                    },
                    Account(exchange='Kraken', holder='Bob'): {
                        '5': 5,
                    },
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Coinbase", "Bob", "BlockFi", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "BlockFi", "Bob", "BlockFi", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "BlockFi", "Bob", "BlockFi", "Bob", 1, 11, 11),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Bob", "BlockFi", "Bob", 1, 5, 5),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "BlockFi", "Bob", "BlockFi", "Bob", 1, 6, 6),
                    IntraTransactionDescriptor("ga/-6", 366, -6, "BlockFi", "Bob", "Coinbase", "Bob", 1, 7, 7),
                    IntraTransactionDescriptor("ga/-7", 366, -7, "BlockFi", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-8", 366, -8, "Kraken", "Bob", "Kraken", "Bob", 1, 25, 25),
                    IntraTransactionDescriptor("ga/-9", 366, -9, "Coinbase", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-10", 366, -10, "Coinbase", "Bob", "Kraken", "Bob", 1, 3, 3),
                ],
                want_error="",
            ),
            _Test(
                description="Interlaced in and intra transactions",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1", "4/-2"]}),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4, to_lot_unique_ids={Account("Kraken", "Bob"): ["4/-3"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor('2/-1', 2, -1, 'Kraken', 'Bob', 110, 4, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-2', 4, -2, 'Kraken', 'Bob', 110, 6, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-3', 4, -3, 'Kraken', 'Bob', 130, 4, from_lot_unique_id="3", cost_basis_day=3),
                    ],
                },
                input_account_order=[Account("Coinbase", "Bob"), Account("Kraken", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 0, '3': 0},
                    Account(exchange='Kraken', holder='Bob'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "Kraken", "Bob", 1, 4, 4),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Kraken", "Bob", 1, 6, 6),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Kraken", "Bob", 1, 4, 4),
                ],
                want_error="",
            ),
            _Test(
                description="Two in-lots, three transfers: CB->Kraken",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                    ],
                    Account("Kraken", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Alice", 110, 7, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Alice", 110, 2, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-3", 4, -3, "Kraken", "Alice", 120, 8, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Kraken", "Alice", 120, 12, from_lot_unique_id="2", cost_basis_day=2),
                    ]
                },
                input_account_order=[Account("Kraken", "Alice"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 0, '2': 0},
                    Account(exchange='Kraken', holder='Alice'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Alice", "Kraken", "Alice", 1, 7, 7),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Alice", "Kraken", "Alice", 1, 2, 2),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Alice", "Kraken", "Alice", 1, 8, 8),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Alice", "Kraken", "Alice", 1, 12, 12),
                ],
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                description="Reciprocal transfer: CB->Kraken, Kraken->CB",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 6, from_lot_unique_id="2", cost_basis_day=2),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                input_account_order=[Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 6},
                    Account(exchange='Kraken', holder='Bob'): {'2': 3},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Coinbase", "Bob", "Kraken", "Bob", 1, 6, 6),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Coinbase", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Coinbase", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Coinbase", "Bob", "Coinbase", "Bob", 1, 6, 6),
                ],
                want_error="",
            ),
            _Test(
                description="Reciprocal transfer + sales: CB->Kraken, Kraken->CB, CB sales",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 1, from_lot_unique_id="2", cost_basis_day=2),
                        OutTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", 150, 3, 2),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 2, 1),
                        OutTransactionDescriptor("5", 5, 5, "Kraken", "Bob", 150, 2, 1),
                    ],
                },
                input_account_order=[Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 1},
                    Account(exchange='Kraken', holder='Bob'): {'2': 5},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Coinbase", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Kraken", "Bob", 1, 5, 5),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Kraken", "Bob", 1, 2, 2),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Bob", "Coinbase", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "Coinbase", "Bob", "Coinbase", "Bob", 1, 1, 1),
                ],
                want_error="",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                self._run_test(test, AccountingMethodFIFO())


    def test_global_allocation_using_lifo(self) -> None:
        # Go-style, table-based tests. The input field contains test input and the want field contains the expected result.
        tests: List[_Test] = [
            _Test(
                description="Simple test.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 20),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3", 3, 3, "BlockFi", "Bob", 130, 30),
                    ],
                },
                input_account_order=[Account("Coinbase", "Bob"), Account("Kraken", "Bob"), Account("BlockFi", "Bob")],
                input_actual_amounts={},
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "BlockFi", "Bob", "Coinbase", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "BlockFi", "Bob", "Kraken", "Bob", 1, 20, 20),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "BlockFi", "Bob", 1, 20, 20),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Coinbase", "Bob", "BlockFi", "Bob", 1, 10, 10),
                ],
                want_error="",
            ),
            _Test(
                description="Simple test with unsorted values.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 120, 30),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 130, 10),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3", 3, 3, "BlockFi", "Bob", 110, 20),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={},
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "BlockFi", "Bob", "BlockFi", "Bob", 1, 20, 20),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Kraken", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Coinbase", "Bob", "Coinbase", "Bob", 1, 30, 30),
                ],
                want_error="",
            ),
            _Test(
                description="Mixed test with in, intra, out transactions.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                       InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 20),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 5, 4),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor('3/-1', 3, -1, 'BlockFi', 'Bob', 120, 4, from_lot_unique_id="2", cost_basis_day=2),
                        OutTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", 140, 2),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='BlockFi', holder='Bob'): {"3/-1": 2},
                    Account(exchange='Kraken', holder='Bob'): {"2": 15},
                    Account(exchange='Coinbase', holder='Bob'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "BlockFi", "Bob", 1, 2, 2),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Kraken", "Bob", 1, 13, 13),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "BlockFi", "Bob", "Kraken", "Bob", 1, 2, 2),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Coinbase", "Bob", "Coinbase", "Bob", 1, 10, 10),
                ],
                want_error="",
            ),
            _Test(
                description="Larger test with in, intra, out transactions.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 130, 10),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "BlockFi", "Bob", 130, 5, 3),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 15),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "BlockFi", "Bob", 130, 17, 16),
                        InTransactionDescriptor('9/-5', 9, -5, 'Coinbase', 'Bob', 130, 1, from_lot_unique_id="2/-1", cost_basis_day=1),
                        InTransactionDescriptor('9/-6', 9, -6, 'Coinbase', 'Bob', 130, 3, from_lot_unique_id="4/-2", cost_basis_day=1),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor('2/-1', 2, -1, 'BlockFi', 'Bob', 130, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-2', 4, -2, 'BlockFi', 'Bob', 130, 5, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-3', 4, -3, 'BlockFi', 'Bob', 120, 11, from_lot_unique_id="3", cost_basis_day=3),
                        InTransactionDescriptor('6/-4', 6, -4, 'BlockFi', 'Bob', 110, 14, from_lot_unique_id="5", cost_basis_day=5),
                        OutTransactionDescriptor("8", 8, 8, "BlockFi", "Bob", 140, 2),
                        IntraTransactionDescriptor("9", 9, 9, "BlockFi", "Bob", "Coinbase", "Bob", 130, 5, 4),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("5", 5, 5, "Kraken", "Bob", 110, 20),
                        IntraTransactionDescriptor("6", 6, 6, "Kraken", "Bob", "BlockFi", "Bob", 130, 15, 14),
                        InTransactionDescriptor("7", 7, 7, "Kraken", "Bob", 140, 25),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Coinbase", "Bob"), Account("Kraken", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {
                        '1': 0,
                        '3': 3,
                    },
                    Account(exchange='BlockFi', holder='Bob'): {
                        '2/-1': 0,
                        '4/-2': 1,
                    },
                    Account(exchange='Kraken', holder='Bob'): {
                        '5': 5,
                    },
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "BlockFi", "Bob", 1, 25, 25),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "BlockFi", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Coinbase", "Bob", 1, 4, 4),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "BlockFi", "Bob", "Coinbase", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "BlockFi", "Bob", "Kraken", "Bob", 1, 11, 11),
                    IntraTransactionDescriptor("ga/-6", 366, -6, "Coinbase", "Bob", "Kraken", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-7", 366, -7, "BlockFi", "Bob", "Kraken", "Bob", 1, 11, 11),
                    IntraTransactionDescriptor("ga/-8", 366, -8, "BlockFi", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-9", 366, -9, "Coinbase", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-10", 366, -10, "Coinbase", "Bob", "Kraken", "Bob", 1, 3, 3),
                ],
                want_error="",
            ),
            _Test(
                description="Interlaced in and intra transactions",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1", "4/-2"]}),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4, to_lot_unique_ids={Account("Kraken", "Bob"): ["4/-3"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor('2/-1', 2, -1, 'Kraken', 'Bob', 110, 4, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-2', 4, -2, 'Kraken', 'Bob', 110, 6, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-3', 4, -3, 'Kraken', 'Bob', 130, 4, from_lot_unique_id="3", cost_basis_day=3),
                    ],
                },
                input_account_order=[Account("Coinbase", "Bob"), Account("Kraken", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 0, '3': 0},
                    Account(exchange='Kraken', holder='Bob'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "Kraken", "Bob", 1, 4, 4),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Kraken", "Bob", 1, 4, 4),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Kraken", "Bob", 1, 6, 6),
                ],
                want_error="",
            ),
            _Test(
                description="Two in-lots, three transfers: CB->Kraken",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                    ],
                    Account("Kraken", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Alice", 110, 7, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Alice", 110, 2, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-3", 4, -3, "Kraken", "Alice", 120, 8, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Kraken", "Alice", 120, 12, from_lot_unique_id="2", cost_basis_day=2),
                    ]
                },
                input_account_order=[Account("Kraken", "Alice"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 0, '2': 0},
                    Account(exchange='Kraken', holder='Alice'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Alice", "Kraken", "Alice", 1, 8, 8),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Alice", "Kraken", "Alice", 1, 12, 12),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Alice", "Kraken", "Alice", 1, 7, 7),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Alice", "Kraken", "Alice", 1, 2, 2),
                ],
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                description="Reciprocal transfer: CB->Kraken, Kraken->CB",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 6, from_lot_unique_id="2", cost_basis_day=2),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                input_account_order=[Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 6},
                    Account(exchange='Kraken', holder='Bob'): {'2': 3},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "Kraken", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Coinbase", "Bob", "Kraken", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Coinbase", "Bob", "Coinbase", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Coinbase", "Bob", "Coinbase", "Bob", 1, 6, 6),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "Kraken", "Bob", "Coinbase", "Bob", 1, 3, 3),
                ],
                want_error="",
            ),
            _Test(
                description="Reciprocal transfer + sales: CB->Kraken, Kraken->CB, CB sales",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 1, from_lot_unique_id="2", cost_basis_day=2),
                        OutTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", 150, 3, 2),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 2, 1),
                        OutTransactionDescriptor("5", 5, 5, "Kraken", "Bob", 150, 2, 1),
                    ],
                },
                input_account_order=[Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 1},
                    Account(exchange='Kraken', holder='Bob'): {'2': 5},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "Kraken", "Bob", 1, 5, 5),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Coinbase", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Coinbase", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "Kraken", "Bob", "Coinbase", "Bob", 1, 2, 2),
                ],
                want_error="",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                self._run_test(test, AccountingMethodLIFO())


    def test_global_allocation_using_hifo(self) -> None:
        # Go-style, table-based tests. The input field contains test input and the want field contains the expected result.
        tests: List[_Test] = [
            _Test(
                description="Simple test.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 20),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3", 3, 3, "BlockFi", "Bob", 130, 30),
                    ],
                },
                input_account_order=[Account("Coinbase", "Bob"), Account("Kraken", "Bob"), Account("BlockFi", "Bob")],
                input_actual_amounts={},
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "BlockFi", "Bob", "Coinbase", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "BlockFi", "Bob", "Kraken", "Bob", 1, 20, 20),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "BlockFi", "Bob", 1, 20, 20),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Coinbase", "Bob", "BlockFi", "Bob", 1, 10, 10),
                ],
                want_error="",
            ),
            _Test(
                description="Simple test with unsorted values.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 120, 30),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 130, 10),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3", 3, 3, "BlockFi", "Bob", 110, 20),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={},
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "BlockFi", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Coinbase", "Bob", "BlockFi", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Coinbase", "Bob", "Kraken", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Coinbase", "Bob", "Coinbase", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "BlockFi", "Bob", "Coinbase", "Bob", 1, 20, 20),
                ],
                want_error="",
            ),
            _Test(
                description="Mixed test with in, intra, out transactions.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                       InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 20),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 5, 4),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor('3/-1', 3, -1, 'BlockFi', 'Bob', 120, 4, from_lot_unique_id="2", cost_basis_day=2),
                        OutTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", 140, 2),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='BlockFi', holder='Bob'): {"3/-1": 2},
                    Account(exchange='Kraken', holder='Bob'): {"2": 15},
                    Account(exchange='Coinbase', holder='Bob'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "BlockFi", "Bob", 1, 2, 2),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Kraken", "Bob", 1, 13, 13),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "BlockFi", "Bob", "Kraken", "Bob", 1, 2, 2),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Coinbase", "Bob", "Coinbase", "Bob", 1, 10, 10),
                ],
                want_error="",
            ),
            _Test(
                description="Larger test with in, intra, out transactions.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 130, 10),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "BlockFi", "Bob", 130, 5, 3),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 15),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "BlockFi", "Bob", 130, 17, 16),
                        InTransactionDescriptor('9/-5', 9, -5, 'Coinbase', 'Bob', 130, 1, from_lot_unique_id="2/-1", cost_basis_day=1),
                        InTransactionDescriptor('9/-6', 9, -6, 'Coinbase', 'Bob', 130, 3, from_lot_unique_id="4/-2", cost_basis_day=1),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor('2/-1', 2, -1, 'BlockFi', 'Bob', 130, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-2', 4, -2, 'BlockFi', 'Bob', 130, 5, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-3', 4, -3, 'BlockFi', 'Bob', 120, 11, from_lot_unique_id="3", cost_basis_day=3),
                        InTransactionDescriptor('6/-4', 6, -4, 'BlockFi', 'Bob', 110, 14, from_lot_unique_id="5", cost_basis_day=5),
                        OutTransactionDescriptor("8", 8, 8, "BlockFi", "Bob", 140, 2),
                        IntraTransactionDescriptor("9", 9, 9, "BlockFi", "Bob", "Coinbase", "Bob", 130, 5, 4),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("5", 5, 5, "Kraken", "Bob", 110, 20),
                        IntraTransactionDescriptor("6", 6, 6, "Kraken", "Bob", "BlockFi", "Bob", 130, 15, 14),
                        InTransactionDescriptor("7", 7, 7, "Kraken", "Bob", 140, 25),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Coinbase", "Bob"), Account("Kraken", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {
                        '1': 0,
                        '3': 3,
                    },
                    Account(exchange='BlockFi', holder='Bob'): {
                        '2/-1': 0,
                        '4/-2': 1,
                    },
                    Account(exchange='Kraken', holder='Bob'): {
                        '5': 5,
                    },
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "BlockFi", "Bob", 1, 25, 25),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "BlockFi", "Bob", "BlockFi", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Coinbase", "Bob", "Coinbase", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Coinbase", "Bob", "Coinbase", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "Coinbase", "Bob", "Coinbase", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-6", 366, -6, "BlockFi", "Bob", "Kraken", "Bob", 1, 11, 11),
                    IntraTransactionDescriptor("ga/-7", 366, -7, "Kraken", "Bob", "Kraken", "Bob", 1, 5, 5),
                    IntraTransactionDescriptor("ga/-8", 366, -8, "BlockFi", "Bob", "Kraken", "Bob", 1, 14, 14),
                ],
                want_error="",
            ),
            _Test(
                description="Interlaced in and intra transactions",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1", "4/-2"]}),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4, to_lot_unique_ids={Account("Kraken", "Bob"): ["4/-3"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor('2/-1', 2, -1, 'Kraken', 'Bob', 110, 4, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-2', 4, -2, 'Kraken', 'Bob', 110, 6, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-3', 4, -3, 'Kraken', 'Bob', 130, 4, from_lot_unique_id="3", cost_basis_day=3),
                    ],
                },
                input_account_order=[Account("Coinbase", "Bob"), Account("Kraken", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 0, '3': 0},
                    Account(exchange='Kraken', holder='Bob'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "Kraken", "Bob", 1, 4, 4),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Kraken", "Bob", 1, 4, 4),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Kraken", "Bob", 1, 6, 6),
                ],
                want_error="",
            ),
            _Test(
                description="Two in-lots, three transfers: CB->Kraken",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                    ],
                    Account("Kraken", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Alice", 110, 7, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Alice", 110, 2, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-3", 4, -3, "Kraken", "Alice", 120, 8, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Kraken", "Alice", 120, 12, from_lot_unique_id="2", cost_basis_day=2),
                    ]
                },
                input_account_order=[Account("Kraken", "Alice"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 0, '2': 0},
                    Account(exchange='Kraken', holder='Alice'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Alice", "Kraken", "Alice", 1, 8, 8),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Alice", "Kraken", "Alice", 1, 12, 12),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Alice", "Kraken", "Alice", 1, 7, 7),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Alice", "Kraken", "Alice", 1, 2, 2),
                ],
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                description="Reciprocal transfer: CB->Kraken, Kraken->CB",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 6, from_lot_unique_id="2", cost_basis_day=2),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                input_account_order=[Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 6},
                    Account(exchange='Kraken', holder='Bob'): {'2': 3},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "Kraken", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Coinbase", "Bob", "Kraken", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Coinbase", "Bob", "Coinbase", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Coinbase", "Bob", "Coinbase", "Bob", 1, 6, 6),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "Kraken", "Bob", "Coinbase", "Bob", 1, 3, 3),
                ],
                want_error="",
            ),
            _Test(
                description="Reciprocal transfer + sales: CB->Kraken, Kraken->CB, CB sales",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 1, from_lot_unique_id="2", cost_basis_day=2),
                        OutTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", 150, 3, 2),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 2, 1),
                        OutTransactionDescriptor("5", 5, 5, "Kraken", "Bob", 150, 2, 1),
                    ],
                },
                input_account_order=[Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 1},
                    Account(exchange='Kraken', holder='Bob'): {'2': 5},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "Kraken", "Bob", 1, 5, 5),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Coinbase", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Coinbase", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "Kraken", "Bob", "Coinbase", "Bob", 1, 2, 2),
                ],
                want_error="",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                self._run_test(test, AccountingMethodHIFO())


    def test_global_allocation_using_lofo(self) -> None:
        # Go-style, table-based tests. The input field contains test input and the want field contains the expected result.
        tests: List[_Test] = [
            _Test(
                description="Simple test.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 20),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3", 3, 3, "BlockFi", "Bob", 130, 30),
                    ],
                },
                input_account_order=[Account("Coinbase", "Bob"), Account("Kraken", "Bob"), Account("BlockFi", "Bob")],
                input_actual_amounts={},
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Coinbase", "Bob", "Coinbase", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Kraken", "Bob", 1, 20, 20),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "BlockFi", "Bob", "BlockFi", "Bob", 1, 30, 30),
                ],
                want_error="",
            ),
            _Test(
                description="Simple test with unsorted values.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 120, 30),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 130, 10),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3", 3, 3, "BlockFi", "Bob", 110, 20),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={},
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "BlockFi", "Bob", "BlockFi", "Bob", 1, 20, 20),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Coinbase", "Bob", "Kraken", "Bob", 1, 10, 10),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Coinbase", "Bob", "Coinbase", "Bob", 1, 20, 20),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Bob", "Coinbase", "Bob", 1, 10, 10),
                ],
                want_error="",
            ),
            _Test(
                description="Mixed test with in, intra, out transactions.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                       InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 20),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 5, 4),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor('3/-1', 3, -1, 'BlockFi', 'Bob', 120, 4, from_lot_unique_id="2", cost_basis_day=2),
                        OutTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", 140, 2),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='BlockFi', holder='Bob'): {"3/-1": 2},
                    Account(exchange='Kraken', holder='Bob'): {"2": 15},
                    Account(exchange='Coinbase', holder='Bob'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Coinbase", "Bob", "BlockFi", "Bob", 1, 2, 2),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Coinbase", "Bob", "Kraken", "Bob", 1, 8, 8),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Kraken", "Bob", 1, 7, 7),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Bob", "Coinbase", "Bob", 1, 8, 8),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "BlockFi", "Bob", "Coinbase", "Bob", 1, 2, 2),
                ],
                want_error="",
            ),
            _Test(
                description="Larger test with in, intra, out transactions.",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 130, 10),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "BlockFi", "Bob", 130, 5, 3),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 15),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "BlockFi", "Bob", 130, 17, 16),
                        InTransactionDescriptor('9/-5', 9, -5, 'Coinbase', 'Bob', 130, 1, from_lot_unique_id="2/-1", cost_basis_day=1),
                        InTransactionDescriptor('9/-6', 9, -6, 'Coinbase', 'Bob', 130, 3, from_lot_unique_id="4/-2", cost_basis_day=1),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor('2/-1', 2, -1, 'BlockFi', 'Bob', 130, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-2', 4, -2, 'BlockFi', 'Bob', 130, 5, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-3', 4, -3, 'BlockFi', 'Bob', 120, 11, from_lot_unique_id="3", cost_basis_day=3),
                        InTransactionDescriptor('6/-4', 6, -4, 'BlockFi', 'Bob', 110, 14, from_lot_unique_id="5", cost_basis_day=5),
                        OutTransactionDescriptor("8", 8, 8, "BlockFi", "Bob", 140, 2),
                        IntraTransactionDescriptor("9", 9, 9, "BlockFi", "Bob", "Coinbase", "Bob", 130, 5, 4),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("5", 5, 5, "Kraken", "Bob", 110, 20),
                        IntraTransactionDescriptor("6", 6, 6, "Kraken", "Bob", "BlockFi", "Bob", 130, 15, 14),
                        InTransactionDescriptor("7", 7, 7, "Kraken", "Bob", 140, 25),
                    ],
                },
                input_account_order=[Account("BlockFi", "Bob"), Account("Coinbase", "Bob"), Account("Kraken", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {
                        '1': 0,
                        '3': 3,
                    },
                    Account(exchange='BlockFi', holder='Bob'): {
                        '2/-1': 0,
                        '4/-2': 1,
                    },
                    Account(exchange='Kraken', holder='Bob'): {
                        '5': 5,
                    },
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "BlockFi", "Bob", 1, 5, 5),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "BlockFi", "Bob", "BlockFi", "Bob", 1, 14, 14),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Coinbase", "Bob", "BlockFi", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "BlockFi", "Bob", "BlockFi", "Bob", 1, 4, 4),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "BlockFi", "Bob", "Coinbase", "Bob", 1, 7, 7),
                    IntraTransactionDescriptor("ga/-6", 366, -6, "BlockFi", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-7", 366, -7, "Coinbase", "Bob", "Kraken", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-8", 366, -8, "Coinbase", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-9", 366, -9, "Kraken", "Bob", "Kraken", "Bob", 1, 25, 25),
                ],
                want_error="",
            ),
            _Test(
                description="Interlaced in and intra transactions",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1", "4/-2"]}),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4, to_lot_unique_ids={Account("Kraken", "Bob"): ["4/-3"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor('2/-1', 2, -1, 'Kraken', 'Bob', 110, 4, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-2', 4, -2, 'Kraken', 'Bob', 110, 6, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor('4/-3', 4, -3, 'Kraken', 'Bob', 130, 4, from_lot_unique_id="3", cost_basis_day=3),
                    ],
                },
                input_account_order=[Account("Coinbase", "Bob"), Account("Kraken", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 0, '3': 0},
                    Account(exchange='Kraken', holder='Bob'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Bob", "Kraken", "Bob", 1, 4, 4),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Kraken", "Bob", 1, 6, 6),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Kraken", "Bob", 1, 4, 4),
                ],
                want_error="",
            ),
            _Test(
                description="Two in-lots, three transfers: CB->Kraken",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                    ],
                    Account("Kraken", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Alice", 110, 7, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Alice", 110, 2, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-3", 4, -3, "Kraken", "Alice", 120, 8, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Kraken", "Alice", 120, 12, from_lot_unique_id="2", cost_basis_day=2),
                    ]
                },
                input_account_order=[Account("Kraken", "Alice"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 0, '2': 0},
                    Account(exchange='Kraken', holder='Alice'): {},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Kraken", "Alice", "Kraken", "Alice", 1, 7, 7),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Alice", "Kraken", "Alice", 1, 2, 2),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Alice", "Kraken", "Alice", 1, 8, 8),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Alice", "Kraken", "Alice", 1, 12, 12),
                ],
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                description="Reciprocal transfer: CB->Kraken, Kraken->CB",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 6, from_lot_unique_id="2", cost_basis_day=2),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                input_account_order=[Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 6},
                    Account(exchange='Kraken', holder='Bob'): {'2': 3},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Coinbase", "Bob", "Kraken", "Bob", 1, 6, 6),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Coinbase", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Coinbase", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Coinbase", "Bob", "Coinbase", "Bob", 1, 6, 6),
                ],
                want_error="",
            ),
            _Test(
                description="Reciprocal transfer + sales: CB->Kraken, Kraken->CB, CB sales",
                input_per_wallet_transactions={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 1, from_lot_unique_id="2", cost_basis_day=2),
                        OutTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", 150, 3, 2),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 2, 1),
                        OutTransactionDescriptor("5", 5, 5, "Kraken", "Bob", 150, 2, 1),
                    ],
                },
                input_account_order=[Account("Kraken", "Bob"), Account("Coinbase", "Bob")],
                input_actual_amounts={
                    Account(exchange='Coinbase', holder='Bob'): {'1': 1},
                    Account(exchange='Kraken', holder='Bob'): {'2': 5},
                },
                want_intra_transactions=[
                    IntraTransactionDescriptor("ga/-1", 366, -1, "Coinbase", "Bob", "Kraken", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-2", 366, -2, "Kraken", "Bob", "Kraken", "Bob", 1, 3, 3),
                    IntraTransactionDescriptor("ga/-3", 366, -3, "Kraken", "Bob", "Kraken", "Bob", 1, 4, 4),
                    IntraTransactionDescriptor("ga/-4", 366, -4, "Kraken", "Bob", "Coinbase", "Bob", 1, 1, 1),
                    IntraTransactionDescriptor("ga/-5", 366, -5, "Coinbase", "Bob", "Coinbase", "Bob", 1, 1, 1),
                ],
                want_error="",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                self._run_test(test, AccountingMethodLOFO())

if __name__ == "__main__":
    unittest.main()

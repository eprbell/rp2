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

from typing import List

from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO

from per_wallet_tax_engine_common import _Test, Account, InTransactionDescriptor, OutTransactionDescriptor, IntraTransactionDescriptor, AbstractTestPerWalletTaxEngine

# These tests are dependent on transfer semantics, so they are not run for all accounting methods.
class TestPerWalletTaxEngine(AbstractTestPerWalletTaxEngine):

    # Transfer analysis across different accounts using only FIFO transfer semantics.
    def test_transfer_analysis_success_using_multiple_accounts_and_fifo(self) -> None:
        # Go-style, table-based tests. The input field contains test input and the want field contains the expected results.
        tests: List[_Test] = [
            _Test(
                description="Interlaced in and intra transactions",
                input = [
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                ],
                want = {
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1", "4/-2"]}),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4, to_lot_unique_ids={Account("Kraken", "Bob"): ["4/-3"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2/-1", 2, -1, "Kraken", "Bob", 110, 4, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Bob", 110, 6, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-3", 4, -3, "Kraken", "Bob", 130, 4, from_lot_unique_id="3", cost_basis_day=3),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Same exchange transfer (but with two different holders). Two in-lots, three transfers",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 8, 7),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 10, 10),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Alice", 150, 12, 12),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Coinbase", "Alice"): ["3/-1", "4/-2"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20, to_lot_unique_ids={Account("Coinbase", "Alice"): ["4/-3", "5/-4"]}),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Alice", 150, 12, 12),
                    ],
                    Account("Coinbase", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Coinbase", "Alice", 110, 7, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Alice", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-3", 4, -3, "Coinbase", "Alice", 120, 7, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Coinbase", "Alice", 120, 12, from_lot_unique_id="2", cost_basis_day=2),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Two in-lots, three transfers: CB->Kraken",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Alice"): ["3/-1", "4/-2"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20, to_lot_unique_ids={Account("Kraken", "Alice"): ["4/-3", "5/-4"]}),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                    ],
                    Account("Kraken", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Alice", 110, 7, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Alice", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-3", 4, -3, "Kraken", "Alice", 120, 7, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Kraken", "Alice", 120, 12, from_lot_unique_id="2", cost_basis_day=2),
                    ],
                },
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                description="Reciprocal transfer on same exchange but different holders: Bob -> Alice, Alice -> Bob",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Alice", 120, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 4, 3),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Alice", "Coinbase", "Bob", 140, 7, 6),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Coinbase", "Alice"): ["3/-1"]}),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 6, from_lot_unique_id="2", cost_basis_day=2),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 4, 3),
                    ],
                    Account("Coinbase", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Coinbase", "Alice", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Alice", 120, 10, to_lot_unique_ids={Account("Coinbase", "Bob"): ["4/-2"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Alice", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                description="Reciprocal transfer: CB->Kraken, Kraken->CB",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                    IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["3/-1"]}),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 6, from_lot_unique_id="2", cost_basis_day=2),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10, to_lot_unique_ids={Account("Coinbase", "Bob"): ["4/-2"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Many transactions with loops, sales and self-transfers across three accounts",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 6),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 130, 6),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 6),
                    InTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 6),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 160, 4, 4),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Kraken", "Bob", 170, 4, 4),
                    IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Kraken", "Bob", 180, 4, 4),
                    IntraTransactionDescriptor("8", 8, 8, "Coinbase", "Bob", "Kraken", "Bob", 190, 4, 4),
                    IntraTransactionDescriptor("9", 9, 9, "Coinbase", "Bob", "Kraken", "Bob", 200, 4, 4),
                    IntraTransactionDescriptor("10", 10, 10, "Coinbase", "Bob", "Kraken", "Bob", 210, 4, 4),
                    IntraTransactionDescriptor("11", 11, 11, "Kraken", "Bob", "BlockFi", "Bob", 220, 12, 12),
                    IntraTransactionDescriptor("12", 12, 12, "Kraken", "Bob", "BlockFi", "Bob", 230, 12, 12),
                    IntraTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", "BlockFi", "Bob", 230, 24, 24),
                    OutTransactionDescriptor("14", 14, 14, "BlockFi", "Bob", 240, 6, 0),
                    IntraTransactionDescriptor("15", 15, 15, "BlockFi", "Bob", "Coinbase", "Bob", 240, 18, 18),
                    IntraTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", "Coinbase", "Bob", 250, 18, 18),
                    IntraTransactionDescriptor("17", 17, 17, "Coinbase", "Bob", "Coinbase", "Bob", 260, 18, 18),
                    IntraTransactionDescriptor("18", 18, 18, "Coinbase", "Bob", "Coinbase", "Bob", 270, 18, 18),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["5/-1", "6/-2"], Account("BlockFi", "Bob"): ["11/-9", "11/-10"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 130, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["6/-3", "7/-4"], Account("BlockFi", "Bob"): ["11/-11", "11/-12"]}),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["8/-5", "9/-6"], Account("BlockFi", "Bob"): ["12/-13", "12/-14"]}),
                        InTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["9/-7", "10/-8"], Account("BlockFi", "Bob"): ["12/-15", "12/-16"]}),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 160, 4, 4),
                        IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Kraken", "Bob", 170, 4, 4),
                        IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Kraken", "Bob", 180, 4, 4),
                        IntraTransactionDescriptor("8", 8, 8, "Coinbase", "Bob", "Kraken", "Bob", 190, 4, 4),
                        IntraTransactionDescriptor("9", 9, 9, "Coinbase", "Bob", "Kraken", "Bob", 200, 4, 4),
                        IntraTransactionDescriptor("10", 10, 10, "Coinbase", "Bob", "Kraken", "Bob", 210, 4, 4),
                        IntraTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", "Coinbase", "Bob", 250, 18, 18),
                        IntraTransactionDescriptor("17", 17, 17, "Coinbase", "Bob", "Coinbase", "Bob", 260, 18, 18),
                        IntraTransactionDescriptor("18", 18, 18, "Coinbase", "Bob", "Coinbase", "Bob", 270, 18, 18),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("5/-1", 5, -1, "Kraken", "Bob", 110, 4, from_lot_unique_id="1", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-9"]}, cost_basis_day=1),
                        InTransactionDescriptor("6/-2", 6, -2, "Kraken", "Bob", 110, 2, from_lot_unique_id="1", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-10"]}, cost_basis_day=1),
                        InTransactionDescriptor("6/-3", 6, -3, "Kraken", "Bob", 130, 2, from_lot_unique_id="2", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-11"]}, cost_basis_day=2),
                        InTransactionDescriptor("7/-4", 7, -4, "Kraken", "Bob", 130, 4, from_lot_unique_id="2", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-12"]}, cost_basis_day=2),
                        InTransactionDescriptor("8/-5", 8, -5, "Kraken", "Bob", 120, 4, from_lot_unique_id="3", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-13"]}, cost_basis_day=3),
                        InTransactionDescriptor("9/-6", 9, -6, "Kraken", "Bob", 120, 2, from_lot_unique_id="3", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-14"]}, cost_basis_day=3),
                        InTransactionDescriptor("9/-7", 9, -7, "Kraken", "Bob", 140, 2, from_lot_unique_id="4", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-15"]}, cost_basis_day=4),
                        InTransactionDescriptor("10/-8", 10, -8, "Kraken", "Bob", 140, 4, from_lot_unique_id="4", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-16"]}, cost_basis_day=4),
                        IntraTransactionDescriptor("11", 11, 11, "Kraken", "Bob", "BlockFi", "Bob", 220, 12, 12),
                        IntraTransactionDescriptor("12", 12, 12, "Kraken", "Bob", "BlockFi", "Bob", 230, 12, 12),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("11/-9", 11, -9, "BlockFi", "Bob", 110, 4, from_lot_unique_id="5/-1", cost_basis_day=1),
                        InTransactionDescriptor("11/-10", 11, -10, "BlockFi", "Bob", 110, 2, from_lot_unique_id="6/-2", cost_basis_day=1),
                        InTransactionDescriptor("11/-11", 11, -11, "BlockFi", "Bob", 130, 2, from_lot_unique_id="6/-3", cost_basis_day=2),
                        InTransactionDescriptor("11/-12", 11, -12, "BlockFi", "Bob", 130, 4, from_lot_unique_id="7/-4", cost_basis_day=2),
                        InTransactionDescriptor("12/-13", 12, -13, "BlockFi", "Bob", 120, 4, from_lot_unique_id="8/-5", cost_basis_day=3),
                        InTransactionDescriptor("12/-14", 12, -14, "BlockFi", "Bob", 120, 2, from_lot_unique_id="9/-6", cost_basis_day=3),
                        InTransactionDescriptor("12/-15", 12, -15, "BlockFi", "Bob", 140, 2, from_lot_unique_id="9/-7", cost_basis_day=4),
                        InTransactionDescriptor("12/-16", 12, -16, "BlockFi", "Bob", 140, 4, from_lot_unique_id="10/-8", cost_basis_day=4),
                        IntraTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", "BlockFi", "Bob", 230, 24, 24),
                        OutTransactionDescriptor("14", 14, 14, "BlockFi", "Bob", 240, 6, 0),
                        IntraTransactionDescriptor("15", 15, 15, "BlockFi", "Bob", "Coinbase", "Bob", 240, 18, 18),
                    ],
                },
                want_error="",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                self._run_test(test, AccountingMethodFIFO())


    # Transfer analysis across different accounts using only LIFO transfer semantics.
    def test_transfer_analysis_success_using_multiple_accounts_and_lifo(self) -> None:
        # Go-style, table-based tests. The input field contains test input and the want field contains the expected results.
        tests: List[_Test] = [
            _Test(
                description="Interlaced in and intra transactions",
                input = [
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                ],
                want = {
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1", "4/-3"]}),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4, to_lot_unique_ids={Account("Kraken", "Bob"): ["4/-2"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2/-1", 2, -1, "Kraken", "Bob", 110, 4, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Bob", 130, 4, from_lot_unique_id="3", cost_basis_day=3),
                        InTransactionDescriptor("4/-3", 4, -3, "Kraken", "Bob", 110, 6, from_lot_unique_id="1", cost_basis_day=1),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Same exchange transfer (but with two different holders). Two in-lots, three transfers",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 8, 7),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 10, 10),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Alice", 150, 12, 12),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Coinbase", "Alice"): ["5/-4"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20, to_lot_unique_ids={Account("Coinbase", "Alice"): ["3/-1", "4/-2", "5/-3"]}),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Alice", 150, 12, 12),
                    ],
                    Account("Coinbase", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Coinbase", "Alice", 120, 7, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Alice", 120, 10, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-3", 5, -3, "Coinbase", "Alice", 120, 3, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Coinbase", "Alice", 110, 9, from_lot_unique_id="1", cost_basis_day=1),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Two in-lots, three transfers: CB->Kraken",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Alice"): ["5/-4"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20, to_lot_unique_ids={Account("Kraken", "Alice"): ["3/-1", "4/-2", "5/-3"]}),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                    ],
                    Account("Kraken", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Alice", 120, 7, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Alice", 120, 10, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-3", 5, -3, "Kraken", "Alice", 120, 3, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Kraken", "Alice", 110, 9, from_lot_unique_id="1", cost_basis_day=1),
                    ],
                },
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                description="Reciprocal transfer on same exchange but different holders: Bob -> Alice, Alice -> Bob",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Alice", 120, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 4, 3),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Alice", "Coinbase", "Bob", 140, 7, 6),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Coinbase", "Alice"): ["3/-1"]}),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 4, 3),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 6, from_lot_unique_id="2", cost_basis_day=2),
                    ],
                    Account("Coinbase", "Alice"): [
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Alice", 120, 10, to_lot_unique_ids={Account("Coinbase", "Bob"): ["4/-2"]}),
                        InTransactionDescriptor("3/-1", 3, -1, "Coinbase", "Alice", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Alice", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                description="Reciprocal transfer: CB->Kraken, Kraken->CB",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                    IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["3/-1"]}),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 6, from_lot_unique_id="2", cost_basis_day=2),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10, to_lot_unique_ids={Account("Coinbase", "Bob"): ["4/-2"]}),
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Many transactions with loops, sales and self-transfers across three accounts",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 6),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 130, 6),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 6),
                    InTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 6),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 160, 4, 4),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Kraken", "Bob", 170, 4, 4),
                    IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Kraken", "Bob", 180, 4, 4),
                    IntraTransactionDescriptor("8", 8, 8, "Coinbase", "Bob", "Kraken", "Bob", 190, 4, 4),
                    IntraTransactionDescriptor("9", 9, 9, "Coinbase", "Bob", "Kraken", "Bob", 200, 4, 4),
                    IntraTransactionDescriptor("10", 10, 10, "Coinbase", "Bob", "Kraken", "Bob", 210, 4, 4),
                    IntraTransactionDescriptor("11", 11, 11, "Kraken", "Bob", "BlockFi", "Bob", 220, 12, 12),
                    IntraTransactionDescriptor("12", 12, 12, "Kraken", "Bob", "BlockFi", "Bob", 230, 12, 12),
                    IntraTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", "BlockFi", "Bob", 230, 24, 24),
                    OutTransactionDescriptor("14", 14, 14, "BlockFi", "Bob", 240, 6, 0),
                    IntraTransactionDescriptor("15", 15, 15, "BlockFi", "Bob", "Coinbase", "Bob", 240, 18, 18),
                    IntraTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", "Coinbase", "Bob", 250, 18, 18),
                    IntraTransactionDescriptor("17", 17, 17, "Coinbase", "Bob", "Coinbase", "Bob", 260, 18, 18),
                    IntraTransactionDescriptor("18", 18, 18, "Coinbase", "Bob", "Coinbase", "Bob", 270, 18, 18),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["9/-7", "10/-8"], Account("BlockFi", "Bob"): ["12/-15", "12/-16"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 130, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["8/-5", "9/-6"], Account("BlockFi", "Bob"): ["12/-13", "12/-14"]}),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["6/-3", "7/-4"], Account("BlockFi", "Bob"): ["11/-11", "11/-12"]}),
                        InTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["5/-1", "6/-2"], Account("BlockFi", "Bob"): ["11/-9", "11/-10"]}),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 160, 4, 4),
                        IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Kraken", "Bob", 170, 4, 4),
                        IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Kraken", "Bob", 180, 4, 4),
                        IntraTransactionDescriptor("8", 8, 8, "Coinbase", "Bob", "Kraken", "Bob", 190, 4, 4),
                        IntraTransactionDescriptor("9", 9, 9, "Coinbase", "Bob", "Kraken", "Bob", 200, 4, 4),
                        IntraTransactionDescriptor("10", 10, 10, "Coinbase", "Bob", "Kraken", "Bob", 210, 4, 4),
                        IntraTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", "Coinbase", "Bob", 250, 18, 18),
                        IntraTransactionDescriptor("17", 17, 17, "Coinbase", "Bob", "Coinbase", "Bob", 260, 18, 18),
                        IntraTransactionDescriptor("18", 18, 18, "Coinbase", "Bob", "Coinbase", "Bob", 270, 18, 18),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("5/-1", 5, -1, "Kraken", "Bob", 140, 4, from_lot_unique_id="4", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-9"]}, cost_basis_day=4),
                        InTransactionDescriptor("6/-2", 6, -2, "Kraken", "Bob", 140, 2, from_lot_unique_id="4", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-10"]}, cost_basis_day=4),
                        InTransactionDescriptor("6/-3", 6, -3, "Kraken", "Bob", 120, 2, from_lot_unique_id="3", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-11"]}, cost_basis_day=3),
                        InTransactionDescriptor("7/-4", 7, -4, "Kraken", "Bob", 120, 4, from_lot_unique_id="3", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-12"]}, cost_basis_day=3),
                        InTransactionDescriptor("8/-5", 8, -5, "Kraken", "Bob", 130, 4, from_lot_unique_id="2", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-13"]}, cost_basis_day=2),
                        InTransactionDescriptor("9/-6", 9, -6, "Kraken", "Bob", 130, 2, from_lot_unique_id="2", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-14"]}, cost_basis_day=2),
                        InTransactionDescriptor("9/-7", 9, -7, "Kraken", "Bob", 110, 2, from_lot_unique_id="1", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-15"]}, cost_basis_day=1),
                        InTransactionDescriptor("10/-8", 10, -8, "Kraken", "Bob", 110, 4, from_lot_unique_id="1", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-16"]}, cost_basis_day=1),
                        IntraTransactionDescriptor("11", 11, 11, "Kraken", "Bob", "BlockFi", "Bob", 220, 12, 12),
                        IntraTransactionDescriptor("12", 12, 12, "Kraken", "Bob", "BlockFi", "Bob", 230, 12, 12),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("11/-9", 11, -9, "BlockFi", "Bob", 140, 4, from_lot_unique_id="5/-1", cost_basis_day=4),
                        InTransactionDescriptor("11/-10", 11, -10, "BlockFi", "Bob", 140, 2, from_lot_unique_id="6/-2", cost_basis_day=4),
                        InTransactionDescriptor("11/-11", 11, -11, "BlockFi", "Bob", 120, 2, from_lot_unique_id="6/-3", cost_basis_day=3),
                        InTransactionDescriptor("11/-12", 11, -12, "BlockFi", "Bob", 120, 4, from_lot_unique_id="7/-4", cost_basis_day=3),
                        InTransactionDescriptor("12/-13", 12, -13, "BlockFi", "Bob", 130, 4, from_lot_unique_id="8/-5", cost_basis_day=2),
                        InTransactionDescriptor("12/-14", 12, -14, "BlockFi", "Bob", 130, 2, from_lot_unique_id="9/-6", cost_basis_day=2),
                        InTransactionDescriptor("12/-15", 12, -15, "BlockFi", "Bob", 110, 2, from_lot_unique_id="9/-7", cost_basis_day=1),
                        InTransactionDescriptor("12/-16", 12, -16, "BlockFi", "Bob", 110, 4, from_lot_unique_id="10/-8", cost_basis_day=1),
                        IntraTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", "BlockFi", "Bob", 230, 24, 24),
                        OutTransactionDescriptor("14", 14, 14, "BlockFi", "Bob", 240, 6, 0),
                        IntraTransactionDescriptor("15", 15, 15, "BlockFi", "Bob", "Coinbase", "Bob", 240, 18, 18),
                    ]
                },
                want_error="",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                self._run_test(test, AccountingMethodLIFO())


    # Transfer analysis across different accounts using only HIFO transfer semantics.
    def test_transfer_analysis_success_using_multiple_accounts_and_hifo(self) -> None:
        # Go-style, table-based tests. The input field contains test input and the want field contains the expected results.
        tests: List[_Test] = [
            _Test(
                description="Interlaced in and intra transactions",
                input = [
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                ],
                want = {
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1", "4/-3"]}),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4, to_lot_unique_ids={Account("Kraken", "Bob"): ["4/-2"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2/-1", 2, -1, "Kraken", "Bob", 110, 4, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Bob", 130, 4, from_lot_unique_id="3", cost_basis_day=3),
                        InTransactionDescriptor("4/-3", 4, -3, "Kraken", "Bob", 110, 6, from_lot_unique_id="1", cost_basis_day=1),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Same exchange transfer (but with two different holders). Two in-lots, three transfers",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 8, 7),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 10, 10),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Alice", 150, 12, 12),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Coinbase", "Alice"): ["5/-4"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20, to_lot_unique_ids={Account("Coinbase", "Alice"): ["3/-1", "4/-2", "5/-3"]}),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Alice", 150, 12, 12),
                    ],
                    Account("Coinbase", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Coinbase", "Alice", 120, 7, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Alice", 120, 10, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-3", 5, -3, "Coinbase", "Alice", 120, 3, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Coinbase", "Alice", 110, 9, from_lot_unique_id="1", cost_basis_day=1),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Two in-lots, three transfers: CB->Kraken",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Alice"): ["5/-4"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20, to_lot_unique_ids={Account("Kraken", "Alice"): ["3/-1", "4/-2", "5/-3"]}),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                    ],
                    Account("Kraken", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Alice", 120, 7, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Alice", 120, 10, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-3", 5, -3, "Kraken", "Alice", 120, 3, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Kraken", "Alice", 110, 9, from_lot_unique_id="1", cost_basis_day=1),
                    ],
                },
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                description="Reciprocal transfer on same exchange but different holders: Bob -> Alice, Alice -> Bob",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Alice", 120, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 4, 3),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Alice", "Coinbase", "Bob", 140, 7, 6),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Coinbase", "Alice"): ["3/-1"]}),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 6, from_lot_unique_id="2", cost_basis_day=2),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 4, 3),
                    ],
                    Account("Coinbase", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Coinbase", "Alice", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Alice", 120, 10, to_lot_unique_ids={Account("Coinbase", "Bob"): ["4/-2"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Alice", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                description="Reciprocal transfer: CB->Kraken, Kraken->CB",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                    IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["3/-1"]}),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 6, from_lot_unique_id="2", cost_basis_day=2),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10, to_lot_unique_ids={Account("Coinbase", "Bob"): ["4/-2"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Many transactions with loops, sales and self-transfers across three accounts",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 6),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 130, 6),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 6),
                    InTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 6),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 160, 4, 4),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Kraken", "Bob", 170, 4, 4),
                    IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Kraken", "Bob", 180, 4, 4),
                    IntraTransactionDescriptor("8", 8, 8, "Coinbase", "Bob", "Kraken", "Bob", 190, 4, 4),
                    IntraTransactionDescriptor("9", 9, 9, "Coinbase", "Bob", "Kraken", "Bob", 200, 4, 4),
                    IntraTransactionDescriptor("10", 10, 10, "Coinbase", "Bob", "Kraken", "Bob", 210, 4, 4),
                    IntraTransactionDescriptor("11", 11, 11, "Kraken", "Bob", "BlockFi", "Bob", 220, 12, 12),
                    IntraTransactionDescriptor("12", 12, 12, "Kraken", "Bob", "BlockFi", "Bob", 230, 12, 12),
                    IntraTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", "BlockFi", "Bob", 230, 24, 24),
                    OutTransactionDescriptor("14", 14, 14, "BlockFi", "Bob", 240, 6, 0),
                    IntraTransactionDescriptor("15", 15, 15, "BlockFi", "Bob", "Coinbase", "Bob", 240, 18, 18),
                    IntraTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", "Coinbase", "Bob", 250, 18, 18),
                    IntraTransactionDescriptor("17", 17, 17, "Coinbase", "Bob", "Coinbase", "Bob", 260, 18, 18),
                    IntraTransactionDescriptor("18", 18, 18, "Coinbase", "Bob", "Coinbase", "Bob", 270, 18, 18),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["9/-7", "10/-8"], Account("BlockFi", "Bob"): ["12/-15", "12/-16"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 130, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["6/-3", "7/-4"], Account("BlockFi", "Bob"): ["11/-11", "11/-12"]}),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["8/-5", "9/-6"], Account("BlockFi", "Bob"): ["12/-13", "12/-14"]}),
                        InTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["5/-1", "6/-2"], Account("BlockFi", "Bob"): ["11/-9", "11/-10"]}),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 160, 4, 4),
                        IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Kraken", "Bob", 170, 4, 4),
                        IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Kraken", "Bob", 180, 4, 4),
                        IntraTransactionDescriptor("8", 8, 8, "Coinbase", "Bob", "Kraken", "Bob", 190, 4, 4),
                        IntraTransactionDescriptor("9", 9, 9, "Coinbase", "Bob", "Kraken", "Bob", 200, 4, 4),
                        IntraTransactionDescriptor("10", 10, 10, "Coinbase", "Bob", "Kraken", "Bob", 210, 4, 4),
                        IntraTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", "Coinbase", "Bob", 250, 18, 18),
                        IntraTransactionDescriptor("17", 17, 17, "Coinbase", "Bob", "Coinbase", "Bob", 260, 18, 18),
                        IntraTransactionDescriptor("18", 18, 18, "Coinbase", "Bob", "Coinbase", "Bob", 270, 18, 18),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("5/-1", 5, -1, "Kraken", "Bob", 140, 4, from_lot_unique_id="4", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-9"]}, cost_basis_day=4),
                        InTransactionDescriptor("6/-2", 6, -2, "Kraken", "Bob", 140, 2, from_lot_unique_id="4", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-10"]}, cost_basis_day=4),
                        InTransactionDescriptor("6/-3", 6, -3, "Kraken", "Bob", 130, 2, from_lot_unique_id="2", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-11"]}, cost_basis_day=2),
                        InTransactionDescriptor("7/-4", 7, -4, "Kraken", "Bob", 130, 4, from_lot_unique_id="2", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-12"]}, cost_basis_day=2),
                        InTransactionDescriptor("8/-5", 8, -5, "Kraken", "Bob", 120, 4, from_lot_unique_id="3", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-13"]}, cost_basis_day=3),
                        InTransactionDescriptor("9/-6", 9, -6, "Kraken", "Bob", 120, 2, from_lot_unique_id="3", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-14"]}, cost_basis_day=3),
                        InTransactionDescriptor("9/-7", 9, -7, "Kraken", "Bob", 110, 2, from_lot_unique_id="1", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-15"]}, cost_basis_day=1),
                        InTransactionDescriptor("10/-8", 10, -8, "Kraken", "Bob", 110, 4, from_lot_unique_id="1", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-16"]}, cost_basis_day=1),
                        IntraTransactionDescriptor("11", 11, 11, "Kraken", "Bob", "BlockFi", "Bob", 220, 12, 12),
                        IntraTransactionDescriptor("12", 12, 12, "Kraken", "Bob", "BlockFi", "Bob", 230, 12, 12),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("11/-9", 11, -9, "BlockFi", "Bob", 140, 4, from_lot_unique_id="5/-1", cost_basis_day=4),
                        InTransactionDescriptor("11/-10", 11, -10, "BlockFi", "Bob", 140, 2, from_lot_unique_id="6/-2", cost_basis_day=4),
                        InTransactionDescriptor("11/-11", 11, -11, "BlockFi", "Bob", 130, 2, from_lot_unique_id="6/-3", cost_basis_day=2),
                        InTransactionDescriptor("11/-12", 11, -12, "BlockFi", "Bob", 130, 4, from_lot_unique_id="7/-4", cost_basis_day=2),
                        InTransactionDescriptor("12/-13", 12, -13, "BlockFi", "Bob", 120, 4, from_lot_unique_id="8/-5", cost_basis_day=3),
                        InTransactionDescriptor("12/-14", 12, -14, "BlockFi", "Bob", 120, 2, from_lot_unique_id="9/-6", cost_basis_day=3),
                        InTransactionDescriptor("12/-15", 12, -15, "BlockFi", "Bob", 110, 2, from_lot_unique_id="9/-7", cost_basis_day=1),
                        InTransactionDescriptor("12/-16", 12, -16, "BlockFi", "Bob", 110, 4, from_lot_unique_id="10/-8", cost_basis_day=1),
                        IntraTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", "BlockFi", "Bob", 230, 24, 24),
                        OutTransactionDescriptor("14", 14, 14, "BlockFi", "Bob", 240, 6, 0),
                        IntraTransactionDescriptor("15", 15, 15, "BlockFi", "Bob", "Coinbase", "Bob", 240, 18, 18),
                    ]
                },
                want_error="",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                self._run_test(test, AccountingMethodHIFO())


    # Transfer analysis across different accounts using only LOFO transfer semantics.
    def test_transfer_analysis_success_using_multiple_accounts_and_lofo(self) -> None:
        # Go-style, table-based tests. The input field contains test input and the want field contains the expected results.
        tests: List[_Test] = [
            _Test(
                description="Interlaced in and intra transactions",
                input = [
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                ],
                want = {
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1", "4/-2"]}),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 4, to_lot_unique_ids={Account("Kraken", "Bob"): ["4/-3"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 10, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("2/-1", 2, -1, "Kraken", "Bob", 110, 4, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Bob", 110, 6, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-3", 4, -3, "Kraken", "Bob", 130, 4, from_lot_unique_id="3", cost_basis_day=3),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Same exchange transfer (but with two different holders). Two in-lots, three transfers",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 8, 7),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 10, 10),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Alice", 150, 12, 12),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Coinbase", "Alice"): ["3/-1", "4/-2"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20, to_lot_unique_ids={Account("Coinbase", "Alice"): ["4/-3", "5/-4"]}),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Alice", 150, 12, 12),
                    ],
                    Account("Coinbase", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Coinbase", "Alice", 110, 7, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Alice", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-3", 4, -3, "Coinbase", "Alice", 120, 7, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Coinbase", "Alice", 120, 12, from_lot_unique_id="2", cost_basis_day=2),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Two in-lots, three transfers: CB->Kraken",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Alice"): ["3/-1", "4/-2"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20, to_lot_unique_ids={Account("Kraken", "Alice"): ["4/-3", "5/-4"]}),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                    ],
                    Account("Kraken", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Alice", 110, 7, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-2", 4, -2, "Kraken", "Alice", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("4/-3", 4, -3, "Kraken", "Alice", 120, 7, from_lot_unique_id="2", cost_basis_day=2),
                        InTransactionDescriptor("5/-4", 5, -4, "Kraken", "Alice", 120, 12, from_lot_unique_id="2", cost_basis_day=2),
                    ],
                },
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                # Note that using LOFO, the funds sent with transaction 3 are picked to be sent back with transaction 4. This triggers the loop detection
                # logic: so there is no artificial transaction created for the 3 BTC set with transaction 4 (because these coins are being sent back to
                # their place of origin): the transfer analysis algorithm simply increases the partial amount of transaction 1 by 3.
                description="Reciprocal transfer on same exchange but different holders: Bob -> Alice, Alice -> Bob",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Alice", 120, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 4, 3),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Alice", "Coinbase", "Bob", 140, 7, 6),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Coinbase", "Alice"): ["3/-1"]}),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 3, from_lot_unique_id="2", cost_basis_day=2),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 4, 3),
                    ],
                    Account("Coinbase", "Alice"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Coinbase", "Alice", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Alice", 120, 10, to_lot_unique_ids={Account("Coinbase", "Bob"): ["4/-2"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Alice", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                want_error="",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                # Note that using LOFO, the funds sent with transaction 3 are picked to be sent back with transaction 4. This triggers the loop detection
                # logic: so there is no artificial transaction created for the 3 BTC set with transaction 4 (because these coins are being sent back to
                # their place of origin): the transfer analysis algorithm simply increases the partial amount of transaction 1 by 3.
                 description="Reciprocal transfer: CB->Kraken, Kraken->CB",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                    IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["3/-1"]}),
                        InTransactionDescriptor("4/-2", 4, -2, "Coinbase", "Bob", 120, 3, from_lot_unique_id="2", cost_basis_day=2),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("3/-1", 3, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1", cost_basis_day=1),
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10, to_lot_unique_ids={Account("Coinbase", "Bob"): ["4/-2"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Many transactions with loops and self-transfers across three accounts",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 6),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 130, 6),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 6),
                    InTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 6),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 160, 4, 4),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Kraken", "Bob", 170, 4, 4),
                    IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Kraken", "Bob", 180, 4, 4),
                    IntraTransactionDescriptor("8", 8, 8, "Coinbase", "Bob", "Kraken", "Bob", 190, 4, 4),
                    IntraTransactionDescriptor("9", 9, 9, "Coinbase", "Bob", "Kraken", "Bob", 200, 4, 4),
                    IntraTransactionDescriptor("10", 10, 10, "Coinbase", "Bob", "Kraken", "Bob", 210, 4, 4),
                    IntraTransactionDescriptor("11", 11, 11, "Kraken", "Bob", "BlockFi", "Bob", 220, 12, 12),
                    IntraTransactionDescriptor("12", 12, 12, "Kraken", "Bob", "BlockFi", "Bob", 230, 12, 12),
                    IntraTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", "BlockFi", "Bob", 230, 24, 24),
                    OutTransactionDescriptor("14", 14, 14, "BlockFi", "Bob", 240, 6, 0),
                    IntraTransactionDescriptor("15", 15, 15, "BlockFi", "Bob", "Coinbase", "Bob", 240, 18, 18),
                    IntraTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", "Coinbase", "Bob", 250, 18, 18),
                    IntraTransactionDescriptor("17", 17, 17, "Coinbase", "Bob", "Coinbase", "Bob", 260, 18, 18),
                    IntraTransactionDescriptor("18", 18, 18, "Coinbase", "Bob", "Coinbase", "Bob", 270, 18, 18),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["5/-1", "6/-2"], Account("BlockFi", "Bob"): ["11/-9", "11/-10"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 130, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["8/-5", "9/-6"], Account("BlockFi", "Bob"): ["12/-13", "12/-14"]}),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 120, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["6/-3", "7/-4"], Account("BlockFi", "Bob"): ["11/-11", "11/-12"]}),
                        InTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 6, to_lot_unique_ids={Account("Kraken", "Bob"): ["9/-7", "10/-8"], Account("BlockFi", "Bob"): ["12/-15", "12/-16"]}),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 160, 4, 4),
                        IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Kraken", "Bob", 170, 4, 4),
                        IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Kraken", "Bob", 180, 4, 4),
                        IntraTransactionDescriptor("8", 8, 8, "Coinbase", "Bob", "Kraken", "Bob", 190, 4, 4),
                        IntraTransactionDescriptor("9", 9, 9, "Coinbase", "Bob", "Kraken", "Bob", 200, 4, 4),
                        IntraTransactionDescriptor("10", 10, 10, "Coinbase", "Bob", "Kraken", "Bob", 210, 4, 4),
                        IntraTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", "Coinbase", "Bob", 250, 18, 18),
                        IntraTransactionDescriptor("17", 17, 17, "Coinbase", "Bob", "Coinbase", "Bob", 260, 18, 18),
                        IntraTransactionDescriptor("18", 18, 18, "Coinbase", "Bob", "Coinbase", "Bob", 270, 18, 18),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("5/-1", 5, -1, "Kraken", "Bob", 110, 4, from_lot_unique_id="1", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-9"]}, cost_basis_day=1),
                        InTransactionDescriptor("6/-2", 6, -2, "Kraken", "Bob", 110, 2, from_lot_unique_id="1", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-10"]}, cost_basis_day=1),
                        InTransactionDescriptor("6/-3", 6, -3, "Kraken", "Bob", 120, 2, from_lot_unique_id="3", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-11"]}, cost_basis_day=3),
                        InTransactionDescriptor("7/-4", 7, -4, "Kraken", "Bob", 120, 4, from_lot_unique_id="3", to_lot_unique_ids={Account("BlockFi", "Bob"): ["11/-12"]}, cost_basis_day=3),
                        InTransactionDescriptor("8/-5", 8, -5, "Kraken", "Bob", 130, 4, from_lot_unique_id="2", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-13"]}, cost_basis_day=2),
                        InTransactionDescriptor("9/-6", 9, -6, "Kraken", "Bob", 130, 2, from_lot_unique_id="2", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-14"]}, cost_basis_day=2),
                        InTransactionDescriptor("9/-7", 9, -7, "Kraken", "Bob", 140, 2, from_lot_unique_id="4", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-15"]}, cost_basis_day=4),
                        InTransactionDescriptor("10/-8", 10, -8, "Kraken", "Bob", 140, 4, from_lot_unique_id="4", to_lot_unique_ids={Account("BlockFi", "Bob"): ["12/-16"]}, cost_basis_day=4),
                        IntraTransactionDescriptor("11", 11, 11, "Kraken", "Bob", "BlockFi", "Bob", 220, 12, 12),
                        IntraTransactionDescriptor("12", 12, 12, "Kraken", "Bob", "BlockFi", "Bob", 230, 12, 12),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("11/-9", 11, -9, "BlockFi", "Bob", 110, 4, from_lot_unique_id="5/-1", cost_basis_day=1),
                        InTransactionDescriptor("11/-10", 11, -10, "BlockFi", "Bob", 110, 2, from_lot_unique_id="6/-2", cost_basis_day=1),
                        InTransactionDescriptor("11/-11", 11, -11, "BlockFi", "Bob", 120, 2, from_lot_unique_id="6/-3", cost_basis_day=3),
                        InTransactionDescriptor("11/-12", 11, -12, "BlockFi", "Bob", 120, 4, from_lot_unique_id="7/-4", cost_basis_day=3),
                        InTransactionDescriptor("12/-13", 12, -13, "BlockFi", "Bob", 130, 4, from_lot_unique_id="8/-5", cost_basis_day=2),
                        InTransactionDescriptor("12/-14", 12, -14, "BlockFi", "Bob", 130, 2, from_lot_unique_id="9/-6", cost_basis_day=2),
                        InTransactionDescriptor("12/-15", 12, -15, "BlockFi", "Bob", 140, 2, from_lot_unique_id="9/-7", cost_basis_day=4),
                        InTransactionDescriptor("12/-16", 12, -16, "BlockFi", "Bob", 140, 4, from_lot_unique_id="10/-8", cost_basis_day=4),
                        IntraTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", "BlockFi", "Bob", 230, 24, 24),
                        OutTransactionDescriptor("14", 14, 14, "BlockFi", "Bob", 240, 6, 0),
                        IntraTransactionDescriptor("15", 15, 15, "BlockFi", "Bob", "Coinbase", "Bob", 240, 18, 18),
                    ]
                },
                want_error="",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                self._run_test(test, AccountingMethodLOFO())


if __name__ == "__main__":
    unittest.main()

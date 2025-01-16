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

from rp2.in_transaction import Account

from transfer_analysis_test_common import _Test, InTransactionDescriptor, OutTransactionDescriptor, IntraTransactionDescriptor, AbstractTestPerWalletTaxEngine


# These tests are independent of the accounting method, so they are repeated for all accounting methods.
class TestPerWalletTaxEngine(AbstractTestPerWalletTaxEngine):

    # Transfer analysis failure tests. These tests are independent of transfer semantics, so the code repeats each test with all transfer semantics.
    def test_transfer_analysis_failure_all_transfer_semantics(self) -> None:
        # Go-style, table-based tests. The input field contains test input and the want_error field contains the expected error message.
        tests: List[_Test] = [
            _Test(
                description="Transfer more than is available (one in, one intra)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 20, 20),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 10 B1\): .*",
            ),
            _Test(
                description="Sell more than is available (one in, one out)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    OutTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 10, 1),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to cover out transaction \(amount 1 B1\): .*",
            ),
            _Test(
                description="Transfer more than is available (three in, one intra)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 20, 20),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 6 B1\): .*",
            ),
            _Test(
                description="Sell more than is available (three in, one out)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    OutTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 20, 0),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to cover out transaction \(amount 6 B1\): .*",
            ),
            _Test(
                description="Transfer more than is available (three in, three intra)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 12, 11),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 150, 11, 10),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Kraken", "Bob", 160, 16, 15),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 7 B1\): .*",
            ),
            _Test(
                description="Sell more than is available (three in, three out)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    OutTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 11, 0),
                    OutTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", 150, 3, 0),
                    OutTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", 160, 3, 1),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to cover out transaction \(amount 4 B1\): .*",
            ),
            _Test(
                description="Sell more than is available (three in, two intra, one out)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 12, 11),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 150, 2, 2),
                    OutTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", 160, 1, 1),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to cover out transaction \(amount 1 B1\): .*",
            ),
            _Test(
                description="Sell more than is available (three in, two out, one intra)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    OutTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 10, 1),
                    OutTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", 150, 2, 0),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Kraken", "Bob", 160, 6, 6),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 5 B1\): .*",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2558165460
                description="Transfer more than is available at timestamp 3 (even though funds with earlier cost_basis_timestamp will be available at timestamp 4)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 1),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 3, 3),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 5, 5),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Kraken', holder='Bob'\) to send funds \(amount 2 B1\): .*",
            ),
            _Test(
                # This test is from the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2558165460
                description="Sell more than is available at timestamp 3 (even though funds with earlier cost_basis_timestamp will be available at timestamp 4)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 1),
                    OutTransactionDescriptor("3", 3, 3, "Kraken", "Bob", 130, 1, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 5, 5),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Kraken', holder='Bob'\) to cover out transaction \(amount 2 B1\): .*",
            ),
            _Test(
                description="Same-account transfer. Transfer more than is available (one in, one intra)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Coinbase", "Bob", 120, 20, 20),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 10 B1\): .*",
            ),
            _Test(
                description="Same-account transfer. Transfer more than is available in last intra (three in, four intra)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Bob", 140, 15, 14),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Bob", 150, 14, 13),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Coinbase", "Bob", 160, 14, 14),
                    IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Coinbase", "Bob", 170, 16, 15),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 1 B1\): .*",
            ),
            _Test(
                description=("Same-exchange transfers with different holders. Total transferred sum is greater than crypto in amount (one in, three intra)."),
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Coinbase", "Alice", 120, 9, 8),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 10, 10),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 10, 9),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 8 B1\): .*",
            ),
            _Test(
                description=("Same-exchange transfers with different holders. Total transferred sum is greater than crypto in amount (three in, three intra)."),
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 14, 13),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Alice", 150, 12, 12),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Coinbase", "Alice", 150, 14, 14),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 11 B1\): .*",
            ),
            _Test(
                description="Loop followed by excessive transfer on starting exchange: CB->Kraken->BlockFi->CB + CB->Kraken (not enough funds)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 150, 8, 8),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 1 B1\): .*",
            ),
            _Test(
                description="Loop followed by excessive sale on original exchange: CB->Kraken->BlockFi->CB + OutTransaction (not enough funds)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                    OutTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", 150, 9, 0),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to cover out transaction \(amount 2 B1\): .*",
            ),
            _Test(
                description="Many transactions with loops and self-transfers across three accounts. Excessive transfer at the end of the cycle",
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
                    IntraTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", "Coinbase", "Bob", 240, 25, 25),
                    IntraTransactionDescriptor("14", 14, 14, "Coinbase", "Bob", "Coinbase", "Bob", 250, 24, 24),
                    IntraTransactionDescriptor("15", 15, 15, "Coinbase", "Bob", "Coinbase", "Bob", 260, 24, 24),
                    IntraTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", "Coinbase", "Bob", 270, 24, 24),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='BlockFi', holder='Bob'\) to send funds \(amount 1 B1\): .*",
            ),
            _Test(
                description="Many transactions with loops and self-transfers across three accounts. Excessive sale at the end of the cycle",
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
                    OutTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", 240, 24, 3),
                    IntraTransactionDescriptor("14", 14, 14, "Coinbase", "Bob", "Coinbase", "Bob", 250, 24, 24),
                    IntraTransactionDescriptor("15", 15, 15, "Coinbase", "Bob", "Coinbase", "Bob", 260, 24, 24),
                    IntraTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", "Coinbase", "Bob", 270, 24, 24),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='BlockFi', holder='Bob'\) to cover out transaction \(amount 3 B1\): .*",
            ),
            _Test(
                description="Many transactions with loops and self-transfers across three accounts. One excessive self-transfer",
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
                    IntraTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", "Coinbase", "Bob", 240, 24, 24),
                    IntraTransactionDescriptor("14", 14, 14, "Coinbase", "Bob", "Coinbase", "Bob", 250, 24, 24),
                    IntraTransactionDescriptor("15", 15, 15, "Coinbase", "Bob", "Coinbase", "Bob", 260, 24, 24),
                    IntraTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", "Coinbase", "Bob", 270, 25, 25),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 1 B1\): .*",
            ),
            _Test(
                description="Many transactions with loops and self-transfers across three accounts. Excessive sale after self-transfers",
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
                    IntraTransactionDescriptor("13", 13, 13, "BlockFi", "Bob", "Coinbase", "Bob", 240, 24, 24),
                    IntraTransactionDescriptor("14", 14, 14, "Coinbase", "Bob", "Coinbase", "Bob", 250, 24, 24),
                    IntraTransactionDescriptor("15", 15, 15, "Coinbase", "Bob", "Coinbase", "Bob", 260, 24, 24),
                    OutTransactionDescriptor("16", 16, 16, "Coinbase", "Bob", 270, 30, 0),
                ],
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to cover out transaction \(amount 6 B1\): .*",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                for transfer_semantics in self._transfer_semantics:
                    self._run_test(test, transfer_semantics)

    # Transfer analysis from / to the same account. These tests are independent of transfer semantics because they only use self transfers (which don't
    # generate transfer-semantics-dependent artificial transactions), so the code repeats each test with all transfer semantics.
    def test_transfer_analysis_success_using_same_account_and_all_semantics(self) -> None:
        # Go-style, table-based tests. The input field contains test input and the want field contains the expected result.
        tests: List[_Test] = [
            _Test(
                description=(
                    "Same-account transfers. Total transferred sum is greater than crypto in amount, but individual transfers are not (one in, three intra)."
                ),
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Coinbase", "Bob", 120, 9, 8),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Bob", 130, 10, 10),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Bob", 140, 10, 9),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Coinbase", "Bob", 120, 9, 8),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Bob", 130, 10, 10),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Bob", 140, 10, 9),
                    ],
                },
                want_error="",
            ),
            _Test(
                description=(
                    "Same-account transfer. Total transferred sum is greater than crypto in amount, " "but individual transfers are not (three in, three intra)"
                ),
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Bob", 140, 14, 13),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Bob", 150, 12, 12),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Coinbase", "Bob", 150, 14, 14),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                        InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Bob", 140, 14, 13),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Bob", 150, 12, 12),
                        IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Coinbase", "Bob", 150, 14, 14),
                    ],
                },
                want_error="",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                for transfer_semantics in self._transfer_semantics:
                    self._run_test(test, transfer_semantics)

    # Transfer analysis across different accounts, but with only one InTransaction (this makes these tests independent of transfer semantics), so the code
    # repeats each test with all transfer semantics.
    def test_transfer_analysis_success_using_semantics_independent_scenario_and_all_semantics(self) -> None:
        # Go-style, table-based tests. The input field contains test input and the want field contains the expected results.
        tests: List[_Test] = [
            _Test(
                description="Two different paths from Coinbase to BlockFi: CB->Kraken->BlockFi, CB->BlockFi",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "BlockFi", "Bob", 140, 5, 5),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor(
                            "1",
                            1,
                            1,
                            "Coinbase",
                            "Bob",
                            110,
                            10,
                            to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1"], Account("BlockFi", "Bob"): ["3/-2", "4/-3"]},
                        ),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "BlockFi", "Bob", 140, 5, 5),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor(
                            "2/-1",
                            2,
                            -1,
                            "Kraken",
                            "Bob",
                            110,
                            4,
                            from_lot_unique_id="1",
                            to_lot_unique_ids={Account("BlockFi", "Bob"): ["3/-2"]},
                            cost_basis_day=1,
                        ),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3/-2", 3, -2, "BlockFi", "Bob", 110, 2, from_lot_unique_id="2/-1", cost_basis_day=1),
                        InTransactionDescriptor("4/-3", 4, -3, "BlockFi", "Bob", 110, 5, from_lot_unique_id="1", cost_basis_day=1),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Loop: CB->Kraken->BlockFi->CB",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor(
                            "1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1"], Account("BlockFi", "Bob"): ["3/-2"]}
                        ),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor(
                            "2/-1",
                            2,
                            -1,
                            "Kraken",
                            "Bob",
                            110,
                            4,
                            from_lot_unique_id="1",
                            to_lot_unique_ids={Account("BlockFi", "Bob"): ["3/-2"]},
                            cost_basis_day=1,
                        ),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3/-2", 3, -2, "BlockFi", "Bob", 110, 2, from_lot_unique_id="2/-1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Loop followed by depletion of original exchange via a transfer: CB->Kraken->BlockFi->CB + CB->Kraken (depletion)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 150, 7, 7),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor(
                            "1",
                            1,
                            1,
                            "Coinbase",
                            "Bob",
                            110,
                            10,
                            to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1", "5/-3"], Account("BlockFi", "Bob"): ["3/-2"]},
                        ),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 150, 7, 7),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor(
                            "2/-1",
                            2,
                            -1,
                            "Kraken",
                            "Bob",
                            110,
                            4,
                            from_lot_unique_id="1",
                            to_lot_unique_ids={Account("BlockFi", "Bob"): ["3/-2"]},
                            cost_basis_day=1,
                        ),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                        InTransactionDescriptor("5/-3", 5, -3, "Kraken", "Bob", 110, 7, from_lot_unique_id="1", cost_basis_day=1),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3/-2", 3, -2, "BlockFi", "Bob", 110, 2, from_lot_unique_id="2/-1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Loop followed by depletion of original exchange via a sale: CB->Kraken->BlockFi->CB + Coinbase sale (depletion)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                    OutTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", 150, 7, 0),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor(
                            "1",
                            1,
                            1,
                            "Coinbase",
                            "Bob",
                            110,
                            10,
                            to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1"], Account("BlockFi", "Bob"): ["3/-2"]},
                        ),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        OutTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", 150, 7, 0),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor(
                            "2/-1",
                            2,
                            -1,
                            "Kraken",
                            "Bob",
                            110,
                            4,
                            from_lot_unique_id="1",
                            to_lot_unique_ids={Account("BlockFi", "Bob"): ["3/-2"]},
                            cost_basis_day=1,
                        ),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3/-2", 3, -2, "BlockFi", "Bob", 110, 2, from_lot_unique_id="2/-1", cost_basis_day=1),
                        IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Transfer followed by multiple self-transfers: CB->Kraken, Kraken->Kraken...",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 10, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "Kraken", "Bob", 130, 10, 10),
                    IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Kraken", "Bob", 140, 10, 10),
                    IntraTransactionDescriptor("5", 5, 5, "Kraken", "Bob", "Kraken", "Bob", 150, 10, 10),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor(
                            "1",
                            1,
                            1,
                            "Coinbase",
                            "Bob",
                            110,
                            10,
                            to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1"]},
                        ),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 10, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor(
                            "2/-1",
                            2,
                            -1,
                            "Kraken",
                            "Bob",
                            110,
                            10,
                            from_lot_unique_id="1",
                            cost_basis_day=1,
                        ),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "Kraken", "Bob", 130, 10, 10),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Kraken", "Bob", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Kraken", "Bob", "Kraken", "Bob", 150, 10, 10),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Loop followed by multiple self-transfers: CB->Kraken, Kraken->CB, CB->CB...",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 10, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "Coinbase", "Bob", 130, 10, 10),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Bob", 140, 10, 10),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Bob", 150, 10, 10),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Coinbase", "Bob", 160, 10, 10),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor(
                            "1",
                            1,
                            1,
                            "Coinbase",
                            "Bob",
                            110,
                            10,
                            to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1"]},
                        ),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 10, 10),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Bob", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Bob", 150, 10, 10),
                        IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Coinbase", "Bob", 160, 10, 10),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor(
                            "2/-1",
                            2,
                            -1,
                            "Kraken",
                            "Bob",
                            110,
                            10,
                            from_lot_unique_id="1",
                            cost_basis_day=1,
                        ),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "Coinbase", "Bob", 130, 10, 10),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Loop followed by a sale, followed by multiple self-transfers: CB->Kraken, Kraken->CB, CB sale, CB->CB...",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 10, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "Coinbase", "Bob", 130, 10, 10),
                    OutTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 5, 0),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Bob", 140, 5, 5),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Coinbase", "Bob", 150, 5, 5),
                    IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Coinbase", "Bob", 160, 5, 5),
                ],
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor(
                            "1",
                            1,
                            1,
                            "Coinbase",
                            "Bob",
                            110,
                            10,
                            to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1"]},
                        ),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 10, 10),
                        OutTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", 140, 5, 0),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Bob", 140, 5, 5),
                        IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Coinbase", "Bob", 150, 5, 5),
                        IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Coinbase", "Bob", 160, 5, 5),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor(
                            "2/-1",
                            2,
                            -1,
                            "Kraken",
                            "Bob",
                            110,
                            10,
                            from_lot_unique_id="1",
                            cost_basis_day=1,
                        ),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "Coinbase", "Bob", 130, 10, 10),
                    ],
                },
                want_error="",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                for transfer_semantics in self._transfer_semantics:
                    self._run_test(test, transfer_semantics)


if __name__ == "__main__":
    unittest.main()

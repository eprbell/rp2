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

from dataclasses import dataclass
from difflib import unified_diff
from typing import Dict, List

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.configuration import Configuration
from rp2.in_transaction import Account
from rp2.plugin.country.us import US
from rp2.rp2_error import RP2ValueError
from rp2.transfer_analyzer import TransferAnalyzer
from transaction_processing_common import AbstractTestTransactionProcessing, AbstractTransactionDescriptor


@dataclass(frozen=True, eq=True)
class _Test:
    # English description of the test.
    description: str
    # List of universal-application, input transactions.
    input: List[AbstractTransactionDescriptor]
    # Dictionary of expected per-wallet, input transactions: this is the wanted output of transfer analysis.
    want_per_wallet_transactions: Dict[Account, List[AbstractTransactionDescriptor]]
    # Dictionary of expected actual amounts from transfer analysis: this contains the actual crypto amounts of the per-wallet in-transactions. It
    # is useful to understand where the funds are, because in per-wallet application there can be multiple in-transactions covering the same
    # funds in different exchanges: artificial in-transactions are created when processing intra-transactions to model the reception of funds).
    want_amounts: Dict[Account, Dict[str, int]]
    # If not empty, the test is expected to raise an error and this is the expected error message.
    want_error: str


class AbstractTransferAnalysis(AbstractTestTransactionProcessing):

    # Run a transfer analysis test.
    def _run_test(self, test: _Test, transfer_semantics: AbstractAccountingMethod) -> None:
        print(f"\nDescription: {test.description:}\nTransfer:    {transfer_semantics}\nWant error:  {'yes' if test.want_error else 'no'}")
        configuration = Configuration("./config/test_data.ini", US())

        # Prepare test input
        universal_input_data = self._create_universal_input_data_from_transaction_descriptors(configuration, test.input)

        # If the test expects an error, run transfer analysis and check for error.
        if test.want_error:
            if test.want_per_wallet_transactions:
                raise ValueError(f"Test data error: both want and want_error are set: {test}")
            with self.assertRaisesRegex(RP2ValueError, test.want_error):
                transfer_analyzer = TransferAnalyzer(configuration, transfer_semantics, universal_input_data)
                transfer_analyzer.analyze()
            return

        # Create transfer analyzer, call analyze() on universal InputData and receive per-wallet InputData.
        transfer_analyzer = TransferAnalyzer(configuration, transfer_semantics, universal_input_data)
        got_wallet_2_per_wallet_input_data = transfer_analyzer.analyze()

        # Create expected per-wallet InputData, based on the want field of the test.
        want_wallet_2_per_wallet_input_data = self._create_per_wallet_input_data_from_transaction_descriptors(configuration, test.want_per_wallet_transactions)

        # Diff got and want per-wallet input data.
        got: List[str] = []
        want: List[str] = []
        for wallet, per_wallet_input_data in got_wallet_2_per_wallet_input_data.items():
            got.append(f"{wallet}:")
            self._serialize_input_data_as_string_list(per_wallet_input_data, got)
        for wallet, per_wallet_input_data in want_wallet_2_per_wallet_input_data.items():
            want.append(f"{wallet}:")
            self._serialize_input_data_as_string_list(per_wallet_input_data, want)
        self.assertEqual("\n".join(unified_diff(got, want, lineterm="", n=10)), "")

        # Diff got and want actual amounts.
        got_actual_amounts: Dict[Account, Dict[str, int]] = {
            wallet: {transaction.unique_id: int(actual_amount) for transaction, actual_amount in per_wallet_input_data.in_transaction_2_actual_amount.items()}
            for wallet, per_wallet_input_data in got_wallet_2_per_wallet_input_data.items()
        }
        self.assertEqual(got_actual_amounts, test.want_amounts)

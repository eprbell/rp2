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
    description: str
    input: List[AbstractTransactionDescriptor]
    want: Dict[Account, List[AbstractTransactionDescriptor]]
    want_error: str


class AbstractTransferAnalysis(AbstractTestTransactionProcessing):

    def _run_test(self, test: _Test, transfer_semantics: AbstractAccountingMethod) -> None:
        print(f"\nDescription: {test.description:}\nTransfer:    {transfer_semantics}\nWant error:  {'yes' if test.want_error else 'no'}")
        configuration = Configuration("./config/test_data.ini", US())

        # Prepare the test input
        universal_input_data = self._create_universal_input_data_from_transaction_descriptors(configuration, test.input)

        # Create TransferAnalyzer.
        transfer_analyzer = TransferAnalyzer(configuration, transfer_semantics, universal_input_data)

        # If the test expects an error, run the test and check for error.
        if test.want_error:
            if test.want:
                raise ValueError(f"Test data error: both want and want_error are set: {test}")
            with self.assertRaisesRegex(RP2ValueError, test.want_error):
                transfer_analyzer.analyze()
            return

        # Call analyze() on universal InputData and receive per-wallet InputData.
        wallet_2_per_wallet_input_data = transfer_analyzer.analyze()

        # Create expected per-wallet InputData, based on the want field of the test.
        want_wallet_2_per_wallet_input_data = self._create_per_wallet_input_data_from_transaction_descriptors(configuration, test.want)

        # Diff got and want results.
        got: List[str] = []
        for wallet, per_wallet_input_data in wallet_2_per_wallet_input_data.items():
            got.append(f"{wallet}:")
            for transaction in per_wallet_input_data.unfiltered_in_transaction_set:
                got.append(f"{transaction}")
            for transaction in per_wallet_input_data.unfiltered_out_transaction_set:
                got.append(f"{transaction}")
            for transaction in per_wallet_input_data.unfiltered_intra_transaction_set:
                got.append(f"{transaction}")

        want: List[str] = []
        for wallet, per_wallet_input_data in want_wallet_2_per_wallet_input_data.items():
            want.append(f"{wallet}:")
            for transaction in per_wallet_input_data.unfiltered_in_transaction_set:
                want.append(f"{transaction}")
            for transaction in per_wallet_input_data.unfiltered_out_transaction_set:
                want.append(f"{transaction}")
            for transaction in per_wallet_input_data.unfiltered_intra_transaction_set:
                want.append(f"{transaction}")

        self.assertEqual("\n".join(unified_diff(got, want, lineterm="")), "")
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

from dataclasses import dataclass
from difflib import unified_diff
from typing import Dict, List

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.configuration import Configuration
from rp2.intra_transaction import IntraTransaction
from rp2.rp2_error import RP2ValueError
from rp2.global_allocation import GlobalAllocator
from rp2.in_transaction import Account

from rp2.plugin.country.us import US
from transaction_processing_common import AbstractTestTransactionProcessing, AbstractTransactionDescriptor, IntraTransactionDescriptor


@dataclass(frozen=True, eq=True)
class _Test:
    # English description of the test.
    description: str
    # Dict of per-wallet-application, input transactions.
    input_per_wallet_transactions: Dict[Account, List[AbstractTransactionDescriptor]]
    # List of accounts in the order they should be processed during global allocation.
    input_account_order: List[Account]
    # Actual in-transaction amounts (in-transactions that are not referenced here have their full crypto-in amount):
    input_actual_amounts: Dict[Account, Dict[str, int]]
    # List of expected universal-application transactions, output of global allocation.
    want_intra_transactions: List[IntraTransactionDescriptor]
    # If not empty, the test is expected to raise an error and this is the expected error message.
    want_error: str


class AbstractGlobalAllocation(AbstractTestTransactionProcessing):

    # Run a global allocation test.
    def _run_test(self, test: _Test, allocation_method: AbstractAccountingMethod) -> None:
        print(f"\nDescription: {test.description:}\nAllocation: {allocation_method}\nWant error:  {'yes' if test.want_error else 'no'}")
        configuration = Configuration("./config/test_data.ini", US())

        # Prepare test input
        wallet_to_per_wallet_input_data = self._create_per_wallet_input_data_from_transaction_descriptors(
            configuration,
            test.input_per_wallet_transactions,
            test.input_actual_amounts
        )

        # If the test expects an error, run global allocation and check for error.
        if test.want_error:
            if test.want_intra_transactions:
                raise ValueError(f"Test data error: both want and want_error are set: {test}")
            with self.assertRaisesRegex(RP2ValueError, test.want_error):
                global_allocator = GlobalAllocator(configuration, allocation_method, wallet_to_per_wallet_input_data, 2025, test.input_account_order)
                global_allocator.allocate()
            return

        # Create global allocator, call allocate() and receive input data after applying global allocation.
        global_allocator = GlobalAllocator(configuration, allocation_method, wallet_to_per_wallet_input_data, 2025, test.input_account_order)
        got_intra_transactions = global_allocator.allocate()

        # Diff got and want results.
        got: List[str] = []
        want: List[str] = []
        want_intra_transactions: List[IntraTransaction] = [self._create_intra_transaction(configuration, descriptor)
                                                           for descriptor in test.want_intra_transactions]
        for intra_transaction in got_intra_transactions:
            got.extend(str(intra_transaction).splitlines())
        for intra_transaction in want_intra_transactions:
            want.extend(str(intra_transaction).splitlines())

        self.assertEqual("\n".join(unified_diff(got, want, lineterm="", n=10)), "", "Global allocation")

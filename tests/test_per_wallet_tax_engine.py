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
from datetime import datetime, timedelta, timezone
from difflib import unified_diff
from typing import Dict, List, Optional

from rp2.abstract_transaction import AbstractTransaction
from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.accounting_engine import AccountingEngine
from rp2.configuration import Configuration
from rp2.in_transaction import Account, InTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.input_data import InputData
from rp2.out_transaction import OutTransaction
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
# from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
# from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2ValueError
from rp2.transaction_set import TransactionSet
from rp2.per_wallet_tax_engine import _transfer_analysis


@dataclass(frozen=True, eq=True)
class AbstractTransactionDescriptor:
    unique_id: str
    day: int
    row: int


@dataclass(frozen=True, eq=True)
class InTransactionDescriptor(AbstractTransactionDescriptor):
    exchange: str
    holder: str
    spot_price: float
    crypto_in: float
    crypto_fee: float = 0
    from_lot_unique_id: Optional[str] = None
    to_lot_unique_ids: Optional[Dict[Account, List[str]]] = None


@dataclass(frozen=True, eq=True)
class OutTransactionDescriptor(AbstractTransactionDescriptor):
    exchange: str
    holder: str
    spot_price: float
    crypto_out_no_fee: float
    crypto_fee: float = 0


@dataclass(frozen=True, eq=True)
class IntraTransactionDescriptor(AbstractTransactionDescriptor):
    from_exchange: str
    from_holder: str
    to_exchange: str
    to_holder: str
    spot_price: float
    crypto_sent: float
    crypto_received: float = 0


@dataclass(frozen=True, eq=True)
class _Test:
    description: str
    input: List[AbstractTransactionDescriptor]
    accounting_method: AbstractAccountingMethod
    want: Dict[Account, List[AbstractTransactionDescriptor]]
    want_error: str


class TestPerWalletTaxEngine(unittest.TestCase):
    _asset: str
    _accounting_engine: AccountingEngine
    _start_date: datetime

    @classmethod
    def setUpClass(cls) -> None:
        TestPerWalletTaxEngine._asset = "B1"
        TestPerWalletTaxEngine._start_date = datetime.strptime("2024-01-02", "%Y-%m-%d").replace(tzinfo=timezone.utc)

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def _list_to_transaction_set(self, configuration: Configuration, transaction_list: List[AbstractTransaction], entry_set_type: str) -> TransactionSet:
        result = TransactionSet(configuration, entry_set_type, self._asset)
        for transaction in transaction_list:
            result.add_entry(transaction)
        return result

    def _create_input_data(
        self,
        configuration: Configuration,
        unique_id_2_in_transaction: Dict[str, InTransaction],
        unique_id_2_out_transaction: Dict[str, OutTransaction],
        unique_id_2_intra_transaction: Dict[str, IntraTransaction],
    ) -> InputData:
        result = InputData(
            self._asset,
            self._list_to_transaction_set(configuration, list(unique_id_2_in_transaction.values()), "IN"),
            self._list_to_transaction_set(configuration, list(unique_id_2_out_transaction.values()), "OUT"),
            self._list_to_transaction_set(configuration, list(unique_id_2_intra_transaction.values()), "INTRA"),
        )
        return result

    def _create_in_transaction(
        self, configuration: Configuration, transaction_descriptor: InTransactionDescriptor, from_lot: Optional["InTransaction"] = None
    ) -> InTransaction:
        timestamp = self._start_date + timedelta(days=transaction_descriptor.day)
        return InTransaction(
            configuration,
            timestamp.isoformat(),
            TestPerWalletTaxEngine._asset,
            transaction_descriptor.exchange,
            transaction_descriptor.holder,
            "BUY",
            RP2Decimal(transaction_descriptor.spot_price),
            RP2Decimal(transaction_descriptor.crypto_in),
            RP2Decimal(transaction_descriptor.crypto_fee),
            row=transaction_descriptor.row,
            unique_id=transaction_descriptor.unique_id,
            from_lot=from_lot,
        )

    def _create_out_transaction(self, configuration: Configuration, transaction_descriptor: OutTransactionDescriptor) -> OutTransaction:
        timestamp = self._start_date + timedelta(days=transaction_descriptor.day)
        return OutTransaction(
            configuration,
            timestamp.isoformat(),
            TestPerWalletTaxEngine._asset,
            transaction_descriptor.exchange,
            transaction_descriptor.holder,
            "Sell",
            RP2Decimal(transaction_descriptor.spot_price),
            RP2Decimal(transaction_descriptor.crypto_out_no_fee),
            RP2Decimal(transaction_descriptor.crypto_fee),
            row=transaction_descriptor.row,
            unique_id=str(transaction_descriptor.unique_id),
        )

    def _create_intra_transaction(self, configuration: Configuration, transaction_descriptor: IntraTransactionDescriptor) -> IntraTransaction:
        timestamp = self._start_date + timedelta(days=transaction_descriptor.day)
        return IntraTransaction(
            configuration,
            timestamp.isoformat(),
            TestPerWalletTaxEngine._asset,
            transaction_descriptor.from_exchange,
            transaction_descriptor.from_holder,
            transaction_descriptor.to_exchange,
            transaction_descriptor.to_holder,
            RP2Decimal(transaction_descriptor.spot_price),
            RP2Decimal(transaction_descriptor.crypto_sent),
            RP2Decimal(transaction_descriptor.crypto_received),
            row=transaction_descriptor.row,
            unique_id=str(transaction_descriptor.unique_id),
        )

    def _create_transactions(
        self,
        configuration: Configuration,
        transaction_descriptors: List[AbstractTransactionDescriptor],
        unique_id_2_in_transaction: Dict[str, InTransaction],
        unique_id_2_out_transaction: Dict[str, OutTransaction],
        unique_id_2_intra_transaction: Dict[str, IntraTransaction],
        deferred_transactions: List[AbstractTransactionDescriptor],
    ) -> None:
        for transaction_descriptor in transaction_descriptors:
            transaction: AbstractTransaction
            if isinstance(transaction_descriptor, InTransactionDescriptor):
                from_lot_unique_id = transaction_descriptor.from_lot_unique_id
                if from_lot_unique_id is not None and from_lot_unique_id not in unique_id_2_in_transaction:
                    # Handle forward references to transactions that have not been created yet (this can happen in cycles).
                    deferred_transactions.append(transaction_descriptor)
                    continue
                from_lot = unique_id_2_in_transaction[from_lot_unique_id] if from_lot_unique_id is not None else None
                transaction = self._create_in_transaction(configuration, transaction_descriptor, from_lot)
                if transaction.unique_id in unique_id_2_in_transaction:
                    raise ValueError(f"Test data error: duplicate unique_id in InTransactions: {transaction.unique_id}")
                unique_id_2_in_transaction[transaction.unique_id] = transaction
            elif isinstance(transaction_descriptor, OutTransactionDescriptor):
                transaction = self._create_out_transaction(configuration, transaction_descriptor)
                if transaction.unique_id in unique_id_2_out_transaction:
                    raise ValueError(f"Test data error: duplicate unique_id in OutTransactions: {transaction.unique_id}")
                unique_id_2_out_transaction[transaction.unique_id] = transaction
            elif isinstance(transaction_descriptor, IntraTransactionDescriptor):
                transaction = self._create_intra_transaction(configuration, transaction_descriptor)
                if transaction.unique_id in unique_id_2_intra_transaction:
                    raise ValueError(f"Test data error: duplicate unique_id in IntraTransactions: {transaction.unique_id}")
                unique_id_2_intra_transaction[transaction.unique_id] = transaction
            else:
                raise ValueError(f"Unknown transaction type: {transaction_descriptor}")


    def _run_test(self, test: _Test) -> None:
        print(f"\n{test.description:} / want error: {'yes' if test.want_error else 'no'}")
        unique_id_2_in_transaction: Dict[str, InTransaction] = {}
        unique_id_2_out_transaction: Dict[str, OutTransaction] = {}
        unique_id_2_intra_transaction: Dict[str, IntraTransaction] = {}
        configuration = Configuration("./config/test_data.ini", US())
        deferred_transactions: List[AbstractTransactionDescriptor] = []

        # Create universal InputData from test data.
        self._create_transactions(
            configuration, test.input, unique_id_2_in_transaction, unique_id_2_out_transaction, unique_id_2_intra_transaction, deferred_transactions
        )
        if deferred_transactions:
            raise ValueError(f"Test data error: universal input data deferred transactions not empty: {deferred_transactions}")
        universal_input_data = self._create_input_data(
            configuration, unique_id_2_in_transaction, unique_id_2_out_transaction, unique_id_2_intra_transaction
        )

        # If the test expects an error, check for it.
        if test.want_error:
            with self.assertRaisesRegex(RP2ValueError, test.want_error):
                if test.want:
                    raise ValueError(f"Test data error: both want and want_error are set: {test}")
                _transfer_analysis(configuration, test.accounting_method, universal_input_data)
            return

        # Call _transfer_analysis on universal InputData and receive per-wallet InputData.
        wallet_2_per_wallet_input_data = _transfer_analysis(configuration, test.accounting_method, universal_input_data)

        # Create expected per-wallet InputData, based on the want field of the test.
        unique_id_2_in_transaction = {}
        unique_id_2_out_transaction = {}
        unique_id_2_intra_transaction = {}
        deferred_transactions = []
        want_wallet_2_per_wallet_input_data: Dict[Account, InputData] = {}
        for _, transaction_descriptors in test.want.items():
            self._create_transactions(
                configuration,
                transaction_descriptors,
                unique_id_2_in_transaction,
                unique_id_2_out_transaction,
                unique_id_2_intra_transaction,
                deferred_transactions,
            )
        while True:
            if not deferred_transactions:
                break
            new_deferred_transactions: List[AbstractTransactionDescriptor] = []
            self._create_transactions(
                configuration,
                deferred_transactions,
                unique_id_2_in_transaction,
                unique_id_2_out_transaction,
                unique_id_2_intra_transaction,
                new_deferred_transactions,
            )
            deferred_transactions = new_deferred_transactions
        for exchange, transaction_descriptors in test.want.items():
            in_transaction_set = TransactionSet(configuration, "IN", self._asset)
            out_transaction_set = TransactionSet(configuration, "OUT", self._asset)
            intra_transaction_set = TransactionSet(configuration, "INTRA", self._asset)
            for transaction_descriptor in transaction_descriptors:
                transaction: AbstractTransaction
                if isinstance(transaction_descriptor, InTransactionDescriptor):
                    transaction = unique_id_2_in_transaction[transaction_descriptor.unique_id]
                    in_transaction_set.add_entry(transaction)
                elif isinstance(transaction_descriptor, OutTransactionDescriptor):
                    transaction = unique_id_2_out_transaction[transaction_descriptor.unique_id]
                    out_transaction_set.add_entry(transaction)
                elif isinstance(transaction_descriptor, IntraTransactionDescriptor):
                    transaction = unique_id_2_intra_transaction[transaction_descriptor.unique_id]
                    intra_transaction_set.add_entry(transaction)
                # Initialize to_lots.
                if (
                    isinstance(transaction, InTransaction)
                    and isinstance(transaction_descriptor, InTransactionDescriptor)
                    and transaction_descriptor.to_lot_unique_ids is not None
                ):
                    for to_account, unique_ids in transaction_descriptor.to_lot_unique_ids.items():
                        for unique_id in unique_ids:
                            to_lots = transaction.to_lots.setdefault(to_account, [])
                            to_lots.append(unique_id_2_in_transaction[unique_id])
            want_wallet_2_per_wallet_input_data[exchange] = InputData(self._asset, in_transaction_set, out_transaction_set, intra_transaction_set)

        # Diff got and want results.
        got: List[str] = []
        for wallet, per_wallet_input_data in wallet_2_per_wallet_input_data.items():
            got.append(f"{wallet}:")
            got.append(f"{per_wallet_input_data.unfiltered_in_transaction_set}")
            got.append(f"{per_wallet_input_data.unfiltered_out_transaction_set}")
            got.append(f"{per_wallet_input_data.unfiltered_intra_transaction_set}")

        want: List[str] = []
        for wallet, per_wallet_input_data in want_wallet_2_per_wallet_input_data.items():
            want.append(f"{wallet}:")
            want.append(f"{per_wallet_input_data.unfiltered_in_transaction_set}")
            want.append(f"{per_wallet_input_data.unfiltered_out_transaction_set}")
            want.append(f"{per_wallet_input_data.unfiltered_intra_transaction_set}")

        print("got:")
        for line in got:
            print(line)
        print("want:")
        for line in want:
            print(line)

        self.assertEqual("\n".join(unified_diff(got, want, lineterm="")), "")


    def test_fifo_transfer_analysis(self) -> None:
        # TODO: Add:
        # - Tests with LIFO, HIFO, LOFO

        # Go-style, table-based tests. The input field contains test input and the want field contains the expected results.
        tests: List[_Test] = [
            _Test(
                description="Transfer more than is available (one in, one intra)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 20, 20),
                ],
                accounting_method=AccountingMethodFIFO(),
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 10 B1\): .*",
            ),
            _Test(
                description="Transfer more than is available (three in, one intra)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Bob", 140, 20, 20),
                ],
                accounting_method=AccountingMethodFIFO(),
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 6 B1\): .*",
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
                accounting_method=AccountingMethodFIFO(),
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 7 B1\): .*",
            ),
            _Test(
                description="Same-exchange transfer. Transfer more than is available (one in, one intra)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Coinbase", "Bob", 120, 20, 20),
                ],
                accounting_method=AccountingMethodFIFO(),
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 10 B1\): .*",
            ),
            _Test(
                description="Same-exchange transfer. Transfer more than is available in last intra (three in, four intra)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Bob", 140, 15, 14),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Bob", 150, 14, 13),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Coinbase", "Bob", 160, 14, 14),
                    IntraTransactionDescriptor("7", 7, 7, "Coinbase", "Bob", "Coinbase", "Bob", 170, 16, 15),
                ],
                accounting_method=AccountingMethodFIFO(),
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 1 B1\): .*",
            ),
            _Test(
                description=(
                    "Same-exchange transfers. Total transferred sum is greater than crypto in amount, "
                    "but individual transfers are not (one in, three intra)"
                ),
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Coinbase", "Bob", 120, 9, 8),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Bob", 130, 10, 10),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Bob", 140, 10, 9),
                ],
                accounting_method=AccountingMethodFIFO(),
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
                    "Same-exchange transfers with different users. Total transferred sum is greater than crypto in amount (one in, three intra)."
                ),
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Coinbase", "Alice", 120, 9, 8),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Coinbase", "Alice", 130, 10, 10),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 10, 9),
                ],
                accounting_method=AccountingMethodFIFO(),
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 8 B1\): .*",
            ),
            _Test(
                description=(
                    "Same-exchange transfer. Total transferred sum is greater than crypto in amount, "
                    "but individual transfers are not (three in, three intra)"
                ),
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Bob", 140, 14, 13),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Bob", 150, 12, 12),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Coinbase", "Bob", 150, 14, 14),
                ],
                accounting_method=AccountingMethodFIFO(),
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
            _Test(
                description=(
                    "Same-exchange transfers with different users. Total transferred sum is greater than crypto in amount (three in, three intra)."
                ),
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 8),
                    InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 4),
                    InTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", 130, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Coinbase", "Alice", 140, 14, 13),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Coinbase", "Alice", 150, 12, 12),
                    IntraTransactionDescriptor("6", 6, 6, "Coinbase", "Bob", "Coinbase", "Alice", 150, 14, 14),
                ],
                accounting_method=AccountingMethodFIFO(),
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 11 B1\): .*",
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
                accounting_method=AccountingMethodFIFO(),
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Alice"): ["3/-1", "4/-2"]}),
                        InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20, to_lot_unique_ids={Account("Kraken", "Alice"): ["4/-3", "5/-4"]}),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
                        IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
                        IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
                    ],
                    Account("Kraken", "Alice"): [
                        InTransactionDescriptor("3/-1", 1, -1, "Kraken", "Alice", 110, 7, from_lot_unique_id="1"),
                        InTransactionDescriptor("4/-2", 1, -2, "Kraken", "Alice", 110, 3, from_lot_unique_id="1"),
                        InTransactionDescriptor("4/-3", 2, -3, "Kraken", "Alice", 120, 7, from_lot_unique_id="2"),
                        InTransactionDescriptor("5/-4", 2, -4, "Kraken", "Alice", 120, 12, from_lot_unique_id="2"),
                    ],
                },
                want_error="",
            ),
            _Test(
                # This is equivalent to the example discussed here:
                # https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925
                description="Reciprocal transfer: CB->Kraken, Kraken->CB",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10),
                    IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                    IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                ],
                accounting_method=AccountingMethodFIFO(),
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["3/-1"]}),
                        InTransactionDescriptor("4/-2", 2, -2, "Coinbase", "Bob", 120, 6, from_lot_unique_id="2"),
                        IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Bob", 130, 4, 3),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor("3/-1", 1, -1, "Kraken", "Bob", 110, 3, from_lot_unique_id="1"),
                        InTransactionDescriptor("2", 2, 2, "Kraken", "Bob", 120, 10, to_lot_unique_ids={Account("Coinbase", "Bob"): ["4/-2"]}),
                        IntraTransactionDescriptor("4", 4, 4, "Kraken", "Bob", "Coinbase", "Bob", 140, 7, 6),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Two paths to and from the same exchanges: CB->Kraken->BlockFi, CB->BlockFi",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "BlockFi", "Bob", 140, 5, 5),
                    OutTransactionDescriptor("5", 5, 5, "BlockFi", "Bob", 150, 6),
                ],
                accounting_method=AccountingMethodFIFO(),
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
                            "2/-1", 1, -1, "Kraken", "Bob", 110, 4, from_lot_unique_id="1", to_lot_unique_ids={Account("BlockFi", "Bob"): ["3/-2"]}
                        ),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3/-2", 1, -2, "BlockFi", "Bob", 110, 2, from_lot_unique_id="2/-1"),
                        InTransactionDescriptor("4/-3", 1, -3, "BlockFi", "Bob", 110, 5, from_lot_unique_id="1"),
                        OutTransactionDescriptor("5", 5, 5, "BlockFi", "Bob", 150, 6),
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
                    OutTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", 150, 7),
                ],
                accounting_method=AccountingMethodFIFO(),
                want={
                    Account("Coinbase", "Bob"): [
                        InTransactionDescriptor(
                            "1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Bob"): ["2/-1"], Account("BlockFi", "Bob"): ["3/-2"]}
                        ),
                        IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                        OutTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", 150, 7),
                    ],
                    Account("Kraken", "Bob"): [
                        InTransactionDescriptor(
                            "2/-1", 1, -1, "Kraken", "Bob", 110, 4, from_lot_unique_id="1", to_lot_unique_ids={Account("BlockFi", "Bob"): ["3/-2"]}
                        ),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3/-2", 1, -2, "BlockFi", "Bob", 110, 2, from_lot_unique_id="2/-1"),
                        IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Loop followed by depletion of original exchange: CB->Kraken->BlockFi->CB + CB->Kraken (depletion)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 150, 7, 7),
                ],
                accounting_method=AccountingMethodFIFO(),
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
                            "2/-1", 1, -1, "Kraken", "Bob", 110, 4, from_lot_unique_id="1", to_lot_unique_ids={Account("BlockFi", "Bob"): ["3/-2"]}
                        ),
                        IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                        InTransactionDescriptor("5/-3", 1, -3, "Kraken", "Bob", 110, 7, from_lot_unique_id="1"),
                    ],
                    Account("BlockFi", "Bob"): [
                        InTransactionDescriptor("3/-2", 1, -2, "BlockFi", "Bob", 110, 2, from_lot_unique_id="2/-1"),
                        IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                    ],
                },
                want_error="",
            ),
            _Test(
                description="Loop followed by excessive transfer on original exchange: CB->Kraken->BlockFi->CB + CB->Kraken (not enough funds)",
                input=[
                    InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
                    IntraTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", "Kraken", "Bob", 120, 4, 4),
                    IntraTransactionDescriptor("3", 3, 3, "Kraken", "Bob", "BlockFi", "Bob", 130, 2, 2),
                    IntraTransactionDescriptor("4", 4, 4, "BlockFi", "Bob", "Coinbase", "Bob", 140, 1, 1),
                    IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Bob", 150, 8, 8),
                ],
                accounting_method=AccountingMethodFIFO(),
                want={},
                want_error=r"Insufficient balance on Account\(exchange='Coinbase', holder='Bob'\) to send funds \(amount 1 B1\): .*",
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                self._run_test(test)


    # def test_lifo_transfer_analysis(self) -> None:

    #     # Go-style, table-based tests. The input field contains test input and the want field contains the expected results.
    #     tests: List[_Test] = [
    #         _Test(
    #             description="Two in-lots, three transfers: CB->Kraken",
    #             input=[
    #                 InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10),
    #                 InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20),
    #                 IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
    #                 IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
    #                 IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
    #             ],
    #             accounting_method=AccountingMethodLIFO(),
    #             want={
    #                 Account("Coinbase", "Bob"): [
    #                     InTransactionDescriptor("1", 1, 1, "Coinbase", "Bob", 110, 10, to_lot_unique_ids={Account("Kraken", "Alice"): ["3/-1", "4/-2"]}),
    #                     InTransactionDescriptor("2", 2, 2, "Coinbase", "Bob", 120, 20, to_lot_unique_ids={Account("Kraken", "Alice"): ["4/-3", "5/-4"]}),
    #                     IntraTransactionDescriptor("3", 3, 3, "Coinbase", "Bob", "Kraken", "Alice", 130, 8, 7),
    #                     IntraTransactionDescriptor("4", 4, 4, "Coinbase", "Bob", "Kraken", "Alice", 140, 10, 10),
    #                     IntraTransactionDescriptor("5", 5, 5, "Coinbase", "Bob", "Kraken", "Alice", 150, 12, 12),
    #                 ],
    #                 Account("Kraken", "Alice"): [
    #                     InTransactionDescriptor("3/-1", 1, -1, "Kraken", "Alice", 110, 7, from_lot_unique_id="1"),
    #                     InTransactionDescriptor("4/-2", 1, -2, "Kraken", "Alice", 110, 3, from_lot_unique_id="1"),
    #                     InTransactionDescriptor("4/-3", 2, -3, "Kraken", "Alice", 120, 7, from_lot_unique_id="2"),
    #                     InTransactionDescriptor("5/-4", 2, -4, "Kraken", "Alice", 120, 12, from_lot_unique_id="2"),
    #                 ],
    #             },
    #             want_error="",
    #         ),
    #     ]
    #     for test in tests:
    #         with self.subTest(name=test.description):
    #             self._run_test(test)


if __name__ == "__main__":
    unittest.main()

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
from typing import cast, Dict, List, Optional

from rp2.abstract_transaction import AbstractTransaction
from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.configuration import Configuration
from rp2.in_transaction import Account, InTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.input_data import InputData
from rp2.out_transaction import OutTransaction
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError
from rp2.transaction_set import TransactionSet


# Transaction descriptor data classes are used in tests as short-form descriptions of transactions.
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
    cost_basis_day: Optional[int] = None


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


class AbstractTestTransactionProcessing(unittest.TestCase):
    _asset: str
    _start_date: datetime
    _accounting_methods: List[AbstractAccountingMethod]

    @classmethod
    def setUpClass(cls) -> None:
        AbstractTestTransactionProcessing._asset = "B1"
        AbstractTestTransactionProcessing._start_date = datetime.strptime("2024-01-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
        AbstractTestTransactionProcessing._accounting_methods = [AccountingMethodFIFO(), AccountingMethodLIFO(), AccountingMethodHIFO(), AccountingMethodLOFO()]

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def _serialize_input_data_as_string_list(self, input_data: InputData, output: List[str]) -> None:
        for transaction in input_data.unfiltered_in_transaction_set:
            output.extend(f"{transaction}".splitlines())
        for transaction in input_data.unfiltered_out_transaction_set:
            output.extend(f"{transaction}".splitlines())
        for transaction in input_data.unfiltered_intra_transaction_set:
            output.extend(f"{transaction}".splitlines())

    def _list_to_transaction_set(self, configuration: Configuration, transaction_list: List[AbstractTransaction], entry_set_type: str) -> TransactionSet:
        result = TransactionSet(configuration, entry_set_type, self._asset)
        for transaction in transaction_list:
            result.add_entry(transaction)
        return result

    def _create_input_data_from_unique_id_maps(
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

    def _create_universal_input_data_from_transaction_descriptors(self, configuration: Configuration,
                                                                  descriptors: List[AbstractTransactionDescriptor]) -> InputData:
        unique_id_2_in_transaction: Dict[str, InTransaction] = {}
        unique_id_2_out_transaction: Dict[str, OutTransaction] = {}
        unique_id_2_intra_transaction: Dict[str, IntraTransaction] = {}
        deferred_transactions: List[InTransactionDescriptor] = []

        # Create transactions from transaction descriptors.
        self._create_transactions(
            configuration, descriptors, unique_id_2_in_transaction, unique_id_2_out_transaction,
            unique_id_2_intra_transaction, deferred_transactions
        )
        if deferred_transactions:
            # Deferred transactions are not expected from test input.
            raise ValueError(f"Test data error: universal input data deferred transactions not empty: {deferred_transactions}")

        # Create universal InputData.
        universal_input_data = self._create_input_data_from_unique_id_maps(configuration, unique_id_2_in_transaction,
                                                                           unique_id_2_out_transaction, unique_id_2_intra_transaction)

        return universal_input_data

    def _create_per_wallet_input_data_from_transaction_descriptors(self,
                                                                   configuration: Configuration,
                                                                   per_wallet_descriptors: Dict[Account, List[AbstractTransactionDescriptor]]
                                                                   ) -> Dict[Account, InputData]:
        unique_id_2_in_transaction: Dict[str, InTransaction] = {}
        unique_id_2_out_transaction: Dict[str, OutTransaction] = {}
        unique_id_2_intra_transaction: Dict[str, IntraTransaction] = {}
        deferred_transactions: List[InTransactionDescriptor] = []
        for _, transaction_descriptors in per_wallet_descriptors.items():
            self._create_transactions(
                configuration,
                transaction_descriptors,
                unique_id_2_in_transaction,
                unique_id_2_out_transaction,
                unique_id_2_intra_transaction,
                deferred_transactions,
            )
        # Process deferred transactions until there are no more.
        while True:
            if not deferred_transactions:
                break
            new_deferred_transactions: List[InTransactionDescriptor] = []
            self._create_transactions(
                configuration,
                cast(List[AbstractTransactionDescriptor], deferred_transactions),
                unique_id_2_in_transaction,
                unique_id_2_out_transaction,
                unique_id_2_intra_transaction,
                new_deferred_transactions,
            )
            deferred_transactions = new_deferred_transactions

        want_wallet_2_per_wallet_input_data: Dict[Account, InputData] = {}
        for account, transaction_descriptors in per_wallet_descriptors.items():
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
                else:
                    raise RP2TypeError(f"Invalid transaction_descriptor class: {transaction_descriptor}")
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
            want_wallet_2_per_wallet_input_data[account] = InputData(self._asset, in_transaction_set, out_transaction_set, intra_transaction_set)

        return want_wallet_2_per_wallet_input_data

    def _create_in_transaction(
        self, configuration: Configuration, transaction_descriptor: InTransactionDescriptor, from_lot: Optional["InTransaction"] = None
    ) -> InTransaction:
        timestamp = self._start_date + timedelta(days=transaction_descriptor.day)
        cost_basis_timestamp_string = (
            (self._start_date + timedelta(days=transaction_descriptor.cost_basis_day)).isoformat()
            if transaction_descriptor.cost_basis_day is not None
            else None
        )
        return InTransaction(
            configuration,
            timestamp.isoformat(),
            self._asset,
            transaction_descriptor.exchange,
            transaction_descriptor.holder,
            "Buy",
            RP2Decimal(transaction_descriptor.spot_price),
            RP2Decimal(transaction_descriptor.crypto_in),
            RP2Decimal(transaction_descriptor.crypto_fee),
            row=transaction_descriptor.row,
            unique_id=transaction_descriptor.unique_id,
            from_lot=from_lot,
            cost_basis_timestamp=cost_basis_timestamp_string,
        )

    def _create_out_transaction(self, configuration: Configuration, transaction_descriptor: OutTransactionDescriptor) -> OutTransaction:
        timestamp = self._start_date + timedelta(days=transaction_descriptor.day)
        return OutTransaction(
            configuration,
            timestamp.isoformat(),
            self._asset,
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
            self._asset,
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
        deferred_transactions: List[InTransactionDescriptor],
    ) -> None:
        for transaction_descriptor in transaction_descriptors:
            transaction: AbstractTransaction
            if isinstance(transaction_descriptor, InTransactionDescriptor):
                from_lot_unique_id = transaction_descriptor.from_lot_unique_id
                if from_lot_unique_id is not None and from_lot_unique_id not in unique_id_2_in_transaction:
                    # Handle forward references to transactions that have not been created yet (this can happen in cycles).
                    # Deferred transactions will be created in later passes.
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

# Copyright 2021 eprbell
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
from typing import List, Optional, cast

from dateutil.parser import parse

from rp2.abstract_entry import AbstractEntry
from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import Configuration
from rp2.entry_types import EntrySetType, TransactionType
from rp2.in_transaction import InTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError
from rp2.transaction_set import TransactionSet


class TestTransactionSet(unittest.TestCase):
    _configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        TestTransactionSet._configuration = Configuration("./config/test_data.config", US())

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_good_transaction_set(self) -> None:
        transaction_set: TransactionSet = TransactionSet(self._configuration, "MIXED", "B1")

        # Test empty iterator
        count: int = 0
        entry: AbstractEntry
        transaction: AbstractTransaction
        for entry in transaction_set:
            transaction = cast(AbstractTransaction, entry)
            count += 1
        self.assertEqual(count, 0)

        transaction3: InTransaction = InTransaction(
            self._configuration,
            "1/8/2021 8:42:43.883 -04:00",
            "B1",
            "Coinbase",
            "Alice",
            "bUy",
            RP2Decimal("1000"),
            RP2Decimal("3.0002"),
            fiat_fee=RP2Decimal("20"),
            fiat_in_no_fee=RP2Decimal("3000.2"),
            fiat_in_with_fee=RP2Decimal("3020.2"),
            internal_id=30,
        )
        transaction_set.add_entry(transaction3)

        transaction2: InTransaction = InTransaction(
            self._configuration,
            "2021-01-02T08:42:43.882Z",
            "B1",
            "BlockFi",
            "Bob",
            "InTeREST",
            RP2Decimal("1000.0"),
            RP2Decimal("2.0002"),
            fiat_fee=RP2Decimal("0"),
            fiat_in_no_fee=RP2Decimal("2000.2"),
            fiat_in_with_fee=RP2Decimal("2000.2"),
            internal_id=20,
        )
        transaction_set.add_entry(transaction2)

        timestamps: List[str] = [
            "2021-01-02T08:42:43.882Z",
            "1/8/2021 8:42:43.883 -04:00",
        ]

        count = 0
        timestamp: str
        for transaction, timestamp in zip(transaction_set, timestamps):  # type: ignore
            self.assertEqual(transaction.timestamp, parse(timestamp))
            count += 1
        self.assertEqual(count, 2)

        transaction1: OutTransaction = OutTransaction(
            self._configuration,
            "6/1/2020 3:59:59 -04:00",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SeLL",
            RP2Decimal("900.9"),
            RP2Decimal("2.2"),
            RP2Decimal("0"),
            internal_id=10,
        )
        transaction_set.add_entry(transaction1)

        transaction5: IntraTransaction = IntraTransaction(
            self._configuration,
            "2021-04-02T08:42:43.882Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BlockFi",
            "Alice",
            RP2Decimal("1000.0"),
            RP2Decimal("2.0002"),
            RP2Decimal("1.9998"),
            internal_id=50,
        )
        transaction_set.add_entry(transaction5)

        transaction4: IntraTransaction = IntraTransaction(
            self._configuration,
            "2021-03-28T08:42:43.882Z",
            "B1",
            "Coinbase",
            "Bob",
            "Coinbase",
            "Alice",
            RP2Decimal("100.0"),
            RP2Decimal("30"),
            RP2Decimal("30"),
            internal_id=40,
        )
        transaction_set.add_entry(transaction4)

        self.assertEqual(transaction_set.entry_set_type, EntrySetType.MIXED)
        self.assertEqual(transaction_set.asset, "B1")

        internal_ids: List[str] = ["10", "20", "30", "40", "50"]
        transactions: List[AbstractTransaction] = [transaction1, transaction2, transaction3, transaction4, transaction5]
        parents: List[Optional[AbstractTransaction]] = [
            None,
            transaction1,
            transaction2,
            transaction3,
            transaction4,
        ]
        timestamps = [
            "6/1/2020 3:59:59 -04:00",
            "2021-01-02T08:42:43.882Z",
            "1/8/2021 8:42:43.883 -04:00",
            "2021-03-28T08:42:43.882Z",
            "2021-04-02T08:42:43.882Z",
        ]
        transaction_types: List[TransactionType] = [
            TransactionType.SELL,
            TransactionType.INTEREST,
            TransactionType.BUY,
            TransactionType.MOVE,
            TransactionType.MOVE,
        ]
        fiat_taxable_amounts: List[RP2Decimal] = [RP2Decimal(s) for s in ["1981.98", "2000.2", "0", "0", "0.4"]]
        crypto_balance_changes: List[RP2Decimal] = [RP2Decimal(s) for s in ["2.2", "2.0002", "3.0002", "0", "0.0004"]]
        fiat_balance_changes: List[RP2Decimal] = [RP2Decimal(s) for s in ["1981.98", "2000.2", "3020.2", "0", "0.4"]]

        count = 0
        expected_transaction: AbstractTransaction
        parent: AbstractTransaction
        internal_id: str
        transaction_type: TransactionType
        fiat_taxable_amount: RP2Decimal
        crypto_balance_change: RP2Decimal
        fiat_balance_change: RP2Decimal
        for (  # type: ignore
            transaction,
            expected_transaction,
            parent,
            internal_id,
            timestamp,
            transaction_type,
            fiat_taxable_amount,
            crypto_balance_change,
            fiat_balance_change,
        ) in zip(  # type: ignore
            transaction_set,
            transactions,
            parents,
            internal_ids,
            timestamps,
            transaction_types,
            fiat_taxable_amounts,
            crypto_balance_changes,
            fiat_balance_changes,
        ):
            self.assertEqual(transaction, expected_transaction)
            self.assertEqual(transaction_set.get_parent(transaction), parent)
            self.assertEqual(transaction.internal_id, internal_id)
            self.assertEqual(transaction.timestamp, parse(timestamp))
            self.assertEqual(transaction.transaction_type, transaction_type)
            self.assertEqual(transaction.asset, "B1")
            self.assertEqual(transaction.fiat_taxable_amount, fiat_taxable_amount)
            self.assertEqual(transaction.crypto_balance_change, crypto_balance_change)
            self.assertEqual(transaction.fiat_balance_change, fiat_balance_change)
            count += 1
        self.assertEqual(count, 5)

        self.assertTrue(str(transaction_set).startswith("TransactionSet:\n  configuration=./config/test_data.config\n  entry_set_type=EntrySetType.MIXED"))

    def test_bad_transaction_set(self) -> None:
        in_transaction = InTransaction(
            self._configuration,
            "2021-01-02T08:42:43.882Z",
            "B1",
            "BlockFi",
            "Bob",
            "INTERest",
            RP2Decimal("1000.0"),
            RP2Decimal("2.0002"),
            fiat_fee=RP2Decimal("0"),
            fiat_in_with_fee=RP2Decimal("2000.2"),
            fiat_in_no_fee=RP2Decimal("2000.2"),
            internal_id=20,
        )
        # Different instance with same contents as in_transaction
        in_transaction2 = InTransaction(
            self._configuration,
            "2021-01-02T08:42:43.882Z",
            "B1",
            "BlockFi",
            "Bob",
            "interEST",
            RP2Decimal("1000.0"),
            RP2Decimal("2.0002"),
            fiat_fee=RP2Decimal("0"),
            fiat_in_with_fee=RP2Decimal("2000.2"),
            fiat_in_no_fee=RP2Decimal("2000.2"),
            internal_id=20,
        )
        out_transaction = OutTransaction(
            self._configuration,
            "6/1/2020 3:59:59 -04:00",
            "B1",
            "Coinbase Pro",
            "Bob",
            "sELl",
            RP2Decimal("900.9"),
            RP2Decimal("2.2"),
            RP2Decimal("0"),
            internal_id=10,
        )
        intra_transaction = IntraTransaction(
            self._configuration,
            "2021-04-02T08:42:43.882Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BlockFi",
            "Alice",
            RP2Decimal("1000.0"),
            RP2Decimal("2.0002"),
            RP2Decimal("1.9998"),
            internal_id=50,
        )

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            TransactionSet(None, "IN", "B1")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            TransactionSet(1111, "IN", "B1")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'entry_set_type' has non-string value .*"):
            # Bad transaction set type
            TransactionSet(self._configuration, None, "B1")  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Parameter .* has invalid entry set type value: .*"):
            # Bad transaction set type
            TransactionSet(self._configuration, "foobar", "B1")
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'entry_set_type' has non-string value .*"):
            # Bad transaction set type
            TransactionSet(self._configuration, 1111, "B1")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'asset' has non-string value .*"):
            # Bad asset
            TransactionSet(self._configuration, "IN", None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'asset' has non-string value .*"):
            # Bad asset
            TransactionSet(self._configuration, "IN", 1111)  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'asset' value is not known: .*"):
            # Bad asset
            TransactionSet(self._configuration, "IN", "Qwerty")
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'from_date' is not of type date"):
            # Bad from_date
            TransactionSet(self._configuration, "IN", "B1", "2018")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'from_date' is not of type date"):
            # Bad from_date
            TransactionSet(self._configuration, "IN", "B1", "foobar")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'from_date' is not of type date"):
            # Bad to_date
            TransactionSet(self._configuration, "IN", "B1", "2018-01-03", "2019-07")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'from_date' is not of type date"):
            # Bad to_date
            TransactionSet(self._configuration, "IN", "B1", "2018-01-03", 0)  # type: ignore

        in_transaction_set = TransactionSet(self._configuration, "IN", "B1")
        out_transaction_set = TransactionSet(self._configuration, "OUT", "B1")
        intra_transaction_set = TransactionSet(self._configuration, "INTRA", "B1")

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'entry' is not of type AbstractTransaction: .*"):
            # Bad transaction add
            in_transaction_set.add_entry(None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'entry' is not of type AbstractTransaction: .*"):
            # Bad transaction add
            in_transaction_set.add_entry(1111)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Attempting to add a .* to a set of type IN"):
            # Transaction add type mismatch
            in_transaction_set.add_entry(out_transaction)
        with self.assertRaisesRegex(RP2TypeError, "Attempting to add a .* to a set of type OUT"):
            # Transaction add type mismatch
            out_transaction_set.add_entry(intra_transaction)
        with self.assertRaisesRegex(RP2TypeError, "Attempting to add a .* to a set of type INTRA"):
            # Transaction add type mismatch
            intra_transaction_set.add_entry(in_transaction)

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'entry' is not of type AbstractTransaction: .*"):
            # Bad get_parent parameter
            in_transaction_set.get_parent(None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'entry' is not of type AbstractTransaction: .*"):
            # Bad get_parent parameter
            in_transaction_set.get_parent(1111)  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Unknown entry:.*"):
            # Unknown get_parent parameter
            in_transaction_set.get_parent(out_transaction)
        with self.assertRaisesRegex(RP2ValueError, "Unknown entry:.*"):
            # Unknown get_parent parameter
            out_transaction_set.get_parent(intra_transaction)
        with self.assertRaisesRegex(RP2ValueError, "Unknown entry:.*"):
            # Unknown get_parent parameter
            intra_transaction_set.get_parent(in_transaction)
        with self.assertRaisesRegex(RP2ValueError, "Entry already added: InTransaction"):
            in_transaction_set = TransactionSet(self._configuration, "IN", "B1")
            in_transaction_set.add_entry(in_transaction)
            in_transaction_set.add_entry(in_transaction)
        with self.assertRaisesRegex(RP2ValueError, "Entry already added: InTransaction"):
            in_transaction_set = TransactionSet(self._configuration, "IN", "B1")
            in_transaction_set.add_entry(in_transaction)
            in_transaction_set.add_entry(in_transaction2)


if __name__ == "__main__":
    unittest.main()

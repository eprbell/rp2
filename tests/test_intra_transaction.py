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

import re
import unittest

from dateutil.tz import tzutc

from rp2.configuration import Configuration
from rp2.entry_types import TransactionType
from rp2.in_transaction import InTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError


class TestIntraTransaction(unittest.TestCase):
    _configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        TestIntraTransaction._configuration = Configuration("./config/test_data.config", US())

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_taxable_intra_transaction(self) -> None:
        intra_transaction: IntraTransaction = IntraTransaction(
            self._configuration,
            "2021-01-02T08:42:43.882Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BlockFi",
            "Alice",
            RP2Decimal("1000.0"),
            RP2Decimal("2.0002"),
            RP2Decimal("1.9998"),
            internal_id=19,
        )

        IntraTransaction.type_check("my_instance", intra_transaction)
        self.assertTrue(intra_transaction.is_taxable())
        self.assertEqual(RP2Decimal("0.4"), intra_transaction.fiat_taxable_amount)
        self.assertEqual("19", intra_transaction.internal_id)
        self.assertEqual(2021, intra_transaction.timestamp.year)
        self.assertEqual(1, intra_transaction.timestamp.month)
        self.assertEqual(2, intra_transaction.timestamp.day)
        self.assertEqual(8, intra_transaction.timestamp.hour)
        self.assertEqual(42, intra_transaction.timestamp.minute)
        self.assertEqual(43, intra_transaction.timestamp.second)
        self.assertEqual(882000, intra_transaction.timestamp.microsecond)
        self.assertEqual(tzutc(), intra_transaction.timestamp.tzinfo)
        self.assertEqual("B1", intra_transaction.asset)
        self.assertEqual("Coinbase Pro", intra_transaction.from_exchange)
        self.assertEqual("Bob", intra_transaction.from_holder)
        self.assertEqual("BlockFi", intra_transaction.to_exchange)
        self.assertEqual("Alice", intra_transaction.to_holder)
        self.assertEqual(TransactionType.MOVE, intra_transaction.transaction_type)
        self.assertEqual(RP2Decimal("1000"), intra_transaction.spot_price)
        self.assertEqual(RP2Decimal("2.0002"), intra_transaction.crypto_sent)
        self.assertEqual(RP2Decimal("1.9998"), intra_transaction.crypto_received)
        self.assertEqual(RP2Decimal("0.0004"), intra_transaction.crypto_fee)
        self.assertEqual(RP2Decimal("0.4"), intra_transaction.fiat_fee)
        self.assertEqual(RP2Decimal("0.0004"), intra_transaction.crypto_balance_change)
        self.assertEqual(RP2Decimal("0.4"), intra_transaction.fiat_balance_change)

        self.assertEqual(
            str(intra_transaction),
            """IntraTransaction:
  id=19
  timestamp=2021-01-02 08:42:43.882000 +0000
  asset=B1
  from_exchange=Coinbase Pro
  from_holder=Bob
  to_exchange=BlockFi
  to_holder=Alice
  transaction_type=TransactionType.MOVE
  spot_price=1000.0000
  crypto_sent=2.00020000
  crypto_received=1.99980000
  crypto_fee=0.00040000
  fiat_fee=0.4000
  unique_id=
  is_taxable=True
  fiat_taxable_amount=0.4000""",
        )
        self.assertEqual(
            intra_transaction.to_string(2, repr_format=False, extra_data=["foobar", "qwerty"]),
            """    IntraTransaction:
      id=19
      timestamp=2021-01-02 08:42:43.882000 +0000
      asset=B1
      from_exchange=Coinbase Pro
      from_holder=Bob
      to_exchange=BlockFi
      to_holder=Alice
      transaction_type=TransactionType.MOVE
      spot_price=1000.0000
      crypto_sent=2.00020000
      crypto_received=1.99980000
      crypto_fee=0.00040000
      fiat_fee=0.4000
      unique_id=
      is_taxable=True
      fiat_taxable_amount=0.4000
      foobar
      qwerty""",
        )
        self.assertEqual(
            intra_transaction.to_string(2, repr_format=True, extra_data=["foobar", "qwerty"]),
            (
                "    IntraTransaction("
                "id='19', "
                "timestamp='2021-01-02 08:42:43.882000 +0000', "
                "asset='B1', "
                "from_exchange='Coinbase Pro', "
                "from_holder='Bob', "
                "to_exchange='BlockFi', "
                "to_holder='Alice', "
                "transaction_type=<TransactionType.MOVE: 'move'>, "
                "spot_price=1000.0000, "
                "crypto_sent=2.00020000, "
                "crypto_received=1.99980000, "
                "crypto_fee=0.00040000, "
                "fiat_fee=0.4000, "
                "unique_id=, "
                "is_taxable=True, "
                "fiat_taxable_amount=0.4000, "
                "foobar, "
                "qwerty)"
            ),
        )

    def test_non_taxable_intra_transaction(self) -> None:
        intra_transaction: IntraTransaction = IntraTransaction(
            self._configuration,
            "2021-01-02T08:42:43.882Z",
            "B2",
            "Coinbase",
            "Bob",
            "Coinbase",
            "Alice",
            RP2Decimal("100.0"),
            RP2Decimal("30"),
            RP2Decimal("30"),
            internal_id=19,
        )
        self.assertFalse(intra_transaction.is_taxable())
        self.assertEqual(RP2Decimal("0"), intra_transaction.fiat_taxable_amount)
        self.assertEqual("B2", intra_transaction.asset)
        self.assertEqual(TransactionType.MOVE, intra_transaction.transaction_type)
        self.assertEqual(RP2Decimal("0"), intra_transaction.crypto_fee)
        self.assertEqual(RP2Decimal("0"), intra_transaction.fiat_fee)
        self.assertEqual(RP2Decimal("-0"), intra_transaction.crypto_balance_change)
        self.assertEqual(RP2Decimal("0.0"), intra_transaction.fiat_balance_change)

        self.assertEqual(
            str(intra_transaction),
            """IntraTransaction:
  id=19
  timestamp=2021-01-02 08:42:43.882000 +0000
  asset=B2
  from_exchange=Coinbase
  from_holder=Bob
  to_exchange=Coinbase
  to_holder=Alice
  transaction_type=TransactionType.MOVE
  spot_price=100.0000
  crypto_sent=30.00000000
  crypto_received=30.00000000
  crypto_fee=0.00000000
  fiat_fee=0.0000
  unique_id=
  is_taxable=False
  fiat_taxable_amount=0.0000""",
        )

    def test_intra_transaction_equality_and_hashing(self) -> None:
        intra_transaction: IntraTransaction = IntraTransaction(
            self._configuration,
            "2021-01-02T08:42:43.882Z",
            "B2",
            "Coinbase",
            "Bob",
            "Coinbase",
            "Alice",
            RP2Decimal("100.0"),
            RP2Decimal("30"),
            RP2Decimal("30"),
            internal_id=19,
        )
        intra_transaction2: IntraTransaction = IntraTransaction(
            self._configuration,
            "2021-01-02T08:42:43.882Z",
            "B2",
            "Coinbase",
            "Bob",
            "Coinbase",
            "Alice",
            RP2Decimal("100.0"),
            RP2Decimal("30"),
            RP2Decimal("30"),
            internal_id=19,
        )
        intra_transaction3: IntraTransaction = IntraTransaction(
            self._configuration,
            "2021-01-02T08:42:43.882Z",
            "B2",
            "Coinbase",
            "Bob",
            "Coinbase",
            "Alice",
            RP2Decimal("100.0"),
            RP2Decimal("30"),
            RP2Decimal("30"),
            internal_id=11,
        )
        self.assertEqual(intra_transaction, intra_transaction)
        self.assertEqual(intra_transaction, intra_transaction2)
        self.assertNotEqual(intra_transaction, intra_transaction3)
        self.assertEqual(hash(intra_transaction), hash(intra_transaction))
        self.assertEqual(hash(intra_transaction), hash(intra_transaction2))
        # These hashes would only be equal in case of hash collision (possible but very unlikey)
        self.assertNotEqual(hash(intra_transaction), hash(intra_transaction3))

    def test_bad_to_string(self) -> None:
        intra_transaction: IntraTransaction = IntraTransaction(
            self._configuration,
            "2021-01-02T08:42:43.882Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BlockFi",
            "Alice",
            RP2Decimal("1000.0"),
            RP2Decimal("2.0002"),
            RP2Decimal("1.9998"),
            internal_id=19,
        )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'indent' has non-integer value"):
            intra_transaction.to_string(None, repr_format=False, extra_data=["foobar", "qwerty"])  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'indent' has non-positive value.*"):
            intra_transaction.to_string(-1, repr_format=False, extra_data=["foobar", "qwerty"])
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'repr_format' has non-bool value .*"):
            intra_transaction.to_string(1, repr_format="False", extra_data=["foobar", "qwerty"])  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'extra_data' is not of type List"):
            intra_transaction.to_string(1, repr_format=False, extra_data="foobar")  # type: ignore

    def test_bad_intra_transaction(self) -> None:
        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string:.*"):
            IntraTransaction.type_check(None, None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_instance' is not of type IntraTransaction:.*"):
            IntraTransaction.type_check("my_instance", None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_instance' is not of type IntraTransaction: InTransaction"):
            IntraTransaction.type_check(
                "my_instance",
                InTransaction(
                    self._configuration,
                    "2021-01-12T11:51:38Z",
                    "B1",
                    "BlockFi",
                    "Bob",
                    "BUY",
                    RP2Decimal("10000"),
                    RP2Decimal("1"),
                    fiat_fee=RP2Decimal("0"),
                    internal_id=45,
                ),
            )

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            IntraTransaction(
                None,  # type: ignore
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            IntraTransaction(
                "config",  # type: ignore
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'internal_id' has non-integer value .*"):
            # Bad internal_id
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=(1, 2, 3),  # type: ignore
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'timestamp' has non-string value .*"):
            # Bad timestamp
            IntraTransaction(
                self._configuration,
                None,  # type: ignore
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'timestamp' value has no timezone info: .*"):
            # Bad timestamp
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'asset' value is not known: .*"):
            # Bad asset
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "hhh",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'asset' has non-string value .*"):
            # Bad asset
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                None,  # type: ignore
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'from_exchange' value is not known: .*"):
            # Bad from exchange
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "COinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'from_exchange' has non-string value .*"):
            # Bad from exchange
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                (1, 2, 3),  # type: ignore
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'from_holder' value is not known: .*"):
            # Bad from holder
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'from_holder' has non-string value .*"):
            # Bad from holder
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                None,  # type: ignore
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'to_exchange' value is not known: .*"):
            # Bad to exchange
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'to_exchange' has non-string value .*"):
            # Bad to exchange
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                None,  # type: ignore
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'to_holder' value is not known: .*"):
            # Bad to holder
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "A lice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'to_holder' has non-string value .*"):
            # Bad to holder
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                1111,  # type: ignore
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'spot_price' has non-positive value .*"):
            # Bad spot price
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("-1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'spot_price' has non-RP2Decimal value .*"):
            # Bad spot price
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                "1000",  # type: ignore
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_sent' has zero value"):
            # Bad crypto sent
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("0"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_sent' has non-positive value .*"):
            # Bad crypto sent
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("-2"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'crypto_sent' has non-RP2Decimal value .*"):
            # Bad crypto sent
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                None,  # type: ignore
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'crypto_sent' has non-RP2Decimal value .*"):
            # Bad crypto sent
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                "-2.0002",  # type: ignore
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_received' has non-positive value .*"):
            # Bad crypto received
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("-2"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'crypto_received' has non-RP2Decimal value .*"):
            # Bad crypto received
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                None,  # type: ignore
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'crypto_received' has non-RP2Decimal value .*"):
            # Bad crypto received
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                (1, 2, 3),  # type: ignore
                internal_id=19,
            )

        with self.assertLogs(level="WARNING") as log:
            # From/to exchanges/holders are the same: sending to self
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "BlockFi",
                "Bob",
                "BlockFi",
                "Bob",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
            self.assertTrue(re.search(".*IntraTransaction.*: from/to exchanges/holders are the same: sending to self", log.output[0]))  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_sent' has non-positive value .*"):
            # Crypto sent < 0
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("-2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_sent' has zero value"):
            # Crypto sent == 0
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("0"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_received' has non-positive value .*"):
            # Crypto received < 0
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("-1.9998"),
                internal_id=19,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'notes' has non-string value .*"):
            # Bad notes
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
                notes=1111,  # type: ignore
            )
        with self.assertLogs(level="WARNING") as log:
            # Sender and receiver are the same
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "BlockFi",
                "Alice",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("2.0002"),
                RP2Decimal("1.9998"),
                internal_id=19,
            )
            self.assertTrue(re.search(".*IntraTransaction.*: from/to exchanges/holders are the same: sending to self", log.output[0]))  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, ".*IntraTransaction .*, id.*crypto sent < crypto received"):
            # Crypto sent < crypto received
            IntraTransaction(
                self._configuration,
                "2021-01-02T08:42:43.882Z",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BlockFi",
                "Alice",
                RP2Decimal("1000.0"),
                RP2Decimal("1.0002"),
                RP2Decimal("2.9998"),
                internal_id=19,
            )


if __name__ == "__main__":
    unittest.main()

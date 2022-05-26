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

from dateutil.tz import tzoffset

from rp2.configuration import Configuration
from rp2.entry_types import TransactionType
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError


class TestOutTransaction(unittest.TestCase):
    _configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        TestOutTransaction._configuration = Configuration("./config/test_data.config", US())

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_taxable_out_transaction(self) -> None:
        out_transaction: OutTransaction = OutTransaction(
            self._configuration,
            "6/1/2020 3:59:59 -04:00",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("900.9"),
            RP2Decimal("2.2"),
            RP2Decimal("0.01"),
            internal_id=38,
        )
        OutTransaction.type_check("my_instance", out_transaction)

        self.assertTrue(out_transaction.is_taxable())
        self.assertEqual(RP2Decimal("1981.98"), out_transaction.fiat_taxable_amount)
        self.assertEqual(RP2Decimal("2.2"), out_transaction.crypto_taxable_amount)
        self.assertEqual("38", out_transaction.internal_id)
        self.assertEqual(2020, out_transaction.timestamp.year)
        self.assertEqual(6, out_transaction.timestamp.month)
        self.assertEqual(1, out_transaction.timestamp.day)
        self.assertEqual(3, out_transaction.timestamp.hour)
        self.assertEqual(59, out_transaction.timestamp.minute)
        self.assertEqual(59, out_transaction.timestamp.second)
        self.assertEqual(tzoffset(None, -14400), out_transaction.timestamp.tzinfo)
        self.assertEqual("B1", out_transaction.asset)
        self.assertEqual("Coinbase Pro", out_transaction.exchange)
        self.assertEqual("Bob", out_transaction.holder)
        self.assertEqual(TransactionType.SELL, out_transaction.transaction_type)
        self.assertEqual(RP2Decimal("900.9"), out_transaction.spot_price)
        self.assertEqual(RP2Decimal("2.2"), out_transaction.crypto_out_no_fee)
        self.assertEqual(RP2Decimal("2.21"), out_transaction.crypto_balance_change)
        self.assertEqual(RP2Decimal("1990.989"), out_transaction.fiat_balance_change)

        self.assertEqual(
            str(out_transaction),
            """OutTransaction:
  id=38
  timestamp=2020-06-01 03:59:59.000000 -0400
  asset=B1
  exchange=Coinbase Pro
  holder=Bob
  transaction_type=TransactionType.SELL
  spot_price=900.9000
  crypto_out_no_fee=2.20000000
  crypto_fee=0.01000000
  unique_id=
  is_taxable=True
  fiat_taxable_amount=1981.9800""",
        )
        self.assertEqual(
            out_transaction.to_string(2, repr_format=False, extra_data=["foobar", "qwerty"]),
            """    OutTransaction:
      id=38
      timestamp=2020-06-01 03:59:59.000000 -0400
      asset=B1
      exchange=Coinbase Pro
      holder=Bob
      transaction_type=TransactionType.SELL
      spot_price=900.9000
      crypto_out_no_fee=2.20000000
      crypto_fee=0.01000000
      unique_id=
      is_taxable=True
      fiat_taxable_amount=1981.9800
      foobar
      qwerty""",
        )
        self.assertEqual(
            out_transaction.to_string(2, repr_format=True, extra_data=["foobar", "qwerty"]),
            (
                "    OutTransaction("
                "id='38', "
                "timestamp='2020-06-01 03:59:59.000000 -0400', "
                "asset='B1', "
                "exchange='Coinbase Pro', "
                "holder='Bob', "
                "transaction_type=<TransactionType.SELL: 'sell'>, "
                "spot_price=900.9000, "
                "crypto_out_no_fee=2.20000000, "
                "crypto_fee=0.01000000, "
                "unique_id=, "
                "is_taxable=True, "
                "fiat_taxable_amount=1981.9800, "
                "foobar, "
                "qwerty)"
            ),
        )

    def test_out_transaction_equality_and_hashing(self) -> None:
        out_transaction: OutTransaction = OutTransaction(
            self._configuration,
            "6/1/2020 3:59:59 -04:00",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("900.9"),
            RP2Decimal("2.2"),
            RP2Decimal("0.01"),
            internal_id=38,
        )
        out_transaction2: OutTransaction = OutTransaction(
            self._configuration,
            "6/1/2020 3:59:59 -04:00",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("900.9"),
            RP2Decimal("2.2"),
            RP2Decimal("0.01"),
            internal_id=38,
        )
        out_transaction3: OutTransaction = OutTransaction(
            self._configuration,
            "6/1/2020 3:59:59 -04:00",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("900.9"),
            RP2Decimal("2.2"),
            RP2Decimal("0.01"),
            internal_id=7,
        )
        self.assertEqual(out_transaction, out_transaction)
        self.assertEqual(out_transaction, out_transaction2)
        self.assertNotEqual(out_transaction, out_transaction3)
        self.assertEqual(hash(out_transaction), hash(out_transaction))
        self.assertEqual(hash(out_transaction), hash(out_transaction2))
        # These hashes would only be equal in case of hash collision (possible but very unlikey)
        self.assertNotEqual(hash(out_transaction), hash(out_transaction3))

    def test_bad_to_string(self) -> None:
        out_transaction: OutTransaction = OutTransaction(
            self._configuration,
            "6/1/2020 3:59:59 -04:00",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("900.9"),
            RP2Decimal("2.2"),
            RP2Decimal("0.01"),
            internal_id=38,
        )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'indent' has non-integer value"):
            out_transaction.to_string(None, repr_format=False, extra_data=["foobar", "qwerty"])  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'indent' has non-positive value.*"):
            out_transaction.to_string(-1, repr_format=False, extra_data=["foobar", "qwerty"])
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'repr_format' has non-bool value .*"):
            out_transaction.to_string(1, repr_format="False", extra_data=["foobar", "qwerty"])  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'extra_data' is not of type List"):
            out_transaction.to_string(1, repr_format=False, extra_data="foobar")  # type: ignore

    def test_bad_out_transaction(self) -> None:
        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string:.*"):
            OutTransaction.type_check(None, None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_instance' is not of type OutTransaction:.*"):
            OutTransaction.type_check("my_instance", None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_instance' is not of type OutTransaction: IntraTransaction"):
            OutTransaction.type_check(
                "my_instance",
                IntraTransaction(
                    self._configuration,
                    "2021-01-12T11:51:38Z",
                    "B1",
                    "BlockFi",
                    "Bob",
                    "Coinbase",
                    "Alice",
                    RP2Decimal("10000"),
                    RP2Decimal("1"),
                    RP2Decimal("1"),
                    internal_id=45,
                ),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            OutTransaction(
                (1, 2, 3),  # type: ignore
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "GIFT",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            OutTransaction(
                None,  # type: ignore
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'internal_id' has non-integer value .*"):
            # Bad internal_id
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=(1, 2, 3),  # type: ignore
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'timestamp' has non-string value .*"):
            # Bad timestamp
            OutTransaction(
                self._configuration,
                None,  # type: ignore
                "B1",
                "Coinbase Pro",
                "Bob",
                "gIfT",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'timestamp' value has no timezone info: .*"):
            # Bad timestamp
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59",
                "B1",
                "Coinbase Pro",
                "Bob",
                "selL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'timestamp' has non-string value .*"):
            # Bad timestamp
            OutTransaction(
                self._configuration,
                (1, 2, 3),  # type: ignore
                "B1",
                "Coinbase Pro",
                "Bob",
                "GIFT",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'asset' value is not known: .*"):
            # Bad asset
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "YYY",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'asset' has non-string value .*"):
            # Bad asset
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                None,  # type: ignore
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'exchange' value is not known: .*"):
            # Bad exchange
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "CoinbasE Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'exchange' has non-string value .*"):
            # Bad exchange
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                None,  # type: ignore
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'holder' value is not known: .*"):
            # Bad holder
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "foobar",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'holder' has non-string value .*"):
            # Bad holder
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                None,  # type: ignore
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, ".*OutTransaction .*, id.*invalid transaction type .*"):
            # Bad transaction type
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "Buy",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, ".*OutTransaction .*, id.*invalid transaction type .*"):
            # Bad transaction type
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "iNteResT",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter .* has invalid transaction type value: .*"):
            # Bad transaction type
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BEND",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter .* has non-string value .*"):
            # Bad transaction type
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                None,  # type: ignore
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "OutTransaction .*, id.*parameter 'spot_price' cannot be 0"):
            # Bad spot price
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("0"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'spot_price' has non-positive value .*"):
            # Bad spot price
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("-900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'spot_price' has non-RP2Decimal value ,*"):
            # Bad spot price
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "GIFT",
                None,  # type: ignore
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_out_no_fee' has zero value"):
            # Bad crypto out no fee
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "GIFT",
                RP2Decimal("900.9"),
                RP2Decimal("0"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_out_no_fee' has non-positive value .*"):
            # Bad crypto out no fee
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("-2.2"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'crypto_out_no_fee' has non-RP2Decimal value .*"):
            # Bad crypto out no fee
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                None,  # type: ignore
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "fee-typed transaction has non-zero 'crypto_out_no_fee'"):
            # Bad crypto out no fee
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "FEE",
                RP2Decimal("900.9"),
                RP2Decimal("10"),
                RP2Decimal("0"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_fee' has non-positive value .*"):
            # Bad crypto fee
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("-0.1"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'crypto_fee' has non-RP2Decimal value .*"):
            # Bad crypto fee
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                "foobar",  # type: ignore
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'fiat_out_no_fee' has non-positive value .*"):
            # Bad fiat_out_no_fee
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                fiat_out_no_fee=RP2Decimal("-0.1"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'fiat_out_no_fee' has non-RP2Decimal value .*"):
            # Bad fiat_out_no_fee
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                fiat_out_no_fee="foobar",  # type: ignore
                internal_id=38,
            )

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'fiat_fee' has non-positive value .*"):
            # Bad fiat fee
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                fiat_out_no_fee=RP2Decimal("1800"),
                fiat_fee=RP2Decimal("-10"),
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'fiat_fee' has non-RP2Decimal value .*"):
            # Bad fiat fee
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                fiat_out_no_fee=RP2Decimal("1800"),
                fiat_fee="foobar",  # type: ignore
                internal_id=38,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'notes' has non-string value .*"):
            # Bad notes
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                notes=(1, 2, 3),  # type: ignore
                internal_id=38,
            )

        with self.assertLogs(level="WARNING") as log:
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0.1"),
                crypto_out_with_fee=RP2Decimal("2.2"),
                internal_id=38,
            )
            self.assertTrue(re.search("crypto_out_with_fee != crypto_out_no_fee.*crypto_fee:.*", log.output[0]))  # type: ignore
        with self.assertLogs(level="WARNING") as log:
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0.1"),
                fiat_out_no_fee=RP2Decimal("1981.98"),
                fiat_fee=RP2Decimal("5.9"),
                internal_id=38,
            )
            self.assertTrue(re.search("crypto_fee.*spot_price.*!= fiat_fee.*:.*", log.output[0]))  # type: ignore
        with self.assertLogs(level="WARNING") as log:
            OutTransaction(
                self._configuration,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "GIFT",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0.1"),
                fiat_out_no_fee=RP2Decimal("1081.98"),
                fiat_fee=RP2Decimal("90.09"),
                internal_id=38,
            )
            self.assertTrue(re.search("crypto_out_no_fee.*spot_price.*!= fiat_out_no_fee.*:.*", log.output[0]))  # type: ignore


if __name__ == "__main__":
    unittest.main()

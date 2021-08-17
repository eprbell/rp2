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

from configuration import Configuration
from entry_types import TransactionType
from intra_transaction import IntraTransaction
from out_transaction import OutTransaction
from rp2_decimal import RP2Decimal
from rp2_error import RP2TypeError, RP2ValueError


class TestOutTransaction(unittest.TestCase):
    _configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        TestOutTransaction._configuration = Configuration("./config/test_data.config")

    def setUp(self) -> None:
        self.maxDiff = None

    def test_taxable_out_transaction(self) -> None:
        out_transaction: OutTransaction = OutTransaction(
            self._configuration,
            38,
            "6/1/2020 3:59:59 -04:00",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("900.9"),
            RP2Decimal("2.2"),
            RP2Decimal("0.01"),
        )
        OutTransaction.type_check("my_instance", out_transaction)

        self.assertTrue(out_transaction.is_taxable())
        self.assertEqual(RP2Decimal("1990.989"), out_transaction.usd_taxable_amount)
        self.assertEqual(RP2Decimal("2.21"), out_transaction.crypto_taxable_amount)
        self.assertEqual(38, out_transaction.line)
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
        self.assertEqual(RP2Decimal("1990.989"), out_transaction.usd_balance_change)

        self.assertEqual(
            str(out_transaction),
            """OutTransaction:
  line=38
  timestamp=2020-06-01 03:59:59.000000 -0400
  asset=B1
  exchange=Coinbase Pro
  holder=Bob
  transaction_type=TransactionType.SELL
  spot_price=900.9000
  crypto_out_no_fee=2.20000000
  crypto_fee=0.01000000
  is_taxable=True
  usd_taxable_amount=1990.9890""",
        )
        self.assertEqual(
            out_transaction.to_string(2, repr_format=False, extra_data=["foobar", "qwerty"]),
            """    OutTransaction:
      line=38
      timestamp=2020-06-01 03:59:59.000000 -0400
      asset=B1
      exchange=Coinbase Pro
      holder=Bob
      transaction_type=TransactionType.SELL
      spot_price=900.9000
      crypto_out_no_fee=2.20000000
      crypto_fee=0.01000000
      is_taxable=True
      usd_taxable_amount=1990.9890
      foobar
      qwerty""",
        )
        self.assertEqual(
            out_transaction.to_string(2, repr_format=True, extra_data=["foobar", "qwerty"]),
            (
                "    OutTransaction("
                "line=38, "
                "timestamp='2020-06-01 03:59:59.000000 -0400', "
                "asset='B1', "
                "exchange='Coinbase Pro', "
                "holder='Bob', "
                "transaction_type=<TransactionType.SELL: 'sell'>, "
                "spot_price=900.9000, "
                "crypto_out_no_fee=2.20000000, "
                "crypto_fee=0.01000000, "
                "is_taxable=True, "
                "usd_taxable_amount=1990.9890, "
                "foobar, "
                "qwerty)"
            ),
        )

    def test_bad_to_string(self) -> None:
        out_transaction: OutTransaction = OutTransaction(
            self._configuration,
            38,
            "6/1/2020 3:59:59 -04:00",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("900.9"),
            RP2Decimal("2.2"),
            RP2Decimal("0.01"),
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
                    45,
                    "2021-01-12T11:51:38Z",
                    "B1",
                    "BlockFi",
                    "Bob",
                    "Coinbase",
                    "Alice",
                    RP2Decimal("10000"),
                    RP2Decimal("1"),
                    RP2Decimal("1"),
                ),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            OutTransaction(
                (1, 2, 3),  # type: ignore
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "GIFT",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            OutTransaction(
                None,  # type: ignore
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'line' has non-positive value .*"):
            # Bad line
            OutTransaction(
                self._configuration,
                -38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "GIFT",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'line' has non-integer value .*"):
            # Bad line
            OutTransaction(
                self._configuration,
                None,  # type: ignore
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'timestamp' has non-string value .*"):
            # Bad timestamp
            OutTransaction(
                self._configuration,
                38,
                None,  # type: ignore
                "B1",
                "Coinbase Pro",
                "Bob",
                "gIfT",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'timestamp' value has no timezone info: .*"):
            # Bad timestamp
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59",
                "B1",
                "Coinbase Pro",
                "Bob",
                "selL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'timestamp' has non-string value .*"):
            # Bad timestamp
            OutTransaction(
                self._configuration,
                38,
                (1, 2, 3),  # type: ignore
                "B1",
                "Coinbase Pro",
                "Bob",
                "GIFT",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'asset' value is not known: .*"):
            # Bad asset
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "YYY",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'asset' has non-string value .*"):
            # Bad asset
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                None,  # type: ignore
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'exchange' value is not known: .*"):
            # Bad exchange
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "CoinbasE Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'exchange' has non-string value .*"):
            # Bad exchange
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                None,  # type: ignore
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'holder' value is not known: .*"):
            # Bad holder
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "foobar",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'holder' has non-string value .*"):
            # Bad holder
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                None,  # type: ignore
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, ".*OutTransaction at line.*invalid transaction type .*"):
            # Bad transaction type
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "Buy",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, ".*OutTransaction at line.*invalid transaction type .*"):
            # Bad transaction type
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "eArN",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter .* has invalid transaction type value: .*"):
            # Bad transaction type
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "BEND",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter .* has non-string value .*"):
            # Bad transaction type
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                None,  # type: ignore
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, "OutTransaction at line.*parameter 'spot_price' cannot be 0"):
            # Bad spot price
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("0"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'spot_price' has non-positive value .*"):
            # Bad spot price
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("-900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'spot_price' has non-Decimal value ,*"):
            # Bad spot price
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "GIFT",
                None,  # type: ignore
                RP2Decimal("2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_out_no_fee' has zero value"):
            # Bad crypto out no fee
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "GIFT",
                RP2Decimal("900.9"),
                RP2Decimal("0"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_out_no_fee' has non-positive value .*"):
            # Bad crypto out no fee
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("-2.2"),
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'crypto_out_no_fee' has non-Decimal value .*"):
            # Bad crypto out no fee
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                None,  # type: ignore
                RP2Decimal("0"),
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_fee' has non-positive value .*"):
            # Bad crypto fee
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("-0.1"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'crypto_fee' has non-Decimal value .*"):
            # Bad crypto fee
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                "foobar",  # type: ignore
            )
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'usd_out_no_fee' has non-positive value .*"):
            # Bad usd_out_no_fee
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                usd_out_no_fee=RP2Decimal("-0.1"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'usd_out_no_fee' has non-Decimal value .*"):
            # Bad usd_out_no_fee
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                usd_out_no_fee="foobar",  # type: ignore
            )

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'usd_fee' has non-positive value .*"):
            # Bad usd fee
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                usd_out_no_fee=RP2Decimal("1800"),
                usd_fee=RP2Decimal("-10"),
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'usd_fee' has non-Decimal value .*"):
            # Bad usd fee
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                usd_out_no_fee=RP2Decimal("1800"),
                usd_fee="foobar",  # type: ignore
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'notes' has non-string value .*"):
            # Bad notes
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0"),
                notes=(1, 2, 3),  # type: ignore
            )

        with self.assertLogs(level="WARNING") as log:
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0.1"),
                RP2Decimal("2.2"),
            )
            self.assertTrue(re.search("crypto_out_with_fee != crypto_out_no_fee.*crypto_fee:.*", log.output[0]))  # type: ignore
        with self.assertLogs(level="WARNING") as log:
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0.1"),
                usd_out_no_fee=RP2Decimal("1981.98"),
                usd_fee=RP2Decimal("5.9"),
            )
            self.assertTrue(re.search("crypto_fee.*spot_price.*!= usd_fee.*:.*", log.output[0]))  # type: ignore
        with self.assertLogs(level="WARNING") as log:
            OutTransaction(
                self._configuration,
                38,
                "6/1/2020 3:59:59 -04:00",
                "B1",
                "Coinbase Pro",
                "Bob",
                "GIFT",
                RP2Decimal("900.9"),
                RP2Decimal("2.2"),
                RP2Decimal("0.1"),
                usd_out_no_fee=RP2Decimal("1081.98"),
                usd_fee=RP2Decimal("90.09"),
            )
            self.assertTrue(re.search("crypto_out_no_fee.*spot_price.*!= usd_out_no_fee.*:.*", log.output[0]))  # type: ignore


if __name__ == "__main__":
    unittest.main()

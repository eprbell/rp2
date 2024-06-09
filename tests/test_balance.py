# Copyright 2024 qwhelan
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
from datetime import date

from rp2.balance import BalanceSet
from rp2.configuration import Configuration
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.out_transaction import OutTransaction
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2ValueError
from rp2.transaction_set import TransactionSet


class TestBalanceSet(unittest.TestCase):
    _configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        TestBalanceSet._configuration = Configuration("./config/test_data.ini", US())

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_easy_negative_case(self) -> None:
        """
        Check that an exception is raised in the case where sum(OUT) > sum(IN)
        """
        asset = "B1"
        end_date = date(2024, 1, 1)
        in_transaction_set: TransactionSet = TransactionSet(self._configuration, "IN", asset)
        out_transaction_set: TransactionSet = TransactionSet(self._configuration, "OUT", asset)
        intra_transaction_set: TransactionSet = TransactionSet(self._configuration, "INTRA", asset)

        transaction1: InTransaction = InTransaction(
            self._configuration,
            "1/8/2021 8:42:43.883 -04:00",
            asset,
            "Coinbase",
            "Alice",
            "BUY",
            RP2Decimal("1000"),
            RP2Decimal("3.0002"),
            fiat_fee=RP2Decimal("20"),
            fiat_in_no_fee=RP2Decimal("3000.2"),
            fiat_in_with_fee=RP2Decimal("3020.2"),
            row=30,
        )
        in_transaction_set.add_entry(transaction1)

        transaction2: OutTransaction = OutTransaction(
            self._configuration,
            "1/9/2021 8:42:43.883 -04:00",
            asset,
            "Coinbase",
            "Alice",
            "SELL",
            RP2Decimal("1000"),
            RP2Decimal("4.0000"),
            crypto_fee=RP2Decimal("0.0002"),
            fiat_out_no_fee=RP2Decimal("4000.0"),
            row=31,
        )
        out_transaction_set.add_entry(transaction2)

        input_data = InputData(asset, in_transaction_set, out_transaction_set, intra_transaction_set)

        with self.assertRaisesRegex(
            RP2ValueError, r'B1 balance of account "Coinbase" \(holder "Alice"\) went negative \(-1.0000\) on the following transaction: .*'
        ):
            BalanceSet(self._configuration, input_data, end_date)

    def test_hard_negative_case(self) -> None:
        """
        Check that an exception is raised in the case where sum(OUT) > sum(IN) only briefly
        """
        asset = "B1"
        end_date = date(2024, 1, 1)
        in_transaction_set: TransactionSet = TransactionSet(self._configuration, "IN", asset)
        out_transaction_set: TransactionSet = TransactionSet(self._configuration, "OUT", asset)
        intra_transaction_set: TransactionSet = TransactionSet(self._configuration, "INTRA", asset)

        transaction1: InTransaction = InTransaction(
            self._configuration,
            "1/8/2021 8:42:43.883 -04:00",
            asset,
            "Coinbase",
            "Alice",
            "BUY",
            RP2Decimal("1000"),
            RP2Decimal("3.0002"),
            fiat_fee=RP2Decimal("20"),
            fiat_in_no_fee=RP2Decimal("3000.2"),
            fiat_in_with_fee=RP2Decimal("3020.2"),
            row=30,
        )
        in_transaction_set.add_entry(transaction1)

        transaction2: OutTransaction = OutTransaction(
            self._configuration,
            "1/9/2021 8:42:43.883 -04:00",
            asset,
            "Coinbase",
            "Alice",
            "SELL",
            RP2Decimal("1000"),
            RP2Decimal("4.0000"),
            crypto_fee=RP2Decimal("0.0002"),
            fiat_out_no_fee=RP2Decimal("6000.0"),
            row=31,
        )
        out_transaction_set.add_entry(transaction2)

        transaction3: InTransaction = InTransaction(
            self._configuration,
            "1/10/2021 8:42:43.883 -04:00",
            asset,
            "Coinbase",
            "Alice",
            "BUY",
            RP2Decimal("1000"),
            RP2Decimal("3.0002"),
            fiat_fee=RP2Decimal("20"),
            fiat_in_no_fee=RP2Decimal("3000.2"),
            fiat_in_with_fee=RP2Decimal("3020.2"),
            row=32,
        )
        in_transaction_set.add_entry(transaction3)

        transaction4: OutTransaction = OutTransaction(
            self._configuration,
            "1/11/2021 8:42:43.883 -04:00",
            asset,
            "Coinbase",
            "Alice",
            "SELL",
            RP2Decimal("1000"),
            RP2Decimal("2.0000"),
            crypto_fee=RP2Decimal("0.0002"),
            fiat_out_no_fee=RP2Decimal("2000.0"),
            row=33,
        )
        out_transaction_set.add_entry(transaction4)

        input_data = InputData(asset, in_transaction_set, out_transaction_set, intra_transaction_set)

        with self.assertRaisesRegex(
            RP2ValueError, r'B1 balance of account "Coinbase" \(holder "Alice"\) went negative \(-1.0000\) on the following transaction: .*'
        ):
            BalanceSet(self._configuration, input_data, end_date)


if __name__ == "__main__":
    unittest.main()

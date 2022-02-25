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
from typing import Dict, List, NamedTuple, Optional, Type

from dateutil.parser import parse

from rp2.configuration import Configuration
from rp2.entry_types import TransactionType
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.ods_parser import open_ods, parse_ods
from rp2.out_transaction import OutTransaction
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2Error, RP2TypeError, RP2ValueError
from rp2.transaction_set import TransactionSet


class ErrorAndMessage(NamedTuple):
    error_class: Type[RP2Error]
    message: str


class TestInputParser(unittest.TestCase):
    _good_input_configuration: Configuration
    _bad_input_configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        TestInputParser._good_input_configuration = Configuration("./config/test_data.config", US())
        TestInputParser._bad_input_configuration = Configuration("./config/test_bad_data.config", US())

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_good_input(self) -> None:
        self._verify_good_sheet("B1", out_empty=True, intra_empty=True)
        self._verify_good_sheet("B2", out_empty=False, intra_empty=True)
        self._verify_good_sheet("B3", out_empty=True, intra_empty=False)
        self._verify_good_sheet("B4", out_empty=False, intra_empty=False)

    def _verify_good_sheet(self, sheet_name: str, out_empty: bool, intra_empty: bool) -> None:

        asset = sheet_name
        input_file_handle: object = open_ods(configuration=self._good_input_configuration, input_file_path="./input/test_data.ods")
        input_data: InputData = parse_ods(self._good_input_configuration, asset, input_file_handle)

        # In table is always present
        self._verify_non_empty_in_table(input_data.unfiltered_in_transaction_set, asset)
        if out_empty:
            self._verify_empty_table(input_data.unfiltered_out_transaction_set)
        else:
            self._verify_non_empty_out_table(input_data.unfiltered_out_transaction_set, asset)
        if intra_empty:
            self._verify_empty_table(input_data.unfiltered_intra_transaction_set)
        else:
            self._verify_non_empty_intra_table(input_data.unfiltered_intra_transaction_set, asset)

    def _verify_empty_table(self, transaction_set: TransactionSet) -> None:
        self.assertTrue(transaction_set.is_empty())

    def _verify_non_empty_in_table(self, in_transaction_set: TransactionSet, asset: str) -> None:
        internal_ids: List[str] = ["4", "3", "7", "6", "5"]
        timestamps: List[str] = [
            "2020-01-01T08:41Z",
            "2020-02-01T11:18Z",
            "2020-03-01T09:45Z",
            "2020-04-01T09:45Z",
            "2020-05-01T14:03Z",
        ]
        transaction_types: List[TransactionType] = [
            TransactionType.BUY,
            TransactionType.INTEREST,
            TransactionType.INTEREST,
            TransactionType.BUY,
            TransactionType.BUY,
        ]
        spot_prices: List[RP2Decimal] = [RP2Decimal(s) for s in ["11000", "12000", "13000", "14000", "15000"]]
        fiat_taxable_amounts: List[RP2Decimal] = [RP2Decimal(s) for s in ["0", "24000", "39000", "0", "0"]]
        crypto_balance_changes: List[RP2Decimal] = [RP2Decimal(s) for s in ["1", "2", "3", "4", "5"]]
        fiat_balance_changes: List[RP2Decimal] = [RP2Decimal(s) for s in ["11100", "24000", "39000", "56400", "75500"]]
        is_taxable_values: List[bool] = [False, True, True, False, False]

        count: int = 0
        internal_id: str
        timestamp: str
        transaction_type: TransactionType
        spot_price: RP2Decimal
        fiat_taxable_amount: RP2Decimal
        crypto_balance_change: RP2Decimal
        fiat_balance_change: RP2Decimal
        is_taxable: bool

        transaction: Optional[InTransaction] = None
        previous_transaction: Optional[InTransaction] = None
        for (  # type: ignore
            transaction,
            internal_id,
            timestamp,
            transaction_type,
            spot_price,
            fiat_taxable_amount,
            crypto_balance_change,
            fiat_balance_change,
            is_taxable,
        ) in zip(  # type: ignore
            in_transaction_set,
            internal_ids,
            timestamps,
            transaction_types,
            spot_prices,
            fiat_taxable_amounts,
            crypto_balance_changes,
            fiat_balance_changes,
            is_taxable_values,
        ):
            if not in_transaction_set or not transaction:  # Unwrap the Optional types to keep mypy happy
                raise Exception("Internal error: in_transaction_set or transaction are None")
            self.assertEqual(in_transaction_set.get_parent(transaction), previous_transaction)
            self.assertEqual(transaction.internal_id, internal_id)
            self.assertEqual(transaction.timestamp, parse(timestamp))
            self.assertEqual(transaction.transaction_type, transaction_type)
            self.assertEqual(transaction.spot_price, spot_price)
            self.assertEqual(transaction.asset, asset)
            self.assertEqual(transaction.fiat_taxable_amount, fiat_taxable_amount)
            self.assertEqual(transaction.crypto_balance_change, crypto_balance_change)
            self.assertEqual(transaction.fiat_balance_change, fiat_balance_change)
            self.assertEqual(transaction.is_taxable(), is_taxable)
            previous_transaction = transaction
            count += 1
        self.assertEqual(count, 5)

    def _verify_non_empty_out_table(self, out_transaction_set: TransactionSet, asset: str) -> None:
        internal_ids: List[str] = ["16", "15", "17", "13", "14"]
        timestamps: List[str] = [
            "2020-01-11T11:15Z",
            "2020-02-11T19:58Z",
            "2020-04-11T07:10Z",
            "2020-04-12T17:50Z",
            "2021-06-11T05:31Z",
        ]
        transaction_types: List[TransactionType] = [
            TransactionType.SELL,
            TransactionType.SELL,
            TransactionType.GIFT,
            TransactionType.DONATE,
            TransactionType.SELL,
        ]
        spot_prices: List[RP2Decimal] = [RP2Decimal(d) for d in ["11200", "12200", "14200", "14300", "20200"]]
        fiat_taxable_amounts: List[RP2Decimal] = [RP2Decimal(d) for d in ["2240", "12200", "71000", "54197", "40400.0"]]
        crypto_balance_changes: List[RP2Decimal] = [RP2Decimal(d) for d in ["0.2", "1", "5", "3.79", "2.01"]]
        fiat_balance_changes: List[RP2Decimal] = [RP2Decimal(d) for d in ["2240", "12200", "71000", "54197", "40602.0"]]
        is_taxable_values: List[bool] = [True, True, True, True, True]

        count: int = 0
        internal_id: str
        timestamp: str
        transaction_type: TransactionType
        spot_price: RP2Decimal
        fiat_taxable_amount: RP2Decimal
        crypto_balance_change: RP2Decimal
        fiat_balance_change: RP2Decimal
        is_taxable: bool

        transaction: Optional[OutTransaction] = None
        previous_transaction: Optional[OutTransaction] = None

        for (  # type: ignore
            transaction,
            internal_id,
            timestamp,
            transaction_type,
            spot_price,
            fiat_taxable_amount,
            crypto_balance_change,
            fiat_balance_change,
            is_taxable,
        ) in zip(  # type: ignore
            out_transaction_set,
            internal_ids,
            timestamps,
            transaction_types,
            spot_prices,
            fiat_taxable_amounts,
            crypto_balance_changes,
            fiat_balance_changes,
            is_taxable_values,
        ):
            if not out_transaction_set or not transaction:  # Unwrap the Optional types to keep mypy happy
                raise Exception("Internal error: in_transaction_set or transaction are None")
            self.assertEqual(out_transaction_set.get_parent(transaction), previous_transaction)
            self.assertEqual(transaction.internal_id, internal_id)
            self.assertEqual(transaction.timestamp, parse(timestamp))
            self.assertEqual(transaction.transaction_type, transaction_type)
            self.assertEqual(transaction.spot_price, spot_price)
            self.assertEqual(transaction.asset, asset)
            self.assertEqual(transaction.fiat_taxable_amount, fiat_taxable_amount)
            self.assertEqual(transaction.crypto_balance_change, crypto_balance_change)
            self.assertEqual(transaction.fiat_balance_change, fiat_balance_change)
            self.assertEqual(transaction.is_taxable(), is_taxable)
            previous_transaction = transaction
            count += 1
        self.assertEqual(count, 5)

    def _verify_non_empty_intra_table(self, intra_transaction_set: TransactionSet, asset: str) -> None:
        internal_ids: List[str] = ["26", "24", "25", "23"]
        timestamps: List[str] = [
            "2020-01-21T18:33:14.342Z",
            "2020-02-21T20:23:31Z",
            "2020-05-21T12:58:10Z",
            "2021-07-21T10:02:02Z",
        ]
        transaction_types: List[TransactionType] = [
            TransactionType.MOVE,
            TransactionType.MOVE,
            TransactionType.MOVE,
            TransactionType.MOVE,
        ]
        spot_prices: List[RP2Decimal] = [RP2Decimal(d) for d in ["11400", "0", "14400", "21400"]]
        fiat_taxable_amounts: List[RP2Decimal] = [RP2Decimal(d) for d in ["114", "0", "288", "856"]]
        crypto_balance_changes: List[RP2Decimal] = [RP2Decimal(d) for d in ["0.01", "0", "0.02", "0.04"]]
        fiat_balance_changes: List[RP2Decimal] = [RP2Decimal(d) for d in ["114", "0", "288", "856"]]
        is_taxable_values: List[bool] = [True, False, True, True]

        count: int = 0
        internal_id: str
        timestamp: str
        transaction_type: TransactionType
        spot_price: RP2Decimal
        fiat_taxable_amount: RP2Decimal
        crypto_balance_change: RP2Decimal
        fiat_balance_change: RP2Decimal
        is_taxable: bool

        transaction: Optional[IntraTransaction] = None
        previous_transaction: Optional[IntraTransaction] = None
        for (  # type: ignore
            transaction,
            internal_id,
            timestamp,
            transaction_type,
            spot_price,
            fiat_taxable_amount,
            crypto_balance_change,
            fiat_balance_change,
            is_taxable,
        ) in zip(  # type: ignore
            intra_transaction_set,
            internal_ids,
            timestamps,
            transaction_types,
            spot_prices,
            fiat_taxable_amounts,
            crypto_balance_changes,
            fiat_balance_changes,
            is_taxable_values,
        ):
            if not intra_transaction_set or not transaction:  # Unwrap the Optional types to keep mypy happy
                raise Exception("Internal error: intra_transaction_set or transaction are None")
            self.assertEqual(intra_transaction_set.get_parent(transaction), previous_transaction)
            self.assertEqual(transaction.internal_id, internal_id)
            self.assertEqual(transaction.timestamp, parse(timestamp))
            self.assertEqual(transaction.transaction_type, transaction_type)
            self.assertEqual(transaction.spot_price, spot_price)
            self.assertEqual(transaction.asset, asset)
            self.assertEqual(transaction.fiat_taxable_amount, fiat_taxable_amount)
            self.assertEqual(transaction.crypto_balance_change, crypto_balance_change)
            self.assertEqual(transaction.fiat_balance_change, fiat_balance_change)
            self.assertEqual(transaction.is_taxable(), is_taxable)
            previous_transaction = transaction
            count += 1
        self.assertEqual(count, 4)

    def test_bad_input(self) -> None:

        sheets_to_expected_messages: Dict[str, ErrorAndMessage] = {
            "B1": ErrorAndMessage(RP2ValueError, "IN table not found"),
            "B2": ErrorAndMessage(RP2ValueError, 'Found an invalid cell "foo" while looking for a table-begin token'),
            "B3": ErrorAndMessage(RP2ValueError, 'Found an invalid cell "bar" while looking for a table-begin token'),
            "B4": ErrorAndMessage(RP2ValueError, "Found end-table keyword without having found a table-begin keyword first"),
            "B5": ErrorAndMessage(RP2ValueError, "Found end-table keyword without having found a table-begin keyword first"),
            "B6": ErrorAndMessage(RP2ValueError, "TABLE END not found for EntrySetType.IN table"),
            "B7": ErrorAndMessage(RP2ValueError, "TABLE END not found for EntrySetType.OUT table"),
            "B8": ErrorAndMessage(RP2ValueError, "TABLE END not found for EntrySetType.INTRA table"),
            "B9": ErrorAndMessage(RP2ValueError, 'Found "IN" keyword while parsing table EntrySetType.IN'),
            "B10": ErrorAndMessage(RP2ValueError, 'Found "OUT" keyword while parsing table EntrySetType.OUT'),
            "B11": ErrorAndMessage(RP2ValueError, 'Found "INTRA" keyword while parsing table EntrySetType.INTRA'),
            "B12": ErrorAndMessage(RP2ValueError, 'Found "OUT" keyword while parsing table EntrySetType.IN'),
            "B13": ErrorAndMessage(RP2ValueError, 'Found "OUT" keyword while parsing table EntrySetType.INTRA'),
            "B14": ErrorAndMessage(RP2ValueError, "IN table not found or empty"),
            "B15": ErrorAndMessage(RP2ValueError, "TABLE END not found for EntrySetType.IN table"),
            "B16": ErrorAndMessage(RP2ValueError, "Parameter 'data' has length .*, but required minimum from in-table headers in .* is .*"),
            "B17": ErrorAndMessage(RP2ValueError, "Parameter 'data' has length .*, but required minimum from out-table headers in .* is .*"),
            "B18": ErrorAndMessage(RP2TypeError, "Parameter 'asset' has non-string value .*"),
            "B19": ErrorAndMessage(RP2ValueError, "Found an empty cell while parsing table EntrySetType.OUT"),
            "B20": ErrorAndMessage(RP2ValueError, "IN table not found"),
            "B21": ErrorAndMessage(RP2ValueError, "IN table not found or empty"),
            "B22": ErrorAndMessage(RP2ValueError, "Found data with no header"),
            "B23": ErrorAndMessage(RP2ValueError, "Parameter 'timestamp' value has no timezone info: .*"),
            "B24": ErrorAndMessage(RP2ValueError, "Parameter 'exchange' value is not known: .*"),
            "B25": ErrorAndMessage(RP2ValueError, "Parameter 'holder' value is not known: .*"),
            "B26": ErrorAndMessage(RP2ValueError, "Parameter 'transaction_type' has invalid transaction type value: .*"),
            "B27": ErrorAndMessage(RP2ValueError, "Parameter 'asset' value is not known: .*"),
            "B28": ErrorAndMessage(RP2ValueError, "Parameter 'crypto_in' has non-positive value .*"),
            "B29": ErrorAndMessage(RP2ValueError, "Parameter 'spot_price' has non-positive value .*"),
            "B30": ErrorAndMessage(RP2ValueError, "Parameter 'fiat_fee' has non-positive value .*"),
            "B31": ErrorAndMessage(RP2ValueError, "Found an empty cell while parsing table EntrySetType.IN"),
            "B32": ErrorAndMessage(RP2ValueError, "TABLE END not found for EntrySetType.OUT table"),
            "B33": ErrorAndMessage(RP2ValueError, "Found more than one IN symbol"),
            "B34": ErrorAndMessage(RP2ValueError, "IN table not found or empty"),
            "B35": ErrorAndMessage(RP2ValueError, "IN table not found or empty"),
            "B36": ErrorAndMessage(RP2ValueError, "IN table not found or empty"),
        }

        sheet: str
        message: str
        for sheet, (error_class, message) in sheets_to_expected_messages.items():
            with self.assertRaisesRegex(error_class, message):
                asset: str = sheet
                input_file_handle: object = open_ods(configuration=self._bad_input_configuration, input_file_path="./input/test_bad_data.ods")
                parse_ods(self._bad_input_configuration, asset, input_file_handle)


if __name__ == "__main__":
    unittest.main()

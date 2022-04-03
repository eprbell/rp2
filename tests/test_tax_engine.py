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

from rp2_test_output import RP2_TEST_OUTPUT  # pylint: disable=wrong-import-order

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.computed_data import ComputedData
from rp2.configuration import Configuration
from rp2.input_data import InputData
from rp2.ods_parser import open_ods, parse_ods
from rp2.out_transaction import OutTransaction
from rp2.plugin.accounting_method.fifo import AccountingMethod
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError
from rp2.tax_engine import compute_tax


class TestTaxEngine(unittest.TestCase):
    _good_input_configuration: Configuration
    _bad_input_configuration: Configuration
    _accounting_method: AbstractAccountingMethod

    @classmethod
    def setUpClass(cls) -> None:
        TestTaxEngine._good_input_configuration = Configuration("./config/test_data.config", US())
        TestTaxEngine._bad_input_configuration = Configuration("./config/test_bad_data.config", US())
        TestTaxEngine._accounting_method = AccountingMethod()

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_good_input(self) -> None:
        self._verify_good_output("B1")
        self._verify_good_output("B2")
        self._verify_good_output("B3")
        self._verify_good_output("B4")

    def _verify_good_output(self, sheet_name: str) -> None:
        asset = sheet_name

        # Parser is tested separately (on same input) in test_input_parser.py
        input_file_handle: object = open_ods(self._good_input_configuration, "./input/test_data.ods")
        input_data: InputData = parse_ods(self._good_input_configuration, asset, input_file_handle)

        # In table is always present
        computed_data: ComputedData = compute_tax(self._good_input_configuration, self._accounting_method, input_data)

        if asset in RP2_TEST_OUTPUT:
            self.assertEqual(str(computed_data.gain_loss_set), RP2_TEST_OUTPUT[asset])

    def test_bad_input(self) -> None:
        asset = "B4"
        input_file_handle: object = open_ods(self._good_input_configuration, "./input/test_data.ods")
        input_data: InputData = parse_ods(self._bad_input_configuration, asset, input_file_handle)

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            compute_tax(
                None,  # type: ignore
                self._accounting_method,
                input_data,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            compute_tax(
                1111,  # type: ignore
                self._accounting_method,
                input_data,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'accounting_method' is not of type AbstractAccountingMethod: .*"):
            compute_tax(
                self._good_input_configuration,
                None,  # type: ignore
                input_data,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'accounting_method' is not of type AbstractAccountingMethod: .*"):
            compute_tax(
                self._good_input_configuration,
                1111,  # type: ignore
                input_data,
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'input_data' is not of type InputData: .*"):
            compute_tax(
                self._bad_input_configuration,
                self._accounting_method,
                None,  # type: ignore
            )
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'input_data' is not of type InputData: .*"):
            compute_tax(
                self._bad_input_configuration,
                self._accounting_method,
                "foobar",  # type: ignore
            )

        input_data.unfiltered_out_transaction_set.add_entry(
            OutTransaction(
                self._good_input_configuration,
                "6/1/2020 3:59:59 -04:00",
                asset,
                "Coinbase Pro",
                "Bob",
                "SELL",
                RP2Decimal("900.9"),
                RP2Decimal("20.2"),
                RP2Decimal("1"),
                internal_id=38,
            )
        )

        with self.assertRaisesRegex(RP2ValueError, "Total in-transaction crypto value < total taxable crypto value"):
            compute_tax(
                self._good_input_configuration,
                self._accounting_method,
                input_data,
            )


if __name__ == "__main__":
    unittest.main()

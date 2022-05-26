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

import json
import os
import unittest
from datetime import datetime
from tempfile import NamedTemporaryFile
from typing import Any, Optional

import jsonschema
from dateutil.tz import tzoffset, tzutc

from rp2.abstract_country import AbstractCountry
from rp2.configuration import Configuration
from rp2.plugin.country.us import US
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError


class TestConfiguration(unittest.TestCase):
    _country: AbstractCountry
    _configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        TestConfiguration._country = US()
        TestConfiguration._configuration = Configuration("./config/test_data.config", TestConfiguration._country)

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    @staticmethod
    def _test_config(config: Any) -> Configuration:
        result: Optional[Configuration] = None
        with NamedTemporaryFile(delete=False) as temporary_file:
            temporary_file.write(json.dumps(config).encode())
            temporary_file.flush()

            result = Configuration(temporary_file.name, TestConfiguration._country)
        os.remove(temporary_file.name)

        return result

    def test_config_file(self) -> None:
        config: Any = {}
        with self.assertRaisesRegex(KeyError, "in_header"):
            self._test_config(config)

        config["in_header"] = None
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "None is not of type 'object'"):
            self._test_config(config)

        config["in_header"] = {}
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "'timestamp' is a required property"):
            self._test_config(config)

        config["in_header"].update(
            {
                "timestamp": 0,
                "asset": 6,
                "exchange": 1,
                "holder": 2,
                "transaction_type": 5,
            }
        )
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "'spot_price' is a required property"):
            self._test_config(config)

        config["in_header"].update({"spot_price": 8, "crypto_in": 7, "fiat_fee": 11, "fiat_in_no_fee": 9, "fiat_in_with_fee": 10, "notes": 12})
        with self.assertRaisesRegex(KeyError, "out_header"):
            self._test_config(config)

        config["out_header"] = "foobar"
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "'foobar' is not of type 'object'"):
            self._test_config(config)

        config["out_header"] = {}
        config["out_header"].update({"timestamp": 0, "asset": 6, "exchange": 1, "holder": 2, "transaction_type": 5})
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "'spot_price' is a required property"):
            self._test_config(config)

        config["out_header"].update({"spot_price": 8, "crypto_out_no_fee": 7, "crypto_fee": 9, "notes": 12})
        with self.assertRaisesRegex(KeyError, "intra_header"):
            self._test_config(config)

        config["intra_header"] = [1, 2, 3]
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, r"\[1, 2, 3\] is not of type 'object'"):
            self._test_config(config)

        config["intra_header"] = {}
        config["intra_header"].update(
            {
                "timestamp": 0,
                "asset": 6,
                "from_exchange": 1,
                "from_holder": 2,
                "to_exchange": 3,
            }
        )
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "'to_holder' is a required property"):
            self._test_config(config)

        config["intra_header"].update({"to_holder": 4, "spot_price": 8, "crypto_sent": 7, "crypto_received": 10, "notes": 12})
        with self.assertRaisesRegex(KeyError, "assets"):
            self._test_config(config)

        config["assets"] = "foobar"
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "'foobar' is not of type 'array'"):
            self._test_config(config)

        config["assets"] = []
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, r"\[\] is too short"):
            self._test_config(config)

        config["assets"] = [1, 2, 3]
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "1 is not of type 'string'"):
            self._test_config(config)

        config["assets"] = ["B1", "B2"]
        with self.assertRaisesRegex(KeyError, "exchanges"):
            self._test_config(config)

        config["exchanges"] = None
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "None is not of type 'array'"):
            self._test_config(config)

        config["exchanges"] = []
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, r"\[\] is too short"):
            self._test_config(config)

        config["exchanges"] = [1, 2, 3]
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "1 is not of type 'string'"):
            self._test_config(config)

        config["exchanges"] = ["BlockFi", "Coinbase", "Kraken"]
        with self.assertRaisesRegex(KeyError, "holders"):
            self._test_config(config)

        config["holders"] = 7
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "7 is not of type 'array'"):
            self._test_config(config)

        config["holders"] = []
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, r"\[\] is too short"):
            self._test_config(config)

        config["holders"] = [1, 2, 3]
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "1 is not of type 'string'"):
            self._test_config(config)

        config["holders"] = ["Bob"]
        self.assertIsNotNone(self._test_config(config))

        config["in_header"].update({"spot_price": -8})
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "-8 is less than the minimum of 0"):
            self._test_config(config)

        config["in_header"].update({"spot_price": 8})
        config["out_header"].update({"notes": -12})
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "-12 is less than the minimum of 0"):
            self._test_config(config)

        config["out_header"].update({"notes": 12})
        config["intra_header"].update({"crypto_sent": -7})
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "-7 is less than the minimum of 0"):
            self._test_config(config)

        config["intra_header"].update({"crypto_sent": 7})
        config["assets"].append("B1")
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, ".* has non-unique elements"):
            self._test_config(config)

        config["assets"] = ["B1", "B2"]

        config["in_header"].update({"foobar": 23})
        with self.assertRaisesRegex(jsonschema.exceptions.ValidationError, "Additional properties are not allowed .*'foobar' was unexpected.*"):
            self._test_config(config)

    def test_creation(self) -> None:
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'country' is not of type AbstractCountry: .*"):
            Configuration("./config/test_data.config", None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration_path' has non-string value .*"):
            Configuration(None, self._country)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration_path' has non-string value .*"):
            Configuration(111, self._country)  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "/non/existing/file does not exist"):
            Configuration("/non/existing/file", self._country)
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'from_date' is not of type date"):
            Configuration("./config/test_data.config", self._country, from_date=None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'from_date' is not of type date"):
            Configuration("./config/test_data.config", self._country, from_date="foobar")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'to_date' is not of type date"):
            Configuration("./config/test_data.config", self._country, to_date=None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'to_date' is not of type date"):
            Configuration("./config/test_data.config", self._country, to_date="foobar")  # type: ignore

    def test_argument_packs(self) -> None:
        self.assertEqual(
            str(self._configuration.get_in_table_constructor_argument_pack([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120])),
            (
                "{'timestamp': 0, 'asset': 60, 'exchange': 10, 'holder': 20, 'transaction_type': 50, 'spot_price': 80, "
                "'crypto_in': 70, 'fiat_fee': 110, 'fiat_in_no_fee': 90, 'fiat_in_with_fee': 100, 'notes': 120}"
            ),
        )
        self.assertEqual(
            str(self._configuration.get_out_table_constructor_argument_pack([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120])),
            (
                "{'timestamp': 0, 'asset': 60, 'exchange': 10, 'holder': 20, 'transaction_type': 50, 'spot_price': 80, "
                "'crypto_out_no_fee': 70, 'crypto_fee': 90, 'notes': 120}"
            ),
        )
        self.assertEqual(
            str(self._configuration.get_intra_table_constructor_argument_pack([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120])),
            (
                "{'timestamp': 0, 'asset': 60, 'from_exchange': 10, 'from_holder': 20, 'to_exchange': 30, 'to_holder': 40, "
                "'spot_price': 80, 'crypto_sent': 70, 'crypto_received': 100, 'notes': 120}"
            ),
        )

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'data' value is not a List"):
            self._configuration.get_in_table_constructor_argument_pack(None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'data' value is not a List"):
            self._configuration.get_out_table_constructor_argument_pack("foobar")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'data' value is not a List"):
            self._configuration.get_intra_table_constructor_argument_pack(8)  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'data' has length .*, but required minimum from in-table headers in .* is .*"):
            self._configuration.get_in_table_constructor_argument_pack([1, 2, 3])
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'data' has length .*, but required minimum from out-table headers in .* is .*"):
            self._configuration.get_out_table_constructor_argument_pack([])
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'data' has length .*, but required minimum from intra-table headers in .* is .*"):
            self._configuration.get_intra_table_constructor_argument_pack([1])

    def test_get_column_position(self) -> None:
        self.assertEqual(self._configuration.get_in_table_column_position("timestamp"), 0)
        self.assertEqual(self._configuration.get_in_table_column_position("asset"), 6)
        self.assertEqual(self._configuration.get_in_table_column_position("exchange"), 1)
        self.assertEqual(self._configuration.get_in_table_column_position("holder"), 2)
        self.assertEqual(self._configuration.get_in_table_column_position("transaction_type"), 5)
        self.assertEqual(self._configuration.get_in_table_column_position("spot_price"), 8)
        self.assertEqual(self._configuration.get_in_table_column_position("crypto_in"), 7)
        self.assertEqual(self._configuration.get_in_table_column_position("fiat_fee"), 11)
        self.assertEqual(self._configuration.get_in_table_column_position("fiat_in_no_fee"), 9)
        self.assertEqual(self._configuration.get_in_table_column_position("fiat_in_with_fee"), 10)
        self.assertEqual(self._configuration.get_in_table_column_position("notes"), 12)

        self.assertEqual(self._configuration.get_out_table_column_position("timestamp"), 0)
        self.assertEqual(self._configuration.get_out_table_column_position("asset"), 6)
        self.assertEqual(self._configuration.get_out_table_column_position("exchange"), 1)
        self.assertEqual(self._configuration.get_out_table_column_position("holder"), 2)
        self.assertEqual(self._configuration.get_out_table_column_position("transaction_type"), 5)
        self.assertEqual(self._configuration.get_out_table_column_position("spot_price"), 8)
        self.assertEqual(self._configuration.get_out_table_column_position("crypto_out_no_fee"), 7)
        self.assertEqual(self._configuration.get_out_table_column_position("crypto_fee"), 9)
        self.assertEqual(self._configuration.get_out_table_column_position("notes"), 12)

        self.assertEqual(self._configuration.get_intra_table_column_position("timestamp"), 0)
        self.assertEqual(self._configuration.get_intra_table_column_position("asset"), 6)
        self.assertEqual(self._configuration.get_intra_table_column_position("from_exchange"), 1)
        self.assertEqual(self._configuration.get_intra_table_column_position("from_holder"), 2)
        self.assertEqual(self._configuration.get_intra_table_column_position("to_exchange"), 3)
        self.assertEqual(self._configuration.get_intra_table_column_position("to_holder"), 4)
        self.assertEqual(self._configuration.get_intra_table_column_position("spot_price"), 8)
        self.assertEqual(self._configuration.get_intra_table_column_position("crypto_sent"), 7)
        self.assertEqual(self._configuration.get_intra_table_column_position("crypto_received"), 10)
        self.assertEqual(self._configuration.get_intra_table_column_position("notes"), 12)

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'input_parameter' has non-string value .*"):
            self._configuration.get_in_table_column_position(None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'input_parameter' has non-string value .*"):
            self._configuration.get_out_table_column_position(12)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'input_parameter' has non-string value .*"):
            self._configuration.get_intra_table_column_position([1, 2])  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Unknown 'input_parameter' .*"):
            self._configuration.get_in_table_column_position("non_existent")
        with self.assertRaisesRegex(RP2ValueError, "Unknown 'input_parameter' .*"):
            self._configuration.get_out_table_column_position("foobar")
        with self.assertRaisesRegex(RP2ValueError, "Unknown 'input_parameter' .*"):
            self._configuration.get_intra_table_column_position("whatever")

    def test_string_representation(self) -> None:
        self.assertEqual(
            str(self._configuration),
            (
                "Configuration(configuration_path=./config/test_data.config, country=US(country_iso_code=us, "
                "currency_iso_code=usd, long_term_capital_gain_period=365), from_date=non-specified, "
                "to_date=non-specified, in_header={'timestamp': 0, 'asset': 6, 'exchange': 1, 'holder': 2, 'transaction_type': 5, 'spot_price': 8, "
                "'crypto_in': 7, 'fiat_fee': 11, 'fiat_in_no_fee': 9, 'fiat_in_with_fee': 10, 'notes': 12}, out_header={'timestamp': 0, 'asset': 6, "
                "'exchange': 1, 'holder': 2, 'transaction_type': 5, 'spot_price': 8, 'crypto_out_no_fee': 7, 'crypto_fee': 9, 'notes': 12}, "
                "intra_header={'timestamp': 0, 'asset': 6, 'from_exchange': 1, 'from_holder': 2, 'to_exchange': 3, 'to_holder': 4, "
                "'spot_price': 8, 'crypto_sent': 7, 'crypto_received': 10, 'notes': 12}, assets=['B1', 'B2', 'B3', 'B4'], "
                "exchanges=['BlockFi', 'Coinbase', 'Coinbase Pro', 'Kraken'], holders=['Alice', 'Bob'])"
            ),
        )

    def test_internal_id(self) -> None:
        self.assertEqual(13, self._configuration.type_check_internal_id("internal_id", 13))

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_internal_id(None, 10)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'internal_id' has non-integer value .*"):
            self._configuration.type_check_internal_id("internal_id", 7.7)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'internal_id' has non-integer value .*"):
            self._configuration.type_check_internal_id("internal_id", None)  # type: ignore

    def test_timestamp(self) -> None:
        date: datetime = self._configuration.type_check_timestamp_from_string("timestamp", "2020-06-21T23:29:03.117Z")
        self.assertEqual(2020, date.year)
        self.assertEqual(6, date.month)
        self.assertEqual(21, date.day)
        self.assertEqual(23, date.hour)
        self.assertEqual(29, date.minute)
        self.assertEqual(3, date.second)
        self.assertEqual(117000, date.microsecond)
        self.assertEqual(tzutc(), date.tzinfo)

        date = self._configuration.type_check_timestamp_from_string("timestamp", "2020-12-01 03:59:49 -04:00")
        self.assertEqual(2020, date.year)
        self.assertEqual(12, date.month)
        self.assertEqual(1, date.day)
        self.assertEqual(3, date.hour)
        self.assertEqual(59, date.minute)
        self.assertEqual(49, date.second)
        self.assertEqual(0, date.microsecond)
        self.assertEqual(tzoffset(None, -14400), date.tzinfo)

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_timestamp_from_string(12, "2020-12-01 03:59:49 -04:00")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'timestamp' has non-string value .*"):
            self._configuration.type_check_timestamp_from_string("timestamp", 2020)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'timestamp' has non-string value .*"):
            self._configuration.type_check_timestamp_from_string("timestamp", None)  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'timestamp' value has no timezone info: .*"):
            self._configuration.type_check_timestamp_from_string("timestamp", "2020-12-01 03:59:49")
        with self.assertRaisesRegex(RP2ValueError, "hour must be in 0..23"):
            self._configuration.type_check_timestamp_from_string("timestamp", "2020-12-01 25:59:49")
        with self.assertRaisesRegex(RP2ValueError, "Unknown string format: .*"):
            self._configuration.type_check_timestamp_from_string("timestamp", "foo bar baz")

    def test_exchange(self) -> None:
        self.assertEqual("Coinbase Pro", self._configuration.type_check_exchange("exchange", "Coinbase Pro"))

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_exchange(None, "Coinbase")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'exchange' has non-string value .*"):
            self._configuration.type_check_exchange("exchange", 34.6)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'exchange' has non-string value .*"):
            self._configuration.type_check_exchange("exchange", None)  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'exchange' value is not known: .*"):
            self._configuration.type_check_exchange("exchange", "coinbase pro")
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'exchange' value is not known: .*"):
            self._configuration.type_check_exchange("exchange", "Coinbase Proo")

    def test_holder(self) -> None:
        self.assertEqual("Bob", self._configuration.type_check_holder("holder", "Bob"))

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_holder(None, "Alice")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'holder' has non-string value .*"):
            self._configuration.type_check_holder("holder", 34.6)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'holder' has non-string value .*"):
            self._configuration.type_check_holder("holder", None)  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'holder' value is not known: .*"):
            self._configuration.type_check_holder("holder", "John")

    def test_asset(self) -> None:
        self.assertEqual("B1", self._configuration.type_check_asset("asset", "B1"))
        self.assertEqual("B2", self._configuration.type_check_asset("asset", "B2"))

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_asset(None, "B1")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'asset' has non-string value .*"):
            self._configuration.type_check_asset("asset", 34.6)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'asset' has non-string value .*"):
            self._configuration.type_check_asset("asset", None)  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'asset' value is not known: .*"):
            self._configuration.type_check_asset("asset", "btc")
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'asset' value is not known: .*"):
            self._configuration.type_check_asset("asset", "qwerty")

    def test_string(self) -> None:
        self.assertEqual("foobar", self._configuration.type_check_string("my_string", "foobar"))

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_string(None, "foobar")  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_string' has non-string value .*"):
            self._configuration.type_check_string("my_string", [1, 2, 3])  # type: ignore

    def test_int(self) -> None:
        self.assertEqual(5, self._configuration.type_check_int("my_int", 5))
        self.assertEqual(5, self._configuration.type_check_positive_int("my_int", 5))
        self.assertEqual(5, self._configuration.type_check_positive_int("my_int", 5, non_zero=True))

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_int(None, 5)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_int' has non-integer value .*"):
            self._configuration.type_check_int("my_int", None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_int' has non-integer value .*"):
            self._configuration.type_check_int("my_int", "5")  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_positive_int(None, 5)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_int' has non-integer value .*"):
            self._configuration.type_check_positive_int("my_int", None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_int' has non-integer value .*"):
            self._configuration.type_check_positive_int("my_int", "5")  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'my_int' has non-positive value .*"):
            self._configuration.type_check_positive_int("my_int", -5)
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'my_int' has zero value"):
            self._configuration.type_check_positive_int("my_int", 0, non_zero=True)

    def test_float(self) -> None:
        self.assertEqual(5.5, self._configuration.type_check_float("my_float", 5.5))
        self.assertEqual(5.5, self._configuration.type_check_positive_float("my_float", 5.5))
        self.assertEqual(5.5, self._configuration.type_check_positive_float("my_float", 5.5, non_zero=True))

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_float(None, 5.5)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_float' has non-numeric value .*"):
            self._configuration.type_check_float("my_float", None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_float' has non-numeric value .*"):
            self._configuration.type_check_float("my_float", "5.5")  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_positive_float(None, 5.5)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_float' has non-numeric value .*"):
            self._configuration.type_check_positive_float("my_float", None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_float' has non-numeric value .*"):
            self._configuration.type_check_positive_float("my_float", "5.5")  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'my_float' has non-positive value .*"):
            self._configuration.type_check_positive_float("my_float", -5.5)
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'my_float' has zero value"):
            self._configuration.type_check_positive_float("my_float", 0, non_zero=True)

    def test_rp2_decimal(self) -> None:
        minus_one: RP2Decimal = RP2Decimal("-1")
        one: RP2Decimal = RP2Decimal("1")

        self.assertEqual(minus_one, self._configuration.type_check_decimal("minus_one", minus_one))
        self.assertEqual(one, self._configuration.type_check_positive_decimal("one", one))

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_decimal(None, one)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_decimal' has non-RP2Decimal value .*"):
            self._configuration.type_check_decimal("my_decimal", None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_decimal' has non-RP2Decimal value .*"):
            self._configuration.type_check_decimal("my_decimal", "5.5")  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_positive_decimal(None, one)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_decimal' has non-RP2Decimal value .*"):
            self._configuration.type_check_positive_decimal("my_decimal", None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_decimal' has non-RP2Decimal value .*"):
            self._configuration.type_check_positive_decimal("my_decimal", "5.5")  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'my_decimal' has non-positive value .*"):
            self._configuration.type_check_positive_decimal("my_decimal", minus_one)
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'my_decimal' has zero value"):
            self._configuration.type_check_positive_decimal("my_decimal", ZERO, non_zero=True)

    def test_bool(self) -> None:
        self.assertEqual(True, self._configuration.type_check_bool("my_bool", True))
        self.assertEqual(False, self._configuration.type_check_bool("my_bool", False))

        with self.assertRaisesRegex(RP2TypeError, "Parameter name is not a string: .*"):
            self._configuration.type_check_bool(14, True)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_bool' has non-bool value .*"):
            self._configuration.type_check_bool("my_bool", None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'my_bool' has non-bool value .*"):
            self._configuration.type_check_bool("my_bool", "True")  # type: ignore


if __name__ == "__main__":
    unittest.main()

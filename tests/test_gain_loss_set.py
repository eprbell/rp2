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
from typing import Dict, List

from rp2_test_output import RP2_TEST_OUTPUT  # pylint: disable=wrong-import-order

from rp2.configuration import Configuration
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
from rp2.in_transaction import InTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.plugin.accounting_method.fifo import AccountingMethod
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError

_ASSETS: List[str] = ["B1", "B2", "B3", "B4"]


class TestGainLossSet(unittest.TestCase):
    _configuration: Configuration
    _accounting_method: AccountingMethod

    _in3: Dict[str, InTransaction]
    _in2: Dict[str, InTransaction]
    _in6: Dict[str, InTransaction]
    _in5: Dict[str, InTransaction]
    _in4: Dict[str, InTransaction]

    _out15: Dict[str, OutTransaction]
    _out14: Dict[str, OutTransaction]
    _out16: Dict[str, OutTransaction]
    _out12: Dict[str, OutTransaction]
    _out13: Dict[str, OutTransaction]

    _intra25: Dict[str, IntraTransaction]
    _intra24: Dict[str, IntraTransaction]
    _intra22: Dict[str, IntraTransaction]

    _gain_loss1: GainLoss
    _gain_loss2: GainLoss

    _gain_loss_set: Dict[str, GainLossSet]

    @classmethod
    def setUpClass(cls) -> None:
        cls._configuration = Configuration("./config/test_data.config", US())
        cls._accounting_method = AccountingMethod()

        cls._in3 = {}
        cls._in2 = {}
        cls._in6 = {}
        cls._in5 = {}
        cls._in4 = {}

        cls._out15 = {}
        cls._out14 = {}
        cls._out16 = {}
        cls._out12 = {}
        cls._out13 = {}

        cls._intra25 = {}
        cls._intra24 = {}
        cls._intra22 = {}

        cls._gain_loss_set = {}

        for asset in _ASSETS:
            cls._initialize_transactions(asset)

    @classmethod
    # Reproduce programmatically the data from sheets B1 to B4 in input/test_data.ods
    def _initialize_transactions(cls, asset: str) -> None:
        cls._in3[asset] = InTransaction(
            cls._configuration,
            "2020-01-01 08:41:00.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "BUY",
            RP2Decimal("11000"),
            RP2Decimal("1"),
            fiat_fee=RP2Decimal("100.00"),
            internal_id=4,
        )
        cls._in2[asset] = InTransaction(
            cls._configuration,
            "2020-02-01 11:18:00.000000 +0000",
            asset,
            "BlockFi",
            "Bob",
            "INTEREST",
            RP2Decimal("12000.0"),
            RP2Decimal("2.0"),
            fiat_fee=RP2Decimal("0"),
            internal_id=3,
        )
        cls._in6[asset] = InTransaction(
            cls._configuration,
            "2020-03-01 09:45:00.000000 +0000",
            asset,
            "BlockFi",
            "Bob",
            "INTEREST",
            RP2Decimal("13000.0"),
            RP2Decimal("3"),
            fiat_fee=RP2Decimal("0"),
            internal_id=7,
        )
        cls._in5[asset] = InTransaction(
            cls._configuration,
            "2020-04-01T09:45Z",
            asset,
            "Coinbase",
            "Bob",
            "BUY",
            RP2Decimal("14000.0"),
            RP2Decimal("4.0"),
            fiat_fee=RP2Decimal("400"),
            internal_id=6,
        )
        cls._in4[asset] = InTransaction(
            cls._configuration,
            "2020-05-01T14:03Z",
            asset,
            "Coinbase",
            "Bob",
            "BUY",
            RP2Decimal("15000.0"),
            RP2Decimal("5.0"),
            fiat_fee=RP2Decimal("500"),
            internal_id=5,
        )
        cls._out15[asset] = OutTransaction(
            cls._configuration,
            "2020-01-11 11:15:00.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "SELL",
            RP2Decimal("11200.0"),
            RP2Decimal("0.2"),
            RP2Decimal("0"),
            internal_id=16,
        )
        cls._out14[asset] = OutTransaction(
            cls._configuration,
            "2020-02-11 19:58:00.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "SELL",
            RP2Decimal("12200.0"),
            RP2Decimal("1.0"),
            RP2Decimal("0"),
            internal_id=15,
        )
        cls._out16[asset] = OutTransaction(
            cls._configuration,
            "2020-04-11 07:10:00.000000 +0000",
            asset,
            "BlockFi",
            "Bob",
            "GIFT",
            RP2Decimal("14200.00"),
            RP2Decimal("5.0"),
            RP2Decimal("0"),
            internal_id=17,
        )
        cls._out12[asset] = OutTransaction(
            cls._configuration,
            "2020-04-12 17:50:00.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "DONATE",
            RP2Decimal("14300"),
            RP2Decimal("3.79"),
            RP2Decimal("0"),
            internal_id=13,
        )
        cls._out13[asset] = OutTransaction(
            cls._configuration,
            "2021-06-11 05:31:00.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "SELL",
            RP2Decimal("20200.00"),
            RP2Decimal("2"),
            RP2Decimal("0.01"),
            internal_id=14,
        )
        cls._intra25[asset] = IntraTransaction(
            cls._configuration,
            "2020-01-21 18:33:14.342000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "BlockFi",
            "Bob",
            RP2Decimal("11400.0"),
            RP2Decimal("0.1"),
            RP2Decimal("0.09"),
            internal_id=26,
        )
        cls._intra24[asset] = IntraTransaction(
            cls._configuration,
            "2020-05-21 12:58:10.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "Kraken",
            "Alice",
            RP2Decimal("14400.0"),
            RP2Decimal("0.2"),
            RP2Decimal("0.18"),
            internal_id=25,
        )
        cls._intra22[asset] = IntraTransaction(
            cls._configuration,
            "2021-07-21 10:02:02.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "Kraken",
            "Alice",
            RP2Decimal("21400.0"),
            RP2Decimal("0.5"),
            RP2Decimal("0.46"),
            internal_id=23,
        )
        cls._gain_loss_set[asset] = GainLossSet(cls._configuration, cls._accounting_method, asset)
        if asset == "B1":
            # In transactions only
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("2"), cls._in2[asset], None))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("3"), cls._in6[asset], None))
        elif asset == "B2":
            # In and out transactions only
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.2"), cls._out15[asset], cls._in3[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("2"), cls._in2[asset], None))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.8"), cls._out14[asset], cls._in3[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.20"), cls._out14[asset], cls._in2[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("3"), cls._in6[asset], None))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("1.8"), cls._out16[asset], cls._in2[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("3"), cls._out16[asset], cls._in6[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.2"), cls._out16[asset], cls._in5[asset]))
            cls._gain_loss_set[asset].add_entry(
                GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("3.79"), cls._out12[asset], cls._in5[asset])
            )  # ==
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.01"), cls._out13[asset], cls._in5[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("2.0"), cls._out13[asset], cls._in4[asset]))
        elif asset == "B3":
            # In and intra transactions only
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.01"), cls._intra25[asset], cls._in3[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("2"), cls._in2[asset], None))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("3"), cls._in6[asset], None))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.02"), cls._intra24[asset], cls._in3[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.04"), cls._intra22[asset], cls._in3[asset]))
        else:  # asset == "B4", "BTC" or others
            cls._gain_loss1 = GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.2"), cls._out15[asset], cls._in3[asset])
            cls._gain_loss2 = GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.01"), cls._intra25[asset], cls._in3[asset])
            cls._gain_loss_set[asset].add_entry(cls._gain_loss1)
            cls._gain_loss_set[asset].add_entry(cls._gain_loss2)
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("2"), cls._in2[asset], None))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.79"), cls._out14[asset], cls._in3[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.21"), cls._out14[asset], cls._in2[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("3"), cls._in6[asset], None))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("1.79"), cls._out16[asset], cls._in2[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("3"), cls._out16[asset], cls._in6[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.21"), cls._out16[asset], cls._in5[asset]))
            cls._gain_loss_set[asset].add_entry(
                GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("3.79"), cls._out12[asset], cls._in5[asset])
            )  # ==
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.02"), cls._intra24[asset], cls._in4[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("2.01"), cls._out13[asset], cls._in4[asset]))
            cls._gain_loss_set[asset].add_entry(GainLoss(cls._configuration, cls._accounting_method, RP2Decimal("0.04"), cls._intra22[asset], cls._in4[asset]))

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    # Reproduce programmatically the data from sheets B1 to B4 in input/test_data.ods
    # and check them against golden output
    def test_good_gain_loss_sets(self) -> None:
        for asset in _ASSETS:
            self.assertEqual(str(self._gain_loss_set[asset]), RP2_TEST_OUTPUT[asset])

    def test_bad_gain_loss_set(self) -> None:
        gain_loss_set: GainLossSet
        asset: str = "B4"
        gain_loss1: GainLoss = self._gain_loss1
        gain_loss2: GainLoss = self._gain_loss2
        in3: InTransaction = self._in3[asset]
        in5: InTransaction = self._in5[asset]
        in6: InTransaction = self._in6[asset]
        out15: OutTransaction = self._out15[asset]
        out14: OutTransaction = self._out14[asset]
        out16: OutTransaction = self._out16[asset]

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            GainLossSet(None, self._accounting_method, asset)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            GainLossSet("configuration", self._accounting_method, asset)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'accounting_method' is not of type AbstractAccountingMethod: .*"):
            # Bad configuration
            GainLossSet(self._configuration, None, asset)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'asset' has non-string value .*"):
            # Bad asset
            GainLossSet(self._configuration, self._accounting_method, None)  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'asset' value is not known: .*"):
            # Bad configuration
            GainLossSet(self._configuration, self._accounting_method, "foobar")

        gain_loss_set = GainLossSet(self._configuration, self._accounting_method, asset)

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'entry' is not of type GainLoss: .*"):
            # Bad transaction add
            gain_loss_set.add_entry(None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'entry' is not of type GainLoss: .*"):
            # Bad transaction add
            gain_loss_set.add_entry(1111)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'entry' is not of type GainLoss: .*"):
            # Bad transaction add
            gain_loss_set.add_entry(in3)
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'entry' is not of type GainLoss: .*"):
            # Bad get_parent parameter
            gain_loss_set.get_parent(None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'entry' is not of type GainLoss: .*"):
            # Bad get_parent parameter
            gain_loss_set.get_parent(1111)  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Unknown entry:.*"):
            # Unknown get_parent parameter (set empty)
            gain_loss_set.get_parent(gain_loss1)

        gain_loss_set = GainLossSet(self._configuration, self._accounting_method, asset)
        gain_loss_set.add_entry(gain_loss1)

        with self.assertRaisesRegex(RP2ValueError, "Unknown entry:.*"):
            # Unknown get_parent parameter (set non-empty)
            gain_loss_set.get_parent(gain_loss2)
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'transaction' is not of type AbstractTransaction: .*"):
            # Bad get_taxable_event_fractions parameter
            gain_loss_set.get_taxable_event_number_of_fractions(None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'transaction' is not of type AbstractTransaction: .*"):
            # Bad get_taxable_event_fractions parameter
            gain_loss_set.get_taxable_event_number_of_fractions(self)  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Unknown transaction:.*"):
            # Bad get_taxable_event_fractions parameter
            gain_loss_set.get_taxable_event_number_of_fractions(out15)
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'transaction' is not of type InTransaction: .*"):
            # Bad get_taxable_event_fractions parameter
            gain_loss_set.get_acquired_lot_number_of_fractions(None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'transaction' is not of type InTransaction: .*"):
            # Bad get_taxable_event_fractions parameter
            gain_loss_set.get_acquired_lot_number_of_fractions(self)  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Unknown transaction:.*"):
            # Bad get_taxable_event_fractions parameter
            gain_loss_set.get_acquired_lot_number_of_fractions(in3)
        with self.assertRaisesRegex(
            RP2ValueError, "Timestamp .* of acquired_lot entry .* is incompatible with timestamp .* of its ancestor .* using .* accounting method: .*"
        ):
            gain_loss_set = GainLossSet(self._configuration, self._accounting_method, asset)
            in_transaction_test: InTransaction = InTransaction(
                self._configuration,
                "2020-01-05 11:18:00.000000 +0000",
                asset,
                "Coinbase",
                "Bob",
                "INTEREST",
                RP2Decimal("12000.0"),
                RP2Decimal("2.0"),
                fiat_fee=RP2Decimal("0"),
                internal_id=3,
            )
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.2"), out15, in_transaction_test))
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.01"), out14, in3))
            for _ in gain_loss_set:
                pass
        with self.assertRaisesRegex(
            RP2ValueError, "Timestamp .* of acquired_lot entry .* is incompatible with timestamp .* of its ancestor .* using .* accounting method: .*"
        ):
            gain_loss_set = GainLossSet(self._configuration, self._accounting_method, asset)
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.2"), out15, in_transaction_test))
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("2"), self._in2[asset], None))
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.01"), out14, in3))
            for _ in gain_loss_set:
                pass
        with self.assertRaisesRegex(RP2ValueError, "Entry already added: GainLoss"):
            gain_loss_set = GainLossSet(self._configuration, self._accounting_method, asset)
            gain_loss_set.add_entry(gain_loss1)
            gain_loss_set.add_entry(gain_loss1)
        with self.assertRaisesRegex(RP2ValueError, "Entry already added: GainLoss"):
            gain_loss_set = GainLossSet(self._configuration, self._accounting_method, asset)
            gain_loss_set.add_entry(gain_loss1)
            # Different instance with same contents as gain_loss1
            gain_loss_test: GainLoss = GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.2"), self._out15[asset], self._in3[asset])
            gain_loss_set.add_entry(gain_loss_test)
        with self.assertRaisesRegex(RP2ValueError, "Taxable event crypto amount already exhausted for OutTransaction"):
            gain_loss_set = GainLossSet(self._configuration, self._accounting_method, asset)
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.2"), out15, in3))
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.2"), out15, in_transaction_test))
            for _ in gain_loss_set:
                pass
        with self.assertRaisesRegex(RP2ValueError, "Acquired lot crypto amount already exhausted for InTransaction"):
            gain_loss_set = GainLossSet(self._configuration, self._accounting_method, asset)
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("1"), out14, in3))
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("1"), out16, in3))
            for _ in gain_loss_set:
                pass
        with self.assertRaisesRegex(RP2ValueError, "Current taxable event amount .* exceeded crypto balance change of taxable event .* GainLoss"):
            gain_loss_set = GainLossSet(self._configuration, self._accounting_method, asset)
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("3"), out16, in6))
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("4"), out16, in5))
            for _ in gain_loss_set:
                pass
        with self.assertRaisesRegex(RP2ValueError, "Current acquired lot amount .* exceeded crypto balance change of acquired lot .* GainLoss"):
            gain_loss_set = GainLossSet(self._configuration, self._accounting_method, asset)
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.2"), out15, in3))
            gain_loss_set.add_entry(GainLoss(self._configuration, self._accounting_method, RP2Decimal("1"), out14, in3))
            for _ in gain_loss_set:
                pass


if __name__ == "__main__":
    unittest.main()

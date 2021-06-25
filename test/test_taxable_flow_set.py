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
from typing import List, cast

from rp2_test_output import RP2_TEST_OUTPUT

from configuration import Configuration
from gain_loss import GainLoss
from gain_loss_set import GainLossSet
from in_transaction import InTransaction
from intra_transaction import IntraTransaction
from out_transaction import OutTransaction
from rp2_error import RP2TypeError, RP2ValueError


class TestGainLossSet(unittest.TestCase):
    _configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        TestGainLossSet._configuration = Configuration("./config/test_data.config")

    def setUp(self) -> None:
        self.maxDiff = None

    # Reproduce programmatically the data from sheets B1 to B4 in input/test_data.ods
    def _create_transactions(self, asset: str) -> List[GainLoss]:
        in3: InTransaction = InTransaction(
            self._configuration,
            3,
            "2020-01-01 08:41:00.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "BUY",
            11000,
            1,
            100.00,
        )
        in2: InTransaction = InTransaction(
            self._configuration,
            2,
            "2020-02-01 11:18:00.000000 +0000",
            asset,
            "BlockFi",
            "Bob",
            "EARN",
            12000.0,
            2.0,
            0,
        )
        in6: InTransaction = InTransaction(
            self._configuration,
            6,
            "2020-03-01 09:45:00.000000 +0000",
            asset,
            "BlockFi",
            "Bob",
            "EARN",
            13000.0,
            3,
            0,
        )
        in5: InTransaction = InTransaction(
            self._configuration,
            5,
            "2020-04-01T09:45Z",
            asset,
            "Coinbase",
            "Bob",
            "BUY",
            14000.0,
            4.0,
            400,
        )
        in4: InTransaction = InTransaction(
            self._configuration,
            4,
            "2020-05-01T14:03Z",
            asset,
            "Coinbase",
            "Bob",
            "BUY",
            15000.0,
            5.0,
            500,
        )
        out15: OutTransaction = OutTransaction(
            self._configuration,
            15,
            "2020-01-11 11:15:00.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "SELL",
            11200.0,
            0.2,
            0,
        )
        out14: OutTransaction = OutTransaction(
            self._configuration,
            14,
            "2020-02-11 19:58:00.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "SELL",
            12200.0,
            1.0,
            0,
        )
        out16: OutTransaction = OutTransaction(
            self._configuration,
            16,
            "2020-04-11 07:10:00.000000 +0000",
            asset,
            "BlockFi",
            "Bob",
            "GIFT",
            14200.00,
            5.0,
            0,
        )
        out12: OutTransaction = OutTransaction(
            self._configuration,
            12,
            "2020-04-12 17:50:00.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "DONATE",
            14300,
            3.79,
            0,
        )
        out13: OutTransaction = OutTransaction(
            self._configuration,
            13,
            "2021-06-11 05:31:00.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "SELL",
            20200.00,
            2,
            0.01,
        )
        intra25: IntraTransaction = IntraTransaction(
            self._configuration,
            25,
            "2020-01-21 18:33:14.342000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "BlockFi",
            "Bob",
            11400.0,
            0.1,
            0.09,
        )
        intra24: IntraTransaction = IntraTransaction(
            self._configuration,
            24,
            "2020-05-21 12:58:10.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "Kraken",
            "Alice",
            14400.0,
            0.2,
            0.18,
        )
        intra22: IntraTransaction = IntraTransaction(
            self._configuration,
            22,
            "2021-07-21 10:02:02.000000 +0000",
            asset,
            "Coinbase",
            "Bob",
            "Kraken",
            "Alice",
            21400.0,
            0.5,
            0.46,
        )
        result: List[GainLoss]
        if asset == "B1":
            # In transactions only
            result = [
                GainLoss(self._configuration, 2, in2, None),
                GainLoss(self._configuration, 3, in6, None),
            ]
        elif asset == "B2":
            # In and out transactions only
            result = [
                GainLoss(self._configuration, 0.2, out15, in3),
                GainLoss(self._configuration, 2, in2, None),
                GainLoss(self._configuration, 0.8, out14, in3),
                GainLoss(self._configuration, 0.20, out14, in2),
                GainLoss(self._configuration, 3, in6, None),
                GainLoss(self._configuration, 1.8, out16, in2),
                GainLoss(self._configuration, 3, out16, in6),
                GainLoss(self._configuration, 0.2, out16, in5),
                GainLoss(self._configuration, 3.79, out12, in5),  # ==
                GainLoss(self._configuration, 0.01, out13, in5),
                GainLoss(self._configuration, 2.0, out13, in4),
            ]
        elif asset == "B3":
            # In and intra transactions only
            result = [
                GainLoss(self._configuration, 0.01, intra25, in3),
                GainLoss(self._configuration, 2, in2, None),
                GainLoss(self._configuration, 3, in6, None),
                GainLoss(self._configuration, 0.02, intra24, in3),
                GainLoss(self._configuration, 0.04, intra22, in3),
            ]
        else:  # asset == "B4", "BTC" or others
            result = [
                # All transactions
                GainLoss(self._configuration, 0.2, out15, in3),
                GainLoss(self._configuration, 0.01, intra25, in3),
                GainLoss(self._configuration, 2, in2, None),
                GainLoss(self._configuration, 0.79, out14, in3),
                GainLoss(self._configuration, 0.21, out14, in2),
                GainLoss(self._configuration, 3, in6, None),
                GainLoss(self._configuration, 1.79, out16, in2),
                GainLoss(self._configuration, 3, out16, in6),
                GainLoss(self._configuration, 0.21, out16, in5),
                GainLoss(self._configuration, 3.79, out12, in5),  # ==
                GainLoss(self._configuration, 0.02, intra24, in4),
                GainLoss(self._configuration, 2.01, out13, in4),
                GainLoss(self._configuration, 0.04, intra22, in4),
            ]

        return result

    def _test_good_transaction_set(self, asset: str) -> None:
        gain_loss_set: GainLossSet = GainLossSet(self._configuration, asset)
        for gain_loss in self._create_transactions(asset):
            gain_loss_set.add_entry(gain_loss)
        self.assertEqual(str(gain_loss_set), RP2_TEST_OUTPUT[asset])

    # Reproduce programmatically the data from sheets B1 to B4 in input/test_data.ods
    # and check them against golden output
    def test_good_gain_loss_sets(self) -> None:
        for asset in ["B1", "B2", "B3", "B4"]:
            self._test_good_transaction_set(asset)

    def test_bad_gain_loss_set(self) -> None:
        gain_loss_set: GainLossSet
        asset: str = "B4"
        gain_losss: List[GainLoss] = self._create_transactions(asset)
        gain_loss1: GainLoss = gain_losss[0]
        gain_loss2: GainLoss = gain_losss[1]
        in3: InTransaction = gain_loss1.from_lot  # type: ignore
        out15: OutTransaction = cast(OutTransaction, gain_loss1.taxable_event)
        out14: OutTransaction = cast(OutTransaction, gain_losss[3].taxable_event)

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            GainLossSet(None, asset)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            GainLossSet("configuration", asset)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'asset' has non-string value .*"):
            # Bad asset
            GainLossSet(self._configuration, None)  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'asset' value is not known: .*"):
            # Bad configuration
            GainLossSet(self._configuration, "foobar")

        gain_loss_set = GainLossSet(self._configuration, asset)

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

        gain_loss_set = GainLossSet(self._configuration, asset)
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
            gain_loss_set.get_from_lot_number_of_fractions(None)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'transaction' is not of type InTransaction: .*"):
            # Bad get_taxable_event_fractions parameter
            gain_loss_set.get_from_lot_number_of_fractions(self)  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "Unknown transaction:.*"):
            # Bad get_taxable_event_fractions parameter
            gain_loss_set.get_from_lot_number_of_fractions(in3)
        with self.assertRaisesRegex(RP2ValueError, "Date of from_lot entry at line .* is < the date of its parent at line .*"):
            gain_loss_set = GainLossSet(self._configuration, asset)
            in_transaction: InTransaction = InTransaction(
                self._configuration,
                2,
                "2020-01-05 11:18:00.000000 +0000",
                asset,
                "Coinbase",
                "Bob",
                "EARN",
                12000.0,
                2.0,
                0,
            )
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.2, out15, in_transaction))
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.01, out14, in3))
            for gain_loss in gain_loss_set:
                pass
        with self.assertRaisesRegex(RP2ValueError, "Entry already added: GainLoss"):
            gain_loss_set = GainLossSet(self._configuration, asset)
            gain_loss_set.add_entry(gain_loss1)
            gain_loss_set.add_entry(gain_loss1)
        with self.assertRaisesRegex(RP2ValueError, "Taxable event crypto amount already exhausted for OutTransaction"):
            gain_loss_set = GainLossSet(self._configuration, asset)
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.2, out15, in3))
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.2, out15, in3))
            for gain_loss in gain_loss_set:
                pass
        with self.assertRaisesRegex(RP2ValueError, "From-lot crypto amount already exhausted for InTransaction"):
            gain_loss_set = GainLossSet(self._configuration, asset)
            in_transaction = InTransaction(
                self._configuration,
                10,
                "2020-01-01 08:41:00.000000 +0000",
                asset,
                "Coinbase",
                "Bob",
                "BUY",
                11000,
                0.1,
                100.00,
            )
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.1, out15, in_transaction))
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.1, out15, in_transaction))
            for gain_loss in gain_loss_set:
                pass
        with self.assertRaisesRegex(RP2ValueError, "Current taxable event amount .* exceeds crypto balance change of taxable event .* GainLoss"):
            gain_loss_set = GainLossSet(self._configuration, asset)
            in_transaction = InTransaction(
                self._configuration,
                10,
                "2020-01-02T08:42:43.882Z",
                asset,
                "Coinbase Pro",
                "Bob",
                "BuY",
                10000,
                2.0002,
                20,
                20002,
                20022,
            )
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.1, out15, in_transaction))
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.05, out15, in_transaction))
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.1, out15, in_transaction))
            for gain_loss in gain_loss_set:
                pass
        with self.assertRaisesRegex(RP2ValueError, "Current from-lot amount exceeded crypto balance change of from-lot .* by .* GainLoss"):
            gain_loss_set = GainLossSet(self._configuration, asset)
            out_transaction: OutTransaction = OutTransaction(
                self._configuration,
                15,
                "2020-01-11 11:15:00.000000 +0000",
                asset,
                "Coinbase",
                "Bob",
                "GIFT",
                11200.0,
                2,
                0,
            )
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.5, out_transaction, in3))
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.25, out_transaction, in3))
            gain_loss_set.add_entry(GainLoss(self._configuration, 0.5, out_transaction, in3))
            for gain_loss in gain_loss_set:
                pass


if __name__ == "__main__":
    unittest.main()

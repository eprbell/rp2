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

from configuration import Configuration
from gain_loss import GainLoss
from in_transaction import InTransaction
from intra_transaction import IntraTransaction
from out_transaction import OutTransaction
from rp2_error import RP2TypeError, RP2ValueError


class TestGainLoss(unittest.TestCase):
    _configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        TestGainLoss._configuration = Configuration("./config/test_data.config")

    def setUp(self) -> None:
        self.maxDiff = None

        self._in_buy = InTransaction(
            self._configuration,
            10,
            "2020-01-02T08:42:43.882Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BuY",
            10000,
            2.0002,
            20,
            20002,
            20022,
        )
        self._in_buy2 = InTransaction(
            self._configuration,
            11,
            "2020-01-12T17:33:18Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BuY",
            10500,
            0.8,
            10,
        )
        self._in_buy3 = InTransaction(
            self._configuration,
            11,
            "2020-04-27T03:28:47Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BuY",
            1300,
            1.5,
            20,
        )
        self._in_earn = InTransaction(
            self._configuration,
            14,
            "2020-02-21T13:14:08 -00:04",
            "B1",
            "BlockFi",
            "Bob",
            "eaRn",
            11000,
            0.1,
            0,
        )
        self._out: OutTransaction = OutTransaction(
            self._configuration,
            20,
            "3/3/2020 3:59:59 -04:00",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            12000,
            0.2,
            0,
        )
        self._intra: IntraTransaction = IntraTransaction(
            self._configuration,
            30,
            "2021-03-10T11:18:58 -00:04",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BlockFi",
            "Alice",
            12500.0,
            0.4,
            0.39,
        )

    def test_good_earn_gain_loss(self) -> None:
        flow: GainLoss = GainLoss(self._configuration, 0.1, self._in_earn, None)
        self.assertEqual(flow.crypto_amount, 0.1)
        self.assertEqual(flow.taxable_event, self._in_earn)
        self.assertEqual(flow.from_lot, None)
        self.assertEqual(flow.timestamp, flow.taxable_event.timestamp)
        self.assertEqual(flow.crypto_balance_change, 0.1)
        self.assertEqual(flow.taxable_event_usd_amount_with_fee_fraction, 1100)
        self.assertEqual(
            str(flow),
            """GainLoss:
  id='14->None'
  crypto_amount=0.10000000
  usd_cost_basis=0.0000
  usd_gain=1100.0000
  is_long_term_capital_gains=False
  taxable_event_usd_amount_with_fee_fraction=1100.0000
  taxable_event_fraction_percentage=100.0000%
  taxable_event=InTransaction:
    line=14
    timestamp=2020-02-21 13:14:08.000000 -0004
    asset=B1
    exchange=BlockFi
    holder=Bob
    transaction_type=TransactionType.EARN
    spot_price=11000.0000
    crypto_in=0.10000000
    usd_fee=0.0000
    usd_in_no_fee=1100.0000
    usd_in_with_fee=1100.0000
    is_taxable=True
    usd_taxable_amount=1100.0000
  from_lot_usd_amount_with_fee_fraction=0.0000
  from_lot_fraction_percentage=0.0000%
  from_lot=None""",
        )
        self.assertEqual(
            repr(flow),
            "GainLoss(id='14->None', crypto_amount=0.10000000, usd_cost_basis=0.0000, usd_gain=1100.0000, is_long_term_capital_gains=False, taxable_event_usd_amount_with_fee_fraction=1100.0000, taxable_event_fraction_percentage=100.0000%, taxable_event=InTransaction(line=14, timestamp='2020-02-21 13:14:08.000000 -0004', asset='B1', exchange='BlockFi', holder='Bob', transaction_type=<TransactionType.EARN: 'earn'>, spot_price=11000.0000, crypto_in=0.10000000, usd_fee=0.0000, usd_in_no_fee=1100.0000, usd_in_with_fee=1100.0000, is_taxable=True, usd_taxable_amount=1100.0000), from_lot_usd_amount_with_fee_fraction=0.0000, from_lot_fraction_percentage=0.0000%, from_lot=None)",
        )

    def test_good_non_earn_gain_loss(self) -> None:
        flow: GainLoss = GainLoss(self._configuration, 0.001, self._intra, self._in_buy)
        self.assertEqual(flow.crypto_amount, 0.001)
        self.assertEqual(flow.taxable_event, self._intra)
        self.assertEqual(flow.from_lot, self._in_buy)
        self.assertEqual(flow.timestamp, flow.taxable_event.timestamp)
        self.assertEqual(flow.crypto_balance_change, 0.001)
        self.assertEqual(flow.taxable_event_usd_amount_with_fee_fraction, 12.5)
        self.assertEqual(
            str(flow),
            """GainLoss:
  id='30->10'
  crypto_amount=0.00100000
  usd_cost_basis=10.0100
  usd_gain=2.4900
  is_long_term_capital_gains=True
  taxable_event_usd_amount_with_fee_fraction=12.5000
  taxable_event_fraction_percentage=10.0000%
  taxable_event=IntraTransaction:
    line=30
    timestamp=2021-03-10 11:18:58.000000 -0004
    asset=B1
    from_exchange=Coinbase Pro
    from_holder=Bob
    to_exchange=BlockFi
    to_holder=Alice
    transaction_type=TransactionType.MOVE
    spot_price=12500.0000
    crypto_sent=0.40000000
    crypto_received=0.39000000
    crypto_fee=0.01000000
    usd_fee=125.0000
    is_taxable=True
    usd_taxable_amount=125.0000
  from_lot_usd_amount_with_fee_fraction=10.0100
  from_lot_fraction_percentage=0.0500%
  from_lot=InTransaction:
    line=10
    timestamp=2020-01-02 08:42:43.882000 +0000
    asset=B1
    exchange=Coinbase Pro
    holder=Bob
    transaction_type=TransactionType.BUY
    spot_price=10000.0000
    crypto_in=2.00020000
    usd_fee=20.0000
    usd_in_no_fee=20002.0000
    usd_in_with_fee=20022.0000
    is_taxable=False
    usd_taxable_amount=0.0000""",
        )
        self.assertEqual(
            repr(flow),
            "GainLoss(id='30->10', crypto_amount=0.00100000, usd_cost_basis=10.0100, usd_gain=2.4900, is_long_term_capital_gains=True, taxable_event_usd_amount_with_fee_fraction=12.5000, taxable_event_fraction_percentage=10.0000%, taxable_event=IntraTransaction(line=30, timestamp='2021-03-10 11:18:58.000000 -0004', asset='B1', from_exchange='Coinbase Pro', from_holder='Bob', to_exchange='BlockFi', to_holder='Alice', transaction_type=<TransactionType.MOVE: 'move'>, spot_price=12500.0000, crypto_sent=0.40000000, crypto_received=0.39000000, crypto_fee=0.01000000, usd_fee=125.0000, is_taxable=True, usd_taxable_amount=125.0000), from_lot_usd_amount_with_fee_fraction=10.0100, from_lot_fraction_percentage=0.0500%, from_lot=InTransaction(line=10, timestamp='2020-01-02 08:42:43.882000 +0000', asset='B1', exchange='Coinbase Pro', holder='Bob', transaction_type=<TransactionType.BUY: 'buy'>, spot_price=10000.0000, crypto_in=2.00020000, usd_fee=20.0000, usd_in_no_fee=20002.0000, usd_in_with_fee=20022.0000, is_taxable=False, usd_taxable_amount=0.0000))",
        )

    def test_bad_gain_loss(self) -> None:
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            GainLoss(None, 0.5, self._in_earn, None)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            GainLoss("config", 0.5, self._in_earn, None)  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_amount' has non-positive value .*"):
            # Bad amount
            GainLoss(self._configuration, -1, self._out, None)

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'crypto_amount' has non-numeric value"):
            # Bad amount
            GainLoss(self._configuration, "0.5", self._in_earn, None)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'taxable_event' is not of type AbstractTransaction: .*"):
            # Bad taxable event
            GainLoss(self._configuration, 0.5, None, self._in_buy)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'taxable_event' is not of type AbstractTransaction: .*"):
            # Bad taxable event
            GainLoss(self._configuration, 0.5, "foobar", self._in_buy)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'from_lot' is not of type InTransaction: "):
            # Bad from lot
            GainLoss(self._configuration, 0.1, self._out, 33)  # type: ignore

        with self.assertRaisesRegex(
            RP2TypeError,
            "from_lot must be None for EARN-typed taxable_events, instead it's foobar",
        ):
            # Bad from lot
            GainLoss(self._configuration, 0.1, self._in_earn, "foobar")  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'taxable_event' of class InTransaction is not taxable: .*"):
            # Taxable event not taxable
            GainLoss(self._configuration, 0.2, self._in_buy2, self._in_buy)

        with self.assertRaisesRegex(
            RP2ValueError,
            "crypto_amount must be == taxable_event.crypto_balance_change for EARN-typed taxable events, but they differ .* != .*",
        ):
            # Taxable event of type EARN: from_lot not None
            GainLoss(self._configuration, 1.1, self._in_earn, None)

        with self.assertRaisesRegex(
            RP2TypeError,
            "from_lot must be None for EARN-typed taxable_events, instead it's .*",
        ):
            # Taxable event of type EARN: from_lot not None
            GainLoss(self._configuration, 0.1, self._in_earn, self._in_buy2)

        with self.assertRaisesRegex(RP2TypeError, "from_lot must not be None for non-EARN-typed taxable_events"):
            # Taxable event not of type EARN: from lot None
            GainLoss(self._configuration, 0.2, self._out, None)

        with self.assertRaisesRegex(
            RP2ValueError,
            "crypto_amount .* is greater than taxable event amount .* or from-lot amount .*: ",
        ):
            # Taxable event of type EARN: from_lot not None
            GainLoss(self._configuration, 2, self._out, self._in_buy2)

        with self.assertRaisesRegex(RP2ValueError, "Timestamp of taxable_event <= timestamp of from_lot"):
            # Taxable event of type EARN: from_lot not None
            GainLoss(self._configuration, 0.1, self._out, self._in_buy3)

        with self.assertRaisesRegex(RP2ValueError, "taxable_event.asset .* != from_lot.asset .*"):
            # Mix different assets (B1 and B2) in the same GainLoss
            in_transaction: InTransaction = InTransaction(
                self._configuration,
                11,
                "2019-04-27T03:28:47Z",
                "B2",
                "Coinbase Pro",
                "Bob",
                "BuY",
                1300,
                1.5,
                20,
            )
            GainLoss(self._configuration, 0.1, self._out, in_transaction)


if __name__ == "__main__":
    unittest.main()

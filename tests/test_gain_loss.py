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

from rp2.configuration import Configuration
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.plugin.accounting_method.fifo import AccountingMethod
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError


class TestGainLoss(unittest.TestCase):
    # pylint: disable=line-too-long
    _configuration: Configuration
    _accounting_method: AccountingMethod

    @classmethod
    def setUpClass(cls) -> None:
        cls._configuration = Configuration("./config/test_data.config", US())
        cls._accounting_method = AccountingMethod()

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

        self._in_buy = InTransaction(
            self._configuration,
            "2020-01-02T08:42:43.882Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BuY",
            RP2Decimal("10000"),
            RP2Decimal("2.0002"),
            fiat_fee=RP2Decimal("20"),
            fiat_in_no_fee=RP2Decimal("20002"),
            fiat_in_with_fee=RP2Decimal("20022"),
            internal_id=10,
        )
        self._in_buy2 = InTransaction(
            self._configuration,
            "2020-01-12T17:33:18Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BuY",
            RP2Decimal("10500"),
            RP2Decimal("0.8"),
            fiat_fee=RP2Decimal("10"),
            internal_id=11,
        )
        self._in_buy3 = InTransaction(
            self._configuration,
            "2020-04-27T03:28:47Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BuY",
            RP2Decimal("1300"),
            RP2Decimal("1.5"),
            fiat_fee=RP2Decimal("20"),
            internal_id=12,
        )
        self._in_interest = InTransaction(
            self._configuration,
            "2020-02-21T13:14:08 -00:04",
            "B1",
            "BlockFi",
            "Bob",
            "interest",
            RP2Decimal("11000"),
            RP2Decimal("0.1"),
            fiat_fee=RP2Decimal("0"),
            internal_id=14,
        )
        self._out: OutTransaction = OutTransaction(
            self._configuration,
            "3/3/2020 3:59:59 -04:00",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("12000"),
            RP2Decimal("0.2"),
            RP2Decimal("0"),
            internal_id=20,
        )
        self._intra: IntraTransaction = IntraTransaction(
            self._configuration,
            "2021-03-10T11:18:58 -00:04",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BlockFi",
            "Alice",
            RP2Decimal("12500.0"),
            RP2Decimal("0.4"),
            RP2Decimal("0.39"),
            internal_id=30,
        )

    def test_good_interest_gain_loss(self) -> None:
        flow: GainLoss = GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.1"), self._in_interest, None)
        self.assertEqual(flow.crypto_amount, RP2Decimal("0.1"))
        self.assertEqual(flow.taxable_event, self._in_interest)
        self.assertEqual(flow.acquired_lot, None)
        self.assertEqual(flow.timestamp, flow.taxable_event.timestamp)
        self.assertEqual(flow.crypto_balance_change, RP2Decimal("0.1"))
        self.assertEqual(flow.taxable_event_fiat_amount_with_fee_fraction, RP2Decimal("1100"))
        self.assertEqual(
            str(flow),
            """GainLoss:
  id=14->None
  crypto_amount=0.10000000
  fiat_cost_basis=0.0000
  fiat_gain=1100.0000
  is_long_term_capital_gains=False
  taxable_event_fiat_amount_with_fee_fraction=1100.0000
  taxable_event_fraction_percentage=100.0000%
  taxable_event=InTransaction:
    id=14
    timestamp=2020-02-21 13:14:08.000000 -0004
    asset=B1
    exchange=BlockFi
    holder=Bob
    transaction_type=TransactionType.INTEREST
    spot_price=11000.0000
    crypto_in=0.10000000
    fiat_fee=0.0000
    fiat_in_no_fee=1100.0000
    fiat_in_with_fee=1100.0000
    unique_id=
    is_taxable=True
    fiat_taxable_amount=1100.0000
  acquired_lot_fiat_amount_with_fee_fraction=0.0000
  acquired_lot_fraction_percentage=0.0000%
  acquired_lot=None""",
        )
        self.assertEqual(
            repr(flow),
            "GainLoss(id='14->None', crypto_amount=0.10000000, fiat_cost_basis=0.0000, fiat_gain=1100.0000, is_long_term_capital_gains=False, taxable_event_fiat_amount_with_fee_fraction=1100.0000, taxable_event_fraction_percentage=100.0000%, taxable_event=InTransaction(id='14', timestamp='2020-02-21 13:14:08.000000 -0004', asset='B1', exchange='BlockFi', holder='Bob', transaction_type=<TransactionType.INTEREST: 'interest'>, spot_price=11000.0000, crypto_in=0.10000000, fiat_fee=0.0000, fiat_in_no_fee=1100.0000, fiat_in_with_fee=1100.0000, unique_id=, is_taxable=True, fiat_taxable_amount=1100.0000), acquired_lot_fiat_amount_with_fee_fraction=0.0000, acquired_lot_fraction_percentage=0.0000%, acquired_lot=None)",
        )

    def test_good_non_interest_gain_loss(self) -> None:
        flow: GainLoss = GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.001"), self._intra, self._in_buy)
        self.assertEqual(flow.crypto_amount, RP2Decimal("0.001"))
        self.assertEqual(flow.taxable_event, self._intra)
        self.assertEqual(flow.acquired_lot, self._in_buy)
        self.assertEqual(flow.timestamp, flow.taxable_event.timestamp)
        self.assertEqual(flow.crypto_balance_change, RP2Decimal("0.001"))
        self.assertEqual(flow.taxable_event_fiat_amount_with_fee_fraction, RP2Decimal("12.5"))
        self.assertEqual(
            str(flow),
            """GainLoss:
  id=30->10
  crypto_amount=0.00100000
  fiat_cost_basis=10.0100
  fiat_gain=2.4900
  is_long_term_capital_gains=True
  taxable_event_fiat_amount_with_fee_fraction=12.5000
  taxable_event_fraction_percentage=10.0000%
  taxable_event=IntraTransaction:
    id=30
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
    fiat_fee=125.0000
    unique_id=
    is_taxable=True
    fiat_taxable_amount=125.0000
  acquired_lot_fiat_amount_with_fee_fraction=10.0100
  acquired_lot_fraction_percentage=0.0500%
  acquired_lot=InTransaction:
    id=10
    timestamp=2020-01-02 08:42:43.882000 +0000
    asset=B1
    exchange=Coinbase Pro
    holder=Bob
    transaction_type=TransactionType.BUY
    spot_price=10000.0000
    crypto_in=2.00020000
    fiat_fee=20.0000
    fiat_in_no_fee=20002.0000
    fiat_in_with_fee=20022.0000
    unique_id=
    is_taxable=False
    fiat_taxable_amount=0.0000""",
        )
        self.assertEqual(
            repr(flow),
            "GainLoss(id='30->10', crypto_amount=0.00100000, fiat_cost_basis=10.0100, fiat_gain=2.4900, is_long_term_capital_gains=True, taxable_event_fiat_amount_with_fee_fraction=12.5000, taxable_event_fraction_percentage=10.0000%, taxable_event=IntraTransaction(id='30', timestamp='2021-03-10 11:18:58.000000 -0004', asset='B1', from_exchange='Coinbase Pro', from_holder='Bob', to_exchange='BlockFi', to_holder='Alice', transaction_type=<TransactionType.MOVE: 'move'>, spot_price=12500.0000, crypto_sent=0.40000000, crypto_received=0.39000000, crypto_fee=0.01000000, fiat_fee=125.0000, unique_id=, is_taxable=True, fiat_taxable_amount=125.0000), acquired_lot_fiat_amount_with_fee_fraction=10.0100, acquired_lot_fraction_percentage=0.0500%, acquired_lot=InTransaction(id='10', timestamp='2020-01-02 08:42:43.882000 +0000', asset='B1', exchange='Coinbase Pro', holder='Bob', transaction_type=<TransactionType.BUY: 'buy'>, spot_price=10000.0000, crypto_in=2.00020000, fiat_fee=20.0000, fiat_in_no_fee=20002.0000, fiat_in_with_fee=20022.0000, unique_id=, is_taxable=False, fiat_taxable_amount=0.0000))",
        )

    def test_gain_loss_equality_and_hashing(self) -> None:
        gain_loss: GainLoss = GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.001"), self._intra, self._in_buy)
        gain_loss2: GainLoss = GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.001"), self._intra, self._in_buy)
        gain_loss3: GainLoss = GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.001"), self._intra, self._in_buy2)
        gain_loss4: GainLoss = GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.001"), self._out, self._in_buy)
        gain_loss5: GainLoss = GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.001"), self._out, self._in_buy2)
        gain_loss6: GainLoss = GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.1"), self._in_interest, None)
        self.assertEqual(gain_loss, gain_loss)
        self.assertEqual(gain_loss, gain_loss2)
        self.assertNotEqual(gain_loss, gain_loss3)
        self.assertNotEqual(gain_loss, gain_loss4)
        self.assertNotEqual(gain_loss, gain_loss5)
        self.assertNotEqual(gain_loss, gain_loss6)
        self.assertEqual(hash(gain_loss), hash(gain_loss))
        self.assertEqual(hash(gain_loss), hash(gain_loss2))
        # These hashes would only be equal in case of hash collision (possible but very unlikey).
        self.assertNotEqual(hash(gain_loss), hash(gain_loss3))
        self.assertNotEqual(hash(gain_loss), hash(gain_loss4))
        self.assertNotEqual(hash(gain_loss), hash(gain_loss5))
        self.assertNotEqual(hash(gain_loss), hash(gain_loss6))

    def test_bad_gain_loss(self) -> None:
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            GainLoss(None, self._accounting_method, RP2Decimal("0.5"), self._in_interest, None)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            GainLoss("config", self._accounting_method, RP2Decimal("0.5"), self._in_interest, None)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'accounting_method' is not of type AbstractAccountingMethod: .*"):
            # Bad configuration
            GainLoss(self._configuration, None, RP2Decimal("0.5"), self._in_interest, None)  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_amount' has non-positive value .*"):
            # Bad amount
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("-1"), self._out, None)

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'crypto_amount' has non-RP2Decimal value"):
            # Bad amount
            GainLoss(self._configuration, self._accounting_method, "0.5", self._in_interest, None)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'taxable_event' is not of type AbstractTransaction: .*"):
            # Bad taxable event
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.5"), None, self._in_buy)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'taxable_event' is not of type AbstractTransaction: .*"):
            # Bad taxable event
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.5"), "foobar", self._in_buy)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'acquired_lot' is not of type InTransaction: "):
            # Bad acquired lot
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.1"), self._out, 33)  # type: ignore

        with self.assertRaisesRegex(
            RP2TypeError,
            "acquired_lot must be None for earn-typed taxable_events, instead it's foobar",
        ):
            # Bad acquired lot
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.1"), self._in_interest, "foobar")  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'taxable_event' of class InTransaction is not taxable: .*"):
            # Taxable event not taxable
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.2"), self._in_buy2, self._in_buy)

        with self.assertRaisesRegex(
            RP2ValueError,
            "crypto_amount must be == taxable_event.crypto_balance_change for earn-typed taxable events, but they differ .* != .*",
        ):
            # Earn-typed taxable event: acquired_lot not None
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("1.1"), self._in_interest, None)

        with self.assertRaisesRegex(
            RP2TypeError,
            "acquired_lot must be None for earn-typed taxable_events, instead it's .*",
        ):
            # Earn-typed taxable event: acquired_lot not None
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.1"), self._in_interest, self._in_buy2)

        with self.assertRaisesRegex(RP2TypeError, "acquired_lot must not be None for non-earn-typed taxable_events"):
            # Non-earn-typed taxable event: acquired lot None
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.2"), self._out, None)

        with self.assertRaisesRegex(
            RP2ValueError,
            "crypto_amount .* is greater than taxable event amount .* or acquired-lot amount .*: ",
        ):
            # Non-earn-typed taxable event: acquired_lot not None
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("2"), self._out, self._in_buy2)

        with self.assertRaisesRegex(RP2ValueError, "Timestamp .* of taxable_event is earlier than timestamp .* of acquired_lot: .*"):
            # Non-earn-typed taxable event: acquired_lot not None
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.1"), self._out, self._in_buy3)

        with self.assertRaisesRegex(RP2ValueError, "taxable_event.asset .* != acquired_lot.asset .*"):
            # Mix different assets (B1 and B2) in the same GainLoss
            in_transaction: InTransaction = InTransaction(
                self._configuration,
                "2019-04-27T03:28:47Z",
                "B2",
                "Coinbase Pro",
                "Bob",
                "BuY",
                RP2Decimal("1300"),
                RP2Decimal("1.5"),
                fiat_fee=RP2Decimal("20"),
                internal_id=11,
            )
            GainLoss(self._configuration, self._accounting_method, RP2Decimal("0.1"), self._out, in_transaction)


if __name__ == "__main__":
    unittest.main()

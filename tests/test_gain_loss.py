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
from typing import List, Tuple

from rp2.configuration import Configuration
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError


class TestGainLoss(unittest.TestCase):
    # pylint: disable=line-too-long
    _configuration: Configuration

    @classmethod
    def setUpClass(cls) -> None:
        cls._configuration = Configuration("./config/test_data.ini", US())

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
            row=10,
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
            row=11,
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
            row=12,
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
            row=14,
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
            row=20,
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
            row=30,
        )

    def test_good_interest_gain_loss(self) -> None:
        """
        Interest/staking/mining income has no acquired lot — it is ordinary income at the
        fair market value when received (dominion and control), not a capital gain.
        acquired_lot=None signals this to GainLoss.

        IRS rules:
          Rev. Rul. 2023-14 (staking rewards are income at FMV when received):
            https://www.irs.gov/pub/irs-drop/rr-23-14.pdf
          IRS Digital Assets FAQ (mining, interest, airdrops — FMV at receipt is income):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions
          IRC §61 (gross income includes all income from whatever source derived)
        """
        flow: GainLoss = GainLoss(self._configuration, RP2Decimal("0.1"), self._in_interest, None)
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
    from_lot=
    to_lots=
    cost_basis_timestamp=2020-02-21 13:14:08.000000 -0004
  acquired_lot_fiat_amount_with_fee_fraction=0.0000
  acquired_lot_fraction_percentage=0.0000%
  acquired_lot=None""",
        )
        self.assertEqual(
            repr(flow),
            "GainLoss(id='14->None', crypto_amount=0.10000000, fiat_cost_basis=0.0000, fiat_gain=1100.0000, is_long_term_capital_gains=False, taxable_event_fiat_amount_with_fee_fraction=1100.0000, taxable_event_fraction_percentage=100.0000%, taxable_event=InTransaction(id='14', timestamp='2020-02-21 13:14:08.000000 -0004', asset='B1', exchange='BlockFi', holder='Bob', transaction_type=<TransactionType.INTEREST: 'interest'>, spot_price=11000.0000, crypto_in=0.10000000, fiat_fee=0.0000, fiat_in_no_fee=1100.0000, fiat_in_with_fee=1100.0000, unique_id=, is_taxable=True, fiat_taxable_amount=1100.0000, from_lot=, to_lots=, cost_basis_timestamp='2020-02-21 13:14:08.000000 -0004'), acquired_lot_fiat_amount_with_fee_fraction=0.0000, acquired_lot_fraction_percentage=0.0000%, acquired_lot=None)",
        )

    def test_good_non_interest_gain_loss(self) -> None:
        """
        Crypto used to pay an IntraTransaction fee is a property disposal — gain or loss
        must be recognised at disposal, using the original cost basis of that lot fraction.

        IRS rules:
          IRS Digital Assets FAQ Q81 (transfer between own wallets is non-taxable
          EXCEPT crypto used to pay the transaction fee, which IS a disposal):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions
          IRS Notice 2014-21 (crypto is property; general property rules apply):
            https://www.irs.gov/pub/irs-drop/n-14-21.pdf
        """
        flow: GainLoss = GainLoss(self._configuration, RP2Decimal("0.001"), self._intra, self._in_buy)
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
    fiat_taxable_amount=0.0000
    from_lot=
    to_lots=
    cost_basis_timestamp=2020-01-02 08:42:43.882000 +0000""",
        )
        self.assertEqual(
            repr(flow),
            "GainLoss(id='30->10', crypto_amount=0.00100000, fiat_cost_basis=10.0100, fiat_gain=2.4900, is_long_term_capital_gains=True, taxable_event_fiat_amount_with_fee_fraction=12.5000, taxable_event_fraction_percentage=10.0000%, taxable_event=IntraTransaction(id='30', timestamp='2021-03-10 11:18:58.000000 -0004', asset='B1', from_exchange='Coinbase Pro', from_holder='Bob', to_exchange='BlockFi', to_holder='Alice', transaction_type=<TransactionType.MOVE: 'move'>, spot_price=12500.0000, crypto_sent=0.40000000, crypto_received=0.39000000, crypto_fee=0.01000000, fiat_fee=125.0000, unique_id=, is_taxable=True, fiat_taxable_amount=125.0000), acquired_lot_fiat_amount_with_fee_fraction=10.0100, acquired_lot_fraction_percentage=0.0500%, acquired_lot=InTransaction(id='10', timestamp='2020-01-02 08:42:43.882000 +0000', asset='B1', exchange='Coinbase Pro', holder='Bob', transaction_type=<TransactionType.BUY: 'buy'>, spot_price=10000.0000, crypto_in=2.00020000, fiat_fee=20.0000, fiat_in_no_fee=20002.0000, fiat_in_with_fee=20022.0000, unique_id=, is_taxable=False, fiat_taxable_amount=0.0000, from_lot=, to_lots=, cost_basis_timestamp='2020-01-02 08:42:43.882000 +0000'))",
        )

    def test_gain_loss_equality_and_hashing(self) -> None:
        gain_loss: GainLoss = GainLoss(self._configuration, RP2Decimal("0.001"), self._intra, self._in_buy)
        gain_loss2: GainLoss = GainLoss(self._configuration, RP2Decimal("0.001"), self._intra, self._in_buy)
        gain_loss3: GainLoss = GainLoss(self._configuration, RP2Decimal("0.001"), self._intra, self._in_buy2)
        gain_loss4: GainLoss = GainLoss(self._configuration, RP2Decimal("0.001"), self._out, self._in_buy)
        gain_loss5: GainLoss = GainLoss(self._configuration, RP2Decimal("0.001"), self._out, self._in_buy2)
        gain_loss6: GainLoss = GainLoss(self._configuration, RP2Decimal("0.1"), self._in_interest, None)
        self.assertEqual(gain_loss, gain_loss)
        self.assertEqual(gain_loss, gain_loss2)
        self.assertNotEqual(gain_loss, gain_loss3)
        self.assertNotEqual(gain_loss, gain_loss4)
        self.assertNotEqual(gain_loss, gain_loss5)
        self.assertNotEqual(gain_loss, gain_loss6)
        self.assertEqual(hash(gain_loss), hash(gain_loss))
        self.assertEqual(hash(gain_loss), hash(gain_loss2))
        # These hashes would only be equal in case of hash collision (possible but very unlikely).
        self.assertNotEqual(hash(gain_loss), hash(gain_loss3))
        self.assertNotEqual(hash(gain_loss), hash(gain_loss4))
        self.assertNotEqual(hash(gain_loss), hash(gain_loss5))
        self.assertNotEqual(hash(gain_loss), hash(gain_loss6))

    def test_ltcg_boundary(self) -> None:
        """
        Capital gains are long-term only when the holding period is MORE THAN one year. The holding period is measured
        in calendar dates (not in days): counting starts the day after acquisition and includes the day of disposal, so
        a sale is long-term only if its date is after the first anniversary of the acquisition date. Across February 29th
        a hold of exactly one year is 366 days and is still short-term.

        IRS rules:
          IRS Digital Assets FAQ Q50 (holding period for LTCG on digital assets):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions
          IRC §1222 (defines "long-term capital gain" as asset held "more than 1 year"):
            https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section1222
          IRS Publication 544, "Holding period" ("start counting on the day following the day you acquired the property.
          The day you disposed of the property is part of your holding period"):
            https://www.irs.gov/publications/p544
        """
        # Exactly 365 days must be short-term (IRS: "more than one year" means strictly > 365 days).
        buy_365 = InTransaction(
            self._configuration,
            "2021-01-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BUY",
            RP2Decimal("10000"),
            RP2Decimal("1.0"),
            row=50,
        )
        sell_at_365 = OutTransaction(
            self._configuration,
            "2022-01-01T00:00:00Z",  # exactly 365 days later (2021 is not a leap year)
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("12000"),
            RP2Decimal("1.0"),
            RP2Decimal("0"),
            row=51,
        )
        sell_at_366 = OutTransaction(
            self._configuration,
            "2022-01-02T00:00:00Z",  # 366 days later
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("12000"),
            RP2Decimal("1.0"),
            RP2Decimal("0"),
            row=52,
        )
        # Leap year boundary: 2020 has 366 days, so Jan 1 → Jan 1 next year is 366 days, but it's exactly one year.
        buy_leap = InTransaction(
            self._configuration,
            "2020-01-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BUY",
            RP2Decimal("10000"),
            RP2Decimal("1.0"),
            row=53,
        )
        sell_leap_year_boundary = OutTransaction(
            self._configuration,
            "2021-01-01T00:00:00Z",  # 366 days later because 2020 is a leap year
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("12000"),
            RP2Decimal("1.0"),
            RP2Decimal("0"),
            row=54,
        )

        gl_365 = GainLoss(self._configuration, RP2Decimal("1.0"), sell_at_365, buy_365)
        gl_366 = GainLoss(self._configuration, RP2Decimal("1.0"), sell_at_366, buy_365)
        gl_leap = GainLoss(self._configuration, RP2Decimal("1.0"), sell_leap_year_boundary, buy_leap)

        self.assertFalse(gl_365.is_long_term_capital_gains(), "365-day holding should be short-term (IRS: more than 1 year required)")
        self.assertTrue(gl_366.is_long_term_capital_gains(), "366-day holding should be long-term")
        self.assertFalse(gl_leap.is_long_term_capital_gains(), "Exactly one year (366 days across February 29th) should be short-term")

        def is_long_term(bought: str, sold: str) -> bool:
            buy = InTransaction(self._configuration, bought, "B1", "Coinbase Pro", "Bob", "BUY", RP2Decimal("10000"), RP2Decimal("1.0"), row=55)
            sell = OutTransaction(
                self._configuration, sold, "B1", "Coinbase Pro", "Bob", "SELL", RP2Decimal("12000"), RP2Decimal("1.0"), RP2Decimal("0"), row=56
            )
            return GainLoss(self._configuration, RP2Decimal("1.0"), sell, buy).is_long_term_capital_gains()

        # Publication 544 example: bought June 17, 2024; sold June 17, 2025 is not longer than 1 year, sold June 19, 2025 is.
        self.assertFalse(is_long_term("2024-06-17T12:00:00Z", "2025-06-17T12:00:00Z"))
        self.assertTrue(is_long_term("2024-06-17T12:00:00Z", "2025-06-18T12:00:00Z"))
        self.assertTrue(is_long_term("2024-06-17T12:00:00Z", "2025-06-19T12:00:00Z"))
        # Across February 29th: 2023-03-01 -> 2024-03-01 is 366 days but exactly one year.
        self.assertFalse(is_long_term("2023-03-01T12:00:00Z", "2024-03-01T12:00:00Z"))
        self.assertTrue(is_long_term("2023-03-01T12:00:00Z", "2024-03-02T12:00:00Z"))
        # Acquired on February 29th: the anniversary is February 28th, so long-term from March 1st.
        self.assertFalse(is_long_term("2024-02-29T12:00:00Z", "2025-02-28T12:00:00Z"))
        self.assertTrue(is_long_term("2024-02-29T12:00:00Z", "2025-03-01T12:00:00Z"))
        # Time of day doesn't matter: the day after the anniversary is long-term even if less than 365 * 24 hours have passed.
        self.assertTrue(is_long_term("2024-03-01T23:00:00Z", "2025-03-02T01:00:00Z"))

    def test_earn_type_income_recognition(self) -> None:
        """
        Every earn-typed in-transaction (HARDFORK, AIRDROP, MINING, STAKING, WAGES, INCOME)
        produces ordinary income at FMV when received — not a capital gain.
        Common characteristics:
          - acquired_lot must be None (no prior cost basis lot to pair against)
          - fiat_cost_basis == 0
          - fiat_gain == spot_price * crypto_in  (FMV at the moment of receipt)
          - is_long_term_capital_gains() == False  (earn income is never LTCG)

        IRS rules by earn type:
          HARDFORK — Rev. Rul. 2019-24 (income recognised at FMV when dominion and control
            obtained over new chain tokens; "dominion and control" timing applies):
            https://www.irs.gov/pub/irs-drop/rr-19-24.pdf
          AIRDROP — Rev. Rul. 2019-24 (same rule applies to airdropped tokens):
            https://www.irs.gov/pub/irs-drop/rr-19-24.pdf
          MINING — IRS Notice 2014-21 Q8 (mined coins are gross income at FMV when received):
            https://www.irs.gov/pub/irs-drop/n-14-21.pdf
          STAKING — Rev. Rul. 2023-14 (staking rewards are income at FMV when received):
            https://www.irs.gov/pub/irs-drop/rr-23-14.pdf
          WAGES — IRS Digital Assets FAQ Q57-Q61 (crypto wages = ordinary income at FMV):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions
          INCOME — IRC §61 (gross income includes income from whatever source derived):
            https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section61
        """
        earn_type_tests: List[Tuple[str, RP2Decimal, RP2Decimal, RP2Decimal]] = [
            ("HARDFORK", RP2Decimal("8000"), RP2Decimal("0.5"), RP2Decimal("4000")),
            ("AIRDROP", RP2Decimal("8000"), RP2Decimal("0.5"), RP2Decimal("4000")),
            ("MINING", RP2Decimal("8000"), RP2Decimal("0.5"), RP2Decimal("4000")),
            ("STAKING", RP2Decimal("8000"), RP2Decimal("0.5"), RP2Decimal("4000")),
            ("WAGES", RP2Decimal("8000"), RP2Decimal("0.5"), RP2Decimal("4000")),
            ("INCOME", RP2Decimal("8000"), RP2Decimal("0.5"), RP2Decimal("4000")),
        ]
        for i, (ttype, spot_price, crypto_in, expected_fiat_gain) in enumerate(earn_type_tests):
            with self.subTest(transaction_type=ttype):
                earn_in: InTransaction = InTransaction(
                    self._configuration,
                    "2021-06-01T00:00:00Z",
                    "B1",
                    "Coinbase Pro",
                    "Bob",
                    ttype,
                    spot_price,
                    crypto_in,
                    fiat_fee=RP2Decimal("0"),
                    row=60 + i,
                )
                gl: GainLoss = GainLoss(self._configuration, crypto_in, earn_in, None)
                self.assertIsNone(gl.acquired_lot)
                self.assertEqual(gl.fiat_cost_basis, RP2Decimal("0"))
                self.assertEqual(gl.fiat_gain, expected_fiat_gain)
                self.assertFalse(gl.is_long_term_capital_gains(), f"{ttype} earn income should never be long-term capital gain")

    def test_donate_gift_disposal_gain_loss(self) -> None:
        """
        DONATE and GIFT out-transactions are disposals of property: gain/loss is computed
        the same way as SELL (proceeds minus cost basis). RP2 surfaces the figures for tax
        professionals; the actual tax treatment differs under US law (see user_faq.md).

        IRS rules:
          DONATE — IRS Digital Assets FAQ Q78 (long-term donations to 501(c)(3) deduct FMV;
            short-term deduct lesser of basis/FMV; underlying gain/loss must still be computed):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions
          GIFT — IRS Digital Assets FAQ Q75-Q77 (gift is not a taxable event for the giver
            w.r.t. capital gains, but carryover basis and holding-period rules mean the
            gain/loss figures produced here are needed for the recipient's future return):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions
          IRS Notice 2014-21 (crypto is property; general property disposal rules apply):
            https://www.irs.gov/pub/irs-drop/n-14-21.pdf
        """
        in_acquisition: InTransaction = InTransaction(
            self._configuration,
            "2020-01-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BUY",
            RP2Decimal("10000"),
            RP2Decimal("1.0"),
            fiat_fee=RP2Decimal("0"),
            row=70,
        )
        # 517 days later → long-term (2020 is a leap year: 366 + 151 days)
        disposal_types: List[Tuple[str, int]] = [("DONATE", 71), ("GIFT", 72)]
        for disposal_type, row in disposal_types:
            with self.subTest(transaction_type=disposal_type):
                out: OutTransaction = OutTransaction(
                    self._configuration,
                    "2021-06-01T00:00:00Z",
                    "B1",
                    "Coinbase Pro",
                    "Bob",
                    disposal_type,
                    RP2Decimal("12000"),
                    RP2Decimal("0.5"),
                    RP2Decimal("0"),
                    row=row,
                )
                # proceeds = 0.5 * 12000 = 6000; cost_basis = (10000 * 0.5) / 1.0 = 5000
                gl: GainLoss = GainLoss(self._configuration, RP2Decimal("0.5"), out, in_acquisition)
                self.assertEqual(gl.taxable_event_fiat_amount_with_fee_fraction, RP2Decimal("6000"))
                self.assertEqual(gl.fiat_cost_basis, RP2Decimal("5000"))
                self.assertEqual(gl.fiat_gain, RP2Decimal("1000"))
                self.assertTrue(gl.is_long_term_capital_gains(), f"{disposal_type} held 517 days should be long-term")

    def test_holding_period_resets_after_exchange(self) -> None:
        """
        When you receive new crypto in a crypto-to-crypto exchange, the holding period for
        the RECEIVED asset starts fresh on the day of receipt — even if the asset you gave
        up was a long-term lot.

        Practical impact: a trader who held ETH for 2 years (long-term), swaps it for BTC,
        and sells the BTC 30 days later has a SHORT-TERM gain on the BTC, not long-term.
        The holding period clock for BTC resets to the exchange date.

        IRS rules:
          IRS Digital Assets FAQ Q74 (holding period for exchanged digital assets begins the
            day after the date of receipt):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions
          IRC §1223(1) (tacking of holding period only applies to carry-over basis situations,
            not arm's-length exchanges):
            https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section1223
        """
        # Simulates receiving new asset B in exchange for asset A on 2021-06-01.
        # The holding period for B starts on 2021-06-01 regardless of how long A was held.
        in_b_received: InTransaction = InTransaction(
            self._configuration,
            "2021-06-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BUY",
            RP2Decimal("50000"),
            RP2Decimal("1.0"),
            row=80,
        )
        # 2021-06-01 → 2022-06-01 = exactly 365 days (no Feb 29 in this span) → short-term
        sell_at_365: OutTransaction = OutTransaction(
            self._configuration,
            "2022-06-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("55000"),
            RP2Decimal("1.0"),
            RP2Decimal("0"),
            row=81,
        )
        # 2021-06-01 → 2022-06-02 = 366 days → long-term
        sell_at_366: OutTransaction = OutTransaction(
            self._configuration,
            "2022-06-02T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("55000"),
            RP2Decimal("1.0"),
            RP2Decimal("0"),
            row=82,
        )
        gl_365: GainLoss = GainLoss(self._configuration, RP2Decimal("1.0"), sell_at_365, in_b_received)
        gl_366: GainLoss = GainLoss(self._configuration, RP2Decimal("1.0"), sell_at_366, in_b_received)

        self.assertFalse(gl_365.is_long_term_capital_gains(), "Exactly 365 days from exchange date must be short-term (IRS Q74)")
        self.assertTrue(gl_366.is_long_term_capital_gains(), "366 days from exchange date must be long-term (IRS Q74)")

    def test_fee_out_transaction_gain_loss(self) -> None:
        """
        A FEE-typed out-transaction represents crypto paid solely as a network/gas fee
        (crypto_out_no_fee must be zero; only crypto_fee is non-zero). The disposal of that
        fee crypto is a taxable event: gain/loss = FMV of fee at disposal minus cost basis
        of the fraction of the acquired lot consumed.

        This is distinct from a MOVE intra-transaction fee (tested elsewhere). Here the fee
        stands alone as the entire transaction — e.g. calling a smart contract that costs
        gas but produces no crypto in or out for the user.

        IRS rules:
          IRS Digital Assets FAQ Q97 (gain/loss recognised on digital assets used to pay
            transaction fees — FMV at disposal minus adjusted basis):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions
          IRS Digital Assets FAQ Q53 (transaction costs such as gas fees form part of the
            cost basis of received assets and reduce amount realised on disposals):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions
          IRS Notice 2014-21 (crypto is property; general property disposal rules apply):
            https://www.irs.gov/pub/irs-drop/n-14-21.pdf
        """
        in_acquisition: InTransaction = InTransaction(
            self._configuration,
            "2020-01-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BUY",
            RP2Decimal("10000"),
            RP2Decimal("1.0"),
            fiat_fee=RP2Decimal("0"),
            row=90,
        )
        # FEE-typed: crypto_out_no_fee=0 (required), crypto_fee=0.01 (the disposed amount)
        fee_out: OutTransaction = OutTransaction(
            self._configuration,
            "2021-06-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "FEE",
            RP2Decimal("15000"),
            RP2Decimal("0"),  # crypto_out_no_fee must be 0 for FEE type
            RP2Decimal("0.01"),  # crypto_fee is what was actually disposed
            row=91,
        )
        # fiat_taxable_amount for FEE = fiat_fee = 0.01 * 15000 = 150
        # fiat_cost_basis = (10000 * 0.01) / 1.0 = 100
        # fiat_gain = 150 - 100 = 50
        gl: GainLoss = GainLoss(self._configuration, RP2Decimal("0.01"), fee_out, in_acquisition)
        self.assertEqual(gl.taxable_event_fiat_amount_with_fee_fraction, RP2Decimal("150"))
        self.assertEqual(gl.fiat_cost_basis, RP2Decimal("100"))
        self.assertEqual(gl.fiat_gain, RP2Decimal("50"))
        self.assertTrue(gl.is_long_term_capital_gains(), "517-day holding (from 2020-01-01 to 2021-06-01) should be long-term")

    def test_purchase_fee_increases_cost_basis(self) -> None:
        """
        The fee paid to acquire digital assets is added to the cost basis.
        When the asset is later sold, the higher basis (purchase price + fee) reduces
        the taxable gain compared to an identical purchase with no fee.

        IRS rules:
          IRS Virtual Currency FAQ Q8 (basis = amount paid including fees and commissions):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-virtual-currency-transactions#q8
          IRS Digital Assets FAQ Q56 (basis = price paid + transaction service costs):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions#q56
        """
        buy_no_fee = InTransaction(
            self._configuration,
            "2020-01-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BUY",
            RP2Decimal("10000"),
            RP2Decimal("1.0"),
            fiat_fee=RP2Decimal("0"),
            fiat_in_no_fee=RP2Decimal("10000"),
            fiat_in_with_fee=RP2Decimal("10000"),
            row=100,
        )
        buy_with_fee = InTransaction(
            self._configuration,
            "2020-01-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BUY",
            RP2Decimal("10000"),
            RP2Decimal("1.0"),
            fiat_fee=RP2Decimal("100"),
            fiat_in_no_fee=RP2Decimal("10000"),
            fiat_in_with_fee=RP2Decimal("10100"),
            row=101,
        )
        sell = OutTransaction(
            self._configuration,
            "2021-06-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("12000"),
            RP2Decimal("1.0"),
            RP2Decimal("0"),
            row=102,
        )
        gl_no_fee = GainLoss(self._configuration, RP2Decimal("1.0"), sell, buy_no_fee)
        gl_with_fee = GainLoss(self._configuration, RP2Decimal("1.0"), sell, buy_with_fee)

        # No fee: proceeds = $12,000; basis = $10,000; gain = $2,000
        self.assertEqual(gl_no_fee.fiat_cost_basis, RP2Decimal("10000"))
        self.assertEqual(gl_no_fee.fiat_gain, RP2Decimal("2000"))

        # With $100 fee: proceeds = $12,000; basis = $10,100; gain = $1,900
        self.assertEqual(gl_with_fee.fiat_cost_basis, RP2Decimal("10100"))
        self.assertEqual(gl_with_fee.fiat_gain, RP2Decimal("1900"))

    def test_earned_crypto_cost_basis_for_subsequent_sale(self) -> None:
        """
        When you earn crypto (staking, mining, wages, etc.), the FMV at the time of
        receipt is both ordinary income AND the cost basis of that crypto going forward.
        A subsequent sale uses that FMV as the adjusted basis — not zero.

        IRS rules:
          IRS Virtual Currency FAQ Q13 (basis of crypto received for services = FMV when received):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-virtual-currency-transactions#q13
          IRS Digital Assets FAQ Q59 (same rule for 2025+ transactions):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions#q59
          Rev. Rul. 2023-14 (staking rewards are income at FMV; that FMV becomes cost basis):
            https://www.irs.gov/pub/irs-drop/rr-23-14.pdf
        """
        # 0.1 BTC received as staking at $11,000/BTC → FMV = $1,100 (income recognised + cost basis established)
        staking_reward = InTransaction(
            self._configuration,
            "2020-06-01T00:00:00Z",
            "B1",
            "BlockFi",
            "Bob",
            "STAKING",
            RP2Decimal("11000"),
            RP2Decimal("0.1"),
            fiat_fee=RP2Decimal("0"),
            row=110,
        )
        # Later sell 0.1 BTC at $15,000/BTC → proceeds = $1,500
        sell = OutTransaction(
            self._configuration,
            "2022-06-15T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("15000"),
            RP2Decimal("0.1"),
            RP2Decimal("0"),
            row=111,
        )
        gl = GainLoss(self._configuration, RP2Decimal("0.1"), sell, staking_reward)

        # Cost basis = FMV at time of staking receipt = 0.1 × $11,000 = $1,100 (not $0)
        # Proceeds = 0.1 × $15,000 = $1,500
        # Gain = $1,500 − $1,100 = $400
        self.assertEqual(gl.fiat_cost_basis, RP2Decimal("1100"))
        self.assertEqual(gl.taxable_event_fiat_amount_with_fee_fraction, RP2Decimal("1500"))
        self.assertEqual(gl.fiat_gain, RP2Decimal("400"))
        self.assertTrue(gl.is_long_term_capital_gains(), "Holding from 2020-06-01 to 2022-06-15 (>730 days) should be long-term")

    def test_crypto_to_crypto_exchange_gain_loss(self) -> None:
        """
        Exchanging one digital asset for another (materially different) asset is a taxable
        disposal of the asset given up. Gain or loss = FMV of the asset disposed at the
        time of exchange minus the adjusted basis of that asset.

        The holding period of the RECEIVED asset resets to the exchange date (see also
        test_holding_period_resets_after_exchange).

        IRS rules:
          IRS Virtual Currency FAQ Q16-Q17 (exchange of crypto for other property = capital gain/loss):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-virtual-currency-transactions#q16
          IRS Digital Assets FAQ Q64-Q66 (amount realized = FMV of asset received):
            https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions#q64
          IRS Notice 2014-21 (crypto is property; general property disposal rules apply):
            https://www.irs.gov/pub/irs-drop/n-14-21.pdf
        """
        # Buy 1.0 B1 (e.g. ETH) at $2,000 → cost basis = $2,000
        buy = InTransaction(
            self._configuration,
            "2020-01-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "BUY",
            RP2Decimal("2000"),
            RP2Decimal("1.0"),
            fiat_fee=RP2Decimal("0"),
            row=120,
        )
        # Exchange 1.0 B1 for another asset when B1 spot = $3,000 — modelled as a SELL of B1
        exchange_out = OutTransaction(
            self._configuration,
            "2022-01-01T00:00:00Z",
            "B1",
            "Coinbase Pro",
            "Bob",
            "SELL",
            RP2Decimal("3000"),
            RP2Decimal("1.0"),
            RP2Decimal("0"),
            row=121,
        )
        gl = GainLoss(self._configuration, RP2Decimal("1.0"), exchange_out, buy)

        # Amount realized = FMV of B1 at exchange = $3,000
        # Adjusted basis = cost of B1 = $2,000
        # Gain = $3,000 − $2,000 = $1,000
        self.assertEqual(gl.taxable_event_fiat_amount_with_fee_fraction, RP2Decimal("3000"))
        self.assertEqual(gl.fiat_cost_basis, RP2Decimal("2000"))
        self.assertEqual(gl.fiat_gain, RP2Decimal("1000"))
        # Jan 1 2020 → Jan 1 2022 = 731 days (2020 is a leap year) → long-term
        self.assertTrue(gl.is_long_term_capital_gains(), "731-day holding should be long-term")

    def test_bad_gain_loss(self) -> None:
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            GainLoss(None, RP2Decimal("0.5"), self._in_interest, None)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'configuration' is not of type Configuration: .*"):
            # Bad configuration
            GainLoss("config", RP2Decimal("0.5"), self._in_interest, None)  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'crypto_amount' has non-positive value .*"):
            # Bad amount
            GainLoss(self._configuration, RP2Decimal("-1"), self._out, None)

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'crypto_amount' has non-RP2Decimal value"):
            # Bad amount
            GainLoss(self._configuration, "0.5", self._in_interest, None)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'taxable_event' is not of type AbstractTransaction: .*"):
            # Bad taxable event
            GainLoss(self._configuration, RP2Decimal("0.5"), None, self._in_buy)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'taxable_event' is not of type AbstractTransaction: .*"):
            # Bad taxable event
            GainLoss(self._configuration, RP2Decimal("0.5"), "foobar", self._in_buy)  # type: ignore

        with self.assertRaisesRegex(RP2TypeError, "Parameter 'acquired_lot' is not of type InTransaction: "):
            # Bad acquired lot
            GainLoss(self._configuration, RP2Decimal("0.1"), self._out, 33)  # type: ignore

        with self.assertRaisesRegex(
            RP2TypeError,
            "acquired_lot must be None for earn-typed taxable_events, instead it's foobar",
        ):
            # Bad acquired lot
            GainLoss(self._configuration, RP2Decimal("0.1"), self._in_interest, "foobar")  # type: ignore

        with self.assertRaisesRegex(RP2ValueError, "Parameter 'taxable_event' of class InTransaction is not taxable: .*"):
            # Taxable event not taxable
            GainLoss(self._configuration, RP2Decimal("0.2"), self._in_buy2, self._in_buy)

        with self.assertRaisesRegex(
            RP2ValueError,
            "crypto_amount must be == taxable_event.crypto_balance_change for earn-typed taxable events, but they differ .* != .*",
        ):
            # Earn-typed taxable event: acquired_lot not None
            GainLoss(self._configuration, RP2Decimal("1.1"), self._in_interest, None)

        with self.assertRaisesRegex(
            RP2TypeError,
            "acquired_lot must be None for earn-typed taxable_events, instead it's .*",
        ):
            # Earn-typed taxable event: acquired_lot not None
            GainLoss(self._configuration, RP2Decimal("0.1"), self._in_interest, self._in_buy2)

        with self.assertRaisesRegex(RP2TypeError, "acquired_lot must not be None for non-earn-typed taxable_events"):
            # Non-earn-typed taxable event: acquired lot None
            GainLoss(self._configuration, RP2Decimal("0.2"), self._out, None)

        with self.assertRaisesRegex(
            RP2ValueError,
            "crypto_amount .* is greater than taxable event amount .* or acquired-lot amount .*: ",
        ):
            # Non-earn-typed taxable event: acquired_lot not None
            GainLoss(self._configuration, RP2Decimal("2"), self._out, self._in_buy2)

        with self.assertRaisesRegex(RP2ValueError, "Timestamp .* of taxable_event is earlier than timestamp .* of acquired_lot: .*"):
            # Non-earn-typed taxable event: acquired_lot not None
            GainLoss(self._configuration, RP2Decimal("0.1"), self._out, self._in_buy3)

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
                row=11,
            )
            GainLoss(self._configuration, RP2Decimal("0.1"), self._out, in_transaction)


if __name__ == "__main__":
    unittest.main()

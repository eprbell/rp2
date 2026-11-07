# Copyright 2026 eprbell
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

# Holding periods (R15 of the review of eprbell/rp2#155): when a gain is long-term. The tests check the rules of the country plugins
# (AbstractCountry.is_long_term_capital_gain() and its overrides) and their results through GainLoss. Converting the timestamps to tax dates
# is a separate step: GainLoss does it before calling the rule (R06, see Configuration.get_tax_timestamp()), and test_tax_dates.py tests it.
# - Every country except the US counts whole days (24-hour periods): a gain is long-term if at least get_long_term_capital_gain_period()
#   days passed, as in RP2 1.7.2. Example with Spain (365 days): bought on 2021-03-01 at noon and sold on 2022-03-01 at noon (365 days) is
#   long-term, and sold at 11:59 AM it's short-term.
# - The US compares calendar dates: long-term means held more than 1 year (IRC §1222), counted from the day after the purchase and
#   including the day of the sale (IRS Publication 544), so a sale is long-term only if its date is after the first anniversary of the
#   purchase date. Example: bought on 2023-03-01, a sale on 2024-03-01 is short-term (although 366 days passed, because of February 29th) and
#   a sale on 2024-03-02 is long-term. RP2 1.7.2 counted 365 days instead: test_us_rule_compared_with_rp2_1_7_2 shows which results change.

import os
import unittest
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, Iterator, List, NamedTuple
from unittest.mock import patch

from per_wallet_common import AbstractPerWalletTest, _create_configuration, _GainLoss, _In, _Intra, _Out, _sorted

from rp2.abstract_country import AbstractCountry
from rp2.computed_data import ComputedData
from rp2.configuration import Configuration
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.out_transaction import OutTransaction
from rp2.plugin.country.es import ES
from rp2.plugin.country.generic import Generic
from rp2.plugin.country.ie import IE
from rp2.plugin.country.jp import JP
from rp2.plugin.country.us import US
from rp2.rp2_decimal import RP2Decimal
from rp2.tax_engine import compute_tax, compute_tax_per_wallet

_CONFIGURATION_PATH = "./config/test_data.ini"
# UTC offsets of the generated timestamps: a day count doesn't depend on them.
_OFFSETS = [timezone.utc, timezone(timedelta(hours=-5)), timezone(timedelta(hours=9))]


# The generic country, with LONG_TERM_CAPITAL_GAINS set to days.
def _generic(days: str) -> Generic:
    environment: Dict[str, str] = {"CURRENCY_CODE": "eur", "LONG_TERM_CAPITAL_GAINS": days}
    with patch.dict(os.environ, environment):
        return Generic()


# RP2 1.7.2's rule (GainLoss.is_long_term_capital_gains()): the whole days between the purchase and the sale are at least the country's period.
def _rp2_1_7_2_is_long_term(country: AbstractCountry, purchase: datetime, sale: datetime) -> bool:
    return (sale - purchase).days >= country.get_long_term_capital_gain_period()


# The first anniversary of a date, computed independently of the US plugin: the same month and day one year later, or February 28th for
# February 29th (the next year has no February 29th).
def _anniversary(day: date) -> date:
    if day.month == 2 and day.day == 29:
        return date(day.year + 1, 2, 28)
    return date(day.year + 1, day.month, day.day)


# A purchase, a sale and whether the sale is long-term.
class _Case(NamedTuple):
    description: str
    purchase: str
    sale: str
    is_long_term: bool


class TestHoldingPeriod(AbstractPerWalletTest):
    def _assert_cases(self, country: AbstractCountry, cases: List[_Case]) -> None:
        for case in cases:
            with self.subTest(country=f"{country.country_iso_code} ({country.get_long_term_capital_gain_period()} days)", name=case.description):
                got = country.is_long_term_capital_gain(datetime.fromisoformat(case.purchase), datetime.fromisoformat(case.sale))
                self.assertEqual(got, case.is_long_term)

    @staticmethod
    def _gain_loss(configuration: Configuration, purchase: datetime, sale: datetime) -> GainLoss:
        lot = InTransaction(configuration, purchase.isoformat(), "B1", "Coinbase", "Bob", "BUY", RP2Decimal("100"), RP2Decimal("1"), row=1)
        disposal = OutTransaction(configuration, sale.isoformat(), "B1", "Coinbase", "Bob", "SELL", RP2Decimal("200"), RP2Decimal("1"), RP2Decimal("0"), row=2)
        return GainLoss(configuration, RP2Decimal("1"), disposal, lot)

    # Purchases around the end of the year, the end of February and February 29th, at different times of the day and UTC offsets.
    @staticmethod
    def _purchases() -> Iterator[datetime]:
        for day in ["2019-12-31", "2020-02-28", "2020-02-29", "2020-03-01", "2021-02-28", "2021-03-01", "2023-02-28", "2023-03-01", "2024-02-29"]:
            for time_of_day in ["00:00:00", "12:00:00", "23:59:59"]:
                for offset in _OFFSETS:
                    yield datetime.fromisoformat(f"{day}T{time_of_day}").replace(tzinfo=offset)

    # Sales from 2 days before to 2 days after the end of the period, exactly at it or 1 second or 1 hour away, in every UTC offset.
    @staticmethod
    def _sales(purchase: datetime, days: int) -> Iterator[datetime]:
        for day in range(days - 2, days + 3):
            for delta in [timedelta(0), timedelta(seconds=-1), timedelta(seconds=1), timedelta(hours=-1), timedelta(hours=1)]:
                for offset in _OFFSETS:
                    yield (purchase + timedelta(days=day) + delta).astimezone(offset)

    # The exact threshold of the day count: exactly the period is long-term, anything less is short-term. 365 days for Spain and for the
    # generic country with LONG_TERM_CAPITAL_GAINS=365.
    def test_day_count_threshold(self) -> None:
        cases: List[_Case] = [
            _Case("365 days: long-term", "2021-03-01T12:00:00+00:00", "2022-03-01T12:00:00+00:00", True),
            _Case("1 second less: short-term", "2021-03-01T12:00:00+00:00", "2022-03-01T11:59:59+00:00", False),
            _Case("364 days: short-term", "2021-03-01T12:00:00+00:00", "2022-02-28T12:00:00+00:00", False),
            # Days are 24-hour periods, and February 29th is a day like the others.
            _Case("365 days across February 29th, a day before the anniversary: long-term", "2023-03-01T12:00:00+00:00", "2024-02-29T12:00:00+00:00", True),
            # 2021-03-01T23:00:00-05:00 is 2021-03-02T04:00:00+00:00, and 2022-03-02T13:00:00+09:00 is 2022-03-02T04:00:00+00:00.
            _Case("365 days in different UTC offsets: long-term", "2021-03-01T23:00:00-05:00", "2022-03-02T13:00:00+09:00", True),
        ]
        countries_with_365_days: List[AbstractCountry] = [ES(), _generic("365")]
        for country in countries_with_365_days:
            self._assert_cases(country, cases)
        # Another period: 30 days.
        self._assert_cases(
            _generic("30"),
            [
                _Case("30 days: long-term", "2021-03-01T12:00:00+00:00", "2021-03-31T12:00:00+00:00", True),
                _Case("1 second less: short-term", "2021-03-01T12:00:00+00:00", "2021-03-31T11:59:59+00:00", False),
            ],
        )
        # With 0 days every sale is long-term, also at the instant of the purchase.
        self._assert_cases(_generic("0"), [_Case("the same instant: long-term", "2021-03-01T12:00:00+00:00", "2021-03-01T12:00:00+00:00", True)])
        # Japan and Ireland have no long-term capital gains: their period is sys.maxsize days.
        never: List[_Case] = [_Case("10 years: short-term", "2021-03-01T12:00:00+00:00", "2031-03-01T12:00:00+00:00", False)]
        countries_without_long_term: List[AbstractCountry] = [JP(), IE()]
        for country in countries_without_long_term:
            self._assert_cases(country, never)

    # Through GainLoss, the day count gives the results of RP2 1.7.2, for purchases around the end of the year and of February and sales
    # around the end of the period, at different times and in different UTC offsets.
    def test_day_count_matches_rp2_1_7_2(self) -> None:
        for country in (ES(), _generic("365"), _generic("30")):
            configuration = Configuration(_CONFIGURATION_PATH, country)
            days = country.get_long_term_capital_gain_period()
            long_term_count = 0
            short_term_count = 0
            for purchase in self._purchases():
                for sale in self._sales(purchase, days):
                    want = _rp2_1_7_2_is_long_term(country, purchase, sale)
                    got = self._gain_loss(configuration, purchase, sale).is_long_term_capital_gains()
                    self.assertEqual(got, want, msg=f"{country.country_iso_code} ({days} days): bought {purchase.isoformat()}, sold {sale.isoformat()}")
                    if got:
                        long_term_count += 1
                    else:
                        short_term_count += 1
            # Both results occur, so the comparison checks both sides of the threshold.
            self.assertGreater(long_term_count, 0)
            self.assertGreater(short_term_count, 0)

    # The US rule: the anniversary of the purchase date is short-term, the following day is long-term, and the time of day doesn't matter.
    # The timestamps are already tax timestamps here (UTC): GainLoss converts them before calling the rule (see test_tax_dates.py).
    def test_us_anniversary_and_following_day(self) -> None:
        self._assert_cases(
            US(),
            [
                # Publication 544's example: bought on June 17, 2024. Sold on June 17, 2025 the holding period isn't longer than 1 year, sold on
                # June 19, 2025 it is. June 18, 2025 is long-term too: counting from June 18, 2024, it's the first day after a full year.
                _Case("Publication 544: the anniversary", "2024-06-17T12:00:00+00:00", "2025-06-17T12:00:00+00:00", False),
                _Case("Publication 544: the day after the anniversary", "2024-06-17T12:00:00+00:00", "2025-06-18T12:00:00+00:00", True),
                _Case("Publication 544: two days after the anniversary", "2024-06-17T12:00:00+00:00", "2025-06-19T12:00:00+00:00", True),
                # Publication 550's example: bought on January 31, 2024. Sold on January 29, 2025 it's short-term, sold on February 6, 2025 it's
                # long-term. In between, the anniversary (January 31) is short-term and the next day (February 1) is long-term.
                _Case("Publication 550: before the anniversary", "2024-01-31T12:00:00+00:00", "2025-01-29T12:00:00+00:00", False),
                _Case("Publication 550: the anniversary", "2024-01-31T12:00:00+00:00", "2025-01-31T12:00:00+00:00", False),
                _Case("Publication 550: the day after the anniversary", "2024-01-31T12:00:00+00:00", "2025-02-01T12:00:00+00:00", True),
                _Case("Publication 550: a week after the anniversary", "2024-01-31T12:00:00+00:00", "2025-02-06T12:00:00+00:00", True),
                # Dates, not hours: a second after midnight of the following day is long-term, although 1 year and 1 second passed...
                _Case("the first second of the following day", "2024-06-17T23:59:59+00:00", "2025-06-18T00:00:00+00:00", True),
                # ...and the last second of the anniversary is short-term, although 365 days and almost 24 hours passed.
                _Case("the last second of the anniversary", "2024-06-17T00:00:00+00:00", "2025-06-17T23:59:59+00:00", False),
                _Case("the end of the year: the anniversary", "2019-12-31T12:00:00+00:00", "2020-12-31T12:00:00+00:00", False),
                _Case("the end of the year: the following day", "2019-12-31T12:00:00+00:00", "2021-01-01T12:00:00+00:00", True),
            ],
        )

    # The US rule around February 29th: the anniversary is short-term even when 366 days passed, and a purchase on February 29th has its
    # anniversary on February 28th (the next year has no February 29th), so it's long-term from March 1st.
    def test_us_leap_year_boundaries(self) -> None:
        self._assert_cases(
            US(),
            [
                _Case("bought on March 1st, 2023: February 29th, 2024 (365 days)", "2023-03-01T12:00:00+00:00", "2024-02-29T12:00:00+00:00", False),
                _Case("bought on March 1st, 2023: the anniversary (366 days)", "2023-03-01T12:00:00+00:00", "2024-03-01T12:00:00+00:00", False),
                _Case("bought on March 1st, 2023: the following day", "2023-03-01T12:00:00+00:00", "2024-03-02T12:00:00+00:00", True),
                _Case("bought on February 29th, 2024: February 28th, 2025", "2024-02-29T12:00:00+00:00", "2025-02-28T12:00:00+00:00", False),
                _Case("bought on February 29th, 2024: March 1st, 2025", "2024-02-29T12:00:00+00:00", "2025-03-01T12:00:00+00:00", True),
                _Case("bought on February 29th, 2020: February 28th, 2021", "2020-02-29T12:00:00+00:00", "2021-02-28T12:00:00+00:00", False),
                _Case("bought on February 29th, 2020: March 1st, 2021", "2020-02-29T12:00:00+00:00", "2021-03-01T12:00:00+00:00", True),
                _Case("bought on February 28th, 2024: the anniversary", "2024-02-28T12:00:00+00:00", "2025-02-28T12:00:00+00:00", False),
                _Case("bought on February 28th, 2024: March 1st, 2025", "2024-02-28T12:00:00+00:00", "2025-03-01T12:00:00+00:00", True),
                _Case("bought on March 1st, 2024: the anniversary (365 days)", "2024-03-01T12:00:00+00:00", "2025-03-01T12:00:00+00:00", False),
                _Case("bought on March 1st, 2024: the following day", "2024-03-01T12:00:00+00:00", "2025-03-02T12:00:00+00:00", True),
                _Case("bought on February 28th, 2023: the anniversary", "2023-02-28T12:00:00+00:00", "2024-02-28T12:00:00+00:00", False),
                # The day after the anniversary is February 29th. Rev. Rul. 66-7 counts a holding period that starts on the first day of a month
                # in calendar months, which would make this sale short-term (long-term from March 1st): see the question in R15's reply.
                _Case("bought on February 28th, 2023: February 29th, 2024", "2023-02-28T12:00:00+00:00", "2024-02-29T12:00:00+00:00", True),
                _Case("bought on February 28th, 2023: March 1st, 2024", "2023-02-28T12:00:00+00:00", "2024-03-01T12:00:00+00:00", True),
            ],
        )

    # Historical results: RP2 1.7.2 counted 365 days of 24 hours, also before 2025. Compared with it, the US rule changes only sales on the
    # anniversary of the purchase date and, when February 29th is in between (366 days to the anniversary), on the day before it: all of them
    # from long-term to short-term. Checked for every purchase date from 2015 to 2024 at noon, with sales from 363 to 368 days later an hour
    # before, at and after noon.
    def test_us_rule_compared_with_rp2_1_7_2(self) -> None:
        us = US()
        changed_count = 0
        purchase_day = date(2015, 1, 1)
        while purchase_day <= date(2024, 12, 31):
            purchase = datetime.combine(purchase_day, time(12), tzinfo=timezone.utc)
            anniversary = _anniversary(purchase_day)
            has_february_29 = (anniversary - purchase_day).days == 366
            for days in range(363, 369):
                for hour in (11, 12, 13):
                    sale = datetime.combine(purchase_day + timedelta(days=days), time(hour), tzinfo=timezone.utc)
                    rp2_1_7_2 = _rp2_1_7_2_is_long_term(us, purchase, sale)
                    got = us.is_long_term_capital_gain(purchase, sale)
                    message = f"bought {purchase.isoformat()}, sold {sale.isoformat()}: RP2 1.7.2 {rp2_1_7_2}, now {got}"
                    # The US rule never turns a short-term result of 1.7.2 into a long-term one.
                    self.assertFalse(got and not rp2_1_7_2, msg=message)
                    # 1.7.2 was long-term once 365 days of 24 hours passed: on the anniversary at noon or later (or at any time, if February 29th is
                    # in between), and on the day before it at noon or later, if February 29th is in between.
                    at_noon_or_later = hour >= 12
                    on_anniversary = sale.date() == anniversary
                    on_day_before = sale.date() == anniversary - timedelta(days=1)
                    expected_change = (on_anniversary and (at_noon_or_later or has_february_29)) or (on_day_before and has_february_29 and at_noon_or_later)
                    self.assertEqual(got != rp2_1_7_2, expected_change, msg=message)
                    if got != rp2_1_7_2:
                        changed_count += 1
            purchase_day += timedelta(days=1)
        self.assertGreater(changed_count, 0)

    # Historical results through universal application (a report without per-wallet settings, all before 2025), with FIFO: the sales on the
    # anniversary and on the day before it (February 29th in between) are short-term, while RP2 1.7.2 reported them as long-term.
    def test_us_historical_results(self) -> None:
        configuration = _create_configuration(None)
        transactions: List[object] = [
            _In("i1", "2022-06-17T12:00:00+00:00", "Coinbase", "Buy", "100", "1"),
            _In("i2", "2023-03-01T12:00:00+00:00", "Coinbase", "Buy", "100", "1"),
            _In("i3", "2023-06-01T12:00:00+00:00", "Coinbase", "Buy", "100", "1"),
            # The anniversary, an hour after the purchase's time of day: 365 days and 1 hour (1.7.2: long-term).
            _Out("o1", "2023-06-17T13:00:00+00:00", "Coinbase", "200", "1"),
            # The day after the anniversary: 367 days (1.7.2: long-term too).
            _Out("o2", "2024-03-02T12:00:00+00:00", "Coinbase", "200", "1"),
            # The day before the anniversary, with February 29th in between: 365 days (1.7.2: long-term).
            _Out("o3", "2024-05-31T12:00:00+00:00", "Coinbase", "200", "1"),
        ]
        computed_data: ComputedData = compute_tax(configuration, self._create_accounting_engine(None), self._create_input_data(configuration, transactions))
        got = _sorted(self._to_tuples([gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)]))
        want = [
            _GainLoss("o1", "i1", "1", "100", "100", False),
            _GainLoss("o2", "i2", "1", "100", "100", True),
            _GainLoss("o3", "i3", "1", "100", "100", False),
        ]
        self.assertEqual(got, _sorted(self._want_tuples(want)))

    # The holding period starts at the original purchase, also after the opening allocation and transfers. Example: 1 coin bought on
    # Coinbase on 2024-03-01 and moved to Kraken in 2024. At the switch the allocation assigns that lot to Kraken, the only wallet with
    # funds. In 2025 the coin goes to BlockFi and back to Kraken (a round trip) and is sold: on 2025-03-01 (the anniversary) it's short-term,
    # on 2025-03-02 long-term. Universal application, which doesn't move lots, gives the same results.
    def test_us_purchase_date_survives_allocation_and_transfers(self) -> None:
        configuration = _create_configuration()
        for sale_timestamp, is_long_term in [("2025-03-01T12:00:00+00:00", False), ("2025-03-02T12:00:00+00:00", True)]:
            with self.subTest(sale=sale_timestamp):
                transactions: List[object] = [
                    _In("i1", "2024-03-01T12:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _Intra("t0", "2024-06-01T12:00:00+00:00", "Coinbase", "Kraken", "150", "1", "1"),
                    _Intra("t1", "2025-02-01T12:00:00+00:00", "Kraken", "BlockFi", "150", "1", "1"),
                    _Intra("t2", "2025-02-15T12:00:00+00:00", "BlockFi", "Kraken", "150", "1", "1"),
                    _Out("o1", sale_timestamp, "Kraken", "200", "1"),
                ]
                want = _sorted(self._want_tuples([_GainLoss("o1", "i1", "1", "100", "100", is_long_term)]))
                input_data = self._create_input_data(configuration, transactions)
                per_wallet = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
                universal = compute_tax(configuration, self._create_accounting_engine(None), self._create_input_data(configuration, transactions))
                for name, computed_data in (("per-wallet", per_wallet), ("universal", universal)):
                    got = _sorted(self._to_tuples([gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)]))
                    self.assertEqual(got, want, msg=name)
                # The allocation gave Kraken a lot at the switch, which keeps the purchase date of i1.
                opening_allocation = per_wallet.opening_allocation
                self.assertIsNotNone(opening_allocation)
                if opening_allocation is not None:
                    wallet_and_lot: List[str] = []
                    for lot in opening_allocation.allocated_lots:
                        wallet_and_lot.append(f"{lot.exchange}/{lot.original_lot.unique_id}")
                        self.assertEqual(lot.cost_basis_timestamp, datetime.fromisoformat("2024-03-01T12:00:00+00:00"))
                    want_wallet_and_lot: List[str] = ["Kraken/i1"]
                    self.assertEqual(wallet_and_lot, want_wallet_and_lot)


if __name__ == "__main__":
    unittest.main()

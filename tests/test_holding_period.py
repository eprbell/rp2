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
# Every country except the US counts whole days (24-hour periods): a gain is long-term if at least get_long_term_capital_gain_period() days
# passed, as in RP2 1.7.2. Example with Spain (365 days): bought on 2021-03-01 at noon and sold on 2022-03-01 at noon (365 days) is long-term,
# and sold at 11:59 AM it's short-term.

import os
import unittest
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterator, List, NamedTuple
from unittest.mock import patch

from rp2.abstract_country import AbstractCountry
from rp2.configuration import Configuration
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.out_transaction import OutTransaction
from rp2.plugin.country.es import ES
from rp2.plugin.country.generic import Generic
from rp2.plugin.country.ie import IE
from rp2.plugin.country.jp import JP
from rp2.rp2_decimal import RP2Decimal

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


# A purchase, a sale and whether the sale is long-term.
class _Case(NamedTuple):
    description: str
    purchase: str
    sale: str
    is_long_term: bool


class TestHoldingPeriod(unittest.TestCase):
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
            for time in ["00:00:00", "12:00:00", "23:59:59"]:
                for offset in _OFFSETS:
                    yield datetime.fromisoformat(f"{day}T{time}").replace(tzinfo=offset)

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


if __name__ == "__main__":
    unittest.main()

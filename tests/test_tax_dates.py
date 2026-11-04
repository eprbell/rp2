# Copyright 2025 eprbell
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

# R06 from the review of eprbell/rp2#155: tax dates and years come from one policy, the time zone of the country section of the configuration
# file (see Configuration.tax_timezone). Timestamps keep their own time zone and transactions are still sorted by the instant they happen,
# but every calendar date is the date in that time zone: date filters, tax years and yearly totals, the accounting method of each year, the
# switch to per-wallet application, holding periods and report dates. Both computations use it: compute_tax() (universal application) and
# compute_tax_per_wallet() (universal application before the switch, per-wallet application after it). Without a time zone in the
# configuration (other countries, or the US without a country section, which is only possible before 2025), the date of a timestamp is the
# one in its own time zone, as before.
#
# Example from the review: with America/New_York, 2025-12-31T23:30:00-08:00 (11:30 PM in Los Angeles) is 2:30 AM of January 1st, 2026 in
# New York, so it's in tax year 2026 and uses the accounting method of 2026.

import os
import shutil
import time
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

from ods_diff import read_sheet_rows
from per_wallet_common import _ASSET, _COINBASE, _KRAKEN, AbstractPerWalletTest, _create_configuration, _GainLoss, _GainLossTuple, _In, _Out, _sorted

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.abstract_transaction import AbstractTransaction
from rp2.computed_data import ComputedData
from rp2.configuration import MAX_DATE, MIN_DATE
from rp2.gain_loss import GainLoss
from rp2.localization import set_generation_language
from rp2.per_wallet_configuration import PerWalletConfiguration
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.country.jp import JP
from rp2.plugin.country.us import US
from rp2.plugin.report.us.tax_report_us import Generator as TaxReportUSGenerator
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError
from rp2.tax_engine import compute_tax, compute_tax_per_wallet

_NEW_YORK = PerWalletConfiguration(timezone_name="America/New_York")
# Two coins in the same wallet: FIFO sells the $100 one, HIFO the $300 one (the sale price is $400).
_TWO_COINS_2025: List[object] = [
    _In("i1", "2025-01-02T12:00:00-05:00", "Coinbase", "Buy", "100", "1"),
    _In("i2", "2025-02-03T12:00:00-05:00", "Coinbase", "Buy", "300", "1"),
]
_FIFO_SALE = [_GainLoss("o1", "i1", "1", "100", "300", False)]
_HIFO_SALE = [_GainLoss("o1", "i2", "1", "300", "100", False)]


class _Case(NamedTuple):
    description: str
    transactions: List[object]
    want: List[_GainLoss]
    # None means no country section (no time zone): then only universal application (compute_tax()) can run.
    per_wallet_configuration: Optional[PerWalletConfiguration] = _NEW_YORK
    years_2_methods: Optional[Dict[int, AbstractAccountingMethod]] = None
    # True if universal application (compute_tax()) must give the same result: a single wallet, or all transactions before the switch.
    same_as_universal: bool = True


class TestTaxDates(AbstractPerWalletTest):
    def _run(self, case: _Case) -> None:
        configuration = _create_configuration(case.per_wallet_configuration)
        input_data = self._create_input_data(configuration, case.transactions)
        want = _sorted(self._want_tuples(case.want))
        if case.per_wallet_configuration is not None:
            computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine(case.years_2_methods), input_data)
            self.assertEqual(_sorted(self._get_gain_losses(computed_data)), want, msg="per-wallet application")
        if case.same_as_universal or case.per_wallet_configuration is None:
            computed_data = compute_tax(configuration, self._create_accounting_engine(case.years_2_methods), input_data)
            self.assertEqual(_sorted(self._get_gain_losses(computed_data)), want, msg="universal application")

    def _get_gain_losses(self, computed_data: ComputedData) -> List[_GainLossTuple]:
        return self._to_tuples([gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)])

    # The conversion itself: the same instant, in the tax time zone. Without a time zone, the timestamp is unchanged.
    def test_tax_timestamp(self) -> None:
        timestamp = datetime.fromisoformat("2025-12-31T23:30:00-08:00")
        configuration = _create_configuration(_NEW_YORK)
        self.assertEqual(configuration.get_tax_timestamp(timestamp).isoformat(), "2026-01-01T02:30:00-05:00")
        self.assertEqual(configuration.get_tax_timestamp(timestamp), timestamp)
        self.assertEqual(configuration.get_tax_date(timestamp), date(2026, 1, 1))
        self.assertEqual(configuration.get_tax_year(timestamp), 2026)
        # New York is at UTC-5 in winter and at UTC-4 in summer (daylight saving time).
        self.assertEqual(configuration.get_tax_timestamp(datetime(2025, 1, 1, 4, 30, tzinfo=timezone.utc)).isoformat(), "2024-12-31T23:30:00-05:00")
        self.assertEqual(configuration.get_tax_timestamp(datetime(2025, 7, 1, 4, 30, tzinfo=timezone.utc)).isoformat(), "2025-07-01T00:30:00-04:00")
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'timestamp' is not a timezone-aware datetime"):
            configuration.get_tax_timestamp(datetime(2025, 12, 31, 23, 30))
        for configuration in (_create_configuration(None), _create_configuration(None, JP())):
            with self.subTest(country=configuration.country.country_iso_code):
                self.assertIsNone(configuration.tax_timezone)
                self.assertIs(configuration.get_tax_timestamp(timestamp), timestamp)
                self.assertEqual(configuration.get_tax_date(timestamp), date(2025, 12, 31))
                self.assertEqual(configuration.get_tax_year(timestamp), 2025)

    # The accounting method of a sale is the one of its tax year, in both phases. With FIFO until 2025 and HIFO from 2026, a sale at
    # 2025-12-31T23:30:00-08:00 uses HIFO, because it's 2026 in New York. Both sides of the year boundary, written in different time zones.
    def test_accounting_method_of_the_tax_year(self) -> None:
        fifo_then_hifo: Dict[int, AbstractAccountingMethod] = {1970: AccountingMethodFIFO(), 2026: AccountingMethodHIFO()}
        cases: List[_Case] = []
        for description, timestamp, want in [
            ("the example of the review: 11:30 PM of December 31st in Los Angeles", "2025-12-31T23:30:00-08:00", _HIFO_SALE),
            ("the last second of 2025 in New York, in Los Angeles time", "2025-12-31T20:59:59-08:00", _FIFO_SALE),
            ("the first second of 2026 in New York, in Los Angeles time", "2025-12-31T21:00:00-08:00", _HIFO_SALE),
            ("the last second of 2025 in New York, in UTC", "2026-01-01T04:59:59+00:00", _FIFO_SALE),
            ("the first second of 2026 in New York, in UTC", "2026-01-01T05:00:00+00:00", _HIFO_SALE),
            ("the first second of 2026 in New York, in New York time", "2026-01-01T00:00:00-05:00", _HIFO_SALE),
            ("the last second of 2025 in New York, in Tokyo time", "2026-01-01T13:59:59+09:00", _FIFO_SALE),
            ("the first second of 2026 in New York, in Tokyo time", "2026-01-01T14:00:00+09:00", _HIFO_SALE),
        ]:
            transactions = [*_TWO_COINS_2025, _Out("o1", timestamp, "Coinbase", "400", "1")]
            cases.append(_Case(f"per-wallet application: {description}", transactions, want, years_2_methods=fifo_then_hifo))
        # Before the switch (universal application), with FIFO until 2023 and HIFO from 2024: 2023-12-31T23:30:00-08:00 is 2024 in New York.
        fifo_then_hifo_2024: Dict[int, AbstractAccountingMethod] = {1970: AccountingMethodFIFO(), 2024: AccountingMethodHIFO()}
        two_coins_2023: List[object] = [
            _In("i1", "2023-01-02T12:00:00-05:00", "Coinbase", "Buy", "100", "1"),
            _In("i2", "2023-02-03T12:00:00-05:00", "Coinbase", "Buy", "300", "1"),
        ]
        for description, timestamp, want in [
            ("11:30 PM of December 31st in Los Angeles is 2024 in New York", "2023-12-31T23:30:00-08:00", _HIFO_SALE),
            ("the last second of 2023 in New York, in Los Angeles time", "2023-12-31T20:59:59-08:00", _FIFO_SALE),
        ]:
            transactions = [*two_coins_2023, _Out("o1", timestamp, "Coinbase", "400", "1")]
            cases.append(_Case(f"universal application: {description}", transactions, want, years_2_methods=fifo_then_hifo_2024))
        for case in cases:
            with self.subTest(name=case.description):
                self._run(case)

    # The switch to per-wallet application is the start of January 1st, 2025 in New York (Rev. Proc. 2024-28, section 3.10: "immediately
    # after the close of the taxpayer's day on December 31, 2024"). A Kraken sale just before it is universal, so FIFO uses the older coin,
    # bought on Coinbase for $100; just after it, the sale can only use the coin allocated to Kraken at the switch, bought for $300.
    def test_switch_to_per_wallet_application(self) -> None:
        allocation = PerWalletConfiguration(
            timezone_name="America/New_York", unused_basis_allocation_method="fifo", unused_basis_allocation_wallet_order=(_COINBASE, _KRAKEN)
        )
        universal_sale = [_GainLoss("o1", "i1", "1", "100", "400", False)]
        per_wallet_sale = [_GainLoss("o1", "i2", "1", "300", "200", False)]
        for description, timestamp, want in [
            ("the last second of 2024 in New York, in New York time", "2024-12-31T23:59:59-05:00", universal_sale),
            ("the first second of 2025 in New York, in New York time", "2025-01-01T00:00:00-05:00", per_wallet_sale),
            ("the last second of 2024 in New York, in UTC", "2025-01-01T04:59:59+00:00", universal_sale),
            ("the first second of 2025 in New York, in UTC", "2025-01-01T05:00:00+00:00", per_wallet_sale),
            ("3 AM of January 1st in Tokyo is still 2024 in New York", "2025-01-01T03:00:00+09:00", universal_sale),
            ("11:30 PM of December 31st in Los Angeles is already 2025 in New York", "2024-12-31T23:30:00-08:00", per_wallet_sale),
        ]:
            transactions: List[object] = [
                _In("i1", "2024-06-01T12:00:00-04:00", "Coinbase", "Buy", "100", "1"),
                _In("i2", "2024-07-01T12:00:00-04:00", "Kraken", "Buy", "300", "1"),
                _Out("o1", timestamp, "Kraken", "500", "1"),
            ]
            with self.subTest(name=description):
                self._run(_Case(description, transactions, want, allocation, same_as_universal=False))

    # Holding period (IRC §1222, IRS Publication 544): in the US a sale is long-term if its date is after the first anniversary of the
    # purchase date, and both are tax dates. The same UTC time of day can fall on different dates in New York, which is at UTC-5 in winter and
    # at UTC-4 in summer (daylight saving time). Without a time zone (the last case) the dates are those of the timestamps, UTC here: the
    # time zone changes this historical result.
    def test_holding_period_uses_tax_dates(self) -> None:
        cases: List[_Case] = []
        for description, bought, sold, is_long_term, per_wallet_configuration in [
            (
                "winter: 4:30 AM UTC is 11:30 PM of the day before in New York, the anniversary",
                "2024-01-10T12:00:00-05:00",
                "2025-01-11T04:30:00+00:00",
                False,
                _NEW_YORK,
            ),
            (
                "winter: 5:30 AM UTC is 0:30 AM of the same day in New York, the day after the anniversary",
                "2024-01-10T12:00:00-05:00",
                "2025-01-11T05:30:00+00:00",
                True,
                _NEW_YORK,
            ),
            (
                "summer: 3:30 AM UTC is 11:30 PM of the day before in New York, the anniversary",
                "2024-07-01T12:00:00-04:00",
                "2025-07-02T03:30:00+00:00",
                False,
                _NEW_YORK,
            ),
            # With a fixed UTC-5 (e.g. the EST time zone, which has no daylight saving time) it would still be July 1st.
            ("summer: 4:30 AM UTC is 0:30 AM of the same day in New York", "2024-07-01T12:00:00-04:00", "2025-07-02T04:30:00+00:00", True, _NEW_YORK),
            (
                "the purchase date is a tax date too: 3 AM UTC of January 11th is January 10th in New York",
                "2024-01-11T03:00:00+00:00",
                "2025-01-11T05:30:00+00:00",
                True,
                _NEW_YORK,
            ),
            ("2024: 4:30 AM UTC of January 11th is the anniversary in New York", "2023-01-10T12:00:00-05:00", "2024-01-11T04:30:00+00:00", False, _NEW_YORK),
            (
                "2024 without a time zone: 4:30 AM UTC of January 11th is January 11th, after the anniversary",
                "2023-01-10T12:00:00-05:00",
                "2024-01-11T04:30:00+00:00",
                True,
                None,
            ),
        ]:
            transactions: List[object] = [_In("i1", bought, "Coinbase", "Buy", "100", "1"), _Out("o1", sold, "Coinbase", "200", "1")]
            cases.append(_Case(description, transactions, [_GainLoss("o1", "i1", "1", "100", "100", is_long_term)], per_wallet_configuration))
        for case in cases:
            with self.subTest(name=case.description):
                self._run(case)

    # Transactions are sorted by the instant they happen, not by their local time. On November 2nd, 2025 New York goes back from UTC-4 to
    # UTC-5 at 2 AM, so 1:15 AM UTC-5 is 45 minutes after 1:30 AM UTC-4: with FIFO, the sale at 1:30 AM UTC-4 gets the older coin.
    def test_order_is_by_instant_across_daylight_saving_time(self) -> None:
        transactions: List[object] = [
            *_TWO_COINS_2025,
            _Out("o2", "2025-11-02T01:15:00-05:00", "Coinbase", "400", "1"),
            _Out("o1", "2025-11-02T01:30:00-04:00", "Coinbase", "400", "1"),
        ]
        want = [_GainLoss("o1", "i1", "1", "100", "300", False), _GainLoss("o2", "i2", "1", "300", "100", False)]
        self._run(_Case("FIFO across the end of daylight saving time", transactions, want))

    # Date filters (-f and -t) and report dates are tax dates. With to_date December 31st, 2025, a sale at 3 AM UTC of January 1st, 2026
    # (10 PM of December 31st in New York) is in the report, and one at 6 AM UTC (1 AM of January 1st in New York) isn't. The US tax report
    # shows tax dates (the coin bought at 3 AM UTC of January 2nd, 2025 was bought on January 1st in New York) and, in its last column, the
    # timestamp of the sale as it is in the input.
    def test_report_filters_use_tax_dates(self) -> None:
        set_generation_language("en")
        transactions: List[object] = [
            _In("i1", "2025-01-02T03:00:00+00:00", "Coinbase", "Buy", "100", "1"),
            _Out("o1", "2026-01-01T03:00:00+00:00", "Coinbase", "200", "0.5"),
            _Out("o2", "2026-01-01T06:00:00+00:00", "Coinbase", "300", "0.5"),
        ]
        output_dir = Path("output") / Path("test_tax_dates")
        for from_date, to_date, want_sale, want_year, want_balance, want_report_row in [
            (MIN_DATE, date(2025, 12, 31), "o1", 2025, "0.5", ["0.5", _ASSET, "01/01/2025", "12/31/2025", "100.0", "50.0", "", "", "50.0"]),
            (date(2026, 1, 1), MAX_DATE, "o2", 2026, "0", ["0.5", _ASSET, "01/01/2025", "01/01/2026", "150.0", "50.0", "", "", "100.0"]),
        ]:
            configuration = _create_configuration(_NEW_YORK, from_date=from_date, to_date=to_date)
            input_data = self._create_input_data(configuration, transactions)
            for name, computed_data in [
                ("per-wallet application", compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)),
                ("universal application", compute_tax(configuration, self._create_accounting_engine(None), input_data)),
            ]:
                with self.subTest(name=name, from_date=from_date, to_date=to_date):
                    want_sales: List[str] = [want_sale]
                    taxable_events = [entry.unique_id for entry in computed_data.taxable_event_set if isinstance(entry, AbstractTransaction)]
                    self.assertEqual(taxable_events, want_sales)
                    gain_losses = [entry.taxable_event.unique_id for entry in computed_data.gain_loss_set if isinstance(entry, GainLoss)]
                    self.assertEqual(gain_losses, want_sales)
                    want_years: List[int] = [want_year]
                    years: List[int] = [yearly_gain_loss.year for yearly_gain_loss in computed_data.yearly_gain_loss_list]
                    self.assertEqual(years, want_years)
                    want_balances: List[RP2Decimal] = [RP2Decimal(want_balance)]
                    balances: List[RP2Decimal] = [balance.final_balance for balance in computed_data.balance_set]
                    self.assertEqual(balances, want_balances)

                    shutil.rmtree(output_dir, ignore_errors=True)
                    output_dir.mkdir(parents=True)
                    TaxReportUSGenerator().generate(US(), {1970: "fifo"}, {_ASSET: computed_data}, str(output_dir), "", from_date, to_date, "en")
                    rows = read_sheet_rows(output_dir / Path("fifo_tax_report_us.ods"), "Capital Gains") or []
                    sale_rows = [row for row in rows if row[1:2] == [_ASSET]]
                    want_report_rows: List[List[str]] = [want_report_row]
                    report_rows: List[List[str]] = [row[:9] for row in sale_rows]
                    self.assertEqual(report_rows, want_report_rows)
                    sale = next(transaction for transaction in transactions if isinstance(transaction, _Out) and transaction.unique_id == want_sale)
                    self.assertEqual(sale_rows[0][15], str(datetime.fromisoformat(sale.timestamp)))

    # The results don't depend on the time zone of the computer (set by the TZ environment variable; it can be changed at run time only on
    # Unix).
    def test_results_do_not_depend_on_the_computer_time_zone(self) -> None:
        if not hasattr(time, "tzset"):
            self.skipTest("time.tzset() is only available on Unix")
        old_computer_timezone = os.environ.get("TZ")

        def restore_computer_timezone() -> None:
            if old_computer_timezone is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = old_computer_timezone
            time.tzset()

        self.addCleanup(restore_computer_timezone)
        fifo_then_hifo: Dict[int, AbstractAccountingMethod] = {1970: AccountingMethodFIFO(), 2026: AccountingMethodHIFO()}
        cases = [
            _Case(
                "the example of the review",
                [*_TWO_COINS_2025, _Out("o1", "2025-12-31T23:30:00-08:00", "Coinbase", "400", "1")],
                _HIFO_SALE,
                years_2_methods=fifo_then_hifo,
            ),
            _Case(
                "the last second of 2025",
                [*_TWO_COINS_2025, _Out("o1", "2026-01-01T04:59:59+00:00", "Coinbase", "400", "1")],
                _FIFO_SALE,
                years_2_methods=fifo_then_hifo,
            ),
        ]
        for computer_timezone in ("UTC", "America/Los_Angeles", "America/New_York", "Asia/Tokyo"):
            os.environ["TZ"] = computer_timezone
            time.tzset()
            for case in cases:
                with self.subTest(computer_timezone=computer_timezone, name=case.description):
                    self._run(case)

    # Countries without a time zone in their configuration (all but the US, which allows per-wallet application) keep the dates of their
    # timestamps: in Japan, 2025-12-31T23:30:00-08:00 is in 2025.
    def test_other_countries_keep_the_dates_of_their_timestamps(self) -> None:
        configuration = _create_configuration(None, JP())
        input_data = self._create_input_data(configuration, [*_TWO_COINS_2025, _Out("o1", "2025-12-31T23:30:00-08:00", "Coinbase", "400", "1")])
        computed_data = compute_tax(configuration, self._create_accounting_engine(None), input_data)
        self.assertEqual(_sorted(self._get_gain_losses(computed_data)), _sorted(self._want_tuples(_FIFO_SALE)))
        years: List[int] = [yearly_gain_loss.year for yearly_gain_loss in computed_data.yearly_gain_loss_list]
        want_years: List[int] = [2025]
        self.assertEqual(years, want_years)


if __name__ == "__main__":
    unittest.main()

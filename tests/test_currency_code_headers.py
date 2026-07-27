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

"""Unit tests verifying that rp2_full_report column headers reflect the active
currency code rather than the hardcoded "USD" string (regression for PR #144)."""

import unittest
from typing import ClassVar, List, Set, cast

from rp2.abstract_country import AbstractCountry
from rp2.plugin.report.rp2_full_report import Generator


def _make_country(country_iso: str, currency_iso: str) -> AbstractCountry:
    """Return a minimal concrete AbstractCountry for the given codes."""

    class _Country(AbstractCountry):
        def __init__(self) -> None:
            super().__init__(country_iso, currency_iso)

        def get_long_term_capital_gain_period(self) -> int:
            return 365

        def get_default_accounting_method(self) -> str:
            return "fifo"

        def get_accounting_methods(self) -> Set[str]:
            return {"fifo", "hifo", "lifo", "lofo"}

        def get_report_generators(self) -> Set[str]:
            return {"rp2_full_report"}

        def get_default_generation_language(self) -> str:
            return "en"

    return _Country()


class TestCurrencyCodeHeaders(unittest.TestCase):
    """Verify _setup_text_data uses the country's currency code in headers."""

    # Map of (country_iso, currency_iso) -> expected uppercase currency string
    CASES: ClassVar = [
        ("us", "usd", "USD"),
        ("de", "eur", "EUR"),
        ("gb", "gbp", "GBP"),
        ("jp", "jpy", "JPY"),
        ("ch", "chf", "CHF"),
        ("ca", "cad", "CAD"),
    ]

    def _get_headers(self, country_iso: str, currency_iso: str) -> List[str]:
        # pylint: disable=protected-access
        g = Generator()
        g._setup_text_data(_make_country(country_iso, currency_iso))
        # Access name-mangled attribute
        return cast(List[str], g._Generator__yearly_gain_loss_summary_header_names_row_1)  # type: ignore[attr-defined]

    def test_yearly_gain_loss_summary_headers_contain_currency_code(self) -> None:
        """Header row 1 of the gain/loss summary must use the active currency, not USD."""
        for country_iso, currency_iso, expected_code in self.CASES:
            with self.subTest(currency=expected_code):
                headers = self._get_headers(country_iso, currency_iso)
                self.assertIn(
                    expected_code,
                    headers,
                    msg=f"Expected '{expected_code}' in yearly gain/loss summary headers, got {headers}",
                )
                self.assertIn(
                    f"{expected_code} Total",
                    headers,
                    msg=f"Expected '{expected_code} Total' in yearly gain/loss summary headers, got {headers}",
                )

    def test_non_usd_headers_do_not_contain_literal_usd(self) -> None:
        """For non-USD currencies the hardcoded 'USD' string must not appear in headers."""
        non_usd_cases = [(ci, cu, ex) for ci, cu, ex in self.CASES if ex != "USD"]
        for country_iso, currency_iso, expected_code in non_usd_cases:
            with self.subTest(currency=expected_code):
                headers = self._get_headers(country_iso, currency_iso)
                self.assertNotIn(
                    "USD",
                    headers,
                    msg=f"Hardcoded 'USD' found in headers for {expected_code} country: {headers}",
                )
                self.assertNotIn(
                    "USD Total",
                    headers,
                    msg=f"Hardcoded 'USD Total' found in headers for {expected_code} country: {headers}",
                )

    def test_usd_country_headers_unchanged(self) -> None:
        """For a US/USD country the headers should still read 'USD' and 'USD Total'."""
        headers = self._get_headers("us", "usd")
        self.assertIn("USD", headers)
        self.assertIn("USD Total", headers)


if __name__ == "__main__":
    unittest.main()

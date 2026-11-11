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

import sys
import unittest

from rp2.plugin.country.ca import CA


class TestCountryCA(unittest.TestCase):
    def setUp(self) -> None:
        self._country = CA()

    def test_country_and_currency_codes(self) -> None:
        self.assertEqual(self._country.country_iso_code, "ca")
        self.assertEqual(self._country.currency_iso_code, "cad")

    def test_long_term_capital_gain_period(self) -> None:
        # Canada taxes capital gains regardless of the holding period, so
        # there is no long-term capital gain period
        self.assertEqual(self._country.get_long_term_capital_gain_period(), sys.maxsize)

    def test_accounting_methods(self) -> None:
        # Placeholder until the average-cost (ACB) method is implemented: the
        # default method must be one of the accepted ones
        self.assertIn(self._country.get_default_accounting_method(), self._country.get_accounting_methods())
        self.assertEqual(self._country.get_accounting_methods(), {"fifo"})

    def test_report_generators(self) -> None:
        self.assertEqual(self._country.get_report_generators(), {"open_positions", "rp2_full_report"})

    def test_default_generation_language(self) -> None:
        self.assertEqual(self._country.get_default_generation_language(), "en")


if __name__ == "__main__":
    unittest.main()

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

import os
import unittest
from typing import Dict, Tuple
from unittest.mock import patch

from rp2.application_policy import (
    UNIVERSAL_APPLICATION_POLICY,
    ApplicationMode,
    ApplicationPeriod,
    ApplicationPolicy,
)
from rp2.plugin.country.es import ES
from rp2.plugin.country.generic import Generic
from rp2.plugin.country.ie import IE
from rp2.plugin.country.jp import JP
from rp2.plugin.country.us import US
from rp2.rp2_error import RP2TypeError, RP2ValueError

_UNIVERSAL = ApplicationMode.UNIVERSAL
_PER_WALLET = ApplicationMode.PER_WALLET


def _year_2_mode(*year_and_modes: Tuple[int, ApplicationMode]) -> Dict[int, ApplicationMode]:
    return dict(year_and_modes)


class TestApplicationPolicy(unittest.TestCase):
    # US: universal application until 2024, per-wallet application from 2025 (Treas. Reg. §1.1012-1(j)(6)), with no choice in either period.
    def test_us_policy(self) -> None:
        policy = US().get_application_policy()
        self.assertTrue(policy.allows_per_wallet)
        self.assertEqual(policy.get_year_2_mode([2023, 2024], None), _year_2_mode((2023, _UNIVERSAL), (2024, _UNIVERSAL)))
        self.assertEqual(policy.get_year_2_mode([2024, 2025, 2026], None), _year_2_mode((2024, _UNIVERSAL), (2025, _PER_WALLET), (2026, _PER_WALLET)))
        self.assertEqual(policy.get_year_2_mode([], None), _year_2_mode())

        # The switch is at the start of 2025 even if the first per-wallet year with transactions is later.
        self.assertIsNone(policy.get_per_wallet_start_year(policy.get_year_2_mode([2020, 2024], None)))
        self.assertEqual(policy.get_per_wallet_start_year(policy.get_year_2_mode([2025], None)), 2025)
        self.assertEqual(policy.get_per_wallet_start_year(policy.get_year_2_mode([2023, 2027], None)), 2025)

        # An explicit choice is accepted only if every year with transactions allows it.
        self.assertEqual(policy.get_year_2_mode([2024], _UNIVERSAL), _year_2_mode((2024, _UNIVERSAL)))
        self.assertEqual(policy.get_year_2_mode([2025], _PER_WALLET), _year_2_mode((2025, _PER_WALLET)))
        with self.assertRaisesRegex(RP2ValueError, "Application mode 'universal' is not allowed in 2025: allowed modes from 2025 are per_wallet"):
            policy.get_year_2_mode([2024, 2025], _UNIVERSAL)
        with self.assertRaisesRegex(RP2ValueError, "Application mode 'per_wallet' is not allowed in 2024: allowed modes from 1 are universal"):
            policy.get_year_2_mode([2024, 2025], _PER_WALLET)

    # Countries that don't declare a policy use universal application in every year: they never get the US rules by accident.
    def test_universal_only_countries(self) -> None:
        environment: Dict[str, str] = {"CURRENCY_CODE": "eur", "LONG_TERM_CAPITAL_GAINS": "365"}
        with patch.dict(os.environ, environment):
            generic = Generic()
        for country in (JP(), ES(), IE(), generic):
            with self.subTest(country=country.country_iso_code):
                policy = country.get_application_policy()
                self.assertIs(policy, UNIVERSAL_APPLICATION_POLICY)
                self.assertFalse(policy.allows_per_wallet)
                self.assertEqual(policy.get_year_2_mode([2024, 2025, 2030], None), _year_2_mode((2024, _UNIVERSAL), (2025, _UNIVERSAL), (2030, _UNIVERSAL)))
                self.assertIsNone(policy.get_per_wallet_start_year(policy.get_year_2_mode([2025], None)))
                with self.assertRaisesRegex(RP2ValueError, "Application mode 'per_wallet' is not allowed in 2025"):
                    policy.get_year_2_mode([2025], _PER_WALLET)

    # A period that allows both modes takes the user's choice; switching back from per-wallet to universal application isn't supported.
    def test_policy_with_a_choice(self) -> None:
        policy = ApplicationPolicy(
            [
                ApplicationPeriod(1, frozenset({_UNIVERSAL}), _UNIVERSAL),
                ApplicationPeriod(2030, frozenset({_UNIVERSAL, _PER_WALLET}), _UNIVERSAL),
            ]
        )
        self.assertIsNone(policy.get_per_wallet_start_year(policy.get_year_2_mode([2029, 2031], None)))
        with self.assertRaisesRegex(RP2ValueError, "'per_wallet' is not allowed in 2029"):
            policy.get_year_2_mode([2029, 2031], _PER_WALLET)
        self.assertEqual(policy.get_per_wallet_start_year(policy.get_year_2_mode([2031], _PER_WALLET)), 2030)

        policy = ApplicationPolicy(
            [
                ApplicationPeriod(1, frozenset({_PER_WALLET}), _PER_WALLET),
                ApplicationPeriod(2030, frozenset({_UNIVERSAL}), _UNIVERSAL),
            ]
        )
        with self.assertRaisesRegex(RP2ValueError, "Switching back from per-wallet to universal application is not supported"):
            policy.get_per_wallet_start_year(policy.get_year_2_mode([2029, 2031], None))

    def test_invalid_policies(self) -> None:
        with self.assertRaisesRegex(RP2ValueError, "at least one period"):
            ApplicationPolicy([])
        with self.assertRaisesRegex(RP2ValueError, "strictly increasing start year: 2025, 2025"):
            ApplicationPolicy([ApplicationPeriod(2025, frozenset({_UNIVERSAL}), _UNIVERSAL), ApplicationPeriod(2025, frozenset({_UNIVERSAL}), _UNIVERSAL)])
        with self.assertRaisesRegex(RP2TypeError, "non-ApplicationPeriod element"):
            ApplicationPolicy([2025])  # type: ignore
        with self.assertRaisesRegex(RP2ValueError, "allows no application mode"):
            ApplicationPeriod(2025, frozenset(), _UNIVERSAL)
        with self.assertRaisesRegex(RP2ValueError, "default mode per_wallet is not an allowed mode"):
            ApplicationPeriod(2025, frozenset({_UNIVERSAL}), _PER_WALLET)
        with self.assertRaisesRegex(RP2TypeError, "not an integer"):
            ApplicationPeriod("2025", frozenset({_UNIVERSAL}), _UNIVERSAL)  # type: ignore
        with self.assertRaisesRegex(RP2TypeError, "not of type ApplicationMode"):
            ApplicationPeriod(2025, frozenset({"universal"}), _UNIVERSAL)  # type: ignore

    def test_application_mode_from_string(self) -> None:
        self.assertEqual(ApplicationMode.from_string(" Per_Wallet "), _PER_WALLET)
        self.assertEqual(ApplicationMode.from_string("universal"), _UNIVERSAL)
        with self.assertRaisesRegex(RP2ValueError, "Invalid application mode 'per-wallet': valid values are universal, per_wallet"):
            ApplicationMode.from_string("per-wallet")


if __name__ == "__main__":
    unittest.main()

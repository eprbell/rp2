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
import shutil
import unittest
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Any, List, NamedTuple, Optional

import ezodf

from abstract_test_ods_output_diff import (
    CONFIG_PATH,
    INPUT_PATH,
    AbstractTestODSOutputDiff,
    OutputPlugins,
)
from ods_diff import ods_diff

ROOT_PATH: Path = Path(os.path.dirname(__file__)).parent.absolute()

_COUNTRY_US_SECTION: str = "\n[country.us]\ntimezone = America/New_York\n"


class _Dataset(NamedTuple):
    test_name: str
    config: str
    methods: List[str]
    allow_negative_balances: bool


# All these datasets end before 2025, so the US application policy uses universal application for all of them: adding the country section
# (with the per-wallet settings) must not change the output, which is checked against golden files in test_ods_output_diff.py.
_DATASETS: List[_Dataset] = [
    _Dataset("crypto_example", "crypto_example", AbstractTestODSOutputDiff.METHODS, True),
    _Dataset("test_data", "test_data", AbstractTestODSOutputDiff.METHODS, True),
    _Dataset("test_data4", "test_data4", AbstractTestODSOutputDiff.METHODS, False),
    _Dataset("test_many_year_data", "test_data", AbstractTestODSOutputDiff.METHODS, True),
    _Dataset("test_data_multi_method", "test_data_multi_method", ["mixed"], True),
]


# The application mode comes from the country's application policy (US: universal until 2024, per-wallet from 2025) and the configuration
# file's country section, not from a command line flag.
class TestODSOutputDiffPerWallet(AbstractTestODSOutputDiff):
    output_dir: Path
    universal_output_dir: Path
    config_dir: Path
    input_2025_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.output_dir = ROOT_PATH / Path("output") / Path(cls.__module__)
        cls.universal_output_dir = cls.output_dir / Path("universal")
        cls.config_dir = cls.output_dir / Path("config")
        shutil.rmtree(cls.output_dir, ignore_errors=True)
        cls.config_dir.mkdir(parents=True)

        for dataset in _DATASETS:
            config_text = (CONFIG_PATH / Path(f"{dataset.config}.ini")).read_text(encoding="utf-8")
            (cls.config_dir / Path(f"{dataset.config}.ini")).write_text(config_text + _COUNTRY_US_SECTION, encoding="utf-8")
            for method in dataset.methods:
                AbstractTestODSOutputDiff._generate(
                    cls.universal_output_dir,
                    test_name=dataset.test_name,
                    config=dataset.config,
                    method=method,
                    allow_negative_balances=dataset.allow_negative_balances,
                )
                AbstractTestODSOutputDiff._generate(
                    cls.output_dir,
                    test_name=dataset.test_name,
                    config=dataset.config,
                    method=method,
                    allow_negative_balances=dataset.allow_negative_balances,
                    config_dir=cls.config_dir,
                )

        # test_data4 with the B4 staking disposal moved from 2020 to 2025: B4 then has transactions on both sides of the US switch.
        cls.input_2025_path = cls.output_dir / Path("test_data4_2025.ods")
        document: Any = ezodf.opendoc(str(INPUT_PATH / Path("test_data4.ods")))
        sheet = document.sheets["B4"]
        if sheet[7, 0].value != "2020-02-01T08:41Z":
            raise ValueError(f"Unexpected test_data4.ods content: {sheet[7, 0].value}")
        sheet[7, 0].set_value("2025-02-01T08:41Z")
        document.saveas(str(cls.input_2025_path))

    def _run(self, country: str, config_suffix: str, input_path: Path, extra_arguments: Optional[List[str]] = None) -> "CompletedProcess[str]":
        config_path = self.config_dir / Path(f"test_data4_{country}_{abs(hash(config_suffix))}.ini")
        config_path.write_text((CONFIG_PATH / Path("test_data4.ini")).read_text(encoding="utf-8") + config_suffix, encoding="utf-8")
        arguments = [f"rp2_{country}", "-o", str(self.output_dir / Path(country)), "-a", "B4", *(extra_arguments or []), str(config_path), str(input_path)]
        return run(arguments, check=False, capture_output=True, text=True)

    def test_country_section_does_not_change_output_before_2025(self) -> None:
        for dataset in _DATASETS:
            for method in dataset.methods:
                for plugin_name in (OutputPlugins.OPEN_POSITIONS.name, OutputPlugins.RP2_FULL_REPORT.name, OutputPlugins.TAX_REPORT_US.name):
                    plugin_name = plugin_name.lower()
                    with self.subTest(dataset=dataset.test_name, method=method, plugin=plugin_name):
                        file_name = Path(f"{dataset.test_name}_{method}_{plugin_name}.ods")
                        self.assertTrue((self.output_dir / file_name).exists(), msg=str(file_name))
                        diff = ods_diff(self.universal_output_dir / file_name, self.output_dir / file_name, generate_ascii_representation=True)
                        self.assertFalse(diff, msg=diff)

    def test_per_wallet_flag_is_removed(self) -> None:
        result = self._run("us", _COUNTRY_US_SECTION, INPUT_PATH / Path("test_data4.ods"), ["-w"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments: -w", result.stderr)

    def test_us_data_before_2025_needs_no_country_section(self) -> None:
        result = self._run("us", "", INPUT_PATH / Path("test_data4.ods"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("per-wallet application from", result.stdout + result.stderr)

    def test_us_data_from_2025_uses_per_wallet_application(self) -> None:
        # Without the country section: an error, never a silent fallback to universal application.
        result = self._run("us", "", self.input_2025_path)
        self.assertNotEqual(result.returncode, 0)
        message = "B4 has transactions in 2025 or later, when US requires per-wallet application: add a 'country.us' section with at least the 'timezone'"
        self.assertIn(message, result.stdout + result.stderr)
        # A country section without the per-wallet settings is also missing the required data.
        result = self._run("us", "\n[country.us]\n", self.input_2025_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("add a 'country.us' section with at least the 'timezone' field", result.stdout + result.stderr)

        # With the per-wallet settings: universal application in 2020, per-wallet application from 2025, selected automatically.
        result = self._run("us", _COUNTRY_US_SECTION, self.input_2025_path)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("B4: universal application before 2025, per-wallet application from 2025 (timezone America/New_York)", result.stdout + result.stderr)

    def test_conflicting_application_mode_is_rejected(self) -> None:
        # Each US period allows one mode: an explicit choice that a year with transactions doesn't allow is an error.
        result = self._run("us", _COUNTRY_US_SECTION + "application_mode = universal\n", self.input_2025_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("B4: Application mode 'universal' is not allowed in 2025: allowed modes from 2025 are per_wallet", result.stdout + result.stderr)
        result = self._run("us", _COUNTRY_US_SECTION + "application_mode = per_wallet\n", self.input_2025_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("B4: Application mode 'per_wallet' is not allowed in 2020: allowed modes from 1 are universal", result.stdout + result.stderr)
        # A choice that matches the only allowed mode of every year with transactions is accepted.
        result = self._run("us", _COUNTRY_US_SECTION + "application_mode = universal\n", INPUT_PATH / Path("test_data4.ods"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        result = self._run("us", _COUNTRY_US_SECTION + "application_mode = wallet\n", self.input_2025_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid application mode 'wallet'", result.stdout + result.stderr)

    def test_japan_never_uses_per_wallet_application(self) -> None:
        # Japan computes cost basis across all wallets in every year: 2025 data uses universal application, and US settings are rejected.
        result = self._run("jp", "", self.input_2025_path, ["-g", "en"])
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("per-wallet application from", result.stdout + result.stderr)
        result = self._run("jp", _COUNTRY_US_SECTION, self.input_2025_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("section 'country.us' is for another country: this is rp2_jp", result.stdout + result.stderr)
        result = self._run("jp", "\n[country.jp]\ntimezone = Asia/Tokyo\n", self.input_2025_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("country 'jp' always uses universal application", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

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
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import ezodf

from abstract_test_ods_output_diff import (
    CONFIG_PATH,
    INPUT_PATH,
    AbstractTestODSOutputDiff,
    OutputPlugins,
)
from ods_diff import ods_diff, read_sheet_rows

ROOT_PATH: Path = Path(os.path.dirname(__file__)).parent.absolute()

_COUNTRY_US_SECTION: str = "\n[country.us]\ntimezone = America/New_York\n"
_GOLDEN_DATASET: str = "test_data_per_wallet"


class _Dataset(NamedTuple):
    test_name: str
    config: str
    methods: List[str]
    allow_negative_balances: bool


# All these datasets end before 2025, so the US application policy uses universal application for all of them: adding the country section
# (with the per-wallet settings) must not change the output, which is checked against golden files in test_ods_output_diff.py. The time zone
# of the section is also the one of tax dates, but these datasets have no timestamps that fall on a different date in New York (see
# test_tax_dates.py for timestamps that do).
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
    input_sold_path: Path

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

        # The per-wallet golden dataset (see test_per_wallet_golden_files()).
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name=_GOLDEN_DATASET, config=_GOLDEN_DATASET, method="mixed")

        # test_data4 with the B4 staking disposal moved from 2020 to 2025: B4 then has transactions on both sides of the US switch.
        cls.input_2025_path = cls.output_dir / Path("test_data4_2025.ods")
        document: Any = ezodf.opendoc(str(INPUT_PATH / Path("test_data4.ods")))
        sheet = document.sheets["B4"]
        if sheet[7, 0].value != "2020-02-01T08:41Z":
            raise ValueError(f"Unexpected test_data4.ods content: {sheet[7, 0].value}")
        sheet[7, 0].set_value("2025-02-01T08:41Z")
        document.saveas(str(cls.input_2025_path))
        # test_data4 with the whole B4 unit disposed of in 2020 (instead of half of it): B4 then holds nothing after 2020.
        cls.input_sold_path = cls.output_dir / Path("test_data4_sold.ods")
        document = ezodf.opendoc(str(INPUT_PATH / Path("test_data4.ods")))
        sheet = document.sheets["B4"]
        if sheet[7, 7].value != 0.5:
            raise ValueError(f"Unexpected test_data4.ods content: {sheet[7, 7].value}")
        sheet[7, 7].set_value(1.0)
        document.saveas(str(cls.input_sold_path))

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
        # Without -t the report ends on the date of the last transaction.
        message = (
            "B4 has transactions or holdings in 2025 or later (the report ends on 2025-02-01), when US requires per-wallet application: add a "
            "'country.us' section with at least the 'timezone' field to the configuration file (see docs/input_files.md), or end the report "
            "before 2025 with -t"
        )
        self.assertIn(message, result.stdout + result.stderr)
        # A country section without the per-wallet settings is also missing the required data.
        result = self._run("us", "\n[country.us]\n", self.input_2025_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("add a 'country.us' section with at least the 'timezone' field", result.stdout + result.stderr)

        # With the per-wallet settings: universal application in 2020, per-wallet application from 2025, selected automatically.
        result = self._run("us", _COUNTRY_US_SECTION, self.input_2025_path)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("B4: universal application before 2025, per-wallet application from 2025 (timezone America/New_York)", result.stdout + result.stderr)

    # R10: the period of the report decides whether it needs per-wallet application, not the transactions after it. The report ends on the -t
    # date or, without -t, on the date of the last transaction: never on today's date.
    def test_report_period_decides_the_application_mode(self) -> None:
        # test_data4.ods ends in 2020, when B4 still holds 0.5 units: a report that reaches 2025 needs their opening allocation, even though
        # B4 has no transactions after 2020.
        result = self._run("us", "", INPUT_PATH / Path("test_data4.ods"), ["-t", "2025-12-31"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("B4 has transactions or holdings in 2025 or later (the report ends on 2025-12-31)", result.stdout + result.stderr)
        result = self._run("us", _COUNTRY_US_SECTION, INPUT_PATH / Path("test_data4.ods"), ["-t", "2025-12-31"])
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn(
            "B4: per-wallet application from 2025-01-01T00:00:00-05:00 (start of 2025 in America/New_York): 1 lot pieces allocated at the "
            "switch, 0 transactions after it",
            result.stdout + result.stderr,
        )
        # The opening allocation report: only Coinbase/Bob holds B4 (0.5 units of the lot bought for $10 per unit), so the allocation is
        # automatic, with FIFO (no method is configured). The switch is midnight in New York.
        allocation_path = self.output_dir / Path("us") / Path("fifo_opening_allocation.ods")
        summary_rows = (read_sheet_rows(allocation_path, "Summary") or [])[3:]
        want_summary_rows = [
            ["B4", "2025-01-01T00:00:00-05:00", "America/New_York", "Automatic", "FIFO", "", "Coinbase/Bob", "", "0.5", "0.5", "0.5", "5.0", "5.0"]
        ]
        self.assertEqual(summary_rows, want_summary_rows)
        # If B4 holds nothing at the end of the report and has no transactions in 2025, there's nothing to allocate: universal application.
        # The opening allocation report of the previous run is removed, since it doesn't belong to this one.
        result = self._run("us", "", self.input_sold_path, ["-t", "2025-12-31"])
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("per-wallet application from", result.stdout + result.stderr)
        self.assertFalse(allocation_path.exists())
        # A report that ends before 2025 doesn't need the per-wallet settings, even if the input has transactions in 2025.
        result = self._run("us", "", self.input_2025_path, ["-t", "2024-12-31"])
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn("per-wallet application from", result.stdout + result.stderr)

    # R11 from the review of eprbell/rp2#155: a per-wallet golden dataset, input/test_data_per_wallet.ods with config/test_data_per_wallet.ini
    # (time zone America/New_York; FIFO until 2025, HIFO from 2026; allocation FIFO with wallet order Kraken, BlockFi, Coinbase, and HIFO with
    # Coinbase, Kraken for B2). Its transactions:
    # - B1, before the switch: i1 buy 3 on Coinbase for $100 each plus a $3 fee ($101 per coin, January 10th, 2024); i2 buy 2 on Kraken for
    #   $200 each (March 15th); t1 Coinbase -> BlockFi, 1.1 sent, 1.0 received (June 1st); o1 sell 0.5 on Kraken (September 1st); i3 buy 1
    #   on Coinbase for $400 at 2025-01-01T03:00Z, which is 10 PM of December 31st, 2024 in New York. At the switch Kraken holds 1.5,
    #   BlockFi 1.0 and Coinbase 2.9, and FIFO has used 0.6 coins of i1: the unused lots are i1 2.4, i2 2 and i3 1. Allocation: Kraken
    #   gets i1 1.5, BlockFi i1 0.9 and i2 0.1, Coinbase i2 1.9 and i3 1;
    # - B1, after the switch: t2 Kraken -> BlockFi, 1.0 sent, 0.9 received, and t3 BlockFi -> Kraken, 0.9 (a cycle); s1 staking 0.2 on Kraken
    #   ($600); o2 sell 2 on Coinbase in June 2025 (FIFO: i2 1.9, i3 0.1); o3 sell 0.5 on BlockFi at 2026-01-01T04:00Z, which is December
    #   31st, 2025 in New York (FIFO, the method of 2025: i1); o4 sell 1 on Kraken in February 2026 (HIFO: s1 0.2 first, then i1 0.8);
    # - B2: j1 ($50, Coinbase), j2 ($80, Kraken), j3 ($60, Kraken) and a transfer Kraken -> Coinbase in 2024; HIFO allocation gives Coinbase
    #   j2 and j3 and Kraken j1, which p1 sells in March 2025;
    # - B3: 5 coins bought on BlockFi in 2024, nothing else: automatic allocation, without later transactions;
    # - B4: bought in 2025 and moved to Kraken: nothing to allocate.
    # The reports are compared with golden files (input/golden/us/test_data_per_wallet_mixed_*.ods) and their key cells and formulas with
    # values computed by hand (test_per_wallet_golden_cells()). The full report shows artificial lot ids for the lots of per-wallet sales
    # (e.g. i1/-1): R17 replaces them with the original lots, and updates the golden file.
    def test_per_wallet_golden_files(self) -> None:
        for plugin in (OutputPlugins.OPEN_POSITIONS, OutputPlugins.OPENING_ALLOCATION, OutputPlugins.RP2_FULL_REPORT, OutputPlugins.TAX_REPORT_US):
            with self.subTest(plugin=plugin.value):
                self._compare(self.output_dir, test_name=_GOLDEN_DATASET, method="mixed", output_plugin=plugin)

    def test_per_wallet_golden_cells(self) -> None:
        prefix = self.output_dir / Path(f"{_GOLDEN_DATASET}_mixed_")

        # US tax report: every disposal and income, merged by taxable event and lot (asset, event, date acquired, date sold, holding period):
        # coins, proceeds, cost basis, gain. Dates are New York dates: i3 was acquired on December 31st, 2024 and o3 sold on December 31st,
        # 2025. Holding periods follow the coins through transfers and the allocation (e.g. o3 sells coins of i1, bought in January 2024).
        want_tax: Dict[str, Dict[Tuple[str, str, str, str, str], Tuple[str, str, str, str]]] = {
            "Capital Gains": {
                ("B1", "o1", "01/10/2024", "09/01/2024", "SHORT"): ("0.5", "150", "50.5", "99.5"),
                ("B1", "o2", "03/15/2024", "06/01/2025", "LONG"): ("1.9", "1330", "380", "950"),
                ("B1", "o2", "12/31/2024", "06/01/2025", "SHORT"): ("0.1", "70", "40", "30"),
                ("B1", "o3", "01/10/2024", "12/31/2025", "LONG"): ("0.5", "400", "50.5", "349.5"),
                ("B1", "o4", "04/01/2025", "02/01/2026", "SHORT"): ("0.2", "180", "120", "60"),
                ("B1", "o4", "01/10/2024", "02/01/2026", "LONG"): ("0.8", "720", "80.8", "639.2"),
                ("B2", "p1", "02/01/2024", "03/01/2025", "LONG"): ("1", "100", "50", "50"),
            },
            "Investment Expenses": {
                ("B1", "t1", "01/10/2024", "06/01/2024", "SHORT"): ("0.1", "25", "10.1", "14.9"),
                ("B1", "t2", "01/10/2024", "02/01/2025", "LONG"): ("0.1", "50", "10.1", "39.9"),
            },
            "Staking": {("B1", "s1", "", "04/01/2025", "SHORT"): ("0.2", "120", "0", "120")},
        }
        for sheet, want_rows in want_tax.items():
            got_rows: Dict[Tuple[str, str, str, str, str], List[float]] = {}
            for row in read_sheet_rows(Path(f"{prefix}tax_report_us.ods"), sheet) or []:
                if len(row) < 15 or row[1] not in ("B1", "B2"):
                    continue
                key = (row[1], row[13], row[2], row[3], row[14])
                values = got_rows.setdefault(key, [0.0, 0.0, 0.0, 0.0])
                for index, column in enumerate((0, 4, 5, 8)):
                    values[index] += float(row[column]) if row[column] else 0.0
            self.assertEqual(sorted(got_rows), sorted(want_rows), msg=sheet)
            for key, want_values in want_rows.items():
                for got_value, want_value in zip(got_rows[key], want_values):
                    self.assertAlmostEqual(got_value, float(want_value), msg=f"{sheet} {key}")

        # Open positions: each wallet's coins and actual cost basis (R04), and the formulas that use the prices of the Input sheet.
        exchange_rows = read_sheet_rows(Path(f"{prefix}open_positions.ods"), "Asset - Exchange") or []
        got_wallets: List[List[str]] = [row[:6] for row in exchange_rows[3:9]]
        want_wallets: List[List[str]] = [
            ["B1", "Bob", "BlockFi", "0.5", "120.8", "60.4"],
            ["B1", "Bob", "Coinbase", "0.9", "400.0", "360.0"],
            ["B1", "Bob", "Kraken", "0.6", "101.0", "60.6"],
            ["B2", "Bob", "Coinbase", "2.0", "70.0", "140.0"],
            ["B3", "Bob", "BlockFi", "5.0", "10.0", "50.0"],
            ["B4", "Bob", "Kraken", "2.0", "20.0", "40.0"],
        ]
        self.assertEqual(got_wallets, want_wallets)
        # Kraken's B1 row (row 6): value = coins * price, gain = value - cost basis; the total covers the six wallets (rows 4 to 9).
        got_formulas: List[str] = exchange_rows[5][8:11] + [exchange_rows[9][5]]
        want_formulas: List[str] = ["=D6*H6", "=I6-F6", "=(I6-F6)/F6", "=SUM(F$4:F$9)"]
        self.assertEqual(got_formulas, want_formulas)

        # Opening allocation (R10): every sheet, for B1 (configured rule), B2 (per-asset override) and B3 (automatic); B4 has nothing to
        # allocate. The switch is midnight in New York.
        switch = ["2025-01-01T00:00:00-05:00", "America/New_York"]
        want_allocation: Dict[str, List[List[str]]] = {
            "Summary": [
                ["B1", *switch, "Configured", "FIFO", "unused_basis_allocation_method", "Kraken/Bob, BlockFi/Bob, Coinbase/Bob"]
                + ["unused_basis_allocation_wallet_order", "5.4", "5.4", "5.4", "1042.4", "1042.4"],
                ["B2", *switch, "Configured", "HIFO", "unused_basis_allocation_method.B2", "Coinbase/Bob, Kraken/Bob"]
                + ["unused_basis_allocation_wallet_order.B2", "3.0", "3.0", "3.0", "190.0", "190.0"],
                ["B3", *switch, "Automatic", "FIFO", "unused_basis_allocation_method", "BlockFi/Bob", "", "5.0", "5.0", "5.0", "50.0", "50.0"],
            ],
            "Wallets": [
                ["B1", "1.0", "Kraken", "Bob", "1.5", "1.5", "151.5", "1.0"],
                ["B1", "2.0", "BlockFi", "Bob", "1.0", "1.0", "110.9", "2.0"],
                ["B1", "3.0", "Coinbase", "Bob", "2.9", "2.9", "780.0", "2.0"],
                ["Total B1", "", "", "", "5.4", "5.4", "1042.4", "5.0"],
                ["B2", "1.0", "Coinbase", "Bob", "2.0", "2.0", "140.0", "2.0"],
                ["B2", "2.0", "Kraken", "Bob", "1.0", "1.0", "50.0", "1.0"],
                ["Total B2", "", "", "", "3.0", "3.0", "190.0", "3.0"],
                ["B3", "1.0", "BlockFi", "Bob", "5.0", "5.0", "50.0", "1.0"],
                ["Total B3", "", "", "", "5.0", "5.0", "50.0", "1.0"],
            ],
            "Unused Lots": [
                ["B1", "1.0", "i1", "3.0", "2024-01-10", "Coinbase", "Bob", "BUY", "100.0", "3.0", "2.4", "101.0", "242.4"],
                ["B1", "2.0", "i2", "4.0", "2024-03-15", "Kraken", "Bob", "BUY", "200.0", "2.0", "2.0", "200.0", "400.0"],
                ["B1", "3.0", "i3", "5.0", "2024-12-31", "Coinbase", "Bob", "BUY", "400.0", "1.0", "1.0", "400.0", "400.0"],
                ["Total B1", "", "", "", "", "", "", "", "", "", "5.4", "", "1042.4"],
                ["B2", "1.0", "j2", "4.0", "2024-05-01", "Kraken", "Bob", "BUY", "80.0", "1.0", "1.0", "80.0", "80.0"],
                ["B2", "2.0", "j3", "5.0", "2024-07-01", "Kraken", "Bob", "BUY", "60.0", "1.0", "1.0", "60.0", "60.0"],
                ["B2", "3.0", "j1", "3.0", "2024-02-01", "Coinbase", "Bob", "BUY", "50.0", "1.0", "1.0", "50.0", "50.0"],
                ["Total B2", "", "", "", "", "", "", "", "", "", "3.0", "", "190.0"],
                ["B3", "1.0", "k1", "3.0", "2024-04-01", "BlockFi", "Bob", "BUY", "10.0", "5.0", "5.0", "10.0", "50.0"],
                ["Total B3", "", "", "", "", "", "", "", "", "", "5.0", "", "50.0"],
            ],
            "Allocation": [
                ["B1", "Kraken", "Bob", "i1", "3.0", "2024-01-10", "1.5", "101.0", "151.5"],
                ["B1", "BlockFi", "Bob", "i1", "3.0", "2024-01-10", "0.9", "101.0", "90.9"],
                ["B1", "BlockFi", "Bob", "i2", "4.0", "2024-03-15", "0.1", "200.0", "20.0"],
                ["B1", "Coinbase", "Bob", "i2", "4.0", "2024-03-15", "1.9", "200.0", "380.0"],
                ["B1", "Coinbase", "Bob", "i3", "5.0", "2024-12-31", "1.0", "400.0", "400.0"],
                ["Total B1", "", "", "", "", "", "5.4", "", "1042.4"],
                ["B2", "Coinbase", "Bob", "j2", "4.0", "2024-05-01", "1.0", "80.0", "80.0"],
                ["B2", "Coinbase", "Bob", "j3", "5.0", "2024-07-01", "1.0", "60.0", "60.0"],
                ["B2", "Kraken", "Bob", "j1", "3.0", "2024-02-01", "1.0", "50.0", "50.0"],
                ["Total B2", "", "", "", "", "", "3.0", "", "190.0"],
                ["B3", "BlockFi", "Bob", "k1", "3.0", "2024-04-01", "5.0", "10.0", "50.0"],
                ["Total B3", "", "", "", "", "", "5.0", "", "50.0"],
            ],
        }
        for sheet, want_rows_list in want_allocation.items():
            got_rows_list: List[List[str]] = (read_sheet_rows(Path(f"{prefix}opening_allocation.ods"), sheet) or [])[3:]
            self.assertEqual(got_rows_list, want_rows_list, msg=sheet)

        # Full report, B1 Tax sheet: yearly totals (year, asset, gain, term, type, coins, proceeds, cost basis) and account balances
        # (acquired, sent, received, final).
        tax_rows = read_sheet_rows(Path(f"{prefix}rp2_full_report.ods"), "B1 Tax") or []
        got_summary: List[List[str]] = tax_rows[3:11]
        want_summary: List[List[str]] = [
            ["2026.0", "B1", "60.0", "SHORT", "SELL", "0.2", "180.0", "120.0"],
            ["2026.0", "B1", "639.2", "LONG", "SELL", "0.8", "720.0", "80.8"],
            ["2025.0", "B1", "120.0", "SHORT", "STAKING", "0.2", "120.0", "0"],
            ["2025.0", "B1", "30.0", "SHORT", "SELL", "0.1", "70.0", "40.0"],
            ["2025.0", "B1", "1299.5", "LONG", "SELL", "2.4", "1730.0", "430.5"],
            ["2025.0", "B1", "39.9", "LONG", "MOVE", "0.1", "50.0", "10.1"],
            ["2024.0", "B1", "99.5", "SHORT", "SELL", "0.5", "150.0", "50.5"],
            ["2024.0", "B1", "14.9", "SHORT", "MOVE", "0.1", "25.0", "10.1"],
        ]
        self.assertEqual(got_summary, want_summary)
        got_balances: List[List[str]] = [row[:7] for row in tax_rows if row[:1] in (["BlockFi"], ["Coinbase"], ["Kraken"])]
        want_balances: List[List[str]] = [
            ["BlockFi", "Bob", "B1", "0", "1.4", "1.9", "0.5"],
            ["Coinbase", "Bob", "B1", "4.0", "3.1", "0", "0.9"],
            ["Kraken", "Bob", "B1", "2.2", "2.5", "0.9", "0.6"],
        ]
        self.assertEqual(got_balances, want_balances)
        # Gain / Loss Detail: every taxable event is a link to its row of the In-Out sheet, and every lot shows the timestamp of the original
        # acquisition (also when the coins came from the allocation or a transfer). The links and ids of artificial lots are R17's.
        document: Any = ezodf.opendoc(f"{prefix}rp2_full_report.ods")
        tax_sheet = document.sheets["B1 Tax"]
        detail_rows = [index for index in range(tax_sheet.nrows()) if tax_sheet[index, 1].value == "B1" and tax_sheet[index, 5].formula]
        got_events: List[Tuple[str, str]] = []
        for index in detail_rows:
            timestamp_cell = tax_sheet[index, 12]
            lot_timestamp = timestamp_cell.formula.split(";")[1].strip(' ")') if timestamp_cell.formula else timestamp_cell.value
            self.assertTrue(tax_sheet[index, 5].formula.startswith('=HYPERLINK("#B1 In-Out.'), msg=f"row {index}")
            got_events.append((tax_sheet[index, 10].formula.split(";")[1].strip(' ")'), lot_timestamp or ""))
        want_events: List[Tuple[str, str]] = [
            ("t1", "2024-01-10 15:00:00+00:00"),
            ("o1", "2024-01-10 15:00:00+00:00"),
            ("t2", "2024-01-10 15:00:00+00:00"),
            ("s1", ""),
            ("o2", "2024-03-15 15:00:00+00:00"),
            ("o2", "2025-01-01 03:00:00+00:00"),
            ("o3", "2024-01-10 15:00:00+00:00"),
            ("o4", "2025-04-01 15:00:00+00:00"),
            ("o4", "2024-01-10 15:00:00+00:00"),
            ("o4", "2024-01-10 15:00:00+00:00"),
        ]
        self.assertEqual(got_events, want_events)

    # The golden dataset from the command line, in cases that must not use (or can't use) per-wallet application.
    def test_per_wallet_golden_dataset_cli_cases(self) -> None:
        config_text = (CONFIG_PATH / Path(f"{_GOLDEN_DATASET}.ini")).read_text(encoding="utf-8")
        country_section = config_text[config_text.index("[country.us]") :]
        timezone_only = config_text.replace(country_section, "[country.us]\ntimezone = America/New_York\n")
        input_path = INPUT_PATH / Path(f"{_GOLDEN_DATASET}.ods")
        for name, text, extra_arguments, want_error in [
            # Three wallets hold B1 at the switch: the rule is needed.
            ("no allocation rule", timezone_only, [], "Unused basis allocation is needed at 2025-01-01 00:00:00-05:00 (3 wallets hold B1 funds"),
            ("no country section", config_text.replace(country_section, ""), [], "has transactions or holdings in 2025 or later"),
            # A report that ends in 2024 uses universal application and needs no per-wallet settings.
            ("report ending in 2024", config_text.replace(country_section, ""), ["-t", "2024-12-31"], ""),
        ]:
            with self.subTest(name=name):
                config_path = self.config_dir / Path(f"{_GOLDEN_DATASET}_{name.replace(' ', '_')}.ini")
                config_path.write_text(text, encoding="utf-8")
                output_dir = self.output_dir / Path(name.replace(" ", "_"))
                result = run(
                    ["rp2_us", "-o", str(output_dir), *extra_arguments, str(config_path), str(input_path)], check=False, capture_output=True, text=True
                )
                if want_error:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(want_error, result.stdout + result.stderr)
                    continue
                self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
                self.assertNotIn("per-wallet application from", result.stdout + result.stderr)
                self.assertFalse((output_dir / Path("mixed_opening_allocation.ods")).exists())
                # Only the 2024 disposals are reported: the sale o1 and the fee of t1, both paid with i1 (FIFO).
                got_rows: List[List[str]] = [
                    row[:6] + row[13:15]
                    for sheet in ("Capital Gains", "Investment Expenses")
                    for row in read_sheet_rows(output_dir / Path("mixed_tax_report_us.ods"), sheet) or []
                    if len(row) > 14 and row[1] == "B1"
                ]
                want_rows: List[List[str]] = [
                    ["0.5", "B1", "01/10/2024", "09/01/2024", "150.0", "50.5", "o1", "SHORT"],
                    ["0.1", "B1", "01/10/2024", "06/01/2024", "25.0", "10.1", "t1", "SHORT"],
                ]
                self.assertEqual(got_rows, want_rows)

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

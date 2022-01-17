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

import os
import shutil
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List

import ezodf
from abstract_test_ods_output_diff import AbstractTestODSOutputDiff, OutputPlugins
from dateutil.tz import gettz

ROOT_PATH: Path = Path(os.path.dirname(__file__)).parent.absolute()


class TestLargeInput(AbstractTestODSOutputDiff):

    output_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.output_dir = ROOT_PATH / Path("output") / Path(cls.__module__)

        shutil.rmtree(cls.output_dir, ignore_errors=True)

        cls._generate_large_input(cls.output_dir)
        for method in AbstractTestODSOutputDiff.METHODS:
            AbstractTestODSOutputDiff._generate(
                cls.output_dir, test_name="test_large_input", config="test_large_input", method=method, input_path=cls.output_dir
            )

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    @staticmethod
    def _fill_row(sheet: Any, row_index: int, row: List[Any]) -> int:

        for col_index, element in enumerate(row):
            sheet[row_index, col_index].set_value(element)
        return row_index + 1

    @classmethod
    def _generate_large_input(cls, output_dir: Path) -> None:
        output_file_path: Path = output_dir / Path("test_large_input.ods")
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        if not output_dir.is_dir():
            raise Exception(f"output_dir '{str(output_dir)}' exists but it's not a directory")

        output_file: Any = ezodf.newdoc("ods", str(output_file_path), template=None)
        row_index: int = 0
        timestamp: datetime = datetime(2015, 1, 1, 1, 1, 1, 0, tzinfo=gettz("UTC"))
        asset: str = "B1"
        exchanges: List[str] = ["Coinbase", "Kraken"]
        holders: List[str] = ["Alice", "Bob"]
        in_type: List[str] = ["buy", "interest"]
        out_type: List[str] = ["sell", "donate"]

        column_total: int = 30
        table_row_total: int = 200 if "RP2_TEST_TABLE_SIZE" not in os.environ else int(str(os.environ.get("RP2_TEST_TABLE_SIZE")))

        sheet: Any = ezodf.Table("B1")
        output_file.sheets += sheet

        sheet.reset(size=(table_row_total * 2 + 100, column_total))

        row_index = cls._fill_row(sheet, row_index, ["IN"])
        row_index = cls._fill_row(
            sheet,
            row_index,
            [
                "timestamp",
                "asset",
                "exchange",
                "holder",
                "type",
                "spot",
                "crypto in",
                "fiat fee",
                "notes",
            ],
        )
        for i in range(0, table_row_total):
            row_index = cls._fill_row(
                sheet,
                row_index,
                [
                    timestamp,
                    asset,
                    exchanges[int(i / 5) % 2],
                    holders[int(i / 10) % 2],
                    in_type[int(i / 10) % 2],
                    float(1 + i % 10) / 10,
                    1 + i % 5,
                    0,
                ],
            )
            if i < table_row_total * 0.93:
                timestamp += timedelta(minutes=1)
        row_index = cls._fill_row(sheet, row_index, ["TABLE END"])

        row_index = cls._fill_row(sheet, row_index, [""])

        row_index = cls._fill_row(sheet, row_index, ["OUT"])
        row_index = cls._fill_row(
            sheet,
            row_index,
            [
                "timestamp",
                "asset",
                "exchange",
                "holder",
                "type",
                "spot",
                "crypto out",
                "crypto fee",
                "notes",
            ],
        )
        for i in range(0, table_row_total):
            row_index = cls._fill_row(
                sheet,
                row_index,
                [
                    timestamp,
                    asset,
                    exchanges[int(i / 5) % 2],
                    holders[int(i / 10) % 2],
                    out_type[int(i / 10) % 2],
                    float(1 + i % 10) / 10,
                    float(1 + i % 10) / 20,
                    0,
                ],
            )
            if i < table_row_total * 0.80:
                timestamp += timedelta(minutes=1)
        row_index = cls._fill_row(sheet, row_index, ["TABLE END"])

        output_file.save()

    def test_large_input_rp2_full_report(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_large_input", method=method, output_plugin=OutputPlugins.RP2_FULL_REPORT)

    def test_large_input_tax_report_us(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_large_input", method=method, output_plugin=OutputPlugins.TAX_REPORT_US)


if __name__ == "__main__":
    unittest.main()

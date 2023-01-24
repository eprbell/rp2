# Copyright 2022 Neal Chambers
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

from abstract_test_ods_output_diff import AbstractTestODSOutputDiff, OutputPlugins

ROOT_PATH: Path = Path(os.path.dirname(__file__)).parent.absolute()


class TestODSOutputDiff(AbstractTestODSOutputDiff):  # pylint: disable=too-many-public-methods

    output_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.output_dir = ROOT_PATH / Path("output") / Path(cls.__module__)

        shutil.rmtree(cls.output_dir, ignore_errors=True)

        AbstractTestODSOutputDiff._generate(
            cls.output_dir, test_name="crypto_example", config="crypto_example", method="fifo", country="jp", generation_language="en"
        )
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_data", config="test_data", method="fifo", country="jp", generation_language="en")
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_data2", config="test_data", method="fifo", country="jp", generation_language="en")
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_data3", config="test_data", method="fifo", country="jp", generation_language="en")
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_data4", config="test_data4", method="fifo", country="jp", generation_language="en")
        AbstractTestODSOutputDiff._generate(
            cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", country="jp", generation_language="en"
        )

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_crypto_example_rp2_full_report(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="crypto_example",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.RP2_FULL_REPORT,
            generation_language="en",
        )

    def test_crypto_example_tax_report_jp(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="crypto_example",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.TAX_REPORT_JP,
            generation_language="en",
        )

    def test_test_data_rp2_full_report(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_data",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.RP2_FULL_REPORT,
            generation_language="en",
        )

    def test_test_data_tax_report_jp(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_data",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.TAX_REPORT_JP,
            generation_language="en",
        )

    def test_test_data2_rp2_full_report(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_data2",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.RP2_FULL_REPORT,
            generation_language="en",
        )

    def test_test_data2_tax_report_jp(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_data2",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.TAX_REPORT_JP,
            generation_language="en",
        )

    def test_test_data3_rp2_full_report(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_data3",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.RP2_FULL_REPORT,
            generation_language="en",
        )

    def test_test_data3_tax_report_jp(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_data3",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.TAX_REPORT_JP,
            generation_language="en",
        )

    def test_test_data4_rp2_full_report(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_data4",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.RP2_FULL_REPORT,
            generation_language="en",
        )

    def test_test_data4_tax_report_jp(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_data4",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.TAX_REPORT_JP,
            generation_language="en",
        )

    def test_test_many_year_data_rp2_full_report(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_many_year_data",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.RP2_FULL_REPORT,
            generation_language="en",
        )

    def test_test_many_year_data_tax_report_jp(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_many_year_data",
            method="fifo",
            country="jp",
            output_plugin=OutputPlugins.TAX_REPORT_JP,
            generation_language="en",
        )


if __name__ == "__main__":
    unittest.main()

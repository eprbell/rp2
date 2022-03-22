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
from datetime import date
from pathlib import Path

from abstract_test_ods_output_diff import AbstractTestODSOutputDiff, OutputPlugins

ROOT_PATH: Path = Path(os.path.dirname(__file__)).parent.absolute()


class TestODSOutputDiff(AbstractTestODSOutputDiff):  # pylint: disable=too-many-public-methods

    output_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.output_dir = ROOT_PATH / Path("output") / Path(cls.__module__)

        shutil.rmtree(cls.output_dir, ignore_errors=True)

        for method in AbstractTestODSOutputDiff.METHODS:
            AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="crypto_example", config="crypto_example", method=method)
            AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_data", config="test_data", method=method)
            AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_data2", config="test_data", method=method)
            AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_data3", config="test_data", method=method)
            AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_data4", config="test_data4", method=method)
            AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_many_year_data", config="test_data", method=method)
            AbstractTestODSOutputDiff._generate(
                cls.output_dir, test_name="test_data3", config="test_data", method=method, from_date=date(2019, 12, 1), to_date=date(2020, 4, 1)
            )

        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", to_date=date(2016, 12, 31))
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", to_date=date(2017, 12, 31))
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", to_date=date(2018, 12, 31))
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", to_date=date(2019, 12, 31))
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", to_date=date(2020, 12, 31))

        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", from_date=date(2017, 1, 1))
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", from_date=date(2018, 1, 1))
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", from_date=date(2019, 1, 1))
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", from_date=date(2020, 1, 1))
        AbstractTestODSOutputDiff._generate(cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", from_date=date(2021, 1, 1))

        AbstractTestODSOutputDiff._generate(
            cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", from_date=date(2017, 1, 1), to_date=date(2019, 12, 31)
        )
        AbstractTestODSOutputDiff._generate(
            cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", from_date=date(2018, 1, 1), to_date=date(2019, 12, 31)
        )
        AbstractTestODSOutputDiff._generate(
            cls.output_dir, test_name="test_many_year_data", config="test_data", method="fifo", from_date=date(2019, 1, 1), to_date=date(2019, 12, 31)
        )

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_crypto_example_rp2_full_report(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="crypto_example", method=method, output_plugin=OutputPlugins.RP2_FULL_REPORT)

    def test_crypto_example_tax_report_us(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="crypto_example", method=method, output_plugin=OutputPlugins.TAX_REPORT_US)

    def test_test_data_rp2_full_report(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_data", method=method, output_plugin=OutputPlugins.RP2_FULL_REPORT)

    def test_test_data_tax_report_us(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_data", method=method, output_plugin=OutputPlugins.TAX_REPORT_US)

    def test_test_data2_rp2_full_report(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_data2", method=method, output_plugin=OutputPlugins.RP2_FULL_REPORT)

    def test_test_data2_tax_report_us(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_data2", method=method, output_plugin=OutputPlugins.TAX_REPORT_US)

    def test_test_data3_rp2_full_report(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_data3", method=method, output_plugin=OutputPlugins.RP2_FULL_REPORT)

    def test_test_data3_tax_report_us(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_data3", method=method, output_plugin=OutputPlugins.TAX_REPORT_US)

    def test_test_data4_rp2_full_report(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_data4", method=method, output_plugin=OutputPlugins.RP2_FULL_REPORT)

    def test_test_data4_tax_report_us(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_data4", method=method, output_plugin=OutputPlugins.TAX_REPORT_US)

    def test_test_many_year_data_rp2_full_report(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_many_year_data", method=method, output_plugin=OutputPlugins.RP2_FULL_REPORT)

    def test_test_many_year_data_tax_report_us(self) -> None:
        for method in self.METHODS:
            self._compare(output_dir=self.output_dir, test_name="test_many_year_data", method=method, output_plugin=OutputPlugins.TAX_REPORT_US)

    def test_test_data3_rp2_full_report_2019_12_01_2020_04_01(self) -> None:
        for method in self.METHODS:
            self._compare(
                output_dir=self.output_dir,
                test_name="test_data3",
                method=method,
                output_plugin=OutputPlugins.RP2_FULL_REPORT,
                from_date=date(2019, 12, 1),
                to_date=date(2020, 4, 1),
            )

    def test_test_data3_tax_report_us_2019_12_01_2020_04_01(self) -> None:
        for method in self.METHODS:
            self._compare(
                output_dir=self.output_dir,
                test_name="test_data3",
                method=method,
                output_plugin=OutputPlugins.TAX_REPORT_US,
                from_date=date(2019, 12, 1),
                to_date=date(2020, 4, 1),
            )

    def test_test_many_year_data_rp2_full_report_0_2016(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.RP2_FULL_REPORT, to_date=date(2016, 12, 31)
        )

    def test_test_many_year_data_tax_report_us_0_2016(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.TAX_REPORT_US, to_date=date(2016, 12, 31)
        )

    def test_test_many_year_data_rp2_full_report_0_2017(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.RP2_FULL_REPORT, to_date=date(2017, 12, 31)
        )

    def test_test_many_year_data_tax_report_us_0_2017(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.TAX_REPORT_US, to_date=date(2017, 12, 31)
        )

    def test_test_many_year_data_rp2_full_report_0_2018(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.RP2_FULL_REPORT, to_date=date(2018, 12, 31)
        )

    def test_test_many_year_data_tax_report_us_0_2018(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.TAX_REPORT_US, to_date=date(2018, 12, 31)
        )

    def test_test_many_year_data_rp2_full_report_0_2019(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.RP2_FULL_REPORT, to_date=date(2019, 12, 31)
        )

    def test_test_many_year_data_tax_report_us_0_2019(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.TAX_REPORT_US, to_date=date(2019, 12, 31)
        )

    def test_test_many_year_data_rp2_full_report_0_2020(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.RP2_FULL_REPORT, to_date=date(2020, 12, 31)
        )

    def test_test_many_year_data_tax_report_us_0_2020(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.TAX_REPORT_US, to_date=date(2020, 12, 31)
        )

    def test_test_many_year_data_rp2_full_report_2017_infinity(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.RP2_FULL_REPORT, from_date=date(2017, 1, 1)
        )

    def test_test_many_year_data_tax_report_us_2017_infinity(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.TAX_REPORT_US, from_date=date(2017, 1, 1)
        )

    def test_test_many_year_data_rp2_full_report_2018_infinity(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.RP2_FULL_REPORT, from_date=date(2018, 1, 1)
        )

    def test_test_many_year_data_tax_report_us_2018_infinity(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.TAX_REPORT_US, from_date=date(2018, 1, 1)
        )

    def test_test_many_year_data_rp2_full_report_2019_infinity(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.RP2_FULL_REPORT, from_date=date(2019, 1, 1)
        )

    def test_test_many_year_data_tax_report_us_2019_infinity(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.TAX_REPORT_US, from_date=date(2019, 1, 1)
        )

    def test_test_many_year_data_rp2_full_report_2020_infinity(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.RP2_FULL_REPORT, from_date=date(2020, 1, 1)
        )

    def test_test_many_year_data_tax_report_us_2020_infinity(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.TAX_REPORT_US, from_date=date(2020, 1, 1)
        )

    def test_test_many_year_data_rp2_full_report_2021_infinity(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.RP2_FULL_REPORT, from_date=date(2021, 1, 1)
        )

    def test_test_many_year_data_tax_report_us_2021_infinity(self) -> None:
        self._compare(
            output_dir=self.output_dir, test_name="test_many_year_data", method="fifo", output_plugin=OutputPlugins.TAX_REPORT_US, from_date=date(2021, 1, 1)
        )

    def test_test_many_year_data_rp2_full_report_2017_2019(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_many_year_data",
            method="fifo",
            output_plugin=OutputPlugins.RP2_FULL_REPORT,
            from_date=date(2017, 1, 1),
            to_date=date(2019, 12, 31),
        )

    def test_test_many_year_data_tax_report_us_2017_2019(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_many_year_data",
            method="fifo",
            output_plugin=OutputPlugins.TAX_REPORT_US,
            from_date=date(2017, 1, 1),
            to_date=date(2019, 12, 31),
        )

    def test_test_many_year_data_rp2_full_report_2018_2019(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_many_year_data",
            method="fifo",
            output_plugin=OutputPlugins.RP2_FULL_REPORT,
            from_date=date(2018, 1, 1),
            to_date=date(2019, 12, 31),
        )

    def test_test_many_year_data_tax_report_us_2018_2019(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_many_year_data",
            method="fifo",
            output_plugin=OutputPlugins.TAX_REPORT_US,
            from_date=date(2018, 1, 1),
            to_date=date(2019, 12, 31),
        )

    def test_test_many_year_data_rp2_full_report_2019_2019(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_many_year_data",
            method="fifo",
            output_plugin=OutputPlugins.RP2_FULL_REPORT,
            from_date=date(2019, 1, 1),
            to_date=date(2019, 12, 31),
        )

    def test_test_many_year_data_tax_report_us_2019_2019(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_many_year_data",
            method="fifo",
            output_plugin=OutputPlugins.TAX_REPORT_US,
            from_date=date(2019, 1, 1),
            to_date=date(2019, 12, 31),
        )


if __name__ == "__main__":
    unittest.main()

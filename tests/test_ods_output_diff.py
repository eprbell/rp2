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
from pathlib import Path
from subprocess import run

from ods_diff import ods_diff

ROOT_PATH: Path = Path(os.path.dirname(__file__)).parent.absolute()

CONFIG_PATH: Path = ROOT_PATH / Path("config")
INPUT_PATH: Path = ROOT_PATH / Path("input")
GOLDEN_PATH: Path = INPUT_PATH / Path("golden")
LOG_PATH: Path = ROOT_PATH / Path("log")
OUTPUT_PATH: Path = ROOT_PATH / Path("output")


# pylint: disable=too-many-public-methods
class TestODSOutputDiff(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Generate output to compare with golden files
        shutil.rmtree(LOG_PATH, ignore_errors=True)
        shutil.rmtree(OUTPUT_PATH, ignore_errors=True)

        # FIFO tests
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "crypto_example_",
                str(CONFIG_PATH / Path("crypto_example.config")),
                str(INPUT_PATH / Path("crypto_example.ods")),
            ],
            check=True,
        )
        run(
            ["rp2_us", "-o", str(OUTPUT_PATH), "-p", "test_data_", str(CONFIG_PATH / Path("test_data.config")), str(INPUT_PATH / Path("test_data.ods"))],
            check=True,
        )
        run(
            ["rp2_us", "-o", str(OUTPUT_PATH), "-p", "test_data2_", str(CONFIG_PATH / Path("test_data.config")), str(INPUT_PATH / Path("test_data2.ods"))],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )

        # LIFO tests
        run(
            [
                "rp2_us",
                "-m",
                "lifo",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "crypto_example_",
                str(CONFIG_PATH / Path("crypto_example.config")),
                str(INPUT_PATH / Path("crypto_example.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-m",
                "lifo",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_data_",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_data.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-m",
                "lifo",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_data2_",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_data2.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-m",
                "lifo",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )

        # Test to_year
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_0_2016_",
                "-t",
                "2016",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_0_2017_",
                "-t",
                "2017",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_0_2018_",
                "-t",
                "2018",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_0_2019_",
                "-t",
                "2019",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_0_2020_",
                "-t",
                "2020",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )

        # Test from_year
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_2017_infinity_",
                "-f",
                "2017",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_2018_infinity_",
                "-f",
                "2018",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_2019_infinity_",
                "-f",
                "2019",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_2020_infinity_",
                "-f",
                "2020",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_2021_infinity_",
                "-f",
                "2021",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )

        # Test both from_year and to_year
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_2017_2019_",
                "-f",
                "2017",
                "-t",
                "2019",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_2018_2019_",
                "-f",
                "2018",
                "-t",
                "2019",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )
        run(
            [
                "rp2_us",
                "-o",
                str(OUTPUT_PATH),
                "-p",
                "test_many_year_data_2019_2019_",
                "-f",
                "2019",
                "-t",
                "2019",
                str(CONFIG_PATH / Path("test_data.config")),
                str(INPUT_PATH / Path("test_many_year_data.ods")),
            ],
            check=True,
        )

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name
        self.generate_ascii_representation = True

    def test_data_fifo_rp2_full_report_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("test_data_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_data_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_data_fifo_tax_report_us_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("test_data_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_data_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_data2_fifo_rp2_full_report_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("test_data2_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_data2_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_data2_fifo_tax_report_us_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("test_data2_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_data2_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_many_year_data_fifo_rp2_full_report_plugin(self) -> None:
        diff: str
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_0_2016_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_0_2016_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_0_2017_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_0_2017_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_0_2018_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_0_2018_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_0_2019_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_0_2019_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_0_2020_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_0_2020_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2017_infinity_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2017_infinity_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2018_infinity_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2018_infinity_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2019_infinity_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2019_infinity_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2020_infinity_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2020_infinity_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2021_infinity_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2021_infinity_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2017_2019_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2017_2019_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2018_2019_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2018_2019_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2019_2019_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2019_2019_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )

    def test_many_year_data_fifo_tax_report_us_plugin(self) -> None:
        diff: str
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_0_2016_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_0_2016_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_0_2017_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_0_2017_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_0_2018_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_0_2018_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_0_2019_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_0_2019_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_0_2020_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_0_2020_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2017_infinity_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2017_infinity_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2018_infinity_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2018_infinity_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2019_infinity_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2019_infinity_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2020_infinity_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2020_infinity_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2021_infinity_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2021_infinity_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2017_2019_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2017_2019_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2018_2019_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2018_2019_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)
        diff = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_2019_2019_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_2019_2019_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_data_lifo_rp2_full_report_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("test_data_lifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_data_lifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_data_lifo_tax_report_us_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("test_data_lifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_data_lifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_data2_lifo_rp2_full_report_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("test_data2_lifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_data2_lifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_data2_lifo_tax_report_us_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("test_data2_lifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_data2_lifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_many_year_data_lifo_rp2_full_report_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_lifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("test_many_year_data_lifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_many_year_data_lifo_tax_report_us_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("test_many_year_data_lifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("test_many_year_data_lifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_crypto_example_fifo_rp2_full_report_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("crypto_example_fifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("crypto_example_fifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_crypto_example_fifo_tax_report_us_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("crypto_example_fifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("crypto_example_fifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_crypto_example_lifo_rp2_full_report_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("crypto_example_lifo_rp2_full_report.ods"),
            OUTPUT_PATH / Path("crypto_example_lifo_rp2_full_report.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)

    def test_crypto_example_lifo_tax_report_us_plugin(self) -> None:
        diff: str = ods_diff(
            GOLDEN_PATH / Path("crypto_example_lifo_tax_report_us.ods"),
            OUTPUT_PATH / Path("crypto_example_lifo_tax_report_us.ods"),
            generate_ascii_representation=self.generate_ascii_representation,
        )
        self.assertFalse(diff, msg=diff)


if __name__ == "__main__":
    unittest.main()

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

import shutil
import unittest
from subprocess import run

from ods_diff import ods_diff


class TestODSOutputDiff(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Generate output to compare with golden files
        shutil.rmtree("./log", ignore_errors=True)
        shutil.rmtree("./output", ignore_errors=True)
        run(["python3", "bin/rp2_tax.py", "-o", "./output/", "-p", "test_data_", "./config/test_data.config", "./input/test_data.ods"], check=True)
        run(["python3", "bin/rp2_tax.py", "-o", "./output/", "-p", "crypto_example_", "./config/crypto_example.config", "./input/crypto_example.ods"], check=True)

    def setUp(self) -> None:
        self.maxDiff = None

    def test_data_tax_report_plugin(self) -> None:
        diff: str = ods_diff(
            "./input/golden/test_data_rp2_report_golden.ods",
            "./output/test_data_rp2_report.ods",
        )
        self.assertFalse(diff, msg=diff)

    def test_data_mock_8949_plugin(self) -> None:
        diff: str = ods_diff(
            "./input/golden/test_data_mock_8949_us_golden.ods",
            "./output/test_data_mock_8949_us.ods",
        )
        self.assertFalse(diff, msg=diff)

    def test_crypto_example_tax_report_plugin(self) -> None:
        diff: str = ods_diff(
            "./input/golden/crypto_example_rp2_report_golden.ods",
            "./output/crypto_example_rp2_report.ods",
        )
        self.assertFalse(diff, msg=diff)

    def test_crypto_example_mock_8949_plugin(self) -> None:
        diff: str = ods_diff(
            "./input/golden/crypto_example_mock_8949_us_golden.ods",
            "./output/crypto_example_mock_8949_us.ods",
        )
        self.assertFalse(diff, msg=diff)


if __name__ == "__main__":
    unittest.main()

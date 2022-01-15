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

from abstract_test_ods_output_diff import AbstractTestODSOutputDiff

ROOT_PATH: Path = Path(os.path.dirname(__file__)).parent.absolute()


class TestODSOutputDiff(AbstractTestODSOutputDiff):

    output_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.output_dir = ROOT_PATH / Path("output") / Path(cls.__module__)

        shutil.rmtree(cls.output_dir, ignore_errors=True)

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name
        self.generate_ascii_representation: bool = True

    def test_crypto_example(self) -> None:
        for method in self.METHODS:
            self._run_and_compare(test_name="crypto_example", config="crypto_example", method=method)

    def test_test_data(self) -> None:
        for method in self.METHODS:
            self._run_and_compare(test_name="test_data", config="test_data", method=method)

    def test_test_data2(self) -> None:
        for method in self.METHODS:
            self._run_and_compare(test_name="test_data2", config="test_data", method=method)

    def test_test_many_year_data(self) -> None:
        for method in self.METHODS:
            self._run_and_compare(test_name="test_many_year_data", config="test_data", method=method)

    def test_test_many_year_data_0_2016(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", to_year=2016)

    def test_test_many_year_data_0_2017(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", to_year=2017)

    def test_test_many_year_data_0_2018(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", to_year=2018)

    def test_test_many_year_data_0_2019(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", to_year=2019)

    def test_test_many_year_data_0_2020(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", to_year=2020)

    def test_test_many_year_data_2017_infinity(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", from_year=2017)

    def test_test_many_year_data_2018_infinity(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", from_year=2018)

    def test_test_many_year_data_2019_infinity(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", from_year=2019)

    def test_test_many_year_data_2020_infinity(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", from_year=2020)

    def test_test_many_year_data_2021_infinity(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", from_year=2021)

    def test_test_many_year_data_2017_2019(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", from_year=2017, to_year=2019)

    def test_test_many_year_data_2018_2019(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", from_year=2018, to_year=2019)

    def test_test_many_year_data_2019_2019(self) -> None:
        self._run_and_compare(test_name="test_many_year_data", config="test_data", method="fifo", from_year=2019, to_year=2019)


if __name__ == "__main__":
    unittest.main()

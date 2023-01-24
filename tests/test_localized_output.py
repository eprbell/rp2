# Copyright 2022 eprbell
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


class TestLocalizedOutput(AbstractTestODSOutputDiff):  # pylint: disable=too-many-public-methods

    output_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.output_dir = ROOT_PATH / Path("output") / Path(cls.__module__)

        shutil.rmtree(cls.output_dir, ignore_errors=True)

        # To test localization plumbing, we generate Japanese taxes for test_data in Kalaallisut language. Note that the localization
        # file (locales/kl/LC_MESSAGES/messages.po) doesn't contain real Kalaallisut translations, but only placeholder strings starting
        # with "__test_": this is good enough to test localization plumbing (and it would work in the same way with a real translation).
        cls._generate(cls.output_dir, test_name="test_data", config="test_data", method="fifo", generation_language="kl", country="jp")

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_test_data_rp2_full_report(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_data",
            method="fifo",
            output_plugin=OutputPlugins.RP2_FULL_REPORT,
            generation_language="kl",
            country="jp",
        )

    def test_test_data_open_positions(self) -> None:
        self._compare(
            output_dir=self.output_dir,
            test_name="test_data",
            method="fifo",
            output_plugin=OutputPlugins.OPEN_POSITIONS,
            generation_language="kl",
            country="jp",
        )


if __name__ == "__main__":
    unittest.main()

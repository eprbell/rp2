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
import unittest
from pathlib import Path
from subprocess import run
from typing import List, Optional

from ods_diff import ods_diff

ROOT_PATH: Path = Path(os.path.dirname(__file__)).parent.absolute()

CONFIG_PATH: Path = ROOT_PATH / Path("config")
INPUT_PATH: Path = ROOT_PATH / Path("input")
GOLDEN_PATH: Path = INPUT_PATH / Path("golden")

OUTPUT_PLUGINS: List[str] = ["rp2_full_report", "tax_report_us"]


class AbstractTestODSOutputDiff(unittest.TestCase):

    METHODS: List[str] = ["fifo", "lifo"]
    output_dir: Path

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name
        self.generate_ascii_representation: bool = True

    def _run_and_compare(
        self, test_name: str, config: str, method: str, input_path: Path = INPUT_PATH, to_year: Optional[int] = None, from_year: Optional[int] = None
    ) -> None:
        config = test_name if config is None else config
        time_interval: str = ""
        if from_year and to_year:
            time_interval = f"{from_year}_{to_year}_"
        elif from_year and not to_year:
            time_interval = f"{from_year}_infinity_"
        elif not from_year and to_year:
            time_interval = f"0_{to_year}_"

        arguments: List[str] = [
            "rp2_us",
            "-m",
            method,
            "-o",
            str(self.output_dir),
            "-p",
            f"{test_name}_{time_interval}",
        ]
        if from_year:
            arguments.extend(["-f", str(from_year)])
        if to_year:
            arguments.extend(["-t", str(to_year)])
        arguments.extend(
            [
                str(CONFIG_PATH / Path(f"{config}.config")),
                str(input_path / Path(f"{test_name}.ods")),
            ]
        )

        run(arguments, check=True)

        for output_plugin in OUTPUT_PLUGINS:
            diff: str
            output_file_name: Path = Path(f"{test_name}_{time_interval}{method}_{output_plugin}.ods")
            full_output_file_name: Path = self.output_dir / output_file_name
            full_golden_file_name: Path = GOLDEN_PATH / output_file_name
            diff = ods_diff(full_golden_file_name, full_output_file_name, generate_ascii_representation=self.generate_ascii_representation)
            self.assertFalse(diff, msg=diff)

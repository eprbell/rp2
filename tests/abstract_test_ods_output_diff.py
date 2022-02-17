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
from datetime import date
from enum import Enum
from pathlib import Path
from subprocess import run
from typing import List

from ods_diff import ods_diff

from rp2.configuration import MAX_DATE, MIN_DATE

ROOT_PATH: Path = Path(os.path.dirname(__file__)).parent.absolute()

CONFIG_PATH: Path = ROOT_PATH / Path("config")
INPUT_PATH: Path = ROOT_PATH / Path("input")
GOLDEN_PATH: Path = INPUT_PATH / Path("golden")


class OutputPlugins(Enum):
    RP2_FULL_REPORT = "rp2_full_report"
    TAX_REPORT_US = "tax_report_us"


class AbstractTestODSOutputDiff(unittest.TestCase):

    METHODS: List[str] = ["fifo", "lifo"]

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    @staticmethod
    def __get_time_interval(from_date: date = MIN_DATE, to_date: date = MAX_DATE) -> str:
        time_interval: str = ""
        if from_date > MIN_DATE and to_date < MAX_DATE:
            time_interval = f"{from_date}_{to_date}_"
        elif from_date > MIN_DATE and to_date >= MAX_DATE:
            time_interval = f"{from_date}_infinity_"
        elif from_date <= MIN_DATE and to_date < MAX_DATE:
            time_interval = f"0_{to_date}_"
        return time_interval

    @classmethod
    def _generate(
        cls,
        output_dir: Path,
        test_name: str,
        config: str,
        method: str,
        input_path: Path = INPUT_PATH,
        from_date: date = MIN_DATE,
        to_date: date = MAX_DATE,
    ) -> None:
        config = test_name if config is None else config
        time_interval: str = cls.__get_time_interval(from_date, to_date)

        arguments: List[str] = [
            "rp2_us",
            "-m",
            method,
            "-o",
            str(output_dir),
            "-p",
            f"{test_name}_{time_interval}",
        ]
        if from_date:
            arguments.extend(["-f", str(from_date)])
        if to_date:
            arguments.extend(["-t", str(to_date)])
        arguments.extend(
            [
                str(CONFIG_PATH / Path(f"{config}.config")),
                str(input_path / Path(f"{test_name}.ods")),
            ]
        )

        run(arguments, check=True)

    def _compare(
        self, output_dir: Path, test_name: str, method: str, output_plugin: OutputPlugins, from_date: date = MIN_DATE, to_date: date = MAX_DATE
    ) -> None:
        time_interval: str = self.__get_time_interval(from_date, to_date)
        diff: str
        output_file_name: Path = Path(f"{test_name}_{time_interval}{method}_{output_plugin.value}.ods")
        full_output_file_name: Path = output_dir / output_file_name
        full_golden_file_name: Path = GOLDEN_PATH / output_file_name
        diff = ods_diff(full_golden_file_name, full_output_file_name, generate_ascii_representation=True)
        self.assertFalse(diff, msg=diff)

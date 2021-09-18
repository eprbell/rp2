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

from argparse import ArgumentParser, Namespace
from difflib import unified_diff
from itertools import zip_longest
from pathlib import Path
from typing import Any, List

import ezodf
from rp2.rp2_decimal import CRYPTO_DECIMALS


def _row_as_string(row: Any) -> str:
    values: List[str] = []
    cell: Any
    for cell in row:
        value: Any = str(_parse_cell_value(cell))
        values.append(value)

    # Remove trailing whitespace from row
    i: int
    for i in range(len(values) - 1, -1, -1):
        if not values[i]:
            del values[i]
        else:
            break

    return ",".join(values)


def _parse_cell_value(cell: Any) -> Any:
    value: Any
    try:
        if cell.value or cell.value == 0:
            value = round(float(cell.value), CRYPTO_DECIMALS)
            if value == -0.0:
                value = 0
        else:
            value = ""
    except ValueError:
        value = cell.value

    return value


def ods_diff(file1_path: Path, file2_path: Path) -> str:

    if not file1_path.exists():
        return f"Error: {file1_path} does not exist"
    if not file2_path.exists():
        return f"Error: {file2_path} does not exist"

    file1: Any = ezodf.opendoc(str(file1_path))
    file2: Any = ezodf.opendoc(str(file2_path))
    sheet1: Any
    sheet2: Any

    contents1: List[str] = []
    contents2: List[str] = []
    for sheet1 in file1.sheets:
        if sheet1.name not in file2.sheets.names():
            contents2.append(f"{sheet1.name}: sheet not found in '{file2_path}'")
            continue
        sheet2 = file2.sheets[sheet1.name]
        contents1.append(sheet1.name)
        contents2.append(sheet1.name)

        row1: Any = None
        row2: Any = None
        for _, (row1, row2) in enumerate(zip_longest(sheet1.rows(), sheet2.rows())):
            if row1:
                contents1.append(_row_as_string(row1))
            if row2:
                contents2.append(_row_as_string(row2))

    for sheet2 in file2.sheets:
        if sheet2.name not in file1.sheets.names():
            contents1.append(f"{sheet2.name}: sheet not found in '{file1_path}'")

    return "\n".join(unified_diff(contents1, contents2, lineterm=""))


def main() -> None:

    parser: ArgumentParser = ArgumentParser(description="Generate yearly capital gain/loss report and account balances for crypto holdings.")
    parser.add_argument(
        "ods_file1",
        action="store",
        help="First ODS file",
        metavar="ODS_FILE1",
        type=str,
    )
    parser.add_argument(
        "ods_file2",
        action="store",
        help="Second ODS file",
        metavar="ODS_FILE2",
        type=str,
    )

    args: Namespace = parser.parse_args()
    print(ods_diff(Path(args.ods_file1), Path(args.ods_file2)))


if __name__ == "__main__":
    main()

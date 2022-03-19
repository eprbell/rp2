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
from tempfile import NamedTemporaryFile
from typing import Any, List

import ezodf

from rp2.rp2_decimal import CRYPTO_DECIMALS

_PURGE_HYPERLIKS = True


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
    if cell.formula:
        value = cell.formula
        if _PURGE_HYPERLIKS and value.startswith("=HYPERLINK"):
            value = value.split(";")[1].lstrip(' "').rstrip('")')
    elif cell.value or cell.value == 0:
        value = cell.value
    else:
        value = ""
    try:
        value = round(float(value), CRYPTO_DECIMALS)
        if value == -0.0:
            value = 0
    except ValueError:
        pass

    if value is None:
        value = ""

    return value


def ods_diff(file1_path: Path, file2_path: Path, generate_ascii_representation: bool) -> str:  # pylint: disable=too-many-branches

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
    row_count1: int = 0
    row_count2: int = 0
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
            string_row: str
            if row1:
                string_row = _row_as_string(row1)
                if string_row:
                    contents1.append(string_row)
                    row_count1 += 1
            if row2:
                string_row = _row_as_string(row2)
                if string_row:
                    contents2.append(string_row)
                    row_count2 += 1

    if row_count1 <= 0 or row_count2 <= 0:
        return f"Error: {file1_path} has no data in common with {file2_path}"

    for sheet2 in file2.sheets:
        if sheet2.name not in file1.sheets.names():
            contents1.append(f"{sheet2.name}: sheet not found in '{file1_path}'")

    if generate_ascii_representation:
        for file_path, contents in zip([file1_path, file2_path], [contents1, contents2]):
            with NamedTemporaryFile(mode="w", delete=False) as temp_file:
                temp_file.write("\n".join(contents))
                temp_file.flush()
                print(f"ASCII representation of {file_path}: {temp_file.name}")

    return "\n".join(unified_diff(contents1, contents2, lineterm=""))


def main() -> None:

    parser: ArgumentParser = ArgumentParser(description="Generate yearly capital gain/loss report and account balances for crypto holdings.")
    parser.add_argument(
        "-a",
        "--ascii-representation",
        action="store_true",
        help="Save ASCII representation of ODS files in temporary directory",
    )
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
    print(ods_diff(Path(args.ods_file1), Path(args.ods_file2), generate_ascii_representation=args.ascii_representation))


if __name__ == "__main__":
    main()

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

from difflib import unified_diff
from itertools import zip_longest
from pathlib import Path
from typing import Any, List

import ezodf

from configuration import Configuration


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
        if cell.value:
            value = round(float(cell.value), Configuration.NUMERIC_PRECISION)
        else:
            value = ""
    except ValueError:
        value = cell.value

    return value


def ods_diff(file1_path: str, file2_path: str) -> str:

    if not Path(file1_path).exists():
        return f"Error: {file1_path} does not exist"
    if not Path(file2_path).exists():
        return f"Error: {file2_path} does not exist"

    file1: Any = ezodf.opendoc(file1_path)
    file2: Any = ezodf.opendoc(file2_path)
    sheet1: Any
    sheet2: Any

    contents1: List[str] = []
    contents2: List[str] = []
    for sheet1 in file1.sheets:
        if not sheet1.name in file2.sheets.names():
            contents2.append(f"{sheet1.name}: sheet not found in '{file2_path}'")
            continue
        sheet2 = file2.sheets[sheet1.name]
        contents1.append(sheet1.name)
        contents2.append(sheet1.name)

        i: int = 0
        row1: Any = None
        row2: Any = None
        for i, (row1, row2) in enumerate(zip_longest(sheet1.rows(), sheet2.rows())):
            if row1:
                contents1.append(_row_as_string(row1))
            if row2:
                contents2.append(_row_as_string(row2))

    for sheet2 in file2.sheets:
        if not sheet2.name in file1.sheets.names():
            contents1.append(f"{sheet2.name}: sheet not found in '{file1_path}'")

    return "\n".join(unified_diff(contents1, contents2, lineterm=""))

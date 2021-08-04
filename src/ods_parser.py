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

from pathlib import Path
from typing import Any, Dict, List, Optional

import ezodf

from abstract_transaction import AbstractTransaction
from configuration import Configuration
from entry_types import EntrySetType
from in_transaction import InTransaction
from input_data import InputData
from intra_transaction import IntraTransaction
from out_transaction import OutTransaction
from rp2_error import RP2ValueError
from transaction_set import TransactionSet

_TABLE_END: str = "TABLE END"


def parse_ods(configuration: Configuration, asset: str, input_file_path: str) -> InputData:

    Configuration.type_check("configuration", configuration)
    configuration.type_check_asset("asset", asset)
    configuration.type_check_string("input_file_path", input_file_path)

    if not Path(input_file_path).exists():
        raise RP2ValueError(f"Error: {input_file_path} does not exist")

    input_file: Any = ezodf.opendoc(input_file_path)
    if asset not in input_file.sheets.names():
        raise RP2ValueError(f"Error: sheet {asset} does not exist in {input_file_path}")
    input_sheet: Any = input_file.sheets[asset]

    transaction_sets: Dict[EntrySetType, TransactionSet] = dict()

    transaction_sets[EntrySetType.IN] = TransactionSet(configuration, "IN", asset)
    transaction_sets[EntrySetType.OUT] = TransactionSet(configuration, "OUT", asset)
    transaction_sets[EntrySetType.INTRA] = TransactionSet(configuration, "INTRA", asset)

    current_table_type: Optional[EntrySetType] = None
    current_table_row_count: int = 0
    i: int = 0
    row: Any = None
    for i, row in enumerate(input_sheet.rows()):
        cell0_value: str = row[0].value
        row_values: List[Any] = [cell.value for cell in row]
        transaction: AbstractTransaction
        if current_table_type is not None:
            # Inside a table
            if _is_table_begin(cell0_value):
                # Found a nested table begin
                raise RP2ValueError(f'{asset}({i + 1}): Found "{cell0_value}" keyword while parsing table {current_table_type}')
            if _is_empty(cell0_value):
                # Found an empty cell inside a table
                raise RP2ValueError(f"{asset}({i + 1}): Found an empty cell while parsing table {current_table_type}")

        else:
            # Outside a table
            if _is_table_end(cell0_value):
                # Found a spurious table end
                raise RP2ValueError(f"{asset}({i + 1}): Found end-table keyword without having found a table-begin keyword first")
            if not _is_empty(cell0_value) and not _is_table_begin(cell0_value):
                # Found a non-empty and non-table-begin cell outside a table
                raise RP2ValueError(f'{asset}({i + 1}): Found an invalid cell "{cell0_value}" while looking for a table-begin token')

        if _is_table_begin(cell0_value):
            # New table start
            current_table_row_count = 0
            current_table_type = _get_entry_set_type(cell0_value)
            if current_table_type and not transaction_sets[current_table_type].is_empty():
                # Found an already-processed table type
                raise RP2ValueError(f"{asset}({i + 1}): Found more than one {cell0_value} symbol")
        elif _is_table_end(cell0_value):
            # Table end
            current_table_type = None
        elif current_table_type is not None and current_table_row_count == 1:
            # Header line: make sure it's not transaction data
            try:
                transaction = _create_transaction(configuration, current_table_type, i, row_values)
            except:
                # Couldn't create transaction as expected: this is a table header
                # TODO: this could still be a transaction but with some bad fields that would
                # cause an exception. In this case this logic would incorrectly assume it's a
                # header. Can we do better in this case? Some heuristics testing field by
                # field would help
                pass
            else:
                raise RP2ValueError(f"{asset}({i + 1}): Found data with no header")
        elif current_table_type is not None and current_table_row_count > 1:
            # Transaction line
            transaction = _create_transaction(configuration, current_table_type, i, row_values)
            if not configuration.up_to_year or transaction.timestamp.year <= configuration.up_to_year:
                # Add transaction if up_to_year was not specified on the cli or if it was specified
                # and the transaction is dated before the up_to_year value
                transaction_sets[current_table_type].add_entry(transaction)
        current_table_row_count += 1

    if current_table_type is not None:
        raise RP2ValueError(f"TABLE END not found for {current_table_type} table")
    if transaction_sets[EntrySetType.IN].is_empty():
        raise RP2ValueError(f"{asset}: IN table not found or empty")

    return InputData(asset, transaction_sets[EntrySetType.IN], transaction_sets[EntrySetType.OUT], transaction_sets[EntrySetType.INTRA])


def _create_transaction(
    configuration: Configuration,
    entry_set_type: EntrySetType,
    line: int,
    row_values: List[Any],
) -> AbstractTransaction:
    transaction: AbstractTransaction
    EntrySetType.type_check("entry_set_type", entry_set_type)
    configuration.type_check_line("line", line)
    if entry_set_type == EntrySetType.IN:
        argument_pack: Dict[str, Any] = configuration.get_in_table_constructor_argument_pack(row_values)
        argument_pack.update({"configuration": configuration, "line": line})
        transaction = InTransaction(**argument_pack)
    elif entry_set_type == EntrySetType.OUT:
        argument_pack = configuration.get_out_table_constructor_argument_pack(row_values)
        argument_pack.update({"configuration": configuration, "line": line})
        transaction = OutTransaction(**argument_pack)
    elif entry_set_type == EntrySetType.INTRA:
        argument_pack = configuration.get_intra_table_constructor_argument_pack(row_values)
        argument_pack.update({"configuration": configuration, "line": line})
        transaction = IntraTransaction(**argument_pack)
    return transaction


def _get_entry_set_type(cell_value: str) -> Optional[EntrySetType]:
    return EntrySetType.get_entry_set_type_from_string(cell_value)


def _is_table_in(cell_value: str) -> bool:
    return _get_entry_set_type(cell_value) == EntrySetType.IN


def _is_table_out(cell_value: str) -> bool:
    return _get_entry_set_type(cell_value) == EntrySetType.OUT


def _is_table_intra(cell_value: str) -> bool:
    return _get_entry_set_type(cell_value) == EntrySetType.INTRA


def _is_table_begin(cell_value: str) -> bool:
    return _is_table_in(cell_value) or _is_table_out(cell_value) or _is_table_intra(cell_value)


def _is_table_end(cell_value: str) -> bool:
    return cell_value == _TABLE_END


def _is_empty(cell_value: str) -> bool:
    return cell_value is None


def main() -> None:
    pass


if __name__ == "__main__":
    main()

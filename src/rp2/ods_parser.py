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

import inspect
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import ezodf
from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import MAX_YEAR, Configuration
from rp2.entry_types import EntrySetType
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.logger import LOGGER
from rp2.out_transaction import OutTransaction
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2ValueError
from rp2.transaction_set import TransactionSet

_TABLE_END: str = "TABLE END"


def open_ods(configuration: Configuration, input_file_path: str) -> Any:
    Configuration.type_check("configuration", configuration)
    configuration.type_check_string("input_file_path", input_file_path)

    if not Path(input_file_path).exists():
        raise RP2ValueError(f"Error: {input_file_path} does not exist")

    return ezodf.opendoc(input_file_path)


def parse_ods(configuration: Configuration, asset: str, input_file_handle: Any) -> InputData:  # pylint: disable=too-many-branches

    Configuration.type_check("configuration", configuration)
    configuration.type_check_asset("asset", asset)

    if asset not in input_file_handle.sheets.names():
        raise RP2ValueError(f"Error: sheet {asset} does not exist in {Path(input_file_handle.docname).resolve()}")
    input_sheet: Any = input_file_handle.sheets[asset]

    unfiltered_transaction_sets: Dict[EntrySetType, TransactionSet] = {}

    unfiltered_transaction_sets[EntrySetType.IN] = TransactionSet(configuration, "IN", asset, 0, MAX_YEAR)
    unfiltered_transaction_sets[EntrySetType.OUT] = TransactionSet(configuration, "OUT", asset, 0, MAX_YEAR)
    unfiltered_transaction_sets[EntrySetType.INTRA] = TransactionSet(configuration, "INTRA", asset, 0, MAX_YEAR)

    current_table_type: Optional[EntrySetType] = None
    current_table_row_count: int = 0
    i: int = 0
    row: Any = None
    for i, row in enumerate(input_sheet.rows()):
        cell0_value: str = row[0].value
        # The numeric elements of the row_values list are used to initialize RP2Decimal instances. In theory we could collect string representations
        # from numeric strings using the plaintext() method of Cell, but this doesn't work well because of an ezodf limitation: such strings are
        # affected by the format of their cell (so they may be less precise than their real value, depending on cell format), so as a workaround
        # we read the value attribute which returns a float. In theory this could cause precision loss, but in reality most of the input data from
        # wallets / exchanges is very low-precision, so using a float is almost always adequate. The only exception would be if a wallet / exchange
        # input data had numbers with more than CRYPTO_DECIMALS (defined in rp2_decimal.py) decimal digits, which is quite uncommon: in this case
        # RP2 would still work, but it would have a little precision loss on these high-precision numbers. Also read the comments in
        # _process_constructor_argument_pack().
        row_values: List[Any] = [cell.value for cell in row]
        LOGGER.debug("parsing row: %s", row_values)

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
            if current_table_type and not unfiltered_transaction_sets[current_table_type].is_empty():
                # Found an already-processed table type
                raise RP2ValueError(f"{asset}({i + 1}): Found more than one {cell0_value} symbol")
        elif _is_table_end(cell0_value):
            # Table end
            current_table_type = None
        elif current_table_type is not None and current_table_row_count == 1:
            # Header line: make sure it's not transaction data
            try:
                transaction = _create_transaction(configuration, current_table_type, i, row_values)
            except Exception:  # pylint: disable=broad-except  # nosec
                # Couldn't create transaction as expected: this is a table header
                # TODO: this could still be a transaction but with some bad fields that would  # pylint: disable=fixme
                # cause an exception. In this case this logic would incorrectly assume it's a
                # header. Can we do better in this case? Some heuristics testing field by
                # field would help.
                pass
            else:
                raise RP2ValueError(f"{asset}({i + 1}): Found data with no header")
        elif current_table_type is not None and current_table_row_count > 1:
            # Transaction line
            transaction = _create_transaction(configuration, current_table_type, i, row_values)
            unfiltered_transaction_sets[current_table_type].add_entry(transaction)
        current_table_row_count += 1

    if current_table_type is not None:
        raise RP2ValueError(f"TABLE END not found for {current_table_type} table")
    if unfiltered_transaction_sets[EntrySetType.IN].is_empty():
        raise RP2ValueError(f"{asset}: IN table not found or empty")

    return InputData(
        asset,
        unfiltered_transaction_sets[EntrySetType.IN],
        unfiltered_transaction_sets[EntrySetType.OUT],
        unfiltered_transaction_sets[EntrySetType.INTRA],
        configuration.from_year,
        configuration.to_year,
    )


# Returns all numeric parameters of the constructor: used in construction of __init__ argument pack to parse such parameters as decimals
@lru_cache(maxsize=None, typed=False)
def _get_decimal_constructor_argument_names(class_name: str) -> List[str]:
    result: List[str] = []
    class_to_inspect: Any
    if class_name not in globals():
        raise Exception(f"Internal error: couldn't find class {class_name}")
    class_to_inspect = globals()[class_name]
    if not issubclass(class_to_inspect, AbstractTransaction):
        raise Exception(f"Internal error: class {class_name} is not a subclass of AbstractTransaction")
    arg_spec = inspect.getfullargspec(class_to_inspect.__init__)
    for parameter_name, parameter_type in arg_spec.annotations.items():
        if parameter_type in [RP2Decimal, Optional[RP2Decimal]]:
            result.append(parameter_name)
    return result


# Add configuration and unique_id to argument pack and turn floats to strings to maximize decimal precision. See comment inside the function.
def _process_constructor_argument_pack(
    configuration: Configuration,
    argument_pack: Dict[str, Any],
    unique_id: int,
    class_name: str,
) -> Dict[str, Any]:
    argument_pack.update({"configuration": configuration, "unique_id": unique_id})
    numeric_parameters: List[str] = _get_decimal_constructor_argument_names(class_name)
    for numeric_parameter in numeric_parameters:
        if numeric_parameter in argument_pack:
            value: Optional[float] = argument_pack[numeric_parameter]
            # It would be ideal to pass a string directly to the RP2Decimal constructor for maximum precision, but due to ezodf limitations we
            # cannot get the string representation directly from the spreadsheet (see the comment on cell format inside parse_ods() for more
            # detail), so at parse time we have to get the float value from the cell. Here we convert the float to string, which allows us to
            # initialize a maximum-precision RP2Decimal (11 decimal digits is enough precision for millisats).
            argument_pack[numeric_parameter] = RP2Decimal(f"{value:.11f}") if value is not None else None

    return argument_pack


def _create_transaction(
    configuration: Configuration,
    entry_set_type: EntrySetType,
    unique_id: int,
    row_values: List[Any],
) -> AbstractTransaction:
    transaction: AbstractTransaction
    EntrySetType.type_check("entry_set_type", entry_set_type)
    configuration.type_check_unique_id("unique_id", unique_id)
    if entry_set_type == EntrySetType.IN:
        argument_pack: Dict[str, Any] = configuration.get_in_table_constructor_argument_pack(row_values)
        argument_pack = _process_constructor_argument_pack(configuration, argument_pack, unique_id, "InTransaction")
        transaction = InTransaction(**argument_pack)
    elif entry_set_type == EntrySetType.OUT:
        argument_pack = configuration.get_out_table_constructor_argument_pack(row_values)
        argument_pack = _process_constructor_argument_pack(configuration, argument_pack, unique_id, "OutTransaction")
        transaction = OutTransaction(**argument_pack)
    elif entry_set_type == EntrySetType.INTRA:
        argument_pack = configuration.get_intra_table_constructor_argument_pack(row_values)
        argument_pack = _process_constructor_argument_pack(configuration, argument_pack, unique_id, "IntraTransaction")
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
    return cell_value is None or cell_value == ""


def main() -> None:
    pass


if __name__ == "__main__":
    main()

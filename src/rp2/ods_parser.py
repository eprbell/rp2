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
from rp2.configuration import MAX_DATE, MIN_DATE, Configuration
from rp2.entry_types import EntrySetType, TransactionType
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.logger import LOGGER
from rp2.out_transaction import OutTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2Error, RP2ValueError
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

    unfiltered_transaction_sets[EntrySetType.IN] = TransactionSet(configuration, "IN", asset, MIN_DATE, MAX_DATE)
    unfiltered_transaction_sets[EntrySetType.OUT] = TransactionSet(configuration, "OUT", asset, MIN_DATE, MAX_DATE)
    unfiltered_transaction_sets[EntrySetType.INTRA] = TransactionSet(configuration, "INTRA", asset, MIN_DATE, MAX_DATE)

    artificial_transaction_list: List[AbstractTransaction] = []

    current_table_type: Optional[EntrySetType] = None
    current_table_row_count: int = 0
    i: int = 0
    row: Any = None
    # Used for artificial transactions only: e.g. the fee-only transaction that is created artificially to model crypto fee of in-transactions.
    # Artificial internal ids are negative.
    artificial_internal_id = 0
    for i, row in enumerate(input_sheet.rows()):
        artificial_internal_id -= 1
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
                _create_transaction(configuration, current_table_type, i + 1, row_values)
            except Exception:  # pylint: disable=broad-except  # nosec
                # Couldn't create transaction as expected: this is a table header
                # TODO: this could still be a transaction but with some bad fields that would  # pylint: disable=fixme
                # cause an exception. In this case this logic would incorrectly assume it's a
                # header. Can we do better in this case? Some heuristics testing field by
                # field might help.
                pass
            else:
                raise RP2ValueError(f"{asset}({i + 1}): Found data with no header")
        elif current_table_type is not None and current_table_row_count > 1:
            # Transaction line
            _create_and_process_transaction(
                configuration, row_values, current_table_type, i + 1, artificial_internal_id, unfiltered_transaction_sets, artificial_transaction_list
            )
        current_table_row_count += 1

    if current_table_type is not None:
        raise RP2ValueError(f"TABLE END not found for {current_table_type} table")
    if unfiltered_transaction_sets[EntrySetType.IN].is_empty():
        raise RP2ValueError(f"{asset}: IN table not found or empty")

    for transaction in artificial_transaction_list:
        if isinstance(transaction, InTransaction):
            unfiltered_transaction_sets[EntrySetType.IN].add_entry(transaction)
        elif isinstance(transaction, OutTransaction):
            unfiltered_transaction_sets[EntrySetType.OUT].add_entry(transaction)
        elif isinstance(transaction, IntraTransaction):
            unfiltered_transaction_sets[EntrySetType.INTRA].add_entry(transaction)
        else:
            raise RP2ValueError(f"Internal error: invalid transaction class: {transaction}")

    return InputData(
        asset,
        unfiltered_transaction_sets[EntrySetType.IN],
        unfiltered_transaction_sets[EntrySetType.OUT],
        unfiltered_transaction_sets[EntrySetType.INTRA],
        configuration.from_date,
        configuration.to_date,
    )


def _create_and_process_transaction(
    configuration: Configuration,
    row_values: List[Any],
    current_table_type: EntrySetType,
    internal_id: int,
    artificial_internal_id: int,
    unfiltered_transaction_sets: Dict[EntrySetType, TransactionSet],
    artificial_transaction_list: List[AbstractTransaction],
) -> None:

    transaction: AbstractTransaction = _create_transaction(configuration, current_table_type, internal_id, row_values)

    if isinstance(transaction, InTransaction) and transaction.is_crypto_fee_defined:
        # If an InTransaction has crypto fee defined it is split into two transactions:
        # - InTransaction with crypto_fee set to 0, but fiat_fee left as-is (the fiat-converted value of crypto_fee),
        # - fee-typed OutTransaction, modeling the crypto_fee.
        # These two transactions correctly model the coin flow of a InTransaction with crypto fee > 0: their notes
        # fields are updated with a description of the above.
        notes: str = f"{transaction.notes}; " if transaction.notes else ""
        notes = (
            f"{notes}This transaction has a crypto fee of {transaction.crypto_fee} {transaction.asset}, "
            "which is modeled with an artificial, fee-only out-transaction (look for it among out-transactions)"
        )

        unfiltered_transaction_sets[EntrySetType.IN].add_entry(
            InTransaction(
                configuration=configuration,
                timestamp=f"{transaction.timestamp}",
                asset=transaction.asset,
                exchange=transaction.exchange,
                holder=transaction.holder,
                transaction_type=transaction.transaction_type.value,
                spot_price=transaction.spot_price,
                crypto_in=transaction.crypto_in,
                crypto_fee=None,
                fiat_in_no_fee=transaction.fiat_in_no_fee,
                fiat_in_with_fee=transaction.fiat_in_with_fee,
                fiat_fee=transaction.fiat_fee,
                internal_id=internal_id,
                unique_id=transaction.unique_id,
                notes=notes,
            )
        )
        artificial_transaction_list.append(
            OutTransaction(
                configuration=configuration,
                timestamp=f"{transaction.timestamp}",
                asset=transaction.asset,
                exchange=transaction.exchange,
                holder=transaction.holder,
                transaction_type=TransactionType.FEE.value,
                spot_price=transaction.spot_price,
                crypto_out_no_fee=ZERO,
                crypto_fee=transaction.crypto_fee,
                internal_id=artificial_internal_id,
                unique_id=transaction.unique_id,
                notes=(
                    f"Artificial transaction modeling the crypto fee of {transaction.crypto_fee} {transaction.asset} "
                    f"of the in-transaction that occurred on {transaction.timestamp} (look for it among in-transactions)"
                ),
            )
        )
    else:
        unfiltered_transaction_sets[current_table_type].add_entry(transaction)


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


# Add configuration and internal_id to argument pack and turn floats to strings to maximize decimal precision. See comment inside the function.
def _process_constructor_argument_pack(
    configuration: Configuration,
    argument_pack: Dict[str, Any],
    internal_id: int,
    class_name: str,
) -> Dict[str, Any]:
    argument_pack.update({"configuration": configuration, "internal_id": internal_id})
    numeric_parameters: List[str] = _get_decimal_constructor_argument_names(class_name)
    for numeric_parameter in numeric_parameters:
        if numeric_parameter in argument_pack:
            try:
                value: Optional[float] = argument_pack[numeric_parameter]
                # It would be ideal to pass a string directly to the RP2Decimal constructor for maximum precision, but due to ezodf limitations we
                # cannot get the string representation directly from the spreadsheet (see the comment on cell format inside parse_ods() for more
                # detail), so at parse time we have to get the float value from the cell. Here we convert the float to string, which allows us to
                # initialize a maximum-precision RP2Decimal (11 decimal digits is enough precision for millisats).
                argument_pack[numeric_parameter] = RP2Decimal(f"{value:.11f}") if value is not None else None
            except (ValueError, RP2Error) as exc:
                raise RP2ValueError(f"Argument '{numeric_parameter}' has non-numeric value: {value}") from exc

    return argument_pack


def _create_transaction(
    configuration: Configuration,
    entry_set_type: EntrySetType,
    internal_id: int,
    row_values: List[Any],
) -> AbstractTransaction:
    transaction: AbstractTransaction
    EntrySetType.type_check("entry_set_type", entry_set_type)
    configuration.type_check_internal_id("internal_id", internal_id)
    if entry_set_type == EntrySetType.IN:
        argument_pack: Dict[str, Any] = configuration.get_in_table_constructor_argument_pack(row_values)
        argument_pack = _process_constructor_argument_pack(configuration, argument_pack, internal_id, "InTransaction")
        transaction = InTransaction(**argument_pack)
    elif entry_set_type == EntrySetType.OUT:
        argument_pack = configuration.get_out_table_constructor_argument_pack(row_values)
        argument_pack = _process_constructor_argument_pack(configuration, argument_pack, internal_id, "OutTransaction")
        transaction = OutTransaction(**argument_pack)
    elif entry_set_type == EntrySetType.INTRA:
        argument_pack = configuration.get_intra_table_constructor_argument_pack(row_values)
        argument_pack = _process_constructor_argument_pack(configuration, argument_pack, internal_id, "IntraTransaction")
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

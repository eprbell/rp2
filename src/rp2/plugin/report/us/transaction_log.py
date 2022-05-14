# Copyright 2022 mdavid217
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

import logging
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Set, cast

from rp2.abstract_country import AbstractCountry
from rp2.computed_data import ComputedData
from rp2.in_transaction import InTransaction
from rp2.out_transaction import OutTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.logger import create_logger
from rp2.plugin.report.abstract_ods_generator import AbstractODSGenerator
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError

LOGGER: logging.Logger = create_logger("tlog")

_TEMPLATE_SHEETS: Set[str] = {"Transactions Style 1", "Transactions Style 2", "Transactions Style 3"}
_TEMPLATE_SHEETS_TO_KEEP: Set[str] = {"__" + sheet_name for sheet_name in _TEMPLATE_SHEETS}
_TRANSACTIONS_STYLE_1: str = "Transactions Style 1"
_TRANSACTIONS_STYLE_2: str = "Transactions Style 2"
_TRANSACTIONS_STYLE_3: str = "Transactions Style 3"
_FIAT_UNIT_DATA_STYLE_2_DECIMAL_MINIMUM = RP2Decimal("1")
_FIAT_UNIT_DATA_STYLE_4_DECIMAL_MINIMUM = RP2Decimal("0.20")


def _get_data_style(price: RP2Decimal) -> str:
    unit_data_style: str = "fiat"
    if _FIAT_UNIT_DATA_STYLE_4_DECIMAL_MINIMUM <= price < _FIAT_UNIT_DATA_STYLE_2_DECIMAL_MINIMUM:
        unit_data_style = "fiat_unit_4"
    elif price < _FIAT_UNIT_DATA_STYLE_4_DECIMAL_MINIMUM:
        unit_data_style = "fiat_unit_7"
    return unit_data_style


def _empty_fee_if_zero(fee: RP2Decimal) -> str | RP2Decimal:
    if fee > ZERO:
        return fee

    return ""


class Generator(AbstractODSGenerator):

    OUTPUT_FILE: str = "transaction_log.ods"
    HEADER_ROWS = 2

    def generate(
        self,
        country: AbstractCountry,
        accounting_method: str,
        asset_to_computed_data: Dict[str, ComputedData],
        output_dir_path: str,
        output_file_prefix: str,
        from_date: date,
        to_date: date,
    ) -> None:

        # pylint: disable=too-many-branches

        row_indexes: Dict[str, int] = {sheet_name: self.HEADER_ROWS for sheet_name in _TEMPLATE_SHEETS}

        if not isinstance(asset_to_computed_data, Dict):
            raise RP2TypeError(f"Parameter 'asset_to_computed_data' has non-Dict value {asset_to_computed_data}")

        template_path: str = str(
            Path(os.path.dirname(__file__)).parent.absolute() / Path("".join(["data/template_transaction_log_", country.country_iso_code, ".ods"]))
        )

        output_file: Any
        output_file = self._initialize_output_file(
            country=country,
            accounting_method=accounting_method,
            output_dir_path=output_dir_path,
            output_file_prefix=output_file_prefix,
            output_file_name=self.OUTPUT_FILE,
            template_path=template_path,
            template_sheets_to_keep=_TEMPLATE_SHEETS_TO_KEEP,
            from_date=from_date,
            to_date=to_date,
        )

        asset: str
        computed_data: ComputedData
        all_transactions: List[Any] = []

        for asset, computed_data in asset_to_computed_data.items():
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)

            for current_transaction in computed_data.in_transaction_set:
                in_transaction = cast(InTransaction, current_transaction)
                all_transactions.append(in_transaction)

            for current_transaction in computed_data.out_transaction_set:
                out_transaction = cast(OutTransaction, current_transaction)
                all_transactions.append(out_transaction)

            for current_transaction in computed_data.intra_transaction_set:
                intra_transaction = cast(IntraTransaction, current_transaction)
                all_transactions.append(intra_transaction)

        row_index: int

        # Style 1
        sheet = output_file.sheets[_TRANSACTIONS_STYLE_1]
        for transaction in sorted(all_transactions, key=lambda i: (i.timestamp)):
            sheet.append_rows(1)
            row_index = row_indexes[_TRANSACTIONS_STYLE_1]

            self._fill_cell(sheet, row_index, 0, transaction.timestamp)
            self._fill_cell(sheet, row_index, 1, transaction.asset)
            self._fill_cell(sheet, row_index, 4, transaction.transaction_type.value.upper())
            self._fill_cell(sheet, row_index, 6, transaction.spot_price, data_style=_get_data_style(transaction.spot_price))

            if isinstance(transaction, InTransaction):
                self._fill_cell(sheet, row_index, 2, transaction.exchange)
                self._fill_cell(sheet, row_index, 3, transaction.holder)
                self._fill_cell(sheet, row_index, 5, transaction.crypto_in, data_style="crypto")
                self._fill_cell(sheet, row_index, 7, transaction.fiat_in_with_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 8, transaction.fiat_in_no_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 9, transaction.fiat_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 10, "", data_style="crypto")
                self._fill_cell(sheet, row_index, 11, "", data_style="crypto")
                self._fill_cell(sheet, row_index, 12, _empty_fee_if_zero(transaction.crypto_fee), data_style="crypto")
            elif isinstance(transaction, OutTransaction):
                self._fill_cell(sheet, row_index, 2, transaction.exchange)
                self._fill_cell(sheet, row_index, 3, transaction.holder)
                self._fill_cell(sheet, row_index, 5, RP2Decimal("-1") * transaction.crypto_balance_change, data_style="crypto")
                self._fill_cell(sheet, row_index, 7, transaction.fiat_out_with_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 8, transaction.fiat_out_no_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 9, transaction.fiat_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 10, "", data_style="crypto")
                self._fill_cell(sheet, row_index, 11, "", data_style="crypto")
                self._fill_cell(sheet, row_index, 12, _empty_fee_if_zero(transaction.crypto_fee), data_style="crypto")
            elif isinstance(transaction, IntraTransaction):
                self._fill_cell(sheet, row_index, 2, transaction.from_exchange + " to " + transaction.to_exchange)
                self._fill_cell(sheet, row_index, 3, transaction.from_holder + " to " + transaction.to_holder)
                self._fill_cell(sheet, row_index, 5, "", data_style="crypto")
                self._fill_cell(sheet, row_index, 7, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 8, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 9, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 10, transaction.crypto_sent, data_style="crypto")
                self._fill_cell(sheet, row_index, 11, transaction.crypto_received, data_style="crypto")
                self._fill_cell(sheet, row_index, 12, _empty_fee_if_zero(transaction.crypto_fee), data_style="crypto")

            row_indexes[_TRANSACTIONS_STYLE_1] = row_index + 1

        # Style 2
        sheet = output_file.sheets[_TRANSACTIONS_STYLE_2]
        for transaction in sorted(all_transactions, key=lambda i: (i.timestamp)):
            sheet.append_rows(1)
            row_index = row_indexes[_TRANSACTIONS_STYLE_2]

            if isinstance(transaction, InTransaction):
                self._fill_cell(sheet, row_index, 0, transaction.timestamp)
                self._fill_cell(sheet, row_index, 1, transaction.asset)
                self._fill_cell(sheet, row_index, 2, transaction.exchange)
                self._fill_cell(sheet, row_index, 3, transaction.holder)
                self._fill_cell(sheet, row_index, 4, transaction.transaction_type.value.upper())
                self._fill_cell(sheet, row_index, 5, transaction.crypto_in, data_style="crypto")
                self._fill_cell(sheet, row_index, 6, transaction.spot_price, data_style=_get_data_style(transaction.spot_price))
                self._fill_cell(sheet, row_index, 7, transaction.fiat_in_with_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 8, transaction.fiat_in_no_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 9, transaction.fiat_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 10, _empty_fee_if_zero(transaction.crypto_fee), data_style="crypto")
            elif isinstance(transaction, OutTransaction):
                self._fill_cell(sheet, row_index, 0, transaction.timestamp)
                self._fill_cell(sheet, row_index, 1, transaction.asset)
                self._fill_cell(sheet, row_index, 2, transaction.exchange)
                self._fill_cell(sheet, row_index, 3, transaction.holder)
                self._fill_cell(sheet, row_index, 4, transaction.transaction_type.value.upper())
                self._fill_cell(sheet, row_index, 5, RP2Decimal("-1") * transaction.crypto_balance_change, data_style="crypto")
                self._fill_cell(sheet, row_index, 6, transaction.spot_price, data_style=_get_data_style(transaction.spot_price))
                self._fill_cell(sheet, row_index, 7, transaction.fiat_out_with_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 8, transaction.fiat_out_no_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 9, transaction.fiat_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 10, _empty_fee_if_zero(transaction.crypto_fee), data_style="crypto")
            elif isinstance(transaction, IntraTransaction):

                # Two rows instead of one.  First row.
                self._fill_cell(sheet, row_index, 0, transaction.timestamp)
                self._fill_cell(sheet, row_index, 1, transaction.asset)
                self._fill_cell(sheet, row_index, 2, "From " + transaction.from_exchange)
                self._fill_cell(sheet, row_index, 3, "From " + transaction.from_holder)
                self._fill_cell(sheet, row_index, 4, transaction.transaction_type.value.upper())
                self._fill_cell(sheet, row_index, 5, RP2Decimal("-1") * transaction.crypto_sent, data_style="crypto")
                self._fill_cell(sheet, row_index, 6, transaction.spot_price, data_style=_get_data_style(transaction.spot_price))
                self._fill_cell(sheet, row_index, 7, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 8, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 9, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 10, _empty_fee_if_zero(transaction.crypto_fee), data_style="crypto")
                row_indexes[_TRANSACTIONS_STYLE_2] = row_index + 1

                # Second row.
                sheet.append_rows(1)
                row_index += 1
                self._fill_cell(sheet, row_index, 0, transaction.timestamp)
                self._fill_cell(sheet, row_index, 1, transaction.asset)
                self._fill_cell(sheet, row_index, 2, "To " + transaction.to_exchange)
                self._fill_cell(sheet, row_index, 3, "To " + transaction.to_holder)
                self._fill_cell(sheet, row_index, 4, transaction.transaction_type.value.upper())
                self._fill_cell(sheet, row_index, 5, transaction.crypto_received, data_style="crypto")
                self._fill_cell(sheet, row_index, 6, transaction.spot_price, data_style=_get_data_style(transaction.spot_price))
                self._fill_cell(sheet, row_index, 7, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 8, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 9, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 10, "", data_style="crypto")

            row_indexes[_TRANSACTIONS_STYLE_2] = row_index + 1

        # Style 3
        sheet = output_file.sheets[_TRANSACTIONS_STYLE_3]
        for transaction in sorted(all_transactions, key=lambda i: (i.timestamp)):
            sheet.append_rows(1)
            row_index = row_indexes[_TRANSACTIONS_STYLE_3]

            self._fill_cell(sheet, row_index, 0, transaction.timestamp)
            self._fill_cell(sheet, row_index, 1, transaction.asset)
            self._fill_cell(sheet, row_index, 4, transaction.transaction_type.value.upper())
            self._fill_cell(sheet, row_index, 5, transaction.spot_price, data_style=_get_data_style(transaction.spot_price))

            if isinstance(transaction, InTransaction):
                self._fill_cell(sheet, row_index, 2, transaction.exchange)
                self._fill_cell(sheet, row_index, 3, transaction.holder)
                self._fill_cell(sheet, row_index, 6, transaction.crypto_in, data_style="crypto")
                self._fill_cell(sheet, row_index, 7, "", data_style="crypto")
                self._fill_cell(sheet, row_index, 8, _empty_fee_if_zero(transaction.crypto_fee), data_style="crypto")
                self._fill_cell(sheet, row_index, 9, transaction.fiat_in_with_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 10, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 11, transaction.fiat_fee, data_style="fiat")
            elif isinstance(transaction, OutTransaction):
                self._fill_cell(sheet, row_index, 2, transaction.exchange)
                self._fill_cell(sheet, row_index, 3, transaction.holder)
                self._fill_cell(sheet, row_index, 6, "", data_style="crypto")
                self._fill_cell(sheet, row_index, 7, transaction.crypto_balance_change, data_style="crypto")
                self._fill_cell(sheet, row_index, 8, _empty_fee_if_zero(transaction.crypto_fee), data_style="crypto")
                self._fill_cell(sheet, row_index, 9, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 10, transaction.fiat_out_with_fee, data_style="fiat")
                self._fill_cell(sheet, row_index, 11, transaction.fiat_fee, data_style="fiat")
            elif isinstance(transaction, IntraTransaction):
                self._fill_cell(sheet, row_index, 2, transaction.from_exchange + " to " + transaction.to_exchange)
                self._fill_cell(sheet, row_index, 3, transaction.from_holder + " to " + transaction.to_holder)
                self._fill_cell(sheet, row_index, 6, transaction.crypto_received, data_style="crypto")
                self._fill_cell(sheet, row_index, 7, transaction.crypto_sent, data_style="crypto")
                self._fill_cell(sheet, row_index, 8, _empty_fee_if_zero(transaction.crypto_fee), data_style="crypto")
                self._fill_cell(sheet, row_index, 9, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 10, "", data_style="fiat")
                self._fill_cell(sheet, row_index, 11, "", data_style="fiat")

            row_indexes[_TRANSACTIONS_STYLE_3] = row_index + 1

        output_file.save()
        LOGGER.info("Plugin '%s' output: %s", __name__, Path(output_file.docname).resolve())

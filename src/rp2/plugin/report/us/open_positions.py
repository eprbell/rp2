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
from datetime import date
import os
from pathlib import Path
from typing import Any, Dict, Set, cast

from rp2.abstract_country import AbstractCountry
from rp2.computed_data import ComputedData
from rp2.in_transaction import InTransaction
from rp2.logger import create_logger
from rp2.plugin.report.abstract_ods_generator import AbstractODSGenerator
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError

LOGGER: logging.Logger = create_logger("open_positions")

_TEMPLATE_SHEETS: Set[str] = {"Asset", "Asset - Exchange", "Input"}
_TEMPLATE_SHEETS_TO_KEEP: Set[str] = {"__" + sheet_name for sheet_name in _TEMPLATE_SHEETS}
_FIAT_UNIT_DATA_STYLE_2_DECIMAL_MINIMUM = RP2Decimal("1")
_FIAT_UNIT_DATA_STYLE_4_DECIMAL_MINIMUM = RP2Decimal("0.20")


class Generator(AbstractODSGenerator):

    OUTPUT_FILE: str = "open_positions.ods"
    HEADER_ROWS = 3

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

        template_path: str = str(Path(os.path.dirname(__file__)).parent.absolute() / Path("".join(["data/template_open_positions_", country.country_iso_code, ".ods"])))

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

        input_sheet = output_file.sheets["Input"]
        asset_exchange_sheet = output_file.sheets["Asset - Exchange"]
        asset_sheet = output_file.sheets["Asset"]

        # First loop through, I want to know the total cost basis for all assets and exchanges after filtering out net cost under $0.01.
        total_cost_basis = ZERO
        for asset, computed_data in asset_to_computed_data.items():
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)

            asset_cost_basis = ZERO
            for current_transaction in computed_data.in_transaction_set:
                in_transaction = cast(InTransaction, current_transaction)
                asset_cost_basis += in_transaction.fiat_in_with_fee * (RP2Decimal("1") - computed_data.get_in_lot_sold_percentage(in_transaction))

            # Skip assets that are zero-value / closed positions.
            if asset_cost_basis == ZERO:
                continue

            total_cost_basis += asset_cost_basis

        # Loop thru every asset again, but this time we can do reporting.
        for asset, computed_data in asset_to_computed_data.items():
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)

            # Net cost basis will be the sum of all usd_in_w_fee for an asset after multiplying off the sold percentage.
            asset_cost_basis = ZERO
            for current_transaction in computed_data.in_transaction_set:
                in_transaction = cast(InTransaction, current_transaction)
                sold_percent: RP2Decimal = computed_data.get_in_lot_sold_percentage(in_transaction)
                asset_cost_basis += in_transaction.fiat_in_with_fee * (RP2Decimal("1") - sold_percent)

            # Sum the total amount of crypto asset remaining.
            total_crypto_balance = ZERO
            for balance_set in computed_data.balance_set:
                total_crypto_balance += balance_set.final_balance

            # Skip assets that are zero-value / closed positions.
            if asset_cost_basis == ZERO:
                continue

            # For report clarity, change how much precision is displayed in the output based on the unit price. The raw value is
            # included in the output, so if the user desires they can change the cell format in the resulting file.
            # The default windowing is set up to hopefully give a good user experience for high value cryptos like BTC
            # all the way through cryptos with minute unit values like SHIB.
            unit_cost_basis: RP2Decimal = asset_cost_basis / total_crypto_balance
            unit_data_style: str = "fiat"
            if _FIAT_UNIT_DATA_STYLE_4_DECIMAL_MINIMUM <= unit_cost_basis < _FIAT_UNIT_DATA_STYLE_2_DECIMAL_MINIMUM:
                unit_data_style = "fiat_unit_4"
            elif unit_cost_basis < _FIAT_UNIT_DATA_STYLE_4_DECIMAL_MINIMUM:
                unit_data_style = "fiat_unit_7"

            # Only 1 record in the AP sheet per asset.
            input_sheet.append_rows(1)
            input_row_index: int = row_indexes["Input"]
            self._fill_cell(input_sheet, input_row_index, 0, asset)
            self._fill_cell(input_sheet, input_row_index, 1, "See Input Tab", data_style="fiat_unit_7")
            row_indexes["Input"] = input_row_index + 1

            # Next do the multi-row Asset/Exchange table which will calc vals that will feed the asset table.
            for balance_set in computed_data.balance_set:

                # Skip exchanges / wallets with no holdings.
                if balance_set.final_balance == ZERO:
                    continue

                asset_exchange_sheet.append_rows(1)
                asset_exchange_row_index: int = row_indexes["Asset - Exchange"]
                self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 0, asset)
                self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 1, balance_set.exchange)
                self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 2, balance_set.final_balance, data_style="crypto")
                self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 3, unit_cost_basis, data_style=unit_data_style)
                self._fill_cell(
                    asset_exchange_sheet, asset_exchange_row_index, 4, balance_set.final_balance * asset_cost_basis / total_crypto_balance, data_style="fiat"
                )
                self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 5, asset_cost_basis / total_cost_basis, data_style="percent")
                self._fill_cell(
                    asset_exchange_sheet, asset_exchange_row_index, 6, f"=VLOOKUP(A{asset_exchange_row_index+1};$Input.A:B;2;0)", data_style=unit_data_style
                )
                self._fill_cell(
                    asset_exchange_sheet, asset_exchange_row_index, 7, f"=C{asset_exchange_row_index+1}*G{asset_exchange_row_index+1}", data_style="fiat"
                )
                self._fill_cell(
                    asset_exchange_sheet, asset_exchange_row_index, 8, f"=H{asset_exchange_row_index+1}-E{asset_exchange_row_index+1}", data_style="fiat"
                )
                self._fill_cell(
                    asset_exchange_sheet,
                    asset_exchange_row_index,
                    9,
                    f"=(H{asset_exchange_row_index+1}-E{asset_exchange_row_index+1})/E{asset_exchange_row_index+1}",
                    data_style="percent",
                )
                row_indexes["Asset - Exchange"] = asset_exchange_row_index + 1

            # Single record per asset.
            asset_sheet.append_rows(1)
            asset_row_index: int = row_indexes["Asset"]
            self._fill_cell(asset_sheet, asset_row_index, 0, asset)
            self._fill_cell(asset_sheet, asset_row_index, 1, total_crypto_balance, data_style="crypto")
            self._fill_cell(asset_sheet, asset_row_index, 2, unit_cost_basis, data_style=unit_data_style)
            self._fill_cell(asset_sheet, asset_row_index, 3, asset_cost_basis, data_style="fiat")
            self._fill_cell(asset_sheet, asset_row_index, 4, asset_cost_basis / total_cost_basis, data_style="percent")
            self._fill_cell(asset_sheet, asset_row_index, 5, f"=VLOOKUP(A{asset_row_index+1};$Input.A:B;2;0)", data_style=unit_data_style)
            self._fill_cell(asset_sheet, asset_row_index, 6, f"=B{asset_row_index+1}*F{asset_row_index+1}", data_style="fiat")
            self._fill_cell(asset_sheet, asset_row_index, 7, f"=G{asset_row_index+1}-D{asset_row_index+1}", data_style="fiat")
            self._fill_cell(asset_sheet, asset_row_index, 8, f"=(G{asset_row_index+1}-D{asset_row_index+1})/D{asset_row_index+1}", data_style="percent")
            row_indexes["Asset"] = asset_row_index + 1

        # There are several portfolio-wide fields in the output that are dependent on values the user enters into the Input tab for
        # live calculation that cannot be accounted for in this report. Since I want to include a totals row in the output, I cannot do
        # full-column sums, e.g. =G4/SUM(G:G), so instead I am using the row index and the header rows info to scope the SUM to the
        # actual rows I know I have placed data into.

        asset_row_index = row_indexes["Asset"]
        for row_idx in range(self.HEADER_ROWS, row_indexes["Asset"]):
            self._fill_cell(asset_sheet, row_idx, 9, f"=H{row_idx+1}/SUM(D${self.HEADER_ROWS+1}:D${asset_row_index})", data_style="percent")
            self._fill_cell(asset_sheet, row_idx, 10, f"=G{row_idx+1}/SUM(G${self.HEADER_ROWS+1}:G${asset_row_index})", data_style="percent")

        asset_exchange_row_index = row_indexes["Asset - Exchange"]
        for row_idx in range(self.HEADER_ROWS, row_indexes["Asset - Exchange"]):
            self._fill_cell(asset_exchange_sheet, row_idx, 10, f"=I{row_idx+1}/SUM(E${self.HEADER_ROWS+1}:E${asset_exchange_row_index})", data_style="percent")
            self._fill_cell(asset_exchange_sheet, row_idx, 11, f"=H{row_idx+1}/SUM(H${self.HEADER_ROWS+1}:H${asset_exchange_row_index})", data_style="percent")

        # Add some total rows.
        asset_sheet.append_rows(1)
        asset_row_index = row_indexes["Asset"]
        self._fill_cell(asset_sheet, asset_row_index, 0, "", visual_style="bold_border")
        self._fill_cell(asset_sheet, asset_row_index, 1, "", visual_style="bold_border")
        self._fill_cell(asset_sheet, asset_row_index, 2, "", visual_style="bold_border")
        self._fill_cell(asset_sheet, asset_row_index, 3, f"=SUM(D${self.HEADER_ROWS+1}:D${asset_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(asset_sheet, asset_row_index, 4, "", visual_style="bold_border")
        self._fill_cell(asset_sheet, asset_row_index, 5, "", visual_style="bold_border")
        self._fill_cell(asset_sheet, asset_row_index, 6, f"=SUM(G${self.HEADER_ROWS+1}:G${asset_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(asset_sheet, asset_row_index, 7, f"=SUM(H${self.HEADER_ROWS+1}:H${asset_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(
            asset_sheet,
            asset_row_index,
            8,
            f"=(G{asset_row_index+1}-D{asset_row_index+1})/D{asset_row_index+1}",
            visual_style="bold_border",
            data_style="percent",
        )
        self._fill_cell(asset_sheet, asset_row_index, 9, "", visual_style="bold_border")
        self._fill_cell(asset_sheet, asset_row_index, 10, "", visual_style="bold_border")
        row_indexes["Asset"] = asset_row_index + 1

        asset_exchange_sheet.append_rows(1)
        asset_exchange_row_index = row_indexes["Asset - Exchange"]
        self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 0, "", visual_style="bold_border")
        self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 1, "", visual_style="bold_border")
        self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 2, "", visual_style="bold_border")
        self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 3, "", visual_style="bold_border")
        self._fill_cell(
            asset_exchange_sheet,
            asset_exchange_row_index,
            4,
            f"=SUM(E${self.HEADER_ROWS+1}:E${asset_exchange_row_index})",
            visual_style="bold_border",
            data_style="fiat",
        )
        self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 5, "", visual_style="bold_border")
        self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 6, "", visual_style="bold_border")
        self._fill_cell(
            asset_exchange_sheet,
            asset_exchange_row_index,
            7,
            f"=SUM(H${self.HEADER_ROWS+1}:H${asset_exchange_row_index})",
            visual_style="bold_border",
            data_style="fiat",
        )
        self._fill_cell(
            asset_exchange_sheet,
            asset_exchange_row_index,
            8,
            f"=SUM(I${self.HEADER_ROWS+1}:I${asset_exchange_row_index})",
            visual_style="bold_border",
            data_style="fiat",
        )
        self._fill_cell(
            asset_exchange_sheet,
            asset_exchange_row_index,
            9,
            f"=(H{asset_exchange_row_index+1}-E{asset_exchange_row_index+1})/E{asset_exchange_row_index+1}",
            visual_style="bold_border",
            data_style="percent",
        )
        self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 10, "", visual_style="bold_border")
        self._fill_cell(asset_exchange_sheet, asset_exchange_row_index, 11, "", visual_style="bold_border")
        row_indexes["Asset - Exchange"] = asset_exchange_row_index + 1

        output_file.save()
        LOGGER.info("Plugin '%s' output: %s", __name__, Path(output_file.docname).resolve())

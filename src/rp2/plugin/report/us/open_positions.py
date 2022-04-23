# Copyright 2021 mdavid217
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
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Set, cast

from rp2.abstract_country import AbstractCountry
from rp2.computed_data import ComputedData
from rp2.in_transaction import InTransaction
from rp2.logger import create_logger
from rp2.plugin.report.abstract_ods_generator import AbstractODSGenerator
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError

LOGGER: logging.Logger = create_logger("open_positions")

_TEMPLATE_SHEETS_TO_KEEP: Set[str] = {"__Asset", "__Asset_and_Exchange", "__AssetPrice"}
_FIAT_EMPTY_BAL_CUTOFF = RP2Decimal("0.01")
_CRYPTO_EMPTY_BAL_CUTOFF = RP2Decimal(".000001")
_FIAT_UNIT_WINDOW_2_DECIMAL = RP2Decimal("1")
_FIAT_UNIT_WINDOW_4_DECIMAL = RP2Decimal("0.02")


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

        sheet_names: Set[str] = {"Asset", "Asset_and_Exchange", "AssetPrice"}
        row_indexes: Dict[str, int] = {sheet_name: self.HEADER_ROWS for sheet_name in sheet_names}

        if not isinstance(asset_to_computed_data, Dict):
            raise RP2TypeError(f"Parameter 'asset_to_computed_data' has non-Dict value {asset_to_computed_data}")

        output_file: Any
        output_file = self._initialize_output_file(
            country=country,
            accounting_method=accounting_method,
            output_dir_path=output_dir_path,
            output_file_prefix=output_file_prefix,
            output_file_name=self.OUTPUT_FILE,
            template_sheets_to_keep=_TEMPLATE_SHEETS_TO_KEEP,
            from_date=from_date,
            to_date=to_date,
            template_file_prefix="open_positions",
        )

        asset: str
        computed_data: ComputedData

        ap_sheet = output_file.sheets["AssetPrice"]
        ae_sheet = output_file.sheets["Asset_and_Exchange"]
        a_sheet = output_file.sheets["Asset"]

        # First loop through, I want to know the total cost basis for all assets and exchanges after filtering out net cost under $0.01.
        total_cost: RP2Decimal = RP2Decimal("0")
        for asset, computed_data in asset_to_computed_data.items():
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)

            net_cost = RP2Decimal("0")
            for current_transaction in computed_data.in_transaction_set:
                in_xact = cast(InTransaction, current_transaction)
                net_cost += in_xact.fiat_in_with_fee * (RP2Decimal("1") - computed_data.get_in_lot_sold_percentage(in_xact))

            if net_cost < _FIAT_EMPTY_BAL_CUTOFF:
                continue

            total_cost += net_cost

        # Loop thru every asset again, but this time we can do reporting.
        for asset, computed_data in asset_to_computed_data.items():
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)

            # Net cost basis will be the sum of all usd_in_w_fee for an asset after multiplying off the sold percentage.
            net_cost = RP2Decimal("0")
            for current_transaction in computed_data.in_transaction_set:
                in_xact = cast(InTransaction, current_transaction)
                sold_pct: RP2Decimal = computed_data.get_in_lot_sold_percentage(in_xact)
                net_cost += in_xact.fiat_in_with_fee * (RP2Decimal("1") - sold_pct)

            # Sum the total amount of crypto asset remaining.
            tot_crypto_bal = RP2Decimal("0")
            for balset in computed_data.balance_set:
                tot_crypto_bal += balset.final_balance

            if net_cost < _FIAT_EMPTY_BAL_CUTOFF:
                continue
            # print("asset ",asset,tot_crypto_bal,net_cost,float(net_cost))

            # For report clarity, this cuts down the decimals in the unit price based on the value of the unt, e.g. $1+
            # shows price to the nearest cent while $0.20-$1.00 shows to 4 decimal places, and anything smaller is
            # left un-rounded (the template formatting currently would show up to 7 decimal places.)
            unit_cost_basis: RP2Decimal = net_cost / tot_crypto_bal
            if unit_cost_basis >= _FIAT_UNIT_WINDOW_2_DECIMAL:
                unit_cost_basis = RP2Decimal(unit_cost_basis.quantize(Decimal("1.00")))
            elif unit_cost_basis >= _FIAT_UNIT_WINDOW_4_DECIMAL:
                unit_cost_basis = RP2Decimal(unit_cost_basis.quantize(Decimal("1.0000")))

            # Only 1 record in the AP sheet per asset.
            ap_sheet.append_rows(1)
            ap_row_index: int = row_indexes["AssetPrice"]
            self._fill_cell(ap_sheet, ap_row_index, 0, asset)
            self._fill_cell(ap_sheet, ap_row_index, 1, 0)
            row_indexes["AssetPrice"] = ap_row_index + 1

            # Next do the multi-row Asset/Exchange table which will calc vals that will feed the asset table.
            for balset in computed_data.balance_set:

                if balset.final_balance < _CRYPTO_EMPTY_BAL_CUTOFF:
                    continue

                ae_sheet.append_rows(1)
                ae_row_index: int = row_indexes["Asset_and_Exchange"]
                self._fill_cell(ae_sheet, ae_row_index, 0, asset)
                self._fill_cell(ae_sheet, ae_row_index, 1, balset.exchange)
                self._fill_cell(ae_sheet, ae_row_index, 2, balset.final_balance, data_style="crypto")
                self._fill_cell(ae_sheet, ae_row_index, 3, float(unit_cost_basis), data_style="fiat_unit")
                self._fill_cell(ae_sheet, ae_row_index, 4, balset.final_balance * (net_cost / tot_crypto_bal), data_style="fiat")
                self._fill_cell(ae_sheet, ae_row_index, 5, (net_cost / total_cost), data_style="percent")
                self._fill_cell(ae_sheet, ae_row_index, 6, f"=VLOOKUP(A{ae_row_index+1};$assetprice.A:B;2;0)", data_style="fiat_unit")
                self._fill_cell(ae_sheet, ae_row_index, 7, f"=C{ae_row_index+1}*G{ae_row_index+1}", data_style="fiat")
                self._fill_cell(ae_sheet, ae_row_index, 8, f"=H{ae_row_index+1}-E{ae_row_index+1}", data_style="fiat")
                self._fill_cell(ae_sheet, ae_row_index, 9, f"=(H{ae_row_index+1}-E{ae_row_index+1})/E{ae_row_index+1}", data_style="percent")
                self._fill_cell(ae_sheet, ae_row_index, 10, f"=I{ae_row_index+1}/SUM(E:E)", data_style="percent")
                self._fill_cell(ae_sheet, ae_row_index, 11, f"=H{ae_row_index+1}/SUM(H:H)", data_style="percent")
                row_indexes["Asset_and_Exchange"] = ae_row_index + 1

            # Single record per asset.
            a_sheet.append_rows(1)
            a_row_index: int = row_indexes["Asset"]
            self._fill_cell(a_sheet, a_row_index, 0, asset)
            self._fill_cell(a_sheet, a_row_index, 1, tot_crypto_bal, data_style="crypto")
            self._fill_cell(a_sheet, a_row_index, 2, float(unit_cost_basis), data_style="fiat_unit")
            self._fill_cell(a_sheet, a_row_index, 3, net_cost, data_style="fiat")
            self._fill_cell(a_sheet, a_row_index, 4, (net_cost / total_cost), data_style="percent")
            self._fill_cell(a_sheet, a_row_index, 5, f"=VLOOKUP(A{a_row_index+1};$assetprice.A:B;2;0)", data_style="fiat_unit")
            self._fill_cell(a_sheet, a_row_index, 6, f"=B{a_row_index+1}*F{a_row_index+1}", data_style="fiat")
            self._fill_cell(a_sheet, a_row_index, 7, f"=G{a_row_index+1}-D{a_row_index+1}", data_style="fiat")
            self._fill_cell(a_sheet, a_row_index, 8, f"=(G{a_row_index+1}-D{a_row_index+1})/D{a_row_index+1}", data_style="percent")
            self._fill_cell(a_sheet, a_row_index, 9, f"=H{a_row_index+1}/SUM(D:D)", data_style="percent")
            self._fill_cell(a_sheet, a_row_index, 10, f"=G{a_row_index+1}/SUM(G:G)", data_style="percent")
            row_indexes["Asset"] = a_row_index + 1

        # There are several portfolio-wide fields in the output that are dependent on values the user enters into the AssetPrice tab for
        # live calculation that cannot be accounted for in this report. Since I want to include a totals row in the output, I cannot do
        # full-column sums, e.g. =G4/SUM(G:G), so instead I am using the row index and the header rows info to scope the SUM to the
        # actual rows I know I have placed data into.

        a_row_index = row_indexes["Asset"]
        for row_idx in range(self.HEADER_ROWS, row_indexes["Asset"]):
            self._fill_cell(a_sheet, row_idx, 9, f"=H{row_idx+1}/SUM(D{self.HEADER_ROWS+1}:D{a_row_index})", data_style="percent")
            self._fill_cell(a_sheet, row_idx, 10, f"=G{row_idx+1}/SUM(G{self.HEADER_ROWS+1}:G{a_row_index})", data_style="percent")

        ae_row_index = row_indexes["Asset_and_Exchange"]
        for row_idx in range(self.HEADER_ROWS, row_indexes["Asset_and_Exchange"]):
            self._fill_cell(ae_sheet, row_idx, 10, f"=I{row_idx+1}/SUM(E{self.HEADER_ROWS+1}:E{ae_row_index})", data_style="percent")
            self._fill_cell(ae_sheet, row_idx, 11, f"=H{row_idx+1}/SUM(H{self.HEADER_ROWS+1}:H{ae_row_index})", data_style="percent")

        # Add some total rows.
        a_sheet.append_rows(1)
        a_row_index = row_indexes["Asset"]
        self._fill_cell(a_sheet, a_row_index, 0, "", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 1, "", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 2, "", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 3, f"=SUM(D{self.HEADER_ROWS+1}:D{a_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(a_sheet, a_row_index, 4, "", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 5, "", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 6, f"=SUM(G{self.HEADER_ROWS+1}:G{a_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(a_sheet, a_row_index, 7, f"=SUM(H{self.HEADER_ROWS+1}:H{a_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(a_sheet, a_row_index, 8, f"=(G{a_row_index+1}-D{a_row_index+1})/D{a_row_index+1}", visual_style="bold_border", data_style="percent")
        self._fill_cell(a_sheet, a_row_index, 9, "", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 10, "", visual_style="bold_border")
        row_indexes["Asset"] = a_row_index + 1

        ae_sheet.append_rows(1)
        ae_row_index = row_indexes["Asset_and_Exchange"]
        self._fill_cell(ae_sheet, ae_row_index, 0, "", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 1, "", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 2, "", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 3, "", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 4, f"=SUM(E{self.HEADER_ROWS+1}:E{ae_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(ae_sheet, ae_row_index, 5, "", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 6, "", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 7, f"=SUM(H{self.HEADER_ROWS+1}:H{ae_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(ae_sheet, ae_row_index, 8, f"=SUM(I{self.HEADER_ROWS+1}:I{ae_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(
            ae_sheet, ae_row_index, 9, f"=(H{ae_row_index+1}-E{ae_row_index+1})/E{ae_row_index+1}", visual_style="bold_border", data_style="percent"
        )
        self._fill_cell(ae_sheet, ae_row_index, 10, "", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 11, "", visual_style="bold_border")
        row_indexes["Asset_and_Exchange"] = ae_row_index + 1

        output_file.save()
        LOGGER.info("Plugin '%s' output: %s", __name__, Path(output_file.docname).resolve())


def main() -> None:
    pass


if __name__ == "__main__":
    main()

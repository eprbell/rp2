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
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Set, cast

from pprint import pprint

from rp2.abstract_country import AbstractCountry
from rp2.balance import BalanceSet
from rp2.computed_data import ComputedData
from rp2.entry_types import TransactionType
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
from rp2.logger import create_logger
from rp2.plugin.report.abstract_ods_generator import AbstractODSGenerator
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError

LOGGER: logging.Logger = create_logger("open_positions")

_TEMPLATE_SHEETS_TO_KEEP: Set[str] = {f"__Asset", f"__Asset_and_Exchange", f"__AssetPrice"}

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

        SheetNames: List[str] = {f"Asset", f"Asset_and_Exchange", f"AssetPrice"}
        row_indexes: Dict[str, int] = {sheet_name: self.HEADER_ROWS for sheet_name in SheetNames}

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
            template_file_prefix="open_positions"
        )

        asset: str
        computed_data: ComputedData

        ap_sheet = output_file.sheets['AssetPrice']
        ae_sheet = output_file.sheets['Asset_and_Exchange']
        a_sheet  = output_file.sheets['Asset']
        
        # First loop through, I want to know the total cost basis for all assets and exchanges after filtering out net cost under $0.01.
        total_cost: RP2Decimal = RP2Decimal("0")
        for asset, computed_data in asset_to_computed_data.items():
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)

            net_cost = RP2Decimal("0")
            for x in computed_data.in_transaction_set:
                net_cost += (x.fiat_in_with_fee * (RP2Decimal("1") - computed_data.get_in_lot_sold_percentage(x)))

            if float(net_cost) < 0.01: continue    
            total_cost += net_cost

        # Loop thru every asset again, but this time we can do reporting.
        for asset, computed_data in asset_to_computed_data.items():
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)

            # Net cost basis will be the sum of all usd_in_w_fee for an asset after multiplying off the sold percentage.
            net_cost = RP2Decimal("0")
            for x in computed_data.in_transaction_set:
                sold_pct: RP2Decimal = computed_data.get_in_lot_sold_percentage(x)
                net_cost += (x.fiat_in_with_fee * (RP2Decimal("1") - sold_pct))

            # Sum the total amount of crypto asset remaining.
            tot_crypto_bal = RP2Decimal("0")
            for balset in computed_data.balance_set:
                tot_crypto_bal = tot_crypto_bal + balset.final_balance

            if float(net_cost) < 0.01: continue
            #print("asset ",asset,tot_crypto_bal,net_cost,float(net_cost))

            # Only 1 record in the AP sheet per asset.
            ap_sheet.append_rows(1)
            ap_row_index: int = row_indexes['AssetPrice']
            self._fill_cell(ap_sheet, ap_row_index, 0, asset)
            self._fill_cell(ap_sheet, ap_row_index, 1, 0)
            row_indexes['AssetPrice'] = ap_row_index + 1

            # Next do the multi-row Asset/Exchange table which will calc vals that will feed the asset table.
            for balset in computed_data.balance_set:
                if float(balset.final_balance) < 0.000001: continue
                ae_sheet.append_rows(1)
                ae_row_index: int = row_indexes['Asset_and_Exchange']
                self._fill_cell(ae_sheet, ae_row_index, 0, asset)
                self._fill_cell(ae_sheet, ae_row_index, 1, balset.exchange)    
                self._fill_cell(ae_sheet, ae_row_index, 2, balset.final_balance, data_style="crypto")
                self._fill_cell(ae_sheet, ae_row_index, 3, (net_cost / tot_crypto_bal), data_style="fiat_unit")
                self._fill_cell(ae_sheet, ae_row_index, 4, balset.final_balance*(net_cost / tot_crypto_bal), data_style="fiat")
                self._fill_cell(ae_sheet, ae_row_index, 5, (net_cost / total_cost), data_style="percent")
                self._fill_cell(ae_sheet, ae_row_index, 6, f"=VLOOKUP(A{ae_row_index+1};$assetprice.A:B;2;0)", data_style="fiat_unit")
                self._fill_cell(ae_sheet, ae_row_index, 7, f"=C{ae_row_index+1}*G{ae_row_index+1}", data_style="fiat")
                self._fill_cell(ae_sheet, ae_row_index, 8, f"=H{ae_row_index+1}-E{ae_row_index+1}", data_style="fiat")
                self._fill_cell(ae_sheet, ae_row_index, 9, f"=(H{ae_row_index+1}-E{ae_row_index+1})/E{ae_row_index+1}", data_style="percent")
                self._fill_cell(ae_sheet, ae_row_index, 10, f"=I{ae_row_index+1}/SUM(E:E)", data_style="percent")
                self._fill_cell(ae_sheet, ae_row_index, 11, f"=H{ae_row_index+1}/SUM(H:H)", data_style="percent")
                row_indexes['Asset_and_Exchange'] = ae_row_index + 1

            # Single record per asset.
            a_sheet.append_rows(1)
            a_row_index: int = row_indexes['Asset']
            self._fill_cell(a_sheet, a_row_index, 0, asset)
            self._fill_cell(a_sheet, a_row_index, 1, tot_crypto_bal, data_style="crypto")
            self._fill_cell(a_sheet, a_row_index, 2, (net_cost / tot_crypto_bal), data_style="fiat_unit")
            self._fill_cell(a_sheet, a_row_index, 3, net_cost, data_style="fiat")
            self._fill_cell(a_sheet, a_row_index, 4, (net_cost / total_cost), data_style="percent")
            self._fill_cell(a_sheet, a_row_index, 5, f"=VLOOKUP(A{a_row_index+1};$assetprice.A:B;2;0)", data_style="fiat_unit")
            self._fill_cell(a_sheet, a_row_index, 6, f"=B{a_row_index+1}*F{a_row_index+1}", data_style="fiat")
            self._fill_cell(a_sheet, a_row_index, 7, f"=G{a_row_index+1}-D{a_row_index+1}", data_style="fiat")
            self._fill_cell(a_sheet, a_row_index, 8, f"=(G{a_row_index+1}-D{a_row_index+1})/D{a_row_index+1}", data_style="percent")
            self._fill_cell(a_sheet, a_row_index, 9,  f"=H{a_row_index+1}/SUM(D:D)", data_style="percent")
            self._fill_cell(a_sheet, a_row_index, 10, f"=G{a_row_index+1}/SUM(G:G)", data_style="percent")
            row_indexes['Asset'] = a_row_index + 1

        # There are several portfolio-wide fields in the output that are dependent on values the user enters into the AssetPrice tab for
        # live calculation that cannot be accounted for in this report. Since I want to include a totals row in the output, I cannot do
        # full-column sums, e.g. =G4/SUM(G:G), so instead I am using the row index and the header rows info to scope the SUM to the 
        # actual rows I know I have placed data into.

        a_row_index = row_indexes['Asset']
        for x in range(self.HEADER_ROWS,row_indexes['Asset']):
            self._fill_cell(a_sheet, x, 9,  f"=H{x+1}/SUM(D{self.HEADER_ROWS+1}:D{a_row_index})", data_style="percent")
            self._fill_cell(a_sheet, x, 10, f"=G{x+1}/SUM(G{self.HEADER_ROWS+1}:G{a_row_index})", data_style="percent")

        ae_row_index = row_indexes['Asset_and_Exchange']
        for x in range(self.HEADER_ROWS,row_indexes['Asset_and_Exchange']):
            self._fill_cell(ae_sheet, x, 10, f"=I{x+1}/SUM(E{self.HEADER_ROWS+1}:E{ae_row_index})", data_style="percent")
            self._fill_cell(ae_sheet, x, 11, f"=H{x+1}/SUM(H{self.HEADER_ROWS+1}:H{ae_row_index})", data_style="percent")
        
        # Add some total rows.
        a_sheet.append_rows(1)
        a_row_index = row_indexes['Asset']
        self._fill_cell(a_sheet, a_row_index, 0, f"", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 1, f"", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 2, f"", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 3, f"=SUM(D{self.HEADER_ROWS+1}:D{a_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(a_sheet, a_row_index, 4, f"", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 5, f"", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 6, f"=SUM(G{self.HEADER_ROWS+1}:G{a_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(a_sheet, a_row_index, 7, f"=SUM(H{self.HEADER_ROWS+1}:H{a_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(a_sheet, a_row_index, 8, f"=(G{a_row_index+1}-D{a_row_index+1})/D{a_row_index+1}", visual_style="bold_border", data_style="percent")
        self._fill_cell(a_sheet, a_row_index, 9, f"", visual_style="bold_border")
        self._fill_cell(a_sheet, a_row_index, 10, f"", visual_style="bold_border")
        row_indexes['Asset'] = a_row_index + 1

        ae_sheet.append_rows(1)
        ae_row_index = row_indexes['Asset_and_Exchange']
        self._fill_cell(ae_sheet, ae_row_index, 0, f"", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 1, f"", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 2, f"", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 3, f"", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 4, f"=SUM(E{self.HEADER_ROWS+1}:E{ae_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(ae_sheet, ae_row_index, 5, f"", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 6, f"", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 7, f"=SUM(H{self.HEADER_ROWS+1}:H{ae_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(ae_sheet, ae_row_index, 8, f"=SUM(I{self.HEADER_ROWS+1}:I{ae_row_index})", visual_style="bold_border", data_style="fiat")
        self._fill_cell(ae_sheet, ae_row_index, 9, f"=(H{ae_row_index+1}-E{ae_row_index+1})/E{ae_row_index+1}", visual_style="bold_border", data_style="percent")
        self._fill_cell(ae_sheet, ae_row_index, 10, f"", visual_style="bold_border")
        self._fill_cell(ae_sheet, ae_row_index, 11, f"", visual_style="bold_border")
        row_indexes['Asset_and_Exchange'] = ae_row_index + 1

        output_file.save()
        LOGGER.info("Plugin '%s' output: %s", __name__, Path(output_file.docname).resolve())


def main() -> None:
    pass


if __name__ == "__main__":
    main()

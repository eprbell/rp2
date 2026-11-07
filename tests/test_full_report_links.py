# Copyright 2026 eprbell
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

# The hyperlinks of the full report (R17 of the review of eprbell/rp2#155): the cells of the Tax sheet link to the row of their transaction in
# the In-Out sheet of the same asset. A transaction that a date filter (-f, -t) leaves out of the In-Out sheet has no row there, so its
# cells have no link. The report finds the rows with a map from transactions to rows. Transactions are equal when they have the same
# internal id (their row in the input), which repeats from asset to asset, so the map must only contain the rows of the current asset and
# report. Example: B1's first purchase is in the report, B2's first purchase was before the -f date, and both are row 1 of their input. A
# map shared by both assets would link B2's lot to the row of B1's purchase.

import shutil
import unittest
from datetime import date
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

from ods_diff import ReportCell, read_sheet_cells
from per_wallet_common import AbstractPerWalletTest, _create_configuration, _In, _Out

from rp2.computed_data import ComputedData
from rp2.configuration import MAX_DATE
from rp2.localization import set_generation_language
from rp2.plugin.country.us import US
from rp2.plugin.report.rp2_full_report import Generator as FullReportGenerator
from rp2.tax_engine import compute_tax

_OUTPUT_DIR = Path("output") / Path("test_full_report_links")
_FROM_DATE = date(2023, 1, 1)


# The lot of a gain/loss in the Gain / Loss Detail table: the taxable event, the lot's unique id and the unique id of the In-Out row that the
# lot's cells link to (None without a link).
class _Lot(NamedTuple):
    taxable_event: str
    lot: str
    linked_row: Optional[str]


# The sale o1 of lot i1: linked to i1's row, or without a link.
_LINKED: List[_Lot] = [_Lot("o1", "i1", "i1")]
_NOT_LINKED: List[_Lot] = [_Lot("o1", "i1", None)]


class TestFullReportLinks(AbstractPerWalletTest):
    # Universal application from _FROM_DATE (-f 2023-01-01) of two assets, with the same input rows: B1 bought in 2023 (in the report), B2
    # bought in 2022 (before it). Both sold in 2023.
    @classmethod
    def _compute(cls) -> Dict[str, ComputedData]:
        configuration = _create_configuration(None, from_date=_FROM_DATE)
        result: Dict[str, ComputedData] = {}
        for asset, purchase in (("B1", "2023-02-01T00:00:00+00:00"), ("B2", "2022-06-01T00:00:00+00:00")):
            transactions: List[object] = [
                _In("i1", purchase, "Coinbase", "Buy", "100", "2"),
                _Out("o1", "2023-06-01T00:00:00+00:00", "Coinbase", "200", "1"),
            ]
            input_data = cls._create_input_data(configuration, transactions, asset)
            result[asset] = compute_tax(configuration, cls._create_accounting_engine(None), input_data)
        return result

    def _generate(self, name: str, asset_to_computed_data: Dict[str, ComputedData], from_date: date) -> Path:
        output_dir = _OUTPUT_DIR / Path(name)
        shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True)
        set_generation_language("en")
        FullReportGenerator().generate(US(), {1970: "fifo"}, asset_to_computed_data, str(output_dir), f"{name}_", from_date, MAX_DATE, "en")
        return output_dir / Path(f"{name}_fifo_rp2_full_report.ods")

    # The lots of the Gain / Loss Detail table of an asset (see _Lot).
    def _get_lots(self, path: Path, asset: str) -> List[_Lot]:
        in_out_rows: List[List[ReportCell]] = read_sheet_cells(path, f"{asset} In-Out") or []
        result: List[_Lot] = []
        for cells in read_sheet_cells(path, f"{asset} Tax") or []:
            if len(cells) < 20 or cells[10].link_sheet != f"{asset} In-Out" or not cells[18].text:
                continue
            link = cells[18]
            linked_row = in_out_rows[link.link_row - 1][14].text if link.link_sheet == f"{asset} In-Out" and link.link_row is not None else None
            result.append(_Lot(cells[10].text, link.text, linked_row))
        return result

    def test_filtered_lots_have_no_link(self) -> None:
        asset_to_computed_data = self._compute()
        path = self._generate("two_assets", asset_to_computed_data, _FROM_DATE)
        # B1's lot is in the report: its cells link to its row. B2's lot was bought before the -f date: no link.
        self.assertEqual(self._get_lots(path, "B1"), _LINKED)
        self.assertEqual(self._get_lots(path, "B2"), _NOT_LINKED)

    # A second report in the same process doesn't use the rows of the first one: here the first report has B1 only, the second B2 only.
    def test_reports_dont_share_rows(self) -> None:
        asset_to_computed_data = self._compute()
        first = self._generate("first", {"B1": asset_to_computed_data["B1"]}, _FROM_DATE)
        second = self._generate("second", {"B2": asset_to_computed_data["B2"]}, _FROM_DATE)
        self.assertEqual(self._get_lots(first, "B1"), _LINKED)
        self.assertEqual(self._get_lots(second, "B2"), _NOT_LINKED)


if __name__ == "__main__":
    unittest.main()

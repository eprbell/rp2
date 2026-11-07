# Copyright 2025 eprbell
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

# End-to-end tests of the reports generated with per-wallet application (compute_tax_per_wallet): they check actual report cells. Expected
# values are computed by hand: each test explains the rule it checks.

import shutil
import unittest
from datetime import date
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

from ods_diff import read_sheet_cells, read_sheet_rows
from per_wallet_common import (
    _ASSET,
    _BLOCKFI,
    _COINBASE,
    _KRAKEN,
    _UTC,
    AbstractPerWalletTest,
    _allocation_config,
    _create_configuration,
    _GainLoss,
    _Holding,
    _holdings,
    _In,
    _Intra,
    _Out,
    _sorted,
)

from rp2.computed_data import ComputedData
from rp2.configuration import MAX_DATE, MIN_DATE
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.localization import set_generation_language
from rp2.per_wallet_configuration import PerWalletConfiguration
from rp2.plugin.country.us import US
from rp2.plugin.report.open_positions import Generator as OpenPositionsGenerator
from rp2.plugin.report.opening_allocation import Generator as OpeningAllocationGenerator
from rp2.plugin.report.rp2_full_report import Generator as FullReportGenerator
from rp2.plugin.report.us.tax_report_us import Generator as TaxReportUSGenerator
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.tax_engine import compute_tax, compute_tax_per_wallet


# The expected rows of an asset in the Wallets, Unused Lots and Allocation sheets of the opening allocation report.
class _OpeningAllocationRows(NamedTuple):
    wallets: List[List[str]]
    unused_lots: List[List[str]]
    allocation: List[List[str]]


# A lot of the Gain / Loss Detail table of the full report: the taxable event, the lot's unique id, the unique id of the In-Out row that
# the lot's cells link to (None without a link) and the lot's description.
class _ReportedLot(NamedTuple):
    taxable_event: str
    lot: str
    linked_row: Optional[str]
    description: str


class TestPerWalletReports(AbstractPerWalletTest):
    # Generates the full report of a history and returns the lots of its Gain / Loss Detail table (see _ReportedLot). Also checks that the
    # cells of a lot all link to the same row, or are all without a link.
    def _get_reported_lots(self, name: str, transactions: List[object], from_date: date = MIN_DATE) -> List[_ReportedLot]:
        configuration = _create_configuration(from_date=from_date)
        computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), self._create_input_data(configuration, transactions))
        output_dir = Path("output") / Path("test_per_wallet_reports") / Path(name)
        shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True)
        set_generation_language("en")
        FullReportGenerator().generate(US(), {1970: "fifo"}, {_ASSET: computed_data}, str(output_dir), f"{name}_", from_date, MAX_DATE, "en")
        TaxReportUSGenerator().generate(US(), {1970: "fifo"}, {_ASSET: computed_data}, str(output_dir), f"{name}_", from_date, MAX_DATE, "en")
        path = output_dir / Path(f"{name}_fifo_rp2_full_report.ods")
        in_out_rows = read_sheet_cells(path, f"{_ASSET} In-Out") or []
        result: List[_ReportedLot] = []
        for cells in read_sheet_cells(path, f"{_ASSET} Tax") or []:
            # Gain / Loss Detail rows: the taxable event's unique id (column 10) links to its row; income has no lot (column 18 is empty).
            if len(cells) < 20 or cells[10].link_sheet != f"{_ASSET} In-Out" or not cells[18].text:
                continue
            link_rows = {(cell.link_sheet, cell.link_row) for cell in cells[12:20]}
            self.assertEqual(len(link_rows), 1, msg=f"{name}: the cells of lot {cells[18].text} link to different rows: {link_rows}")
            link_sheet, link_row = link_rows.pop()
            linked_row = in_out_rows[link_row - 1][14].text if link_sheet == f"{_ASSET} In-Out" and link_row is not None else None
            result.append(_ReportedLot(cells[10].text, cells[18].text, linked_row, cells[19].text))
        return result

    # R17 of the review of eprbell/rp2#155: the full report identifies the lot of every gain/loss by its original lot, the input purchase its
    # coins come from, and links all the lot's cells to that purchase's row of the In-Out sheet. With per-wallet application, coins that came
    # through transfers or the opening allocation are in a lot that RP2 created for their wallet (e.g. t1/-1), which has no row: the lot's
    # description names that lot and its wallet, and the amounts stay those of the coins taken from it. Example (the review's): buy 2 coins on
    # Coinbase (i1), send both to Kraken and sell 1: the lot is i1, linked to i1's row, described as 1 of the 2 coins of Kraken's lot t1/-1.
    def test_lots_link_to_their_original_purchase(self) -> None:
        cases: List[Tuple[str, List[object], date, List[_ReportedLot]]] = [
            (
                "direct",
                [
                    _In("i1", "2025-01-10T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Coinbase", "200", "1"),
                ],
                MIN_DATE,
                [_ReportedLot("o1", "i1", "i1", "1/1: 1.00000000 of 2.00000000 B1")],
            ),
            (
                "review_example",
                [
                    _In("i1", "2025-01-10T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "2", "2"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "200", "1"),
                ],
                MIN_DATE,
                [_ReportedLot("o1", "i1", "i1", "1/1: 1.00000000 of 2.00000000 B1 in Kraken/Bob (lot t1/-1)")],
            ),
            (
                # Bought before the switch: at the switch the allocation gives Coinbase, the only wallet with funds, the lot i1/-1.
                "allocated",
                [
                    _In("i1", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Coinbase", "200", "1"),
                ],
                MIN_DATE,
                [_ReportedLot("o1", "i1", "i1", "1/1: 1.00000000 of 2.00000000 B1 in Coinbase/Bob (lot i1/-1)")],
            ),
            (
                # One transfer takes coins from two lots: Kraken gets a lot for each (t1/-1 from i1 and t1/-2 from i2), and the sale takes
                # 1 coin of the first and 0.5 of the second (FIFO).
                "split_transfer",
                [
                    _In("i1", "2025-01-10T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _In("i2", "2025-01-20T00:00:00+00:00", "Coinbase", "Buy", "200", "1"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "300", "2", "2"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "400", "1.5"),
                ],
                MIN_DATE,
                [
                    _ReportedLot("o1", "i1", "i1", "1/1: 1.00000000 of 1.00000000 B1 in Kraken/Bob (lot t1/-1)"),
                    _ReportedLot("o1", "i2", "i2", "1/1: 0.50000000 of 1.00000000 B1 in Kraken/Bob (lot t1/-2)"),
                ],
            ),
            (
                # A lot split between two wallets, and two hops: 2 of i1's 3 coins go to Kraken (t1/-1) and then to BlockFi (t2/-2). The sale
                # on BlockFi and the one of the coin left on Coinbase both come from i1.
                "multiple_hops",
                [
                    _In("i1", "2025-01-10T00:00:00+00:00", "Coinbase", "Buy", "100", "3"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "2", "2"),
                    _Intra("t2", "2025-02-10T00:00:00+00:00", "Kraken", "BlockFi", "150", "2", "2"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "BlockFi", "200", "1"),
                    _Out("o2", "2025-03-02T00:00:00+00:00", "Coinbase", "200", "1"),
                ],
                MIN_DATE,
                [
                    _ReportedLot("o1", "i1", "i1", "1/1: 1.00000000 of 2.00000000 B1 in BlockFi/Bob (lot t2/-2)"),
                    _ReportedLot("o2", "i1", "i1", "1/1: 1.00000000 of 3.00000000 B1"),
                ],
            ),
            (
                # A round trip: the coins go back to i1, so the sale takes them from i1 itself.
                "cycle",
                [
                    _In("i1", "2025-01-10T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "2", "2"),
                    _Intra("t2", "2025-02-10T00:00:00+00:00", "Kraken", "Coinbase", "150", "2", "2"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Coinbase", "200", "1"),
                ],
                MIN_DATE,
                [_ReportedLot("o1", "i1", "i1", "1/1: 1.00000000 of 2.00000000 B1")],
            ),
            (
                # A round trip after the allocation: the coins go back to Coinbase's allocated lot i1/-1.
                "cycle_after_allocation",
                [
                    _In("i1", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "2", "2"),
                    _Intra("t2", "2025-02-10T00:00:00+00:00", "Kraken", "Coinbase", "150", "2", "2"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Coinbase", "200", "1"),
                ],
                MIN_DATE,
                [_ReportedLot("o1", "i1", "i1", "1/1: 1.00000000 of 2.00000000 B1 in Coinbase/Bob (lot i1/-1)")],
            ),
            (
                # A report from 2025 (-f 2025-01-01) leaves the 2024 purchase out of the In-Out sheet: the lot is still i1, without a link.
                "filtered",
                [
                    _In("i1", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Coinbase", "200", "1"),
                ],
                date(2025, 1, 1),
                [_ReportedLot("o1", "i1", None, "1/1: 1.00000000 of 2.00000000 B1 in Coinbase/Bob (lot i1/-1)")],
            ),
        ]
        for name, transactions, from_date, want in cases:
            with self.subTest(name=name):
                self.assertEqual(self._get_reported_lots(name, transactions, from_date), want)

        # The US tax report shows the same unique ids and descriptions (columns 11 and 10 of the Capital Gains sheet).
        tax_rows = read_sheet_rows(
            Path("output") / Path("test_per_wallet_reports") / Path("split_transfer") / Path("split_transfer_fifo_tax_report_us.ods"), "Capital Gains"
        )
        got_us: List[Tuple[str, str, str]] = [(row[13], row[11], row[10]) for row in tax_rows or [] if len(row) > 13 and row[1] == _ASSET]
        want_us: List[Tuple[str, str, str]] = [
            ("o1", "i1", "1/1: 1.00000000 of 1.00000000 B1 in Kraken/Bob (lot t1/-1)"),
            ("o1", "i2", "1/1: 0.50000000 of 1.00000000 B1 in Kraken/Bob (lot t1/-2)"),
        ]
        self.assertEqual(got_us, want_us)

    def test_reports_with_artificial_lots(self) -> None:
        # Gain/losses on artificial lots (transfer destinations, unused basis allocation) must not break report generation, and Form 8949
        # "date acquired" must be the original acquisition date, not the transfer date.
        set_generation_language("en")
        configuration = _create_configuration(
            PerWalletConfiguration(timezone_name="UTC", unused_basis_allocation_method="fifo", unused_basis_allocation_wallet_order=(_COINBASE, _KRAKEN))
        )
        input_data = self._create_input_data(
            configuration,
            [
                _In("i1", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "100", "2", fiat_fee="1"),
                _In("i2", "2024-07-01T00:00:00+00:00", "Kraken", "Buy", "150", "1"),
                _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "2", "1.9"),
                _Out("o1", "2025-08-01T00:00:00+00:00", "Kraken", "300", "2.5"),
            ],
        )
        computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
        gain_losses = [gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)]
        self.assertTrue(any(gain_loss.acquired_lot is not None and gain_loss.acquired_lot.from_lot is not None for gain_loss in gain_losses))
        for gain_loss in gain_losses:
            if gain_loss.acquired_lot is not None:
                self.assertEqual(gain_loss.acquired_lot.cost_basis_timestamp, gain_loss.acquired_lot.original_lot.timestamp)
        # The sold percentage of an input lot includes sales of its artificial descendants: i1 (2 units) had 0.1 disposed of as a transfer fee
        # and 1.9 sold on Kraken.
        original_lot = next(lot for lot in input_data.unfiltered_in_transaction_set if isinstance(lot, InTransaction) and lot.unique_id == "i1")
        self.assertEqual(computed_data.get_in_lot_sold_percentage(original_lot), RP2Decimal("1"))

        output_dir = Path("output") / Path("test_per_wallet_tax_engine")
        shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True)
        for generator in (OpenPositionsGenerator(), FullReportGenerator(), TaxReportUSGenerator()):
            generator.generate(US(), {1970: "fifo"}, {_ASSET: computed_data}, str(output_dir), "per_wallet_", MIN_DATE, MAX_DATE, "en")
        self.assertEqual(len(list(output_dir.glob("per_wallet_*.ods"))), 3)

    # IRS FAQ A81 and A97: the crypto paid as a fee on a transfer between the taxpayer's own wallets is disposed of and gain or loss is
    # recognized on it; A53: that fee is not a digital asset transaction cost, so it is not added to the basis of the received units.
    # Reproduction from the review of eprbell/rp2#155 (R02), checked in the actual report cells: buy 1 unit for $100, transfer it when it is
    # worth $200 paying a 0.1 unit fee, sell the 0.9 received units for $270.
    def test_transfer_fee_is_a_disposal_in_reports(self) -> None:
        set_generation_language("en")
        configuration = _create_configuration()
        input_data = self._create_input_data(
            configuration,
            [
                _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "200", "1", "0.9"),
                _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "300", "0.9"),
            ],
        )
        computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
        output_dir = Path("output") / Path("test_per_wallet_tax_engine_fee")
        shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True)
        TaxReportUSGenerator().generate(US(), {1970: "fifo"}, {_ASSET: computed_data}, str(output_dir), "fee_", MIN_DATE, MAX_DATE, "en")
        report_path = output_dir / Path("fee_fifo_tax_report_us.ods")

        # Columns: amount, asset, date acquired, date sold or transacted, proceeds, cost basis, (f), (g), gain or loss, then the additional
        # transaction information (type, acquired lot fraction and id, taxable event fraction and id, capital gains type, full timestamp).
        def data_rows(sheet_name: str) -> List[List[str]]:
            rows = read_sheet_rows(report_path, sheet_name)
            self.assertIsNotNone(rows, msg=f"missing sheet {sheet_name}")
            return [row for row in rows or [] if row[1:2] == [_ASSET]]

        # The fee (MOVE): 0.1 unit of lot i1 disposed of at $200/unit: proceeds $20, basis $10, gain $10, with its source lot and transfer.
        want_fee_rows: List[List[str]] = [
            ["0.1", "B1", "01/02/2025", "02/01/2025", "20.0", "10.0", "", "", "10.0", "INTRA / MOVE"]
            + ["1/1: 0.10000000 of 1.00000000 B1", "i1", "1/1: 0.10000000 of 0.10000000 B1", "t1", "SHORT", "2025-02-01 00:00:00+00:00"]
        ]
        self.assertEqual(data_rows("Investment Expenses"), want_fee_rows)
        # The sale: the 0.9 received units keep their basis ($90) and acquisition date. (Its acquired lot id column is fixed by R17.)
        want_sale_rows: List[List[str]] = [["0.9", "B1", "01/02/2025", "03/01/2025", "270.0", "90.0", "", "", "180.0", "OUT / SELL"]]
        got_sale_rows: List[List[str]] = [row[:10] for row in data_rows("Capital Gains")]
        self.assertEqual(got_sale_rows, want_sale_rows)

    # R09 from the review of eprbell/rp2#155: a transfer that receives nothing (the whole amount went to fees) must not break the reports.
    # Example: buy 2 coins for $100 each on Coinbase, then send 1 to Kraken when it's worth $150 and receive 0. The whole coin is the fee,
    # shown like any transfer fee (INTRA / MOVE, with its source lot and transfer): $150 of proceeds, $100 of cost basis, $50 of gain. Open
    # Positions shows only Coinbase, with the coin it still holds: Kraken never received anything.
    def test_zero_receipt_transfer_in_reports(self) -> None:
        set_generation_language("en")
        configuration = _create_configuration()
        input_data = self._create_input_data(
            configuration,
            [
                _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "1", "0"),
            ],
        )
        computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
        output_dir = Path("output") / Path("test_per_wallet_tax_engine_r09")
        shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True)
        for generator in (OpenPositionsGenerator(), FullReportGenerator(), TaxReportUSGenerator()):
            generator.generate(US(), {1970: "fifo"}, {_ASSET: computed_data}, str(output_dir), "r09_", MIN_DATE, MAX_DATE, "en")
        self.assertEqual(len(list(output_dir.glob("r09_*.ods"))), 3)

        # Columns: amount, asset, date acquired, date sold or transacted, proceeds, cost basis, (f), (g), gain or loss, then the additional
        # transaction information (type, acquired lot fraction and id, taxable event fraction and id, capital gains type, full timestamp).
        tax_report_rows = read_sheet_rows(output_dir / Path("r09_fifo_tax_report_us.ods"), "Investment Expenses") or []
        want_fee_rows: List[List[str]] = [
            ["1.0", "B1", "01/02/2025", "02/01/2025", "150.0", "100.0", "", "", "50.0", "INTRA / MOVE"]
            + ["1/1: 1.00000000 of 2.00000000 B1", "i1", "1/1: 1.00000000 of 1.00000000 B1", "t1", "SHORT", "2025-02-01 00:00:00+00:00"]
        ]
        fee_rows: List[List[str]] = [row for row in tax_report_rows if row[1:2] == [_ASSET]]
        self.assertEqual(fee_rows, want_fee_rows)

        # Open Positions, "Asset" sheet: (holder, balance, cost basis); "Asset - Exchange" sheet: (holder, wallet, balance, cost basis).
        open_positions_path = output_dir / Path("r09_fifo_open_positions.ods")
        got_by_asset = [(row[1], row[2], row[4]) for row in read_sheet_rows(open_positions_path, "Asset") or [] if row[:1] == [_ASSET]]
        got_by_exchange = [(row[1], row[2], row[3], row[5]) for row in read_sheet_rows(open_positions_path, "Asset - Exchange") or [] if row[:1] == [_ASSET]]
        want_by_asset: List[Tuple[str, str, str]] = [("Bob", "1.0", "100.0")]
        want_by_exchange: List[Tuple[str, str, str, str]] = [("Bob", "Coinbase", "1.0", "100.0")]
        self.assertEqual(got_by_asset, want_by_asset)
        self.assertEqual(got_by_exchange, want_by_exchange)

    # R05 from the review of eprbell/rp2#155: after a transfer fee, the basis left in the reports must match the coins actually left.
    #
    # The rule in plain English: the coins paid as a transfer fee are treated as sold (IRS FAQ A81, A97), so they use up their own share of
    # the purchase cost. The fee is not added to the cost of the coins that arrive (FAQ A53), and the coins that arrive keep their purchase
    # cost and date (Treas. Reg. §1.1012-1(j)(1): the date units were transferred into a wallet is disregarded).
    #
    # Example: buy 10 coins for $1,000 ($100 each), move them to another wallet paying 1 coin as the fee, so 9 coins arrive. The fee coin
    # uses up $100 of cost, and the 9 coins that arrive carry the other $900. Sell 1 of them: 8 coins are left, with $800 of cost.
    #
    # The removed "basis carryover" option (R02) got this wrong: it spread the fee coin's $100 over the 9 coins that arrived ($111.11 each),
    # but the Open Positions report still subtracted only the coins sold, so 8 coins showed $900 instead of $888.89. Selling all 9 left
    # $100 of cost with no coins to hold it, and the Open Positions report crashed with KeyError: 'B1'.
    def test_transfer_fee_leaves_no_phantom_basis(self) -> None:
        class _Case(NamedTuple):
            description: str
            transactions: List[object]
            want: List[_GainLoss]
            # Fraction of lot i1 that is used up (fee plus sales), as shown in the "Sent/Sold" column of the full report.
            want_sold_fraction: str
            # Open Positions "Asset" sheet: asset, holder, balance, cost per unit, total cost of the coins still held.
            want_by_asset: List[List[str]]
            # Open Positions "Asset - Exchange" sheet: the same, per wallet.
            want_by_exchange: List[List[str]]

        buy_10 = _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10")
        # Move all 10 coins when they are worth $150 each, paying 1 coin as the fee. The fee is a sale of 1 coin for $150 with $100 of cost.
        move_all = _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "10", "9")
        fee_of_1_coin = _GainLoss("t1", "i1", "1", "100", "50", False)
        cases = [
            _Case(
                description="sell 1 of the 9 coins received: 8 coins left with $800 of cost",
                transactions=[buy_10, move_all, _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "200", "1")],
                want=[fee_of_1_coin, _GainLoss("o1", "i1", "1", "100", "100", False)],
                want_sold_fraction="0.2",
                want_by_asset=[["B1", "Bob", "8.0", "100.0", "800.0"]],
                want_by_exchange=[["B1", "Bob", "Kraken", "8.0", "100.0", "800.0"]],
            ),
            _Case(
                description="sell all 9 coins received: no coins and no cost left, and every report is generated",
                transactions=[buy_10, move_all, _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "200", "9")],
                want=[fee_of_1_coin, _GainLoss("o1", "i1", "9", "900", "900", False)],
                want_sold_fraction="1.0",
                want_by_asset=[],
                want_by_exchange=[],
            ),
            _Case(
                # Part of the lot stays behind and part travels: move 6 of the 10 coins paying 1 coin as the fee (5 arrive), then sell 3 of
                # the 5. Used up: 1 (fee) + 3 (sale) = 4 of 10 coins. Left: 4 coins on Coinbase and 2 on Kraken, $100 each.
                description="lot partly used up across wallets: 6 coins left with $600 of cost",
                transactions=[
                    buy_10,
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "6", "5"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "200", "3"),
                ],
                want=[fee_of_1_coin, _GainLoss("o1", "i1", "3", "300", "300", False)],
                want_sold_fraction="0.4",
                want_by_asset=[["B1", "Bob", "6.0", "100.0", "600.0"]],
                want_by_exchange=[["B1", "Bob", "Coinbase", "4.0", "100.0", "400.0"], ["B1", "Bob", "Kraken", "2.0", "100.0", "200.0"]],
            ),
            _Case(
                # Amounts that don't divide evenly must not leave a tiny rounding remainder of cost behind: buy 3 coins for $21 ($7 each),
                # move them paying 0.1 coin as the fee, sell the 2.9 that arrive. Fee: 0.1 × $7 = $0.70 of cost; sale: 2.9 × $7 = $20.30.
                description="uneven amounts: no rounding remainder of cost is left",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "7", "3"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "9", "3", "2.9"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "11", "2.9"),
                ],
                want=[_GainLoss("t1", "i1", "0.1", "0.7", "0.2", False), _GainLoss("o1", "i1", "2.9", "20.3", "11.6", False)],
                want_sold_fraction="1.0",
                want_by_asset=[],
                want_by_exchange=[],
            ),
        ]

        set_generation_language("en")
        configuration = _create_configuration()
        for case in cases:
            with self.subTest(name=case.description):
                input_data = self._create_input_data(configuration, case.transactions)
                computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
                gain_losses = [gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)]
                self.assertEqual(_sorted(self._to_tuples(gain_losses)), _sorted(self._want_tuples(case.want)))

                # Generating the reports must not fail (selling everything used to crash Open Positions with KeyError: 'B1').
                output_dir = Path("output") / Path("test_per_wallet_tax_engine_r05")
                shutil.rmtree(output_dir, ignore_errors=True)
                output_dir.mkdir(parents=True)
                for generator in (OpenPositionsGenerator(), FullReportGenerator(), TaxReportUSGenerator()):
                    generator.generate(US(), {1970: "fifo"}, {_ASSET: computed_data}, str(output_dir), "r05_", MIN_DATE, MAX_DATE, "en")

                # Full report, In-Flow Detail: the first column of lot i1 is the fraction of the lot used up, counting the fee and the sales
                # made from the wallet the coins were moved to.
                in_out_rows = read_sheet_rows(output_dir / Path("r05_fifo_rp2_full_report.ods"), f"{_ASSET} In-Out") or []
                got_sold_fraction: List[str] = [row[0] for row in in_out_rows if row[14:15] == ["i1"]]
                want_sold_fraction: List[str] = [case.want_sold_fraction]
                self.assertEqual(got_sold_fraction, want_sold_fraction)

                # Open Positions: the coins still held and their remaining cost (purchase cost minus the cost used up by the fee and sales).
                open_positions_path = output_dir / Path("r05_fifo_open_positions.ods")
                got_by_asset: List[List[str]] = [row[:5] for row in read_sheet_rows(open_positions_path, "Asset") or [] if row[:1] == [_ASSET]]
                self.assertEqual(got_by_asset, case.want_by_asset)
                got_by_exchange: List[List[str]] = [row[:6] for row in read_sheet_rows(open_positions_path, "Asset - Exchange") or [] if row[:1] == [_ASSET]]
                self.assertEqual(got_by_exchange, case.want_by_exchange)

    # R04 from the review of eprbell/rp2#155: the Open Positions report must show each wallet's actual remaining cost basis.
    #
    # The rule in plain English: from 2025, US taxpayers track cost basis wallet by wallet. Each wallet has its own coins with their own cost
    # and purchase dates (IRC §1012(c)(1): "on an account by account basis"; Treas. Reg. §1.1012-1(j)(1) and (j)(3): units are identified
    # within each wallet or broker account). Coins that were bought before 2025 and not yet sold get their cost assigned to the wallets at
    # the start of 2025 (Rev. Proc. 2024-28 §5.02, global allocation). So a wallet's cost basis is the cost of the coins that wallet holds.
    #
    # Example (from the review): in 2025 buy 1 coin for $100 in Coinbase and 1 coin for $1,000 in Kraken. Coinbase's cost basis is $100 and
    # Kraken's is $1,000. Before the fix the report spread the $1,100 total over the coins and showed $550 for each wallet.
    #
    # Each case checks the actual report cells: the balance and cost basis of every holder ("Asset" sheet) and every wallet ("Asset -
    # Exchange" sheet), that the per-unit cost basis is cost basis / balance, and that the wallets add up to the holder's row. The report shows
    # the holdings at the end of the report's to date (not the final ones), whatever its from date. If the to date is before 2025, the report
    # shows them like universal application always did (each wallet gets the average cost), and so do assets in universal application.
    def test_open_positions_show_each_wallet_actual_cost_basis(self) -> None:
        class _Case(NamedTuple):
            description: str
            transactions: List[object]
            # "Asset" sheet: (holder, balance, cost basis). "Asset - Exchange" sheet: (holder, wallet, balance, cost basis).
            want_by_asset: List[Tuple[str, str, str]]
            want_by_exchange: List[Tuple[str, str, str, str]]
            from_date: date = MIN_DATE
            to_date: date = MAX_DATE
            per_wallet_configuration: PerWalletConfiguration = _UTC
            # What the wallets hold at the to date, as (wallet, original lot, amount, cost basis, acquisition date), if checked.
            want_holdings: Optional[List[Tuple[str, str, str, str, str]]] = None
            # Use universal application (compute_tax()) instead of per-wallet application.
            universal: bool = False

        buy_100_coinbase = _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "1")
        buy_1000_kraken = _In("i2", "2025-01-03T00:00:00+00:00", "Kraken", "Buy", "1000", "1")
        # The same purchases in 2024, plus a 2025 purchase in BlockFi (so that the asset uses per-wallet application from 2025).
        history_2024: List[object] = [
            _In("i1", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
            _In("i2", "2024-07-01T00:00:00+00:00", "Kraken", "Buy", "1000", "1"),
            _In("i3", "2025-02-01T00:00:00+00:00", "BlockFi", "Buy", "500", "1"),
        ]
        cases = [
            _Case(
                description="the review's example: $100 in Coinbase, $1,000 in Kraken",
                transactions=[buy_100_coinbase, buy_1000_kraken],
                want_by_asset=[("Bob", "2.0", "1100.0")],
                want_by_exchange=[("Bob", "Coinbase", "1.0", "100.0"), ("Bob", "Kraken", "1.0", "1000.0")],
            ),
            _Case(
                description="partial sale: half of Kraken's coin is sold, so half of its $1,000 is left",
                transactions=[buy_100_coinbase, buy_1000_kraken, _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "1200", "0.5")],
                want_by_asset=[("Bob", "1.5", "600.0")],
                want_by_exchange=[("Bob", "Coinbase", "1.0", "100.0"), ("Bob", "Kraken", "0.5", "500.0")],
            ),
            _Case(
                description="complete sale: Kraken's coin is sold, so Kraken has no row",
                transactions=[buy_100_coinbase, buy_1000_kraken, _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "1200", "1")],
                want_by_asset=[("Bob", "1.0", "100.0")],
                want_by_exchange=[("Bob", "Coinbase", "1.0", "100.0")],
            ),
            _Case(
                # Kraken buys 2 coins for $1,000 each and sends 1.1 to Coinbase, paying 0.1 as the fee: the fee coin is sold (its $100 of
                # cost is used up) and the coin that arrives keeps its $1,000 cost. Coinbase: $100 + $1,000. Kraken: 0.9 x $1,000.
                description="transfer with a fee: the coin that arrives keeps its cost",
                transactions=[
                    buy_100_coinbase,
                    _In("i2", "2025-01-03T00:00:00+00:00", "Kraken", "Buy", "1000", "2"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Kraken", "Coinbase", "1200", "1.1", "1"),
                ],
                want_by_asset=[("Bob", "2.9", "2000.0")],
                want_by_exchange=[("Bob", "Coinbase", "2.0", "1100.0"), ("Bob", "Kraken", "0.9", "900.0")],
            ),
            _Case(
                # Kraken's coin moves to Coinbase on March 1st and both coins are sold on May 1st: at the end of March Coinbase holds both.
                description="to date filter: the holdings at the end of the to date, not the final ones",
                transactions=[
                    buy_100_coinbase,
                    buy_1000_kraken,
                    _Intra("t1", "2025-03-01T00:00:00+00:00", "Kraken", "Coinbase", "1200", "1", "1"),
                    _Out("o1", "2025-05-01T00:00:00+00:00", "Coinbase", "1300", "2"),
                ],
                to_date=date(2025, 3, 31),
                want_by_asset=[("Bob", "2.0", "1100.0")],
                want_by_exchange=[("Bob", "Coinbase", "2.0", "1100.0")],
                want_holdings=[("Coinbase", "i1", "1", "100", "2025-01-02"), ("Coinbase", "i2", "1", "1000", "2025-01-03")],
            ),
            _Case(
                description="from date filter: holdings bought before the from date are still shown",
                transactions=[buy_100_coinbase, buy_1000_kraken],
                from_date=date(2025, 2, 1),
                want_by_asset=[("Bob", "2.0", "1100.0")],
                want_by_exchange=[("Bob", "Coinbase", "1.0", "100.0"), ("Bob", "Kraken", "1.0", "1000.0")],
            ),
            _Case(
                # At the switch the coins bought in 2024 are allocated in FIFO order to Kraken first, then to Coinbase (the configured wallet
                # order): Kraken gets the $100 coin bought in Coinbase and Coinbase the $1,000 coin bought in Kraken. They keep their dates.
                description="coins bought before 2025: the allocation at the switch decides each wallet's cost basis",
                transactions=history_2024,
                per_wallet_configuration=_allocation_config((_KRAKEN, _COINBASE, _BLOCKFI)),
                want_by_asset=[("Bob", "3.0", "1600.0")],
                want_by_exchange=[("Bob", "BlockFi", "1.0", "500.0"), ("Bob", "Coinbase", "1.0", "1000.0"), ("Bob", "Kraken", "1.0", "100.0")],
                want_holdings=[
                    ("BlockFi", "i3", "1", "500", "2025-02-01"),
                    ("Coinbase", "i2", "1", "1000", "2024-07-01"),
                    ("Kraken", "i1", "1", "100", "2024-06-01"),
                ],
            ),
            _Case(
                description="to date before 2025: universal application, each wallet gets the average cost basis ($550)",
                transactions=history_2024,
                per_wallet_configuration=_allocation_config((_KRAKEN, _COINBASE, _BLOCKFI)),
                to_date=date(2024, 12, 31),
                want_by_asset=[("Bob", "2.0", "1100.0")],
                want_by_exchange=[("Bob", "Coinbase", "1.0", "550.0"), ("Bob", "Kraken", "1.0", "550.0")],
            ),
            _Case(
                description="universal application: unchanged, each wallet gets the average cost basis ($550)",
                transactions=[buy_100_coinbase, buy_1000_kraken],
                universal=True,
                want_by_asset=[("Bob", "2.0", "1100.0")],
                want_by_exchange=[("Bob", "Coinbase", "1.0", "550.0"), ("Bob", "Kraken", "1.0", "550.0")],
            ),
        ]

        set_generation_language("en")
        output_dir = Path("output") / Path("test_per_wallet_tax_engine_r04")
        for case in cases:
            with self.subTest(name=case.description):
                # Universal application runs without per-wallet settings, like the US before 2025.
                per_wallet_configuration = None if case.universal else case.per_wallet_configuration
                configuration = _create_configuration(per_wallet_configuration, from_date=case.from_date, to_date=case.to_date)
                input_data = self._create_input_data(configuration, case.transactions)
                engine = self._create_accounting_engine(None)
                if case.universal:
                    computed_data = compute_tax(configuration, engine, input_data)
                else:
                    computed_data = compute_tax_per_wallet(configuration, engine, input_data)
                wallet_lots = computed_data.wallet_lots
                if case.universal or case.to_date < date(2025, 1, 1):
                    self.assertIsNone(wallet_lots)
                else:
                    assert wallet_lots is not None
                    if case.want_holdings is not None:
                        want_holdings: List[_Holding] = [
                            _Holding(wallet, lot, RP2Decimal(amount), RP2Decimal(basis), day) for wallet, lot, amount, basis, day in case.want_holdings
                        ]
                        self.assertEqual(_holdings(wallet_lots), want_holdings)

                shutil.rmtree(output_dir, ignore_errors=True)
                output_dir.mkdir(parents=True)
                OpenPositionsGenerator().generate(US(), {1970: "fifo"}, {_ASSET: computed_data}, str(output_dir), "r04_", case.from_date, case.to_date, "en")
                report_path = output_dir / Path("r04_fifo_open_positions.ods")
                # Columns: asset, holder, (exchange), balance, per-unit cost basis, cost basis, cost basis weight %, ...
                asset_rows = [row for row in read_sheet_rows(report_path, "Asset") or [] if row[:1] == [_ASSET]]
                exchange_rows = [row for row in read_sheet_rows(report_path, "Asset - Exchange") or [] if row[:1] == [_ASSET]]
                got_by_asset: List[Tuple[str, str, str]] = [(row[1], row[2], row[4]) for row in asset_rows]
                got_by_exchange: List[Tuple[str, str, str, str]] = [(row[1], row[2], row[3], row[5]) for row in exchange_rows]
                self.assertEqual(got_by_asset, case.want_by_asset)
                self.assertEqual(got_by_exchange, case.want_by_exchange)

                # The per-unit cost basis is the cost basis divided by the balance, and the cost basis weight is relative to the total.
                total_cost_basis = sum(float(row[5]) for row in exchange_rows)
                for row in asset_rows:
                    self.assertAlmostEqual(float(row[3]), float(row[4]) / float(row[2]))
                for row in exchange_rows:
                    self.assertAlmostEqual(float(row[4]), float(row[5]) / float(row[3]))
                    self.assertAlmostEqual(float(row[6]), float(row[5]) / total_cost_basis)
                # The wallets of each holder add up to the holder's row.
                for row in asset_rows:
                    self.assertAlmostEqual(sum(float(exchange_row[3]) for exchange_row in exchange_rows if exchange_row[1] == row[1]), float(row[2]))
                    self.assertAlmostEqual(sum(float(exchange_row[5]) for exchange_row in exchange_rows if exchange_row[1] == row[1]), float(row[4]))

    # A sale whose crypto_out_with_fee differs from crypto_out_no_fee + crypto_fee (both are input fields, and exchange rounding can make
    # them differ): the tax computation and the wallet lots use crypto_out_with_fee, while balances use crypto_out_no_fee + crypto_fee. This
    # used to stop the whole run with an internal error: now it's a warning, and the reports are generated from the lots.
    # Example: buy 2 coins for $100 each, then sell with crypto_out_no_fee = 1, crypto_fee = 0.001 and crypto_out_with_fee = 1.00100001.
    # The lots hold 0.99899999 coins (2 - 1.00100001), with $99.899999 of cost basis, while the balance is 0.999 (2 - 1 - 0.001).
    def test_inconsistent_sale_amounts_are_a_warning(self) -> None:
        set_generation_language("en")
        configuration = _create_configuration()
        input_data = self._create_input_data(
            configuration,
            [
                _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                _Out("o1", "2025-02-01T00:00:00+00:00", "Coinbase", "200", "1", "0.001", crypto_out_with_fee="1.00100001"),
            ],
        )
        with self.assertLogs("rp2", level="WARNING") as logs:
            computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
        self.assertTrue(any("the lots of Coinbase/Bob add up to 0.99899999" in message for message in logs.output), msg=str(logs.output))
        wallet_lots = computed_data.wallet_lots
        assert wallet_lots is not None
        want_holdings: List[_Holding] = [_Holding("Coinbase", "i1", RP2Decimal("0.99899999"), RP2Decimal("99.899999"), "2025-01-02")]
        self.assertEqual(_holdings(wallet_lots), want_holdings)

        output_dir = Path("output") / Path("test_per_wallet_reports_inconsistent_sale")
        shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True)
        for generator in (OpenPositionsGenerator(), FullReportGenerator(), TaxReportUSGenerator()):
            generator.generate(US(), {1970: "fifo"}, {_ASSET: computed_data}, str(output_dir), "inconsistent_", MIN_DATE, MAX_DATE, "en")
        exchange_rows = read_sheet_rows(output_dir / Path("inconsistent_fifo_open_positions.ods"), "Asset - Exchange") or []
        got_by_exchange: List[List[str]] = [row[1:4] + row[5:6] for row in exchange_rows if row[:1] == [_ASSET]]
        want_by_exchange: List[List[str]] = [["Bob", "Coinbase", "0.99899999", "99.899999"]]
        self.assertEqual(got_by_exchange, want_by_exchange)

    # R10 from the review of eprbell/rp2#155: the opening allocation report records how the unused basis was assigned to the wallets at the
    # switch (Rev. Proc. 2024-28 global allocation), as it was then: transactions after the switch don't change it.
    #
    # The rule in plain English: at the start of 2025 the lots that universal application hasn't sold yet (the unused basis) are sorted with
    # the allocation method and assigned to the wallets in the configured order, each wallet up to the coins it holds then, so a lot can be
    # split between two wallets. Each piece keeps the cost and the purchase date of its lot.
    #
    # Example (B1 below): in 2024 buy 4 coins on Coinbase for $100 each (i1), 4 on Kraken for $300 each (i2) and 4 on Coinbase for $200 each
    # (i3), move 2 coins from Coinbase to Kraken and sell 1 coin on Kraken. Universal FIFO sells 1 coin of i1, so the unused lots are i1 (3
    # coins), i2 (4) and i3 (4), and at the switch Kraken holds 5 coins and Coinbase 6. The wallet order is Kraken, BlockFi, Coinbase: BlockFi
    # holds nothing, so it gets nothing. FIFO sorts the lots by date (i1, i2, i3): Kraken gets the 3 coins of i1 and 2 of i2, Coinbase the other
    # 2 of i2 and the 4 of i3. LIFO, HIFO and LOFO sort them differently and split another lot.
    # B2 has its own rule (LIFO, Coinbase first) and B3 is held by one wallet only, so its allocation is automatic. Each method is checked
    # with and without transactions after the switch: the report must be the same.
    def test_opening_allocation_report(self) -> None:
        # Lots: unique id -> (input row, acquisition date, exchange, price, coins bought, coins unused at the switch).
        lots: Dict[str, Tuple[str, str, str, str, str, str]] = {
            "i1": ("1", "2024-01-02", "Coinbase", "100", "4", "3"),
            "i2": ("2", "2024-02-01", "Kraken", "300", "4", "4"),
            "i3": ("3", "2024-03-01", "Coinbase", "200", "4", "4"),
            "j1": ("1", "2024-01-05", "Coinbase", "50", "2", "2"),
            "j2": ("2", "2024-02-05", "Kraken", "60", "2", "2"),
            "k1": ("1", "2024-04-01", "Coinbase", "1000", "1", "1"),
        }
        transactions: Dict[str, List[object]] = {
            "B1": [
                _In("i1", "2024-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "4"),
                _In("i2", "2024-02-01T00:00:00+00:00", "Kraken", "Buy", "300", "4"),
                _In("i3", "2024-03-01T00:00:00+00:00", "Coinbase", "Buy", "200", "4"),
                _Intra("t1", "2024-04-01T00:00:00+00:00", "Coinbase", "Kraken", "250", "2", "2"),
                _Out("o1", "2024-05-01T00:00:00+00:00", "Kraken", "250", "1"),
            ],
            "B2": [
                _In("j1", "2024-01-05T00:00:00+00:00", "Coinbase", "Buy", "50", "2"),
                _In("j2", "2024-02-05T00:00:00+00:00", "Kraken", "Buy", "60", "2"),
            ],
            "B3": [_In("k1", "2024-04-01T00:00:00+00:00", "Coinbase", "Buy", "1000", "1")],
        }
        later_transactions: Dict[str, List[object]] = {
            "B1": [
                _Out("o2", "2025-02-01T00:00:00+00:00", "Kraken", "500", "5"),
                _Intra("t2", "2025-03-01T00:00:00+00:00", "Coinbase", "Kraken", "500", "1", "1"),
            ],
            "B2": [_Out("p1", "2025-02-01T00:00:00+00:00", "Coinbase", "70", "2")],
            "B3": [],
        }
        # For each method: the unused lots of B1 in the order of the method, and the pieces allocated to each wallet (wallet, lot, coins).
        # B2 always uses its own rule: LIFO puts j2 first, and Coinbase is filled first.
        method_2_allocation: Dict[str, Tuple[List[str], List[Tuple[str, str, str]]]] = {
            "fifo": (["i1", "i2", "i3"], [("Kraken", "i1", "3"), ("Kraken", "i2", "2"), ("Coinbase", "i2", "2"), ("Coinbase", "i3", "4")]),
            "lifo": (["i3", "i2", "i1"], [("Kraken", "i3", "4"), ("Kraken", "i2", "1"), ("Coinbase", "i2", "3"), ("Coinbase", "i1", "3")]),
            "hifo": (["i2", "i3", "i1"], [("Kraken", "i2", "4"), ("Kraken", "i3", "1"), ("Coinbase", "i3", "3"), ("Coinbase", "i1", "3")]),
            "lofo": (["i1", "i3", "i2"], [("Kraken", "i1", "3"), ("Kraken", "i3", "2"), ("Coinbase", "i3", "2"), ("Coinbase", "i2", "4")]),
        }
        b2_lots_and_pieces: Tuple[List[str], List[Tuple[str, str, str]]] = (["j2", "j1"], [("Coinbase", "j2", "2"), ("Kraken", "j1", "2")])
        b3_lots_and_pieces: Tuple[List[str], List[Tuple[str, str, str]]] = (["k1"], [("Coinbase", "k1", "1")])
        # The allocation method of each run is set by name in the configuration (see PerWalletConfiguration below).
        method_names: List[str] = ["fifo", "lifo", "hifo", "lofo"]

        def number(value: RP2Decimal) -> str:
            return str(float(value))

        # The expected rows of an asset in the Wallets, Unused Lots and Allocation sheets.
        def want_asset_rows(asset: str, wallet_order: List[str], allocation: Tuple[List[str], List[Tuple[str, str, str]]]) -> _OpeningAllocationRows:
            lot_order, pieces = allocation
            unused_rows: List[List[str]] = []
            for order, lot in enumerate(lot_order, start=1):
                row, day, exchange, price, bought, unused = lots[lot]
                unused_basis = RP2Decimal(price) * RP2Decimal(unused)
                unused_rows.append([asset, number(RP2Decimal(order)), lot, number(RP2Decimal(row)), day, exchange, "Bob", "BUY"])
                unused_rows[-1] += [number(RP2Decimal(price)), number(RP2Decimal(bought)), number(RP2Decimal(unused)), number(RP2Decimal(price))]
                unused_rows[-1].append(number(unused_basis))
            total_crypto = RP2Decimal(sum((RP2Decimal(coins) for _, _, coins in pieces), ZERO))
            total_basis = RP2Decimal(sum((RP2Decimal(lots[lot][3]) * RP2Decimal(coins) for _, lot, coins in pieces), ZERO))
            unused_rows.append([f"Total {asset}"] + [""] * 9 + [number(total_crypto), "", number(total_basis)])
            allocation_rows: List[List[str]] = []
            for wallet, lot, coins in pieces:
                row, day, _, price, _, _ = lots[lot]
                basis = RP2Decimal(price) * RP2Decimal(coins)
                allocation_rows.append(
                    [asset, wallet, "Bob", lot, number(RP2Decimal(row)), day, number(RP2Decimal(coins)), number(RP2Decimal(price)), number(basis)]
                )
            allocation_rows.append([f"Total {asset}", "", "", "", "", "", number(total_crypto), "", number(total_basis)])
            wallet_rows: List[List[str]] = []
            for order, wallet in enumerate(wallet_order, start=1):
                wallet_pieces = [(lot, RP2Decimal(coins)) for piece_wallet, lot, coins in pieces if piece_wallet == wallet]
                crypto = RP2Decimal(sum((coins for _, coins in wallet_pieces), ZERO))
                basis = RP2Decimal(sum((RP2Decimal(lots[lot][3]) * coins for lot, coins in wallet_pieces), ZERO))
                # The opening balance is what the wallet held at the switch: it matches what it got.
                wallet_rows.append(
                    [asset, number(RP2Decimal(order)), wallet, "Bob", number(crypto), number(crypto), number(basis), number(RP2Decimal(len(wallet_pieces)))]
                )
            wallet_rows.append([f"Total {asset}", "", "", "", number(total_crypto), number(total_crypto), number(total_basis), number(RP2Decimal(len(pieces)))])
            return _OpeningAllocationRows(wallet_rows, unused_rows, allocation_rows)

        set_generation_language("en")
        output_dir = Path("output") / Path("test_per_wallet_reports_opening_allocation")
        shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True)
        report_path = output_dir / Path("r10_fifo_opening_allocation.ods")
        switch = "2025-01-01T00:00:00+00:00"
        for method_name in method_names:
            per_wallet_configuration = PerWalletConfiguration(
                timezone_name="UTC",
                unused_basis_allocation_method=method_name,
                unused_basis_allocation_wallet_order=(_KRAKEN, _BLOCKFI, _COINBASE),
                asset_2_unused_basis_allocation_method={"B2": "lifo"},
                asset_2_unused_basis_allocation_wallet_order={"B2": (_COINBASE, _KRAKEN)},
            )
            # Hand-computed expected cells (BlockFi is in the order with nothing: it gets nothing). Numbers are as the cells hold them.
            b1_wallets, b1_unused, b1_allocation = want_asset_rows("B1", ["Kraken", "BlockFi", "Coinbase"], method_2_allocation[method_name])
            b1_wallets[1][4:8] = ["0", "0", "0", "0"]
            b2_wallets, b2_unused, b2_allocation = want_asset_rows("B2", ["Coinbase", "Kraken"], b2_lots_and_pieces)
            b3_wallets, b3_unused, b3_allocation = want_asset_rows("B3", ["Coinbase"], b3_lots_and_pieces)
            want_sheets: Dict[str, List[List[str]]] = {
                "Summary": [
                    ["B1", switch, "UTC", "Configured", method_name.upper(), "unused_basis_allocation_method", "Kraken/Bob, BlockFi/Bob, Coinbase/Bob"]
                    + ["unused_basis_allocation_wallet_order", "11.0", "11.0", "11.0", "2300.0", "2300.0"],
                    ["B2", switch, "UTC", "Configured", "LIFO", "unused_basis_allocation_method.B2", "Coinbase/Bob, Kraken/Bob"]
                    + ["unused_basis_allocation_wallet_order.B2", "4.0", "4.0", "4.0", "220.0", "220.0"],
                    # Only Coinbase holds B3: no wallet order is needed, and the method is the default one.
                    ["B3", switch, "UTC", "Automatic", method_name.upper(), "unused_basis_allocation_method", "Coinbase/Bob", ""]
                    + ["1.0", "1.0", "1.0", "1000.0", "1000.0"],
                ],
                "Wallets": b1_wallets + b2_wallets + b3_wallets,
                "Unused Lots": b1_unused + b2_unused + b3_unused,
                "Allocation": b1_allocation + b2_allocation + b3_allocation,
            }
            for with_later_transactions in (False, True):
                with self.subTest(method=method_name, with_later_transactions=with_later_transactions):
                    configuration = _create_configuration(per_wallet_configuration)
                    asset_to_computed_data: Dict[str, ComputedData] = {}
                    for asset in ("B1", "B2", "B3"):
                        input_data = self._create_input_data(
                            configuration, transactions[asset] + (later_transactions[asset] if with_later_transactions else []), asset
                        )
                        # The allocation method of each asset comes from the configuration: B2's override is lifo.
                        asset_to_computed_data[asset] = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
                    OpeningAllocationGenerator().generate(US(), {1970: "fifo"}, asset_to_computed_data, str(output_dir), "r10_", MIN_DATE, MAX_DATE, "en")
                    for sheet_name, want_rows in want_sheets.items():
                        # The first three rows are the title and the two header rows.
                        got_rows: List[List[str]] = (read_sheet_rows(report_path, sheet_name) or [])[3:]
                        self.assertEqual(got_rows, want_rows, msg=sheet_name)

        # A report that ends before the switch has no opening allocation: no file, and the file of the earlier run is removed.
        self.assertTrue(report_path.exists())
        configuration = _create_configuration(per_wallet_configuration, to_date=date(2024, 12, 31))
        input_data = self._create_input_data(configuration, transactions["B1"] + later_transactions["B1"], "B1")
        computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
        self.assertIsNone(computed_data.opening_allocation)
        OpeningAllocationGenerator().generate(US(), {1970: "fifo"}, {"B1": computed_data}, str(output_dir), "r10_", MIN_DATE, date(2024, 12, 31), "en")
        self.assertFalse(report_path.exists())


if __name__ == "__main__":
    unittest.main()

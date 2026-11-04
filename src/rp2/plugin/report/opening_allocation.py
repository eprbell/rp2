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

import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Set, Union

from rp2.abstract_country import AbstractCountry
from rp2.account import Account
from rp2.computed_data import ComputedData
from rp2.in_transaction import InTransaction
from rp2.localization import _
from rp2.logger import create_logger
from rp2.opening_allocation import OpeningAllocation
from rp2.plugin.report.abstract_ods_generator import AbstractODSGenerator
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError

LOGGER: logging.Logger = create_logger("opening_allocation")

_SUMMARY: str = "Summary"
_WALLETS: str = "Wallets"
_UNUSED_LOTS: str = "Unused Lots"
_ALLOCATION: str = "Allocation"
_TEMPLATE_SHEETS: Set[str] = {_SUMMARY, _WALLETS, _UNUSED_LOTS, _ALLOCATION}
_TEMPLATE_SHEETS_TO_KEEP: Set[str] = {"__" + sheet_name for sheet_name in _TEMPLATE_SHEETS}


# A cell of a total row: its value and its data style (the number format: "crypto", "fiat" or "default").
class _TotalCell(NamedTuple):
    value: Union[RP2Decimal, int, str]
    data_style: str


_EMPTY_TOTAL_CELL: _TotalCell = _TotalCell("", "default")


# The opening allocation report: how the cost basis of the units held at the switch to per-wallet application was assigned to the wallets
# that held them (Rev. Proc. 2024-28 global allocation, see OpeningAllocation and UnusedBasisAllocator). It shows the allocation as it was
# made at the switch: transactions after the switch don't change it. It has a block of rows for each asset in these sheets:
# - Summary: the switch instant in the tax time zone, the rule (allocation method, wallet order and the configuration fields they come from,
#   or Automatic if only one wallet held units) and the totals that must match: the units of the unused lots, of the allocated pieces and
#   of the wallets at the switch, and the cost basis of the unused lots and of the allocated pieces;
# - Wallets: the units each wallet held at the switch (its opening balance) and what it received: each wallet is filled up to its opening
#   balance, so the two match;
# - Unused Lots: the lots left unused by universal application, in the order of the allocation method;
# - Allocation: one row for each piece of an unused lot allocated to a wallet: wallet, source lot, acquisition date, units and cost basis.
# Example (see also OpeningAllocation): in 2024 buy 10 coins for $100 each on Coinbase (lot i1) and 10 for $200 each on Kraken (lot i2), and
# move 5 coins from Coinbase to Kraken. With FIFO and the wallet order Kraken, Coinbase the Allocation sheet has three rows: Kraken gets 10
# coins of i1 ($1,000) and 5 coins of i2 ($1,000), Coinbase 5 coins of i2 ($1,000).
# The file is generated only if some asset has an opening allocation: it uses per-wallet application, the report reaches the switch and some
# wallet held units then.
class Generator(AbstractODSGenerator):
    OUTPUT_FILE: str = "opening_allocation.ods"
    HEADER_ROWS = 3

    __legend: List[List[str]] = []
    __summary_header_names_row_1: List[str] = []
    __summary_header_names_row_2: List[str] = []
    __wallets_header_names_row_1: List[str] = []
    __wallets_header_names_row_2: List[str] = []
    __unused_lots_header_names_row_1: List[str] = []
    __unused_lots_header_names_row_2: List[str] = []
    __allocation_header_names_row_1: List[str] = []
    __allocation_header_names_row_2: List[str] = []

    # pylint: disable=line-too-long
    def _setup_text_data(self, country: AbstractCountry) -> None:
        currency_code: str = country.currency_iso_code.upper()

        self.__legend = [
            # fmt: off
            [_("Opening Allocation")],
            [_("How the cost basis of the units held at the switch to per-wallet application was assigned to the wallets that held them")],
            [_("The lots not yet sold under universal application (unused basis) are sorted with the allocation method and assigned to the wallets in the wallet order, each wallet up to the units it held at the switch: a lot can be split across wallets")],
            [_("Each piece keeps the per-unit cost basis and the acquisition date of its lot. The report shows the allocation made at the switch: later transactions don't change it")],
            [""],
            [_("General")],
            [_("Accounting Method")],
            [_("From Date Filter")],
            [_("To Date Filter")],
            [""],
            [_("Summary Fields")],
            [_("Asset"), _("Crypto / asset symbol")],
            [_("Switch Instant"), _("Start of per-wallet application: midnight at the start of January 1st of the first per-wallet year, in the time zone of the configuration file")],
            [_("Time Zone"), _("The timezone field of the country section of the configuration file: all dates are computed in it")],
            [_("Allocation"), _("Automatic if only one wallet held units at the switch (they all go to it), Configured otherwise")],
            [_("Allocation Method"), _("Accounting method that sorts the unused lots (e.g. FIFO: oldest first)")],
            [_("Method Field"), _("Configuration field the method comes from: a name ending with .<asset> is an override for the asset")],
            [_("Wallet Order"), _("Order in which the wallets are filled, as <exchange>/<holder>")],
            [_("Wallet Order Field"), _("Configuration field the wallet order comes from: a name ending with .<asset> is an override for the asset")],
            [_("Unused Crypto / {} Unused Cost Basis").format(currency_code), _("Units and cost basis of the unused lots (Unused Lots tab)")],
            [_("Allocated Crypto / {} Allocated Cost Basis").format(currency_code), _("Units and cost basis of the allocated pieces (Allocation tab): they match the unused lots")],
            [_("Opening Balance"), _("Units held by the wallets at the switch, from the transactions before it (Wallets tab): they match the allocated units")],
            [""],
            [_("Wallets Fields")],
            [_("Order"), _("Position of the wallet in the wallet order (empty if it isn't in the order: it held nothing at the switch)")],
            [_("Exchange / Holder"), _("The wallet")],
            [_("Opening Balance"), _("Units held by the wallet at the switch")],
            [_("Allocated Crypto / {} Allocated Cost Basis").format(currency_code), _("Units and cost basis allocated to the wallet: the units match its opening balance")],
            [_("Lot Pieces"), _("Number of pieces of unused lots allocated to the wallet (Allocation tab)")],
            [""],
            [_("Unused Lots Fields")],
            [_("Order"), _("Position of the lot in the order of the allocation method")],
            [_("Unique ID / Input Row"), _("The lot in the input file: its unique_id and its row in the sheet of the asset")],
            [_("Acquisition Date"), _("Original acquisition date of the lot, in the time zone of the configuration file")],
            [_("Exchange / Holder"), _("Wallet where the lot was acquired (the allocation can assign it to other wallets)")],
            [_("Transaction Type"), _("How the lot was acquired (e.g. BUY)")],
            [_("{} Spot Price").format(currency_code), _("Price per unit when the lot was acquired (HIFO and LOFO sort the lots by it)")],
            [_("Lot Crypto"), _("Units of the lot")],
            [_("Unused Crypto"), _("Units of the lot not disposed of under universal application before the switch")],
            [_("{} Per Unit Cost Basis").format(currency_code), _("Cost basis per unit of the lot, purchase fee included")],
            [_("{} Unused Cost Basis").format(currency_code), _("Unused Crypto * Per Unit Cost Basis")],
            [""],
            [_("Allocation Fields")],
            [_("Exchange / Holder"), _("Wallet the piece was allocated to")],
            [_("Unique ID / Input Row / Acquisition Date"), _("Source lot of the piece (see the Unused Lots tab)")],
            [_("Allocated Crypto"), _("Units of the piece")],
            [_("{} Per Unit Cost Basis").format(currency_code), _("Cost basis per unit of the source lot")],
            [_("{} Allocated Cost Basis").format(currency_code), _("Allocated Crypto * Per Unit Cost Basis")],
            # fmt: on
        ]

        self.__summary_header_names_row_1 = [
            "",
            _("Switch"),
            "",
            "",
            _("Allocation"),
            _("Method"),
            _("Wallet"),
            _("Wallet Order"),
            _("Unused"),
            _("Allocated"),
            _("Opening"),
            _("{} Unused").format(currency_code),
            _("{} Allocated").format(currency_code),
        ]
        self.__summary_header_names_row_2 = [
            _("Asset"),
            _("Instant"),
            _("Time Zone"),
            _("Allocation"),
            _("Method"),
            _("Field"),
            _("Order"),
            _("Field"),
            _("Crypto"),
            _("Crypto"),
            _("Balance"),
            _("Cost Basis"),
            _("Cost Basis"),
        ]

        self.__wallets_header_names_row_1 = [
            "",
            "",
            "",
            "",
            _("Opening"),
            _("Allocated"),
            _("{} Allocated").format(currency_code),
            _("Lot"),
        ]
        self.__wallets_header_names_row_2 = [
            _("Asset"),
            _("Order"),
            _("Exchange"),
            _("Holder"),
            _("Balance"),
            _("Crypto"),
            _("Cost Basis"),
            _("Pieces"),
        ]

        self.__unused_lots_header_names_row_1 = [
            "",
            "",
            _("Unique"),
            _("Input"),
            _("Acquisition"),
            "",
            "",
            _("Transaction"),
            _("{} Spot").format(currency_code),
            _("Lot"),
            _("Unused"),
            _("{} Per Unit").format(currency_code),
            _("{} Unused").format(currency_code),
        ]
        self.__unused_lots_header_names_row_2 = [
            _("Asset"),
            _("Order"),
            _("ID"),
            _("Row"),
            _("Date"),
            _("Exchange"),
            _("Holder"),
            _("Type"),
            _("Price"),
            _("Crypto"),
            _("Crypto"),
            _("Cost Basis"),
            _("Cost Basis"),
        ]

        self.__allocation_header_names_row_1 = [
            "",
            "",
            "",
            _("Unique"),
            _("Input"),
            _("Acquisition"),
            _("Allocated"),
            _("{} Per Unit").format(currency_code),
            _("{} Allocated").format(currency_code),
        ]
        self.__allocation_header_names_row_2 = [
            _("Asset"),
            _("Exchange"),
            _("Holder"),
            _("ID"),
            _("Row"),
            _("Date"),
            _("Crypto"),
            _("Cost Basis"),
            _("Cost Basis"),
        ]

    def generate(
        self,
        country: AbstractCountry,
        years_2_accounting_method_names: Dict[int, str],
        asset_to_computed_data: Dict[str, ComputedData],
        output_dir_path: str,
        output_file_prefix: str,
        from_date: date,
        to_date: date,
        generation_language: str,
    ) -> None:
        if not isinstance(asset_to_computed_data, Dict):
            raise RP2TypeError(f"Parameter 'asset_to_computed_data' has non-Dict value {asset_to_computed_data}")

        opening_allocations: List[OpeningAllocation] = []
        for asset, computed_data in sorted(asset_to_computed_data.items()):
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)
            if computed_data.opening_allocation is not None:
                opening_allocations.append(computed_data.opening_allocation)
        if not opening_allocations:
            # Nothing to report (e.g. the report ends before the switch): a file left by an earlier run would describe an allocation that
            # isn't part of this run, so it's removed, like other generators replace their files.
            output_file_path: Path = self._get_output_file_path(years_2_accounting_method_names, output_dir_path, output_file_prefix, self.OUTPUT_FILE)
            if output_file_path.exists():
                output_file_path.unlink()
                LOGGER.info("Plugin '%s': removed %s, generated by an earlier run", __name__, output_file_path.resolve())
            LOGGER.info(
                "Plugin '%s': no opening allocation (the report doesn't reach the switch to per-wallet application, or no wallet held "
                "units then): no output",
                __name__,
            )
            return

        self._setup_text_data(country)
        template_path: str = self._get_template_path("opening_allocation", country, generation_language)
        output_file: Any = self._initialize_output_file(
            country=country,
            legend_data=self.__legend,
            years_2_accounting_method_names=years_2_accounting_method_names,
            output_dir_path=output_dir_path,
            output_file_prefix=output_file_prefix,
            output_file_name=self.OUTPUT_FILE,
            template_path=template_path,
            template_sheets_to_keep=_TEMPLATE_SHEETS_TO_KEEP,
            from_date=from_date,
            to_date=to_date,
        )

        self.__style_legend(output_file.sheets[_("Legend")])
        summary_sheet: Any = output_file.sheets[_SUMMARY]
        wallets_sheet: Any = output_file.sheets[_WALLETS]
        unused_lots_sheet: Any = output_file.sheets[_UNUSED_LOTS]
        allocation_sheet: Any = output_file.sheets[_ALLOCATION]
        self._fill_header(_("Opening Allocation Summary"), self.__summary_header_names_row_1, self.__summary_header_names_row_2, summary_sheet, 0, 0)
        self._fill_header(_("Wallets at the Switch"), self.__wallets_header_names_row_1, self.__wallets_header_names_row_2, wallets_sheet, 0, 0)
        self._fill_header(_("Unused Lots at the Switch"), self.__unused_lots_header_names_row_1, self.__unused_lots_header_names_row_2, unused_lots_sheet, 0, 0)
        self._fill_header(_("Allocated Lot Pieces"), self.__allocation_header_names_row_1, self.__allocation_header_names_row_2, allocation_sheet, 0, 0)

        row_indexes: Dict[str, int] = {sheet_name: self.HEADER_ROWS for sheet_name in _TEMPLATE_SHEETS}
        for opening_allocation in opening_allocations:
            row_indexes[_SUMMARY] = self.__fill_summary(summary_sheet, row_indexes[_SUMMARY], opening_allocation)
            row_indexes[_WALLETS] = self.__fill_wallets(wallets_sheet, row_indexes[_WALLETS], opening_allocation)
            row_indexes[_UNUSED_LOTS] = self.__fill_unused_lots(unused_lots_sheet, row_indexes[_UNUSED_LOTS], opening_allocation)
            row_indexes[_ALLOCATION] = self.__fill_allocation(allocation_sheet, row_indexes[_ALLOCATION], opening_allocation)

        output_file.save()
        LOGGER.info("Plugin '%s' output: %s", __name__, Path(output_file.docname).resolve())

    # The legend is filled without styles (see AbstractODSGenerator._initialize_output_file()): titles get the title style, and field names
    # (the rows with a description) the header style.
    def __style_legend(self, sheet: Any) -> None:
        titles: Set[str] = {
            _("Opening Allocation"),
            _("General"),
            _("Summary Fields"),
            _("Wallets Fields"),
            _("Unused Lots Fields"),
            _("Allocation Fields"),
        }
        general_fields: Set[str] = {_("Accounting Method"), _("From Date Filter"), _("To Date Filter")}
        for row_index, row in enumerate(self.__legend):
            if row[0] in titles:
                self._apply_style_to_cell(sheet, row_index, 0, "title_default")
            elif row[0] in general_fields or len(row) == 2:
                self._apply_style_to_cell(sheet, row_index, 0, "header_default")
                if len(row) == 2:
                    self._apply_style_to_cell(sheet, row_index, 1, "transparent_default")

    # One row per asset: the rule and the totals that must match (see the comment of the class).
    def __fill_summary(self, sheet: Any, row_index: int, opening_allocation: OpeningAllocation) -> int:
        sheet.append_rows(1)
        self._fill_cell(sheet, row_index, 0, opening_allocation.asset)
        self._fill_cell(sheet, row_index, 1, opening_allocation.switch_timestamp.isoformat())
        self._fill_cell(sheet, row_index, 2, opening_allocation.timezone_name)
        self._fill_cell(sheet, row_index, 3, _("Automatic") if opening_allocation.is_automatic else _("Configured"))
        self._fill_cell(sheet, row_index, 4, opening_allocation.allocation_method_name.upper())
        self._fill_cell(sheet, row_index, 5, opening_allocation.allocation_method_field or "")
        self._fill_cell(sheet, row_index, 6, ", ".join(_get_wallet_name(account) for account in opening_allocation.wallet_order))
        self._fill_cell(sheet, row_index, 7, opening_allocation.wallet_order_field or "")
        self._fill_cell(sheet, row_index, 8, opening_allocation.unused_crypto, data_style="crypto")
        self._fill_cell(sheet, row_index, 9, opening_allocation.allocated_crypto, data_style="crypto")
        self._fill_cell(sheet, row_index, 10, opening_allocation.opening_balance, data_style="crypto")
        self._fill_cell(sheet, row_index, 11, opening_allocation.unused_cost_basis, data_style="fiat")
        self._fill_cell(sheet, row_index, 12, opening_allocation.allocated_cost_basis, data_style="fiat")
        return row_index + 1

    # One row per wallet (see OpeningAllocation.wallets), then the asset's total.
    def __fill_wallets(self, sheet: Any, row_index: int, opening_allocation: OpeningAllocation) -> int:
        wallets: List[Account] = opening_allocation.wallets
        sheet.append_rows(len(wallets) + 1)
        for account in wallets:
            order: Optional[int] = opening_allocation.wallet_order.index(account) + 1 if account in opening_allocation.wallet_order else None
            allocated_lots: List[InTransaction] = opening_allocation.get_allocated_lots(account)
            self._fill_cell(sheet, row_index, 0, opening_allocation.asset)
            self._fill_cell(sheet, row_index, 1, order if order is not None else "")
            self._fill_cell(sheet, row_index, 2, account.exchange)
            self._fill_cell(sheet, row_index, 3, account.holder)
            self._fill_cell(sheet, row_index, 4, opening_allocation.get_opening_balance(account), data_style="crypto")
            self._fill_cell(sheet, row_index, 5, RP2Decimal(sum((lot.crypto_in for lot in allocated_lots), ZERO)), data_style="crypto")
            self._fill_cell(sheet, row_index, 6, RP2Decimal(sum((lot.fiat_in_with_fee for lot in allocated_lots), ZERO)), data_style="fiat")
            self._fill_cell(sheet, row_index, 7, len(allocated_lots))
            row_index += 1
        self.__fill_total_row(
            sheet,
            row_index,
            opening_allocation.asset,
            8,
            {
                4: _TotalCell(opening_allocation.opening_balance, "crypto"),
                5: _TotalCell(opening_allocation.allocated_crypto, "crypto"),
                6: _TotalCell(opening_allocation.allocated_cost_basis, "fiat"),
                7: _TotalCell(len(opening_allocation.allocated_lots), "default"),
            },
        )
        return row_index + 1

    # One row per unused lot, in the order of the allocation method, then the asset's total.
    def __fill_unused_lots(self, sheet: Any, row_index: int, opening_allocation: OpeningAllocation) -> int:
        sheet.append_rows(len(opening_allocation.unused_lots) + 1)
        for order, unused_lot in enumerate(opening_allocation.unused_lots, start=1):
            lot: InTransaction = unused_lot.acquired_lot
            self._fill_cell(sheet, row_index, 0, opening_allocation.asset)
            self._fill_cell(sheet, row_index, 1, order)
            self._fill_cell(sheet, row_index, 2, lot.unique_id)
            self._fill_cell(sheet, row_index, 3, lot.row)
            self._fill_cell(sheet, row_index, 4, _get_acquisition_date(lot))
            self._fill_cell(sheet, row_index, 5, lot.exchange)
            self._fill_cell(sheet, row_index, 6, lot.holder)
            self._fill_cell(sheet, row_index, 7, lot.transaction_type.value.upper())
            self._fill_cell(sheet, row_index, 8, lot.spot_price, data_style="fiat")
            self._fill_cell(sheet, row_index, 9, lot.crypto_in, data_style="crypto")
            self._fill_cell(sheet, row_index, 10, unused_lot.amount, data_style="crypto")
            self._fill_cell(sheet, row_index, 11, lot.fiat_in_with_fee / lot.crypto_in, data_style="fiat")
            self._fill_cell(sheet, row_index, 12, unused_lot.cost_basis, data_style="fiat")
            row_index += 1
        self.__fill_total_row(
            sheet,
            row_index,
            opening_allocation.asset,
            13,
            {10: _TotalCell(opening_allocation.unused_crypto, "crypto"), 12: _TotalCell(opening_allocation.unused_cost_basis, "fiat")},
        )
        return row_index + 1

    # One row per allocated piece, in the order of allocation (wallet by wallet), then the asset's total.
    def __fill_allocation(self, sheet: Any, row_index: int, opening_allocation: OpeningAllocation) -> int:
        sheet.append_rows(len(opening_allocation.allocated_lots) + 1)
        for allocated_lot in opening_allocation.allocated_lots:
            source_lot: InTransaction = allocated_lot.original_lot
            self._fill_cell(sheet, row_index, 0, opening_allocation.asset)
            self._fill_cell(sheet, row_index, 1, allocated_lot.exchange)
            self._fill_cell(sheet, row_index, 2, allocated_lot.holder)
            self._fill_cell(sheet, row_index, 3, source_lot.unique_id)
            self._fill_cell(sheet, row_index, 4, source_lot.row)
            self._fill_cell(sheet, row_index, 5, _get_acquisition_date(allocated_lot))
            self._fill_cell(sheet, row_index, 6, allocated_lot.crypto_in, data_style="crypto")
            self._fill_cell(sheet, row_index, 7, allocated_lot.fiat_in_with_fee / allocated_lot.crypto_in, data_style="fiat")
            self._fill_cell(sheet, row_index, 8, allocated_lot.fiat_in_with_fee, data_style="fiat")
            row_index += 1
        self.__fill_total_row(
            sheet,
            row_index,
            opening_allocation.asset,
            9,
            {6: _TotalCell(opening_allocation.allocated_crypto, "crypto"), 8: _TotalCell(opening_allocation.allocated_cost_basis, "fiat")},
        )
        return row_index + 1

    # The total row of an asset, in bold: "Total" and the asset in the first column, then the given cells by column (the other columns are
    # empty). Example: {4: _TotalCell(RP2Decimal("1.5"), "crypto")} writes 1.5 with the crypto format in column 4.
    def __fill_total_row(self, sheet: Any, row_index: int, asset: str, column_count: int, column_2_cell: Dict[int, _TotalCell]) -> None:
        for column in range(column_count):
            cell: _TotalCell = column_2_cell.get(column, _EMPTY_TOTAL_CELL)
            value: Union[RP2Decimal, int, str] = f"{_('Total')} {asset}" if column == 0 else cell.value
            self._fill_cell(sheet, row_index, column, value, visual_style="bold_border", data_style=cell.data_style)


# Original acquisition date of a lot: the date of its cost_basis_timestamp in the tax time zone (see Configuration.tax_timezone).
def _get_acquisition_date(lot: InTransaction) -> str:
    return lot.configuration.get_tax_date(lot.cost_basis_timestamp).isoformat()


def _get_wallet_name(account: Account) -> str:
    return f"{account.exchange}/{account.holder}"

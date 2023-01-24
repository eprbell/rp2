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

# pylint: disable=too-many-lines

import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Set, cast

import ezodf

from rp2.abstract_country import AbstractCountry
from rp2.abstract_entry import AbstractEntry
from rp2.abstract_transaction import AbstractTransaction
from rp2.balance import BalanceSet
from rp2.computed_data import ComputedData, YearlyGainLoss
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
from rp2.in_transaction import InTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.localization import _
from rp2.logger import create_logger
from rp2.out_transaction import OutTransaction
from rp2.plugin.report.abstract_ods_generator import AbstractODSGenerator
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError
from rp2.transaction_set import TransactionSet

LOGGER: logging.Logger = create_logger("rp2_full_report")


class _TransactionVisualStyle(NamedTuple):
    year: int
    visual_style: str
    highlighted_style: str


class _BorderStyle(NamedTuple):
    year: int
    border_suffix: str


class _AssetAndYear(NamedTuple):
    asset: str
    year: int


_ZERO: RP2Decimal = RP2Decimal(0)


class Generator(AbstractODSGenerator):

    MIN_ROWS: int = 40
    MAX_COLUMNS: int = 40
    OUTPUT_FILE: str = "rp2_full_report.ods"

    TEMPLATE_SHEETS_TO_KEEP: Set[str] = {"__Summary"}

    __in_out_sheet_transaction_2_row: Dict[AbstractTransaction, int] = {}
    __tax_sheet_year_2_row: Dict[_AssetAndYear, int] = {}

    __legend: List[List[str]] = []
    __yearly_gain_loss_summary_header_names_row_1: List[str] = []
    __yearly_gain_loss_summary_header_names_row_2: List[str] = []
    __in_header_names_row_1: List[str] = []
    __in_header_names_row_2: List[str] = []
    __out_header_names_row_1: List[str] = []
    __out_header_names_row_2: List[str] = []
    __intra_header_names_row_1: List[str] = []
    __intra_header_names_row_2: List[str] = []
    __balance_header_names_row_1: List[str] = []
    __balance_header_names_row_2: List[str] = []
    __gain_loss_summary_header_names_row_1: List[str] = []
    __gain_loss_summary_header_names_row_2: List[str] = []
    __gain_loss_detail_header_names_row_1: List[str] = []
    __gain_loss_detail_header_names_row_2: List[str] = []

    # pylint: disable=line-too-long
    def _setup_text_data(self, country: AbstractCountry) -> None:

        currency_code: str = country.currency_iso_code.upper()

        self.__legend: List[List[str]] = [
            # fmt: off
            [_("General")],
            [_("Accounting Method")],
            [_("From Date Filter")],
            [_("To Date Filter")],
            [""],
            [_("Sheet Types")],
            [_("<Crypto> In-Out"), _("Captures all transactions coming in (IN), going out (OUT) and transferring across accounts (INTRA)")],
            [_("<Crypto> Tax"), _("Computation of balances and gain / loss")],
            [""],
            [_("Table Types")],
            [_("In-Flow Detail"), _("Transactions that added new crypto to accounts (e.g. buy, etc.). Only EARN-typed transactions are taxable events (interest received on crypto)")],
            [_("Out-Flow Detail"), _("Transactions that removed some crypto from accounts (e.g. sell, send as gift, etc.). These are taxable events")],
            [_("Intra-Flow Detail"), _("Movements across accounts without increasing/decreasing total value of crypto owned. The amount transferred is non-taxable but the transfer fee is considered a crypto sale and it is a taxable event")],
            [_("Gain / Loss Summary"), _("Computed gain and loss for the given cryptocurrency, organized by year and capital gains type (LONG or SHORT)")],
            [_("Account Balances"), _("Computed balances of all accounts. Useful to double-check that the input transactions have been entered correctly. If values don’t match actual balances some data is missing or wrong")],
            [_("Average Price"), _("Average price at which the crypto was acquired")],
            [_("Gain / Loss Detail"), _("Detailed computation of gain and loss: each lot is divided into fractions, which are used to calculate the cost basis and the gain/loss")],
            [""],
            [_("In-Flow Detail")],
            [_("Sent/Sold"), _("Lots that have been sent or sold, according to the order defined by the Accounting Method (see General section)")],
            [_("Timestamp"), _("Time at which the transaction occurred")],
            [_("Asset"), _("Which cryptocurrency was transacted (e.g. BTC, ETH, etc.)")],
            [_("Exchange"), _("Exchange or wallet on which the transaction occurred (e.g. Coinbase, Coinbase Pro, BlockFi, etc.)")],
            [_("Holder"), _("Exchange account or wallet owner")],
            [_("Transaction Type"), _("Type of the transaction (BUY, GIFT, INTEREST, STAKING, etc.)")],
            [_("Spot Price"), _("Value of 1 unit of the given cryptocurrency at the time the transaction occurred")],
            [_("Crypto In"), _("How much of the given cryptocurrency was acquired with the transaction")],
            [_("Crypto In Running Sum"), _("Running sum of crypto received")],
            [_("{} Fee").format(currency_code), _("{} value of the fees").format(currency_code)],
            [_("{} In No Fee").format(currency_code), _("{} value of the transaction without fees").format(currency_code)],
            [_("{} In With Fee").format(currency_code), _("{} value of the transaction with fees").format(currency_code)],
            [_("Taxable Event"), _("Does the transaction contain a taxable event? If so the taxable amount is highlighted in yellow")],
            [_("Unique Id"), _("Hash or exchange-specific unique identifier for the transaction")],
            [_("Notes"), _("Description of the transaction")],
            [""],
            [_("Out-Flow Detail")],
            [_("Timestamp"), _("Time at which the transaction occurred")],
            [_("Asset"), _("Which cryptocurrency was transacted (e.g. BTC, ETH, etc.)")],
            [_("Exchange"), _("Exchange or wallet on which the transaction occurred (e.g. Coinbase, Coinbase Pro, BlockFi, etc.)")],
            [_("Holder"), _("Exchange account or wallet owner")],
            [_("Transaction Type"), _("Type of the transaction (DONATE, GIFT, SELL, etc.)")],
            [_("Spot Price"), _("Value of 1 unit of the given cryptocurrency at the time the transaction occurred")],
            [_("Crypto Out"), _("How much of the given cryptocurrency was sent with the transaction")],
            [_("Crypto Fee"), _("Crypto value of the fees")],
            [_("Crypto Out Running Sum"), _("Running sum of crypto sent")],
            [_("Crypto Fee Running Sum"), _("Running sum of crypto fees")],
            [_("{} Out").format(currency_code), _("{} value of the transaction without fees").format(currency_code)],
            [_("{} Fee").format(currency_code), _("{} value of the fees").format(currency_code)],
            [_("Taxable Event"), _("Does the transaction contain a taxable event? If so the taxable amount is highlighted in yellow")],
            [_("Unique Id"), _("Hash or exchange-specific unique identifier for the transaction")],
            [_("Notes"), _("Description of the transaction")],
            [""],
            [_("Intra-Flow Detail")],
            [_("Timestamp"), _("Time at which the transaction occurred")],
            [_("Asset"), _("Which cryptocurrency was transacted (e.g. BTC, ETH, etc.)")],
            [_("From Exchange"), _("Exchange or wallet from which the transfer of crypto occurred (e.g. Coinbase, Coinbase Pro, BlockFi, etc.)")],
            [_("From Holder"), _("Owner of the exchange account or wallet from which the transfer of crypto occurred")],
            [_("To Exchange"), _("Exchange or wallet to which the transfer of crypto occurred (e.g. Coinbase, Coinbase Pro, BlockFi, etc.)")],
            [_("To Holder"), _("Owner of the exchange account or wallet to which the transfer of crypto occurred")],
            [_("Spot Price"), _("Value of 1 unit of the given cryptocurrency at the time the transaction occurred")],
            [_("Crypto Sent"), _("How much of the given cryptocurrency was sent with the transaction")],
            [_("Crypto Received"), _("How much of the given cryptocurrency was received with the transaction")],
            [_("Crypto Fee"), _("Crypto value of the fees")],
            [_("Crypto Fee Running Sum"), _("Running sum of crypto fees")],
            [_("{} Fee").format(currency_code), _("{} value of the fees").format(currency_code)],
            [_("Taxable Event"), _("Does the transaction contain a taxable event? If so the taxable amount is highlighted in yellow")],
            [_("Unique Id"), _("Hash of the transaction")],
            [_("Notes"), _("Description of the transaction")],
            [""],
            [_("Gain / Loss Summary")],
            [_("Year"), _("Summary year")],
            [_("Asset"), _("Which cryptocurrency (e.g. BTC, ETH, etc.)")],
            [_("Capital Gains"), _("Sum of all capital gains in {} for transactions of the given capital gains type").format(currency_code)],
            [_("Capital Gains Type"), _("LONG (> 1 year) or SHORT (< 1 year)")],
            [_("Transaction Type"), _("EARN (crypto earned through interest, etc.), GIFT (crypto given), SOLD (crypto sold) OR INTRA (fees for transferring crypto across accounts)")],
            [_("Crypto Taxable Total"), _("Sum of all taxable events in crypto for transactions of the given capital gains type")],
            [_("{} Taxable Total").format(currency_code), _("Sum of all taxable events in {} for transactions of the given capital gains type").format(currency_code)],
            [_("{} Total Cost Basis").format(currency_code), _("Sum of all cost bases in {} for transactions of the given capital gains type").format(currency_code)],
            [""],
            [_("Account Balances")],
            [_("Exchange"), _("Exchange or wallet on which the transaction occurred (e.g. Coinbase, Coinbase Pro, BlockFi, etc.)")],
            [_("Holder"), _("Name of the exchange or wallet account holder")],
            [_("Asset"), _("Which cryptocurrency was transacted (e.g. BTC, ETH, etc.)")],
            [_("Acquired Balance"), _("Balance of all the BUY and EARN transactions for a given exchange and holder")],
            [_("Sent Balance"), _("Balance of all the SEND and SOLD transactions for which the given exchange and holder are sender")],
            [_("Received Balance"), _("Balance of all the SEND and SOLD transactions for which the given exchange and holder are receiver")],
            [_("Final Balance"), _("Final balance of all transactions for a given exchange and holder")],
            [""],
            [_("Average Price")],
            [_("Average Price Paid Per 1 crypto"), _("Average price at which the crypto was acquired, across all transactions")],
            [""],
            [_("Gain / Loss Detail")],
            [_("Crypto Amount"), _("Crypto amount for the given taxable event fraction")],
            [_("Asset"), _("Which cryptocurrency (e.g. BTC, ETH, etc.)")],
            [_("Crypto Amt Running Sum"), _("Running sum of crypto amount")],
            [_("Capital Gains"), _("Sum of all capital gains in {} for transactions of the given capital gains type").format(currency_code)],
            [_("Capital Gains Type"), _("LONG (> 1 year) or SHORT (< 1 year)")],
            [_("Taxable Event Timestamp"), _("Time at which the taxable event occurred")],
            [_("Taxable Event Direction/Type"), _("Direction (IN/OUT/INTRA) and type (BUY, SOLD, etc) of the taxable event")],
            [_("Taxable Event Fraction %"), _("Percentage of the taxable event")],
            [_("Taxable Event {} Amount Fraction").format(currency_code), _("{} amount of this taxable event fraction").format(currency_code)],
            [_("Taxable Event Spot Price"), _("Value of 1 unit of the given cryptocurrency at the time the taxable event occurred")],
            [_("Taxable Event Fraction Description"), _("English description of this taxable event fraction")],
            [_("Acquired Lot Timestamp"), _("Time at which the in-transaction occurred")],
            [_("Acquired Lot Fraction %"), _("Percentage of the in-transaction")],
            [_("Acquired Lot {} Amount Fraction").format(currency_code), _("{} amount of this in-transaction fraction").format(currency_code)],
            [_("Acquired Lot {} Fee Fraction").format(currency_code), _("{} fee of this in-transaction fraction").format(currency_code)],
            [_("Acquired Lot {} Cost Basis").format(currency_code), _("{} cost basis of this in-transaction fraction").format(currency_code)],
            [_("Acquired Lot Spot Price"), _("Value of 1 unit of the given cryptocurrency at the time the in-transaction occurred")],
            [_("Acquired Lot Fraction Description"), _("English description of this in-transaction fraction")],
            # fmt: on
        ]

        self.__yearly_gain_loss_summary_header_names_row_1: List[str] = [
            "",
            "",
            _("Capital"),
            _("Capital"),
            _("Transaction"),
            _("Crypto"),
            _("USD"),
            _("USD Total"),
        ]

        self.__yearly_gain_loss_summary_header_names_row_2: List[str] = [
            _("Year"),
            _("Asset"),
            _("Gains"),
            _("Gains Type"),
            _("Type"),
            _("Taxable Total"),
            _("Taxable Total"),
            _("Cost Basis"),
        ]

        self.__in_header_names_row_1: List[str] = [
            "",
            "",
            "",
            "",
            "",
            _("Transaction"),
            "",
            _("Crypto"),
            _("Crypto In"),
            "",
            _("{} In").format(currency_code),
            _("{} In").format(currency_code),
            _("Taxable"),
            "",
            "",
            "",
        ]

        self.__in_header_names_row_2: List[str] = [
            _("Sent/Sold"),
            _("Timestamp"),
            _("Asset"),
            _("Exchange"),
            _("Holder"),
            _("Type"),
            _("Spot Price"),
            _("In"),
            _("Running Sum"),
            _("{} Fee").format(currency_code),
            _("No Fee"),
            _("With Fee"),
            _("Event"),
            _("N/A"),
            _("Unique Id"),
            _("Notes"),
        ]

        self.__out_header_names_row_1: List[str] = [
            "",
            "",
            "",
            "",
            _("Transaction"),
            "",
            "",
            "",
            _("Crypto Out"),
            _("Crypto Fee"),
            "",
            "",
            _("Taxable"),
            "",
            "",
        ]

        self.__out_header_names_row_2: List[str] = [
            _("Timestamp"),
            _("Asset"),
            _("Exchange"),
            _("Holder"),
            _("Type"),
            _("Spot Price"),
            _("Crypto Out"),
            _("Crypto Fee"),
            _("Running Sum"),
            _("Running Sum"),
            _("{} Out").format(currency_code),
            _("{} Fee").format(currency_code),
            _("Event"),
            _("Unique Id"),
            _("Notes"),
        ]

        self.__intra_header_names_row_1: List[str] = [
            "",
            "",
            _("From"),
            _("From"),
            "",
            "",
            "",
            "",
            _("Crypto"),
            "",
            _("Crypto Fee"),
            "",
            _("Taxable"),
            "",
            "",
        ]

        self.__intra_header_names_row_2: List[str] = [
            _("Timestamp"),
            _("Asset"),
            _("Exchange"),
            _("Holder"),
            _("To Exchange"),
            _("To Holder"),
            _("Spot Price"),
            _("Crypto Sent"),
            _("Received"),
            _("Crypto Fee"),
            _("Running Sum"),
            _("{} Fee").format(currency_code),
            _("Event"),
            _("Unique Id"),
            _("Notes"),
        ]

        self.__balance_header_names_row_1: List[str] = [
            "",
            "",
            "",
            _("Acquired"),
            _("Sent"),
            _("Received"),
            _("Final"),
        ]

        self.__balance_header_names_row_2: List[str] = [
            _("Exchange"),
            _("Holder"),
            _("Asset"),
            _("Balance"),
            _("Balance"),
            _("Balance"),
            _("Balance"),
        ]

        self.__gain_loss_summary_header_names_row_1: List[str] = [
            "",
            "",
            _("Capital"),
            _("Capital"),
            _("Transaction"),
            _("Crypto"),
            _("{}").format(currency_code),
            _("{} Total").format(currency_code),
        ]

        self.__gain_loss_summary_header_names_row_2: List[str] = [
            _("Year"),
            _("Asset"),
            _("Gains"),
            _("Gains Type"),
            _("Type"),
            _("Taxable Total"),
            _("Taxable Total"),
            _("Cost Basis"),
        ]

        self.__gain_loss_detail_header_names_row_1: List[str] = [
            _("Crypto"),
            "",
            _("Crypto Amt"),
            _("Capital"),
            _("Capital"),
            _("Taxable Event"),
            _("Taxable Event"),
            _("Taxable Event"),
            _("Taxable Event {}").format(currency_code),
            _("Taxable Event"),
            "",
            _("Taxable Event"),
            _("Acquired Lot"),
            _("Acquired Lot"),
            _("Acquired Lot {}").format(currency_code),
            _("Acquired Lot {}").format(currency_code),
            _("Acquired Lot {}").format(currency_code),
            _("Acquired Lot"),
            "",
            _("Acquired Lot Fraction"),
        ]

        self.__gain_loss_detail_header_names_row_2: List[str] = [
            _("Amount"),
            _("Asset"),
            _("Running Sum"),
            _("Gains"),
            _("Gains Type"),
            _("Timestamp"),
            _("Direction/Type"),
            _("Fraction %"),
            _("Amount Fraction"),
            _("Spot Price"),
            _("Unique Id"),
            _("Fraction Description"),
            _("Timestamp"),
            _("Fraction %"),
            _("Amount Fraction"),
            _("Fee Fraction"),
            _("Cost Basis"),
            _("Spot Price"),
            _("Unique Id"),
            _("Description"),
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

        self._setup_text_data(country)

        template_path: str = self._get_template_path("rp2_full_report", country, generation_language)

        output_file: Any
        output_file = self._initialize_output_file(
            country=country,
            legend_data=self.__legend,
            years_2_accounting_method_names=years_2_accounting_method_names,
            output_dir_path=output_dir_path,
            output_file_prefix=output_file_prefix,
            output_file_name=self.OUTPUT_FILE,
            template_path=template_path,
            template_sheets_to_keep=self.TEMPLATE_SHEETS_TO_KEEP,
            from_date=from_date,
            to_date=to_date,
        )
        asset: str
        computed_data: ComputedData

        summary_sheet = output_file.sheets["Summary"]
        summary_row_index: int = self._fill_header(
            _("Yearly Gain / Loss Summary"),
            self.__yearly_gain_loss_summary_header_names_row_1,
            self.__yearly_gain_loss_summary_header_names_row_2,
            summary_sheet,
            0,
            0,
        )
        for asset, computed_data in asset_to_computed_data.items():
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)
            summary_row_index = self.__generate_asset(computed_data, output_file, summary_row_index)

        summary_sheet.name = _("Summary")

        output_file.save()
        LOGGER.info("Plugin '%s' output: %s", __name__, Path(output_file.docname).resolve())

    @staticmethod
    def get_in_out_sheet_name(asset: str) -> str:
        return _("{} In-Out").format(asset)

    @staticmethod
    def get_tax_sheet_name(asset: str) -> str:
        return _("{} Tax").format(asset)

    def __get_number_of_rows_in_transaction_sheet(self, computed_data: ComputedData) -> int:
        return self.MIN_ROWS + computed_data.in_transaction_set.count + computed_data.out_transaction_set.count + computed_data.intra_transaction_set.count

    def __get_number_of_rows_in_output_sheet(self, computed_data: ComputedData) -> int:
        return self.MIN_ROWS + len(computed_data.yearly_gain_loss_list) + computed_data.balance_set.count + computed_data.gain_loss_set.count

    def __generate_asset(self, computed_data: ComputedData, output_file: Any, summary_row_index: int) -> int:
        asset: str = computed_data.asset
        transaction_sheet_name: str = self.get_in_out_sheet_name(asset)
        output_sheet_name: str = self.get_tax_sheet_name(asset)

        transaction_sheet: Any = ezodf.Table(transaction_sheet_name)
        output_sheet: Any = ezodf.Table(output_sheet_name)
        summary_sheet: Any = output_file.sheets["Summary"]

        output_file.sheets += transaction_sheet
        output_file.sheets += output_sheet

        transaction_sheet.reset(size=(self.__get_number_of_rows_in_transaction_sheet(computed_data), self.MAX_COLUMNS))
        output_sheet.reset(size=(self.__get_number_of_rows_in_output_sheet(computed_data), self.MAX_COLUMNS))

        new_lines: int = len(computed_data.yearly_gain_loss_list)
        if new_lines:
            summary_sheet.append_rows(new_lines)

        row_index: int = 0
        row_index = self.__generate_in_table(transaction_sheet, computed_data, row_index)
        row_index = self.__generate_out_table(transaction_sheet, computed_data, row_index + 2)
        row_index = self.__generate_intra_table(transaction_sheet, computed_data, row_index + 2)

        row_index = 0
        row_index = self.__generate_gain_loss_summary(output_sheet, computed_data.yearly_gain_loss_list, row_index)
        row_index = self.__generate_account_balances(output_sheet, computed_data.balance_set, row_index + 2)
        row_index = self.__generate_average_price_per_unit(output_sheet, asset, computed_data.price_per_unit, row_index + 2)
        row_index = self.__generate_gain_loss_detail(output_sheet, asset, computed_data, row_index + 2)

        return self.__generate_yearly_gain_loss_summary(summary_sheet, asset, computed_data.yearly_gain_loss_list, summary_row_index)

    @staticmethod
    def __get_transaction_visual_style(transaction: AbstractTransaction, year: int) -> _TransactionVisualStyle:
        visual_style: str = "transparent"
        highlighted_style: str = "transparent"
        if transaction.is_taxable():
            visual_style = "taxable_event"
            highlighted_style = "highlighted"
        if year == 0:
            year = transaction.timestamp.year
        if transaction.timestamp.year != year:
            visual_style = f"{visual_style}_border"
            highlighted_style = f"{highlighted_style}_border"
            year = transaction.timestamp.year
        return _TransactionVisualStyle(year, visual_style, highlighted_style)

    @staticmethod
    def __get_border_style(current_year: int, year: int) -> _BorderStyle:
        border_suffix: str = ""
        if year == 0:
            year = current_year
        if current_year != year:
            border_suffix = "_border"
            year = current_year
        return _BorderStyle(year, border_suffix)

    def __generate_in_table(self, sheet: Any, computed_data: ComputedData, row_index: int) -> int:
        row_index = self._fill_header(_("In-Flow Detail"), self.__in_header_names_row_1, self.__in_header_names_row_2, sheet, row_index, 0)

        in_transaction_set: TransactionSet = computed_data.in_transaction_set
        entry: AbstractEntry
        year: int = 0
        visual_style: str
        previous_transaction: Optional[InTransaction] = None
        border_style: _BorderStyle
        border_suffix: str = ""
        for entry in in_transaction_set:
            transaction: InTransaction = cast(InTransaction, entry)
            highlighted_style: str
            transaction_visual_style: _TransactionVisualStyle = self.__get_transaction_visual_style(transaction, year)
            year = transaction_visual_style.year
            border_style = self.__get_border_style(entry.timestamp.year, year)
            border_suffix = border_style.border_suffix
            visual_style = transaction_visual_style.visual_style
            highlighted_style = transaction_visual_style.highlighted_style
            in_lot_sold_percentage: Optional[RP2Decimal] = computed_data.get_in_lot_sold_percentage(transaction)

            # Write _ZERO only on the first in_transaction if there are no sold lots
            if in_lot_sold_percentage == _ZERO and previous_transaction is not None:
                in_lot_sold_percentage = None
            self._fill_cell(
                sheet,
                row_index,
                0,
                in_lot_sold_percentage if in_lot_sold_percentage is not None else "",
                data_style="percent",
                visual_style="acquired_lot" + border_suffix if in_lot_sold_percentage is not None else "transparent",
            )
            self._fill_cell(sheet, row_index, 1, transaction.timestamp, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 2, transaction.asset, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 3, transaction.exchange, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 4, transaction.holder, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 5, transaction.transaction_type.value.upper(), visual_style=visual_style)
            self._fill_cell(sheet, row_index, 6, transaction.spot_price, data_style="fiat", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 7, transaction.crypto_in, data_style="crypto", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 8, computed_data.get_crypto_in_running_sum(transaction), data_style="crypto", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 9, transaction.fiat_fee, data_style="fiat", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 10, transaction.fiat_in_no_fee, data_style="fiat", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 11, transaction.fiat_in_with_fee, data_style="fiat", visual_style=highlighted_style)
            self._fill_cell(sheet, row_index, 12, _("YES") if transaction.is_taxable() else _("NO"), data_style="fiat", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 13, "", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 14, transaction.unique_id, visual_style="transparent")
            self._fill_cell(sheet, row_index, 15, transaction.notes, visual_style="transparent")

            self.__in_out_sheet_transaction_2_row[transaction] = row_index + 1

            previous_transaction = transaction
            row_index += 1

        return row_index

    def __generate_out_table(self, sheet: Any, computed_data: ComputedData, row_index: int) -> int:
        row_index = self._fill_header(_("Out-Flow Detail"), self.__out_header_names_row_1, self.__out_header_names_row_2, sheet, row_index, 1)

        out_transaction_set: TransactionSet = computed_data.out_transaction_set

        entry: AbstractEntry
        year: int = 0
        for entry in out_transaction_set:
            transaction: OutTransaction = cast(OutTransaction, entry)
            visual_style: str
            highlighted_style: str
            transaction_visual_style: _TransactionVisualStyle = self.__get_transaction_visual_style(transaction, year)
            year = transaction_visual_style.year
            visual_style = transaction_visual_style.visual_style
            highlighted_style = transaction_visual_style.highlighted_style
            self._fill_cell(sheet, row_index, 0, "", visual_style="transparent")
            self._fill_cell(sheet, row_index, 1, transaction.timestamp, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 2, transaction.asset, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 3, transaction.exchange, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 4, transaction.holder, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 5, transaction.transaction_type.value.upper(), visual_style=visual_style)
            self._fill_cell(sheet, row_index, 6, transaction.spot_price, visual_style=visual_style, data_style="fiat")
            self._fill_cell(sheet, row_index, 7, transaction.crypto_out_no_fee, visual_style=visual_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 8, transaction.crypto_fee, visual_style=visual_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 9, computed_data.get_crypto_out_running_sum(transaction), data_style="crypto", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 10, computed_data.get_crypto_out_fee_running_sum(transaction), data_style="crypto", visual_style=visual_style)
            self._fill_cell(
                sheet,
                row_index,
                11,
                transaction.crypto_out_no_fee * transaction.spot_price,
                visual_style=highlighted_style if transaction.crypto_out_no_fee * transaction.spot_price > ZERO else visual_style,
                data_style="fiat",
            )
            self._fill_cell(
                sheet,
                row_index,
                12,
                transaction.fiat_fee,
                visual_style=highlighted_style if transaction.fiat_fee > ZERO else visual_style,
                data_style="fiat",
            )
            self._fill_cell(sheet, row_index, 13, _("YES") if transaction.is_taxable() else _("NO"), data_style="fiat", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 14, transaction.unique_id, visual_style="transparent")
            self._fill_cell(sheet, row_index, 15, transaction.notes, visual_style="transparent")

            self.__in_out_sheet_transaction_2_row[transaction] = row_index + 1

            row_index += 1

        return row_index

    def __generate_intra_table(self, sheet: Any, computed_data: ComputedData, row_index: int) -> int:
        row_index = self._fill_header(_("Intra-Flow Detail"), self.__intra_header_names_row_1, self.__intra_header_names_row_2, sheet, row_index, 1)

        intra_transaction_set: TransactionSet = computed_data.intra_transaction_set

        entry: AbstractEntry
        year: int = 0
        for entry in intra_transaction_set:
            transaction: IntraTransaction = cast(IntraTransaction, entry)
            visual_style: str
            highlighted_style: str
            transaction_visual_style: _TransactionVisualStyle = self.__get_transaction_visual_style(transaction, year)
            year = transaction_visual_style.year
            visual_style = transaction_visual_style.visual_style
            highlighted_style = transaction_visual_style.highlighted_style
            self._fill_cell(sheet, row_index, 0, "", visual_style="transparent")
            self._fill_cell(sheet, row_index, 1, transaction.timestamp, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 2, transaction.asset, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 3, transaction.from_exchange, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 4, transaction.from_holder, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 5, transaction.to_exchange, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 6, transaction.to_holder, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 7, transaction.spot_price, visual_style=visual_style, data_style="fiat")
            self._fill_cell(sheet, row_index, 8, transaction.crypto_sent, visual_style=visual_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 9, transaction.crypto_received, visual_style=visual_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 10, transaction.crypto_fee, visual_style=visual_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 11, computed_data.get_crypto_intra_fee_running_sum(transaction), data_style="crypto", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 12, transaction.fiat_fee, visual_style=highlighted_style, data_style="fiat")
            self._fill_cell(sheet, row_index, 13, _("YES") if transaction.is_taxable() else _("NO"), data_style="fiat", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 14, transaction.unique_id, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 15, transaction.notes, visual_style="transparent")

            self.__in_out_sheet_transaction_2_row[transaction] = row_index + 1

            row_index += 1

        return row_index

    def __generate_gain_loss_summary(self, sheet: Any, yearly_gain_loss_list: List[YearlyGainLoss], row_index: int) -> int:
        row_index = self._fill_header(
            _("Gain / Loss Summary"), self.__gain_loss_summary_header_names_row_1, self.__gain_loss_summary_header_names_row_2, sheet, row_index, 0
        )

        year: int = 0
        for yearly_gain_loss in yearly_gain_loss_list:
            border_suffix: str = ""
            capital_gains_type: str = _("LONG") if yearly_gain_loss.is_long_term_capital_gains else _("SHORT")
            border_style: _BorderStyle = self.__get_border_style(yearly_gain_loss.year, year)
            year = border_style.year
            border_suffix = border_style.border_suffix
            self._fill_cell(sheet, row_index, 0, yearly_gain_loss.year, visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 1, yearly_gain_loss.asset, visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 2, yearly_gain_loss.fiat_gain_loss, visual_style="bold" + border_suffix, data_style="fiat")
            self._fill_cell(sheet, row_index, 3, capital_gains_type, visual_style="bold" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 4, yearly_gain_loss.transaction_type.value.upper(), visual_style="bold" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 5, yearly_gain_loss.crypto_amount, visual_style="transparent" + border_suffix, data_style="crypto")
            self._fill_cell(
                sheet,
                row_index,
                6,
                yearly_gain_loss.fiat_amount,
                visual_style="taxable_event" + border_suffix,
                data_style="fiat",
            )
            self._fill_cell(
                sheet,
                row_index,
                7,
                yearly_gain_loss.fiat_cost_basis,
                visual_style="acquired_lot" + border_suffix,
                data_style="fiat",
            )
            row_index += 1

        return row_index

    def __generate_account_balances(self, sheet: Any, balance_set: BalanceSet, row_index: int) -> int:
        row_index = self._fill_header(_("Account Balances"), self.__balance_header_names_row_1, self.__balance_header_names_row_2, sheet, row_index, 0)

        totals: Dict[str, RP2Decimal] = {}
        value: RP2Decimal
        for balance in balance_set:
            self._fill_cell(sheet, row_index, 0, balance.exchange, visual_style="bold", data_style="default")
            self._fill_cell(sheet, row_index, 1, balance.holder, visual_style="bold", data_style="default")
            self._fill_cell(sheet, row_index, 2, balance.asset)
            self._fill_cell(sheet, row_index, 3, balance.acquired_balance, data_style="crypto")
            self._fill_cell(sheet, row_index, 4, balance.sent_balance, data_style="crypto")
            self._fill_cell(sheet, row_index, 5, balance.received_balance, data_style="crypto")
            self._fill_cell(sheet, row_index, 6, balance.final_balance, visual_style="bold", data_style="crypto")
            value = totals.setdefault(balance.holder, _ZERO)
            value += balance.final_balance
            totals[balance.holder] = value
            row_index += 1

        holder: str
        border_drawn: bool = False
        for (holder, value) in sorted(totals.items()):
            border_suffix: str = ""
            if not border_drawn:
                border_suffix = "_border"
                border_drawn = True
            self._fill_cell(sheet, row_index, 0, _("Total"), visual_style="bold" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 1, holder, visual_style="bold" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 2, "", visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 3, "", visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 4, "", visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 5, "", visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 6, value, visual_style="bold" + border_suffix, data_style="crypto")
            row_index += 1

        return row_index

    def __generate_average_price_per_unit(self, sheet: Any, asset: str, price_per_unit: RP2Decimal, row_index: int) -> int:
        self._fill_cell(sheet, row_index, 0, _("Average Price"), visual_style="title")
        self._fill_cell(sheet, row_index + 1, 0, _("Average Price"), visual_style="header")
        self._fill_cell(sheet, row_index + 2, 0, _("Paid Per 1 {}").format(asset), visual_style="header")
        self._fill_cell(sheet, row_index + 3, 0, price_per_unit, visual_style="transparent", data_style="fiat")

        return row_index + 4

    def __get_hyperlinked_transaction_value(self, transaction: AbstractTransaction, value: Any) -> Any:
        row: Optional[int] = self.__get_in_out_sheet_row(transaction)
        if not row:
            # This may occur if command line time filters are activated
            return value
        if isinstance(value, (RP2Decimal, int, float)):
            return f'=HYPERLINK("#{self.get_in_out_sheet_name(transaction.asset)}.a{row}:z{row}"; {value})'
        return f'=HYPERLINK("#{self.get_in_out_sheet_name(transaction.asset)}.a{row}:z{row}"; "{value}")'

    def __get_hyperlinked_summary_value(self, asset: str, value: Any, year: int) -> Any:
        row: int = self.__tax_sheet_year_2_row[_AssetAndYear(asset, year)]
        if isinstance(value, (RP2Decimal, int, float)):
            return f'=HYPERLINK("#{self.get_tax_sheet_name(asset)}.a{row}:z{row}"; {value})'
        return f'=HYPERLINK("#{self.get_tax_sheet_name(asset)}.a{row}:z{row}"; "{value}")'

    def __get_in_out_sheet_row(self, transaction: AbstractTransaction) -> Optional[int]:
        if transaction not in self.__in_out_sheet_transaction_2_row:
            return None
        return self.__in_out_sheet_transaction_2_row[transaction]

    def __generate_gain_loss_detail(self, sheet: Any, asset: str, computed_data: ComputedData, row_index: int) -> int:

        row_index = self._fill_header(
            _("Gain / Loss Detail"), self.__gain_loss_detail_header_names_row_1, self.__gain_loss_detail_header_names_row_2, sheet, row_index, 0
        )

        gain_loss_set: GainLossSet = computed_data.gain_loss_set

        taxable_event_style_modifier: str = ""
        acquired_lot_style_modifier: str = "_alt"
        year: int = 0
        border_style: _BorderStyle

        previous_acquired_lot: Optional[InTransaction] = None
        for entry in gain_loss_set:
            gain_loss: GainLoss = cast(GainLoss, entry)
            border_suffix: str = ""
            border_style = self.__get_border_style(gain_loss.taxable_event.timestamp.year, year)
            if gain_loss.taxable_event.timestamp.year != year:
                self.__tax_sheet_year_2_row[_AssetAndYear(asset, gain_loss.taxable_event.timestamp.year)] = row_index + 1
            year = border_style.year
            border_suffix = border_style.border_suffix
            transparent_style: str = f"transparent{border_suffix}"
            taxable_event_style: str = f"taxable_event{taxable_event_style_modifier}{border_suffix}"
            highlighted_style: str = f"highlighted{border_suffix}"
            current_taxable_event_fraction: int = gain_loss_set.get_taxable_event_fraction(gain_loss) + 1
            total_taxable_event_fractions: int = gain_loss_set.get_taxable_event_number_of_fractions(gain_loss.taxable_event)
            transaction_type: str = (
                f"{self._get_table_type_from_transaction(gain_loss.taxable_event)} / " f"{gain_loss.taxable_event.transaction_type.value.upper()}"
            )
            taxable_event_note: str = (
                f"{current_taxable_event_fraction}/"
                f"{total_taxable_event_fractions}: "
                f"{gain_loss.crypto_amount:.8f} of "
                f"{gain_loss.taxable_event.crypto_balance_change:.8f} "
                f"{asset}"
            )
            acquired_lot_style: str

            self._fill_cell(sheet, row_index, 0, gain_loss.crypto_amount, visual_style=transparent_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 1, gain_loss.asset, visual_style=transparent_style)
            self._fill_cell(sheet, row_index, 2, computed_data.get_crypto_gain_loss_running_sum(gain_loss), visual_style=transparent_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 3, gain_loss.fiat_gain, visual_style=transparent_style, data_style="fiat")
            self._fill_cell(sheet, row_index, 4, _("LONG") if gain_loss.is_long_term_capital_gains() else _("SHORT"), visual_style=transparent_style)
            self._fill_cell(
                sheet,
                row_index,
                5,
                self.__get_hyperlinked_transaction_value(gain_loss.taxable_event, gain_loss.taxable_event.timestamp),
                visual_style=taxable_event_style,
            )
            self._fill_cell(
                sheet, row_index, 6, self.__get_hyperlinked_transaction_value(gain_loss.taxable_event, transaction_type), visual_style=taxable_event_style
            )
            self._fill_cell(
                sheet,
                row_index,
                7,
                self.__get_hyperlinked_transaction_value(gain_loss.taxable_event, gain_loss.taxable_event_fraction_percentage),
                visual_style=taxable_event_style,
                data_style="percent",
            )
            self._fill_cell(
                sheet,
                row_index,
                8,
                self.__get_hyperlinked_transaction_value(gain_loss.taxable_event, gain_loss.taxable_event_fiat_amount_with_fee_fraction),
                visual_style=highlighted_style,
                data_style="fiat",
            )
            self._fill_cell(
                sheet,
                row_index,
                9,
                self.__get_hyperlinked_transaction_value(gain_loss.taxable_event, gain_loss.taxable_event.spot_price),
                visual_style=taxable_event_style,
                data_style="fiat",
            )
            self._fill_cell(
                sheet,
                row_index,
                10,
                self.__get_hyperlinked_transaction_value(gain_loss.taxable_event, gain_loss.taxable_event.unique_id),
                visual_style=taxable_event_style,
                data_style="fiat",
            )
            self._fill_cell(
                sheet,
                row_index,
                11,
                self.__get_hyperlinked_transaction_value(gain_loss.taxable_event, taxable_event_note),
                visual_style=f"taxable_event_note{border_suffix}",
            )
            if current_taxable_event_fraction == total_taxable_event_fractions:
                # Last fraction: change color
                taxable_event_style_modifier = "" if taxable_event_style_modifier == "_alt" else "_alt"

            if gain_loss.acquired_lot:
                if gain_loss.acquired_lot != previous_acquired_lot:
                    # Last fraction: change color
                    acquired_lot_style_modifier = "" if acquired_lot_style_modifier == "_alt" else "_alt"
                acquired_lot_style = f"acquired_lot{acquired_lot_style_modifier}{border_suffix}"
                current_acquired_lot_fraction: int = gain_loss_set.get_acquired_lot_fraction(gain_loss) + 1
                total_acquired_lot_fractions: int = gain_loss_set.get_acquired_lot_number_of_fractions(gain_loss.acquired_lot)
                acquired_lot_note: str = (
                    f"{current_acquired_lot_fraction}/"
                    f"{total_acquired_lot_fractions}: "
                    f"{gain_loss.crypto_amount:.8f} of "
                    f"{gain_loss.acquired_lot.crypto_balance_change:.8f} "
                    f"{asset}"
                )
                self._fill_cell(
                    sheet,
                    row_index,
                    12,
                    self.__get_hyperlinked_transaction_value(gain_loss.acquired_lot, gain_loss.acquired_lot.timestamp),
                    visual_style=acquired_lot_style,
                )
                self._fill_cell(
                    sheet,
                    row_index,
                    13,
                    self.__get_hyperlinked_transaction_value(gain_loss.acquired_lot, gain_loss.acquired_lot_fraction_percentage),
                    visual_style=acquired_lot_style,
                    data_style="percent",
                )
                self._fill_cell(
                    sheet,
                    row_index,
                    14,
                    self.__get_hyperlinked_transaction_value(gain_loss.acquired_lot, gain_loss.acquired_lot_fiat_amount_with_fee_fraction),
                    visual_style=acquired_lot_style,
                    data_style="fiat",
                )
                fiat_fee_fraction: RP2Decimal = gain_loss.acquired_lot.fiat_fee * gain_loss.acquired_lot_fraction_percentage
                self._fill_cell(
                    sheet,
                    row_index,
                    15,
                    self.__get_hyperlinked_transaction_value(gain_loss.acquired_lot, fiat_fee_fraction),
                    visual_style=acquired_lot_style,
                    data_style="fiat",
                )
                self._fill_cell(
                    sheet,
                    row_index,
                    16,
                    self.__get_hyperlinked_transaction_value(gain_loss.acquired_lot, gain_loss.fiat_cost_basis),
                    visual_style=highlighted_style,
                    data_style="fiat",
                )
                self._fill_cell(
                    sheet,
                    row_index,
                    17,
                    self.__get_hyperlinked_transaction_value(gain_loss.acquired_lot, gain_loss.acquired_lot.spot_price),
                    visual_style=acquired_lot_style,
                    data_style="fiat",
                )
                self._fill_cell(
                    sheet,
                    row_index,
                    18,
                    self.__get_hyperlinked_transaction_value(gain_loss.acquired_lot, gain_loss.acquired_lot.unique_id),
                    visual_style=acquired_lot_style,
                    data_style="fiat",
                )
                self._fill_cell(
                    sheet,
                    row_index,
                    19,
                    self.__get_hyperlinked_transaction_value(gain_loss.acquired_lot, acquired_lot_note),
                    visual_style=f"acquired_lot_note{border_suffix}",
                )

                previous_acquired_lot = gain_loss.acquired_lot
            else:
                acquired_lot_style = f"acquired_lot{acquired_lot_style_modifier}{border_suffix}"
                for i in range(12, 19):
                    self._fill_cell(sheet, row_index, i, "", visual_style=f"{acquired_lot_style}")

            row_index += 1

        return row_index

    def __generate_yearly_gain_loss_summary(self, sheet: Any, asset: str, yearly_gain_loss_list: List[YearlyGainLoss], row_index: int) -> int:
        for gain_loss in yearly_gain_loss_list:
            visual_style: str = "transparent"
            capital_gains_type: str = _("LONG") if gain_loss.is_long_term_capital_gains else _("SHORT")
            year: int = gain_loss.year
            self._fill_cell(sheet, row_index, 0, self.__get_hyperlinked_summary_value(asset, year, year), visual_style=visual_style)
            self._fill_cell(sheet, row_index, 1, self.__get_hyperlinked_summary_value(asset, asset, year), visual_style=visual_style)
            self._fill_cell(
                sheet,
                row_index,
                2,
                self.__get_hyperlinked_summary_value(asset, gain_loss.fiat_gain_loss, year),
                visual_style=visual_style,
                data_style="fiat",
            )
            self._fill_cell(sheet, row_index, 3, self.__get_hyperlinked_summary_value(asset, capital_gains_type, year), visual_style=visual_style)
            self._fill_cell(
                sheet, row_index, 4, self.__get_hyperlinked_summary_value(asset, gain_loss.transaction_type.value.upper(), year), visual_style=visual_style
            )
            self._fill_cell(
                sheet, row_index, 5, self.__get_hyperlinked_summary_value(asset, gain_loss.crypto_amount, year), visual_style=visual_style, data_style="crypto"
            )
            self._fill_cell(
                sheet,
                row_index,
                6,
                self.__get_hyperlinked_summary_value(asset, gain_loss.fiat_amount, year),
                visual_style=visual_style,
                data_style="fiat",
            )
            self._fill_cell(
                sheet,
                row_index,
                7,
                self.__get_hyperlinked_summary_value(asset, gain_loss.fiat_cost_basis, year),
                visual_style=visual_style,
                data_style="fiat",
            )
            row_index += 1

        return row_index

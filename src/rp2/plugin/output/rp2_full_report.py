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

from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Set, cast

import ezodf
from rp2.abstract_entry import AbstractEntry
from rp2.abstract_transaction import AbstractTransaction
from rp2.balance import BalanceSet
from rp2.computed_data import ComputedData, YearlyGainLoss
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
from rp2.in_transaction import InTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.logger import LOGGER
from rp2.out_transaction import OutTransaction
from rp2.plugin.output.abstract_odt_generator import AbstractODTGenerator
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError
from rp2.transaction_set import TransactionSet


class _TransactionVisualStyle(NamedTuple):
    year: int
    visual_style: str
    highlighted_style: str


class _BorderStyle(NamedTuple):
    year: int
    border_suffix: str


_IN_HEADER_NAMES_ROW_1: List[str] = [
    "",
    "",
    "",
    "",
    "",
    "Transaction",
    "",
    "Crypto",
    "Crypto In",
    "",
    "USD In",
    "USD In",
    "Taxable",
    "",
    "",
]

_IN_HEADER_NAMES_ROW_2: List[str] = [
    "Sent/Sold",
    "Timestamp",
    "Asset",
    "Exchange",
    "Holder",
    "Type",
    "Spot Price",
    "In",
    "Running Sum",
    "USD Fee",
    "No Fee",
    "With Fee",
    "Event",
    "N/A",
    "Notes",
]

_OUT_HEADER_NAMES_ROW_1: List[str] = [
    "",
    "",
    "",
    "",
    "Transaction",
    "",
    "",
    "",
    "Crypto Out",
    "Crypto Fee",
    "",
    "",
    "Taxable",
    "",
]

_OUT_HEADER_NAMES_ROW_2: List[str] = [
    "Timestamp",
    "Asset",
    "Exchange",
    "Holder",
    "Type",
    "Spot Price",
    "Crypto Out",
    "Crypto Fee",
    "Running Sum",
    "Running Sum",
    "USD Out",
    "USD Fee",
    "Event",
    "Notes",
]

_INTRA_HEADER_NAMES_ROW_1: List[str] = [
    "",
    "",
    "From",
    "From",
    "",
    "",
    "",
    "",
    "Crypto",
    "",
    "Crypto Fee",
    "",
    "Taxable",
    "",
]

_INTRA_HEADER_NAMES_ROW_2: List[str] = [
    "Timestamp",
    "Asset",
    "Exchange",
    "Holder",
    "To Exchange",
    "To Holder",
    "Spot Price",
    "Crypto Sent",
    "Received",
    "Crypto Fee",
    "Running Sum",
    "USD Fee",
    "Event",
    "Notes",
]

_BALANCE_HEADER_NAMES_ROW_1: List[str] = [
    "",
    "",
    "",
    "Acquired",
    "Sent",
    "Received",
    "Final",
]

_BALANCE_HEADER_NAMES_ROW_2: List[str] = [
    "Exchange",
    "Holder",
    "Asset",
    "Balance",
    "Balance",
    "Balance",
    "Balance",
]

_GAIN_LOSS_SUMMARY_HEADER_NAMES_ROW_1: List[str] = [
    "",
    "",
    "Capital",
    "Capital",
    "Transaction",
    "Crypto",
    "USD",
    "USD Total",
]

_GAIN_LOSS_SUMMARY_HEADER_NAMES_ROW_2: List[str] = [
    "Year",
    "Asset",
    "Gains",
    "Gains Type",
    "Type",
    "Taxable Total",
    "Taxable Total",
    "Cost Basis",
]

_GAIN_LOSS_DETAIL_HEADER_NAMES_ROW_1: List[str] = [
    "Crypto",
    "",
    "Crypto Amt",
    "Capital",
    "Capital",
    "Taxable Event",
    "Taxable Event",
    "Taxable Event",
    "Taxable Event USD",
    "Taxable Event",
    "Taxable Event",
    "In Lot",
    "In Lot",
    "In Lot USD",
    "In Lot USD",
    "In Lot USD",
    "In Lot",
    "In Lot Fraction",
]

_GAIN_LOSS_DETAIL_HEADER_NAMES_ROW_2: List[str] = [
    "Amount",
    "Asset",
    "Running Sum",
    "Gains",
    "Gains Type",
    "Timestamp",
    "Direction/Type",
    "Fraction %",
    "Amount Fraction",
    "Spot Price",
    "Fraction Description",
    "Timestamp",
    "Fraction %",
    "Amount Fraction",
    "Fee Fraction",
    "Cost Basis",
    "Spot Price",
    "Description",
]

_ZERO: RP2Decimal = RP2Decimal(0)


class Generator(AbstractODTGenerator):

    MIN_ROWS: int = 40
    MAX_COLUMNS: int = 40
    OUTPUT_FILE: str = "rp2_full_report.ods"
    TEMPLATE_SHEETS_TO_KEEP: Set[str] = {"__Legend", "__Summary"}

    def generate(
        self,
        asset_to_computed_data: Dict[str, ComputedData],
        output_dir_path: str,
        output_file_prefix: str,
    ) -> None:

        if not isinstance(asset_to_computed_data, Dict):
            raise RP2TypeError(f"Parameter 'asset_to_computed_data' has non-Dict value {asset_to_computed_data}")

        output_file: Any
        output_file = self._initialize_output_file(
            output_dir_path=output_dir_path,
            output_file_prefix=output_file_prefix,
            output_file_name=self.OUTPUT_FILE,
            template_sheets_to_keep=self.TEMPLATE_SHEETS_TO_KEEP,
        )

        asset: str
        computed_data: ComputedData

        summary_row_index: int = 3
        for asset, computed_data in asset_to_computed_data.items():
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)
            summary_row_index = self.__generate_asset(computed_data, output_file, summary_row_index)

        output_file.save()
        LOGGER.info("Plugin '%s' output: %s", __name__, Path(output_file.docname).resolve())

    def __get_number_of_rows_in_transaction_sheet(self, computed_data: ComputedData) -> int:
        return self.MIN_ROWS + computed_data.in_transaction_set.count + computed_data.out_transaction_set.count + computed_data.intra_transaction_set.count

    def __get_number_of_rows_in_output_sheet(self, computed_data: ComputedData) -> int:
        return self.MIN_ROWS + len(computed_data.yearly_gain_loss_list) + computed_data.balance_set.count + computed_data.gain_loss_set.count

    def __generate_asset(self, computed_data: ComputedData, output_file: Any, summary_row_index: int) -> int:
        asset: str = computed_data.asset
        transaction_sheet_name: str = f"{asset} In-Out"
        output_sheet_name: str = f"{asset} Tax"

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
        row_index = self.__generate_in_table(transaction_sheet, computed_data.in_transaction_set, computed_data.gain_loss_set, row_index)
        row_index = self.__generate_out_table(transaction_sheet, computed_data.out_transaction_set, row_index + 2)
        row_index = self.__generate_intra_table(transaction_sheet, computed_data.intra_transaction_set, row_index + 2)

        row_index = 0
        row_index = self.__generate_gain_loss_summary(output_sheet, computed_data.yearly_gain_loss_list, row_index)
        row_index = self.__generate_account_balances(output_sheet, computed_data.balance_set, row_index + 2)
        row_index = self.__generate_average_price_per_unit(output_sheet, asset, computed_data.price_per_unit, row_index + 2)
        row_index = self.__generate_gain_loss_detail(output_sheet, asset, computed_data.gain_loss_set, row_index + 2)

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

    def __generate_in_table(self, sheet: Any, in_transaction_set: TransactionSet, gain_loss_set: GainLossSet, row_index: int) -> int:
        row_index = self._fill_header("In-Flow Detail", _IN_HEADER_NAMES_ROW_1, _IN_HEADER_NAMES_ROW_2, sheet, row_index, 0)

        in_transaction_index: int = row_index
        entry: AbstractEntry
        crypto_in_running_sum: RP2Decimal = _ZERO
        year: int = 0
        visual_style: str
        for entry in in_transaction_set:
            transaction: InTransaction = cast(InTransaction, entry)
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
            self._fill_cell(sheet, row_index, 6, transaction.spot_price, data_style="usd", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 7, transaction.crypto_in, data_style="crypto", visual_style=visual_style)
            crypto_in_running_sum += transaction.crypto_in
            self._fill_cell(sheet, row_index, 8, crypto_in_running_sum, data_style="crypto", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 9, transaction.usd_fee, data_style="usd", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 10, transaction.usd_in_no_fee, data_style="usd", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 11, transaction.usd_in_with_fee, data_style="usd", visual_style=highlighted_style)
            self._fill_cell(sheet, row_index, 12, "YES" if transaction.is_taxable() else "NO", data_style="usd", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 13, "", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 14, transaction.notes, visual_style="transparent")
            row_index += 1

        current_from_lot: Optional[AbstractTransaction] = None
        current_from_lot_percentage: RP2Decimal = _ZERO
        year = 0
        border_style: _BorderStyle
        border_suffix: str = ""
        for entry in gain_loss_set:
            gain_loss: GainLoss = cast(GainLoss, entry)
            if not gain_loss.from_lot:
                continue
            if gain_loss.from_lot != current_from_lot:
                if current_from_lot:
                    border_style = self.__get_border_style(current_from_lot.timestamp.year, year)
                    year = border_style.year
                    border_suffix = border_style.border_suffix
                    self._fill_cell(sheet, in_transaction_index, 0, 1, data_style="percent", visual_style="from_lot" + border_suffix)
                    in_transaction_index += 1
                    current_from_lot_percentage = _ZERO
                current_from_lot = gain_loss.from_lot
            current_from_lot_percentage += gain_loss.from_lot_fraction_percentage
        if current_from_lot:
            border_style = self.__get_border_style(current_from_lot.timestamp.year, year)
            year = border_style.year
            border_suffix = border_style.border_suffix
        self._fill_cell(sheet, in_transaction_index, 0, current_from_lot_percentage, data_style="percent", visual_style="from_lot" + border_suffix)

        return row_index

    def __generate_out_table(self, sheet: Any, out_transaction_set: TransactionSet, row_index: int) -> int:
        row_index = self._fill_header("Out-Flow Detail", _OUT_HEADER_NAMES_ROW_1, _OUT_HEADER_NAMES_ROW_2, sheet, row_index, 1)

        entry: AbstractEntry
        crypto_out_running_sum: RP2Decimal = _ZERO
        crypto_fee_running_sum: RP2Decimal = _ZERO
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
            self._fill_cell(sheet, row_index, 6, transaction.spot_price, visual_style=visual_style, data_style="usd")
            self._fill_cell(sheet, row_index, 7, transaction.crypto_out_no_fee, visual_style=visual_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 8, transaction.crypto_fee, visual_style=visual_style, data_style="crypto")
            crypto_out_running_sum += transaction.crypto_out_no_fee
            crypto_fee_running_sum += transaction.crypto_fee
            self._fill_cell(sheet, row_index, 9, crypto_out_running_sum, data_style="crypto", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 10, crypto_fee_running_sum, data_style="crypto", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 11, transaction.crypto_out_no_fee * transaction.spot_price, visual_style=highlighted_style, data_style="usd")
            self._fill_cell(sheet, row_index, 12, transaction.crypto_fee * transaction.spot_price, visual_style=highlighted_style, data_style="usd")
            self._fill_cell(sheet, row_index, 13, "YES" if transaction.is_taxable() else "NO", data_style="usd", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 14, transaction.notes, visual_style="transparent")
            row_index += 1

        return row_index

    def __generate_intra_table(self, sheet: Any, intra_transaction_set: TransactionSet, row_index: int) -> int:
        row_index = self._fill_header("Intra-Flow Detail", _INTRA_HEADER_NAMES_ROW_1, _INTRA_HEADER_NAMES_ROW_2, sheet, row_index, 1)

        entry: AbstractEntry
        crypto_fee_running_sum: RP2Decimal = _ZERO
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
            self._fill_cell(sheet, row_index, 7, transaction.spot_price, visual_style=visual_style, data_style="usd")
            self._fill_cell(sheet, row_index, 8, transaction.crypto_sent, visual_style=visual_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 9, transaction.crypto_received, visual_style=visual_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 10, transaction.crypto_fee, visual_style=visual_style, data_style="crypto")
            crypto_fee_running_sum += transaction.crypto_fee
            self._fill_cell(sheet, row_index, 11, crypto_fee_running_sum, data_style="crypto", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 12, transaction.usd_fee, visual_style=highlighted_style, data_style="usd")
            self._fill_cell(sheet, row_index, 13, "YES" if transaction.is_taxable() else "NO", data_style="usd", visual_style=visual_style)
            self._fill_cell(sheet, row_index, 14, transaction.notes, visual_style="transparent")
            row_index += 1

        return row_index

    def __generate_gain_loss_summary(self, sheet: Any, yearly_gain_loss_list: List[YearlyGainLoss], row_index: int) -> int:
        row_index = self._fill_header("Gain / Loss Summary", _GAIN_LOSS_SUMMARY_HEADER_NAMES_ROW_1, _GAIN_LOSS_SUMMARY_HEADER_NAMES_ROW_2, sheet, row_index, 0)

        year: int = 0
        for yearly_gain_loss in yearly_gain_loss_list:
            border_suffix: str = ""
            capital_gains_type: str = "LONG" if yearly_gain_loss.is_long_term_capital_gains else "SHORT"
            border_style: _BorderStyle = self.__get_border_style(yearly_gain_loss.year, year)
            year = border_style.year
            border_suffix = border_style.border_suffix
            self._fill_cell(sheet, row_index, 0, yearly_gain_loss.year, visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 1, yearly_gain_loss.asset, visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 2, yearly_gain_loss.usd_gain_loss, visual_style="bold" + border_suffix, data_style="usd")
            self._fill_cell(sheet, row_index, 3, capital_gains_type, visual_style="bold" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 4, yearly_gain_loss.transaction_type.value.upper(), visual_style="bold" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 5, yearly_gain_loss.crypto_amount, visual_style="transparent" + border_suffix, data_style="crypto")
            self._fill_cell(sheet, row_index, 6, yearly_gain_loss.usd_amount, visual_style="taxable_event" + border_suffix, data_style="usd")
            self._fill_cell(sheet, row_index, 7, yearly_gain_loss.usd_cost_basis, visual_style="from_lot" + border_suffix, data_style="usd")
            row_index += 1

        return row_index

    def __generate_account_balances(self, sheet: Any, balance_set: BalanceSet, row_index: int) -> int:
        row_index = self._fill_header("Account Balances", _BALANCE_HEADER_NAMES_ROW_1, _BALANCE_HEADER_NAMES_ROW_2, sheet, row_index, 0)

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
            self._fill_cell(sheet, row_index, 0, "Total", visual_style="bold" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 1, holder, visual_style="bold" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 2, "", visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 3, "", visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 4, "", visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 5, "", visual_style="transparent" + border_suffix, data_style="default")
            self._fill_cell(sheet, row_index, 6, value, visual_style="bold" + border_suffix, data_style="crypto")
            row_index += 1

        return row_index

    def __generate_average_price_per_unit(self, sheet: Any, asset: str, price_per_unit: RP2Decimal, row_index: int) -> int:
        self._fill_cell(sheet, row_index, 0, "Average Price", visual_style="title")
        self._fill_cell(sheet, row_index + 1, 0, "Average Price", visual_style="header")
        self._fill_cell(sheet, row_index + 2, 0, f"Paid Per 1 {asset}", visual_style="header")
        self._fill_cell(sheet, row_index + 3, 0, price_per_unit, visual_style="transparent", data_style="usd")

        return row_index + 4

    def __generate_gain_loss_detail(self, sheet: Any, asset: str, gain_loss_set: GainLossSet, row_index: int) -> int:

        row_index = self._fill_header("Gain / Loss Detail", _GAIN_LOSS_DETAIL_HEADER_NAMES_ROW_1, _GAIN_LOSS_DETAIL_HEADER_NAMES_ROW_2, sheet, row_index, 0)

        taxable_event_style_modifier: str = ""
        from_lot_style_modifier: str = ""
        crypto_amount_running_sum: RP2Decimal = _ZERO
        year: int = 0
        border_style: _BorderStyle
        for entry in gain_loss_set:
            gain_loss: GainLoss = cast(GainLoss, entry)
            border_suffix: str = ""
            border_style = self.__get_border_style(gain_loss.taxable_event.timestamp.year, year)
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
            self._fill_cell(sheet, row_index, 0, gain_loss.crypto_amount, visual_style=transparent_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 1, gain_loss.asset, visual_style=transparent_style)
            crypto_amount_running_sum += gain_loss.crypto_amount
            self._fill_cell(sheet, row_index, 2, crypto_amount_running_sum, visual_style=transparent_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 3, gain_loss.usd_gain, visual_style=transparent_style, data_style="usd")
            self._fill_cell(sheet, row_index, 4, "LONG" if gain_loss.is_long_term_capital_gains() else "SHORT", visual_style=transparent_style)
            self._fill_cell(sheet, row_index, 5, gain_loss.taxable_event.timestamp, visual_style=taxable_event_style)
            self._fill_cell(sheet, row_index, 6, transaction_type, visual_style=taxable_event_style)
            self._fill_cell(sheet, row_index, 7, gain_loss.taxable_event_fraction_percentage, visual_style=taxable_event_style, data_style="percent")
            self._fill_cell(sheet, row_index, 8, gain_loss.taxable_event_usd_amount_with_fee_fraction, visual_style=highlighted_style, data_style="usd")
            self._fill_cell(sheet, row_index, 9, gain_loss.taxable_event.spot_price, visual_style=taxable_event_style, data_style="usd")
            self._fill_cell(sheet, row_index, 10, taxable_event_note, visual_style=f"taxable_event_note{border_suffix}")
            if current_taxable_event_fraction == total_taxable_event_fractions:
                # Last fraction: change color
                taxable_event_style_modifier = "" if taxable_event_style_modifier == "_alt" else "_alt"

            from_lot_style: str = f"from_lot{from_lot_style_modifier}{border_suffix}"
            if gain_loss.from_lot:
                current_from_lot_fraction: int = gain_loss_set.get_from_lot_fraction(gain_loss) + 1
                total_from_lot_fractions: int = gain_loss_set.get_from_lot_number_of_fractions(gain_loss.from_lot)
                from_lot_note: str = (
                    f"{current_from_lot_fraction}/"
                    f"{total_from_lot_fractions}: "
                    f"{gain_loss.crypto_amount:.8f} of "
                    f"{gain_loss.from_lot.crypto_balance_change:.8f} "
                    f"{asset}"
                )
                self._fill_cell(sheet, row_index, 11, gain_loss.from_lot.timestamp, visual_style=from_lot_style)
                self._fill_cell(sheet, row_index, 12, gain_loss.from_lot_fraction_percentage, visual_style=from_lot_style, data_style="percent")
                self._fill_cell(sheet, row_index, 13, gain_loss.from_lot_usd_amount_with_fee_fraction, visual_style=from_lot_style, data_style="usd")
                usd_fee_fraction: RP2Decimal = gain_loss.from_lot.usd_fee * gain_loss.from_lot_fraction_percentage
                self._fill_cell(sheet, row_index, 14, usd_fee_fraction, visual_style=from_lot_style, data_style="usd")
                self._fill_cell(sheet, row_index, 15, gain_loss.usd_cost_basis, visual_style=highlighted_style, data_style="usd")
                self._fill_cell(sheet, row_index, 16, gain_loss.from_lot.spot_price, visual_style=from_lot_style, data_style="usd")
                self._fill_cell(sheet, row_index, 17, from_lot_note, visual_style=f"from_lot_note{border_suffix}")

                if current_from_lot_fraction == total_from_lot_fractions:
                    # Last fraction: change color
                    from_lot_style_modifier = "" if from_lot_style_modifier == "_alt" else "_alt"
            else:
                for i in range(11, 17):
                    self._fill_cell(sheet, row_index, i, "", visual_style=f"{from_lot_style}{border_suffix}")

            row_index += 1

        return row_index

    def __generate_yearly_gain_loss_summary(self, sheet: Any, asset: str, yearly_gain_loss_list: List[YearlyGainLoss], row_index: int) -> int:
        for gain_loss in yearly_gain_loss_list:
            visual_style: str = "transparent"
            capital_gains_type: str = "LONG" if gain_loss.is_long_term_capital_gains else "SHORT"
            self._fill_cell(sheet, row_index, 0, gain_loss.year, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 1, asset, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 2, gain_loss.usd_gain_loss, visual_style=visual_style, data_style="usd")
            self._fill_cell(sheet, row_index, 3, capital_gains_type, visual_style=visual_style)
            self._fill_cell(sheet, row_index, 4, gain_loss.transaction_type.value.upper(), visual_style=visual_style)
            self._fill_cell(sheet, row_index, 5, gain_loss.crypto_amount, visual_style=visual_style, data_style="crypto")
            self._fill_cell(sheet, row_index, 6, gain_loss.usd_amount, visual_style=visual_style, data_style="usd")
            self._fill_cell(sheet, row_index, 7, gain_loss.usd_cost_basis, visual_style=visual_style, data_style="usd")
            row_index += 1

        return row_index


def main() -> None:
    pass


if __name__ == "__main__":
    main()

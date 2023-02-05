# Copyright 2022 Neal Chambers
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
from itertools import chain
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Set, cast

from rp2.abstract_country import AbstractCountry
from rp2.abstract_entry import AbstractEntry
from rp2.abstract_transaction import AbstractTransaction
from rp2.computed_data import ComputedData
from rp2.configuration import MAX_DATE, MIN_DATE
from rp2.entry_types import TransactionType
from rp2.in_transaction import InTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.localization import _
from rp2.logger import create_logger
from rp2.out_transaction import OutTransaction
from rp2.plugin.report.abstract_ods_generator import AbstractODSGenerator
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2TypeError
from rp2.transaction_set import TransactionSet

LOGGER: logging.Logger = create_logger("tax_report_jp")


class _TransactionRow(NamedTuple):
    transaction_type: str
    transaction_month: int
    transaction_day: int
    transaction_client: str
    fee_in_yen: RP2Decimal = ZERO
    gift: RP2Decimal = ZERO
    purchase_crypto_amount: Optional[RP2Decimal] = None
    purchase_amount_in_yen: Optional[RP2Decimal] = None
    sales_crypto_amount: Optional[RP2Decimal] = None
    sales_amount_in_yen: Optional[RP2Decimal] = None
    donated_amount_in_yen: Optional[RP2Decimal] = None


class _SheetNames(Enum):
    ASSET: str = "Asset"
    SUMMARY: str = "Summary"


_TEMPLATE_SHEETS_TO_KEEP: Set[str] = {f"__{item.value}" for item in _SheetNames}
_INCOME_TRANSACTION_TYPES: Dict[TransactionType, None] = {
    TransactionType.AIRDROP: None,
    TransactionType.HARDFORK: None,
    TransactionType.INCOME: None,
    TransactionType.INTEREST: None,
    TransactionType.MINING: None,
    TransactionType.STAKING: None,
    TransactionType.WAGES: None,
}


class Generator(AbstractODSGenerator):

    MIN_ROWS: int = 20
    MAX_COLUMNS: int = 20
    OUTPUT_FILE: str = "tax_report_jp.ods"

    ASSET_TEMPLATE_SHEET: str = "Asset"
    SUMMARY_TEMPLATE_SHEET: str = "Summary"
    TRANSACTION_ROW_START: int = 22

    TRANSFER: str = "Transfer"

    def __init__(self) -> None:

        super().__init__()
        self.__year_row_offset: Dict[int, int] = {}
        self.__number_of_summaries: int = 0

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

        if from_date != MIN_DATE and to_date != MAX_DATE:
            raise RP2RuntimeError("To and From Dates can not be specified for the JP tax report.")

        if not isinstance(asset_to_computed_data, Dict):
            raise RP2TypeError(f"Parameter 'asset_to_computed_data' has non-Dict value {asset_to_computed_data}")

        template_path: str = self._get_template_path("tax_report_jp", country, generation_language)

        output_file: Any
        output_file = self._initialize_output_file(
            country=country,
            legend_data=[],
            years_2_accounting_method_names=years_2_accounting_method_names,
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

        for asset, computed_data in asset_to_computed_data.items():
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)
            self.__generate_asset(computed_data, output_file)

        del output_file.sheets[self.ASSET_TEMPLATE_SHEET]
        del output_file.sheets[self.SUMMARY_TEMPLATE_SHEET]

        output_file.save()
        LOGGER.info("Plugin '%s' output: %s", __name__, Path(output_file.docname).resolve())

    def __insert_secondary_transaction_row(self, sheet_name: Any, row: int) -> None:
        sheet_name.insert_rows(index=row, count=1)
        sheet_name[f"A{row + 1}"].style_name = "transactions_month"
        sheet_name[f"B{row + 1}"].style_name = "transactions_day"
        sheet_name[f"C{row + 1}"].style_name = "transactions_middle"
        sheet_name[f"D{row + 1}"].style_name = "transactions_middle"
        sheet_name[f"E{row + 1}"].style_name = "transactions_crypto"
        sheet_name[f"F{row + 1}"].style_name = "transactions_yen"
        sheet_name[f"G{row + 1}"].style_name = "transactions_crypto"
        sheet_name[f"H{row + 1}"].style_name = "transactions_yen"
        sheet_name[f"I{row + 1}"].style_name = "transactions_right_end"

    def __insert_summary_row(self, sheet_name: Any, row: int) -> None:
        sheet_name.insert_rows(index=row, count=1)
        sheet_name[f"A{row + 1}"].style_name = "transactions_left_end"
        sheet_name[f"B{row + 1}"].style_name = "transactions_middle"
        sheet_name[f"C{row + 1}"].style_name = "transactions_middle"
        sheet_name[f"D{row + 1}"].style_name = "transactions_middle"
        sheet_name[f"E{row + 1}"].style_name = "transactions_crypto"
        sheet_name[f"F{row + 1}"].style_name = "transactions_yen"
        sheet_name[f"G{row + 1}"].style_name = "transactions_right_end"

    @staticmethod
    def get_tax_sheet_name(asset: str, year: int) -> str:
        return _("{}_{}").format(asset, year)

    @staticmethod
    def get_summary_sheet_name(year: int) -> str:
        return _("{}_Summary").format(year)

    def __generate_asset(self, computed_data: ComputedData, output_file: Any) -> None:
        asset: str = computed_data.asset

        in_transaction_set: TransactionSet = computed_data.in_transaction_set
        out_transaction_set: TransactionSet = computed_data.out_transaction_set
        intra_transaction_set: TransactionSet = computed_data.intra_transaction_set
        entry: AbstractEntry
        year: int
        years_2_transaction_sets: Dict[int, List[AbstractTransaction]] = {}
        previous_year_row_offset: int = 0

        # Sort all in and out transactions by year, the fee from intra transactions must be reported
        for entry in chain(in_transaction_set, out_transaction_set, intra_transaction_set):  # type: ignore
            transaction: AbstractTransaction = cast(AbstractTransaction, entry)
            years_2_transaction_sets.setdefault(transaction.timestamp.year, []).append(entry)

        for year, transaction_set in years_2_transaction_sets.items():
            # Sort the transactions by timestamp and generate sheet by year
            previous_year_row_offset = self.__generate_asset_year(
                asset=asset,
                year=year,
                transaction_list=sorted(transaction_set, key=lambda x: x.timestamp),
                output_file=output_file,
                previous_year_row_offset=previous_year_row_offset,
            )

            summary_sheet: Any = output_file.sheets[self.get_summary_sheet_name(year)]

            ### Totals at the bottom
            # Amount Donated
            self._fill_cell(summary_sheet, self.__year_row_offset[year] + 2, 1, f"=SUM(B8:B{self.__year_row_offset[year] + 2})", apply_style=False)
            # Gift Received
            self._fill_cell(summary_sheet, self.__year_row_offset[year] + 2, 2, f"=SUM(C8:C{self.__year_row_offset[year] + 2})", apply_style=False)
            # Total Amount in yen
            self._fill_cell(summary_sheet, self.__year_row_offset[year] + 2, 5, f"=SUM(F8:F{self.__year_row_offset[year] + 2})", apply_style=False)
            # Net Income Amt
            self._fill_cell(summary_sheet, self.__year_row_offset[year] + 2, 6, f"=SUM(G8:G{self.__year_row_offset[year] + 2})", apply_style=False)

    def __process_in_transaction(self, transaction: InTransaction) -> _TransactionRow:

        purchase_amount_in_yen: RP2Decimal = transaction.crypto_in * transaction.spot_price

        # Find the fee in yen
        fee_in_yen: RP2Decimal = ZERO
        if RP2Decimal(transaction.crypto_fee) > ZERO:
            fee_in_yen = transaction.crypto_fee * transaction.spot_price
        elif RP2Decimal(transaction.fiat_fee) > ZERO:
            fee_in_yen = transaction.fiat_fee

        # Record the profit this year of crypto assets earned as income
        # DONATE and GIFT (up to what is allowed) is tax free so we don't report them as income
        sales_crypto_amount: Optional[RP2Decimal] = None
        sales_amount_in_yen: Optional[RP2Decimal] = None
        if transaction.transaction_type in _INCOME_TRANSACTION_TYPES:
            sales_crypto_amount = ZERO
            sales_amount_in_yen = purchase_amount_in_yen

        gift: RP2Decimal = ZERO
        if transaction.transaction_type == TransactionType.GIFT:
            gift = purchase_amount_in_yen

        return _TransactionRow(
            transaction_type=transaction.transaction_type.value.upper(),
            purchase_crypto_amount=transaction.crypto_in,
            purchase_amount_in_yen=purchase_amount_in_yen,
            transaction_month=transaction.timestamp.month,
            transaction_day=transaction.timestamp.day,
            transaction_client=transaction.exchange,
            sales_crypto_amount=sales_crypto_amount,
            sales_amount_in_yen=sales_amount_in_yen,
            fee_in_yen=fee_in_yen,
            gift=gift,
        )

    def __process_intra_transaction(self, transaction: IntraTransaction) -> _TransactionRow:

        transaction_fee_in_crypto: Optional[RP2Decimal] = None
        transaction_fee_in_yen: Optional[RP2Decimal] = None

        transaction_fee_in_crypto = transaction.crypto_sent - transaction.crypto_received
        transaction_fee_in_yen = transaction_fee_in_crypto * transaction.spot_price

        return _TransactionRow(
            transaction_type=TransactionType.FEE.value.upper(),
            transaction_month=transaction.timestamp.month,
            transaction_day=transaction.timestamp.day,
            transaction_client=_(self.TRANSFER),
            sales_crypto_amount=transaction_fee_in_crypto if transaction_fee_in_crypto > ZERO else None,
            sales_amount_in_yen=transaction_fee_in_yen if transaction_fee_in_yen > ZERO else None,
            fee_in_yen=ZERO,
            gift=ZERO,
        )

    def __process_out_transaction(self, transaction: OutTransaction) -> _TransactionRow:

        # Find the fee in yen
        fee_in_yen: RP2Decimal = ZERO
        if RP2Decimal(transaction.crypto_fee) > ZERO:
            fee_in_yen = transaction.crypto_fee * transaction.spot_price
        elif RP2Decimal(transaction.fiat_fee) > ZERO:
            fee_in_yen = transaction.fiat_fee

        # DONATE can be used to reduce tax burden, GIFT is taxed as if sold at the moment it is gifted
        donated_amount_in_yen: Optional[RP2Decimal] = None
        sales_amount_in_yen: Optional[RP2Decimal] = None
        if transaction.transaction_type == TransactionType.DONATE:
            donated_amount_in_yen = RP2Decimal(str(transaction.crypto_out_no_fee * transaction.spot_price))
            sales_amount_in_yen = RP2Decimal("0")
        else:
            sales_amount_in_yen = transaction.crypto_out_no_fee * transaction.spot_price

        return _TransactionRow(
            transaction_type=transaction.transaction_type.value.upper(),
            transaction_month=transaction.timestamp.month,
            transaction_day=transaction.timestamp.day,
            transaction_client=transaction.exchange,
            sales_crypto_amount=transaction.crypto_out_with_fee,
            sales_amount_in_yen=sales_amount_in_yen,
            fee_in_yen=fee_in_yen,
            donated_amount_in_yen=donated_amount_in_yen,
        )

    def __generate_asset_year(self, asset: str, year: int, transaction_list: List[AbstractTransaction], output_file: Any, previous_year_row_offset: int) -> int:

        asset_year_sheet: Any = output_file.sheets[self.ASSET_TEMPLATE_SHEET].copy(newname=self.get_tax_sheet_name(asset, year))
        output_file.sheets += asset_year_sheet

        # Label the asset at the top of the page
        self._fill_cell(asset_year_sheet, 1, 7, asset, apply_style=False)
        row_index: int = 21
        total_donations: RP2Decimal = ZERO
        total_gifts: RP2Decimal = ZERO
        formatted_donation_amount: Optional[str] = None
        transaction_row: _TransactionRow

        for entry in transaction_list:

            if isinstance(entry, InTransaction):
                transaction_row = self.__process_in_transaction(entry)
                total_gifts += transaction_row.gift

            elif isinstance(entry, OutTransaction):
                transaction_row = self.__process_out_transaction(entry)
                if transaction_row.donated_amount_in_yen is not None:
                    total_donations += transaction_row.donated_amount_in_yen
                    formatted_donation_amount = f"0 (￥{float(transaction_row.donated_amount_in_yen):0,.2f})"

            elif isinstance(entry, IntraTransaction):
                transaction_row = self.__process_intra_transaction(entry)

            else:
                raise RP2RuntimeError("Transaction is not InTransaction or OutTransaction.")

            if transaction_row.purchase_crypto_amount is None and transaction_row.sales_crypto_amount is None:
                continue

            self.__insert_secondary_transaction_row(asset_year_sheet, row_index)
            self._fill_cell(asset_year_sheet, row_index, 0, transaction_row.transaction_month, apply_style=False)
            self._fill_cell(asset_year_sheet, row_index, 1, transaction_row.transaction_day, apply_style=False)
            self._fill_cell(asset_year_sheet, row_index, 2, transaction_row.transaction_client, apply_style=False)
            self._fill_cell(asset_year_sheet, row_index, 3, transaction_row.transaction_type, apply_style=False)
            if transaction_row.purchase_crypto_amount is not None:
                self._fill_cell(asset_year_sheet, row_index, 4, transaction_row.purchase_crypto_amount, apply_style=False)
                self._fill_cell(asset_year_sheet, row_index, 5, transaction_row.purchase_amount_in_yen, apply_style=False)
            if transaction_row.sales_crypto_amount is not None:
                self._fill_cell(asset_year_sheet, row_index, 6, transaction_row.sales_crypto_amount, apply_style=False)
                self._fill_cell(
                    asset_year_sheet,
                    row_index,
                    7,
                    transaction_row.sales_amount_in_yen if formatted_donation_amount is None else formatted_donation_amount,
                    apply_style=False,
                )
            self._fill_cell(asset_year_sheet, row_index, 8, transaction_row.fee_in_yen, apply_style=False)

            row_index += 1
            formatted_donation_amount = None

        # Adding the summary formulas at the bottom
        self._fill_cell(asset_year_sheet, row_index + 2, 4, f"=IF(SUM(E22:E{row_index+2})=0;0;SUM(E22:E{row_index+2}))", apply_style=False)
        self._fill_cell(asset_year_sheet, row_index + 2, 5, f"=IF(SUM(F22:F{row_index+2})=0;0;SUM(F22:F{row_index+2}))", apply_style=False)
        self._fill_cell(asset_year_sheet, row_index + 2, 6, f"=IF(SUM(G22:G{row_index+2})=0;0;SUM(G22:G{row_index+2}))", apply_style=False)
        self._fill_cell(asset_year_sheet, row_index + 2, 7, f"=IF(SUM(H22:H{row_index+2})=0;0;SUM(H22:H{row_index+2}))", apply_style=False)
        self._fill_cell(asset_year_sheet, row_index + 2, 8, f"=IF(SUM(I22:I{row_index+2})=0;0;SUM(I22:I{row_index+2}))", apply_style=False)

        ### 4 Calculation of Cost of Sale of Cryptographic Assets (暗号資産の売却原価の計算)

        # Last year's totals
        previous_year_crypto_cell: Optional[str] = None
        previous_year_yen_cell: Optional[str] = None
        if previous_year_row_offset != 0:
            previous_year_sheet_name: str = self.get_tax_sheet_name(asset, year - 1)
            previous_year_crypto_cell = f"='{previous_year_sheet_name}'.I{previous_year_row_offset}"
            previous_year_yen_cell = f"='{previous_year_sheet_name}'.I{previous_year_row_offset+1}"

        self._fill_cell(
            asset_year_sheet,
            row_index + 8,
            4,
            previous_year_crypto_cell if previous_year_crypto_cell else 0,
            apply_style=False,
        )
        self._fill_cell(
            asset_year_sheet,
            row_index + 9,
            4,
            previous_year_yen_cell if previous_year_yen_cell else 0,
            apply_style=False,
        )

        # This year's total purchases, etc...
        self._fill_cell(asset_year_sheet, row_index + 8, 5, f"=E13+E{row_index+3}", apply_style=False)
        self._fill_cell(asset_year_sheet, row_index + 9, 5, f"=F13+F{row_index+3}", apply_style=False)

        # Average Unit Price, located at G{row_index+10}
        self._fill_cell(
            asset_year_sheet,
            row_index + 9,
            6,
            f"=IF((E{row_index+9}+F{row_index+9});(E{row_index+10}+F{row_index+10})/(E{row_index+9}+F{row_index+9});0)",
            apply_style=False,
        )

        ## This year's total sales, etc...
        # Total units sold
        self._fill_cell(asset_year_sheet, row_index + 8, 7, f"=G13+G{row_index+3}", apply_style=False)
        # Total in yen (total units * average unit price)
        self._fill_cell(asset_year_sheet, row_index + 9, 7, f"=H{row_index+9}*G{row_index+10}", apply_style=False)

        ## This year's totals
        # Total units left
        self._fill_cell(asset_year_sheet, row_index + 8, 8, f"=E{row_index+9}+F{row_index+9}-H{row_index+9}", apply_style=False)
        # Total in yen (total units left * average unit price)
        self._fill_cell(asset_year_sheet, row_index + 9, 8, f"=I{row_index+9}*G{row_index+10}", apply_style=False)

        ### 5 Calculation of Income Amount for Virtual Currency (仮想通貨の所得金額の計算)

        ## Gross Income Amount
        # Sale Price
        self._fill_cell(asset_year_sheet, row_index + 17, 0, f"=H13+H{row_index+3}", apply_style=False)
        # Cost of Sale
        self._fill_cell(asset_year_sheet, row_index + 17, 5, f"=H{row_index+10}", apply_style=False)
        # Total Fees
        self._fill_cell(asset_year_sheet, row_index + 17, 6, f"=I{row_index+3}", apply_style=False)
        # Net Income Amt
        self._fill_cell(asset_year_sheet, row_index + 17, 8, f"=I{row_index+20}-I{row_index+21}", apply_style=False)

        # Total Profit
        self._fill_cell(asset_year_sheet, row_index + 19, 8, f"=ROUNDDOWN(SUM(A{row_index+18}:E{row_index+18});0)", apply_style=False)
        # Total Necessary Expenses
        self._fill_cell(asset_year_sheet, row_index + 20, 8, f"=ROUNDUP(SUM(F{row_index+18}:H{row_index+18});0)", apply_style=False)

        ### Add to Summary
        year_summary_sheet: Any
        # If this is the first time we have checked the year offset, set it to 7 and create a new summary sheet
        if self.__year_row_offset.setdefault(year, 7) == 7:
            year_summary_sheet = output_file.sheets[self.SUMMARY_TEMPLATE_SHEET].copy(newname=self.get_summary_sheet_name(year))
            # Place summaries at the beginning so they are easy to find
            output_file.sheets.insert(2 + self.__number_of_summaries, year_summary_sheet)
            self.__number_of_summaries += 1
        else:
            year_summary_sheet = output_file.sheets[self.get_summary_sheet_name(year)]

        self.__insert_summary_row(year_summary_sheet, self.__year_row_offset[year])

        # Name of Asset
        self._fill_cell(year_summary_sheet, self.__year_row_offset[year], 0, asset, apply_style=False)
        # Total Donations
        self._fill_cell(year_summary_sheet, self.__year_row_offset[year], 1, total_donations, apply_style=False)
        # Total Gifts
        self._fill_cell(year_summary_sheet, self.__year_row_offset[year], 2, total_gifts, apply_style=False)
        # Formula for Avg. Unit Price
        self._fill_cell(year_summary_sheet, self.__year_row_offset[year], 3, f"='{self.get_tax_sheet_name(asset, year)}'.G{row_index+10}", apply_style=False)
        # Formula for End Balance Crypto
        self._fill_cell(year_summary_sheet, self.__year_row_offset[year], 4, f"='{self.get_tax_sheet_name(asset, year)}'.I{row_index+9}", apply_style=False)
        # Formula for End Balance Yen
        self._fill_cell(year_summary_sheet, self.__year_row_offset[year], 5, f"='{self.get_tax_sheet_name(asset, year)}'.I{row_index+10}", apply_style=False)
        # Formula for Net Income Amt
        self._fill_cell(year_summary_sheet, self.__year_row_offset[year], 6, f"='{self.get_tax_sheet_name(asset, year)}'.I{row_index+18}", apply_style=False)

        self.__year_row_offset[year] += 1

        return row_index + 9

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

import logging
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Set, cast

from rp2.abstract_country import AbstractCountry
from rp2.computed_data import ComputedData
from rp2.entry_types import TransactionType
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
from rp2.logger import create_logger
from rp2.plugin.report.abstract_ods_generator import AbstractODSGenerator
from rp2.rp2_error import RP2TypeError

LOGGER: logging.Logger = create_logger("tax_report_us")


class SheetNames(Enum):
    AIRDROPS: str = "Airdrops"
    CAPITAL_GAINS: str = "Capital Gains"
    DONATIONS: str = "Donations"
    GIFTS: str = "Gifts"
    HARDFORKS: str = "Hard Forks"
    INCOME: str = "Income"
    INTEREST: str = "Interest"
    INVESTMENT_EXPENSES: str = "Investment Expenses"
    MINING: str = "Mining"
    STAKING: str = "Staking"
    WAGES: str = "Wages"


_TEMPLATE_SHEETS_TO_KEEP: Set[str] = {f"__{item.value}" for item in SheetNames}

_SHEET_TO_TYPE: Dict[str, TransactionType] = {
    SheetNames.AIRDROPS.value: TransactionType.AIRDROP,
    SheetNames.CAPITAL_GAINS.value: TransactionType.SELL,
    SheetNames.DONATIONS.value: TransactionType.DONATE,
    SheetNames.GIFTS.value: TransactionType.GIFT,
    SheetNames.HARDFORKS.value: TransactionType.HARDFORK,
    SheetNames.INCOME.value: TransactionType.INCOME,
    SheetNames.INTEREST.value: TransactionType.INTEREST,
    SheetNames.INVESTMENT_EXPENSES.value: TransactionType.MOVE,
    SheetNames.MINING.value: TransactionType.MINING,
    SheetNames.STAKING.value: TransactionType.STAKING,
    SheetNames.WAGES.value: TransactionType.WAGES,
}

_TYPE_TO_SHEET: Dict[TransactionType, str] = {transaction_type: sheet_name for sheet_name, transaction_type in _SHEET_TO_TYPE.items()}
_TYPE_TO_SHEET[TransactionType.FEE] = SheetNames.INVESTMENT_EXPENSES.value


class Generator(AbstractODSGenerator):

    MIN_ROWS: int = 20
    MAX_COLUMNS: int = 20
    OUTPUT_FILE: str = "tax_report_us.ods"

    HEADER_ROWS = 7

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

        row_indexes: Dict[str, int] = {sheet_name.value: self.HEADER_ROWS for sheet_name in SheetNames}

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
        )

        asset: str
        computed_data: ComputedData
        for asset, computed_data in asset_to_computed_data.items():
            if not isinstance(asset, str):
                raise RP2TypeError(f"Parameter 'asset' has non-string value {asset}")
            ComputedData.type_check("computed_data", computed_data)
            self.__generate(output_file, asset, computed_data.gain_loss_set, row_indexes)

        # Mark sheets that were not written to
        sheet_indexes_to_remove: List[int] = []
        index: int = 0
        sheet_name: str
        for sheet_name in output_file.sheets.names():
            if sheet_name != "Legend" and row_indexes[sheet_name] == Generator.HEADER_ROWS:
                sheet_indexes_to_remove.append(index)
            index += 1

        # Remove sheets that were marked for removal
        for index in reversed(sheet_indexes_to_remove):
            del output_file.sheets[index]

        output_file.save()
        LOGGER.info("Plugin '%s' output: %s", __name__, Path(output_file.docname).resolve())

    def __generate(self, output_file: Any, asset: str, gain_loss_set: GainLossSet, row_indexes: Dict[str, int]) -> None:

        sheet: Any
        for sheet in output_file.sheets:
            if sheet.name == "Legend":
                continue
            sheet_type: TransactionType = _SHEET_TO_TYPE[sheet.name]
            sheet.append_rows(self.MIN_ROWS + gain_loss_set.get_transaction_type_count(sheet_type) + 1)

        border_suffix: str = "_border"
        for entry in gain_loss_set:
            gain_loss: GainLoss = cast(GainLoss, entry)
            sheet_type = gain_loss.taxable_event.transaction_type
            sheet = output_file.sheets[_TYPE_TO_SHEET[sheet_type]]
            row_index: int = row_indexes[sheet.name]
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
            transparent_vs: str = f"transparent{border_suffix}"
            taxable_event_note_vs: str = f"taxable_event_note{border_suffix}"
            acquired_lot_note_vs: str = f"acquired_lot_note{border_suffix}"

            self._fill_cell(sheet, row_index, 0, gain_loss.crypto_amount, visual_style=transparent_vs, data_style="crypto")
            self._fill_cell(sheet, row_index, 1, gain_loss.asset, visual_style=transparent_vs)
            self._fill_cell(sheet, row_index, 3, gain_loss.taxable_event.timestamp.strftime("%m/%d/%Y"), visual_style=taxable_event_note_vs)
            self._fill_cell(sheet, row_index, 4, gain_loss.taxable_event_fiat_amount_with_fee_fraction, visual_style=taxable_event_note_vs, data_style="fiat")
            self._fill_cell(sheet, row_index, 6, "", visual_style=transparent_vs)
            self._fill_cell(sheet, row_index, 7, "", visual_style=transparent_vs)
            self._fill_cell(sheet, row_index, 8, gain_loss.fiat_gain, visual_style=transparent_vs, data_style="fiat")
            self._fill_cell(sheet, row_index, 9, transaction_type, visual_style=taxable_event_note_vs)
            self._fill_cell(sheet, row_index, 12, taxable_event_note, visual_style=taxable_event_note_vs)
            self._fill_cell(sheet, row_index, 13, gain_loss.taxable_event.unique_id, visual_style=taxable_event_note_vs)
            self._fill_cell(sheet, row_index, 14, "LONG" if gain_loss.is_long_term_capital_gains() else "SHORT", visual_style=taxable_event_note_vs)
            self._fill_cell(sheet, row_index, 15, gain_loss.taxable_event.timestamp, visual_style=taxable_event_note_vs)

            if gain_loss.acquired_lot:
                current_acquired_lot_fraction: int = gain_loss_set.get_acquired_lot_fraction(gain_loss) + 1
                total_acquired_lot_fractions: int = gain_loss_set.get_acquired_lot_number_of_fractions(gain_loss.acquired_lot)
                acquired_lot_note: str = (
                    f"{current_acquired_lot_fraction}/"
                    f"{total_acquired_lot_fractions}: "
                    f"{gain_loss.crypto_amount:.8f} of "
                    f"{gain_loss.acquired_lot.crypto_balance_change:.8f} "
                    f"{asset}"
                )
                self._fill_cell(sheet, row_index, 2, gain_loss.acquired_lot.timestamp.strftime("%m/%d/%Y"), visual_style=acquired_lot_note_vs)
                self._fill_cell(sheet, row_index, 5, gain_loss.fiat_cost_basis, visual_style=acquired_lot_note_vs, data_style="fiat")
                self._fill_cell(sheet, row_index, 10, acquired_lot_note, visual_style=acquired_lot_note_vs)
                self._fill_cell(sheet, row_index, 11, gain_loss.acquired_lot.unique_id, visual_style=acquired_lot_note_vs)
            else:
                self._fill_cell(sheet, row_index, 2, "", visual_style=transparent_vs)
                self._fill_cell(sheet, row_index, 5, "", visual_style=transparent_vs)
                self._fill_cell(sheet, row_index, 10, "", visual_style=transparent_vs)
                self._fill_cell(sheet, row_index, 11, "", visual_style=transparent_vs)

            border_suffix = ""
            row_indexes[sheet.name] = row_index + 1


def main() -> None:
    pass


if __name__ == "__main__":
    main()

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

from dataclasses import dataclass
from typing import Dict, List, cast

from rp2.balance import BalanceSet
from rp2.configuration import Configuration
from rp2.entry_types import EntrySetType, TransactionType
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError
from rp2.transaction_set import TransactionSet


@dataclass(frozen=True, eq=True)
class YearlyGainLoss:
    year: int
    asset: str
    transaction_type: TransactionType
    is_long_term_capital_gains: bool
    crypto_amount: RP2Decimal
    fiat_amount: RP2Decimal
    fiat_cost_basis: RP2Decimal
    fiat_gain_loss: RP2Decimal

    def __post_init__(self) -> None:
        Configuration.type_check_positive_int("year", self.year)
        Configuration.type_check_string("asset", self.asset)
        TransactionType.type_check("transaction_type", self.transaction_type)
        Configuration.type_check_bool("is_long_term", self.is_long_term_capital_gains)
        Configuration.type_check_decimal("crypto_amount", self.crypto_amount)
        Configuration.type_check_decimal("fiat_amount", self.fiat_amount)
        Configuration.type_check_decimal("fiat_cost_basis", self.fiat_cost_basis)
        Configuration.type_check_decimal("fiat_gain_loss", self.fiat_gain_loss)

    def __eq__(self, other: object) -> bool:
        if not other:
            return False
        if not isinstance(other, YearlyGainLoss):
            raise RP2TypeError(f"Operand has non-YearlyGainLoss value {repr(other)}")
        result: bool = (
            self.year == other.year
            and self.asset == other.asset
            and self.transaction_type == other.transaction_type
            and self.is_long_term_capital_gains == other.is_long_term_capital_gains
        )
        return result

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other: object) -> bool:
        if not other:
            return False
        if not isinstance(other, YearlyGainLoss):
            raise RP2TypeError(f"Operand has non-YearlyGainLoss value {repr(other)}")
        return self.year < other.year

    def __gt__(self, other: object) -> bool:
        if not other:
            return False
        if not isinstance(other, YearlyGainLoss):
            raise RP2TypeError(f"Operand has non-YearlyGainLoss value {repr(other)}")
        return self.year > other.year

    def __ge__(self, other: object) -> bool:
        return not self.__lt__(other)

    def __le__(self, other: object) -> bool:
        return not self.__gt__(other)

    def __hash__(self) -> int:
        return hash((self.year, self.asset, self.transaction_type, self.is_long_term_capital_gains))


class ComputedData:
    @classmethod
    def type_check(cls, name: str, instance: "ComputedData") -> "ComputedData":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    @staticmethod
    def _filter_yearly_gain_loss_by_year(unfiltered_yearly_gain_loss_list: List[YearlyGainLoss], from_year: int, to_year: int) -> List[YearlyGainLoss]:
        return [y for y in unfiltered_yearly_gain_loss_list if y.year >= from_year and y.year <= to_year]

    @staticmethod
    def _compute_price_per_unit(unfiltered_in_transaction_set: TransactionSet, to_year: int) -> RP2Decimal:
        crypto_in_running_sum: RP2Decimal = ZERO
        fiat_in_with_fee_running_sum: RP2Decimal = ZERO
        for entry in unfiltered_in_transaction_set:
            # from_year is not used when computing average price per unit (because we always start from the beginning): only to_year is relevant.
            if entry.timestamp.year > to_year:
                break
            transaction: InTransaction = cast(InTransaction, entry)
            crypto_in_running_sum += transaction.crypto_in
            fiat_in_with_fee_running_sum += transaction.fiat_in_with_fee
        return fiat_in_with_fee_running_sum / crypto_in_running_sum if crypto_in_running_sum is not ZERO else ZERO

    def __init__(
        self,
        asset: str,
        unfiltered_taxable_event_set: TransactionSet,
        unfiltered_gain_loss_set: GainLossSet,
        unfiltered_yearly_gain_loss_list: List[YearlyGainLoss],
        input_data: InputData,
        from_year: int,
        to_year: int,
    ) -> None:
        # pylint: disable=too-many-branches
        InputData.type_check("input_data", input_data)
        Configuration.type_check_positive_int("from_year", from_year)
        Configuration.type_check_positive_int("to_year", to_year, non_zero=True)

        self.__asset: str = Configuration.type_check_string("asset", asset)
        TransactionSet.type_check("taxable_event_set", unfiltered_taxable_event_set, EntrySetType.MIXED, asset, True)
        GainLossSet.type_check("gain_loss_set", unfiltered_gain_loss_set)

        self.__filtered_taxable_event_set: TransactionSet = cast(TransactionSet, unfiltered_taxable_event_set.duplicate(from_year=from_year, to_year=to_year))
        self.__filtered_gain_loss_set: GainLossSet = cast(GainLossSet, unfiltered_gain_loss_set.duplicate(from_year=from_year, to_year=to_year))

        if not isinstance(unfiltered_yearly_gain_loss_list, List):
            raise RP2TypeError(f"Parameter 'yearly_gain_loss_list' is not of type List: {unfiltered_yearly_gain_loss_list}")
        self.__filtered_yearly_gain_loss_list: List[YearlyGainLoss] = self._filter_yearly_gain_loss_by_year(
            unfiltered_yearly_gain_loss_list, from_year, to_year
        )

        self.__filtered_in_transaction_set: TransactionSet = input_data.filtered_in_transaction_set
        self.__filtered_intra_transaction_set: TransactionSet = input_data.filtered_intra_transaction_set
        self.__filtered_out_transaction_set: TransactionSet = input_data.filtered_out_transaction_set

        self.__filtered_balance_set: BalanceSet = BalanceSet(unfiltered_taxable_event_set.configuration, input_data, to_year)
        self.__filtered_price_per_unit: RP2Decimal = self._compute_price_per_unit(input_data.unfiltered_in_transaction_set, to_year)

        # Compute crypto running sums
        self.__crypto_in_running_sum: Dict[InTransaction, RP2Decimal] = {}
        self.__crypto_out_running_sum: Dict[OutTransaction, RP2Decimal] = {}
        self.__crypto_out_fee_running_sum: Dict[OutTransaction, RP2Decimal] = {}
        self.__crypto_intra_fee_running_sum: Dict[IntraTransaction, RP2Decimal] = {}
        self.__crypto_gain_loss_running_sum: Dict[GainLoss, RP2Decimal] = {}

        crypto_running_sum: RP2Decimal
        crypto_fee_running_sum: RP2Decimal

        crypto_running_sum = ZERO
        for entry in input_data.unfiltered_in_transaction_set:
            in_transaction: InTransaction = cast(InTransaction, entry)
            crypto_running_sum += in_transaction.crypto_in
            self.__crypto_in_running_sum[in_transaction] = crypto_running_sum

        crypto_running_sum = ZERO
        crypto_fee_running_sum = ZERO
        for entry in input_data.unfiltered_out_transaction_set:
            out_transaction: OutTransaction = cast(OutTransaction, entry)
            crypto_running_sum += out_transaction.crypto_out_no_fee
            crypto_fee_running_sum += out_transaction.crypto_fee
            self.__crypto_out_running_sum[out_transaction] = crypto_running_sum
            self.__crypto_out_fee_running_sum[out_transaction] = crypto_fee_running_sum

        crypto_fee_running_sum = ZERO
        for entry in input_data.unfiltered_intra_transaction_set:
            intra_transaction: IntraTransaction = cast(IntraTransaction, entry)
            crypto_fee_running_sum += intra_transaction.crypto_fee
            self.__crypto_intra_fee_running_sum[intra_transaction] = crypto_fee_running_sum

        crypto_running_sum = ZERO
        gain_loss: GainLoss
        for entry in unfiltered_gain_loss_set:
            gain_loss = cast(GainLoss, entry)
            crypto_running_sum += gain_loss.crypto_amount
            self.__crypto_gain_loss_running_sum[gain_loss] = crypto_running_sum

        # Compute in lot sold percentages
        self.__in_lot_sold_percentage: Dict[InTransaction, RP2Decimal] = {}
        for entry in self.__filtered_gain_loss_set:
            gain_loss = cast(GainLoss, entry)
            if not gain_loss.from_lot or gain_loss.from_lot.timestamp.year < from_year or gain_loss.from_lot.timestamp.year > to_year:
                continue
            self.__in_lot_sold_percentage[gain_loss.from_lot] = (
                self.__in_lot_sold_percentage.setdefault(gain_loss.from_lot, ZERO) + gain_loss.from_lot_fraction_percentage
            )

        if self.__filtered_taxable_event_set.asset != self.__asset:
            raise RP2ValueError(f"Asset mismatch in 'taxable_event_set': expected {self.__asset}, found {self.__filtered_taxable_event_set.asset}")
        if self.__filtered_gain_loss_set.asset != self.__asset:
            raise RP2ValueError(f"Asset mismatch in 'gain_loss_set': expected {self.__asset}, found {self.__filtered_gain_loss_set.asset}")
        if self.__filtered_balance_set.asset != self.__asset:
            raise RP2ValueError(f"Asset mismatch in 'balance_set': expected {self.__asset}, found {self.__filtered_balance_set.asset}")

        if self.__asset != input_data.asset:
            raise RP2ValueError(f"Asset mismatch in 'input_data': expected {self.__asset}, found {input_data.asset}")

    @property
    def asset(self) -> str:
        """Asset this ComputedData instance is about."""
        return self.__asset

    @property
    def taxable_event_set(self) -> TransactionSet:
        """Set of taxable events in this ComputedData instance."""
        return self.__filtered_taxable_event_set

    @property
    def gain_loss_set(self) -> GainLossSet:
        """Set of gain/loss mappings in this ComputedData instance."""
        return self.__filtered_gain_loss_set

    @property
    def yearly_gain_loss_list(self) -> List[YearlyGainLoss]:
        """List of gain/loss summaries in this ComputedData instance, grouped by year."""
        return self.__filtered_yearly_gain_loss_list

    @property
    def in_transaction_set(self) -> TransactionSet:
        """Set of in-transactions in this ComputedData instance."""
        return self.__filtered_in_transaction_set

    @property
    def out_transaction_set(self) -> TransactionSet:
        """Set of out-transactions in this ComputedData instance."""
        return self.__filtered_out_transaction_set

    @property
    def intra_transaction_set(self) -> TransactionSet:
        """Set of intra-transactions in this ComputedData instance."""
        return self.__filtered_intra_transaction_set

    @property
    def balance_set(self) -> BalanceSet:
        """Set of account balances in this ComputedData instance."""
        return self.__filtered_balance_set

    @property
    def price_per_unit(self) -> RP2Decimal:
        """Average price per asset unit."""
        return self.__filtered_price_per_unit

    def get_crypto_in_running_sum(self, in_transaction: InTransaction) -> RP2Decimal:
        """Crypto in running sum for a given InTransaction instance."""
        InTransaction.type_check("in_transaction", in_transaction)
        return self.__crypto_in_running_sum[in_transaction]

    def get_crypto_out_running_sum(self, out_transaction: OutTransaction) -> RP2Decimal:
        """Crypto running sum for a given OutTransaction instance."""
        OutTransaction.type_check("out_transaction", out_transaction)
        return self.__crypto_out_running_sum[out_transaction]

    def get_crypto_out_fee_running_sum(self, out_transaction: OutTransaction) -> RP2Decimal:
        """Crypto fee running sum for a given OutTransaction instance."""
        OutTransaction.type_check("out_transaction", out_transaction)
        return self.__crypto_out_fee_running_sum[out_transaction]

    def get_crypto_intra_fee_running_sum(self, intra_transaction: IntraTransaction) -> RP2Decimal:
        """Crypto fee running sum for a given IntraTransaction instance."""
        IntraTransaction.type_check("intra_transaction", intra_transaction)
        return self.__crypto_intra_fee_running_sum[intra_transaction]

    def get_crypto_gain_loss_running_sum(self, gain_loss: GainLoss) -> RP2Decimal:
        """Crypto amount running sum for a given GainLoss instance."""
        GainLoss.type_check("gain_loss", gain_loss)
        return self.__crypto_gain_loss_running_sum[gain_loss]

    def get_in_lot_sold_percentage(self, in_transaction: InTransaction) -> RP2Decimal:
        """Percentage sold for a given InTransaction instance"""
        InTransaction.type_check("in_transaction", in_transaction)
        return self.__in_lot_sold_percentage[in_transaction] if in_transaction in self.__in_lot_sold_percentage else ZERO

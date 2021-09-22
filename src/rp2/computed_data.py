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
from typing import List, cast

from rp2.balance import BalanceSet
from rp2.configuration import Configuration
from rp2.entry_types import EntrySetType, TransactionType
from rp2.gain_loss_set import GainLossSet
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
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
    usd_amount: RP2Decimal
    usd_cost_basis: RP2Decimal
    usd_gain_loss: RP2Decimal

    def __post_init__(self) -> None:
        Configuration.type_check_positive_int("year", self.year)
        Configuration.type_check_string("asset", self.asset)
        TransactionType.type_check("transaction_type", self.transaction_type)
        Configuration.type_check_bool("is_long_term", self.is_long_term_capital_gains)
        Configuration.type_check_decimal("crypto_amount", self.crypto_amount)
        Configuration.type_check_decimal("usd_amount", self.usd_amount)
        Configuration.type_check_decimal("usd_cost_basis", self.usd_cost_basis)
        Configuration.type_check_decimal("usd_gain_loss", self.usd_gain_loss)

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
    def _filter_yearly_gain_loss_by_year(yearly_gain_loss_list: List[YearlyGainLoss], from_year: int, to_year: int) -> List[YearlyGainLoss]:
        return [y for y in yearly_gain_loss_list if y.year >= from_year and y.year <= to_year]

    # from_year is not used when computing average price per unit (because we always start from the beginning): only to_year is relevant.
    @staticmethod
    def _compute_price_per_unit(in_transaction_set: TransactionSet, to_year: int) -> RP2Decimal:
        crypto_in_running_sum: RP2Decimal = ZERO
        usd_in_with_fee_running_sum: RP2Decimal = ZERO
        for entry in in_transaction_set:
            if entry.timestamp.year > to_year:
                break
            transaction: InTransaction = cast(InTransaction, entry)
            crypto_in_running_sum += transaction.crypto_in
            usd_in_with_fee_running_sum += transaction.usd_in_with_fee
        return usd_in_with_fee_running_sum / crypto_in_running_sum if crypto_in_running_sum is not ZERO else ZERO

    def __init__(
        self,
        asset: str,
        taxable_event_set: TransactionSet,
        gain_loss_set: GainLossSet,
        yearly_gain_loss_list: List[YearlyGainLoss],
        input_data: InputData,
        from_year: int,
        to_year: int,
    ) -> None:
        InputData.type_check("input_data", input_data)
        Configuration.type_check_positive_int("from_year", from_year)
        Configuration.type_check_positive_int("to_year", to_year, non_zero=True)

        self.__asset: str = Configuration.type_check_string("asset", asset)
        self.__taxable_event_set: TransactionSet = TransactionSet.type_check("taxable_event_set", taxable_event_set, EntrySetType.MIXED, asset, True)
        self.__gain_loss_set: GainLossSet = GainLossSet.type_check("gain_loss_set", gain_loss_set)

        if not isinstance(yearly_gain_loss_list, List):
            raise RP2TypeError(f"Parameter 'yearly_gain_loss_list' is not of type List: {yearly_gain_loss_list}")
        self.__yearly_gain_loss_list: List[YearlyGainLoss] = self._filter_yearly_gain_loss_by_year(yearly_gain_loss_list, from_year, to_year)

        self.__in_transaction_set: TransactionSet = input_data.in_transaction_set
        self.__intra_transaction_set: TransactionSet = input_data.intra_transaction_set
        self.__out_transaction_set: TransactionSet = input_data.out_transaction_set

        self.__balance_set: BalanceSet = BalanceSet(taxable_event_set.configuration, input_data, to_year)
        self.__price_per_unit: RP2Decimal = self._compute_price_per_unit(input_data.in_transaction_set, to_year)

        if self.__taxable_event_set.asset != self.__asset:
            raise RP2ValueError(f"Asset mismatch in 'taxable_event_set': expected {self.__asset}, found {self.__taxable_event_set.asset}")
        if self.__gain_loss_set.asset != self.__asset:
            raise RP2ValueError(f"Asset mismatch in 'gain_loss_set': expected {self.__asset}, found {self.__gain_loss_set.asset}")
        if self.__balance_set.asset != self.__asset:
            raise RP2ValueError(f"Asset mismatch in 'balance_set': expected {self.__asset}, found {self.__balance_set.asset}")

        if self.__asset != input_data.asset:
            raise RP2ValueError(f"Asset mismatch in 'input_data': expected {self.__asset}, found {input_data.asset}")

    @property
    def asset(self) -> str:
        return self.__asset

    @property
    def taxable_event_set(self) -> TransactionSet:
        return self.__taxable_event_set

    @property
    def gain_loss_set(self) -> GainLossSet:
        return self.__gain_loss_set

    @property
    def yearly_gain_loss_list(self) -> List[YearlyGainLoss]:
        return self.__yearly_gain_loss_list

    @property
    def in_transaction_set(self) -> TransactionSet:
        return self.__in_transaction_set

    @property
    def out_transaction_set(self) -> TransactionSet:
        return self.__out_transaction_set

    @property
    def intra_transaction_set(self) -> TransactionSet:
        return self.__intra_transaction_set

    @property
    def balance_set(self) -> BalanceSet:
        return self.__balance_set

    @property
    def price_per_unit(self) -> RP2Decimal:
        return self.__price_per_unit

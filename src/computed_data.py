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

from dataclasses import InitVar, dataclass
from typing import List

from balance import BalanceSet
from configuration import Configuration
from entry_types import EntrySetType, TransactionType
from gain_loss_set import GainLossSet
from input_data import InputData
from rp2_error import RP2TypeError, RP2ValueError
from transaction_set import TransactionSet


@dataclass(frozen=True)
class YearlyGainLoss:
    year: int
    asset: str
    transaction_type: TransactionType
    is_long_term: bool
    crypto_amount: float
    usd_amount: float
    usd_cost_basis: float
    usd_gain_loss: float

    def __post_init__(self) -> None:
        Configuration.type_check_positive_int("year", self.year)
        Configuration.type_check_string("asset", self.asset)
        TransactionType.type_check("transaction_type", self.transaction_type)
        Configuration.type_check_bool("is_long_term", self.is_long_term)
        Configuration.type_check_float("crypto_amount", self.crypto_amount)
        Configuration.type_check_float("usd_amount", self.usd_amount)
        Configuration.type_check_float("usd_cost_basis", self.usd_cost_basis)
        Configuration.type_check_float("usd_gain_loss", self.usd_gain_loss)

    def __lt__(self, other: "YearlyGainLoss") -> bool:
        return self.year < other.year


@dataclass
class ComputedData:
    asset: str
    taxable_event_set: TransactionSet
    gain_loss_set: GainLossSet
    balance_set: BalanceSet
    yearly_gain_loss_list: List[YearlyGainLoss]
    price_per_unit: float
    input_data: InitVar[InputData]

    @classmethod
    def type_check(cls, name: str, instance: "ComputedData") -> "ComputedData":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __post_init__(self, input_data: InputData) -> None:
        Configuration.type_check_string("asset", self.asset)
        TransactionSet.type_check("taxable_event_set", self.taxable_event_set, EntrySetType.MIXED, self.asset, True)
        GainLossSet.type_check("gain_loss_set", self.gain_loss_set)
        BalanceSet.type_check("balance_set", self.balance_set)
        if not isinstance(self.yearly_gain_loss_list, List):
            raise RP2TypeError(f"Parameter 'yearly_gain_loss_list' is not of type List: {self.yearly_gain_loss_list}")
        InputData.type_check("input_data", input_data)
        Configuration.type_check_positive_float("price_per_unit", self.price_per_unit)

        self.__in_transaction_set: TransactionSet = input_data.in_transaction_set
        self.__out_transaction_set: TransactionSet = input_data.out_transaction_set
        self.__intra_transaction_set: TransactionSet = input_data.intra_transaction_set

        if self.taxable_event_set.asset != self.asset:
            raise RP2ValueError(f"Asset mismatch in 'taxable_event_set': expected {self.asset}, found {self.taxable_event_set.asset}")
        if self.gain_loss_set.asset != self.asset:
            raise RP2ValueError(f"Asset mismatch in 'gain_loss_set': expected {self.asset}, found {self.gain_loss_set.asset}")
        if self.balance_set.asset != self.asset:
            raise RP2ValueError(f"Asset mismatch in 'balance_set': expected {self.asset}, found {self.balance_set.asset}")

        if self.asset != input_data.asset:
            raise RP2ValueError(f"Asset mismatch in 'input_data': expected {self.asset}, found {input_data.asset}")

    @property
    def in_transaction_set(self) -> TransactionSet:
        return self.__in_transaction_set

    @property
    def out_transaction_set(self) -> TransactionSet:
        return self.__out_transaction_set

    @property
    def intra_transaction_set(self) -> TransactionSet:
        return self.__intra_transaction_set

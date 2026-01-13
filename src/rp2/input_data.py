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

from datetime import date
from typing import Dict, Optional, cast

from rp2.abstract_entry import AbstractEntry
from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import MAX_DATE, MIN_DATE, Configuration
from rp2.entry_types import EntrySetType
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError
from rp2.transaction_set import TransactionSet


class InputData:
    @classmethod
    def type_check(cls, name: str, instance: "InputData") -> "InputData":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __init__(
        self,
        asset: str,
        unfiltered_in_transaction_set: TransactionSet,
        unfiltered_out_transaction_set: TransactionSet,
        unfiltered_intra_transaction_set: TransactionSet,
        in_transaction_2_actual_amount: Optional[Dict[InTransaction, RP2Decimal]] = None,
        from_date: date = MIN_DATE,
        to_date: date = MAX_DATE,
    ):
        self.__asset: str = Configuration.type_check_string("asset", asset)
        self.__unfiltered_in_transaction_set: TransactionSet = TransactionSet.type_check(
            "in_transaction_set", unfiltered_in_transaction_set, EntrySetType.IN, self.asset, False
        )
        self.__unfiltered_out_transaction_set: TransactionSet = TransactionSet.type_check(
            "out_transaction_set", unfiltered_out_transaction_set, EntrySetType.OUT, self.asset, True
        )
        self.__unfiltered_intra_transaction_set: TransactionSet = TransactionSet.type_check(
            "intra_transaction_set", unfiltered_intra_transaction_set, EntrySetType.INTRA, self.asset, True
        )
        self.__in_transaction_2_actual_amount: Dict[InTransaction, RP2Decimal] = (
            in_transaction_2_actual_amount if in_transaction_2_actual_amount is not None else {}
        )
        if not isinstance(from_date, date):
            raise RP2TypeError("Parameter 'from_date' is not of type date")
        if not isinstance(to_date, date):
            raise RP2TypeError("Parameter 'to_date' is not of type date")

        self.__filtered_in_transaction_set: TransactionSet = self.__unfiltered_in_transaction_set.duplicate(from_date=from_date, to_date=to_date)
        self.__filtered_out_transaction_set: TransactionSet = self.__unfiltered_out_transaction_set.duplicate(from_date=from_date, to_date=to_date)
        self.__filtered_intra_transaction_set: TransactionSet = self.__unfiltered_intra_transaction_set.duplicate(from_date=from_date, to_date=to_date)

        self.__from_date = from_date
        self.__to_date = to_date

    def __repr__(self) -> str:
        return (
            f"InputData(asset={self.asset}, from_date={self.from_date}, to_date={self.to_date}, "
            f"unfiltered_in_transaction_set={self.unfiltered_in_transaction_set}, "
            f"unfiltered_out_transaction_set={self.unfiltered_out_transaction_set}, "
            f"unfiltered_intra_transaction_set={self.unfiltered_intra_transaction_set}, "
            f"filtered_in_transaction_set={self.filtered_in_transaction_set}, "
            f"filtered_out_transaction_set={self.filtered_out_transaction_set}, "
            f"filtered_intra_transaction_set={self.filtered_intra_transaction_set}, "
            f"in_transaction_2_actual_amount={self.in_transaction_2_actual_amount})"
        )

    def __str__(self) -> str:
        return (
            f"InputData:\n"
            f"  asset={self.asset}\n"
            f"  from_date={self.from_date}\n"
            f"  to_date={self.to_date}\n"
            f"  unfiltered_in_transaction_set={self.unfiltered_in_transaction_set}\n"
            f"  unfiltered_out_transaction_set={self.unfiltered_out_transaction_set}\n"
            f"  unfiltered_intra_transaction_set={self.unfiltered_intra_transaction_set}\n"
            f"  filtered_in_transaction_set={self.filtered_in_transaction_set}\n"
            f"  filtered_out_transaction_set={self.filtered_out_transaction_set}\n"
            f"  filtered_intra_transaction_set={self.filtered_intra_transaction_set}\n"
            f"  in_transaction_2_actual_amount={self.in_transaction_2_actual_amount}\n"
        )

    def create_all_transaction_set(self, configuration: Configuration) -> TransactionSet:
        result: TransactionSet = TransactionSet(configuration, "MIXED", self.asset, MIN_DATE, MAX_DATE)
        for transaction_set in [
            self.unfiltered_in_transaction_set,
            self.unfiltered_out_transaction_set,
            self.unfiltered_intra_transaction_set,
        ]:
            for entry in transaction_set:
                result.add_entry(cast(AbstractTransaction, entry))
        return result

    def create_unfiltered_taxable_event_set(self, configuration: Configuration) -> TransactionSet:
        all_transaction_set: TransactionSet = self.create_all_transaction_set(configuration)
        result: TransactionSet = TransactionSet(configuration, "MIXED", self.asset, MIN_DATE, MAX_DATE)
        entry: AbstractEntry
        for entry in all_transaction_set:
            transaction = cast(AbstractTransaction, entry)
            if transaction.is_taxable():
                result.add_entry(transaction)
        return result

    @property
    def asset(self) -> str:
        return self.__asset

    @property
    def unfiltered_in_transaction_set(self) -> TransactionSet:
        return self.__unfiltered_in_transaction_set

    @property
    def unfiltered_out_transaction_set(self) -> TransactionSet:
        return self.__unfiltered_out_transaction_set

    @property
    def unfiltered_intra_transaction_set(self) -> TransactionSet:
        return self.__unfiltered_intra_transaction_set

    @property
    def filtered_in_transaction_set(self) -> TransactionSet:
        return self.__filtered_in_transaction_set

    @property
    def filtered_out_transaction_set(self) -> TransactionSet:
        return self.__filtered_out_transaction_set

    @property
    def filtered_intra_transaction_set(self) -> TransactionSet:
        return self.__filtered_intra_transaction_set

    # This is non-empty only in per-wallet application: InputData can contain artificial InTransactions that overlap with other InTransactions
    # (artificial or not). To understand which of these InTransactions actually contain funds and how much this Dict can be used. With universal
    # application this is always empty.
    @property
    def in_transaction_2_actual_amount(self) -> Dict[InTransaction, RP2Decimal]:
        return self.__in_transaction_2_actual_amount

    @property
    def from_date(self) -> date:
        return self.__from_date

    @property
    def to_date(self) -> date:
        return self.__to_date

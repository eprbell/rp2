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
from typing import cast

from rp2.configuration import MAX_DATE, MIN_DATE, Configuration
from rp2.entry_types import EntrySetType
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
        if not isinstance(from_date, date):
            raise RP2TypeError("Parameter 'from_date' is not of type date")
        if not isinstance(to_date, date):
            raise RP2TypeError("Parameter 'to_date' is not of type date")

        self.__filtered_in_transaction_set: TransactionSet = cast(
            TransactionSet, self.__unfiltered_in_transaction_set.duplicate(from_date=from_date, to_date=to_date)
        )
        self.__filtered_out_transaction_set: TransactionSet = cast(
            TransactionSet, self.__unfiltered_out_transaction_set.duplicate(from_date=from_date, to_date=to_date)
        )
        self.__filtered_intra_transaction_set: TransactionSet = cast(
            TransactionSet, self.__unfiltered_intra_transaction_set.duplicate(from_date=from_date, to_date=to_date)
        )

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

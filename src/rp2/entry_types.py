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

from enum import Enum
from typing import Optional, Set

from rp2.configuration import Configuration
from rp2.rp2_error import RP2TypeError, RP2ValueError


class TransactionType(Enum):
    AIRDROP: str = "airdrop"
    BUY: str = "buy"
    DONATE: str = "donate"
    FEE: str = "fee"
    GIFT: str = "gift"
    HARDFORK: str = "hardfork"
    INCOME: str = "income"
    INTEREST: str = "interest"
    MINING: str = "mining"
    MOVE: str = "move"
    SELL: str = "sell"
    STAKING: str = "staking"
    WAGES: str = "wages"

    @classmethod
    def has_value(cls, value: str) -> bool:
        return value in _transaction_type_values

    @classmethod
    def type_check_from_string(cls, name: str, transaction_type: str) -> "TransactionType":
        Configuration.type_check_string(name, transaction_type)
        if not TransactionType.has_value(transaction_type.lower()):
            raise RP2ValueError(f"Parameter '{name}' has invalid transaction type value: {transaction_type}")
        return TransactionType[transaction_type.upper()]

    @classmethod
    def type_check(cls, name: str, transaction_type: "TransactionType") -> "TransactionType":
        Configuration.type_check_parameter_name(name)
        if not isinstance(transaction_type, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {transaction_type}")
        return transaction_type

    def is_earn_type(self) -> bool:
        return self in _transaction_type_earn_values


_transaction_type_values: Set[str] = {item.value for item in TransactionType}
_transaction_type_earn_values: Set[TransactionType] = {
    TransactionType.AIRDROP,
    TransactionType.HARDFORK,
    TransactionType.INCOME,
    TransactionType.INTEREST,
    TransactionType.MINING,
    TransactionType.STAKING,
    TransactionType.WAGES,
}


class EntrySetType(Enum):
    IN: str = "in"
    INTRA: str = "intra"
    MIXED: str = "mixed"
    OUT: str = "out"

    @classmethod
    def has_value(cls, value: str) -> bool:
        return value in _entry_set_type_values

    @classmethod
    def get_entry_set_type_from_string(cls, entry_set_type: str) -> Optional["EntrySetType"]:
        if not isinstance(entry_set_type, str):
            # Disable mypy because otherwise it warns about unreachable code (we still want this runtime check)
            return None  # type: ignore
        if not EntrySetType.has_value(entry_set_type.lower()):
            return None
        return EntrySetType[entry_set_type.upper()]

    @classmethod
    def type_check_from_string(cls, name: str, entry_set_type: str) -> "EntrySetType":
        Configuration.type_check_string(name, entry_set_type)
        if not isinstance(entry_set_type, str):
            raise RP2TypeError(f"Parameter '{name}' is not of type string: {entry_set_type}")
        result = cls.get_entry_set_type_from_string(entry_set_type)
        if result is None:
            raise RP2ValueError(f"Parameter '{name}' has invalid entry set type value: {entry_set_type}")
        return result

    @classmethod
    def type_check(cls, name: str, entry_set_type: "EntrySetType") -> "EntrySetType":
        Configuration.type_check_parameter_name(name)
        if not isinstance(entry_set_type, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {entry_set_type}")
        return entry_set_type


_entry_set_type_values: Set[str] = {item.value for item in EntrySetType}

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

from rp2.abstract_entry import AbstractEntry
from rp2.abstract_entry_set import AbstractEntrySet
from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import Configuration
from rp2.entry_types import EntrySetType
from rp2.rp2_error import RP2TypeError, RP2ValueError


class TransactionSet(AbstractEntrySet):
    @classmethod
    def type_check(cls, name: str, instance: "TransactionSet", entry_set_type: EntrySetType, asset: str, allow_empty: bool = False) -> "TransactionSet":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter is not of type {cls.__name__}: {instance}")
        if instance.entry_set_type != entry_set_type:
            raise RP2ValueError(f"entry_set_type {instance.entry_set_type} != {entry_set_type}: {instance}")
        if instance.asset != asset:
            raise RP2ValueError(f"asset {instance.asset} != {asset}: {instance}")
        if not allow_empty and instance.is_empty():
            raise RP2ValueError(f"IN transaction set is empty: {instance}")
        return instance

    def add_entry(self, entry: AbstractEntry) -> None:
        AbstractTransaction.type_check("entry", entry)
        super().add_entry(entry)

    def _validate_entry(self, entry: AbstractEntry) -> None:
        AbstractTransaction.type_check("entry", entry)
        super()._validate_entry(entry)

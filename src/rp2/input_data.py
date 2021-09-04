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

from rp2.configuration import Configuration
from rp2.entry_types import EntrySetType
from rp2.rp2_error import RP2TypeError
from rp2.transaction_set import TransactionSet


@dataclass(frozen=True, eq=True)
class InputData:
    asset: str
    in_transaction_set: TransactionSet
    out_transaction_set: TransactionSet
    intra_transaction_set: TransactionSet

    @classmethod
    def type_check(cls, name: str, instance: "InputData") -> "InputData":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __post_init__(self) -> None:
        Configuration.type_check_string("asset", self.asset)
        TransactionSet.type_check("in_transaction_set", self.in_transaction_set, EntrySetType.IN, self.asset, False)
        TransactionSet.type_check("out_transaction_set", self.out_transaction_set, EntrySetType.OUT, self.asset, True)
        TransactionSet.type_check("intra_transaction_set", self.intra_transaction_set, EntrySetType.INTRA, self.asset, True)

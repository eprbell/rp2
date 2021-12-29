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

from rp2.configuration import Configuration
from rp2.gain_loss_set import GainLossSet
from rp2.rp2_error import RP2TypeError
from rp2.transaction_set import TransactionSet


class AbstractAccountingMethod:
    @classmethod
    def type_check(cls, name: str, instance: "AbstractAccountingMethod") -> "AbstractAccountingMethod":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def map_in_to_out_lots(self, configuration: Configuration, from_lot_set: TransactionSet, unfiltered_taxable_event_set: TransactionSet) -> GainLossSet:
        raise NotImplementedError("Abstract method")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}"

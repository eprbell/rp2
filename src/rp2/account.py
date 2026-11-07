# Copyright 2024 eprbell
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

from rp2.rp2_error import RP2TypeError, RP2ValueError


# Wallet identity: an exchange (or wallet) and its holder. Accounts sort by exchange, then holder.
# Both fields are checked at construction (an Account is a dictionary key in many places, so a wrong type would only fail much later, or
# never): e.g. Account("Kraken", "Bob") is valid, Account("Kraken", "") and Account("Kraken", 1) raise. Configuration checks separately that
# the names are listed in the exchanges and holders of the configuration file.
@dataclass(frozen=True, eq=True, order=True)
class Account:
    exchange: str
    holder: str

    def __post_init__(self) -> None:
        for name, value in (("exchange", self.exchange), ("holder", self.holder)):
            if not isinstance(value, str):
                raise RP2TypeError(f"Parameter '{name}' of Account is not a string: {repr(value)}")
            if not value.strip():
                raise RP2ValueError(f"Parameter '{name}' of Account is empty")

    @classmethod
    def type_check(cls, name: str, instance: "Account") -> "Account":
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

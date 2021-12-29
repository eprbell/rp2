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


from typing import List

from rp2.rp2_error import RP2TypeError


class AbstractCountry:
    @classmethod
    def type_check(cls, name: str, instance: "AbstractCountry") -> "AbstractCountry":
        if not isinstance(name, str):
            raise RP2TypeError(f"Parameter name is not a string: {repr(name)}")
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __init__(
        self,
        country_iso_code: str,  # ISO 3166-1 alpha-2
        currency_iso_code: str,  # ISO 4217
    ) -> None:

        if not isinstance(country_iso_code, str):
            raise RP2TypeError(f"Parameter 'country_iso_code' has non-string value {repr(country_iso_code)}")
        if not isinstance(currency_iso_code, str):
            raise RP2TypeError(f"Parameter 'currency_iso_code' has non-string value {repr(currency_iso_code)}")

        self.__country_iso_code = country_iso_code
        self.__currency_iso_code = currency_iso_code

    def __str__(self) -> str:
        output: List[str] = []
        output.append(f"{type(self).__name__}:")
        output.append(f"  country_iso_code={str(self.country_iso_code)}")
        output.append(f"  currency_iso_code={str(self.currency_iso_code)}")
        output.append(f"  long_term_capital_gain_period={str(self.long_term_capital_gain_period())}")
        return "\n".join(output)

    def __repr__(self) -> str:
        output: List[str] = []
        output.append(f"{type(self).__name__}(")
        output.append(f"country_iso_code={str(self.country_iso_code)}")
        output.append(f", currency_iso_code={str(self.currency_iso_code)}")
        output.append(f", long_term_capital_gain_period={str(self.long_term_capital_gain_period())}")
        output.append(")")
        return "".join(output)

    @property
    def country_iso_code(self) -> str:
        return self.__country_iso_code

    @property
    def currency_iso_code(self) -> str:
        return self.__currency_iso_code

    # Measured in days
    def long_term_capital_gain_period(self) -> int:
        raise NotImplementedError("Abstract function")

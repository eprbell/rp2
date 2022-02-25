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

from datetime import datetime
from typing import List, Optional

from rp2.configuration import Configuration, to_string
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2TypeError


class AbstractEntry:
    def __init__(
        self,
        configuration: Configuration,
        asset: str,
    ) -> None:
        self.__configuration = Configuration.type_check("configuration", configuration)
        self.__asset: str = configuration.type_check_asset("asset", asset)

    @classmethod
    def type_check(cls, name: str, instance: "AbstractEntry") -> "AbstractEntry":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def to_string(self, indent: int = 0, repr_format: bool = True, extra_data: Optional[List[str]] = None) -> str:
        class_specific_data: List[str] = []
        if repr_format:
            class_specific_data.append(f"{type(self).__name__}(id={repr(self.internal_id)}")
        else:
            class_specific_data.append(f"{type(self).__name__}:")
            class_specific_data.append(f"id={str(self.internal_id)}")

        if extra_data:
            class_specific_data.extend(extra_data)

        return to_string(indent=indent, repr_format=repr_format, data=class_specific_data)

    def __str__(self) -> str:
        return self.to_string(indent=0, repr_format=False)

    def __repr__(self) -> str:
        return self.to_string(indent=0, repr_format=True)

    # Used for hashing but there are not enough attributes in this class, so the method is abstract.
    def __eq__(self, other: object) -> bool:
        raise NotImplementedError("Abstract method")

    # Used for hashing but there are not enough attributes in this class, so the method is abstract.
    def __ne__(self, other: object) -> bool:
        raise NotImplementedError("Abstract method")

    # Used for hashing but there are not enough attributes in this class, so the method is abstract.
    def __hash__(self) -> int:
        raise NotImplementedError("Abstract method")

    @property
    def configuration(self) -> Configuration:
        return self.__configuration

    @property
    def asset(self) -> str:
        return self.__asset

    @property
    def internal_id(self) -> str:
        raise NotImplementedError("Abstract property")

    @property
    def timestamp(self) -> datetime:
        raise NotImplementedError("Abstract property")

    # How much crypto was gained / lost with this entry
    @property
    def crypto_balance_change(self) -> RP2Decimal:
        raise NotImplementedError("Abstract property")

    # How much fiat was gained / lost with this entry
    @property
    def fiat_balance_change(self) -> RP2Decimal:
        raise NotImplementedError("Abstract property")

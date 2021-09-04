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

from typing import Optional


class RP2Error(Exception):
    def __init__(self, message: str, unique_id: Optional[int] = None) -> None:
        self.__message = message if unique_id is None else f"{unique_id}: {message}"
        self.__unique_id = unique_id
        super().__init__(self.__message)

    def __repr__(self) -> str:
        return self.message

    @property
    def message(self) -> str:
        return self.__message

    @property
    def unique_id(self) -> Optional[int]:
        return self.__unique_id


class RP2TypeError(RP2Error):
    pass


class RP2ValueError(RP2Error):
    pass

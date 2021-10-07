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

from copy import copy
from datetime import datetime
from typing import Dict, List, Optional, Set

from rp2.abstract_entry import AbstractEntry
from rp2.configuration import MAX_YEAR, Configuration
from rp2.entry_types import EntrySetType
from rp2.in_transaction import InTransaction
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.rp2_error import RP2TypeError, RP2ValueError


class AbstractEntrySet:
    def __init__(
        self,
        configuration: Configuration,
        entry_set_type: str,
        asset: str,
        from_year: int,
        to_year: int,
    ) -> None:
        self.__configuration: Configuration = Configuration.type_check("configuration", configuration)
        self.__entry_set_type: EntrySetType = EntrySetType.type_check_from_string("entry_set_type", entry_set_type)
        self.__asset: str = configuration.type_check_asset("asset", asset)
        self._from_year: int = configuration.type_check_positive_int("from_year", from_year)
        self._to_year: int = configuration.type_check_positive_int("to_year", to_year, non_zero=True)

        self._entry_list: List[AbstractEntry] = []  # List for sorting
        self._entry_set: Set[AbstractEntry] = set()  # Set for fast search (at the cost of extra memory)
        self._entry_to_parent: Dict[AbstractEntry, Optional[AbstractEntry]] = {}
        self.__is_sorted: bool = False

    def duplicate(self, from_year: int = 0, to_year: int = MAX_YEAR) -> "AbstractEntrySet":
        # pylint: disable=protected-access
        result: AbstractEntrySet = copy(self)
        result._from_year = from_year
        result._to_year = to_year
        # Force sort to recompute fields that are affected by time filter
        result._force_sort()
        return result

    def __str__(self) -> str:
        output: List[str] = []
        output.append(f"{type(self).__name__}:")
        output.append(f"  configuration={str(self.__configuration.configuration_path)}")
        output.append(f"  entry_set_type={str(self.entry_set_type)}")
        output.append(f"  asset={str(self.asset)}")
        output.append(f"  from_year={str(self.from_year) if self.from_year > 0 else 'non-specified'}")
        output.append(f"  to_year={str(self.to_year) if self.to_year < MAX_YEAR else 'non-specified'}")
        output.append("  entries=")
        for entry in self:
            parent: Optional[AbstractEntry]
            parent = self.get_parent(entry)
            output.append(entry.to_string(indent=2, repr_format=False, extra_data=[f"parent={str(parent.unique_id if parent else None)}"]))
        return "\n".join(output)

    def __repr__(self) -> str:
        output: List[str] = []
        output.append(f"{type(self).__name__}(")
        output.append(f"configuration={repr(self.__configuration.configuration_path)}")
        output.append(f", entry_set_type={repr(self.entry_set_type)}")
        output.append(f", asset={repr(self.asset)}")
        output.append(f", from_year={repr(self.from_year) if self.from_year > 0 else 'non-specified'}")
        output.append(f", to_year={repr(self.to_year) if self.to_year < MAX_YEAR else 'non-specified'}")
        output.append(", entries=[")
        for entry in self:
            parent: Optional[AbstractEntry]
            parent = self.get_parent(entry)
            output.append(entry.to_string(indent=2, repr_format=True, extra_data=[f"parent={repr(parent.unique_id if parent else None)}"]))
        output.append("]")
        output.append(")")
        return "".join(output)

    @property
    def configuration(self) -> Configuration:
        return self.__configuration

    @property
    def entry_set_type(self) -> EntrySetType:
        return self.__entry_set_type

    @property
    def asset(self) -> str:
        return self.__asset

    @property
    def from_year(self) -> int:
        return self._from_year

    @property
    def to_year(self) -> int:
        return self._to_year

    @property
    def count(self) -> int:
        return len(self._entry_list)

    def add_entry(self, entry: AbstractEntry) -> None:
        AbstractEntry.type_check("entry", entry)

        if entry.asset != self.asset:
            raise RP2ValueError(f"Attempting to add a {entry.asset} entry to a {self.asset} set")
        if self.entry_set_type == EntrySetType.IN and not isinstance(entry, InTransaction):
            raise RP2TypeError(f"Attempting to add a {entry.__class__.__name__} to a set of type IN")
        if self.entry_set_type == EntrySetType.INTRA and not isinstance(entry, IntraTransaction):
            raise RP2TypeError(f"Attempting to add a {entry.__class__.__name__} to a set of type INTRA")
        if self.entry_set_type == EntrySetType.OUT and not isinstance(entry, OutTransaction):
            raise RP2TypeError(f"Attempting to add a {entry.__class__.__name__} to a set of type OUT")
        if entry in self._entry_set:
            raise RP2ValueError(f"Entry already added: {entry}")

        self._entry_list.append(entry)
        self._entry_set.add(entry)
        self.__is_sorted = False

    def is_empty(self) -> bool:
        return self.count == 0

    def _validate_entry(self, entry: AbstractEntry) -> None:
        AbstractEntry.type_check("entry", entry)
        if entry not in self._entry_set:
            raise RP2ValueError(f"Unknown entry:\n{entry}")

    def get_parent(self, entry: AbstractEntry) -> Optional[AbstractEntry]:
        self._validate_entry(entry)
        self._check_sort()
        return self._entry_to_parent[entry]

    def _sort_entries(self) -> None:
        # Sort entries by date, then add parent
        self._entry_list.sort(key=_entry_sort_key)
        parent: Optional[AbstractEntry] = None
        for entry in self._entry_list:
            self._entry_to_parent[entry] = parent
            parent = entry

    def _check_sort(self) -> None:
        if not self.__is_sorted:
            self._sort_entries()
            self.__is_sorted = True

    def _force_sort(self) -> None:
        self.__is_sorted = False
        self._check_sort()

    def __iter__(self) -> "EntrySetIterator":
        self._check_sort()
        return EntrySetIterator(self)


class EntrySetIterator:
    def __init__(self, entry_set: AbstractEntrySet) -> None:
        self.__entry_set: AbstractEntrySet = entry_set
        self.__entry_set_size: int = self.__entry_set.count
        self.__index: int = 0

    def __next__(self) -> AbstractEntry:
        result: Optional[AbstractEntry] = None
        while self.__index < self.__entry_set_size:
            result = self.__entry_set._entry_list[self.__index]  # pylint: disable=protected-access
            self.__index += 1
            if result.timestamp.year > self.__entry_set.to_year:
                raise StopIteration(self)
            if result.timestamp.year >= self.__entry_set.from_year:
                return result
        raise StopIteration(self)


def _entry_sort_key(entry: AbstractEntry) -> datetime:
    return entry.timestamp

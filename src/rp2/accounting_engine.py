# Copyright 2022 eprbell
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
from datetime import datetime, timezone
from typing import Dict, Iterator, List, Mapping, NamedTuple, Optional

from prezzemolo.avl_tree import AVLTree

from rp2.abstract_accounting_method import AbstractAccountingMethod, AbstractAcquiredLotCandidates
from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.lot_consumption import TakeResult, take_lots
from rp2.rp2_decimal import RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2TypeError


# A year of a year-to-method map and the accounting method used from that year on.
class YearAndAccountingMethod(NamedTuple):
    year: int
    accounting_method: AbstractAccountingMethod


def _get_year(year_and_accounting_method: YearAndAccountingMethod) -> int:
    return year_and_accounting_method.year


# The entries of a year-to-method map (e.g. 2024: fifo, 2026: hifo), sorted by year. AVLTree has no iterator, so its nodes are visited
# explicitly. Raises if the map is empty, or if a key isn't a year or a value isn't an accounting method.
def get_years_and_accounting_methods(years_2_methods: AVLTree[int, AbstractAccountingMethod]) -> List[YearAndAccountingMethod]:
    if not isinstance(years_2_methods, AVLTree):
        raise RP2TypeError(f"Parameter 'years_2_methods' is not of type AVLTree: {years_2_methods}")
    result: List[YearAndAccountingMethod] = []
    to_visit = [years_2_methods.root]
    while to_visit:
        node = to_visit.pop()
        if node is None:
            continue
        if not isinstance(node.key, int) or isinstance(node.key, bool):
            raise RP2TypeError(f"Parameter 'years_2_methods' has a non-integer year: {repr(node.key)}")
        if not isinstance(node.value, AbstractAccountingMethod):
            raise RP2TypeError(f"Parameter 'years_2_methods' has a value that is not an accounting method: {node.value}")
        result.append(YearAndAccountingMethod(node.key, node.value))
        to_visit.extend([node.left, node.right])
    if not result:
        raise RP2RuntimeError("Internal error: no accounting method defined")
    return sorted(result, key=_get_year)


# A private copy of a year-to-method map: the caller can't change it afterwards (e.g. by inserting a year).
def _copy_years_2_methods(years_2_methods: AVLTree[int, AbstractAccountingMethod]) -> AVLTree[int, AbstractAccountingMethod]:
    result: AVLTree[int, AbstractAccountingMethod] = AVLTree()
    for year, accounting_method in get_years_and_accounting_methods(years_2_methods):
        result.insert_node(year, accounting_method)
    return result


@dataclass(frozen=True, eq=True)
class _AcquiredLotAndIndex:
    acquired_lot: InTransaction
    index: int


# The lot pool of universal application at a given time: the lots acquired up to that time, in any wallet (lot_candidates), and the
# accounting method of the year (see AccountingEngine._get_lot_pool()).
class _LotPool(NamedTuple):
    accounting_method: AbstractAccountingMethod
    lot_candidates: AbstractAcquiredLotCandidates


# The lots of universal application: it keeps every acquired lot (in any wallet), the coins each one has left and the accounting method of
# each year. take() takes the coins of a taxable event from the lots acquired up to it, with the rules shared with per-wallet application
# (see lot_consumption.take_lots()).
class AccountingEngine:
    __acquired_lot_list: List[InTransaction]
    __acquired_lot_avl: AVLTree[str, _AcquiredLotAndIndex]
    __acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal]

    # Disambiguation is needed for transactions that have the same timestamp, because the avl tree class expects unique keys: 12 decimal digits express
    # 1 quadrillion, which should be enough to capture the maximum number of same-timestamp transactions in all reasonable cases.
    KEY_DISAMBIGUATOR_LENGTH: int = 12
    MAX_KEY_DISAMBIGUATOR = "9" * KEY_DISAMBIGUATOR_LENGTH

    @classmethod
    def type_check(cls, name: str, instance: "AccountingEngine") -> "AccountingEngine":
        if not isinstance(name, str):
            raise RP2TypeError(f"Parameter name is not a string: {repr(name)}")
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    # years_2_methods is copied (and checked): changing the caller's map later doesn't change this engine.
    def __init__(self, years_2_methods: AVLTree[int, AbstractAccountingMethod]) -> None:
        self.__years_2_methods: AVLTree[int, AbstractAccountingMethod] = _copy_years_2_methods(years_2_methods)
        self.__years_2_lot_candidates: AVLTree[int, AbstractAcquiredLotCandidates] = AVLTree()

    # acquired_lot_iterator yields the lots in ascending chronological order. acquired_lot_to_partial_amount (if given) is the amount still
    # available in some lots (e.g. InputData.in_transaction_2_actual_amount): the engine works on a copy, because it updates the amounts while
    # pairing lots, and the caller's data (e.g. the input data) must not change. Before this copy, computing taxes on the same input data
    # twice could give different results.
    def initialize(
        self,
        acquired_lot_iterator: Iterator[InTransaction],
        acquired_lot_to_partial_amount: Optional[Mapping[InTransaction, RP2Decimal]] = None,
    ) -> None:
        self.__acquired_lot_list = []
        self.__acquired_lot_avl: AVLTree[str, _AcquiredLotAndIndex] = AVLTree()
        self.__acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal] = (
            {} if acquired_lot_to_partial_amount is None else dict(acquired_lot_to_partial_amount)
        )

        index: int = 0
        try:
            while True:
                acquired_lot: InTransaction = next(acquired_lot_iterator)
                self.__acquired_lot_list.append(acquired_lot)
                self.__acquired_lot_avl.insert_node(
                    f"{self._get_avl_node_key(acquired_lot.timestamp, acquired_lot.internal_id)}", _AcquiredLotAndIndex(acquired_lot, index)
                )
                index += 1
        except StopIteration:
            # End of acquired_lots
            pass

        if not self.__acquired_lot_avl.root:
            raise RP2RuntimeError("Internal error: AVL tree has no root node")

        for year, accounting_method in get_years_and_accounting_methods(self.__years_2_methods):
            # Pass __acquired_lot_2_partial_amount to all lot candidates so that they share the partial amount cache even across different accounting methods.
            self.__years_2_lot_candidates.insert_node(
                year, accounting_method.create_lot_candidates(self.__acquired_lot_list, self.__acquired_lot_2_partial_amount)
            )

    # AVL tree node keys have this format: <timestamp>_<internal_id>. The internal_id part is needed to disambiguate transactions
    # that have the same timestamp. Timestamp is in format "YYYYmmddHHMMSS.ffffff" and internal_id is padded right in a string of fixed
    # length (KEY_DISAMBIGUATOR_LENGTH).
    def _get_avl_node_key(self, timestamp: datetime, internal_id: str) -> str:
        return f"{timestamp.astimezone(timezone.utc).strftime('%Y%m%d%H%M%S.%f')}_{internal_id:0>{self.KEY_DISAMBIGUATOR_LENGTH}}"

    # This function calls _get_avl_node_key with internal_id=MAX_KEY_DISAMBIGUATOR, so that the generated key is larger than any other key
    # with the same timestamp.
    def _get_avl_node_key_with_max_disambiguator(self, timestamp: datetime) -> str:
        return self._get_avl_node_key(timestamp, self.MAX_KEY_DISAMBIGUATOR)

    # A copy: changing it doesn't change this engine.
    @property
    def years_2_methods(self) -> AVLTree[int, AbstractAccountingMethod]:
        return _copy_years_2_methods(self.__years_2_methods)

    def _get_accounting_method(self, year: int) -> AbstractAccountingMethod:
        method = self.__years_2_methods.find_max_value_less_than(year)
        if method is None:
            raise RP2RuntimeError(f"Internal error: no accounting method assigned for year {year}")
        if not isinstance(method, AbstractAccountingMethod):
            raise RP2RuntimeError(f"Internal error: accounting method assigned for year {year} is not of type AbstractAccountingMethod: {method}")
        return method

    # The lot pool of universal application at timestamp (in the tax time zone, see Configuration.tax_timezone): the lots acquired up to
    # timestamp, in any wallet, with the accounting method of its year. None if no lot was acquired by then.
    def _get_lot_pool(self, timestamp: datetime) -> Optional[_LotPool]:
        # The last lot acquired up to timestamp (lots acquired at timestamp included): its index is the upper bound of the lot candidates.
        acquired_lot_and_index: Optional[_AcquiredLotAndIndex] = self.__acquired_lot_avl.find_max_value_less_than(
            self._get_avl_node_key_with_max_disambiguator(timestamp)
        )
        if acquired_lot_and_index is None:
            return None
        if acquired_lot_and_index.acquired_lot != self.__acquired_lot_list[acquired_lot_and_index.index]:
            raise RP2RuntimeError("Internal error: acquired_lot incongruence in accounting logic")
        method = self._get_accounting_method(timestamp.year)
        lot_candidates: Optional[AbstractAcquiredLotCandidates] = self.__years_2_lot_candidates.find_max_value_less_than(timestamp.year)
        # lot_candidates is 1:1 with acquired_lot_and_index, should always be True
        if not lot_candidates:
            raise RP2RuntimeError("Internal error: no lot candidates found for year")
        lot_candidates.set_to_index(acquired_lot_and_index.index)
        return _LotPool(method, lot_candidates)

    # Takes amount coins for taxable_event (a disposal or a fee) from the lots acquired up to it, in any wallet, in the order of the
    # accounting method of its tax year (see lot_consumption.take_lots()). The tax year comes from the taxable event's timestamp in the tax
    # time zone (see Configuration.tax_timezone): it's the same instant, so the lots acquired before it are the same.
    # Example: lots bought on Coinbase in 2023 and on Kraken in 2024, FIFO: a sale on Kraken in 2024 takes the Coinbase lot first.
    def take(self, taxable_event: AbstractTransaction, amount: RP2Decimal) -> TakeResult:
        AbstractTransaction.type_check("taxable_event", taxable_event)
        tax_timestamp = taxable_event.configuration.get_tax_timestamp(taxable_event.timestamp)
        lot_pool = self._get_lot_pool(tax_timestamp)
        if lot_pool is None:
            return TakeResult([], amount)
        return take_lots(lot_pool.accounting_method, lot_pool.lot_candidates, amount)

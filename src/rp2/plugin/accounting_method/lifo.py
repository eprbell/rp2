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
from datetime import datetime
from typing import Dict, Iterator, List, NamedTuple, Optional

from rp2.abstract_accounting_method import (
    FromLotsExhaustedException,
    TaxableEventAndFromLot,
    TaxableEventsExhaustedException,
)
from rp2.abstract_specific_id import AbstractSpecificId
from rp2.abstract_transaction import AbstractTransaction
from rp2.avl_tree import AVLTree
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal


@dataclass
class FromLotAndIndex:
    from_lot: InTransaction
    index: int


class FromLotAndAmount(NamedTuple):
    from_lot: InTransaction
    amount: RP2Decimal


# LIFO plugin. See https://www.investopedia.com/terms/l/lifo.asp. Note that under LIFO the date acquired must still be before or on the date sold:
# see this discussion for details,
# https://ttlc.intuit.com/community/investments-and-rental-properties/discussion/using-lifo-method-for-cryptocurrency-or-even-stock-cost-basis/00/1433542
class AccountingMethod(AbstractSpecificId):

    __taxable_event_iterator: Iterator[AbstractTransaction]
    __year_2_from_lot_list: Dict[int, List[InTransaction]]
    __year_2_from_lot_avl: Dict[int, AVLTree[str, FromLotAndIndex]]
    __from_lot_2_partial_amount: Dict[InTransaction, RP2Decimal]
    __min_from_lot_year: int

    # Disambiguation is needed for transactions that have the same timestamp, because the avl tree class expects unique keys: 12 decimal digits express
    # 1 quadrillion, which should be enough to capture the maximum number of same-timestamp transactions in all reasonable cases.
    KEY_DISAMBIGUATOR_LENGTH: int = 12
    MAX_KEY_DISAMBIGUATOR = "9" * KEY_DISAMBIGUATOR_LENGTH

    # Iterators yield transactions in ascending chronological order
    def initialize(self, taxable_event_iterator: Iterator[AbstractTransaction], from_lot_iterator: Iterator[InTransaction]) -> None:
        self.__taxable_event_iterator = taxable_event_iterator
        self.__year_2_from_lot_list = {}
        self.__year_2_from_lot_avl = {}
        self.__from_lot_2_partial_amount = {}

        # Initialize data structure to hold from_lots in chronological order by year (dictionary of from_lot lists, indexed by year)
        year: int = 0
        from_lot_list: List[InTransaction] = []
        from_lot_avl: AVLTree[str, FromLotAndIndex] = AVLTree()
        index: int = 0
        try:
            while True:
                from_lot: InTransaction = next(from_lot_iterator)
                if year != from_lot.timestamp.year:
                    if year == 0:
                        self.__min_from_lot_year = from_lot.timestamp.year
                    else:
                        self._store_from_lots_for_year(year, from_lot_list, from_lot_avl)
                    year = from_lot.timestamp.year
                    from_lot_list = []
                    from_lot_avl = AVLTree()
                    index = 0
                from_lot_list.append(from_lot)
                # Key is <timestamp>_<unique_id>
                from_lot_avl.insert_node(f"{self._get_avl_node_key(from_lot.timestamp, from_lot.unique_id)}", FromLotAndIndex(from_lot, index))
                index += 1
        except StopIteration:
            # End of from_lots
            pass
        self._store_from_lots_for_year(year, from_lot_list, from_lot_avl)

    # AVL tree node keys have this format: <timestamp>_<unique_id>. The unique_id part is needed to disambiguate transactions
    # that have the same timestamp. Timestamp is in format "YYYYmmddHHMMSS.ffffff" and unique_id is padded right in a string of fixed
    # length (KEY_DISAMBIGUATOR_LENGTH).
    def _get_avl_node_key(self, timestamp: datetime, unique_id: str) -> str:
        return f"{timestamp.strftime('%Y%m%d%H%M%S.%f')}_{unique_id:0>{self.KEY_DISAMBIGUATOR_LENGTH}}"

    # This function calls _get_avl_node_key with unique_id=MAX_KEY_DISAMBIGUATOR, so that the generated key is larger than any other key
    # with the same timestamp.
    def _get_avl_node_key_with_max_disambiguator(self, timestamp: datetime) -> str:
        return self._get_avl_node_key(timestamp, self.MAX_KEY_DISAMBIGUATOR)

    def _store_from_lots_for_year(self, year: int, from_lot_list: List[InTransaction], from_lot_avl: AVLTree[str, FromLotAndIndex]) -> None:
        self.__year_2_from_lot_list[year] = from_lot_list
        self.__year_2_from_lot_avl[year] = from_lot_avl

        # From lots that have the same timestamp should all have the same from_lots list index (corresponding to the last element
        # with the same timestamp)
        previous_synchronous_from_lots: List[FromLotAndIndex] = []
        for index, from_lot in enumerate(from_lot_list):
            if not previous_synchronous_from_lots or previous_synchronous_from_lots[0].from_lot.timestamp == from_lot.timestamp:
                previous_synchronous_from_lots.append(FromLotAndIndex(from_lot, index))
            else:
                synchronous_index: int = previous_synchronous_from_lots[-1].index
                for previous_from_lot in previous_synchronous_from_lots:
                    previous_from_lot.index = synchronous_index
                previous_synchronous_from_lots = []

    def get_next_taxable_event_and_amount(
        self, taxable_event: Optional[AbstractTransaction], from_lot: Optional[InTransaction], taxable_event_amount: RP2Decimal, from_lot_amount: RP2Decimal
    ) -> TaxableEventAndFromLot:
        new_from_lot: Optional[InTransaction] = from_lot
        new_from_lot_amount: RP2Decimal = from_lot_amount - taxable_event_amount if from_lot is not None else ZERO

        try:
            new_taxable_event: AbstractTransaction = next(self.__taxable_event_iterator)
        except StopIteration:
            raise TaxableEventsExhaustedException() from None
        new_taxable_event_amount: RP2Decimal = new_taxable_event.crypto_taxable_amount

        # If the new taxable event has different year than the from lot (and it's not earn-typed), also get a new from lot from the new year
        if taxable_event and taxable_event.timestamp < new_taxable_event.timestamp:
            if from_lot:
                # Cache old-year from_lot amount
                self.__from_lot_2_partial_amount[from_lot] = new_from_lot_amount
            (_, new_from_lot, _, new_from_lot_amount) = self.get_from_lot_for_taxable_event(
                new_taxable_event, from_lot, new_taxable_event.crypto_taxable_amount, new_from_lot_amount
            )

        return TaxableEventAndFromLot(
            taxable_event=new_taxable_event,
            from_lot=new_from_lot,
            taxable_event_amount=new_taxable_event_amount,
            from_lot_amount=new_from_lot_amount,
        )

    # After selecting the taxable event, RP2 calls this function to find the from_lot to pair with it. This means that the taxable
    # event can be passed to this function (which is useful for certain accounting methods)
    def get_from_lot_for_taxable_event(
        self, taxable_event: AbstractTransaction, from_lot: Optional[InTransaction], taxable_event_amount: RP2Decimal, from_lot_amount: RP2Decimal
    ) -> TaxableEventAndFromLot:
        new_taxable_event_amount: RP2Decimal = taxable_event_amount - from_lot_amount
        year: int = taxable_event.timestamp.year
        while year >= self.__min_from_lot_year:
            if year not in self.__year_2_from_lot_list:
                year -= 1
                continue
            from_lot_list: List[InTransaction] = self.__year_2_from_lot_list[year]
            from_lot_avl: AVLTree[str, FromLotAndIndex] = self.__year_2_from_lot_avl[year]
            first_lot: Optional[FromLotAndIndex] = from_lot_avl.find_max_value_less_than(
                f"{self._get_avl_node_key_with_max_disambiguator(taxable_event.timestamp)}"
            )
            if first_lot is not None:
                from_lot_index: int = first_lot.index
                if first_lot.from_lot != from_lot_list[from_lot_index]:
                    raise Exception("Internal error: from_lot incongruence in LIFO accounting logic")
                from_lot_and_amount: Optional[FromLotAndAmount] = self.seek_from_lot(reversed(from_lot_list[: from_lot_index + 1]))
                if from_lot_and_amount:
                    return TaxableEventAndFromLot(
                        taxable_event=taxable_event,
                        from_lot=from_lot_and_amount.from_lot,
                        taxable_event_amount=new_taxable_event_amount,
                        from_lot_amount=from_lot_and_amount.amount,
                    )
            year -= 1

        raise FromLotsExhaustedException()

    def seek_from_lot(self, from_lot_iterator: Iterator[InTransaction]) -> Optional[FromLotAndAmount]:
        # This while loop make the algorithm's complexity O(nm), where n is the number of taxable events and m is
        # the number of from lots): for every taxable event, loop over the from lot list. There are non-trivial ways
        # of making this faster (by changing the data structures).
        try:
            while True:
                from_lot: InTransaction = next(from_lot_iterator)
                from_lot_amount: RP2Decimal
                if self._has_partial_amount(from_lot):
                    if self._get_partial_amount(from_lot) > ZERO:
                        from_lot_amount = self._get_partial_amount(from_lot)
                        self._clear_partial_amount(from_lot)
                        return FromLotAndAmount(
                            from_lot=from_lot,
                            amount=from_lot_amount,
                        )
                else:
                    from_lot_amount = from_lot.crypto_in
                    self._clear_partial_amount(from_lot)
                    return FromLotAndAmount(
                        from_lot=from_lot,
                        amount=from_lot_amount,
                    )
        except StopIteration:
            # End of from_lots
            pass

        return None

    def _has_partial_amount(self, from_lot: InTransaction) -> bool:
        return from_lot in self.__from_lot_2_partial_amount

    def _get_partial_amount(self, from_lot: InTransaction) -> RP2Decimal:
        if not self._has_partial_amount(from_lot):
            raise Exception(f"Internal error: from lot has no partial amount: {from_lot}")
        return self.__from_lot_2_partial_amount[from_lot]

    def _clear_partial_amount(self, from_lot: InTransaction) -> None:
        self.__from_lot_2_partial_amount[from_lot] = ZERO

    def validate_from_lot_ancestor_timestamp(self, from_lot: InTransaction, from_lot_parent: InTransaction) -> bool:
        # In LIFO the from_lot chain can have non-monotonic timestamps, so no validation is possible. Returning True means the validation never fails.
        return True

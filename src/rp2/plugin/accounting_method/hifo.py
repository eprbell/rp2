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

from ctypes.wintypes import INT
from dataclasses import dataclass
from lib2to3.pgen2.token import OP
from re import A, S
from typing import Dict, Iterator, List, NamedTuple, Optional

from rp2.abstract_accounting_method import (
    AcquiredLotsExhaustedException,
    TaxableEventAndAcquiredLot,
    TaxableEventsExhaustedException,
)
from rp2.abstract_specific_id import AbstractSpecificId
from rp2.abstract_transaction import AbstractTransaction
from rp2.avl_tree import AVLTree
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal


@dataclass
class AcquiredLotAndIndex:
    acquired_lot: InTransaction
    index: int


class AcquiredLotAndAmount(NamedTuple):
    acquired_lot: InTransaction
    amount: RP2Decimal


# HIFO accounting method. See https://www.investopedia.com/terms/h/hifo.asp
class AccountingMethod(AbstractSpecificId):

    __taxable_event_iterator: Iterator[AbstractTransaction]
    __amount_2_acquired_lot_list: Dict[RP2Decimal, List[InTransaction]]
    __amount_2_acquired_lot_avl: Dict[RP2Decimal, AVLTree[str, AcquiredLotAndIndex]]
    __acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal]
    __min_acquired_lot_amount: int

    # Disambiguation is needed for transactions that have the same price, because the avl tree class expects unique keys: 12 decimal digits express
    # 1 quadrillion, which should be enough to capture the maximum number of same-price transactions in all reasonable cases.
    KEY_DISAMBIGUATOR_LENGTH: int = 12
    MAX_KEY_DISAMBIGUATOR = "9" * KEY_DISAMBIGUATOR_LENGTH

    # Iterators yield transactions in ascending chronological order
    def initialize(self, taxable_event_iterator: Iterator[AbstractTransaction], acquired_lot_iterator: Iterator[InTransaction]) -> None:
        self.__taxable_event_iterator = taxable_event_iterator
        self.__amount_2_acquired_lot_list = {}
        self.__amount_2_acquired_lot_avl = {}
        self.__acquired_lot_2_partial_amount = {}

        # Initialize data structures to hold acquired_lots in order by highest price (dictionary of acquired_lot lists, indexed by price)
        rounded_amount : int = 0
        self.__min_acquired_lot_amount = 0
        acquired_lot_list_amount : Dict[int,List[InTransaction]] = {}
        acquired_lot_avl_amount : Dict[int,AVLTree[str,AcquiredLotAndIndex]] = {}
        acquired_lot_list : List[InTransaction] = []
        acquired_lot_avl : AVLTree[str,AcquiredLotAndIndex] = AVLTree()
        index_dict: Dict = {}
        try:
            while True:
                acquired_lot : InTransaction = next(acquired_lot_iterator)
                rounded_amount = int(acquired_lot.spot_price)
                # Initialize minimum amount value
                if self.__min_acquired_lot_amount == 0 or self.__min_acquired_lot_amount>rounded_amount:
                    self.__min_acquired_lot_amount = rounded_amount
                if(rounded_amount not in index_dict.keys()):
                    index_dict[rounded_amount] = 0
                else:
                    index_dict[rounded_amount] += 1
                acquired_lot_list : List[InTransaction] = [acquired_lot]
                # Key is <amount>_<internal_id>
                acquired_lot_avl : AVLTree[str, AcquiredLotAndIndex] = AVLTree()
                acquired_lot_avl.insert_node(
                    f"{self._get_avl_node_key((acquired_lot.spot_price),acquired_lot.internal_id)}",AcquiredLotAndIndex(acquired_lot,index_dict[rounded_amount])
                )
                self._store_acquired_lots_for_price(rounded_amount,acquired_lot_list,acquired_lot_avl)
        except StopIteration:
            # End of acquired_lots
            pass
            
    # AVL tree node keys have this format: <spot_price>_<internal_id>. The internal_id part is needed to disambiguate transactions
    # that have the same spot_price. Internal_id is padded right in a string of fixed length (KEY_DISAMBIGUATOR_LENGTH).
    def _get_avl_node_key(self, spot_price: RP2Decimal, internal_id: str) -> str:
        return f"{spot_price}_{internal_id:0>{self.KEY_DISAMBIGUATOR_LENGTH}}"

    # This function calls _get_avl_node_key with internal_id=MAX_KEY_DISAMBIGUATOR, so that the generated key is larger than any other key
    # with the same timestamp.
    def _get_avl_node_key_with_max_disambiguator(self, spot_price: RP2Decimal) -> str:
        return self._get_avl_node_key(spot_price, self.MAX_KEY_DISAMBIGUATOR)

    def _store_acquired_lots_for_price(self,rounded_amount : int, acquired_lot_list : List[InTransaction], acquired_lot_avl: AVLTree[str,AcquiredLotAndIndex]) -> None:
        if rounded_amount in self.__amount_2_acquired_lot_list.keys():
            self.__amount_2_acquired_lot_list[rounded_amount].append(acquired_lot_list)
        else:
            self.__amount_2_acquired_lot_list[rounded_amount] = acquired_lot_list
        if rounded_amount in self.__amount_2_acquired_lot_avl.keys():
            self.__amount_2_acquired_lot_avl[rounded_amount].append(acquired_lot_avl)
        self.__amount_2_acquired_lot_avl[rounded_amount] = acquired_lot_avl

        # Acquired lots that have the same spot_price should all have the same acquired_lots list index (corresponding to the last element
        # with the same spot_price)
        previous_synchronous_acquired_lots: List[AcquiredLotAndIndex] = []
        for index, acquired_lot in enumerate(acquired_lot_list):
            if not previous_synchronous_acquired_lots or previous_synchronous_acquired_lots[0].acquired_lot.spot_price == acquired_lot.spot_price:
                previous_synchronous_acquired_lots.append(AcquiredLotAndIndex(acquired_lot, index))
            else:
                synchronous_index: int = previous_synchronous_acquired_lots[-1].index
                for previous_acquired_lot in previous_synchronous_acquired_lots:
                    previous_acquired_lot.index = synchronous_index
                previous_synchronous_acquired_lots = []

    def get_next_taxable_event_and_amount(
        self,
        taxable_event: Optional[AbstractTransaction],
        acquired_lot: Optional[InTransaction],
        taxable_event_amount: RP2Decimal,
        acquired_lot_amount: RP2Decimal,
    ) -> TaxableEventAndAcquiredLot:
        new_acquired_lot: Optional[InTransaction] = acquired_lot
        new_acquired_lot_amount: RP2Decimal = acquired_lot_amount - taxable_event_amount if acquired_lot is not None else ZERO
        try:
            new_taxable_event: AbstractTransaction = next(self.__taxable_event_iterator)
        except StopIteration:
            raise TaxableEventsExhaustedException() from None
        new_taxable_event_amount: RP2Decimal = new_taxable_event.crypto_balance_change

        # If the new taxable event has different spot_price than the acquired lot (and it's not earn-typed), also get a new acquired lot from the new spot_price
        if taxable_event and taxable_event.spot_price < new_taxable_event.spot_price:
            if acquired_lot:
                # Cache old-price acquired_lot amount
                self.__acquired_lot_2_partial_amount[acquired_lot] = new_acquired_lot_amount
            (_, new_acquired_lot, _, new_acquired_lot_amount) = self.get_acquired_lot_for_taxable_event(
                new_taxable_event, acquired_lot, new_taxable_event_amount, new_acquired_lot_amount
            )

        return TaxableEventAndAcquiredLot(
            taxable_event=new_taxable_event,
            acquired_lot=new_acquired_lot,
            taxable_event_amount=new_taxable_event_amount,
            acquired_lot_amount=new_acquired_lot_amount,
        )

    def get_acquired_lot_for_taxable_event(
        self, taxable_event: AbstractTransaction, acquired_lot: Optional[InTransaction], taxable_event_amount: RP2Decimal, acquired_lot_amount: RP2Decimal
    ) -> TaxableEventAndAcquiredLot:
        new_taxable_event_amount: RP2Decimal = taxable_event_amount - acquired_lot_amount
        rounded_amount : int = int(taxable_event.spot_price)
        while rounded_amount >= int(self.__min_acquired_lot_amount):
            if rounded_amount not in self.__amount_2_acquired_lot_list.keys():
                rounded_amount -= 1
                continue
            acquired_lot_list: List[InTransaction] = self.__amount_2_acquired_lot_list[rounded_amount]
            acquired_lot_avl: AVLTree[str, AcquiredLotAndIndex] = self.__amount_2_acquired_lot_avl[rounded_amount]
            first_lot: Optional[AcquiredLotAndIndex] = acquired_lot_avl.find_max_value_less_than(
                f"{self._get_avl_node_key_with_max_disambiguator(taxable_event.spot_price)}"
            )
            if first_lot is not None:
                acquired_lot_index: int = first_lot.index
                if first_lot.acquired_lot != acquired_lot_list[acquired_lot_index]:
                    raise Exception("Internal error: acquired_lot incongruence in HIFO accounting logic")
                acquired_lot_and_amount: Optional[AcquiredLotAndAmount] = self.seek_acquired_lot(reversed(acquired_lot_list[: acquired_lot_index + 1]))
                if acquired_lot_and_amount:
                    return TaxableEventAndAcquiredLot(
                        taxable_event=taxable_event,
                        acquired_lot=acquired_lot_and_amount.acquired_lot,
                        taxable_event_amount=new_taxable_event_amount,
                        acquired_lot_amount=acquired_lot_and_amount.amount,
                    )
            rounded_amount =- 1
        raise AcquiredLotsExhaustedException()

    def seek_acquired_lot(self,acquired_lot_iterator: Iterator[InTransaction]) -> Optional[AcquiredLotAndAmount]:
        # This while loop make the algorithm's complexity O(nm), where n is the number of taxable events and m is
        # the number of acquired lots): for every taxable event, loop over the acquired lot list. There are non-trivial ways
        # of making this faster (by changing the data structures).
        try:
            while True:
                acquired_lot: InTransaction = next(acquired_lot_iterator)
                acquired_lot_amount: RP2Decimal
                if self._has_partial_amount(acquired_lot):
                    if self._get_partial_amount(acquired_lot) > ZERO:
                        acquired_lot_amount = self._get_partial_amount(acquired_lot)
                        self._clear_partial_amount(acquired_lot)
                        return AcquiredLotAndAmount(acquired_lot=acquired_lot, amount=acquired_lot_amount,)
                else:
                    acquired_lot_amount = acquired_lot.crypto_in
                    self._clear_partial_amount(acquired_lot)
                    return AcquiredLotAndAmount(acquired_lot=acquired_lot, amount=acquired_lot_amount,)
        except StopIteration:
            # End of acquired_lots
            pass

        return None

    def _has_partial_amount(self, acquired_lot: InTransaction) -> bool:
        return acquired_lot in self.__acquired_lot_2_partial_amount

    def _get_partial_amount(self, acquired_lot: InTransaction) -> RP2Decimal:
        if not self._has_partial_amount(acquired_lot):
            raise Exception(f"Internal error: acquired lot has no partial amount: {acquired_lot}")
        return self.__acquired_lot_2_partial_amount[acquired_lot]

    def _clear_partial_amount(self, acquired_lot: InTransaction) -> None:
        self.__acquired_lot_2_partial_amount[acquired_lot] = ZERO

    def validate_acquired_lot_ancestor_timestamp(self, acquired_lot: InTransaction, acquired_lot_parent: InTransaction) -> bool:
        # In HIFO, aquired_lot doesn't depend on the timestamp.
        return True

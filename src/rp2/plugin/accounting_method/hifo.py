# Copyright 2022 ninideol
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
from typing import Dict, Iterator, List, NamedTuple, Optional

from rp2.abstract_accounting_method import (
    AcquiredLotsExhaustedException,
    TaxableEventAndAcquiredLot,
    TaxableEventsExhaustedException,
)
from rp2.abstract_specific_id import AbstractSpecificId
from rp2.abstract_transaction import AbstractTransaction
from rp2.avl_tree import AVLNode, AVLTree
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal


@dataclass
class AcquiredLotAndIndex:
    acquired_lot: InTransaction
    index: int


class AcquiredLotAndAmount(NamedTuple):
    acquired_lot: InTransaction
    amount: RP2Decimal


# HIFO plugin. See https://www.investopedia.com/terms/h/hifo.asp
class AccountingMethod(AbstractSpecificId):

    __taxable_event_iterator: Iterator[AbstractTransaction]
    __acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal]
    __acquired_lot_avl: AVLTree[str, AcquiredLotAndIndex]
    __spot_price_list: List[RP2Decimal]
    __acquired_lot_list: List[InTransaction]

    # Disambiguation is needed for transactions that have the same spot_price, because the avl tree class expects unique keys: 12 decimal digits express
    # 1 quadrillion, which should be enough to capture the maximum number of same-spot_price transactions in all reasonable cases.
    KEY_DISAMBIGUATOR_LENGTH: int = 12
    MAX_KEY_DISAMBIGUATOR = "9" * KEY_DISAMBIGUATOR_LENGTH
    MIN_KEY_DISAMBIGUATOR = "0" * KEY_DISAMBIGUATOR_LENGTH

    # Iterators yield transactions in ascending chronological order
    def initialize(self, taxable_event_iterator: Iterator[AbstractTransaction], acquired_lot_iterator: Iterator[InTransaction]) -> None:
        self.__taxable_event_iterator = taxable_event_iterator
        self.__acquired_lot_2_partial_amount = {}

        self.__spot_price_list = []
        self.__acquired_lot_list = []
        self.__acquired_lot_avl: AVLTree[str, AcquiredLotAndIndex] = AVLTree()

        index: int = 0
        try:
            while True:
                acquired_lot: InTransaction = next(acquired_lot_iterator)
                self.__acquired_lot_avl.insert_node(
                    f"{self._get_avl_node_key((acquired_lot.spot_price), str(index))}", AcquiredLotAndIndex(acquired_lot, index)
                )
                self.__spot_price_list.append(acquired_lot.spot_price)
                self.__acquired_lot_list.append(acquired_lot)
                index += 1
        except StopIteration:
            # End of acquired_lots
            pass
        self.__spot_price_list.sort()

    # AVL tree node keys have this format: <spot_price>_<node_id>. The node_id part is needed to disambiguate transactions
    # that have the same spot_price. node_id is padded right in a string of fixed length (KEY_DISAMBIGUATOR_LENGTH).
    # The highest node_id is for the earliest acquired lot
    def _get_avl_node_key(self, spot_price: RP2Decimal, node_id: str) -> str:
        return f"{spot_price}_{(int(self.MAX_KEY_DISAMBIGUATOR) - int(node_id)):0>{self.KEY_DISAMBIGUATOR_LENGTH}}"

    # This function calls _get_avl_node_key with node_id=MIN_KEY_DISAMBIGUATOR, so that the generated key is larger than any other key
    # with the same spot_price.
    def _get_avl_node_key_with_max_disambiguator(self, spot_price: RP2Decimal) -> str:
        return self._get_avl_node_key(spot_price, self.MIN_KEY_DISAMBIGUATOR)

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

        # If the new taxable event is newer than the old one (and it's not earn-typed) check if there
        # is a newer acquired lot that is higher price (but still older than the new taxable event)
        if taxable_event and taxable_event.timestamp < new_taxable_event.timestamp:
            if acquired_lot:
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

    # After selecting the taxable event, RP2 calls this function to find the acquired_lot to pair with it. This means that the taxable
    # event can be passed to this function (which is useful for certain accounting methods)
    def get_acquired_lot_for_taxable_event(
        self, taxable_event: AbstractTransaction, acquired_lot: Optional[InTransaction], taxable_event_amount: RP2Decimal, acquired_lot_amount: RP2Decimal
    ) -> TaxableEventAndAcquiredLot:
        # This while loop makes the algorithm's complexity O(n^2), where n is the number of acquired lots. Non-trivial
        # optimizations are possible using different data structures (and likely with some space/time tradeoff)
        new_taxable_event_amount: RP2Decimal = taxable_event_amount - acquired_lot_amount
        spot_price_index = len(self.__spot_price_list) - 1
        current_key: str = f"{self._get_avl_node_key_with_max_disambiguator(self.__spot_price_list[spot_price_index])}"
        while spot_price_index >= 0:
            acquired_lot_list: List[InTransaction] = self.__acquired_lot_list
            if not self.__acquired_lot_avl.root:
                raise Exception("AVL tree has no root node")
            node: Optional[AVLNode[str, AcquiredLotAndIndex]] = self.__acquired_lot_avl.find_max_node_less_than_at_node(
                self.__acquired_lot_avl.root,
                current_key,
            )
            acquired_lot_index: Optional[int] = None
            first_lot: Optional[AcquiredLotAndIndex] = node.value if node else None
            if first_lot is not None and first_lot.acquired_lot.timestamp <= taxable_event.timestamp:
                acquired_lot_index = first_lot.index
                if first_lot.acquired_lot != acquired_lot_list[acquired_lot_index]:
                    raise Exception("Internal error: acquired_lot incongruence in HIFO accounting logic")
                acquired_lot_and_amount: Optional[AcquiredLotAndAmount] = self.seek_acquired_lot(acquired_lot_list, acquired_lot_index)
                if acquired_lot_and_amount:
                    return TaxableEventAndAcquiredLot(
                        taxable_event=taxable_event,
                        acquired_lot=acquired_lot_and_amount.acquired_lot,
                        taxable_event_amount=new_taxable_event_amount,
                        acquired_lot_amount=acquired_lot_and_amount.amount,
                    )
            spot_price_index -= 1
            current_key = f"{self._get_avl_node_key_with_max_disambiguator(self.__spot_price_list[spot_price_index])}"
            if acquired_lot_index is not None and self.__spot_price_list[spot_price_index] == self.__spot_price_list[spot_price_index + 1]:
                current_key = f"{self._get_avl_node_key((self.__spot_price_list[spot_price_index]), str(acquired_lot_index + 1))}"
        raise AcquiredLotsExhaustedException()

    def seek_acquired_lot(self, acquired_lot_list: List[InTransaction], start: int) -> Optional[AcquiredLotAndAmount]:
        # This while loop make the algorithm's complexity O(nm), where n is the number of taxable events and m is
        # the number of acquired lots): for every taxable event, loop over the acquired lot list. There are non-trivial ways
        # of making this faster (by changing the data structures).
        for index in range(start, -1, -1):
            acquired_lot: InTransaction = acquired_lot_list[index]
            acquired_lot_amount: RP2Decimal
            if self._has_partial_amount(acquired_lot):
                if self._get_partial_amount(acquired_lot) > ZERO:
                    acquired_lot_amount = self._get_partial_amount(acquired_lot)
                    self._clear_partial_amount(acquired_lot)
                    return AcquiredLotAndAmount(acquired_lot=acquired_lot, amount=acquired_lot_amount)
            else:
                acquired_lot_amount = acquired_lot.crypto_in
                self._clear_partial_amount(acquired_lot)
                return AcquiredLotAndAmount(acquired_lot=acquired_lot, amount=acquired_lot_amount)

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
        # In HIFO the acquired_lot chain can have non-monotonic timestamps, so no validation is possible. Returning True means the validation never fails.
        return True

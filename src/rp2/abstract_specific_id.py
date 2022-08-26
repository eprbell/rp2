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

from prezzemolo.avl_tree import AVLTree

from rp2.abstract_accounting_method import (
    AbstractAccountingMethod,
    AcquiredLotsExhaustedException,
    TaxableEventAndAcquiredLot,
    TaxableEventsExhaustedException,
)
from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal


@dataclass
class AcquiredLotAndIndex:
    acquired_lot: InTransaction
    index: int


class AcquiredLotAndAmount(NamedTuple):
    acquired_lot: InTransaction
    amount: RP2Decimal


class AbstractSpecificId(AbstractAccountingMethod):
    __taxable_event_iterator: Iterator[AbstractTransaction]
    __acquired_lot_list: List[InTransaction]
    __acquired_lot_avl: AVLTree[str, AcquiredLotAndIndex]
    __acquired_lot_2_partial_amount: Dict[InTransaction, RP2Decimal]

    # Disambiguation is needed for transactions that have the same timestamp, because the avl tree class expects unique keys: 12 decimal digits express
    # 1 quadrillion, which should be enough to capture the maximum number of same-timestamp transactions in all reasonable cases.
    KEY_DISAMBIGUATOR_LENGTH: int = 12
    MAX_KEY_DISAMBIGUATOR = "9" * KEY_DISAMBIGUATOR_LENGTH

    # Iterators yield transactions in ascending chronological order
    def initialize(self, taxable_event_iterator: Iterator[AbstractTransaction], acquired_lot_iterator: Iterator[InTransaction]) -> None:
        self.__taxable_event_iterator = taxable_event_iterator
        self.__acquired_lot_list = []
        self.__acquired_lot_avl: AVLTree[str, AcquiredLotAndIndex] = AVLTree()
        self.__acquired_lot_2_partial_amount = {}

        index: int = 0
        try:
            while True:
                acquired_lot: InTransaction = next(acquired_lot_iterator)
                self.__acquired_lot_list.append(acquired_lot)
                # Key is <timestamp>_<internal_id>
                self.__acquired_lot_avl.insert_node(
                    f"{self._get_avl_node_key(acquired_lot.timestamp, acquired_lot.internal_id)}", AcquiredLotAndIndex(acquired_lot, index)
                )
                index += 1
        except StopIteration:
            # End of acquired_lots
            pass

    # AVL tree node keys have this format: <timestamp>_<internal_id>. The internal_id part is needed to disambiguate transactions
    # that have the same timestamp. Timestamp is in format "YYYYmmddHHMMSS.ffffff" and internal_id is padded right in a string of fixed
    # length (KEY_DISAMBIGUATOR_LENGTH).
    def _get_avl_node_key(self, timestamp: datetime, internal_id: str) -> str:
        return f"{timestamp.strftime('%Y%m%d%H%M%S.%f')}_{internal_id:0>{self.KEY_DISAMBIGUATOR_LENGTH}}"

    # This function calls _get_avl_node_key with internal_id=MAX_KEY_DISAMBIGUATOR, so that the generated key is larger than any other key
    # with the same timestamp.
    def _get_avl_node_key_with_max_disambiguator(self, timestamp: datetime) -> str:
        return self._get_avl_node_key(timestamp, self.MAX_KEY_DISAMBIGUATOR)

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
                self._set_partial_amount(acquired_lot, new_acquired_lot_amount)
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
        new_taxable_event_amount: RP2Decimal = taxable_event_amount - acquired_lot_amount
        if not self.__acquired_lot_avl.root:
            raise Exception("Internal error: AVL tree has no root node")
        avl_result: Optional[AcquiredLotAndIndex] = self.__acquired_lot_avl.find_max_value_less_than(
            self._get_avl_node_key_with_max_disambiguator(taxable_event.timestamp)
        )
        if avl_result is not None:
            if avl_result.acquired_lot != self.__acquired_lot_list[avl_result.index]:
                raise Exception(f"Internal error: acquired_lot incongruence in {self.name} accounting logic")
            acquired_lot_and_amount: Optional[AcquiredLotAndAmount] = self._seek_non_exhausted_acquired_lot_before_index(
                self.__acquired_lot_list, avl_result.index
            )
            if acquired_lot_and_amount:
                return TaxableEventAndAcquiredLot(
                    taxable_event=taxable_event,
                    acquired_lot=acquired_lot_and_amount.acquired_lot,
                    taxable_event_amount=new_taxable_event_amount,
                    acquired_lot_amount=acquired_lot_and_amount.amount,
                )

        raise AcquiredLotsExhaustedException()

    def _has_partial_amount(self, acquired_lot: InTransaction) -> bool:
        return acquired_lot in self.__acquired_lot_2_partial_amount

    def _get_partial_amount(self, acquired_lot: InTransaction) -> RP2Decimal:
        if not self._has_partial_amount(acquired_lot):
            raise Exception(f"Internal error: acquired lot has no partial amount: {acquired_lot}")
        return self.__acquired_lot_2_partial_amount[acquired_lot]

    def _set_partial_amount(self, acquired_lot: InTransaction, amount: RP2Decimal) -> None:
        self.__acquired_lot_2_partial_amount[acquired_lot] = amount

    def _clear_partial_amount(self, acquired_lot: InTransaction) -> None:
        self.__acquired_lot_2_partial_amount[acquired_lot] = ZERO

    def _seek_non_exhausted_acquired_lot_before_index(self, acquired_lot_list: List[InTransaction], last_valid_index: int) -> Optional[AcquiredLotAndAmount]:
        raise NotImplementedError("Abstract function")

    def validate_acquired_lot_ancestor_timestamp(self, acquired_lot: InTransaction, acquired_lot_parent: InTransaction) -> bool:
        raise NotImplementedError("Abstract function")

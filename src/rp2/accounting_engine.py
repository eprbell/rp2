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
from typing import Dict, Iterator, List, NamedTuple, Optional

from prezzemolo.avl_tree import AVLTree

from rp2.abstract_accounting_method import (
    AbstractAccountingMethod,
    AcquiredLotAndAmount,
    AcquiredLotCandidates,
)
from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2TypeError


class TaxableEventAndAcquiredLot(NamedTuple):
    taxable_event: AbstractTransaction
    acquired_lot: Optional[InTransaction]
    taxable_event_amount: RP2Decimal
    acquired_lot_amount: RP2Decimal


@dataclass(frozen=True, eq=True)
class _AcquiredLotAndIndex:
    acquired_lot: InTransaction
    index: int


class _LotExhaustedException(Exception):
    def __init__(self, message: str = "") -> None:
        self.__message = message
        super().__init__(self.__message)

    def __repr__(self) -> str:
        return self.message

    @property
    def message(self) -> str:
        return self.__message


class TaxableEventsExhaustedException(_LotExhaustedException):
    pass


class AcquiredLotsExhaustedException(_LotExhaustedException):
    pass


class AccountingEngine:

    __taxable_event_iterator: Iterator[AbstractTransaction]
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

    def __init__(self, years_2_methods: AVLTree[int, AbstractAccountingMethod]) -> None:
        self.__years_2_methods: AVLTree[int, AbstractAccountingMethod] = years_2_methods
        if not self.__years_2_methods:
            raise RP2RuntimeError("Internal error: no accounting method defined")

    # Iterators yield transactions in ascending chronological order
    def initialize(
        self,
        taxable_event_iterator: Iterator[AbstractTransaction],
        acquired_lot_iterator: Iterator[InTransaction],
    ) -> None:
        self.__taxable_event_iterator = taxable_event_iterator
        self.__acquired_lot_list = []
        self.__acquired_lot_avl: AVLTree[str, _AcquiredLotAndIndex] = AVLTree()
        self.__acquired_lot_2_partial_amount = {}

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

    # AVL tree node keys have this format: <timestamp>_<internal_id>. The internal_id part is needed to disambiguate transactions
    # that have the same timestamp. Timestamp is in format "YYYYmmddHHMMSS.ffffff" and internal_id is padded right in a string of fixed
    # length (KEY_DISAMBIGUATOR_LENGTH).
    def _get_avl_node_key(self, timestamp: datetime, internal_id: str) -> str:
        return f"{timestamp.astimezone(timezone.utc).strftime('%Y%m%d%H%M%S.%f')}_{internal_id:0>{self.KEY_DISAMBIGUATOR_LENGTH}}"

    # This function calls _get_avl_node_key with internal_id=MAX_KEY_DISAMBIGUATOR, so that the generated key is larger than any other key
    # with the same timestamp.
    def _get_avl_node_key_with_max_disambiguator(self, timestamp: datetime) -> str:
        return self._get_avl_node_key(timestamp, self.MAX_KEY_DISAMBIGUATOR)

    @property
    def years_2_methods(self) -> AVLTree[int, AbstractAccountingMethod]:
        return self.__years_2_methods

    def _get_accounting_method(self, year: int) -> AbstractAccountingMethod:
        method = self.__years_2_methods.find_max_value_less_than(year)
        if method is None:
            raise RP2RuntimeError(f"Internal error: no accounting method assigned for year {year}")
        if not isinstance(method, AbstractAccountingMethod):
            raise RP2RuntimeError(f"Internal error: accounting method assigned for year {year} is not of type AbstractAccountingMethod: {method}")
        return method

    def _set_partial_amount(self, acquired_lot: InTransaction, amount: RP2Decimal) -> None:
        self.__acquired_lot_2_partial_amount[acquired_lot] = amount

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

        # If the new taxable event is newer than the old one (and it's not earn-typed) check if there is a newer acquired lot that
        # meets the accounting method criteria (but it's still older than the new taxable event)
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
        self,
        taxable_event: AbstractTransaction,
        acquired_lot: Optional[InTransaction],  # pylint: disable=unused-argument
        taxable_event_amount: RP2Decimal,
        acquired_lot_amount: RP2Decimal,
    ) -> TaxableEventAndAcquiredLot:
        new_taxable_event_amount: RP2Decimal = taxable_event_amount - acquired_lot_amount
        avl_result: Optional[_AcquiredLotAndIndex] = self.__acquired_lot_avl.find_max_value_less_than(
            self._get_avl_node_key_with_max_disambiguator(taxable_event.timestamp)
        )
        if avl_result is not None:
            if avl_result.acquired_lot != self.__acquired_lot_list[avl_result.index]:
                raise RP2RuntimeError("Internal error: acquired_lot incongruence in accounting logic")
            method = self._get_accounting_method(taxable_event.timestamp.year)
            lot_candidates: AcquiredLotCandidates = AcquiredLotCandidates(
                method, self.__acquired_lot_list, self.__acquired_lot_2_partial_amount, avl_result.index
            )
            acquired_lot_and_amount: Optional[AcquiredLotAndAmount] = method.seek_non_exhausted_acquired_lot(
                lot_candidates, taxable_event, new_taxable_event_amount
            )
            if acquired_lot_and_amount:
                return TaxableEventAndAcquiredLot(
                    taxable_event=taxable_event,
                    acquired_lot=acquired_lot_and_amount.acquired_lot,
                    taxable_event_amount=new_taxable_event_amount,
                    acquired_lot_amount=acquired_lot_and_amount.amount,
                )

        raise AcquiredLotsExhaustedException()

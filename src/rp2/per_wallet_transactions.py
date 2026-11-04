# Copyright 2024 eprbell
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

from datetime import date
from types import MappingProxyType
from typing import Dict, List, Mapping, NamedTuple, Optional, Sequence, Tuple

from rp2.abstract_accounting_method import (
    AbstractFeatureBasedAccountingMethod,
    AcquiredLotAndAmount,
    FeatureBasedAcquiredLotCandidates,
)
from rp2.configuration import MAX_DATE, MIN_DATE, Configuration
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2TypeError, RP2ValueError
from rp2.transaction_set import TransactionSet


# A piece of an acquired lot consumed by a disposal or transfer.
class LotPiece(NamedTuple):
    acquired_lot: InTransaction
    amount: RP2Decimal


# Result of taking funds from a wallet: missing_amount is > 0 if the wallet didn't have enough funds.
class TakeResult(NamedTuple):
    pieces: List[LotPiece]
    missing_amount: RP2Decimal


# The lots and transactions of a single wallet during transfer analysis (see TransferAnalyzer).
# - The "actual amount" of a lot is how many of its units are still in this wallet. Lots that have never been touched have no entry in
#   the actual amounts: their actual amount is their whole crypto_in.
# - Lots are selected with the accounting methods' heaps (one heap per method, see FeatureBasedAcquiredLotCandidates). Heaps use lazy
#   deletion: a lot whose actual amount drops to zero stays in the heap and is skipped when popped. A lot whose units come back (e.g. at the
#   end of a round trip A->B->A) must be pushed again: that's what restore_actual_amount() is for.
# - Each method is identified by its name (e.g. "fifo"), not by the method object: two objects of the same method select the same lots.
# - The object owns its collections: they change only through its methods (add_acquired_lot(), add_out_transaction(),
#   add_intra_transaction(), take(), restore_actual_amount()), and it returns copies or read-only views of them (to_input_data() is a
#   snapshot of the wallet).
class PerWalletTransactions:
    def __init__(
        self,
        configuration: Configuration,
        asset: str,
        accounting_methods: Sequence[AbstractFeatureBasedAccountingMethod],
        from_date: date = MIN_DATE,
        to_date: date = MAX_DATE,
    ):
        self.__configuration = Configuration.type_check("configuration", configuration)
        self.__asset = configuration.type_check_asset("asset", asset)
        if not isinstance(from_date, date) or not isinstance(to_date, date):
            raise RP2TypeError(f"Parameters 'from_date' and 'to_date' must be dates: {from_date}, {to_date}")
        self.__from_date = from_date
        self.__to_date = to_date
        self.__acquired_lot_2_actual_amount: Dict[InTransaction, RP2Decimal] = {}
        self.__acquired_lot_list: List[InTransaction] = []
        # One set of lot candidates per accounting method: they share the lot list and the actual amounts, so that the accounting method can
        # change year over year.
        self.__method_name_2_lot_candidates: Dict[str, FeatureBasedAcquiredLotCandidates] = {}
        for accounting_method in accounting_methods:
            if not isinstance(accounting_method, AbstractFeatureBasedAccountingMethod):
                raise RP2TypeError(f"Parameter 'accounting_methods' contains a method that is not feature-based: {accounting_method}")
            if accounting_method.name in self.__method_name_2_lot_candidates:
                raise RP2ValueError(f"Parameter 'accounting_methods' contains two methods named {accounting_method.name}")
            self.__method_name_2_lot_candidates[accounting_method.name] = accounting_method.create_lot_candidates(
                self.__acquired_lot_list, self.__acquired_lot_2_actual_amount
            )
        if not self.__method_name_2_lot_candidates:
            raise RP2ValueError("Parameter 'accounting_methods' is empty")
        self.__out_transactions: List[OutTransaction] = []
        self.__intra_transactions: List[IntraTransaction] = []

    @property
    def asset(self) -> str:
        return self.__asset

    # Read-only view of the actual amounts of the lots that have been touched (see the class comment).
    @property
    def acquired_lot_2_actual_amount(self) -> Mapping[InTransaction, RP2Decimal]:
        return MappingProxyType(self.__acquired_lot_2_actual_amount)

    # The lots that arrived in this wallet, in order of arrival (a copy).
    @property
    def acquired_lot_list(self) -> Tuple[InTransaction, ...]:
        return tuple(self.__acquired_lot_list)

    def add_acquired_lot(self, acquired_lot: InTransaction) -> None:
        InTransaction.type_check("acquired_lot", acquired_lot)
        self.__acquired_lot_list.append(acquired_lot)
        self.__push_to_heaps(acquired_lot)

    def add_out_transaction(self, transaction: OutTransaction) -> None:
        if not isinstance(transaction, OutTransaction) or transaction.asset != self.__asset:
            raise RP2TypeError(f"Parameter 'transaction' is not an OutTransaction of {self.__asset}: {transaction}")
        self.__out_transactions.append(transaction)

    # Transfers are recorded in the wallet they leave from.
    def add_intra_transaction(self, transaction: IntraTransaction) -> None:
        if not isinstance(transaction, IntraTransaction) or transaction.asset != self.__asset:
            raise RP2TypeError(f"Parameter 'transaction' is not an IntraTransaction of {self.__asset}: {transaction}")
        self.__intra_transactions.append(transaction)

    def get_actual_amount(self, acquired_lot: InTransaction) -> RP2Decimal:
        return self.__acquired_lot_2_actual_amount.get(acquired_lot, acquired_lot.crypto_in)

    # Sets the actual amount of a lot whose units come back to this wallet: the lot may have been exhausted (and dropped from the heaps).
    def restore_actual_amount(self, acquired_lot: InTransaction, amount: RP2Decimal) -> None:
        self.__set_actual_amount(acquired_lot, amount)
        self.__push_to_heaps(acquired_lot)

    # Removes amount from the wallet, lot by lot, in the order given by accounting_method, and returns the lot pieces taken. If the wallet
    # doesn't hold enough funds, missing_amount in the result is the part that couldn't be taken (the caller raises an error).
    def take(self, accounting_method: AbstractFeatureBasedAccountingMethod, amount: RP2Decimal) -> TakeResult:
        lot_candidates = self.__get_lot_candidates(accounting_method)
        result: List[LotPiece] = []
        amount_left = amount
        while amount_left > ZERO:
            lot_and_amount: Optional[AcquiredLotAndAmount] = accounting_method.seek_non_exhausted_acquired_lot(lot_candidates, amount_left)
            if lot_and_amount is None:
                return TakeResult(result, amount_left)
            piece_amount = min(lot_and_amount.amount, amount_left)
            # seek_non_exhausted_acquired_lot() zeroes the lot's actual amount: set it to what's left after taking the piece.
            self.__set_actual_amount(lot_and_amount.acquired_lot, lot_and_amount.amount - piece_amount)
            result.append(LotPiece(lot_and_amount.acquired_lot, piece_amount))
            amount_left -= piece_amount
        return TakeResult(result, ZERO)

    # The wallet as input data: its lots (including the artificial ones of transfers and of the opening allocation), disposals, outgoing
    # transfers and the actual amounts of its lots. It's a snapshot: new transaction sets and a copy of the amounts, which don't change if
    # this object does.
    def to_input_data(self) -> InputData:
        in_transaction_set = TransactionSet(self.__configuration, "IN", self.__asset, self.__from_date, self.__to_date)
        for acquired_lot in self.__acquired_lot_list:
            in_transaction_set.add_entry(acquired_lot)
        out_transaction_set = TransactionSet(self.__configuration, "OUT", self.__asset, self.__from_date, self.__to_date)
        for out_transaction in self.__out_transactions:
            out_transaction_set.add_entry(out_transaction)
        intra_transaction_set = TransactionSet(self.__configuration, "INTRA", self.__asset, self.__from_date, self.__to_date)
        for intra_transaction in self.__intra_transactions:
            intra_transaction_set.add_entry(intra_transaction)
        return InputData(
            self.__asset,
            in_transaction_set,
            out_transaction_set,
            intra_transaction_set,
            in_transaction_2_actual_amount=self.__acquired_lot_2_actual_amount,
            from_date=self.__from_date,
            to_date=self.__to_date,
        )

    # The lot candidates of the method with the same name as accounting_method. It must be a method of the same class as the one given to the
    # constructor: e.g. per-wallet FIFO (AcquisitionDateFifo) and the FIFO plugin are both named "fifo", but they order lots differently.
    def __get_lot_candidates(self, accounting_method: AbstractFeatureBasedAccountingMethod) -> FeatureBasedAcquiredLotCandidates:
        lot_candidates = self.__method_name_2_lot_candidates.get(accounting_method.name)
        if lot_candidates is None or type(lot_candidates.accounting_method) is not type(accounting_method):
            raise RP2RuntimeError(f"Internal error: accounting method {accounting_method} was not given to PerWalletTransactions of {self.__asset}")
        return lot_candidates

    def __set_actual_amount(self, acquired_lot: InTransaction, amount: RP2Decimal) -> None:
        if amount < ZERO:
            raise RP2RuntimeError(f"Internal error: negative actual amount {amount} for {acquired_lot}")
        self.__acquired_lot_2_actual_amount[acquired_lot] = amount

    def __push_to_heaps(self, acquired_lot: InTransaction) -> None:
        for lot_candidates in self.__method_name_2_lot_candidates.values():
            accounting_method = lot_candidates.accounting_method
            if not isinstance(accounting_method, AbstractFeatureBasedAccountingMethod):
                raise RP2RuntimeError(f"Internal error: lot candidates with a method that is not feature-based: {accounting_method}")
            accounting_method.add_selected_lot_to_heap(lot_candidates.acquired_lot_heap, acquired_lot)

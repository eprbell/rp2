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

from datetime import date, datetime
from typing import Dict, List, NamedTuple, Optional, Tuple

from prezzemolo.avl_tree import AVLTree

from rp2.abstract_accounting_method import (
    AbstractAccountingMethod,
    AbstractChronologicalAccountingMethod,
    AbstractFeatureBasedAccountingMethod,
    AcquiredLotAndAmount,
    AcquiredLotCandidatesOrder,
    FeatureBasedAcquiredLotCandidates,
)
from rp2.abstract_transaction import AbstractTransaction
from rp2.account import Account
from rp2.acquisition_date_fifo import AcquisitionDateFifo
from rp2.configuration import MAX_DATE, MIN_DATE, Configuration
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2TypeError, RP2ValueError
from rp2.transaction_set import TransactionSet
from rp2.wallet_lot import WalletLot

# Transactions with the same timestamp are processed in this order (then by row): funds that arrive at a given instant (acquisitions
# and transfers) are available to disposals that occur at the same instant.
_TRANSACTION_CLASS_2_RANK: Dict[type, int] = {InTransaction: 0, IntraTransaction: 1, OutTransaction: 2}


def _get_year(year_and_method: Tuple[int, AbstractAccountingMethod]) -> int:
    return year_and_method[0]


def _transaction_processing_order(transaction: AbstractTransaction) -> Tuple[float, int, int]:
    return (transaction.timestamp.timestamp(), _TRANSACTION_CLASS_2_RANK[type(transaction)], transaction.row)


# A piece of an acquired lot consumed by a disposal or transfer.
class _LotPiece(NamedTuple):
    acquired_lot: InTransaction
    amount: RP2Decimal


# Result of taking funds from a wallet: missing_amount is > 0 if the wallet didn't have enough funds.
class _TakeResult(NamedTuple):
    pieces: List[_LotPiece]
    missing_amount: RP2Decimal


class TransferAnalysisResult(NamedTuple):
    wallet_2_input_data: Dict[Account, InputData]
    # Gain/loss pairings of all taxable events, computed per wallet.
    gain_loss_list: List[GainLoss]
    # What each wallet holds at the end of the holdings date passed to analyze_and_pair() (by default, after all transactions).
    wallet_lots: List[WalletLot]


# The lots and transactions of a single wallet during transfer analysis.
# - The "actual amount" of a lot is how many of its units are still in this wallet. Lots that have never been touched have no entry in
#   acquired_lot_2_actual_amount: their actual amount is their whole crypto_in.
# - Lots are selected with the accounting methods' heaps (one heap per method, see FeatureBasedAcquiredLotCandidates). Heaps use lazy
#   deletion: a lot whose actual amount drops to zero stays in the heap and is skipped when popped. A lot whose units come back (e.g. at the
#   end of a round trip A->B->A) must be pushed again: that's what restore_actual_amount() is for.
class PerWalletTransactions:
    def __init__(
        self,
        configuration: Configuration,
        asset: str,
        accounting_methods: List[AbstractFeatureBasedAccountingMethod],
        from_date: date,
        to_date: date,
    ):
        self.__asset = asset
        self.__acquired_lot_2_actual_amount: Dict[InTransaction, RP2Decimal] = {}
        self.__acquired_lot_list: List[InTransaction] = []
        # One set of lot candidates per accounting method: they share the lot list and the actual amounts, so that the accounting method can
        # change year over year.
        self.__method_2_lot_candidates: Dict[AbstractFeatureBasedAccountingMethod, FeatureBasedAcquiredLotCandidates] = {
            method: method.create_lot_candidates(self.__acquired_lot_list, self.__acquired_lot_2_actual_amount) for method in accounting_methods
        }
        self.__out_transactions: TransactionSet = TransactionSet(configuration, "OUT", asset, from_date, to_date)
        self.__intra_transactions: TransactionSet = TransactionSet(configuration, "INTRA", asset, from_date, to_date)

    @property
    def asset(self) -> str:
        return self.__asset

    @property
    def acquired_lot_2_actual_amount(self) -> Dict[InTransaction, RP2Decimal]:
        return self.__acquired_lot_2_actual_amount

    @property
    def acquired_lot_list(self) -> List[InTransaction]:
        return self.__acquired_lot_list

    @property
    def out_transactions(self) -> TransactionSet:
        return self.__out_transactions

    @property
    def intra_transactions(self) -> TransactionSet:
        return self.__intra_transactions

    def add_acquired_lot(self, acquired_lot: InTransaction) -> None:
        self.__acquired_lot_list.append(acquired_lot)
        self.__push_to_heaps(acquired_lot)

    def get_actual_amount(self, acquired_lot: InTransaction) -> RP2Decimal:
        return self.__acquired_lot_2_actual_amount.get(acquired_lot, acquired_lot.crypto_in)

    def set_actual_amount(self, acquired_lot: InTransaction, amount: RP2Decimal) -> None:
        if amount < ZERO:
            raise RP2RuntimeError(f"Internal error: negative actual amount {amount} for {acquired_lot}")
        self.__acquired_lot_2_actual_amount[acquired_lot] = amount

    # Sets the actual amount of a lot whose units come back to this wallet: the lot may have been exhausted (and dropped from the heaps).
    def restore_actual_amount(self, acquired_lot: InTransaction, amount: RP2Decimal) -> None:
        self.set_actual_amount(acquired_lot, amount)
        self.__push_to_heaps(acquired_lot)

    # Removes amount from the wallet, lot by lot, in the order given by accounting_method, and returns the lot pieces taken. If the wallet
    # doesn't hold enough funds, missing_amount in the result is the part that couldn't be taken (the caller raises an error).
    def take(self, accounting_method: AbstractFeatureBasedAccountingMethod, amount: RP2Decimal) -> _TakeResult:
        lot_candidates = self.__method_2_lot_candidates[accounting_method]
        result: List[_LotPiece] = []
        amount_left = amount
        while amount_left > ZERO:
            lot_and_amount: Optional[AcquiredLotAndAmount] = accounting_method.seek_non_exhausted_acquired_lot(lot_candidates, amount_left)
            if lot_and_amount is None:
                return _TakeResult(result, amount_left)
            piece_amount = min(lot_and_amount.amount, amount_left)
            # seek_non_exhausted_acquired_lot() zeroes the lot's actual amount: set it to what's left after taking the piece.
            self.set_actual_amount(lot_and_amount.acquired_lot, lot_and_amount.amount - piece_amount)
            result.append(_LotPiece(lot_and_amount.acquired_lot, piece_amount))
            amount_left -= piece_amount
        return _TakeResult(result, ZERO)

    def __push_to_heaps(self, acquired_lot: InTransaction) -> None:
        for method, lot_candidates in self.__method_2_lot_candidates.items():
            method.add_selected_lot_to_heap(lot_candidates.acquired_lot_heap, acquired_lot)


# TransferAnalyzer processes all transactions of an asset chronologically, tracking which lots are in which wallet (per-wallet application):
# - InTransactions add a lot to their wallet;
# - OutTransactions dispose of lots in their wallet;
# - IntraTransactions move lots (or parts of lots) from one wallet to another: the "to" side is modeled with artificial InTransactions
#   that point back to the original lot (from_lot) and preserve its cost basis and acquisition date. The crypto fee (sent - received) is
#   paid with the first units selected and is disposed of: IRS FAQ A81 and A97 (digital-asset FAQs) state that the crypto used to pay for a
#   transfer between the taxpayer's own wallets is disposed of, with gain or loss, and A53 that it is not a transaction cost that could be
#   added to the basis of the received units.
# Lots are selected with the accounting method of the year in which the transaction occurs (the same method is used for transfers and
# disposals, so transfer semantics and accounting method are always consistent within a year). While doing so, the analyzer pairs every
# taxable event with the lots it consumed and produces the resulting GainLoss objects.
# For details see https://github.com/eprbell/rp2/wiki/Adding-Per%E2%80%90Wallet-Application-to-RP2.
class TransferAnalyzer:
    def __init__(
        self,
        configuration: Configuration,
        transfer_semantics: AbstractAccountingMethod,
        universal_input_data: InputData,
        skip_transfer_pointers: bool = False,
        use_local_artificial_ids: bool = False,
        years_2_accounting_methods: Optional[AVLTree[int, AbstractAccountingMethod]] = None,
    ):
        self.__configuration = Configuration.type_check("configuration", configuration)
        if not isinstance(transfer_semantics, AbstractAccountingMethod):
            raise RP2TypeError(f"Parameter 'transfer_semantics' is not of type AbstractAccountingMethod: {transfer_semantics}")
        # transfer_semantics is the accounting method for every year, unless a per-year map (the same one used by AccountingEngine) is passed:
        # the tax engine passes the map, so that transfers and disposals use the same method in each year.
        if years_2_accounting_methods is None:
            years_2_accounting_methods = AVLTree()
            years_2_accounting_methods.insert_node(MIN_DATE.year, transfer_semantics)
        # Map each (user-facing) accounting method to its per-wallet equivalent (see get_per_wallet_accounting_method()).
        self.__years_2_accounting_methods: AVLTree[int, AbstractFeatureBasedAccountingMethod] = AVLTree()
        self.__accounting_methods: List[AbstractFeatureBasedAccountingMethod] = []
        method_name_2_per_wallet_method: Dict[str, AbstractFeatureBasedAccountingMethod] = {}
        for year, method in self._get_years_and_methods(years_2_accounting_methods):
            per_wallet_method = method_name_2_per_wallet_method.setdefault(method.name, self.get_per_wallet_accounting_method(method))
            self.__years_2_accounting_methods.insert_node(year, per_wallet_method)
            if per_wallet_method not in self.__accounting_methods:
                self.__accounting_methods.append(per_wallet_method)
        self.__universal_input_data = InputData.type_check("universal_input_data", universal_input_data)
        # skip_transfer_pointers is used in global allocation, where the artificial transactions are used only as guides
        # and are replaced by new ones decided by the allocation method.
        self.__skip_transfer_pointers = Configuration.type_check_bool("skip_transfer_pointers", skip_transfer_pointers)
        # use_local_artificial_ids is used in global allocation, to avoid increasing the artificial id counter when running
        # the local transfer analysis (which is a throwaway operation).
        self.__use_local_artificial_ids = Configuration.type_check_bool("use_local_artificial_ids", use_local_artificial_ids)
        self.__local_artificial_id_counter = -1

    # Returns the (year, method) pairs of the map, sorted by year (AVLTree has no iterator, so its nodes are visited explicitly).
    @staticmethod
    def _get_years_and_methods(years_2_accounting_methods: AVLTree[int, AbstractAccountingMethod]) -> List[Tuple[int, AbstractAccountingMethod]]:
        result: List[Tuple[int, AbstractAccountingMethod]] = []
        to_visit = [years_2_accounting_methods.root]
        while to_visit:
            node = to_visit.pop()
            if node is None:
                continue
            result.append((node.key, node.value))
            to_visit.extend([node.left, node.right])
        if not result:
            raise RP2ValueError("Parameter 'years_2_accounting_methods' is empty")
        return sorted(result, key=_get_year)

    # Chronological methods select lots by position in the lot list, which in a wallet is the arrival order, not the acquisition order:
    # replace them with feature-based equivalents that sort by cost_basis_timestamp. Also used by UnusedBasisAllocator to sort unused lots.
    @staticmethod
    def get_per_wallet_accounting_method(accounting_method: AbstractAccountingMethod) -> AbstractFeatureBasedAccountingMethod:
        if isinstance(accounting_method, AbstractFeatureBasedAccountingMethod):
            return accounting_method
        if isinstance(accounting_method, AbstractChronologicalAccountingMethod):
            if accounting_method.lot_candidates_order() == AcquiredLotCandidatesOrder.OLDER_TO_NEWER:
                return AcquisitionDateFifo()
            return AccountingMethodLIFO()
        raise RP2TypeError(f"Unsupported accounting method for per-wallet application: {accounting_method}")

    def _get_accounting_method(self, transaction: AbstractTransaction) -> AbstractFeatureBasedAccountingMethod:
        method = self.__years_2_accounting_methods.find_max_value_less_than(transaction.timestamp.year)
        if method is None:
            raise RP2RuntimeError(f"Internal error: no accounting method assigned for year {transaction.timestamp.year}")
        return method

    def _new_artificial_id(self) -> int:
        if self.__use_local_artificial_ids:
            result = self.__local_artificial_id_counter
            self.__local_artificial_id_counter -= 1
            return result
        return self.__configuration.get_new_artificial_id()

    # Creates an artificial InTransaction modeling the "to" side of an IntraTransaction. The artificial transaction carries the same per-unit
    # cost basis (including purchase fees) as from_in_transaction.
    # Its timestamp is the transfer's (when the funds become available in the destination wallet) and its cost_basis_timestamp is the
    # acquisition date of the original lot (which determines FIFO order and holding period).
    def _create_to_in_transaction(self, from_in_transaction: InTransaction, transfer_transaction: IntraTransaction, amount: RP2Decimal) -> InTransaction:
        artificial_id = self._new_artificial_id()

        fraction = amount / from_in_transaction.crypto_in
        fiat_fee = from_in_transaction.fiat_fee * fraction
        result = InTransaction(
            configuration=self.__configuration,
            timestamp=transfer_transaction.timestamp.isoformat(),
            asset=transfer_transaction.asset,
            exchange=transfer_transaction.to_exchange,
            holder=transfer_transaction.to_holder,
            transaction_type=from_in_transaction.transaction_type.value,
            spot_price=from_in_transaction.spot_price,
            crypto_in=amount,
            fiat_in_no_fee=from_in_transaction.fiat_in_no_fee * fraction,
            fiat_fee=fiat_fee if fiat_fee > ZERO else None,
            row=artificial_id,
            unique_id=f"{transfer_transaction.unique_id}/{artificial_id}",
            notes=(
                f"Artificial transaction modeling the reception of {amount} {transfer_transaction.asset} "
                f"from {transfer_transaction.from_exchange}/{transfer_transaction.from_holder} "
                f"to {transfer_transaction.to_exchange}/{transfer_transaction.to_holder} on {transfer_transaction.timestamp}."
            ),
            from_lot=from_in_transaction,
            cost_basis_timestamp=from_in_transaction.original_lot.timestamp.isoformat(),
        )

        if not self.__skip_transfer_pointers:
            # originates_from (used to detect round trips) only contains lots that wallets actually hold during this analysis: the lot the
            # units leave from, plus the wallets that lot's units were in before (its own originates_from). It doesn't follow from_lot: past
            # a lot created by the unused basis allocation, from_lot leads to an input lot bought before the switch, which is not held by
            # any wallet here. Returning units to it would count them twice.
            # Example: 10 units bought in 2024 are allocated to wallet A at the switch as lot X. Move 4 units A -> B (lot Y), then B -> A:
            # Y.originates_from is {A: X}, so the 4 units go back to X (6 + 4 = 10 units). Following from_lot instead would also reach the
            # 2024 purchase in A: its 10 units plus the 4 returned make 14 units out of 10.
            # When a wallet appears more than once, the most recent lot (the closest to this transfer) is the one that holds the units.
            from_account = Account(from_in_transaction.exchange, from_in_transaction.holder)
            result.originates_from[from_account] = from_in_transaction
            for account, lot in from_in_transaction.originates_from.items():
                result.originates_from.setdefault(account, lot)

            # to_lots records where the units went, for every lot they come from (including input lots bought before the switch).
            to_account = Account(transfer_transaction.to_exchange, transfer_transaction.to_holder)
            current_transaction: Optional[InTransaction] = from_in_transaction
            while current_transaction is not None:
                current_transaction.to_lots.setdefault(to_account, []).append(result)
                current_transaction = current_transaction.from_lot

        return result

    def _convert_per_wallet_transactions_to_input_data(self, universal_input_data: InputData, per_wallet_transactions: PerWalletTransactions) -> InputData:
        in_transaction_set = TransactionSet(
            self.__configuration, "IN", universal_input_data.asset, universal_input_data.from_date, universal_input_data.to_date
        )
        for in_transaction in per_wallet_transactions.acquired_lot_list:
            in_transaction_set.add_entry(in_transaction)

        result: InputData = InputData(
            universal_input_data.asset,
            in_transaction_set,
            per_wallet_transactions.out_transactions,
            per_wallet_transactions.intra_transactions,
            in_transaction_2_actual_amount=per_wallet_transactions.acquired_lot_2_actual_amount,
            from_date=universal_input_data.from_date,
            to_date=universal_input_data.to_date,
        )
        return result

    # True if the lot's units have already been in the transfer's destination wallet (i.e. the transfer closes a round trip).
    def _is_transaction_cycle(self, acquired_lot: InTransaction, transfer: IntraTransaction) -> bool:
        to_account = Account(transfer.to_exchange, transfer.to_holder)
        return to_account in acquired_lot.originates_from

    def _get_or_create_per_wallet_transactions(
        self, wallet_2_per_wallet_transactions: Dict[Account, PerWalletTransactions], account: Account
    ) -> PerWalletTransactions:
        if account not in wallet_2_per_wallet_transactions:
            wallet_2_per_wallet_transactions[account] = PerWalletTransactions(
                self.__configuration,
                self.__universal_input_data.asset,
                self.__accounting_methods,
                self.__universal_input_data.from_date,
                self.__universal_input_data.to_date,
            )
        return wallet_2_per_wallet_transactions[account]

    # Disposals and transfers can only come from a wallet that has received funds before.
    def _get_existing_per_wallet_transactions(
        self, wallet_2_per_wallet_transactions: Dict[Account, PerWalletTransactions], account: Account, transaction: AbstractTransaction
    ) -> PerWalletTransactions:
        if account not in wallet_2_per_wallet_transactions:
            raise RP2ValueError(f"Insufficient balance on {account}: no funds were ever received by this account before transaction: {transaction}")
        return wallet_2_per_wallet_transactions[account]

    # A disposal: its units (fee included) are taken from its own wallet and each lot piece becomes a GainLoss.
    def _process_out_transaction(
        self, wallet_2_per_wallet_transactions: Dict[Account, PerWalletTransactions], transaction: OutTransaction, gain_loss_list: List[GainLoss]
    ) -> None:
        account = Account(transaction.exchange, transaction.holder)
        per_wallet_transactions = self._get_existing_per_wallet_transactions(wallet_2_per_wallet_transactions, account, transaction)
        per_wallet_transactions.out_transactions.add_entry(transaction)
        pieces, missing_amount = per_wallet_transactions.take(self._get_accounting_method(transaction), transaction.crypto_balance_change)
        if missing_amount > ZERO:
            raise RP2ValueError(
                f"Insufficient balance on {account} to cover out transaction "
                f"(missing {missing_amount} of {transaction.crypto_balance_change} {transaction.asset}): {transaction}"
            )
        for piece in pieces:
            gain_loss_list.append(GainLoss(self.__configuration, piece.amount, transaction, piece.acquired_lot))

    # A transfer between wallets: the sent units are taken from the source wallet; the fee (sent - received) is paid with the first of them,
    # the rest arrive in the destination wallet.
    def _process_intra_transaction(
        self, wallet_2_per_wallet_transactions: Dict[Account, PerWalletTransactions], transaction: IntraTransaction, gain_loss_list: List[GainLoss]
    ) -> None:
        from_account = Account(transaction.from_exchange, transaction.from_holder)
        to_account = Account(transaction.to_exchange, transaction.to_holder)
        from_per_wallet_transactions = self._get_existing_per_wallet_transactions(wallet_2_per_wallet_transactions, from_account, transaction)
        # IntraTransactions are added to from_per_wallet_transactions.
        from_per_wallet_transactions.intra_transactions.add_entry(transaction)
        to_per_wallet_transactions = self._get_or_create_per_wallet_transactions(wallet_2_per_wallet_transactions, to_account)

        pieces, missing_amount = from_per_wallet_transactions.take(self._get_accounting_method(transaction), transaction.crypto_sent)
        if missing_amount > ZERO:
            raise RP2ValueError(
                f"Insufficient balance on {from_account} to send funds "
                f"(missing {missing_amount} of {transaction.crypto_sent} {transaction.asset}): {transaction}"
            )
        fee_pieces, received_pieces = self._split_fee_and_received_pieces(pieces, transaction.crypto_fee)
        # The fee is disposed of: each fee piece is paired with its lot.
        for piece in fee_pieces:
            gain_loss_list.append(GainLoss(self.__configuration, piece.amount, transaction, piece.acquired_lot))
        for piece in received_pieces:
            if transaction.is_self_transfer():
                # Self transfer (loop): the received units stay where they were.
                from_per_wallet_transactions.restore_actual_amount(
                    piece.acquired_lot, from_per_wallet_transactions.get_actual_amount(piece.acquired_lot) + piece.amount
                )
            else:
                self._deliver_received_piece(to_per_wallet_transactions, to_account, transaction, piece)

    # Splits the lot pieces taken for a transfer into fee pieces and received pieces. The fee is taken from the first pieces, like universal
    # application does (it disposes of the first units selected by the accounting method to pay the fee).
    @staticmethod
    def _split_fee_and_received_pieces(pieces: List[_LotPiece], fee: RP2Decimal) -> Tuple[List[_LotPiece], List[_LotPiece]]:
        fee_pieces: List[_LotPiece] = []
        received_pieces: List[_LotPiece] = []
        fee_amount_left = fee
        for piece in pieces:
            fee_part = min(piece.amount, fee_amount_left)
            fee_amount_left -= fee_part
            if fee_part > ZERO:
                fee_pieces.append(_LotPiece(piece.acquired_lot, fee_part))
            if piece.amount - fee_part > ZERO:
                received_pieces.append(_LotPiece(piece.acquired_lot, piece.amount - fee_part))
        return fee_pieces, received_pieces

    # Adds a received lot piece to the destination wallet: normally as a new artificial InTransaction; at the end of a round trip
    # (e.g. A->B->A) by returning the units to the lot they left from.
    def _deliver_received_piece(
        self,
        to_per_wallet_transactions: PerWalletTransactions,
        to_account: Account,
        transaction: IntraTransaction,
        piece: _LotPiece,
    ) -> None:
        if self._is_transaction_cycle(piece.acquired_lot, transaction):
            # Transaction cycle detected: the to_account has already been visited. Return the amount to the start-of-cycle lot (which has the
            # same per-unit basis and acquisition date, since transfers never change the basis of the units they move).
            start_of_cycle: InTransaction = piece.acquired_lot.originates_from[to_account]
            returned_amount = to_per_wallet_transactions.get_actual_amount(start_of_cycle) + piece.amount
            if returned_amount > start_of_cycle.crypto_in:
                raise RP2RuntimeError(
                    f"Internal error: start-of-cycle transaction's returned amount exceeds its crypto_in: {returned_amount} > "
                    f"{start_of_cycle.crypto_in}: {start_of_cycle}"
                )
            to_per_wallet_transactions.restore_actual_amount(start_of_cycle, returned_amount)
            return
        to_per_wallet_transactions.add_acquired_lot(self._create_to_in_transaction(piece.acquired_lot, transaction, piece.amount))

    # Performs transfer analysis on the universal InputData and returns one InputData per wallet.
    def analyze(self) -> Dict[Account, InputData]:
        return self.analyze_and_pair().wallet_2_input_data

    # Same as analyze(), but also returns the per-wallet gain/loss pairings of all taxable events and what each wallet holds at the end of
    # holdings_date. Transactions are processed in a single chronological pass (see _transaction_processing_order()), so every disposal or
    # transfer sees exactly the lots its wallet holds at that moment.
    # The holdings are recorded when the pass reaches the first transaction dated after holdings_date (in the transaction's own timezone,
    # like BalanceSet does), so that they match the balances at that date. Example: buy in January, sell in May, holdings_date in April:
    # the holdings include the January lot, untouched by the May sale.
    def analyze_and_pair(self, holdings_date: date = MAX_DATE) -> TransferAnalysisResult:
        # A datetime is also a date, but it can't be compared with the dates of the transactions.
        if not isinstance(holdings_date, date) or isinstance(holdings_date, datetime):
            raise RP2TypeError(f"Parameter 'holdings_date' is not of type date: {holdings_date}")
        all_transactions: List[AbstractTransaction] = []
        for transaction_set in [
            self.__universal_input_data.unfiltered_in_transaction_set,
            self.__universal_input_data.unfiltered_out_transaction_set,
            self.__universal_input_data.unfiltered_intra_transaction_set,
        ]:
            # The isinstance() check only narrows the type of the set's entries (always transactions).
            all_transactions.extend(transaction for transaction in transaction_set if isinstance(transaction, AbstractTransaction))
        all_transactions.sort(key=_transaction_processing_order)

        gain_loss_list: List[GainLoss] = []
        wallet_2_per_wallet_transactions: Dict[Account, PerWalletTransactions] = {}
        wallet_lots: Optional[List[WalletLot]] = None
        for transaction in all_transactions:
            if wallet_lots is None and transaction.timestamp.date() > holdings_date:
                wallet_lots = self._get_wallet_lots(wallet_2_per_wallet_transactions)
            if isinstance(transaction, InTransaction):
                account = Account(transaction.exchange, transaction.holder)
                self._get_or_create_per_wallet_transactions(wallet_2_per_wallet_transactions, account).add_acquired_lot(transaction)
                if transaction.is_earning():
                    gain_loss_list.append(GainLoss(self.__configuration, transaction.crypto_balance_change, transaction, None))
            elif isinstance(transaction, OutTransaction):
                self._process_out_transaction(wallet_2_per_wallet_transactions, transaction, gain_loss_list)
            elif isinstance(transaction, IntraTransaction):
                self._process_intra_transaction(wallet_2_per_wallet_transactions, transaction, gain_loss_list)
            else:
                raise RP2ValueError(f"Internal error: invalid transaction class: {transaction}")

        if wallet_lots is None:
            # No transaction is dated after holdings_date: the holdings are the final ones.
            wallet_lots = self._get_wallet_lots(wallet_2_per_wallet_transactions)

        # Convert per-wallet transactions to input_data.
        wallet_2_input_data: Dict[Account, InputData] = {
            wallet: self._convert_per_wallet_transactions_to_input_data(self.__universal_input_data, per_wallet_transactions)
            for wallet, per_wallet_transactions in wallet_2_per_wallet_transactions.items()
        }
        return TransferAnalysisResult(wallet_2_input_data, gain_loss_list, wallet_lots)

    # What each wallet holds right now: one WalletLot for every lot with units left in the wallet (sorted by wallet, then by lot order).
    @staticmethod
    def _get_wallet_lots(wallet_2_per_wallet_transactions: Dict[Account, PerWalletTransactions]) -> List[WalletLot]:
        result: List[WalletLot] = []
        for account in sorted(wallet_2_per_wallet_transactions):
            per_wallet_transactions = wallet_2_per_wallet_transactions[account]
            for lot in per_wallet_transactions.acquired_lot_list:
                amount = per_wallet_transactions.get_actual_amount(lot)
                if amount > ZERO:
                    result.append(WalletLot(account, lot, amount))
        return result

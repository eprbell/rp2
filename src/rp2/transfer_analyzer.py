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
from typing import Dict, List, Optional

from rp2.configuration import Configuration
from rp2.abstract_accounting_method import AbstractAccountingMethod, AbstractAcquiredLotCandidates, AcquiredLotAndAmount
from rp2.in_transaction import Account, InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2ValueError, RP2TypeError
from rp2.transaction_set import TransactionSet


# Utility class to store the transactions of a single wallet during transfer analysis and other per-wallet processing.
class PerWalletTransactions:
    def __init__(self, configuration: Configuration, asset: str, transfer_semantics: AbstractAccountingMethod, from_date: date, to_date: date):
        self.__asset = asset
        # Transfer semantics: method to decide which lot to pick when transferring funds.
        self.__transfer_semantics = transfer_semantics
        self.__acquired_lot_2_actual_amount: Dict[InTransaction, RP2Decimal] = {}
        acquired_lot_list: List[InTransaction] = []
        self.__in_transactions: AbstractAcquiredLotCandidates = transfer_semantics.create_lot_candidates(
            acquired_lot_list=acquired_lot_list, acquired_lot_2_partial_amount=self.__acquired_lot_2_actual_amount
        )
        self.__out_transactions: TransactionSet = TransactionSet(configuration, "OUT", asset, from_date, to_date)
        self.__intra_transactions: TransactionSet = TransactionSet(configuration, "INTRA", asset, from_date, to_date)

    @property
    def asset(self) -> str:
        return self.__asset

    @property
    def transfer_semantics(self) -> AbstractAccountingMethod:
        return self.__transfer_semantics

    @property
    def acquired_lot_2_actual_amount(self) -> Dict[InTransaction, RP2Decimal]:
        return self.__acquired_lot_2_actual_amount

    @property
    def in_transactions(self) -> AbstractAcquiredLotCandidates:
        return self.__in_transactions

    @property
    def out_transactions(self) -> TransactionSet:
        return self.__out_transactions

    @property
    def intra_transactions(self) -> TransactionSet:
        return self.__intra_transactions


class TransferAnalyzer:
    def __init__(
        self, configuration: Configuration, transfer_semantics: AbstractAccountingMethod, universal_input_data: InputData, skip_transfer_pointers: bool = False
    ):
        self.__configuration = Configuration.type_check("configuration", configuration)
        if not isinstance(transfer_semantics, AbstractAccountingMethod):
            raise RP2TypeError(f"Parameter 'transfer_semantics' is not of type AbstractAccountingMethod: {transfer_semantics}")
        self.__transfer_semantics = transfer_semantics
        self.__universal_input_data = InputData.type_check("universal_input_data", universal_input_data)
        # skip_transfer_pointers is used in universal allocation, where the artificial transactions are used only as guides and are replaced by new ones decided by the allocation method.
        self.__skip_transfer_pointers = Configuration.type_check_bool("skip_transfer_pointers", skip_transfer_pointers)
        # TODO: add run-time argument type checks.

    # Utility function to create an artificial InTransaction modeling the "to" side of an IntraTransaction
    def _create_to_in_transaction(self, from_in_transaction: InTransaction, transfer_transaction: IntraTransaction, amount: RP2Decimal) -> InTransaction:
        artificial_id = self.__configuration.get_new_artificial_id()

        # Find cost basis timestamp.
        current_from_in_transaction: Optional[InTransaction] = from_in_transaction
        cost_basis_timestamp_string = from_in_transaction.timestamp.isoformat()
        while True:
            current_from_in_transaction = current_from_in_transaction.from_lot if current_from_in_transaction is not None else None
            if current_from_in_transaction is None:
                break
            cost_basis_timestamp_string = current_from_in_transaction.timestamp.isoformat()

        result = InTransaction(
            configuration=self.__configuration,
            timestamp=transfer_transaction.timestamp.isoformat(),
            asset=transfer_transaction.asset,
            exchange=transfer_transaction.to_exchange,
            holder=transfer_transaction.to_holder,
            transaction_type=from_in_transaction.transaction_type.value,
            crypto_in=amount,
            spot_price=from_in_transaction.spot_price,
            # TODO: crypto_fee should be split proportionally to the crypto_in.
            crypto_fee=ZERO,
            # TODO: initialize fiat fields...
            row=artificial_id,
            unique_id=f"{transfer_transaction.unique_id}/{artificial_id}",
            notes=(
                f"Artificial transaction modeling the reception of {amount} {transfer_transaction.asset} "
                f"from {transfer_transaction.from_exchange}/{transfer_transaction.from_holder} "
                f"to {transfer_transaction.to_exchange}/{transfer_transaction.to_holder} on {transfer_transaction.timestamp}."
            ),
            from_lot=from_in_transaction,
            cost_basis_timestamp=cost_basis_timestamp_string,
        )

        if not self.__skip_transfer_pointers:
            # Update the originates_from field of the artificial transaction and the to_lots field of all its ancestors.
            current_transaction: Optional[InTransaction] = result
            to_account = Account(transfer_transaction.to_exchange, transfer_transaction.to_holder)
            while True:
                current_transaction = current_transaction.from_lot if current_transaction is not None else None
                if current_transaction is None:
                    break
                current_account = Account(current_transaction.exchange, current_transaction.holder)
                result.originates_from[current_account] = current_transaction
                to_lots = current_transaction.to_lots.setdefault(to_account, [])
                to_lots.append(result)

        return result

    def _convert_per_wallet_transactions_to_input_data(self, universal_input_data: InputData, per_wallet_transactions: PerWalletTransactions) -> InputData:
        in_transaction_set = TransactionSet(
            self.__configuration, "IN", universal_input_data.asset, universal_input_data.from_date, universal_input_data.to_date
        )
        for in_transaction in per_wallet_transactions.in_transactions.acquired_lot_list:
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

    def _is_transaction_cycle(self, acquired_lot: InTransaction, transfer: IntraTransaction) -> bool:
        to_account = Account(transfer.to_exchange, transfer.to_holder)
        return to_account in acquired_lot.originates_from

    # _process_remaining_transfer_amount processes the remaining amount of a transfer (that has not yet been assigned to in lots by transfer analysis):
    # it handles the cases of a self-transfer, a cycle or a normal transfer. In the last case it creates an artificial InTransaction to model the remaining amount.
    def _process_remaining_transfer_amount(
        self,
        wallet_2_per_wallet_transactions: Dict[Account, PerWalletTransactions],
        current_in_lot_and_amount: AcquiredLotAndAmount,
        transfer: IntraTransaction,
        remaining_amount: RP2Decimal,
    ) -> None:
        from_account = Account(transfer.from_exchange, transfer.from_holder)
        from_per_wallet_transactions = wallet_2_per_wallet_transactions[from_account]
        to_account = Account(transfer.to_exchange, transfer.to_holder)
        to_per_wallet_transactions = wallet_2_per_wallet_transactions[to_account]
        if transfer.is_self_transfer():
            # Self transfer (loop): do nothing.
            pass
        elif self._is_transaction_cycle(current_in_lot_and_amount.acquired_lot, transfer):
            # Transaction cycle detected: the to_account has already been visited. Return the remaining amount to the start-of-cycle transaction.
            start_of_cycle: InTransaction = current_in_lot_and_amount.acquired_lot.originates_from[to_account]
            start_of_cycle_per_wallet_transactions = to_per_wallet_transactions
            actual_amount = start_of_cycle_per_wallet_transactions.in_transactions.get_partial_amount(start_of_cycle)
            if actual_amount + remaining_amount > start_of_cycle.crypto_in:
                raise RP2ValueError(
                    f"Internal error: start-of-cycle transaction's returned amount exceeds its crypto_in: "
                    f"{actual_amount} + {remaining_amount} > {start_of_cycle.crypto_in}: {start_of_cycle}"
                )
            start_of_cycle_per_wallet_transactions.in_transactions.reset_partial_amounts(
                self.__transfer_semantics, {start_of_cycle: actual_amount + remaining_amount}
            )
        else:
            # Normal case: create an artificial InTransaction for the remaining amount and add it to the to_per_wallet_transactions.
            to_in_transaction = self._create_to_in_transaction(current_in_lot_and_amount.acquired_lot, transfer, remaining_amount)
            to_per_wallet_transactions.in_transactions.add_acquired_lot(to_in_transaction)
            to_per_wallet_transactions.in_transactions.set_to_index(len(to_per_wallet_transactions.in_transactions.acquired_lot_list) - 1)
        # Remove the remaining amount from the actual amount of the current in lot.
        from_per_wallet_transactions.in_transactions.set_partial_amount(
            current_in_lot_and_amount.acquired_lot, current_in_lot_and_amount.amount - remaining_amount
        )

    # This function performs transfer analysis on an InputData and generates as many new InputData objects as there are wallets.
    # For details see https://github.com/eprbell/rp2/wiki/Adding-Per%E2%80%90Wallet-Application-to-RP2.
    def analyze(self) -> Dict[Account, InputData]:
        # TODO: add run-time argument type checks.
        all_transactions: TransactionSet = TransactionSet(self.__configuration, "MIXED", self.__universal_input_data.asset)
        for transaction_set in [
            self.__universal_input_data.unfiltered_in_transaction_set,
            self.__universal_input_data.unfiltered_out_transaction_set,
            self.__universal_input_data.unfiltered_intra_transaction_set,
        ]:
            for transaction in transaction_set:
                all_transactions.add_entry(transaction)

        wallet_2_per_wallet_transactions: Dict[Account, PerWalletTransactions] = {}
        for transaction in all_transactions:
            if isinstance(transaction, InTransaction):
                account = Account(transaction.exchange, transaction.holder)
                per_wallet_transactions = wallet_2_per_wallet_transactions.setdefault(
                    account,
                    PerWalletTransactions(
                        self.__configuration,
                        self.__universal_input_data.asset,
                        self.__transfer_semantics,
                        self.__universal_input_data.from_date,
                        self.__universal_input_data.to_date,
                    ),
                )
                per_wallet_transactions.in_transactions.add_acquired_lot(transaction)
                per_wallet_transactions.in_transactions.set_to_index(len(per_wallet_transactions.in_transactions.acquired_lot_list) - 1)
            elif isinstance(transaction, OutTransaction):
                account = Account(transaction.exchange, transaction.holder)
                # The wallet transactions object must have been already created when processing a previous InTransaction.
                if account not in wallet_2_per_wallet_transactions:
                    raise RP2ValueError(f"Internal error: missing InTransaction for {account} before OutTransaction: {transaction}")
                per_wallet_transactions = wallet_2_per_wallet_transactions[account]
                per_wallet_transactions.out_transactions.add_entry(transaction)

                # Find the acquired lots that cover the out transaction and mark them as actually (or fully) spent.
                amount_left_to_dispose_of = transaction.crypto_out_with_fee
                while True:
                    current_in_lot_and_amount = self.__transfer_semantics.seek_non_exhausted_acquired_lot(
                        per_wallet_transactions.in_transactions, transaction.crypto_out_with_fee
                    )
                    if current_in_lot_and_amount is None:
                        raise RP2ValueError(
                            f"Insufficient balance on {account} to cover out transaction (amount {amount_left_to_dispose_of} {transaction.asset}): {transaction}"
                        )
                    if current_in_lot_and_amount.amount >= amount_left_to_dispose_of:
                        per_wallet_transactions.in_transactions.set_partial_amount(
                            current_in_lot_and_amount.acquired_lot, current_in_lot_and_amount.amount - amount_left_to_dispose_of
                        )
                        break
                    per_wallet_transactions.in_transactions.clear_partial_amount(current_in_lot_and_amount.acquired_lot)
                    amount_left_to_dispose_of -= current_in_lot_and_amount.amount
            elif isinstance(transaction, IntraTransaction):
                from_account = Account(transaction.from_exchange, transaction.from_holder)
                # The from per wallet transactions object must have been already created when processing a previous InTransaction.
                if from_account not in wallet_2_per_wallet_transactions:
                    raise RP2ValueError(f"Internal error: missing InTransaction for {from_account} before IntraTransaction: {transaction}")
                from_per_wallet_transactions = wallet_2_per_wallet_transactions[from_account]
                # IntraTransactions are added to from_per_wallet_transactions.
                from_per_wallet_transactions.intra_transactions.add_entry(transaction)
                to_account = Account(transaction.to_exchange, transaction.to_holder)
                wallet_2_per_wallet_transactions.setdefault(
                    to_account,
                    PerWalletTransactions(
                        self.__configuration,
                        self.__universal_input_data.asset,
                        self.__transfer_semantics,
                        self.__universal_input_data.from_date,
                        self.__universal_input_data.to_date,
                    ),
                )

                # Find the acquired lots that cover the transfer and mark them as actually (or fully) transferred.
                amount_left_to_transfer = transaction.crypto_received
                original_actual_amounts: Dict[InTransaction, RP2Decimal] = {}
                while True:
                    current_in_lot_and_amount = self.__transfer_semantics.seek_non_exhausted_acquired_lot(
                        from_per_wallet_transactions.in_transactions, transaction.crypto_received
                    )
                    if current_in_lot_and_amount is None:
                        raise RP2ValueError(
                            f"Insufficient balance on {from_account} to send funds (amount {amount_left_to_transfer} {transaction.asset}): {transaction}"
                        )
                    original_actual_amounts[current_in_lot_and_amount.acquired_lot] = current_in_lot_and_amount.amount
                    if current_in_lot_and_amount.amount >= amount_left_to_transfer:
                        self._process_remaining_transfer_amount(
                            wallet_2_per_wallet_transactions,
                            current_in_lot_and_amount,
                            transaction,
                            amount_left_to_transfer,
                        )
                        if transaction.is_self_transfer():
                            from_per_wallet_transactions.in_transactions.reset_partial_amounts(self.__transfer_semantics, original_actual_amounts)
                        break
                    self._process_remaining_transfer_amount(
                        wallet_2_per_wallet_transactions,
                        current_in_lot_and_amount,
                        transaction,
                        current_in_lot_and_amount.amount,
                    )
                    amount_left_to_transfer -= current_in_lot_and_amount.amount
            else:
                raise RP2ValueError(f"Internal error: invalid transaction class: {transaction}")

        # Convert per-wallet transactions to input_data and call the tax engine.
        result: Dict[Account, InputData] = {}
        for wallet, per_wallet_transactions in wallet_2_per_wallet_transactions.items():
            per_wallet_input_data = self._convert_per_wallet_transactions_to_input_data(self.__universal_input_data, per_wallet_transactions)
            result[wallet] = per_wallet_input_data
        return result

# Copyright 2025 eprbell
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

from datetime import datetime
from typing import Iterable, cast, Dict, List, Optional

from rp2.configuration import Configuration
from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.accounting_engine import AccountingEngine, AcquiredLotsExhaustedException
from rp2.in_transaction import Account, InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.logger import LOGGER
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2ValueError, RP2TypeError
from rp2.transaction_set import TransactionSet

from prezzemolo.avl_tree import AVLTree


class GlobalAllocator:
    def __init__(
        self, configuration: Configuration,
        allocation_method: AbstractAccountingMethod,
        wallet_2_per_wallet_input_data: Dict[Account, InputData],
        year: int,
        account_order: List[Account],
    ):
        self.__configuration = Configuration.type_check("configuration", configuration)
        if not isinstance(allocation_method, AbstractAccountingMethod):
            raise RP2TypeError(f"Parameter 'allocation_method' is not of type AbstractAccountingMethod: {allocation_method}")
        self.__allocation_method = allocation_method
        if len(wallet_2_per_wallet_input_data) == 0:
            raise RP2ValueError("Parameter 'wallet_2_per_wallet_input_data' is empty.")
        self.__asset = ""
        # Available balances take into account self-looping transactions (which reduce the available balance for outgoing funds).
        self.__account_to_available_balance: Dict[Account, RP2Decimal] = {}
        for account, input_data in wallet_2_per_wallet_input_data.items():
            if not isinstance(account, Account):
                raise RP2TypeError(f"Parameter 'per_wallet_input_data' contains a key that is not of type Account: {account}")
            InputData.type_check(f"per_wallet_input_data[{account}] is not of type InputData", input_data)
            if self.__asset not in (input_data.asset, ""):
                raise RP2ValueError(f"Asset mismatch: {input_data.asset} != {self.__asset}")
            self.__asset = input_data.asset
            balance = ZERO
            for in_transaction in input_data.unfiltered_in_transaction_set:
                in_transaction = cast(InTransaction, in_transaction)
                balance += input_data.in_transaction_2_actual_amount[in_transaction] \
                    if in_transaction in input_data.in_transaction_2_actual_amount else in_transaction.crypto_in + in_transaction.crypto_fee
            self.__account_to_available_balance[account] = balance
        self.__wallet_2_per_wallet_input_data = wallet_2_per_wallet_input_data
        self.__year = Configuration.type_check_positive_int("year", year)
        self.__leftover_acquired_lot: Optional[InTransaction] = None
        self.__leftover_acquired_lot_partial_amount: RP2Decimal = ZERO
        for account in account_order:
            if not isinstance(account, Account):
                raise RP2TypeError(f"Parameter 'account_order' contains an element that is not of type Account: {account}")
            if not account in self.__wallet_2_per_wallet_input_data:
                raise RP2ValueError(f"Account order list has extra account {account} that is not referenced in the transaction set.")
        self.__account_order = account_order
        if len(self.__wallet_2_per_wallet_input_data) > len(self.__account_order):
            raise RP2ValueError(f"Account order list is incomplete. Missing accounts: {set(self.__wallet_2_per_wallet_input_data.keys()) - set(self.__account_order)}")

    def allocate(self) -> List[IntraTransaction]:
        years_2_accounting_methods: AVLTree[int, AbstractAccountingMethod] = AVLTree()
        years_2_accounting_methods.insert_node(1970, self.__allocation_method)
        global_allocation_intra_transactions: List[IntraTransaction] = []

        LOGGER.info("Global allocation of %s: found %d wallets.", self.__year, len(self.__wallet_2_per_wallet_input_data))
        acquired_lots: TransactionSet = TransactionSet(self.__configuration, "IN", self.__asset)
        in_transaction_2_actual_amount: Dict[InTransaction, RP2Decimal] = {}
        for wallet, per_wallet_input_data in self.__wallet_2_per_wallet_input_data.items():
            LOGGER.info("Global allocation of %s: processing wallet %s", self.__year, wallet)
            in_transaction_2_actual_amount.update(per_wallet_input_data.in_transaction_2_actual_amount)
            for in_transaction in per_wallet_input_data.unfiltered_in_transaction_set:
                in_transaction = cast(InTransaction, in_transaction)
                if in_transaction.from_lot is not None:
                    LOGGER.info("Global allocation of %s: artificial in-transaction: %s", self.__year, repr(in_transaction))
                acquired_lots.add_entry(in_transaction)
        unique_id_to_actual_amount = {in_transaction.unique_id : amount for in_transaction, amount in in_transaction_2_actual_amount.items()}
        LOGGER.info("Global allocation of %s: actual_amounts: %s.", self.__year, unique_id_to_actual_amount)

        # Process wallets in the order specified by the user. For each wallet, create intra transactions that model the global allocation.
        for account in self.__account_order:
            accounting_engine = AccountingEngine(years_2_accounting_methods)
            # Taxable events are not relevant for the global allocation, so pass an empty iterator.
            accounting_engine.initialize(iter([]), iter(cast(Iterable[InTransaction], acquired_lots)), in_transaction_2_actual_amount)
            intra_transactions = self.__process_wallet(accounting_engine, account)
            global_allocation_intra_transactions.extend(intra_transactions)

        LOGGER.info("Global allocation of %s: created %d intra transactions.", self.__year, len(global_allocation_intra_transactions))

        return global_allocation_intra_transactions

    def __create_intra_transaction(self, acquired_lot: InTransaction, timestamp: str, account: Account, amount: RP2Decimal) -> IntraTransaction:
        artificial_id = self.__configuration.get_new_artificial_id()
        return IntraTransaction(
            configuration=self.__configuration,
            timestamp=timestamp,
            asset=acquired_lot.asset,
            from_exchange=acquired_lot.exchange,
            from_holder=acquired_lot.holder,
            to_exchange=account.exchange,
            to_holder=account.holder,
            spot_price=RP2Decimal(1), # TODO: can this be improved? It's not relevant for global allocation, but 1 as spot price may be misleading to users.
            crypto_sent=amount,
            crypto_received=amount,
            row=artificial_id,
            unique_id=f"ga/{artificial_id}",
            notes=(
                f"Artificial intra transaction for {self.__allocation_method} universal application of year "
                f"{self.__year}. Spot price is not relevant and set to 1 arbitrarily."
            ),
        )

    def __process_wallet(self, accounting_engine: AccountingEngine, account: Account) -> List[IntraTransaction]:
        result: List[IntraTransaction] = []
        try:
            timestamp_string = f"{self.__year}-01-01 00:00:00 +0000"
            timestamp = datetime.fromisoformat(timestamp_string)
            balance_left_to_process: RP2Decimal = self.__account_to_available_balance[account]
            if balance_left_to_process == ZERO:
                return result
            acquired_lot: Optional[InTransaction] = None
            acquired_lot_amount: RP2Decimal = ZERO
            transferred_amount = ZERO
            while True:
                if self.__leftover_acquired_lot is not None:
                    acquired_lot = self.__leftover_acquired_lot
                    acquired_lot_amount = self.__leftover_acquired_lot_partial_amount
                    self.__leftover_acquired_lot = None
                    self.__leftover_acquired_lot_partial_amount = ZERO
                else:
                    (acquired_lot, balance_left_to_process, acquired_lot_amount) = accounting_engine.get_acquired_lot_for_timestamp(
                        timestamp, acquired_lot, balance_left_to_process, acquired_lot_amount
                    )
                # Type check values returned by accounting method plugin
                if acquired_lot is None:
                    # There must always be at least one acquired_lot
                    raise RP2RuntimeError("Parameter 'acquired_lot' is None")
                InTransaction.type_check("acquired_lot", acquired_lot)
                Configuration.type_check_positive_decimal("taxable_event_amount", balance_left_to_process)
                Configuration.type_check_positive_decimal("acquired_lot_amount", acquired_lot_amount)

                from_account = Account(acquired_lot.exchange, acquired_lot.holder)
                from_available_balance = self.__account_to_available_balance[from_account]
                if balance_left_to_process <= acquired_lot_amount:
                    transferred_amount = min(balance_left_to_process, from_available_balance)
                    self.__leftover_acquired_lot_partial_amount = acquired_lot_amount - balance_left_to_process
                    self.__leftover_acquired_lot = acquired_lot if self.__leftover_acquired_lot_partial_amount > ZERO else None
                    intra_transaction = self.__create_intra_transaction(acquired_lot, timestamp_string, account, transferred_amount)
                    if intra_transaction.is_self_transfer():
                        self.__account_to_available_balance[account] -= transferred_amount
                    result.append(intra_transaction)
                    break
                # adjusted_final_balance > acquired_lot_amount
                transferred_amount = min(acquired_lot_amount, from_available_balance)
                intra_transaction = self.__create_intra_transaction(acquired_lot, timestamp_string, account, transferred_amount)
                if intra_transaction.is_self_transfer():
                    self.__account_to_available_balance[account] -= transferred_amount
                result.append(intra_transaction)
        except AcquiredLotsExhaustedException:
            raise RP2ValueError("Total in-transaction crypto value < adjusted final balance crypto value") from None

        return result

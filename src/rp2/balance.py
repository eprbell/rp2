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
from datetime import date, datetime
from decimal import Decimal
from typing import Callable, Dict, List, Optional

from prezzemolo.utility import to_string

from rp2.abstract_entry import AbstractEntry
from rp2.configuration import Configuration
from rp2.in_transaction import Account, InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.logger import LOGGER
from rp2.out_transaction import OutTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError

CRYPTO_BALANCE_DECIMAL_MASK: Decimal = Decimal("1." + "0" * 10)


@dataclass(frozen=True, eq=True)
class Balance:
    configuration: Configuration
    asset: str
    exchange: str
    holder: str
    final_balance: RP2Decimal
    acquired_balance: RP2Decimal
    sent_balance: RP2Decimal
    received_balance: RP2Decimal

    def __post_init__(self) -> None:
        Configuration.type_check("configuration", self.configuration)
        self.configuration.type_check_asset("asset", self.asset)
        self.configuration.type_check_exchange("exchange", self.exchange)
        self.configuration.type_check_holder("holder", self.holder)
        self.configuration.type_check_decimal("final_balance", self.final_balance)
        self.configuration.type_check_decimal("acquired_balance", self.acquired_balance)
        self.configuration.type_check_decimal("sent_balance", self.sent_balance)
        self.configuration.type_check_decimal("received_balance", self.received_balance)

    def to_string(self, indent: int = 0, repr_format: bool = True, extra_data: Optional[List[str]] = None) -> str:
        class_specific_data: List[str] = []
        stringify: Callable[[object], str] = repr
        if not repr_format:
            stringify = str

        if repr_format:
            class_specific_data.append(f"{type(self).__name__}(asset={repr(self.asset)}")
        else:
            class_specific_data.append(f"{type(self).__name__}:")
            class_specific_data.append(f"asset={str(self.asset)}")

        class_specific_data.append(f"exchange={stringify(self.exchange)}")
        class_specific_data.append(f"holder={stringify(self.holder)}")
        class_specific_data.append(f"final_balance={self.final_balance:.8f}")
        class_specific_data.append(f"acquired_balance={self.acquired_balance:.8f}")
        class_specific_data.append(f"sent_balance={self.sent_balance:.8f}")
        class_specific_data.append(f"received_balance={self.received_balance:.8f}")

        if extra_data:
            class_specific_data.extend(extra_data)

        return to_string(indent=indent, repr_format=repr_format, data=class_specific_data)

    def __str__(self) -> str:
        return self.to_string(indent=0, repr_format=False)

    def __repr__(self) -> str:
        return self.to_string(indent=0, repr_format=True)


class BalanceSet:
    @classmethod
    def type_check(cls, name: str, instance: "BalanceSet") -> "BalanceSet":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    # from_date is not used when computing average price per unit: only to_date is relevant.
    def __init__(
        self,
        configuration: Configuration,
        input_data: InputData,
        to_date: date,
    ) -> None:
        Configuration.type_check("configuration", configuration)
        self.__input_data = InputData.type_check("input_data", input_data)

        self.__asset: str = configuration.type_check_asset("in_transaction_set.asset", input_data.asset)
        self._balances: List[Balance] = []

        acquired_balances: Dict[Account, RP2Decimal] = {}
        sent_balances: Dict[Account, RP2Decimal] = {}
        received_balances: Dict[Account, RP2Decimal] = {}
        final_balances: Dict[Account, RP2Decimal] = {}

        from_account: Account
        to_account: Account

        in_transactions = list(self.__input_data.unfiltered_in_transaction_set)
        intra_transactions = list(self.__input_data.unfiltered_intra_transaction_set)
        out_transactions = list(self.__input_data.unfiltered_out_transaction_set)

        transactions = in_transactions + intra_transactions + out_transactions
        transactions = sorted(
            transactions,
            key=_transaction_time_sort_key,
        )

        # Balances for bought and earned currency
        for transaction in transactions:
            if transaction.timestamp.date() > to_date:
                break
            if isinstance(transaction, InTransaction):
                in_transaction: InTransaction = transaction
                to_account = Account(in_transaction.exchange, in_transaction.holder)
                acquired_balances[to_account] = acquired_balances.get(to_account, ZERO) + in_transaction.crypto_in
                final_balances[to_account] = final_balances.get(to_account, ZERO) + in_transaction.crypto_in

            # Balances for currency that is moved across accounts
            if isinstance(transaction, IntraTransaction):
                intra_transaction: IntraTransaction = transaction
                from_account = Account(intra_transaction.from_exchange, intra_transaction.from_holder)
                to_account = Account(intra_transaction.to_exchange, intra_transaction.to_holder)
                sent_balances[from_account] = sent_balances.get(from_account, ZERO) + intra_transaction.crypto_sent
                received_balances[to_account] = received_balances.get(to_account, ZERO) + intra_transaction.crypto_received
                final_balances[from_account] = final_balances.get(from_account, ZERO) - intra_transaction.crypto_sent
                final_balances[to_account] = final_balances.get(to_account, ZERO) + intra_transaction.crypto_received
                if (
                    not RP2Decimal.is_equal_within_precision(final_balances[from_account], ZERO, CRYPTO_BALANCE_DECIMAL_MASK)
                    and final_balances[from_account] < ZERO
                    and not configuration.allow_negative_balances
                ):
                    raise RP2ValueError(
                        f'{intra_transaction.asset} balance of account "{from_account.exchange}" (holder "{from_account.holder}") went negative '
                        f"({final_balances[from_account]}) on the following transaction: {intra_transaction}"
                    )

            # Balances for sold and gifted currency
            if isinstance(transaction, OutTransaction):
                out_transaction: OutTransaction = transaction
                from_account = Account(out_transaction.exchange, out_transaction.holder)
                sent_balances[from_account] = sent_balances.get(from_account, ZERO) + out_transaction.crypto_out_no_fee + out_transaction.crypto_fee
                final_balances[from_account] = final_balances.get(from_account, ZERO) - out_transaction.crypto_out_no_fee - out_transaction.crypto_fee
                if (
                    not RP2Decimal.is_equal_within_precision(final_balances[from_account], ZERO, CRYPTO_BALANCE_DECIMAL_MASK)
                    and final_balances[from_account] < ZERO
                    and not configuration.allow_negative_balances
                ):
                    raise RP2ValueError(
                        f'{out_transaction.asset} balance of account "{from_account.exchange}" (holder "{from_account.holder}") went negative '
                        f"({final_balances[from_account]}) on the following transaction: {out_transaction}"
                    )

        for account, final_balance in final_balances.items():
            balance = Balance(
                configuration,
                self.__asset,
                account.exchange,
                account.holder,
                final_balance,
                acquired_balances.get(account, ZERO),
                sent_balances.get(account, ZERO),
                received_balances.get(account, ZERO),
            )
            LOGGER.debug("created balance: %s", balance)
            self._balances.append(balance)

        self._balances.sort(key=_balance_sort_key)

    def __str__(self) -> str:
        output: List[str] = []
        output.append(f"{type(self).__name__}:")
        output.append(f"  asset={self.asset}")
        output.append("  balances=")
        for balance in self:
            output.append(f"{balance.to_string(indent=2, repr_format=False)}")
        return "\n".join(output)

    def __repr__(self) -> str:
        output: List[str] = []
        output.append(f"{type(self).__name__}(")
        output.append(f", asset={repr(self.asset)}")
        output.append(", balances=[")
        count: int = 0
        for balance in self:
            if count > 0:
                output.append(", ")
            output.append(repr(balance))
            count += 1
        output.append("]")
        output.append(")")
        return "".join(output)

    def __iter__(self) -> "BalanceSetIterator":
        return BalanceSetIterator(self)

    @property
    def count(self) -> int:
        return len(self._balances)

    @property
    def asset(self) -> str:
        return self.__asset


class BalanceSetIterator:
    def __init__(self, balance_set: BalanceSet) -> None:
        self.__balance_set: BalanceSet = balance_set
        self.__balance_set_size: int = len(self.__balance_set._balances)
        self.__index: int = 0

    def __next__(self) -> Balance:
        result: Optional[Balance] = None
        if self.__index < self.__balance_set_size:
            result = self.__balance_set._balances[self.__index]  # pylint: disable=protected-access
            self.__index += 1
            return result
        raise StopIteration(self)


def _balance_sort_key(balance: Balance) -> str:
    return f"{balance.exchange}_{balance.holder}"


def _transaction_time_sort_key(transaction: AbstractEntry) -> datetime:
    return transaction.timestamp

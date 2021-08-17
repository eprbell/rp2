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

from decimal import Decimal
from typing import Dict, List, Optional, Tuple, cast

from configuration import Configuration
from in_transaction import InTransaction
from input_data import InputData
from intra_transaction import IntraTransaction
from out_transaction import OutTransaction
from rp2_decimal import ZERO
from rp2_error import RP2TypeError


class Balance:
    def __init__(
        self,
        configuration: Configuration,
        asset: str,
        exchange: str,
        holder: str,
        final_balance: Decimal,
        acquired_balance: Decimal,
        sent_balance: Decimal,
        received_balance: Decimal,
    ) -> None:
        Configuration.type_check("configuration", configuration)
        self.__asset: str = configuration.type_check_asset("asset", asset)
        self.__exchange: str = configuration.type_check_exchange("exchange", exchange)
        self.__holder: str = configuration.type_check_holder("holder", holder)
        self.__final_balance: Decimal = configuration.type_check_decimal("final_balance", final_balance)
        self.__acquired_balance: Decimal = configuration.type_check_decimal("acquired_balance", acquired_balance)
        self.__sent_balance: Decimal = configuration.type_check_decimal("sent_balance", sent_balance)
        self.__received_balance: Decimal = configuration.type_check_decimal("received_balance", received_balance)

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}:\n"
            f"  asset={str(self.asset)}\n"
            f"  exchange={str(self.exchange)}\n"
            f"  holder={str(self.holder)}\n"
            f"  final_balance={self.final_balance:.8f}\n"
            f"  acquired_balance={self.acquired_balance:.8f}\n"
            f"  sent_balance={self.sent_balance:.8f}\n"
            f"  received_balance={self.received_balance:.8f})"
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"asset={repr(self.asset)}, "
            f"exchange={repr(self.exchange)}, "
            f"holder={repr(self.holder)}, "
            f"final_balance={self.final_balance:.8f}, "
            f"acquired_balance={self.acquired_balance:.8f}, "
            f"sent_balance={self.sent_balance:.8f}, "
            f"received_balance={self.received_balance:.8f})"
        )

    @property
    def asset(self) -> str:
        return self.__asset

    @property
    def exchange(self) -> str:
        return self.__exchange

    @property
    def holder(self) -> str:
        return self.__holder

    @property
    def final_balance(self) -> Decimal:
        return self.__final_balance

    @property
    def acquired_balance(self) -> Decimal:
        return self.__acquired_balance

    @property
    def sent_balance(self) -> Decimal:
        return self.__sent_balance

    @property
    def received_balance(self) -> Decimal:
        return self.__received_balance


class BalanceSet:
    def __init__(
        self,
        configuration: Configuration,
        input_data: InputData,
    ) -> None:

        Configuration.type_check("configuration", configuration)
        self.__input_data = InputData.type_check("input_data", input_data)

        self.__asset: str = configuration.type_check_asset("in_transaction_set.asset", input_data.asset)
        self._balances: List[Balance] = []

        acquired_balances: Dict[Tuple[str, str], Decimal] = {}
        sent_balances: Dict[Tuple[str, str], Decimal] = {}
        received_balances: Dict[Tuple[str, str], Decimal] = {}
        final_balances: Dict[Tuple[str, str], Decimal] = {}

        from_account: Tuple[str, str]
        to_account: Tuple[str, str]

        # Balances for bought and earned currency
        for transaction in self.__input_data.in_transaction_set:
            in_transaction: InTransaction = cast(InTransaction, transaction)
            to_account = (in_transaction.exchange, in_transaction.holder)
            acquired_balances[to_account] = acquired_balances.get(to_account, 0) + in_transaction.crypto_in
            final_balances[to_account] = final_balances.get(to_account, 0) + in_transaction.crypto_in

        # Balances for sent and received currency
        for transaction in self.__input_data.intra_transaction_set:
            intra_transaction: IntraTransaction = cast(IntraTransaction, transaction)
            from_account = (intra_transaction.from_exchange, intra_transaction.from_holder)
            to_account = (intra_transaction.to_exchange, intra_transaction.to_holder)
            sent_balances[from_account] = sent_balances.get(from_account, 0) + intra_transaction.crypto_sent
            received_balances[to_account] = received_balances.get(to_account, 0) + intra_transaction.crypto_received
            final_balances[from_account] = final_balances.get(from_account, 0) - intra_transaction.crypto_sent
            final_balances[to_account] = final_balances.get(to_account, 0) + intra_transaction.crypto_received

        for transaction in self.__input_data.out_transaction_set:
            out_transaction: OutTransaction = cast(OutTransaction, transaction)
            from_account = (out_transaction.exchange, out_transaction.holder)
            sent_balances[from_account] = sent_balances.get(from_account, 0) + out_transaction.crypto_out_no_fee + out_transaction.crypto_fee
            final_balances[from_account] = final_balances.get(from_account, 0) - out_transaction.crypto_out_no_fee - out_transaction.crypto_fee

        for (exchange, holder), final_balance in final_balances.items():
            balance = Balance(
                configuration,
                self.__asset,
                exchange,
                holder,
                final_balance,
                acquired_balances.get((exchange, holder), ZERO),
                sent_balances.get((exchange, holder), ZERO),
                received_balances.get((exchange, holder), ZERO),
            )
            self._balances.append(balance)

        self._balances.sort(key=_balance_sort_key)

    @classmethod
    def type_check(cls, name: str, instance: "BalanceSet") -> "BalanceSet":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __str__(self) -> str:
        output: List[str] = []
        output.append(f"{type(self).__name__}:")
        output.append(f"  asset={repr(self.asset)}")
        output.append("  balances=")
        for balance in self:
            output.append(f"    {str(balance).replace('  ', '      ')}")
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
            result = self.__balance_set._balances[self.__index]
            self.__index += 1
            return result
        raise StopIteration(self)


def _balance_sort_key(balance: Balance) -> str:
    return f"{balance.exchange}_{balance.holder}"

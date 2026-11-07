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
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from rp2.account import Account
from rp2.configuration import Configuration
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError


# A lot, or the part of it, that universal application hasn't disposed of at the switch: "unused basis" in Rev. Proc. 2024-28. Example: 10
# coins bought for $1,000 in 2024 and 4 of them sold in 2024 leave an unused lot of 6 coins with $600 of cost basis.
class UnusedLot(NamedTuple):
    acquired_lot: InTransaction
    amount: RP2Decimal

    # Cost basis of the unused amount: the per-unit cost basis of the lot (purchase fee included) times the amount.
    @property
    def cost_basis(self) -> RP2Decimal:
        return self.acquired_lot.fiat_in_with_fee * self.amount / self.acquired_lot.crypto_in


# The opening allocation of one asset at the switch to per-wallet application (Rev. Proc. 2024-28 global allocation, see
# UnusedBasisAllocator), recorded before any later transaction changes what the wallets hold. It contains:
# - what each wallet held at the switch (its opening balance) and the unused lots;
# - the rule that was applied: the allocation method that sorts the unused lots and the order in which the wallets are filled, or the
#   automatic allocation if only one wallet held units (there is nothing to choose then);
# - the allocated lot pieces: one artificial InTransaction per piece of an unused lot that went to a wallet, with the same per-unit cost basis
#   and acquisition date as the lot (its from_lot).
# The opening allocation report shows it (see plugin/report/opening_allocation.py).
#
# Example: in 2024 buy 10 coins for $100 each on Coinbase (lot i1) and 10 coins for $200 each on Kraken (lot i2), then move 5 coins from
# Coinbase to Kraken. At the switch Coinbase holds 5 coins and Kraken 15, and both lots are unused (nothing was sold). With FIFO and the wallet
# order Kraken, Coinbase, the oldest lot goes first to the first wallet: Kraken gets the 10 coins of i1 ($1,000) and 5 coins of i2 ($1,000),
# and Coinbase the other 5 coins of i2 ($1,000). Each piece keeps the purchase date of its lot.
class OpeningAllocation:
    @classmethod
    def type_check(cls, name: str, instance: "OpeningAllocation") -> "OpeningAllocation":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    # wallet_order is the order in which the wallets were filled: the configured one (wallets in it that hold nothing at the switch get
    # nothing) or, in an automatic allocation, the only wallet that holds units. allocation_method_field and wallet_order_field are the names
    # of the configuration fields the rule comes from (e.g. unused_basis_allocation_method.BTC for a per-asset override), or None if the rule
    # doesn't come from the configuration (an automatic allocation needs no wallet order, nor a method: FIFO is used if none is configured).
    def __init__(
        self,
        asset: str,
        switch_timestamp: datetime,
        is_automatic: bool,
        allocation_method_name: str,
        wallet_order: Sequence[Account],
        account_2_balance: Dict[Account, RP2Decimal],
        unused_lots: Sequence[UnusedLot],
        allocated_lots: Sequence[InTransaction],
        allocation_method_field: Optional[str] = None,
        wallet_order_field: Optional[str] = None,
    ) -> None:
        self.__asset: str = Configuration.type_check_string("asset", asset)
        if not isinstance(switch_timestamp, datetime) or switch_timestamp.tzinfo is None:
            raise RP2TypeError(f"Parameter 'switch_timestamp' is not a timezone-aware datetime: {switch_timestamp}")
        self.__switch_timestamp: datetime = switch_timestamp
        self.__is_automatic: bool = Configuration.type_check_bool("is_automatic", is_automatic)
        self.__allocation_method_name: str = Configuration.type_check_string("allocation_method_name", allocation_method_name)
        self.__allocation_method_field: Optional[str] = (
            Configuration.type_check_string("allocation_method_field", allocation_method_field) if allocation_method_field is not None else None
        )
        self.__wallet_order_field: Optional[str] = (
            Configuration.type_check_string("wallet_order_field", wallet_order_field) if wallet_order_field is not None else None
        )
        for account in [*wallet_order, *account_2_balance]:
            if not isinstance(account, Account):
                raise RP2TypeError(f"Opening allocation of {asset}: invalid wallet {account}")
        self.__wallet_order: Tuple[Account, ...] = tuple(wallet_order)
        self.__account_2_balance: Dict[Account, RP2Decimal] = {
            account: Configuration.type_check_decimal("balance", balance) for account, balance in account_2_balance.items()
        }
        for unused_lot in unused_lots:
            if not isinstance(unused_lot, UnusedLot) or unused_lot.acquired_lot.asset != asset:
                raise RP2ValueError(f"Opening allocation of {asset}: invalid unused lot {unused_lot}")
        self.__unused_lots: List[UnusedLot] = list(unused_lots)
        for allocated_lot in allocated_lots:
            InTransaction.type_check("allocated_lot", allocated_lot)
            if allocated_lot.asset != asset or allocated_lot.from_lot is None:
                raise RP2ValueError(f"Opening allocation of {asset}: invalid allocated lot {allocated_lot}")
        self.__allocated_lots: List[InTransaction] = list(allocated_lots)

    def __str__(self) -> str:
        return (
            f"OpeningAllocation(asset={self.__asset}, switch_timestamp={self.__switch_timestamp.isoformat()}, is_automatic={self.__is_automatic}, "
            f"allocation_method={self.__allocation_method_name}, wallet_order=[{', '.join(_wallet_name(account) for account in self.__wallet_order)}], "
            f"unused_lots={len(self.__unused_lots)}, allocated_lots={len(self.__allocated_lots)})"
        )

    @property
    def asset(self) -> str:
        return self.__asset

    # The first instant of per-wallet application, in the tax time zone (e.g. 2025-01-01T00:00:00-05:00 in America/New_York).
    @property
    def switch_timestamp(self) -> datetime:
        return self.__switch_timestamp

    # The tax time zone (see Configuration.tax_timezone), e.g. America/New_York.
    @property
    def timezone_name(self) -> str:
        return str(self.__switch_timestamp.tzinfo)

    # True if only one wallet held units at the switch: they all go to it, without an allocation rule.
    @property
    def is_automatic(self) -> bool:
        return self.__is_automatic

    @property
    def allocation_method_name(self) -> str:
        return self.__allocation_method_name

    @property
    def allocation_method_field(self) -> Optional[str]:
        return self.__allocation_method_field

    @property
    def wallet_order(self) -> Tuple[Account, ...]:
        return self.__wallet_order

    @property
    def wallet_order_field(self) -> Optional[str]:
        return self.__wallet_order_field

    # The wallets of the report: those in the wallet order, in that order, then those that had transactions before the switch but aren't in
    # the order (they hold nothing at the switch), sorted by name.
    @property
    def wallets(self) -> List[Account]:
        others = sorted((account for account in self.__account_2_balance if account not in self.__wallet_order), key=_wallet_name)
        return list(self.__wallet_order) + others

    # The units each wallet held at the switch, computed from the transactions before it (zero for a wallet without transactions).
    def get_opening_balance(self, account: Account) -> RP2Decimal:
        return self.__account_2_balance.get(account, ZERO)

    # The unused lots, in the order of the allocation method (the order in which they were allocated).
    @property
    def unused_lots(self) -> List[UnusedLot]:
        return list(self.__unused_lots)

    # The allocated lot pieces, in the order they were allocated: wallet by wallet (in the wallet order), and within a wallet in the order of
    # the unused lots.
    @property
    def allocated_lots(self) -> List[InTransaction]:
        return list(self.__allocated_lots)

    def get_allocated_lots(self, account: Account) -> List[InTransaction]:
        return [lot for lot in self.__allocated_lots if Account(lot.exchange, lot.holder) == account]

    @property
    def opening_balance(self) -> RP2Decimal:
        return RP2Decimal(sum((balance for balance in self.__account_2_balance.values() if balance > ZERO), ZERO))

    @property
    def unused_crypto(self) -> RP2Decimal:
        return RP2Decimal(sum((unused_lot.amount for unused_lot in self.__unused_lots), ZERO))

    @property
    def unused_cost_basis(self) -> RP2Decimal:
        return RP2Decimal(sum((unused_lot.cost_basis for unused_lot in self.__unused_lots), ZERO))

    @property
    def allocated_crypto(self) -> RP2Decimal:
        return RP2Decimal(sum((lot.crypto_in for lot in self.__allocated_lots), ZERO))

    @property
    def allocated_cost_basis(self) -> RP2Decimal:
        return RP2Decimal(sum((lot.fiat_in_with_fee for lot in self.__allocated_lots), ZERO))


# Wallets are displayed and sorted as <exchange>/<holder>, the same format used in the configuration file.
def _wallet_name(account: Account) -> str:
    return f"{account.exchange}/{account.holder}"

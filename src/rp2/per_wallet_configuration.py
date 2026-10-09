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

from dataclasses import dataclass, field
from datetime import tzinfo
from typing import Dict, Optional, Set, Tuple

from dateutil import tz

from rp2.account import Account
from rp2.rp2_error import RP2TypeError, RP2ValueError


# User choices for per-wallet application: the per-wallet fields of the country section of the configuration file (e.g. [country.us]).
# Each of these is a decision the law doesn't settle, or that only the taxpayer can make, so none of them has a silent default: the
# per-wallet tax engine raises an error if the input needs one of them and it's missing.
@dataclass(frozen=True, eq=True)
class PerWalletConfiguration:
    # IANA time zone (e.g. America/New_York) in which the start of the first per-wallet year is measured.
    timezone_name: str
    # Rev. Proc. 2024-28 global allocation of unused basis: accounting method used to order the unused lots (e.g. fifo) and order in
    # which wallets are filled with them (only needed if more than one wallet holds funds at the switch).
    unused_basis_allocation_method: Optional[str] = None
    unused_basis_allocation_wallet_order: Tuple[Account, ...] = ()
    # Per-asset overrides of the two fields above: Rev. Proc. 2024-28 (sections 4.01(4) and 5.02(6)) applies the safe harbor to each type
    # of digital asset separately, so each asset can have its own allocation rule (e.g. a wallet order based on its own balances).
    asset_2_unused_basis_allocation_method: Dict[str, str] = field(default_factory=dict)
    asset_2_unused_basis_allocation_wallet_order: Dict[str, Tuple[Account, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.timezone_name, str) or not self.timezone_name.strip():
            raise RP2ValueError("Per-wallet configuration: 'timezone' cannot be empty")
        if tz.gettz(self.timezone_name) is None:
            raise RP2ValueError(f"Per-wallet configuration: unknown timezone '{self.timezone_name}' (use an IANA name, e.g. America/New_York)")
        for wallet_order in [self.unused_basis_allocation_wallet_order, *self.asset_2_unused_basis_allocation_wallet_order.values()]:
            for account in wallet_order:
                if not isinstance(account, Account):
                    raise RP2TypeError(f"Per-wallet configuration: wallet order contains a non-Account element: {account}")
            if len(set(wallet_order)) != len(wallet_order):
                raise RP2ValueError(f"Per-wallet configuration: wallet order contains duplicates: {wallet_order}")
        # The effective rule of each asset (default or override) needs both a method and a wallet order, or neither.
        if bool(self.unused_basis_allocation_method) != bool(self.unused_basis_allocation_wallet_order):
            raise RP2ValueError(
                "Per-wallet configuration: 'unused_basis_allocation_method' and 'unused_basis_allocation_wallet_order' must be defined together"
            )
        for asset in set(self.asset_2_unused_basis_allocation_method) | set(self.asset_2_unused_basis_allocation_wallet_order):
            if bool(self.get_unused_basis_allocation_method(asset)) != bool(self.get_unused_basis_allocation_wallet_order(asset)):
                raise RP2ValueError(
                    f"Per-wallet configuration: the unused basis allocation of {asset} has a method or a wallet order, but not both (define the "
                    "missing one for the asset or as a default)"
                )

    @classmethod
    def type_check(cls, name: str, instance: "PerWalletConfiguration") -> "PerWalletConfiguration":
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    # Allocation method of the given asset: its override, if any, otherwise the default.
    def get_unused_basis_allocation_method(self, asset: str) -> Optional[str]:
        return self.asset_2_unused_basis_allocation_method.get(asset, self.unused_basis_allocation_method)

    # Wallet order of the given asset: its override, if any, otherwise the default.
    def get_unused_basis_allocation_wallet_order(self, asset: str) -> Tuple[Account, ...]:
        return self.asset_2_unused_basis_allocation_wallet_order.get(asset, self.unused_basis_allocation_wallet_order)

    # All allocation method names used by the configuration (default and overrides).
    @property
    def unused_basis_allocation_method_names(self) -> Set[str]:
        result = set(self.asset_2_unused_basis_allocation_method.values())
        if self.unused_basis_allocation_method:
            result.add(self.unused_basis_allocation_method)
        return result

    @property
    def timezone(self) -> tzinfo:
        result = tz.gettz(self.timezone_name)
        if result is None:
            raise RP2ValueError(f"Unknown timezone: {self.timezone_name}")
        return result

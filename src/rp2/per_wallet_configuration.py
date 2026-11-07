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
from types import MappingProxyType
from typing import Mapping, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo, available_timezones

from rp2.account import Account
from rp2.rp2_error import RP2TypeError, RP2ValueError

# IANA time zone identifiers available on this computer. They come from the system time zone database or, where there is none (e.g. on
# Windows), from the tzdata package (https://docs.python.org/3/library/zoneinfo.html#data-sources). Listing them reads hundreds of files,
# so it's done only once (see _get_available_timezone_names()).
_AVAILABLE_TIMEZONE_NAMES: Set[str] = set()


def _get_available_timezone_names() -> Set[str]:
    if not _AVAILABLE_TIMEZONE_NAMES:
        _AVAILABLE_TIMEZONE_NAMES.update(available_timezones())
    return _AVAILABLE_TIMEZONE_NAMES


# Returns the time zone with the given IANA identifier (e.g. America/New_York or UTC). The same configuration file must give the same
# result on every computer, so names whose meaning is ambiguous or depends on the computer are rejected:
# - abbreviations, like PST, CST or EST: CST is US Central time to some and China time to others, and some libraries resolve an abbreviation
#   that matches the computer's own time zone to that time zone (with python-dateutil, CST is UTC-6 on a computer set to Chicago time and
#   UTC+8 on one set to Shanghai time). The few abbreviations that IANA keeps for compatibility have no daylight saving time: EST is UTC-5
#   even in summer, when New York is at UTC-4;
# - localtime, which is the computer's own time zone;
# - identifiers with the wrong case (e.g. america/new_york): some systems find them and others don't.
# So the name must be UTC or an Area/Location identifier (e.g. America/New_York, Europe/Rome, Etc/UTC), spelled as in the IANA database.
def _get_iana_timezone(name: str) -> ZoneInfo:
    if name != "UTC" and "/" not in name:
        raise RP2ValueError(
            f"'{name}' is not an IANA time zone identifier: use UTC or an Area/Location identifier (e.g. America/New_York). Abbreviations "
            "like PST, CST or EST are not accepted, because their meaning is ambiguous or depends on the computer's settings"
        )
    available_names = _get_available_timezone_names()
    if not available_names:
        raise RP2ValueError(f"no IANA time zone data on this computer to look up '{name}': install the tzdata Python package (pip install tzdata)")
    if name not in available_names:
        raise RP2ValueError(
            f"unknown IANA time zone '{name}': identifiers are case-sensitive (e.g. America/New_York), see "
            "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
        )
    return ZoneInfo(name)


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
    # They are read-only views of private copies (see __post_init__()).
    asset_2_unused_basis_allocation_method: Mapping[str, str] = field(default_factory=dict)
    asset_2_unused_basis_allocation_wallet_order: Mapping[str, Tuple[Account, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.timezone_name, str) or not self.timezone_name.strip():
            raise RP2ValueError("Per-wallet configuration: 'timezone' cannot be empty")
        try:
            _get_iana_timezone(self.timezone_name)
        except RP2ValueError as exc:
            raise RP2ValueError(f"Per-wallet configuration: invalid 'timezone': {exc}") from exc
        if self.unused_basis_allocation_method is not None:
            _check_method_name("unused_basis_allocation_method", self.unused_basis_allocation_method)
        # frozen=True only prevents assigning the fields: a list or dictionary passed by the caller could still be changed afterwards, and the
        # configuration would change with it, skipping these checks. So the wallet orders are copied into tuples, and the per-asset maps into
        # private dictionaries exposed as read-only views. Example: with overrides = {"BTC": "hifo"} passed as
        # asset_2_unused_basis_allocation_method, a later overrides["BTC"] = "lifo" leaves this configuration with hifo for BTC.
        object.__setattr__(self, "unused_basis_allocation_wallet_order", _copy_wallet_order(self.unused_basis_allocation_wallet_order))
        object.__setattr__(self, "asset_2_unused_basis_allocation_method", _copy_method_overrides(self.asset_2_unused_basis_allocation_method))
        object.__setattr__(
            self, "asset_2_unused_basis_allocation_wallet_order", _copy_wallet_order_overrides(self.asset_2_unused_basis_allocation_wallet_order)
        )
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

    # The time zone of timezone_name (checked when the configuration is created).
    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)


def _check_asset(asset: str) -> str:
    if not isinstance(asset, str) or not asset.strip():
        raise RP2TypeError(f"Per-wallet configuration: invalid asset name: {repr(asset)}")
    return asset


def _check_method_name(name: str, method_name: str) -> str:
    if not isinstance(method_name, str) or not method_name.strip():
        raise RP2ValueError(f"Per-wallet configuration: '{name}' must be the name of an accounting method: {repr(method_name)}")
    return method_name


# True for a tuple or a list. It's a separate function so that the caller's variable keeps its declared type (isinstance() would narrow it).
def _is_tuple_or_list(value: object) -> bool:
    return isinstance(value, (tuple, list))


# Copies a wallet order (a tuple or a list of Account) into a tuple, rejecting other elements and duplicates. Other sequences are rejected:
# e.g. the string "Kraken/Bob" instead of (Account("Kraken", "Bob"),).
def _copy_wallet_order(wallet_order: Sequence[Account]) -> Tuple[Account, ...]:
    if not _is_tuple_or_list(wallet_order):
        raise RP2TypeError(f"Per-wallet configuration: wallet order is not a sequence of wallets: {repr(wallet_order)}")
    for account in wallet_order:
        if not isinstance(account, Account):
            raise RP2TypeError(f"Per-wallet configuration: wallet order contains a non-Account element: {account}")
    if len(set(wallet_order)) != len(wallet_order):
        raise RP2ValueError(f"Per-wallet configuration: wallet order contains duplicates: {wallet_order}")
    return tuple(wallet_order)


# Copies the per-asset allocation methods into a private dictionary and returns a read-only view of it.
def _copy_method_overrides(asset_2_method_name: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(asset_2_method_name, Mapping):
        raise RP2TypeError(f"Per-wallet configuration: 'asset_2_unused_basis_allocation_method' is not a mapping: {asset_2_method_name}")
    return MappingProxyType(
        {_check_asset(asset): _check_method_name(f"unused_basis_allocation_method.{asset}", method_name) for asset, method_name in asset_2_method_name.items()}
    )


# Copies the per-asset wallet orders into a private dictionary of tuples and returns a read-only view of it.
def _copy_wallet_order_overrides(asset_2_wallet_order: Mapping[str, Sequence[Account]]) -> Mapping[str, Tuple[Account, ...]]:
    if not isinstance(asset_2_wallet_order, Mapping):
        raise RP2TypeError(f"Per-wallet configuration: 'asset_2_unused_basis_allocation_wallet_order' is not a mapping: {asset_2_wallet_order}")
    return MappingProxyType({_check_asset(asset): _copy_wallet_order(wallet_order) for asset, wallet_order in asset_2_wallet_order.items()})

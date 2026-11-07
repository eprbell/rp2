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

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence

from rp2.rp2_error import RP2TypeError, RP2ValueError


# How lots are pooled when pairing taxable events with acquisitions:
# - UNIVERSAL: all lots of an asset form one pool, regardless of the wallet they are in;
# - PER_WALLET: each wallet (exchange/holder pair) has its own pool, and a sale or transfer can only use lots of its own wallet.
class ApplicationMode(Enum):
    UNIVERSAL = "universal"
    PER_WALLET = "per_wallet"

    @classmethod
    def type_check(cls, name: str, value: "ApplicationMode") -> "ApplicationMode":
        if not isinstance(value, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {value}")
        return value

    @classmethod
    def from_string(cls, value: str) -> "ApplicationMode":
        try:
            return cls(value.strip().lower())
        except ValueError:
            raise RP2ValueError(f"Invalid application mode '{value}': valid values are {', '.join(mode.value for mode in cls)}") from None


# The application modes a country allows from start_year on (until the start year of the next period), and the one used when the user
# doesn't choose.
@dataclass(frozen=True)
class ApplicationPeriod:
    start_year: int
    allowed_modes: FrozenSet[ApplicationMode]
    default_mode: ApplicationMode

    def __post_init__(self) -> None:
        if not isinstance(self.start_year, int) or isinstance(self.start_year, bool):
            raise RP2TypeError(f"Parameter 'start_year' is not an integer: {self.start_year}")
        if not self.allowed_modes:
            raise RP2ValueError(f"Application period starting in {self.start_year} allows no application mode")
        for mode in self.allowed_modes:
            ApplicationMode.type_check("allowed_modes", mode)
        ApplicationMode.type_check("default_mode", self.default_mode)
        if self.default_mode not in self.allowed_modes:
            raise RP2ValueError(f"Application period starting in {self.start_year}: default mode {self.default_mode.value} is not an allowed mode")


# A country's application policy: which application modes are allowed in each tax year, and which one is the default. The first period
# also covers all the years before its start year. Countries define it in AbstractCountry.get_application_policy().
class ApplicationPolicy:
    @classmethod
    def type_check(cls, name: str, instance: "ApplicationPolicy") -> "ApplicationPolicy":
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __init__(self, periods: Sequence[ApplicationPeriod]) -> None:
        if not periods:
            raise RP2ValueError("An application policy needs at least one period")
        for period in periods:
            if not isinstance(period, ApplicationPeriod):
                raise RP2TypeError(f"Application policy contains a non-ApplicationPeriod element: {period}")
        for previous, current in zip(periods, periods[1:]):
            if current.start_year <= previous.start_year:
                raise RP2ValueError(f"Application periods must be sorted by strictly increasing start year: {previous.start_year}, {current.start_year}")
        self.__periods: List[ApplicationPeriod] = list(periods)

    @property
    def periods(self) -> List[ApplicationPeriod]:
        return list(self.__periods)

    # True if some tax year allows per-wallet application (otherwise per-wallet settings in the configuration file are meaningless).
    @property
    def allows_per_wallet(self) -> bool:
        return any(ApplicationMode.PER_WALLET in period.allowed_modes for period in self.__periods)

    def get_period(self, year: int) -> ApplicationPeriod:
        result = self.__periods[0]
        for period in self.__periods:
            if period.start_year <= year:
                result = period
        return result

    # Application mode of each of the given tax years: the user's choice (explicit_mode) if given, otherwise the default of the year's
    # period. A choice that a year doesn't allow is an error, even if other years allow it: e.g. in the US universal application isn't
    # allowed from 2025, so choosing it for a history that reaches 2025 is rejected rather than silently applied to part of it.
    def get_year_2_mode(self, years: Iterable[int], explicit_mode: Optional[ApplicationMode]) -> Dict[int, ApplicationMode]:
        if explicit_mode is not None:
            ApplicationMode.type_check("explicit_mode", explicit_mode)
        result: Dict[int, ApplicationMode] = {}
        for year in sorted(set(years)):
            period = self.get_period(year)
            if explicit_mode is None:
                result[year] = period.default_mode
            elif explicit_mode in period.allowed_modes:
                result[year] = explicit_mode
            else:
                raise RP2ValueError(
                    f"Application mode '{explicit_mode.value}' is not allowed in {year}: allowed modes from {period.start_year} are "
                    f"{', '.join(sorted(mode.value for mode in period.allowed_modes))}"
                )
        return result

    # First year of per-wallet application for the given year-to-mode map, or None if all years are universal. RP2 supports one switch,
    # from universal to per-wallet application, at the start of a policy period: the switch happens at the start of the period of the
    # first per-wallet year (not at the first year with transactions), and all later years must be per-wallet too.
    def get_per_wallet_start_year(self, year_2_mode: Dict[int, ApplicationMode]) -> Optional[int]:
        per_wallet_years = [year for year, mode in year_2_mode.items() if mode == ApplicationMode.PER_WALLET]
        if not per_wallet_years:
            return None
        first_year = min(per_wallet_years)
        later_universal_years = sorted(year for year, mode in year_2_mode.items() if year > first_year and mode == ApplicationMode.UNIVERSAL)
        if later_universal_years:
            raise RP2ValueError(
                f"Switching back from per-wallet to universal application is not supported (per-wallet in {first_year}, universal in "
                f"{later_universal_years[0]})"
            )
        start_year = self.get_period(first_year).start_year
        earlier_per_wallet_start = [year for year in year_2_mode if start_year <= year < first_year]
        if earlier_per_wallet_start:
            raise RP2ValueError(f"Internal error: years {earlier_per_wallet_start} of the period starting in {start_year} have different modes")
        return start_year


# The policy of countries that always use universal application (the default of AbstractCountry.get_application_policy()).
UNIVERSAL_APPLICATION_POLICY = ApplicationPolicy([ApplicationPeriod(1, frozenset({ApplicationMode.UNIVERSAL}), ApplicationMode.UNIVERSAL)])

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

import os
from typing import Set

from rp2.abstract_country import AbstractCountry
from rp2.rp2_error import RP2ValueError
from rp2.rp2_main import rp2_main


# Generic country class
class Generic(AbstractCountry):
    def __init__(self) -> None:
        currency_iso_code = os.environ.get("CURRENCY_CODE")
        if not currency_iso_code:
            raise RP2ValueError("CURRENCY_CODE environment variable not found: it is required to use the generic country plugin")
        long_term_capital_gain_period = os.environ.get("LONG_TERM_CAPITAL_GAINS")
        if not long_term_capital_gain_period:
            raise RP2ValueError("LONG_TERM_CAPITAL_GAINS environment variable not found: it is required to use the generic country plugin")
        try:
            self.__long_term_capital_gain_period = int(long_term_capital_gain_period)
        except (ValueError, TypeError) as exc:
            raise RP2ValueError(
                f"LONG_TERM_CAPITAL_GAINS environment variable has value " f"'{long_term_capital_gain_period}', which is not convertible to integer"
            ) from exc
        if self.__long_term_capital_gain_period < 0:
            raise RP2ValueError(
                f"LONG_TERM_CAPITAL_GAINS environment variable has negative value " f"'{long_term_capital_gain_period}': it should be >= 0 instead"
            )
        super().__init__("generic", currency_iso_code)

    # Measured in days
    def get_long_term_capital_gain_period(self) -> int:
        return self.__long_term_capital_gain_period

    # Default accounting method to use if the user doesn't specify one on the command line
    def get_default_accounting_method(self) -> str:
        return "fifo"

    # Set of accounting methods accepted in the country
    def get_accounting_methods(self) -> Set[str]:
        return {"fifo", "hifo", "lifo", "lofo"}

    # Default set of generators to use if the user doesn't specify them on the command line
    def get_report_generators(self) -> Set[str]:
        return {
            "open_positions",
            "rp2_full_report",
        }

    # Default language to use at report generation if the user doesn't specify it on the command line (in ISO 639-1 format)
    def get_default_generation_language(self) -> str:
        return "en"


# US-specific entry point
def rp2_entry() -> None:
    rp2_main(Generic())

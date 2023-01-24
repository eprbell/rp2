# Copyright 2022 macanudo527
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


import sys
from typing import Set

from rp2.abstract_country import AbstractCountry
from rp2.rp2_main import rp2_main


# JP-specific class
class JP(AbstractCountry):
    def __init__(self) -> None:
        super().__init__("jp", "jpy")

    # Measured in days
    def get_long_term_capital_gain_period(self) -> int:
        # No long-term capital gains in Japan for crypto assets (as of 7/2022)
        return sys.maxsize

    # Default accounting method to use if the user doesn't specify one on the command line
    def get_default_accounting_method(self) -> str:
        # This is incorrect and only a placeholder: we still need to implement Japan-specific accounting methods
        return "fifo"

    # Set of accounting methods accepted in the country
    def get_accounting_methods(self) -> Set[str]:
        # This is incorrect and only a placeholder: we still need to implement Japan-specific accounting methods
        return {"fifo"}

    def get_report_generators(self) -> Set[str]:
        return {
            "open_positions",
            "rp2_full_report",
            "jp.tax_report_jp",
        }

    # Default language to use at report generation if the user doesn't specify it on the command line (in ISO 639-1 format)
    def get_default_generation_language(self) -> str:
        return "ja"


# JP-specific entry point
def rp2_entry() -> None:
    rp2_main(JP())

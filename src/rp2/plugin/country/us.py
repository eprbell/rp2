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


from typing import Set

from rp2.abstract_country import AbstractCountry
from rp2.rp2_main import rp2_main


# US-specific class
class US(AbstractCountry):
    def __init__(self) -> None:
        super().__init__("us", "usd")

    # Measured in days
    def get_long_term_capital_gain_period(self) -> int:
        return 365

    # Default accounting method to use if the user doesn't specify one on the command line
    def get_default_accounting_method(self) -> str:
        return "fifo"

    # Set of accounting methods accepted in the country
    def get_accounting_methods(self) -> Set[str]:
        # Temporarily removed lifo and hifo due to https://github.com/eprbell/rp2/issues/79
        return {"fifo"}

    # Default set of generators to use if the user doesn't specify them on the command line
    def get_report_generators(self) -> Set[str]:
        return {
            "open_positions",
            "rp2_full_report",
            "us.tax_report_us",
        }

    # Default language to use at report generation if the user doesn't specify it on the command line (in ISO 639-1 format)
    def get_default_generation_language(self) -> str:
        return "en"


# US-specific entry point
def rp2_entry() -> None:
    rp2_main(US())

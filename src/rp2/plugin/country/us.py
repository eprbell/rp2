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


from rp2.abstract_country import AbstractCountry
from rp2.rp2_main import rp2_main


# US-specific class
class US(AbstractCountry):
    def __init__(self) -> None:
        super().__init__("us", "usd")

    # Measured in days
    def long_term_capital_gain_period(self) -> int:
        return 365


# US-specific entry point
def rp2_entry() -> None:
    rp2_main(US())

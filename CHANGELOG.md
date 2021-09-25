<!--- Copyright 2021 eprbell --->

<!--- Licensed under the Apache License, Version 2.0 (the "License"); --->
<!--- you may not use this file except in compliance with the License. --->
<!--- You may obtain a copy of the License at --->

<!---     http://www.apache.org/licenses/LICENSE-2.0 --->

<!--- Unless required by applicable law or agreed to in writing, software --->
<!--- distributed under the License is distributed on an "AS IS" BASIS, --->
<!--- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. --->
<!--- See the License for the specific language governing permissions and --->
<!--- limitations under the License. --->

# RP2 Change Log

## v0.8.0
- added new transaction types: AIRDROP, HARDFORK, INTEREST, MINING, STAKING, WAGES. Removed transaction type EARN, which used to encompass all the above types
- revisited output generators: rp2_report was renamed to rp2_full_report and mock_8949_us was renamed to tax_report_us. The tax_report_us plugin now generates one sheet per taxable event type: Airdrops, Capital Gains, Donations, Gifts, Hard Forks, Interest, Investment Expense, Mining, Staking, Wages.
- fixed bug in from/to_year logic: entry sets didn't consider the time filter in certain corner cases

## v0.7.3
- Added from/to_year command line option

## v0.7.2
- Minor fixes related to Pypi package distribution and upload

## v0.7.1
- Minor fixes related to Pypi package distribution and upload

## v0.7.0
* First version uploaded to Pypi
* Added pre-commit hooks
* Added bandit security checks
* Major revision of user and developer documentation
* Fixed lint errors
* Various bug fixes and improvements

## v0.6.0
* First version tracked in change log
* Added Python packaging support
* Switched to high-precision math (decimal.Decimal)
* Finished documentation (except FAQs)
* Added bumpversion
* Various bug fixes and improvements

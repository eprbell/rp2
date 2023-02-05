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

## 1.4.1
* added new RP2RuntimeError to handle non-recoverable problems without using Exception

## 1.4.0
* added support for Japan
* temporarily disable LIFO and HIFO (see https://github.com/eprbell/rp2/issues/79)
* documentation improvements

## 1.3.1
* fixed #77: accounting engine AVLTree keys didn't normalize timezones, which caused a rare but obscure bug in certain cases
* added debug log for progress of tax engine during lot accounting. This should make it much easier to debug certain user data errors, such as "Total in-transaction crypto value < total taxable crypto value"
* fixed tax_report_us plugin bug: investment expenses sheet was resized only with number of move transactions (ignoring number of fee ones): this caused a row overflow when generating tax_report_us output under certain conditions
* minor documentation improvements

## 1.3.0
* configuration files are no longer expressed in JSON format: they now use the INI format. Old JSON-format configuration files can be converted automatically to the new INI format with the following command: rp2_config <json_config>

## 1.2.0
* added support for [switching accounting methods year over year](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#can-i-change-accounting-method)
* added support for simplified accounting method plugin creation. With this new infrastructure a new accounting method can be added by defining just two small methods. See [documentation](https://github.com/eprbell/rp2/blob/main/README.dev.md#simplified-procedure)
* updated documentation with new accounting method features

## 1.1.0
* fixed 2 bugs in HIFO plugin: see #74 for details. If you're using HIFO, be sure to upgrade to this or later version.
* refactored classic computer science data structures in separate Prezzemolo library
* added FAQs and tweaked documentation

## 1.0.9
* revised and improved all documentation
* added FAQs
* minor fixes

## 1.0.8
* added generated report localization infrastructure: it's now possible to generate taxes for any country in any language (e.g. Japanese taxes in French). See README.dev.md for details
* added -g command line option to select the language to use for generated reports
* default generators are now specified in the country plugin (so that each country can select their allowed generators)
* allowed accounting methods are now specified in the country plugin (so that each country can select their allowed accounting methods)
* minor fixes in the Legend generation code
* updated documentation with new Localization section and updated Country and Report plugin sections with latest API changes
* added user FAQs

## 1.0.6
* added HIFO accounting method plugin
* updated documentation and FAQs

## 1.0.5
* added country plugin for Japan
* small improvements in documentation

## 1.0.4
* fixed issue #39: if ODS file had numeric unique_id it tripped the type checking system
* added support for generators section in configuration: this allows users to select which generator plugins to run. Also deprecated -l/--plugin CLI options
* updated documentation with new generators section description
* added FAQ

## 1.0.3
* minor improvements

## 1.0.2
* new open positions plugin, showing a variety of information on unrealized gains and losses (https://github.com/eprbell/rp2/pull/35)
* minor improvements to documentation

## 1.0.0
* Tax season is over: time for RP2 to hit v1.0.0! RP2 (and DaLI) gained a lot of users and traction in less than one year of existence (https://star-history.com/#eprbell/rp2&Date). During this time lots of bugs were fixed and features added. Thanks to everybody who engaged with PRs, issues, discussions and DMs.

## 0.9.31
* fixed a bug in rp2_full_report generator reported in #31: in out-transactions if crypto_fee == 0 and fiat_fee > 0, the fiat fee was reported as zero (but this affected only the output, not the tax calculation which was correct)
* added some user FAQs

## 0.9.30
* minor improvements to documentation

## 0.9.29
* various improvements to documentation

## 0.9.28
* RP2 logo worked on Github, but not on Pypi: fixed

## 0.9.27
* added RP2 logo to readme.md
* improved an error message when disposed-of crypto is greater than acquired crypto

## 0.9.26
* removed requirements.txt: now using dev section in setup.cfg, which avoids duplication of information
* added FAQ on Excel being unable to open some RP2-generated ODS files

## v0.9.25
* added initial version of developer FAQ document: https://github.com/eprbell/rp2/blob/main/docs/developer_faq.md
* minor refactoring edits

## v0.9.24
* added crypto_fee to InTransactions (by popular demand): previously in-transaction fee would only accept fees in fiat, but in certain situations fee is paid in crypto (e.g. crypto conversion, etc.). With this fix, either crypto_fee or fiat fee can be assigned (not both). If fiat_fee is assigned, crypto_fee is set to 0. If crypto_fee is assigned, fiat_fee is set to crypto_fee * spot_price. The reason for this behavior is that if the fee is paid in fiat, then no crypto is used for the fee, but if the fee is paid in crypto, then its converted fiat value is needed to compute taxes. Note that RP2 models a non-zero crypto_fee with a separate fee-typed out-transaction.
* added new unit test for the new InTransaction crypto_fee (input/test_data4.ods)
* updated documentation to reflect new features from this release
* added a new FAQ on crypto rewards and reworded various answers.

## v0.9.23
* added fee-only transactions: this type of transactions occur in certain DeFi scenarios (see [relevant FAQ](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-fee-only-defi-transactions) for more)
* added documentation of transparent computation, including one new FAQ on how to verify RP2 tax computation results: https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-verify-that-tax-computation-is-correct
* minor edits to documentation

## v0.9.19
* added new FAQs
* added pointers in documentation to DaLI, the data loader and input generator for RP2: https://github.com/eprbell/dali-rp2

## v0.9.18
* improved error message when ods_parser._process_constructor_argument_pack tries to parse a numeric argument and fails because the value is not numeric

## v0.9.17
* added an extra check in IntraTransaction constructor: if spot_price == 0 and fee > 0 then raise an error (because the fiat value of the fee cannot be computed)
* minor edits to documentation

## v0.9.16
* in the tax_report_us output the following tabs had the description field mistakenly hidden: Airdrops, Income, Interest, Mining, Staking, Wages. All other tabs didn't have the problem. The hidden field is now visible
* the unique_id field (containing hash or exchange-specific id) is now generated in the output files (both tax_report_us and rp2_full_report)

## v0.9.15
* added Income sheet to plugin ODS template (needed by tax_report_us generator to support the new Income InTransaction type)

## v0.9.14
* added support for Income-type InTransaction (to capture misc income like Coinbase Earn)
* renamed old unique_id field to internal_id and added a new unique_id field to all transactions, which captures hash for IntraTransactions and exchange-specific unique ids for In/OutTransactions
* updated documentation to reflect latest changes
* minor fixes and refactoring

## v0.9.13
* Add py.typed to rp2 package to indicate type hint support.

## v0.9.12
* Added support for multiple logger names (e.g. plugins can use different logger names than core RP2 code).

## v0.9.11
* refactored to_string() method to be top-level, so that it's easier to use in external projects.
* added [RP2 Ecosystem](https://github.com/eprbell/rp2/tree/main/README.md#rp2-ecosystem) paragraph to README.md
* added a few more FAQs to user frequently asked questions document
* improved CLI description
* minor fixes

## v0.9.10
* fixed [issue #6](https://github.com/eprbell/rp2/issues/6): OUT transaction fee is now a deduction as per https://www.irs.gov/publications/p544 and https://taxbit.com/cryptocurrency-tax-guide (previously it was considered part of proceeds and therefore taxed)
* restructured User FAQ document
* added several questions to User FAQ document (many of them DeFi-related)
* various edits and improvements throughout entire documentation

## v0.9.9
* add DONATE and GIFT-typed InTransactions
* changed Legend sheet to include time filter information
* updated documentation to reflect changes in this version

## v0.9.8
* added hyperlinks to rp2_full_report output:
  * taxable events and acquired lots in tax sheet are now hyperlinked to their definition line in the in-out sheet. In LibreOffice, CTRL-click on them to jump to the target (on Mac Command-click)
  * summary lines in the Summary sheet are now hyperlinked to the first line of the given year in the tax sheet
* modified time filter CLI options (-f and -t) to accept a full date (YYYY-MM-DD): so it's now possible to filter transactions before and after a given day
* major refactoring: renamed "from lot" and "in lot" to "acquired lot" throughout identifiers, strings, templates, documentation, etc.
* updated documentation to reflect changes in this version

## v0.9.7
* added profiler instrumentation
* added large input test and refactored ODS output test
* removed rmtree("output") from test_ods_output_diff.py: it modifies the file system, which can cause problems when running tests in parallel (currently not enabled, but that may change in the future).
* minor fixes

## v0.9.6
* fixed a bug in timestamp check: in and out lots were not allowed to have the same timestamp, but in certain scenarios it could happen (e.g. high-frequency trading)
* fixed a subtle corner-case bug in LIFO, which caused the first gain/loss pair to be incorrect: the minimal input that reproduced the bug is now captured in one of the tests (test_data2.ods, sheet B1). This ensures there will not be a regression.
* disable a link check in user faq: the link was failing the check (incorrectly) on Github actions

## v0.9.5
* added new LIFO tests
* minor fixes

## v0.9.4
* added accounting-method programmable plugin infrastructure: by subclassing AbstractAccountingMethod it's now possible to add support for a new accounting method (previously only FIFO was hard-coded in)
* added accounting-method plugins: FIFO, LIFO
* added accounting-method-specific tests, plus additional tests of internal classes (both new and old)
* Added Legend sheet to tax_report_us output
* updated documentation to reflect changes in this version
* minor fixes

## v0.9.3
* added country-specific programmable plugin infrastructure: by subclassing AbstractCountry it's now possible to add support for a new country (currently only US is supported)
* abstracted out currency from APIs and code in general: references to "usd" have been changed to "fiat"
* updated documentation to reflect changes in this version

## v0.9.2
* Verified software is up to date for FY 2021
* Wrote several answers in User FAQ document
* Minor fixes

## v0.8.1
* Added several new tests (from/to_year command line option variations and new transaction types)
* Reworked time filter logic to fix two bugs related to -f and -t options:
  * with time filtering on, running sums reflected only filtered transactions, instead of all transactions (in other words, running sums should not be affected by filtering)
  * with time filtering on, number of fractions reflected also fractions with year higher than time filter
  * with time filtering on, sold lot percentages would be shown incorrectly in some cases
* Updated documentation: various fixes and improvements

## v0.8.0
* added new transaction types: AIRDROP, HARDFORK, INTEREST, MINING, STAKING, WAGES. Removed transaction type EARN, which used to encompass all the above types
* revisited output generators: rp2_report was renamed to rp2_full_report and mock_8949_us was renamed to tax_report_us. The tax_report_us plugin now generates one sheet per taxable event type: Airdrops, Capital Gains, Donations, Gifts, Hard Forks, Interest, Investment Expense, Mining, Staking, Wages.
* fixed bug in from/to_year logic: entry sets didn't consider the time filter in certain corner cases
* updated documentation to reflect above changes

## v0.7.3
* Added from/to_year command line option

## v0.7.2
* Minor fixes related to Pypi package distribution and upload

## v0.7.1
* Minor fixes related to Pypi package distribution and upload

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

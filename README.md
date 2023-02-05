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

![RP2 Logo](https://raw.githubusercontent.com/eprbell/rp2/main/docs/images/rp2_header.png)

# RP2 v1.4.1
Privacy-focused, free, powerful crypto tax calculator

[![Static Analysis / Main Branch](https://github.com/eprbell/rp2/actions/workflows/static_analysis.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/static_analysis.yml)
[![Documentation Check / Main Branch](https://github.com/eprbell/rp2/actions/workflows/documentation_check.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/documentation_check.yml)
[![Unix Unit Tests / Main Branch](https://github.com/eprbell/rp2/actions/workflows/unix_unit_tests.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/unix_unit_tests.yml)
[![Windows Unit Tests / Main Branch](https://github.com/eprbell/rp2/actions/workflows/windows_unit_tests.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/windows_unit_tests.yml)
[![CodeQL/Main Branch](https://github.com/eprbell/rp2/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/codeql-analysis.yml)

[![Tweet](https://img.shields.io/twitter/url/http/shields.io.svg?style=social)](https://twitter.com/intent/tweet?text=I%20use%20RP2,%20the%20privacy-focused,%20open%20source,%20free,%20non-commercial%20crypto%20tax%20calculator&url=https://github.com/eprbell/rp2/?anything)

## Table of Contents
* **[Introduction](https://github.com/eprbell/rp2/blob/main/README.md#introduction)**
  * [How RP2 Operates](https://github.com/eprbell/rp2/blob/main/README.md#how-rp2-operates)
* **[License](https://github.com/eprbell/rp2/blob/main/README.md#license)**
* **[Download](https://github.com/eprbell/rp2/blob/main/README.md#download)**
* **[Installation](https://github.com/eprbell/rp2/blob/main/README.md#installation)**
  * [Ubuntu Linux](https://github.com/eprbell/rp2/blob/main/README.md#installation-on-ubuntu-linux)
  * [macOS](https://github.com/eprbell/rp2/blob/main/README.md#installation-on-macos)
  * [Windows 10](https://github.com/eprbell/rp2/blob/main/README.md#installation-on-windows-10)
  * [Other Unix-like Systems](https://github.com/eprbell/rp2/blob/main/README.md#installation-on-other-unix-like-systems)
* **[Running](https://github.com/eprbell/rp2/blob/main/README.md#running)**
* **[Input and Output Files](https://github.com/eprbell/rp2/blob/main/README.md#input-and-output-files)**
* **[RP2 Ecosystem](https://github.com/eprbell/rp2/blob/main/README.md#rp2-ecosystem)**
  * [List of Ecosystem Projects](https://github.com/eprbell/rp2/blob/main/README.md#list-of-ecosystem-projects)
* **[Reporting Bugs](https://github.com/eprbell/rp2/blob/main/README.md#reporting-bugs)**
* **[Contributing](https://github.com/eprbell/rp2/blob/main/README.md#contributing)**
* **[Developer Documentation](https://github.com/eprbell/rp2/blob/main/README.md#developer-documentation)**
* **[Frequently Asked Questions](https://github.com/eprbell/rp2/blob/main/README.md#frequently-asked-questions)**
* **[Change Log](https://github.com/eprbell/rp2/blob/main/README.md#change-log)**

## Introduction
[RP2](https://github.com/eprbell/rp2) is a privacy-focused, free, non-commercial, open-source cryptocurrency tax calculator. Preparing crypto taxes can be a daunting and error-prone task, especially if multiple transactions, coins, exchanges and wallets are involved. This task could be delegated to a crypto tax preparation service, but many crypto users value their privacy and prefer not to send their transaction information to third parties unnecessarily. Additionally, many of these services cost money. RP2 solves all of these problems:
* it manages the complexity related to coin flows and tax calculation and it generates [reports that accountants can understand](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#advisor-friendly-report-tax-report-us-output) (in the format of form 8949, for the US case), even if they are not cryptocurrency experts;
* it prioritizes user privacy by storing crypto transactions and tax results on the user's computer and not sending them anywhere else;
* it's 100% free, open-source and non-commercial.

This means that with RP2 there are no transaction limits, no premium versions, no payment requests, no personal data sent to a server (at risk of being hacked), no account creation, no unauditable source code.

Another unique advantage of RP2 is [transparent computation](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#transparent-computation-rp2-full-report-output): it generates full computation details for every lot fraction, so that it's possible to:
* verify step-by-step how RP2 reaches the final result;
* track down every lot fraction and its accounting details, in case of an audit.

RP2 currently only supports the [FIFO](https://www.investopedia.com/terms/f/fifo.asp) accounting method for US taxes. Only the Total Average Method is supported for Japanese taxes.<!--- [LIFO](https://www.investopedia.com/terms/l/lifo.asp) and [HIFO](https://www.investopedia.com/terms/h/hifo.asp) accounting methods. It also supports [switching accounting methods](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#can-i-change-accounting-method) from one year to the next. --->

RP2 reads a configuration file and an input spreadsheet containing crypto transactions. These [input files](https://github.com/eprbell/rp2/blob/main/docs/input_files.md) can be generated either manually or automatically using [DaLI](https://github.com/eprbell/dali-rp2), a RP2 data loader and input generator (which is also privacy-focused, free, non-commercial and open-source). After parsing the input RP2 uses high-precision math to calculate long/short term capital gains, cost bases, balances, average price, in/out lot relationships/fractions, and finally it generates [output files](https://github.com/eprbell/rp2/blob/main/docs/output_files.md).

RP2 has a programmable plugin architecture for [output generators](https://github.com/eprbell/rp2/tree/main/README.dev.md#adding-a-new-report-generator), [accounting methods](https://github.com/eprbell/rp2/tree/main/README.dev.md#adding-a-new-accounting-method) and [countries](https://github.com/eprbell/rp2/tree/main/README.dev.md#adding-support-for-a-new-country). The builtin output generator plugins are in part generic and in part US-specific, but RP2's architecture makes it possible to contribute additional generators for different countries or for different US-based cases. The builtin output generator plugins are:
* tax_report_us: generates a US-specific tax report meant to be read by tax preparers (in the format of form 8949);
* rp2_full_report: generates a comprehensive report (valid for any country), with complete transaction history, lot relationships/fractions and computation details;
* open_positions: geterates a report (valid for any country) on assets with non-zero crypto balance: unrealized gains / losses, portfolio weighting, and more.

RP2 has extensive [unit test](https://github.com/eprbell/rp2/tree/main/tests/) coverage to reduce the risk of regression.

**IMPORTANT DISCLAIMERS**:
* RP2 offers no guarantee of correctness (read the [license](https://github.com/eprbell/rp2/tree/main/LICENSE)): always verify results with the help of a tax professional.
* The author of RP2 is not a tax professional, but has used RP2 personally for a few years.

### How RP2 Operates
RP2 has been designed to have expressive primitives that can be used as building blocks for most tax scenarios: complex tax events can be described with patterns, built on top of these primitives (see the [FAQ list](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#tax-scenarios) for examples).

RP2 treats virtual currency as property for tax purposes, as per [IRS Virtual Currency Guidance](https://www.irs.gov/newsroom/irs-reminds-taxpayers-to-report-virtual-currency-transactions).

RP2 supports the FIFO accounting method: however, in and out lots typically don't have matching amounts, so RP2 fractions them, maps in/out lot fractions and computes the resulting cost basis and capital gains for each lot fraction.

RP2 groups lot fractions into the following taxable event categories, each of which has a [specific tax treatment](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#which-crypto-tax-forms-to-file):
* [AIRDROP](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-airdrops): gains from airdrops;
* [DONATE](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-donations): donations to charitable organizations;
* [FEE](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#hhow-to-handle-fee-only-defi-transactions): fee-only transaction, used in some DeFi scenarios (e.g. gas fee for running certain smart contracts);
* [GIFT](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-gifts): gifts to parties who are not charitable organizations (not tax-deductible).
* [HARDFORK](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-hard-forks): gains from hard forks;
* [INCOME](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-miscellaneous-crypto-income): gains from miscellaneous income (e.g. Coinbase Earn);
* [INTEREST](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-crypto-interest): gains from interest;
* [MINING](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-income-from-mining): gains from mining;
* [MOVE](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-a-transfer-of-funds-from-a-wallet-or-exchange-to-another): the fee for moving currency between two accounts controlled by the same owner;
* SELL: specifically, sale and [conversion of a cryptocurrency to another](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-conversion-of-a-cryptocurrency-to-another). RP2 splits them in two subcategories:
  * long-term capital gains (if supported by the country plugin: e.g. in the US it's 1 year or more), or
  * short-term capital gains otherwise;
* [STAKING](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-income-from-staking): gains from staking;
* [WAGES](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-income-from-crypto-wages): income from crypto wages.

For each of these categories RP2 generates an output spreadsheet with transaction details and computed gains/losses (see [Input and Output Files](https://github.com/eprbell/rp2/blob/main/README.md#input-and-output-files) for more details). Users can give this output to their tax preparer with the rest of their tax documentation (see also FAQ on [which tax forms to file](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#which-crypto-tax-forms-to-file)). Note that buying cryptocurrency using fiat currency is not a taxable event.

**NOTE ON NFTs**: Read the [FAQ on NFTs](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md#how-to-handle-nfts) to learn about how RP2 treats NFTs.

## License
RP2 is released under the terms of Apache License Version 2.0. For more information see [LICENSE](https://github.com/eprbell/rp2/tree/main/LICENSE) or <http://www.apache.org/licenses/LICENSE-2.0>.

## Download
The latest version of RP2 can be downloaded at: <https://pypi.org/project/rp2/>

## Installation
RP2 has been tested on Ubuntu Linux, macOS and Windows 10 but it should work on all systems that have Python version 3.7.0 or greater.

### Installation on Ubuntu Linux
Open a terminal window and enter the following commands:
```
sudo apt-get update
sudo apt-get install python3 python3-pip
```

Then install RP2:
```
pip install rp2
```
### Installation on macOS
First make sure [Homebrew](https://brew.sh) is installed, then open a terminal window and enter the following commands:
```
brew update
brew install python3
```

Then install RP2:
```
pip install rp2
```
### Installation on Windows 10
First make sure [Python](https://python.org) 3.7 or greater is installed (in the Python installer window be sure to click on "Add Python to PATH"), then open a PowerShell window and enter the following:
```
pip install rp2
```

### Installation on Other Unix-like Systems
* install python 3.7 or greater
* install pip3
* `pip install rp2`

## Running
RP2 requires two files as input:
* an ODS-format spreadsheet, containing crypto transactions (ODS-format files can be opened and edited with [LibreOffice](https://www.libreoffice.org/) and many other spreadsheet applications);
* a config file, describing the format of the spreadsheet file: what value each column corresponds to (e.g. timestamp, amount, exchange, fee, etc.) and which cryptocurrencies and exchanges to expect.

The two input files can either:
* be generated automatically using [DaLI](https://github.com/eprbell/dali-rp2), the data loader and input generator for RP2, or
* be prepared manually by the user.

The formats of these files are described in detail in the [Input Files](https://github.com/eprbell/rp2/blob/main/docs/input_files.md) section of the documentation.

Examples of an input spreadsheet and its respective config file:
* [input/crypto_example.ods](https://github.com/eprbell/rp2/tree/main/input/crypto_example.ods)
* [config/crypto_example.ini](https://github.com/eprbell/rp2/tree/main/config/crypto_example.ini).

After reading the input files, RP2 computes taxes and generates output files, which contain information on long/short capital gains, cost bases, balances, average price, in/out lot relationships and fractions, etc. They are described in detail in the [Output Files](https://github.com/eprbell/rp2/blob/main/docs/output_files.md) section of the documentation.

To try RP2 with example files, download [crypto_example.ods](https://github.com/eprbell/rp2/tree/main/input/crypto_example.ods) and [crypto_example.ini](https://github.com/eprbell/rp2/tree/main/config/crypto_example.ini). Let's call `<download_directory>` the location of the downloaded files.

The RP2 executable is country-dependent: `rp2_<country_code>`, where country code is a [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2), 2-letter identifier (e.g. `rp2_us`, `rp2_jp`, etc).

To generate US tax output for the example files open a terminal window (or PowerShell if on Windows) and enter the following commands:
  ```
  cd <download_directory>
  rp2_us -o output -p crypto_example_ crypto_example.ini crypto_example.ods
  ```
Results are generated in the `output` directory and logs are stored in the `log` directory.

<!--- The `-m` option is particularly important, because is selects the accounting method: `rp2_us` supports FIFO, LIFO and HIFO (if `-m` is not specified it defaults to FIFO). --->

To print full command usage information for the `rp2_us` command:
  ```
  rp2_us --help
  ```

## Input and Output Files
Read the [input files](https://github.com/eprbell/rp2/blob/main/docs/input_files.md) and [output files](https://github.com/eprbell/rp2/blob/main/docs/output_files.md) documentation.

## RP2 Ecosystem
This is a call for coders: come and help us expand RP2's functionality!

RP2 is the first component of what could be a powerful, community-driven suite of open-source, crypto tax software. It is intended as the core of a larger project ecosystem, maintained by the community. These projects can extend RP2's capability, usefulness and ease of use in new ways. For example:
* [DaLI data loader plugins](https://github.com/eprbell/dali-rp2/blob/main/README.dev.md#dali-internals): add support for more exchanges and wallets (via REST API and/or CSV files). [Dali](https://github.com/eprbell/dali-rp2), the RP2 data loader, uses them to generate an input ODS file and a config file that can be fed directly to RP2;
* [RP2 plugins](https://github.com/eprbell/rp2/tree/main/README.dev.md#plugin-development): RP2 can be expanded via its programmable plugin architecture, which enables support for new output generators, countries and accounting methods;
* RP2 GUI: make RP2 more user-friendly and accessible to people who are not familiar with the CLI;
* RP2 high-level interface: RP2 captures complex tax events using a few powerful, low-level primitives, aggregated in patterns. A higher level tool, might abstract out these patterns and present them to the user in a friendlier way (for example it may capture a complex concept like DeFi bridging as a primitive, rather than a pattern);
* more...

**Important note**: any RP2 ecosystem project must make user privacy its first priority.

If you'd like to start an ecosystem project, please open an [issue](https://github.com/eprbell/rp2/issues) to let the RP2 community know.

### List of Ecosystem Projects
Here's the current list of projects in the RP2 ecosystem:
* [DaLI](https://github.com/eprbell/dali-rp2): data loader and input generator for RP2 (https://github.com/eprbell/rp2).

## Reporting Bugs
Read the [Contributing](https://github.com/eprbell/rp2/tree/main/CONTRIBUTING.md#reporting-bugs) document.

## Contributing
Read the [Contributing](https://github.com/eprbell/rp2/tree/main/CONTRIBUTING.md) document.

## Developer Documentation
Read the [developer documentation](https://github.com/eprbell/rp2/tree/main/README.dev.md).

## Frequently Asked Questions
Read the [user FAQ list](https://github.com/eprbell/rp2/blob/main/docs/user_faq.md) and the [developer FAQ list](https://github.com/eprbell/rp2/blob/main/docs/developer_faq.md).

## Change Log
Read the [Change Log](https://github.com/eprbell/rp2/tree/main/CHANGELOG.md) document.

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

![RP2 Logo](https://github.com/eprbell/rp2/blob/main/docs/RP2_logo.png)

# RP2 v0.9.27
[![Static Analysis / Main Branch](https://github.com/eprbell/rp2/actions/workflows/static_analysis.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/static_analysis.yml)
[![Documentation Check / Main Branch](https://github.com/eprbell/rp2/actions/workflows/documentation_check.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/documentation_check.yml)
[![Unix Unit Tests / Main Branch](https://github.com/eprbell/rp2/actions/workflows/unix_unit_tests.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/unix_unit_tests.yml)
[![Windows Unit Tests / Main Branch](https://github.com/eprbell/rp2/actions/workflows/windows_unit_tests.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/windows_unit_tests.yml)
[![CodeQL/Main Branch](https://github.com/eprbell/rp2/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/codeql-analysis.yml)

## Table of Contents
* **[Introduction](https://github.com/eprbell/rp2/tree/main/README.md#introduction)**
  * [How RP2 Operates](https://github.com/eprbell/rp2/tree/main/README.md#how-rp2-operates)
* **[License](https://github.com/eprbell/rp2/tree/main/README.md#license)**
* **[Download](https://github.com/eprbell/rp2/tree/main/README.md#download)**
* **[Installation](https://github.com/eprbell/rp2/tree/main/README.md#installation)**
  * [Ubuntu Linux](https://github.com/eprbell/rp2/tree/main/README.md#installation-on-ubuntu-linux)
  * [macOS](https://github.com/eprbell/rp2/tree/main/README.md#installation-on-macos)
  * [Windows 10](https://github.com/eprbell/rp2/tree/main/README.md#installation-on-windows-10)
  * [Other Unix-like Systems](https://github.com/eprbell/rp2/tree/main/README.md#installation-on-other-unix-like-systems)
* **[Running](https://github.com/eprbell/rp2/tree/main/README.md#running)**
* **[Input and Output Files](https://github.com/eprbell/rp2/tree/main/README.md#input-and-output-files)**
* **[RP2 Ecosystem](https://github.com/eprbell/rp2/tree/main/README.md#rp2-ecosystem)**
  * [List of Ecosystem Projects](https://github.com/eprbell/rp2/tree/main/README.md#list-of-ecosystem-projects)
* **[Reporting Bugs](https://github.com/eprbell/rp2/tree/main/README.md#reporting-bugs)**
* **[Contributing](https://github.com/eprbell/rp2/tree/main/README.md#contributing)**
* **[Developer Documentation](https://github.com/eprbell/rp2/tree/main/README.md#developer-documentation)**
* **[Frequently Asked Questions](https://github.com/eprbell/rp2/tree/main/README.md#frequently-asked-questions)**
* **[Change Log](https://github.com/eprbell/rp2/tree/main/README.md#change-log)**

## Introduction
[RP2](https://pypi.org/project/rp2/) is a privacy-focused, free, [open-source](https://github.com/eprbell/rp2) US cryptocurrency tax calculator, that is up to date for Fiscal Year 2021. Preparing crypto taxes can be a daunting and error-prone task, especially if multiple transactions, coins, exchanges and wallets are involved. This task could be delegated to a crypto tax preparation service, but many crypto users value their privacy and prefer not to send their transaction information to third parties unnecessarily. Additionally, many of these services cost money. RP2 solves all of these problems:
* it manages the complexity related to coin flows and tax calculation and it generates [data that accountants can understand](https://github.com/eprbell/rp2/tree/main/docs/output_files.md#advisor-friendly-report-tax-report-us-output) (in the format of form 8949), even if they are not cryptocurrency experts;
* it prioritizes user privacy by storing crypto transactions and tax results on the user's computer and not sending them anywhere else;
* it's free and open-source.

Another unique advantage of RP2 is [transparent computation](https://github.com/eprbell/rp2/tree/main/docs/output_files.md#transparent-computation-rp2-full-report-output): it generates full computation details for every lot fraction, so that it's possible to verify step-by-step how RP2 reaches the final result.

RP2 supports the [FIFO](https://www.investopedia.com/terms/f/fifo.asp) and [LIFO](https://www.investopedia.com/terms/l/lifo.asp) accounting methods, to help minimize the amount due.

It reads in a spreadsheet containing crypto transactions. The spreadsheet can be generated either manually or automatically using [DaLI](https://pypi.org/project/dali-rp2), a RP2 data loader and input generator (which is also privacy-focused, free and [open-source](https://github.com/eprbell/dali-rp2)). After parsing the input RP2 uses high-precision math to calculate long/short term capital gains, cost bases, balances, average price, in/out lot relationships/fractions, and finally it generates output spreadsheets.

RP2 has a programmable plugin architecture for [output generators](https://github.com/eprbell/rp2/tree/main/README.dev.md#adding-a-new-report-generator), [accounting methods](https://github.com/eprbell/rp2/tree/main/README.dev.md#adding-a-new-accounting-method) and [countries](https://github.com/eprbell/rp2/tree/main/README.dev.md#adding-support-for-a-new-country). The output generator builtin plugins are US-specific, but RP2's architecture makes it possible to contribute additional generators for different countries or for different US-based cases. The builtin generator plugins are:
* tax_report_us: generates a tax report meant to be read by tax preparers (in the format of form 8949);
* rp2_full_report: generates a comprehensive report, with complete transaction history, lot relationships/fractions and computation details.

RP2 has extensive [unit test](https://github.com/eprbell/rp2/tree/main/tests/) coverage to reduce the risk of regression.

**IMPORTANT DISCLAIMERS**:
* RP2 offers no guarantee of correctness (read the [license](https://github.com/eprbell/rp2/tree/main/LICENSE)): always verify results with the help of a tax professional.
* The author of RP2 is not a tax professional, but has used RP2 personally for a few years.

### How RP2 Operates
RP2's has been designed with expressive primitives that can be used as building blocks for most tax scenarios: complex tax events can be described with patterns, built using these primitives (see the [FAQ list](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#tax-scenarios) for examples).

RP2 treats virtual currency as property for tax purposes, as per [IRS Virtual Currency Guidance](https://www.irs.gov/newsroom/irs-reminds-taxpayers-to-report-virtual-currency-transactions).

RP2 supports the FIFO and LIFO accounting methods: however, in and out lots typically don't have matching amounts, so RP2 fractions them, maps in/out lot fractions and computes the resulting cost basis and capital gains for each lot fraction.

RP2 groups lot fractions into the following taxable event categories, each of which has a [specific tax treatment](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#which-crypto-tax-forms-to-file):
* [AIRDROP](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-airdrops): gains from airdrops;
* DONATE: donations to charitable organizations;
* [FEE](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#hhow-to-handle-fee-only-defi-transactions): fee-only transaction, used in some DeFi scenarios (e.g. gas fee for running certain smart contracts);
* GIFT: gifts to parties who are not charitable organizations (not tax-deductible).
* [HARDFORK](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-hard-forks): gains from hard forks;
* INCOME: gains from miscellaneous income (e.g. Coinbase Earn);
* INTEREST: gains from interest;
* [MINING](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-income-from-mining): gains from mining;
* MOVE: the fee for moving currency between two accounts controlled by the same owner;
* SELL: specifically, sale and [exchange of one cryptocurrency for another](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-conversion-of-a-cryptocurrency-to-another). RP2 splits them in two subcategories:
  * long-term capital gains, if the lot was held for more than 1 year, or
  * short-term capital gains otherwise;
* [STAKING](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-income-from-staking): gains from staking;
* WAGES: income from crypto wages.

For each of these categories RP2 generates an output spreadsheet with transaction details and computed gains/losses (see [Input and Output Files](https://github.com/eprbell/rp2/tree/main/README.md#input-and-output-files) for more details). Users can give this output to their tax preparer with the rest of their tax documentation (see also FAQ on [which tax forms to file](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#which-crypto-tax-forms-to-file)). Note that buying cryptocurrency using fiat currency is not a taxable event.

**NOTE ON NFTs**: Read the [FAQ on NFTs](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-nfts) to learn about how RP2 treats NFTs.

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
* a JSON config file, describing the format of the spreadsheet file: what value each column corresponds to (e.g. timestamp, amount, exchange, fee, etc.) and which cryptocurrencies and exchanges to expect.

The two input files can either:
* be generated automatically using [DaLI](https://pypi.org/project/dali-rp2/), the data loader and input generator for RP2, or
* be prepared manually by the user.

The formats of these files are described in detail in the [Input Files](https://github.com/eprbell/rp2/tree/main/docs/input_files.md) section of the documentation.

Examples of an input spreadsheet and its respective config file:
* [input/crypto_example.ods](https://github.com/eprbell/rp2/tree/main/input/crypto_example.ods)
* [config/crypto_example.config](https://github.com/eprbell/rp2/tree/main/config/crypto_example.config) (if desired, this config file can be used as boilerplate).

After reading the input files, RP2 computes taxes and generates output files, which contain information on long/short capital gains, cost bases, balances, average price, in/out lot relationships and fractions. They are described in detail in the [Output Files](https://github.com/eprbell/rp2/tree/main/docs/output_files.md) section of the documentation.

To try RP2 with example files, download [crypto_example.ods](https://github.com/eprbell/rp2/tree/main/input/crypto_example.ods) and [crypto_example.config](https://github.com/eprbell/rp2/tree/main/config/crypto_example.config). Let's call `<download_directory>` the location of the downloaded files.

To generate output for the example files open a terminal window (or PowerShell if on Windows) and enter the following commands:
  ```
  cd <download_directory>
  rp2_us -m fifo -o output -p crypto_example_ crypto_example.config crypto_example.ods
  ```
Results are generated in the `output` directory and logs are stored in the `log` directory.

The `-m` option is particularly important, because is selects the accounting method: RP2 supports FIFO and LIFO (if `-m` is not specified it defaults to FIFO).

To print full command usage information for the `rp2_us` command:
  ```
  rp2_us --help
  ```

## Input and Output Files
Read the [input files](https://github.com/eprbell/rp2/tree/main/docs/input_files.md) and [output files](https://github.com/eprbell/rp2/tree/main/docs/output_files.md) documentation.

## RP2 Ecosystem
This is a call for projects: come and help us expand RP2's functionality!

RP2 is the first component of what could be a powerful, community-driven suite of open-source, crypto tax software. It is intended as the core of a larger project ecosystem, maintained by the community. These projects can extend RP2's capability, usefulness and ease of use in new ways, for example:
* RP2 [data loader plugins](https://github.com/eprbell/dali-rp2/blob/main/README.dev.md#dali-internals): add support for more exchanges and wallets (via REST API and/or CSV files). [Dali](https://github.com/eprbell/dali-rp2), the RP2 data loader uses them to generate an input ODS file and a config file that can be fed directly to RP2;
* RP2 GUI: make RP2 more user-friendly and accessible to people who are not familiar with the CLI;
* RP2 high-level interface: RP2 captures complex tax events using a few powerful, low-level primitives, aggregated in patterns. A higher level tool, might abstract out these patterns and present them to the user in a friendlier way (for example it may capture a complex concept like DeFi bridging as a primitive, rather than a pattern);
* [RP2 plugins](https://github.com/eprbell/rp2/tree/main/README.dev.md#plugin-development): RP2 can be expanded via its programmable plugin architecture, which enables support for new output generators, countries and accounting methods;
* more...

If you'd like to start an ecosystem project, please open an [issue](https://github.com/eprbell/rp2/issues) to let the RP2 community know.

### List of Ecosystem Projects
Here's the current list of projects in the RP2 ecosystem:
* [DaLI](https://pypi.org/project/dali-rp2/): data loader and input generator for RP2 (https://pypi.org/project/rp2/).

## Reporting Bugs
Read the [Contributing](https://github.com/eprbell/rp2/tree/main/CONTRIBUTING.md#reporting-bugs) document.

## Contributing
Read the [Contributing](https://github.com/eprbell/rp2/tree/main/CONTRIBUTING.md) document.

## Developer Documentation
Read the [developer documentation](https://github.com/eprbell/rp2/tree/main/README.dev.md).

## Frequently Asked Questions
Read the [user FAQ list](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md) and the [developer FAQ list](https://github.com/eprbell/rp2/tree/main/docs/developer_faq.md).

## Change Log
Read the [Change Log](https://github.com/eprbell/rp2/tree/main/CHANGELOG.md) document.

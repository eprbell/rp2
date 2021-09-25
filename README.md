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

# RP2 v0.8.0
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
  * [Linux, macOS, Windows 10 and Other Unix-like Systems](https://github.com/eprbell/rp2/tree/main/README.md#running-on-linux-macos-windows-10-and-other-unix-like-systems)
  * [Windows 10](https://github.com/eprbell/rp2/tree/main/README.md#running-on-windows-10)
* **[Input and Output Files](https://github.com/eprbell/rp2/tree/main/README.md#input-and-output-files)**
* **[Reporting Bugs](https://github.com/eprbell/rp2/tree/main/README.md#reporting-bugs)**
* **[Contributing](https://github.com/eprbell/rp2/tree/main/README.md#contributing)**
* **[Developer Documentation](https://github.com/eprbell/rp2/tree/main/README.md#developer-documentation)**
* **[Frequently Asked Questions](https://github.com/eprbell/rp2/tree/main/README.md#frequently-asked-questions)**
* **[Change Log](https://github.com/eprbell/rp2/tree/main/README.md#change-log)**

## Introduction
[RP2](https://pypi.org/project/rp2/) is a privacy-focused, free, [open-source](https://github.com/eprbell/rp2) cryptocurrency tax calculator. Preparing crypto taxes can be a daunting and error-prone task, especially if multiple transactions, coins, exchanges and wallets are involved. This task could be delegated to a crypto tax preparation service, but many crypto users value their privacy and prefer not to send their transaction information to third parties unnecessarily. Additionally, many of these services cost money. RP2 solves all of these problems:
* it manages the complexity related to coin flows and tax calculation and it generates data that accountants can understand, even if they are not cryptocurrency experts (form 8949, etc.);
* it prioritizes user privacy by storing crypto transactions and tax results on the user's computer and not sending them anywhere else;
* it's free and open-source.

RP2 reads in a user-prepared spreadsheet containing crypto transactions. It then uses high-precision math to calculate long/short term capital gains, cost bases, balances, average price, in/out lot relationships/fractions, and finally it generates output spreadsheets. It supports the FIFO accounting method.

It has a programmable plugin architecture for [output generators](https://github.com/eprbell/rp2/tree/main/src/rp2/plugin/output): the builtin plugins are US-specific, but RP2's architecture makes it possible to contribute additional output generators for different countries or for different US-based cases. The builtin plugins are:
* tax_report_us: generates a tax report meant to be read by tax professionals (in the format of form 8949);
* rp2_full_report: generates a comprehensive report, with complete transaction history, lot relationships/fractions and computation details.

RP2 has extensive [unit test](https://github.com/eprbell/rp2/tree/main/tests/) coverage to reduce the risk of regression.

The author of RP2 is not a tax professional, but has used RP2 personally for a few years.

**IMPORTANT DISCLAIMER**: RP2 offers no guarantee of correctness (read the [license](https://github.com/eprbell/rp2/tree/main/LICENSE)): always verify results with the help of a tax professional.

### How RP2 Operates
RP2 treats virtual currency as property for tax purposes, as per [IRS Virtual Currency Guidance](https://www.irs.gov/newsroom/irs-reminds-taxpayers-to-report-virtual-currency-transactions).

RP2 uses the FIFO accounting method (lots acquired first are disposed of first): however, in and out lots typically don't have matching amounts, so RP2 fractions them, maps in/out lot fractions and computes the resulting cost bases and capital gains for each lot fraction.

RP2 groups lot fractions into the following taxable event categories, each of which has a unique tax treatment (ask your tax professional):
* EARN: specifically, interest from lending, wages, [mining](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-income-from-mining), [staking](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-income-from-staking), [airdrops](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-airdrops) and [hard forks](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-hard-forks). Note that buying cryptocurrency is not a taxable event;
* SELL: specifically, sale and [exchange of one cryptocurrency for another](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-conversion-of-a-cryptocurrency-to-another). RP2 splits them in two subcategories:
  * long-term capital gains, if the lot was held for more than 1 year, or
  * short-term capital gains otherwise;
* DONATE: donations to charitable organizations;
* GIFT: gifts to parties who are not charitable organizations are not tax-deductible.
* MOVE: the fee for moving currency between two accounts controlled by the same owner; these may not be taxable or tax deductible but they still affect the FIFO order so they are tracked.

For each of these categories RP2 generates an output spreadsheet with transaction details and computed gains. Users can give this output to their tax professional with the rest of their tax documentation.

**NOTE ON NFTs**: RP2 treats [NFTs](https://github.com/eprbell/rp2/tree/main/docs/user_faq.md#how-to-handle-nfts) as cryptocurrencies (that is, as property).

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

Then install RP2 Python package requirements:
```
pip install rp2
```
### Installation on macOS
First make sure [Homebrew](https://brew.sh) is installed, then open a terminal window and enter the following commands:
```
brew update
brew install python3
```

Finally install RP2 Python package requirements:
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
Before running RP2, the user must prepare two files:
* an ODS-format spreadsheet, containing crypto transactions (ODS-format files can be opened and edited with [LibreOffice](https://www.libreoffice.org/), Microsoft Excel and many other spreadsheet applications);
* a JSON config file, describing the format of the spreadsheet file: what value each column corresponds to (e.g. timestamp, amount, exchange, fee, etc.) and which cryptocurrencies and exchanges to expect.

The formats of these files are described in detail in the [Input Files](https://github.com/eprbell/rp2/tree/main/docs/input_files.md) section of the documentation.

Examples of an input spreadsheet and its respective config file:
* [input/crypto_example.ods](https://github.com/eprbell/rp2/tree/main/input/crypto_example.ods)
* [config/crypto_example.config](https://github.com/eprbell/rp2/tree/main/config/crypto_example.config) (if desired, this config file can be used as boilerplate).

After reading the input files, RP2 computes taxes and generates output files, which contain information on long/short capital gains, cost bases, balances, average price, in/out lot relationships and fractions. They are described in detail in the [Output Files](https://github.com/eprbell/rp2/tree/main/docs/output_files.md) section of the documentation.

### Running on Linux, macOS, Windows 10 and Other Unix-like Systems
Download [crypto_example.ods](https://github.com/eprbell/rp2/tree/main/input/crypto_example.ods) and [crypto_example.config](https://github.com/eprbell/rp2/tree/main/config/crypto_example.config). Let's call `<download_directory>` the location of the downloaded files.

To generate output for the example files open a terminal window (or PowerShell if on Windows) and enter the following commands:
  ```
  cd <download_directory>
  rp2 -o output -p crypto_example_ crypto_example.config crypto_example.ods
  ```
Results are generated in the `output` directory and logs are stored in the `log` directory.

To print command usage information for the `rp2` command:
  ```
  rp2 --help
  ```

## Input and Output Files
Read the [input files](https://github.com/eprbell/rp2/tree/main/docs/input_files.md) and [output files](https://github.com/eprbell/rp2/tree/main/docs/output_files.md) documentation.

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

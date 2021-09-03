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

# RP2 v0.5.0

![Main branch](https://github.com/eprbell/rp2/actions/workflows/static_analysis.yml/badge.svg)
![Main branch](https://github.com/eprbell/rp2/actions/workflows/unix_unit_tests.yml/badge.svg)
![Main branch](https://github.com/eprbell/rp2/actions/workflows/windows_unit_tests.yml/badge.svg)
![Main branch](https://github.com/eprbell/rp2/actions/workflows/codeql-analysis.yml/badge.svg)

## Table of Contents
* **[Introduction](#introduction)**
  * [How RP2 Operates](#how-rp2-operates)
* **[License](#license)**
* **[Download](#download)**
* **[Installation](#installation)**
  * [Ubuntu Linux](#installation-on-ubuntu-linux)
  * [macOS](#installation-on-macos)
  * [Windows 10](#installation-on-windows-10)
  * [Other Unix-like Systems](#installation-on-other-unix-like-systems)
* **[Running](#running)**
  * [Linux, macOS and Other Unix-like Systems](#running-on-linux-macos-and-other-unix-like-systems)
  * [Windows 10](#running-on-windows-10)
* **[Input and Output Files](#input-and-output-files)**
* **[Reporting Bugs](#reporting-bugs)**
* **[Contributing](#contributing)**
* **[Full Documentation](#full-documentation)**
* **[Frequently Asked Questions](#frequently-asked-questions)**

## Introduction
[RP2](https://github.com/eprbell/rp2) is a privacy-focused, free, open-source cryptocurrency tax calculator. Preparing crypto taxes can be a daunting and error-prone task, especially if multiple transactions, coins, exchanges and wallets are involved. This problem could be delegated to a crypto tax preparation service, but many crypto users value their privacy and prefer not to send their transaction information to third parties unnecessarily. Additionally, many of these services cost money. RP2 solves all of these problems:
* it manages the complexity related to coin flows and tax calculation and it generates forms tax that accountants can understand, even if they are not cryptocurrency experts (e.g. form 8949);
* it prioritizes user privacy by storing crypto transactions and tax results on the user's computer and not sending them anywhere else;
* it's free and open-source.

RP2 reads in a user-prepared spreadsheet containing crypto transactions. It then uses high-precision math to calculate long/short term capital gains, cost bases, balances, average price, in/out lot relationships and fractions, and finally it generates output spreadsheets. It supports the FIFO accounting method.

It has a programmable plugin architecture for [output generators](plugin/output): currently only US-specific plugins are available (one for form 8949 and another for a full tax report), but the architecture makes it possible to contribute additional output generators for different countries or for different US-based cases.

RP2 has extensive [unit test](test/) coverage to reduce the risk of regression.

The author of RP2 is not a tax professional, but has used RP2 personally for a few years.

**IMPORTANT DISCLAIMER**: RP2 offers no guarantee of correctness (read the [license](#license)): always verify results with the help of a tax professional.

### How RP2 Operates
RP2 treats virtual currency as property for tax purposes, as per [IRS Virtual Currency Guidance](https://www.irs.gov/newsroom/irs-reminds-taxpayers-to-report-virtual-currency-transactions).

RP2 uses the FIFO accounting method (lots acquired first are disposed of first): however, in and out lots typically don't have matching amounts, so RP2 fractions them as needed and manages the resulting cost bases and capital gains.

RP2 identifies the following taxable events:
* acquisition: any cryptocurrency that is earned (e.g. interest, wages, etc.) is treated as ordinary income (or short-term capital gains). Note that buying cryptocurrency is not a taxable event;
* transfer of ownership: any cryptocurrency that is sold, gifted or donated is treated as:
  * long-term capital gains if the lot was held for more than 1 year, or
  * short-term capital gains otherwise;
* transfer fee (the fee for moving currency between two accounts controlled by the same owner) is treated like a sale: long-term capital gains if the lot was held for more than 1 year, or short-term capital gains otherwise. Note that only the fee is taxable: the transferred amount is not;

## License
RP2 is released under the terms of Apache License Version 2.0. For more information see [LICENSE](LICENSE) or http://www.apache.org/licenses/LICENSE-2.0.

## Download
The latest version of RP2 can be downloaded at: https://github.com/eprbell/rp2

## Installation
RP2 has been tested on Ubuntu Linux, macOS and Windows 10 but it should work on all systems that have Python version 3.7.0 or greater.

### Installation on Ubuntu Linux
First make sure Python, pip and virtualenv are installed. If not, open a terminal window and enter the following commands:
```
sudo apt-get update
sudo apt-get install make python3 python3-pip virtualenv
```

Then install RP2 Python package requirements:
```
cd <rp2_directory>
make
```
### Installation on macOS
First make sure [Homebrew](https://brew.sh) is installed, then open a terminal window and enter the following commands:
```
brew update
brew install python3 virtualenv
```

Finally install RP2 Python package requirements:
```
cd <rp2_directory>
make
```
### Installation on Windows 10
First make sure [Python](https://python.org) 3.7 or greater is installed (in the Python installer window be sure to click on "Add Python to PATH"), then open a PowerShell window and enter the following commands:
```
python -m pip install virtualenv
cd <rp2_directory>
virtualenv -p python .venv
```

Finally install RP2 Python package requirements:
```
cd <rp2_directory>
python -m pip install -r requirements.txt
```

### Installation on Other Unix-like Systems
* install GNU make
* install python 3.7 or greater
* install pip3
* install virtualenv
* update PATH variable, if needed
* cd _<rp2_directory>_
* make

## Running
Before running RP2 the user must prepare two files:
* an ODS-format spreadsheet, containing crypto transactions (ODS-format files can be opened and edited with [LibreOffice](https://www.libreoffice.org/), Microsoft Excel and many other spreadsheet applications);
* a JSON config file, describing the format of the spreadsheet file: what value each column corresponds to (e.g. timestamp, amount, exchange, fee, etc.) and which cryptocurrencies and exchanges to expect.

The formats of these files are described in detail in the [Input Files](doc/input_files.md) section of the documentation.

Examples of an input spreadsheet and its respective config file:
* [input/crypto_example.ods](input/crypto_example.ods)
* [config/crypto_example.config](config/crypto_example.config) (if desired, this config file can be used as boilerplate).

After reading the input files, RP2 generates output files based on the transaction information therein. The output files contain information on long/short capital gains, cost bases, balances, average price, in/out lot relationships and fractions. They are described in detail in the [Output Files](doc/output_files.md) section of the documentation.

The next sections contain platform-specific information on how to run RP2 on different systems.

### Running on Linux, macOS and Other Unix-like Systems

To generate output for the above example open a terminal window and enter the following commands:
  ```
  cd <rp2_directory>
  . .venv/bin/activate
  bin/rp2.py -o output -p crypto_example_ config/crypto_example.config input/crypto_example.ods
  ```
Results are generated in the `output` directory. Logs are stored in the `log` directory.

To print command usage information for the `rp2.py` command:
  ```
  bin/rp2.py --help
  ```

### Running on Windows 10

To generate output for the above example open a PowerShell window and enter the following commands:
  ```
  cd <rp2_directory>
  .venv\Scripts\activate.ps1
  python bin\rp2.py -o output -p crypto_example_ config\crypto_example.config input\crypto_example.ods
  ```

Results are generated in the `output` directory. Logs are stored in the `log` directory.

To print command usage information for the `rp2.py` command:
  ```
  python bin\rp2.py --help
  ```

## Input and Output Files
Read the [input files](doc/input_files.md) and [output files](doc/output_files.md) documentation.

## Reporting Bugs
Read the [Contributing](CONTRIBUTING.md) document.

## Contributing
Read the [Contributing](CONTRIBUTING.md) document.

## Full Documentation
Read the [full documentation](doc/README.md).

## Frequently Asked Questions
Read the [user FAQ list](doc/user_faq.md) and the [developer FAQ list](doc/developer_faq.md).
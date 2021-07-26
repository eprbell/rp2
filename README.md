# RP2 v0.1.1

## Table of Contents
* **[Introduction](#introduction)**
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
* **[Development And Testing](#development-and-testing)**
* **[Contributing](#contributing)**
* **[Documentation](#documentation)**

## Introduction
RP2 is a privacy-focused, free, open-source cryptocurrency tax calculator. Calculating crytpocurrency-related taxes can be a daunting and error-prone task, especially if many transactions and multiple exchanges are involved. [RP2](https://github.com/eprbell/rp2) makes this process easier. It reads as input a spreadsheet containing crypto transactions, divided in three tables (one per direction):
* in (buy, earn),
* out (sell, gift, donate),
* intra (move across accounts).

It then calculates long/short capital gains, cost bases, balances, average price, in/out lot relationships and fractions and generates output spreadsheets. It supports the FIFO accounting method.

RP2 prioritizes user privacy: it stores crypto transaction information locally on the user's computer and doesn't send transaction information anywhere else.

RP2 has a programmable plugin architecture for output generators: currently only US-specific plugins are available, but the architecture makes it possible to contribute additional output generators for different countries or for different US-based cases.

**IMPORTANT DISCLAIMER**: RP2 offers no guarantee of correctness: always verify results with the help of a tax professional.

## License
RP2 is released under the terms of Apache License Version 2.0. For more information see [LICENSE](LICENSE) or http://www.apache.org/licenses/LICENSE-2.0.

## Download
The latest version of RP2 can be downloaded at: https://github.com/eprbell/rp2

## Installation
RP2 has been tested on Ubuntu Linux, macOS and Windows 10 but it should work on all systems that have Python version 3.8.0 or greater.

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

Then install RP2 Python package requirements:
```
cd <rp2_directory>
make
```
### Installation on Windows 10
First make sure [Python](https://python.org) 3.8 or greater is installed (in the Python installer window be sure to click on "Add Python to PATH"), then open a PowerShell window and enter the following commands:
```
python -m pip install virtualenv
cd <rp2_directory>
virtualenv -p python .venv
```

Then install RP2 Python package requirements:
```
cd <rp2_directory>
python -m pip install -r requirements.txt
```

### Installation on Other Unix-like Systems
* install GNU make
* install python 3.8 or greater
* install pip3
* install virtualenv
* update PATH variable, if needed
* cd _<rp2_directory>_
* make

## Running
RP2 reads as input two user-prepared files:
- an ODS-format spreadsheet (containing crypto transactions)
- a JSON config (describing the format of the spreadsheet file).

The formats of these files are described in detail in the [Input Files](doc/input_files.md) section of the documentation.

Examples of an input spreadsheet and its respective config file:
* [input/crypto_example.ods](input/crypto_example.ods)
* [config/crypto_example.config](config/crypto_example.config). If desired, this config file can be used as-is as a ready-made format for the spreadsheet.

RP2 generates output files based on the received input. The output files contain information on long/short capital gains, cost bases, balances, average price, in/out lot relationships and fractions. They are described in detail in the [Output Files](doc/output_files.md) section of the documentation.

### Running on Linux, macOS and Other Unix-like Systems

To generate output for the above example open a terminal window and enter the following commands:
  ```
  cd <rp2_directory>
  . .venv/bin/activate
  bin/rp2.py -o output -p crypto_example_ config/crypto_example.config input/crypto_example.ods
  ```
Results are generated in the `output` directory. Logs are stored in the `log` directory.

To print usage information for the `rp2.py` command:
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

To print usage information for the `rp2.py` command:
  ```
  python bin\rp2.py --help
  ```

## Development and Testing
The development and testing workflows are supported only on Linux and macOS (not on Windows).

Here are the relevant make targets:
* `make`: installs package requirements
* `make archive`: creates a .zip file with the contents of the RP2 directory
* `make clean`: removes the virtual environment, logs, outputs, caches, etc.
* `make lint`: analyzes all Python sources with Pylint
* `make reformat`: formats all Python sources using Black
* `make test`: runs all RP2 unit tests
* `make typecheck`: analyzes all Python sources with Mypy static type checker

Logs are stored in the `log` directory. To generate debug logs, prepend the command line with `LOG_LEVEL=DEBUG`, e.g.:
```
LOG_LEVEL=DEBUG bin/rp2.py -o output -p crypto_example_ config/crypto_example.config input/crypto_example.ods
```

## Contributing
Feel free to submit pull requests and submit bugs via Issue Tracker. For pull requests, please follow the PEP 8 coding standard (which is enforced by the `reformat` make target) and make sure your code doesn't trigger new issues with the following make targets:
```
make lint reformat test typecheck
```
Unit tests for new code are highly appreciated.

## Documentation
Documentation is available in the [doc](doc/README.md) directory

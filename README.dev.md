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

# RP2 v0.9.28 Developer Guide
[![Static Analysis / Main Branch](https://github.com/eprbell/rp2/actions/workflows/static_analysis.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/static_analysis.yml)
[![Documentation Check / Main Branch](https://github.com/eprbell/rp2/actions/workflows/documentation_check.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/documentation_check.yml)
[![Unix Unit Tests / Main Branch](https://github.com/eprbell/rp2/actions/workflows/unix_unit_tests.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/unix_unit_tests.yml)
[![Windows Unit Tests / Main Branch](https://github.com/eprbell/rp2/actions/workflows/windows_unit_tests.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/windows_unit_tests.yml)
[![CodeQL/Main Branch](https://github.com/eprbell/rp2/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/eprbell/rp2/actions/workflows/codeql-analysis.yml)

## Table of Contents
* **[Introduction](#introduction)**
* **[License](#license)**
* **[Download](#download)**
* **[Setup](#setup)**
  * [Ubuntu Linux](#setup-on-ubuntu-linux)
  * [macOS](#setup-on-macos)
  * [Windows 10](#setup-on-windows-10)
  * [Other Unix-like Systems](#setup-on-other-unix-like-systems)
* **[Source Code](#source-code)**
* **[Development](#development)**
  * [Design Guidelines](#design-guidelines)
  * [Development Workflow](#development-workflow)
  * [Unit Tests](#unit-tests)
* **[Plugin Development](#plugin-development)**
  * [Adding a New Report Generator](#adding-a-new-report-generator)
  * [Adding a New Accounting Method](#adding-a-new-accounting-method)
  * [Adding Support for a New Country](#adding-support-for-a-new-country)
* **[Frequently Asked Developer Questions](#frequently-asked-developer-questions)**

## Introduction
This document describes [RP2](https://github.com/eprbell/rp2) setup instructions, development workflow, design principles, source tree structure and plugin architecture.

## License
RP2 is released under the terms of Apache License Version 2.0. For more information see [LICENSE](LICENSE) or <http://www.apache.org/licenses/LICENSE-2.0>.

## Download
The latest RP2 source can be downloaded at: <https://github.com/eprbell/rp2>

## Setup
RP2 has been tested on Ubuntu Linux, macOS and Windows 10 but it should work on all systems that have Python version 3.7.0 or greater. Virtualenv is recommended for RP2 development.

### Setup on Ubuntu Linux
First make sure Python, pip and virtualenv are installed. If not, open a terminal window and enter the following commands:
```
sudo apt-get update
sudo apt-get install python3 python3-pip virtualenv
```

Then install RP2 Python package requirements:
```
cd <rp2_directory>
virtualenv -p python3 .venv
. .venv/bin/activate
.venv/bin/pip3 install -e '.[dev]'
```
### Setup on macOS
First make sure [Homebrew](https://brew.sh) is installed, then open a terminal window and enter the following commands:
```
brew update
brew install python3 virtualenv
```

Then install RP2 Python package requirements:
```
cd <rp2_directory>
virtualenv -p python3 .venv
. .venv/bin/activate
.venv/bin/pip3 install -e '.[dev]'
```
### Setup on Windows 10
First make sure [Python](https://python.org) 3.7 or greater is installed (in the Python installer window be sure to click on "Add Python to PATH"), then open a PowerShell window and enter the following commands:
```
python -m pip install virtualenv
```

Then install RP2 Python package requirements:
```
cd <rp2_directory>
virtualenv -p python .venv
.venv\Scripts\activate.ps1
python -m pip install -e ".[dev]"
```
### Setup on Other Unix-like Systems
* install python 3.7 or greater
* install pip3
* install virtualenv
* cd _<rp2_directory>_
* `virtualenv -p python3 .venv`
* `.venv/bin/pip3 install -e '.[dev]'`

## Source Code
The RP2 source tree is organized as follows:
* `.bumpversion.cfg`: bumpversion configuration;
* `CHANGELOG.md`: change log document;
* `config/`: config files for examples and tests;
* `CONTRIBUTING.md`: contribution guidelines;
* `docs/`: additional documentation, referenced from the README files;
* `.editorconfig`;
* `.github/workflows/`: configuration of Github continuous integration;
* `.gitignore`;
* `input/`: examples and tests;
* `input/golden/`: expected outputs that RP2 tests compare against;
* `.isort.cfg`: isort configuration;
* `LICENSE`: license information;
* `Makefile`: alternative old-school build flow;
* `MANIFEST.in`: source distribution configuration;
* `mypy.ini`: mypy configuration;
* `.pre-commit-config.yaml`: pre-commit configuration;
* `.pylintrc`: pylint configuration;
* `pyproject.toml`: packaging configuration;
* `README.dev.md`: developer documentation;
* `README.md`: user documentation;
* `setup.cfg`: static packaging configuration file;
* `setup.py`: dynamic packaging configuration file;
* `src/rp2`: RP2 code, including classes for transactions, gains, tax engine, balances, logger, ODS parser, etc.;
* `src/rp2/plugin/accounting_method/`: accounting method plugins;
* `src/rp2/plugin/country/`: country plugins/entry points;
* `src/rp2/plugin/report/`: report generator plugins;
* `src/rp2/plugin/report/data/`: spreadsheet templates that are used by the builtin report plugins;
* `src/rp2/plugin/report/<country>`: country-specific report generator plugins;
* `src/stubs/`: RP2 relies on third-party libraries, some of which don't have typing information, so it is added here;
* `tests/`: unit tests.

## Development
Read the [Contributing](CONTRIBUTING.md) document on pull requests guidelines.

### Design Guidelines
RP2 code adheres to these principles:
* immutability: generally data structures are read-only (the only exceptions are for data structures that would incur a major complexity increase without write permission: e.g. AVL tree node).
  * class fields are private (prepended with double-underscore). Fields that need public access have a read-only property. Write-properties are not used;
  * @dataclass classes have `frozen=True`
* runtime checks: parameters of public functions are type-checked at runtime:
  * `Configuration.type_check_*()` for primitive types;
  * `<class>.type_check()` for classes;
* type hints: all variables and functions have Python type hints;
* no id-based hashing: classes that are added to dictionaries and sets redefine `__eq__()`, `__neq__()` and `__hash__()`;
* encapsulated math: all high-precision math is done via `RP2Decimal` (a subclass of Decimal), to ensure the correct precision is used throughout the code. `RP2Decimal` instances are never mixed with other types in expressions;
* f-strings only: every time string interpolation is needed, f-strings are used;
* logging: logging is done via the `logger` module;
* no unnamed tuples: dataclasses or named tuples are used instead;
* one class per file (with exceptions for trivial classes);
* files containing a class must have the same name as the class (but lowercase with underscores): e.g. class AbstractEntry lives in file abstract_entry.py;
* abstract class names start with `Abstract`;
* no imports with `*`.

### Development Workflow
RP2 uses pre-commit hooks for quick validation at commit time and continuous integration via Github actions for deeper testing. Pre-commit hooks invoke: flake8, black, isort, pyupgrade and more. Github actions invoke: mypy, pylint, bandit, unit tests (on Linux, Mac and Windows), markdown link check and more.

While every commit and push is automatically tested as described, sometimes it's useful to run some of the above commands locally without waiting for continuous integration. Here's how to run the most common ones:
* run unit tests: `pytest --tb=native --verbose`
* type check: `mypy src tests`
* lint: `pylint -r y src tests/*.py`
* security check: `bandit -r src`
* reformat code: `black src tests`
* sort imports: `isort .`
* run pre-commit tests without committing: `pre-commit run --all-files`

Logs are stored in the `log` directory. To generate debug logs, prepend the command line with `LOG_LEVEL=DEBUG`, e.g.:
```
LOG_LEVEL=DEBUG bin/rp2_us -o output -p crypto_example_ config/crypto_example.config input/crypto_example.ods
```

### Unit Tests
RP2 has considerable unit test coverage to reduce the risk of regression. Unit tests are in the [tests](tests) directory. Please add unit tests for any new code.

## Plugin Development
RP2 has a plugin architecture for countries, report generators and accounting methods, which makes it extensible for new use cases.

### Adding a New Report Generator
Report generator plugins translate data structures that result from tax computation into output. Writing a new report generator plugin is quite easy: the [tax_report_us](src/rp2/plugin/report/us/tax_report_us.py) generator is a simple example, the [rp2_full_report](src/rp2/plugin/report/rp2_full_report.py) one is more comprehensive.

Report generator plugins are discovered by RP2 at runtime and they must adhere to the conventions shown below. To add a new plugin follow this procedure:
* if the new plugin is not country-specific, add a new Python file in the `src/rp2/plugin/report/` directory and give it a meaningful name
* if the new plugin is country-specific, add a new Python file in the `src/rp2/plugin/report/<country>` directory and give it a meaningful name (where `<country>` is a 2-letter country code adhering to the [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) format)
* import the following (plus any other RP2 file you might need):
```
from rp2.abstract_country import AbstractCountry
from rp2.abstract_report_generator import AbstractReportGenerator
from rp2.computed_data import ComputedData
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
```
* Optionally, RP2 provides a logger facility:
```
from logger import LOGGER
```
* Add a class named `Generator`, deriving from `AbstractReportGenerator`:
```
class Generator(AbstractReportGenerator):
```
* Add a `generate()` method with the following signature:
```
    def generate(
        self,
        country: AbstractCountry,
        accounting_method: str,
        asset_to_computed_data: Dict[str, ComputedData],
        output_dir_path: str,
        output_file_prefix: str,
    ) -> None:
```
* write the body of the method. The parameters are:
  * `country`: instance of [AbstractCountry](src/rp2/abstract_country.py); see [Adding Support for a New Country](#adding-support-for-a-new-country) for more details;
  * `accounting_method`: string name of the accounting method used to compute the taxes;
  * `asset_to_computed_data`: dictionary mapping user asset (i.e. cryptocurrency) to the computed tax data for that asset. For each user asset there is one instance of [ComputedData](src/rp2/computed_data.py);
  * `output_dir_path`: directory in which to write the output;
  * `output_file_prefix`: prefix to be prepended to the output file name.

**NOTE**: If you're interested in adding support for a new report generator, open a [PR](CONTRIBUTING.md).

### Adding a New Accounting Method
Accounting method plugins modify the behavior of the tax engine. They pair in/out lots according to the given accounting algorithm: [FIFO](src/rp2/plugin/accounting_method/fifo.py) and [LIFO](src/rp2/plugin/accounting_method/lifo.py) are examples of accounting method plugins (FIFO is simpler, LIFO more elaborate).

Accounting method plugins are discovered by RP2 at runtime and they must adhere to the conventions shown below. To add a new plugin follow this procedure:
* add a new Python file to the `src/rp2/plugin/accounting_method/` directory and give it a meaningful name (like fifo.py)
* import the following (plus any other RP2 file you might need):
```
from typing import Iterator, Optional

from rp2.abstract_accounting_method import (
    AbstractAccountingMethod,
    AcquiredLotsExhaustedException,
    TaxableEventAndAcquiredLot,
    TaxableEventsExhaustedException,
)
from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import RP2Decimal
```
* Optionally, RP2 provides a logger facility:
```
from logger import LOGGER
```
* Add an `initialize()` method with the following signature:
```
    def initialize(self, taxable_event_iterator: Iterator[AbstractTransaction], acquired_lot_iterator: Iterator[InTransaction]) -> None:
```
* write the body of `initialize()`. This method is passed iterators on taxable events and aquired lots and performs accounting-method-specific initialization (e.g. it might iterate over the iterators and add the elements to custom data structures, like AVL trees, etc.). The parameters are:
  * `taxable_event_iterator`: iterator over TaxableEvent instances (disposed-of lots), in chronological order;
  * `acquired_lot_iterator`: iterator over InTransaction instances (acquired lots), in chronological order;
* Add `get_next_taxable_event_and_amount()` and `get_acquired_lot_for_taxable_event()` methods with the following signatures:
```
    def get_next_taxable_event_and_amount(
        self,
        taxable_event: Optional[AbstractTransaction],
        acquired_lot: Optional[InTransaction],
        taxable_event_amount: RP2Decimal,
        acquired_lot_amount: RP2Decimal,
    ) -> TaxableEventAndAcquiredLot:
    def get_acquired_lot_for_taxable_event(
        self,
        taxable_event: AbstractTransaction,
        acquired_lot: Optional[InTransaction],
        taxable_event_amount: RP2Decimal,
        acquired_lot_amount: RP2Decimal
    ) -> TaxableEventAndAcquiredLot:
```
* write the bodies of the methods. The parameters/return values are:
  * `taxable_event`: the disposed-of lot;
  * `acquired_lot`: the acquired lot;
  * `taxable_event_amount`: the amount that is leftover of the current taxable event;
  * `acquired_lot_amount`: the amount that is leftover of the current acquired lot.
  * it returns TaxableEventAndAcquiredLot, which captures a new taxable event/acquired lot pair. Notice that in most cases only one of the two is new and the other stays the same and only gets its amount adjusted. However in some special cases that depend on the semantics of the plugin, one of these methods may need to update both taxable event and aquired lot (e.g. in the LIFO version of `get_next_taxable_event_and_amount()`, if the new taxable event has a timestamp with a new year, then the method also has to look for a new acquired lot in the same new year).
* Add a `validate_acquired_lot_ancestor_timestamp()` method with the following signature:
```
    def validate_acquired_lot_ancestor_timestamp(self, acquired_lot: InTransaction, acquired_lot_parent: InTransaction) -> bool:
```
* write the body of the method: it returns `True` if the ancestor's acquired lot timestamp is compatible with the current acquired lot timestamp according to the accounting method and `False` otherwise: e.g. in FIFO the ancestor must be earlier than the current. The ancestor lot has been processed before the current one, according to the logic of the accounting method.

**NOTE**: If you're interested in adding support for a new accounting method, open a [PR](CONTRIBUTING.md).

### Adding Support for a New Country
RP2 has experimental infrastructure to support countries other than the US. The abstract superclass is [AbstractCountry](src/rp2/abstract_country.py), which captures the following:
* country code (2-letter string in [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) format);
* currency code (3-letter string in [ISO 4217](https://en.wikipedia.org/wiki/ISO_4217) format);
* long term capital gain period in days (e.g. for the US it's 365).

To add support for a new country, add a new Python file to the `src/rp2/plugin/country` directory and name it after the ISO 3166-1 alpha-2 2-letter code for the country. Then define the `long_term_capital_gain_period()` method with the appropriate value and add a global function called `rp2_entry()` which simply calls `rp2_main()` and passes it an instance of the new country class: in fact subclasses of `AbstractCountry` are entry points, not plugins. As an example see the [us.py](src/rp2/plugin/country/us.py) file.

Finally add a console script to [setup.cfg](setup.cfg) pointing the new country rp2_entry (see the US example in the console_scripts section of setup.cfg).

**NOTE**: as mentioned, the country infrastructure is experimental. If you're interested in adding support for a new country and have feedback or notice missing functionality, open a [PR](CONTRIBUTING.md).

## Frequently Asked Developer Questions
Read the [frequently asked developer questions](docs/developer_faq.md).

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

# RP2 v1.4.1 Developer Guide
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
* **[Creating a Release](#creating-a-release)**
* **[Plugin Development](#plugin-development)**
  * [Adding a New Report Generator](#adding-a-new-report-generator)
  * [Adding a New Accounting Method](#adding-a-new-accounting-method)
  * [Adding Support for a New Country](#adding-support-for-a-new-country)
* **[Localization](#localization)**
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
* `.gitattributes`;
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
* `src/locales`: RP2 localization data;
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
* user privacy is of paramount importance: user data never leaves the user's machine and no network calls are allowed.
* all identifiers have [descriptive names](https://realpython.com/python-pep8/#how-to-choose-names);
* immutability:
  * global variables have upper case names, are initialized where declared and are never modified afterwards;
  * generally data structures are read-only (the only exceptions are for data structures that would incur a major complexity increase without write permission: e.g. AVL tree node):
    * class fields are private (prepended with double-underscore). Fields that need public access have a read-only property. Write-properties are not used;
    * @dataclass classes have `frozen=True`;
* data encapsulation: all data fields are private (prepended with double-underscore):
  * for private access nothing else is needed;
  * for protected access add a read-only property starting with single underscore or an accessor function starting with `_get_`;
  * for public access add a read-only property starting with no underscore or an accessor function starting with `get_`;
* runtime checks: parameters of public functions are type-checked at runtime:
  * `Configuration.type_check_*()` for primitive types;
  * `<class>.type_check()` for classes;
* type hints: all variables and functions have Python type hints (with the exception of local variables, for which type hints are optional);
* no id-based hashing: classes that are added to dictionaries and sets redefine `__eq__()`, `__neq__()` and `__hash__()`;
* encapsulated math: all high-precision math is done via `RP2Decimal` (a subclass of Decimal), to ensure the correct precision is used throughout the code. `RP2Decimal` instances are never mixed with other types in expressions;
* f-strings only: every time string interpolation is needed, f-strings are used;
* no raw strings (unless they occur only once): use global constants instead;
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
LOG_LEVEL=DEBUG bin/rp2_us -o output -p crypto_example_ config/crypto_example.ini input/crypto_example.ods
```

### Unit Tests
RP2 has considerable unit test coverage to reduce the risk of regression. Unit tests are in the [tests](tests) directory. Please add unit tests for any new code.

## Creating a Release
This section is for project maintainers.

To create a new release:
* add a section named as the new version in CHANGELOG.md
* use the output of `git log` to collect significant changes since last version and add them to CHANGELOG.md as a list of brief bullet points
* `git add CHANGELOG.md`
* `git commit -m "Updated with latest changes" CHANGELOG.md`
* `bumpversion patch` (or `bumpversion minor` or `bumpversion major`)
* `git push`
* wait for all tests to pass successfully on Github
* add a tag in Github (named the same as the version but with a `v` in front, e.g. `v1.0.4`):  click on "Releases" and then "Draft a new release"

To create a Pypi distribution:
* `make distribution`
* `make upload_distribution`

## Plugin Development
RP2 has a plugin architecture for countries, report generators and accounting methods, which makes it extensible for new use cases.

### Adding a New Report Generator
Report generator plugins translate data structures that result from tax computation into output. Writing a new report generator plugin is quite easy: the [tax_report_us](src/rp2/plugin/report/us/tax_report_us.py) generator is a simple example, the [rp2_full_report](src/rp2/plugin/report/rp2_full_report.py) one is more comprehensive.

Report generator plugins are discovered by RP2 at runtime and they must adhere to the conventions shown below. To add a new plugin follow this procedure:
* if the new plugin is not country-specific, add a new Python file in the `src/rp2/plugin/report/` directory and give it a meaningful name
* if the new plugin is country-specific, add a new Python file in the `src/rp2/plugin/report/<country>` directory and give it a meaningful name (where `<country>` is a 2-letter country code adhering to the [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) format)
* import the following (plus any other RP2 or Python package you might need):
```
from typing import Dict

from rp2.abstract_country import AbstractCountry
from rp2.computed_data import ComputedData
from rp2.entry_types import TransactionType
from rp2.gain_loss import GainLoss
from rp2.gain_loss_set import GainLossSet
```
* Optionally, RP2 provides a logger facility:
```
from logger import LOGGER
```
* Add a class named `Generator`, deriving from `AbstractReportGenerator` or `AbstractODSGenerator` (if generating a .ods file):
```
class Generator(AbstractReportGenerator):
```
* Add a `generate()` method to the class with the following signature:
```
    def generate(
        self,
        country: AbstractCountry,
        accounting_method: str,
        asset_to_computed_data: Dict[str, ComputedData],
        output_dir_path: str,
        output_file_prefix: str,
        from_date: date,
        to_date: date,
        generation_language: str,
    ) -> None:
```
* write the body of the `generate()`. The parameters are:
  * `country`: instance of [AbstractCountry](src/rp2/abstract_country.py); see [Adding Support for a New Country](#adding-support-for-a-new-country) for more details;
  * `accounting_method`: string name of the accounting method used to compute the taxes. This is for purposes of generation only (it can be emitted in the output);
  * `asset_to_computed_data`: dictionary mapping user assets (i.e. cryptocurrency) to the computed tax data for that asset. For each user asset there is one instance of [ComputedData](src/rp2/computed_data.py);
  * `output_dir_path`: directory in which to write the output;
  * `output_file_prefix`: prefix to be prepended to the output file name;
  * `from_date`: filter out transactions before this date. This is for generation purposes only (it can be emitted in the output): the computed data is already time-filtered;
  * `to_date`: filter out transactions after this date. This is for generation purposes only (it can be emitted in the output): the computed data is already time-filtered;
  * `generation_language`: language to use for generation. This is a hint and, depending on the nature of the plugin it can be used or ignored: e.g.
    * the tax_report_us plugin ignores `generation_language` because it generates a 8849-sytle report that has no use outside the US (so only English is used)
    * the rp2_full_report plugin uses `generation_language` because it generates a generic report that can be useful in any country (so it has to be localization-friendly)

Report plugin output can be localized in many languages (see the [Localization](#localization) section for more on this): for an example of a localization-aware plugin see [rp2_full_report](src/rp2/plugin/report/rp2_full_report.py).

**NOTE**: If you're interested in adding support for a new report generator, open a [PR](CONTRIBUTING.md).

### Adding a New Accounting Method
Accounting method plugins modify the behavior of the tax engine. They pair in/out lots according to the given accounting algorithm: [FIFO](src/rp2/plugin/accounting_method/fifo.py) is an example of accounting method plugin.

Accounting method plugins are discovered by RP2 at runtime and they must adhere to the conventions shown below. To add a new plugin follow this procedure:
* add a new Python file to the `src/rp2/plugin/accounting_method/` directory and give it a meaningful name (like fifo.py)
* import the following (plus any other RP2 or Python package you might need):
```
from typing import Optional

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.abstract_accounting_method import AcquiredLotCandidates, AcquiredLotCandidatesOrder, AcquiredLotAndAmount
from rp2.abstract_transaction import AbstractTransaction
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
```
* Add a class named `AccountingMethod`, deriving from `AbstractAccountingMethod`:
```
class AccountingMethod(AbstractAccountingMethod):
```
* Add a `seek_non_exhausted_acquired_lot()` method to the class with the following signature:
```
    def seek_non_exhausted_acquired_lot(
        self,
        lot_candidates: AcquiredLotCandidates,
        taxable_event: Optional[AbstractTransaction],
        taxable_event_amount: RP2Decimal,
    ) -> Optional[AcquiredLotAndAmount]:
```
* write the body of the method. The parameters/return values are:
  * `lot_candidates`: iterable of acquired lot candidates to select from according to the accounting method. The lots are in the order specified by the `lot_candidates_order()` method (see below);
  * `taxable_event`: the taxable event the method is finding an acquired lot to pair with;
  * `taxable_event_amount`: the amount left in taxable event;
  * it returns `None` if it doesn't find a suitable acquired lot, or `AcquiredLotAndAmount`, which captures a new acquired lot and its remaining amount. Note that, since lots can be fractioned, the remaining amount can be less than `crypto_in`. In the body of the function use the `has_partial_amount()` and `get_partial_amount()` methods of `AcquiredLotCandidates` to check if the lot has a partial amount and how much it is.

* Add a `lot_candidates_order()` method to the class with the following signature:
```
    def lot_candidates_order(self) -> AcquiredLotCandidatesOrder:
```
* write the body of the method: it returns `AcquiredLotCandidatesOrder.OLDER_TO_NEWER` or `AcquiredLotCandidatesOrder.NEWER_TO_OLDER`, depending on whether the desired chronological order is ascending or descending.

**NOTE**: If you're interested in adding support for a new accounting method, open a [PR](CONTRIBUTING.md).

### Adding Support for a New Country
RP2 has built-in support for the US but it also has infrastructure to support other countries. The abstract superclass of country plugins is [AbstractCountry](src/rp2/abstract_country.py), which captures the following:
* country code (2-letter string in [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) format);
* currency code (3-letter string in [ISO 4217](https://en.wikipedia.org/wiki/ISO_4217) format);
* long term capital gain period in days (e.g. for the US it's 365);
* accepted accounting methods;
* accepted report generators;
* default language for the country.

 To add a new plugin follow this procedure:
* add a new Python file to the `src/rp2/plugin/country/` directory and name it after the ISO 3166-1 alpha-2, 2-letter code for the country (e.g. us.py or jp.py);
* add a class named as the ISO 3166-1 alpha-2, 2-letter code for the country (all uppercase), deriving from AbstractCountry;
* in the constructor invoke the superclass constructor passing in country code and currency code;
* add the `get_long_term_capital_gain_period()` method with the appropriate value. If there is no long-term capital gains, return `sys.maxsize`;
* `get_default_accounting_method()` method returning accounting method to use if the user doesn't specify one on the command line (e.g. for the US case it's `"fifo"`);
* `get_accounting_methods()` method returning a set of accounting methods that are accepted in the country (e.g. `{"fifo"}`);
* `get_report_generators()`: method returning a set of report generators to use if the user doesn't specify them on the command line;
* `get_default_generation_language()`: method returning the default language (in [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) format) to use at report generation if the user doesn't specify it on the command line;
* `rp2_entry()` global function calling `rp2_main()` and passing it an instance of the new country class (in fact technically subclasses of `AbstractCountry` are entry points, not plugins).

As an example see the [us.py](src/rp2/plugin/country/us.py) file.

Finally add a console script to [setup.cfg](setup.cfg) pointing the new country rp2_entry (see the US example in the console_scripts section of setup.cfg).

## Localization
RP2 supports generation of tax reports in any language via the Babel Python package. For example the JP country plugin accepts the rp2_full_report and the open_positions report generators. The user can use the `-g` command line option to generate Japanese taxes in English, Japanese, or any language for which there are translations (the argument to `-g` is a [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) format, 2-letter string). Translatable strings are enclosed in the code with `_(...)` (see examples in the [rp2_full_report](src/rp2/plugin/report/rp2_full_report.py) plugin).

Localizable strings and their translations are kept in the `src/rp2/locales` directory and here's how to manage them, when strings change in the code:
* generate the main message catalog (locales/messages.pot):
  ```pybabel extract . -o src/rp2/locales/messages.pot --no-wrap --sort-output --copyright-holder=eprbell --project=rp2 --version=`cat .bumpversion.cfg | grep "current_version =" | cut -f3 -d " "` --no-location src ```
* manage language-specific catalogs (which are generated from src/rp2/locales/messages.pot): this step updates locales/&lt;language&gt;/LC_MESSAGES/messages.po:
  * if the .po file doesn't exist, add support for a new language by creating a new translation catalog:

    ```pybabel init --no-wrap -l ja -i src/rp2/locales/messages.pot -d src/rp2/locales```
  * or if the .po file already exists, update the catalog for a language:

     ```pybabel update -i src/rp2/locales/messages.pot -d src/rp2/locales --no-wrap```

* manually translate any new strings: open src/rp2/locales/&lt;language&gt;/LC_MESSAGES/messages.po and add the missing translations in `msgstr` lines. If you don't know how to translate strings for a language leave them blank.

* check for `fuzzy`-marked translations in src/rp2/locales/&lt;language&gt;/LC_MESSAGES/messages.po: sometimes Babel marks a translation as `fuzzy` in the .po file. Such entries must be reviewed manually for correctness and then the `fuzzy` comment must be removed (otherwise that translation doesn't get included at runtime).

* compile the .po file into the final binary format (.mo): this step updates src/rp2/locales/&lt;language&gt;/LC_MESSAGES/messages.mo:

  ```pybabel compile -d src/rp2/locales```


## Frequently Asked Developer Questions
Read the [frequently asked developer questions](docs/developer_faq.md).

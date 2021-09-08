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

# RP2 Developer Guide (Developer)

## Table of Contents
* **[License](#license)**
* **[Design Guidelines](#design-guidelines)**
* **[Contributing and Development Workflow](#contributing-and-development-workflow)**
* **[Source Code](#source-code)**
* **[Plugin Development](#plugin-development)**
* **[Frequently Asked Developer Questions](#faq)**

## License
RP2 is released under the terms of Apache License Version 2.0. For more information see [LICENSE](../LICENSE) or http://www.apache.org/licenses/LICENSE-2.0.

## Contributing and Development Workflow
Read the [Contributing](../CONTRIBUTING.md) document.

## Design Guidelines
RP2 code adheres to these principles:
* immutability: all class fields are private (prepended with double-underscore). Fields that need public access have a read-only property. Write-properties are never used;
* runtime checks: parameters of public functions are type-checked at runtime:
  * `Configuration.type_check_*()` for primitive types;
  * `<class>.type_check()` for classes
* type hints: all variables and functions have Python type hints;
* no id-based hashing: classes that are added to dictionaries and sets redefine `__eq__()`, `__neq__()` and `__hash__()`;
* encapsulated math: all high-precision math is done via `RP2Decimal` (a subclass of Decimal), to ensure the correct precision is used throughout the code. `RP2Decimal` instances are never mixed with other types in expressions;
* f-strings only: every time string interpolation is needed, use f-strings;
* logging: logging is done via `logger.LOGGER`;
* no unnamed tuples: use dataclasses or named tuples;
* no imports with `*`.

## Source Code
The RP2 source tree is organized as follows:
* `bin/`: top level scripts performing requirement/version checks and calling RP2 entry logic;
* `config/`: config files for examples and tests;
* `CONTRIBUTING.md`: contribution guidelines;
* `docs/`: documentation;
* `.github/workflows/`: configuration of Github continuous integration;
* `.gitignore`
* `input/`: examples and tests;
* `input/golden/`: expected outputs that RP2 tests compare against;
* `LICENSE`: license information;
* `Makefile`: it encapsulates several development tasks. It has targets for [installing, linting, reformatting, static checking, unit testing](../CONTRIBUTING.md#development-workflow), etc.;
* `mypy.ini`: Mypy configuration;
* `.pylintrc`: Pylint configuration;
* `README.md`: documentation entry point;
* `requirements.txt`: standard Python dependency file;
* `src/rp2`: RP2 code, including classes for transactions, gains, tax engine, balances, logger, ODS parser, etc.;
* `src/rp2/plugin/output/`: output generator plugins;
* `src/rp2/plugin/output/data/`: spreadsheet templates that are used by the standard output plugins;
* `src/stubs/`: RP2 relies on the pyexcel-ezodf library, which doesn't have typing information, so it is added here;
* `tests/`: unit tests.

## Plugin Development
RP2 has a plugin architecture for output generators, which makes it extensible for new use cases. Writing a new plugin is quite easy: the [8949 form generator](../src/rp2/plugin/output/mock_8949_us.py) is a simple example, the [RP2 report generator](../src/rp2/plugin/output/rp2_report.py) is more comprehensive.

Plugins are discovered by RP2 at runtime and they must adhere to the specific conventions shown below. To add a new plugin follow this procedure:
* add a new Python file in the plugin/output directory and give it a meaningful name
* import the following:
```
from abstract_generator import AbstractGenerator
from computed_data import ComputedData
from gain_loss import GainLoss
from gain_loss_set import GainLossSet
```
* Optionally, RP2 also provides a logger facility:
```
from logger import LOGGER
```
* Add a class named Generator, deriving from AbstractGenerator:
```
class Generator(AbstractGenerator):
```
* Add a generate method with the following signature:
```
    def generate(
        self,
        asset_to_computed_data: Dict[str, ComputedData],
        output_dir_path: str,
        output_file_prefix: str,
    ) -> None:
```
* write the body of the method. The parameters are:
  *  asset_to_computed_data: dictionary mapping user asset (i.e. cryptocurrency) to the computed tax data for that asset. For each user asset there is one instance of [ComputedData](../src/computed_data.py);
  * output_dir_path: directory in which to write the output;
  * output_file_prefix: prefix to be prepended to the output file name

## FAQ
Read the [frequently asked developer questions](developer_faq.md).

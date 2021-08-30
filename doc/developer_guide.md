# RP2 Developer Guide (Developer)

## Table of Contents
* **[License](#license)**
* **[Contributing and Development Workflow](#contributing-and-development-workflow)**
* **[Source Code](#source-code)**
* **[Plugin Development](#plugin-development)**
* **[Frequently Asked Developer Questions](#faq)**

## License
RP2 is released under the terms of Apache License Version 2.0. For more information see [LICENSE](../LICENSE) or http://www.apache.org/licenses/LICENSE-2.0.

## Contributing and Development Workflow
Read the [Contributing](../CONTRIBUTING.md) document.

## Source Code
The RP2 source tree is organized as follows:
* `bin/`: top level scripts performing requirement/version checks and calling RP2 entry logic;
* `config/`: config files for examples and tests;
* `CONTRIBUTING.md`: contribution guidelines;
* `doc/`: documentation;
* `.github/workflows/`: configuration of Github continuous integration;
* `.gitignore`
* `input/`: examples and tests;
* `input/golden/`: expected outputs that RP2 tests compare against;
* `LICENSE`: license information;
* `Makefile`: it encapsulates several development tasks. It has targets for [installing, linting, reformatting, static checking, unit testing](../CONTRIBUTING.md#development-workflow), etc.;
* `mypy.ini`: Mypy configuration;
* `plugin/output/`: output generator plugins;
* `.pylintrc`: Pylint configuration;
* `README.md`: documentation entry point;
* `requirements.txt`: standard Python dependency file;
* `resources/`: spreadsheet templates that are used by the standard plugins;
* `src/`: RP2 code, including classes modeling transactions, gains, tax engine, balances, logger, ODS parser, etc.;
* `stubs/`: RP2 relies on the pyexcel-ezodf library, which doesn't have typing information, so it is added here;
* `test/`: unit tests.

## Plugin Development
RP2 has a plugin architecture for output generators, which makes it extensible for new use cases. Writing a new plugin is quite easy: the [8949 form generator](../plugin/output/mock_8949_us.py) is a simple example, the [RP2 report generator](../plugin/output/rp2_report.py) is more comprehensive.

Plugins are discovered by RP2 at runtime and they must adhere to the specific conventions shown below. To add a new plugin follow this procedure:
- add a new Python file in the plugin/output directory and give it a meaningful name
- import the following:
```
from abstract_generator import AbstractGenerator
from computed_data import ComputedData
from gain_loss import GainLoss
from gain_loss_set import GainLossSet
```
- Optionally, RP2 also provides a logger facility:
```
from logger import LOGGER
```
- Add a class named Generator, deriving from AbstractGenerator:
```
class Generator(AbstractGenerator):
```
- Add a generate method with the following signature:
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

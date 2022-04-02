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

# Contributing to RP2

## Table of Contents
* **[Reporting Bugs](#reporting-bugs)**
* **[Contributing to the Repository](#contributing-to-the-repository)**
  * [Submitting Pull Requests](#submitting-pull-requests)
* **[Contributing with an Ecosystem Project](#contributing-with-an-ecosystem-project)**

## Reporting Bugs
Feel free to submit bugs via [Issue Tracker](https://github.com/eprbell/rp2/issues), but **PLEASE READ THE FOLLOWING FIRST**: RP2 stores logs and outputs locally on the user's machine and doesn't send this data elsewhere. Logs, inputs and outputs can be useful to reproduce a bug, so a user can decide (or not) to share them to help fix a problem. If you decide to share this information, be mindful of what you post or send out: stack traces are typically free of personal data, but RP2 logs, inputs and outputs, while very useful to reproduce an issue, may contain information that can identify you and your transactions. Before posting such data publicly or even sending it privately to the maintainers of RP2, make sure that:
* the data is sanitized of personal information (although this may make it harder to reproduce the problem), or
* you're comfortable sharing your personal data.

Logs are stored in the `log/` directory and each file name is appended with a timestamp. Outputs are stored in the `output/` directory or where specified by the user with the `-o` option.

## Contributing to the Repository
Read the [developer guide](README.dev.md), which describes setup instructions, development workflow, design principles, source tree structure, plugin architecture, etc.

### Submitting Pull Requests
Feel free to submit pull requests. Please follow these practices:
* follow the RP2 [design guidelines](README.dev.md#design-guidelines)
* follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) coding standard;
* add [unit tests](tests/) for any new code;
* ensure your commits are atomic (one feature per commit);
* write a clear log message for your commits.

## Contributing with an Ecosystem Project
Read about the [RP2 Ecosystem](README.md#rp2-ecosystem).
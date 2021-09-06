#!/usr/bin/env python3

# Copyright 2021 eprbell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

from rp2_check_requirements import check_requirements


# This code performs a Python version check: it's written using basic language features (e.g. no type hints, no f-strings,
# etc.) to ensure it parses and runs correctly on old versions of the interpreter.
def main():
    # pylint: disable=import-outside-toplevel
    message = check_requirements()
    if message:
        print(message)
        print("Exiting...")
        sys.exit(1)

    # From here on we can assume the required Python version is available

    # The pathlib module was introduced in Python 3.4, so import is done in-function, after Python version check,
    # to avoid problems with earlier versions of the interpreter.
    from pathlib import Path

    root_path = Path(os.path.dirname(__file__)).parent.absolute()
    sys.path.append(str(root_path / Path("src")))

    try:
        from rp2.rp2_main import rp2_main

        rp2_main()
    except ModuleNotFoundError:
        print("rp2 requirements missing: please read installation instructions in README, then try again.")
        raise


if __name__ == "__main__":
    main()

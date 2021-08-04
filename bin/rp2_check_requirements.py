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

MINIMUM_VERSION = (3, 5, 0)

# This code performs a Python version check: it's written using basic language features (e.g. no type hints, no f-strings,
# etc.) to ensure it parses and runs correctly on old versions of the interpreter.
def check_requirements():
    current_version = (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
    current_version_string = ".".join(str(n) for n in current_version)
    minimum_version_string = ".".join(str(n) for n in MINIMUM_VERSION)
    if current_version < MINIMUM_VERSION:
        return "Python version {} or higher required. Installed version is {}".format(minimum_version_string, current_version_string)

    # From here on we can assume the required Python version is available

    # The shutil.which function was introduced in Python 3.3, so import is done in-function, after Python version check,
    # to avoid problems with earlier versions of the interpreter.
    from shutil import which

    # virtualenv is required by the RP2 makefile. When RP2 is ran outside the makefile, it doesn't necessarily need virtualenv (e.g. Github servers)
    if "RP2_MAKEFILE" in os.environ and which("virtualenv") is None:
        return "virtualenv not found: please install it."

    if which("pip3") is None:
        return "pip3 not found: please install it."

    return None


def main():
    message = check_requirements()
    if message:
        print(message)
        sys.exit(1)


if __name__ == "__main__":
    main()

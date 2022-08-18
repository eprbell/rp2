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

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

LOG_FILE: str = f"./log/rp2_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')}.log"
Path("./log").mkdir(parents=True, exist_ok=True)


def create_logger(logger_name: str = "rp2") -> logging.Logger:
    logger: logging.Logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    _console_handler: logging.StreamHandler = logging.StreamHandler()
    _console_format: logging.Formatter = logging.Formatter("%(levelname)s: %(message)s")
    _console_handler.setLevel(logging.INFO)
    _console_handler.setFormatter(_console_format)

    _file_handler: logging.FileHandler = logging.FileHandler(LOG_FILE)
    _file_format: logging.Formatter = logging.Formatter("%(asctime)s/%(name)s/%(levelname)s: %(message)s")
    _log_level: Optional[str] = os.environ.get("LOG_LEVEL")
    _log_level = "INFO" if not _log_level else _log_level
    _file_handler.setLevel(_log_level)
    _file_handler.setFormatter(_file_format)

    logger.addHandler(_console_handler)
    logger.addHandler(_file_handler)

    return logger


LOGGER: logging.Logger = create_logger()

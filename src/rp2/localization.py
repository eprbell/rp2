# Copyright 2022 eprbell
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

import gettext
import os
from pathlib import Path

from babel import Locale
from babel.core import UnknownLocaleError

from rp2.rp2_error import RP2TypeError, RP2ValueError

_ = gettext.gettext


def set_generation_language(generation_language: str) -> None:
    global _  # pylint: disable=global-statement
    locales_dir = Path(os.path.dirname(__file__)).absolute() / Path("locales")
    if not isinstance(generation_language, str):
        raise RP2TypeError(f"generation_language parameter is not a string: {generation_language}")
    try:
        Locale(generation_language)
        translation = gettext.translation("messages", localedir=str(locales_dir), languages=[generation_language])
    except UnknownLocaleError as exc:
        raise RP2ValueError(f"Unrecognized language: {generation_language}") from exc
    except FileNotFoundError as exc:
        raise RP2ValueError(f"No translation found for language: {generation_language}") from exc

    translation.install()
    _ = translation.gettext

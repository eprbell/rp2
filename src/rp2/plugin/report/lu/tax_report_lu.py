# Copyright 2026 eprbell
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
from datetime import date
from typing import Dict

from rp2.abstract_country import AbstractCountry
from rp2.computed_data import ComputedData
from rp2.logger import create_logger
from rp2.plugin.report.be.tax_report_be import Generator as TaxReportBEGenerator

LOGGER: logging.Logger = create_logger("tax_report_lu")


class Generator(TaxReportBEGenerator):
    OUTPUT_FILE: str = "tax_report_lu.ods"
    TEMPLATE_NAME: str = "tax_report_lu"

    def generate(
        self,
        country: AbstractCountry,
        years_2_accounting_method_names: Dict[int, str],
        asset_to_computed_data: Dict[str, ComputedData],
        output_dir_path: str,
        output_file_prefix: str,
        from_date: date,
        to_date: date,
        generation_language: str,
    ) -> None:
        output_file = self._generate(
            country, years_2_accounting_method_names, asset_to_computed_data, output_dir_path, output_file_prefix, from_date, to_date, generation_language
        )
        LOGGER.info("Plugin '%s' output: %s", __name__, output_file.resolve())

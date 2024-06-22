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

# Supported Countries

## Table of Contents
* **[Introduction](#introduction)**
* **[Countries](#countries)**
  * [Ireland](#ireland)
  * [Japan](#japan)
  * [Spain](#Spain)
  * [USA](#usa)

## Introduction
RP2 supports multiple countries each of which has different accounting methods and report generators, as explained in the sections below.

## Countries

### Ireland
* Accounting methods (note that in Ireland [specific](https://www.revenue.ie/en/tax-professionals/tdm/income-tax-capital-gains-tax-corporation-tax/part-19/19-04-03.pdf) [rules](https://www.revenue.ie/en/gains-gifts-and-inheritance/transfering-an-asset/selling-or-disposing-of-shares.aspx) apply to assets bought and sold within a 4 week window: this is **NOT** yet supported by RP2):
  * [FIFO](https://www.investopedia.com/terms/f/fifo.asp)
* [Output generators](https://github.com/eprbell/rp2/blob/main/docs/output_files.md):
  * [rp2_full_report](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#rp2-full-report-transparent-computation): comprehensive report (valid for any country), with complete transaction history, lot relationships/fractions and computation details;
  * [tax_report_ie](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#tax-report-ie-advisor-friendly-report): tax report meant to be read by tax preparers;
  * [open_positions](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#open-positions-report-unrealized-gains): report on assets with non-zero crypto balance (valid for any country): unrealized gains / losses, portfolio weighting, and more.
* Ireland-specific RP2 executable: `rp2_ie`.

### Japan
RP2 support for Japan includes the following features:
* Accounting methods:
  * Total Average Method;
* [Output generators](https://github.com/eprbell/rp2/blob/main/docs/output_files.md):
  * [rp2_full_report](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#rp2-full-report-transparent-computation): comprehensive report (valid for any country), with complete transaction history, lot relationships/fractions and computation details;
  * [tax_report_jp](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#tax-report-jp-advisor-friendly-report): Japan-specific tax report meant to be read by tax preparers;
  * [open_positions](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#open-positions-report-unrealized-gains): report on assets with non-zero crypto balance (valid for any country): unrealized gains / losses, portfolio weighting, and more.
* Japan-specific RP2 executable: `rp2_jp`.

### Spain
RP2 support for Spain includes the following features:
* Accounting methods:
  * [FIFO](https://www.investopedia.com/terms/f/fifo.asp).
* [Output generators](https://github.com/eprbell/rp2/blob/main/docs/output_files.md):
  * [rp2_full_report](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#rp2-full-report-transparent-computation): comprehensive report (valid for any country), with complete transaction history, lot relationships/fractions and computation details;
  * [open_positions](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#open-positions-report-unrealized-gains): report on assets with non-zero crypto balance (valid for any country): unrealized gains / losses, portfolio weighting, and more.
* Spain-specific RP2 executable: `rp2_es`.

### USA
RP2 support for the US includes the following features:
* Accounting methods (note that these methods use [universal application](https://www.forbes.com/sites/shehanchandrasekera/2020/09/17/what-crypto-taxpayers-need-to-know-about-fifo-lifo-hifo-specific-id/), not per-wallet application):
  * [FIFO](https://www.investopedia.com/terms/f/fifo.asp),
  * [LIFO](https://www.investopedia.com/terms/l/lifo.asp),
  * [HIFO](https://www.investopedia.com/terms/h/hifo.asp).
* [Output generators](https://github.com/eprbell/rp2/blob/main/docs/output_files.md):
  * [rp2_full_report](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#rp2-full-report-transparent-computation): comprehensive report (valid for any country), with complete transaction history, lot relationships/fractions and computation details;
  * [tax_report_us](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#tax-report-us-advisor-friendly-report): tax report meant to be read by tax preparers (in the format of form 8949);
  * [open_positions](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#open-positions-report-unrealized-gains): report on assets with non-zero crypto balance (valid for any country): unrealized gains / losses, portfolio weighting, and more.
* US-specific RP2 executable: `rp2_us`.

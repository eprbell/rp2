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

# Supported Countries and Accounting Methods

## Table of Contents
* **[Introduction](#introduction)**
* **[Accounting Methods](#accounting-methods)**
* **[Countries](#countries)**
  * [Generic](#generic)
  * [Ireland](#ireland)
  * [Japan](#japan)
  * [Spain](#Spain)
  * [USA](#usa)
    * [Per-Wallet Application from 2025](#per-wallet-application-from-2025)
    * [US Sources](#us-sources)

## Introduction
RP2 supports most countries each of which has different accounting methods and report generators, as explained in the sections below. Some countries have direct support (by means of a country-specific RP2 plugin), but other countries can still benefit from RP2 via the generic country plugin (see below).

## Accounting Methods
RP2 supports the following accounting methods (although not all countries support all accounting methods):
  * [FIFO](https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting): lots acquired first are disposed of first;
  * [LIFO](https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting): lots acquired last are disposed of first (opposite of FIFO);
  * [HIFO](https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting): highest priced lots are disposed of first;
  * LOFO: lowest priced lots are disposed of first (opposite of HIFO).

## Countries

### Generic
This is a placeholder country that is meant to be used by people of countries that are yet unsupported by RP2. It produces a country-agnostic, detailed report and supports all RP2 accounting methods (which can be selected with the `-m` option). It requires the definition of two environment variables:
* `CURRENCY_CODE`: [ISO 4217](https://en.wikipedia.org/wiki/ISO_4217) string representing the currency used;
* `LONG_TERM_CAPITAL_GAINS`: period in days after which sold assets trigger long-term capital gains instead of short-term ones (for the US this value is 365). For countries that don't have short/long-term capital gains a very large number can be used (e.g. 1000000000).
To set environment variables for the generic RP2 executable on Unix-like systems:
```
CURRENCY_CODE=eur LONG_TERM_CAPITAL_GAINS=1000000000 rp2_generic...
```
To set environment variables for the generic RP2 executable on Windows systems:
```
Set CURRENCY_CODE=eur LONG_TERM_CAPITAL_GAINS=1000000000 rp2_generic...
```
RP2 Generic supports the following features:
* Generic RP2 executable: `rp2_generic`.
* Accounting methods (note that these methods use [universal application](https://www.forbes.com/sites/shehanchandrasekera/2020/09/17/what-crypto-taxpayers-need-to-know-about-fifo-lifo-hifo-specific-id/), not per-wallet application):
  * [FIFO](https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting),
  * [LIFO](https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting),
  * [HIFO](https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting),
  * LOFO.
* [Output generators](https://github.com/eprbell/rp2/blob/main/docs/output_files.md):
  * [rp2_full_report](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#rp2-full-report-transparent-computation): comprehensive report (valid for any country), with complete transaction history, lot relationships/fractions and computation details;
  * [open_positions](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#open-positions-report-unrealized-gains): report on assets with non-zero crypto balance (valid for any country): unrealized gains / losses, portfolio weighting, and more.

### Ireland
RP2 support for Ireland includes the following features:
* Ireland-specific RP2 executable: `rp2_ie`.
* Accounting methods (note that in Ireland [specific](https://www.revenue.ie/en/tax-professionals/tdm/income-tax-capital-gains-tax-corporation-tax/part-19/19-04-03.pdf) [rules](https://www.revenue.ie/en/gains-gifts-and-inheritance/transfering-an-asset/selling-or-disposing-of-shares.aspx) apply to assets bought and sold within a 4 week window: this is **NOT** yet supported by RP2):
  * [FIFO](https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting).
* [Output generators](https://github.com/eprbell/rp2/blob/main/docs/output_files.md):
  * [rp2_full_report](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#rp2-full-report-transparent-computation): comprehensive report (valid for any country), with complete transaction history, lot relationships/fractions and computation details;
  * [tax_report_ie](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#tax-report-ie-advisor-friendly-report): tax report meant to be read by tax preparers;
  * [open_positions](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#open-positions-report-unrealized-gains): report on assets with non-zero crypto balance (valid for any country): unrealized gains / losses, portfolio weighting, and more.

### Japan
RP2 support for Japan includes the following features:
* Japan-specific RP2 executable: `rp2_jp`.
* Accounting methods:
  * [Total Average Method](https://en.wikipedia.org/wiki/Average_cost_method).
* [Output generators](https://github.com/eprbell/rp2/blob/main/docs/output_files.md):
  * [rp2_full_report](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#rp2-full-report-transparent-computation): comprehensive report (valid for any country), with complete transaction history, lot relationships/fractions and computation details;
  * [tax_report_jp](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#tax-report-jp-advisor-friendly-report): Japan-specific tax report meant to be read by tax preparers;
  * [open_positions](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#open-positions-report-unrealized-gains): report on assets with non-zero crypto balance (valid for any country): unrealized gains / losses, portfolio weighting, and more.

### Spain
RP2 support for Spain includes the following features:
* Spain-specific RP2 executable: `rp2_es`.
* Accounting methods:
  * [FIFO](https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting).
* [Output generators](https://github.com/eprbell/rp2/blob/main/docs/output_files.md):
  * [rp2_full_report](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#rp2-full-report-transparent-computation): comprehensive report (valid for any country), with complete transaction history, lot relationships/fractions and computation details;
  * [open_positions](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#open-positions-report-unrealized-gains): report on assets with non-zero crypto balance (valid for any country): unrealized gains / losses, portfolio weighting, and more.

### USA
RP2 support for the US includes the following features:
* US-specific RP2 executable: `rp2_us`.
* Accounting methods:
  * [FIFO](https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting),
  * [LIFO](https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting),
  * [HIFO](https://en.wikipedia.org/wiki/FIFO_and_LIFO_accounting),
  * LOFO.
* Application of the accounting methods: [universal application](https://www.forbes.com/sites/shehanchandrasekera/2020/09/17/what-crypto-taxpayers-need-to-know-about-fifo-lifo-hifo-specific-id/) until 2024, per-wallet application from 2025 (experimental: see [below](#per-wallet-application-from-2025)). RP2 selects it automatically, and a report that needs per-wallet application also needs the `country.us` section of the [config file](input_files.md#the-config-file) (see [How Do I Use Per-Wallet Application?](user_faq.md#how-do-i-use-per-wallet-application)).
* Holding period: a gain is long-term if the asset was held more than one year ([IRC §1222](https://www.law.cornell.edu/uscode/text/26/1222)). Counting starts on the day after the acquisition and includes the day of the sale ([Publication 544](https://www.irs.gov/publications/p544), "Holding period"), so RP2 compares calendar dates: a sale is long-term only if its date is after the first anniversary of the acquisition date, and the time of day doesn't matter. E.g. a coin bought on June 17, 2024 is short-term if sold on June 17, 2025 and long-term if sold on June 18, 2025. A coin bought on March 1st, 2023 and sold on March 1st, 2024 is short-term, although the period has 366 days (because of February 29th). Transferred and allocated units keep their original acquisition date.
* [Output generators](https://github.com/eprbell/rp2/blob/main/docs/output_files.md):
  * [rp2_full_report](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#rp2-full-report-transparent-computation): comprehensive report (valid for any country), with complete transaction history, lot relationships/fractions and computation details;
  * [tax_report_us](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#tax-report-us-advisor-friendly-report): tax report meant to be read by tax preparers (in the format of form 8949);
  * [open_positions](https://github.com/eprbell/rp2/blob/main/docs/output_files.md#open-positions-report-unrealized-gains): report on assets with non-zero crypto balance (valid for any country): unrealized gains / losses, portfolio weighting, and more;
  * [opening_allocation](output_files.md#opening-allocation-report-unused-basis-at-the-switch): how the unused basis was assigned to the wallets on January 1st, 2025, if the report reaches it.

#### Per-Wallet Application from 2025
How RP2 implements the US rules (the sources are listed [below](#us-sources)):
* **Wallet by wallet from 2025**: the basis rules of [Treas. Reg. §1.1012-1(j)](https://www.ecfr.gov/current/title-26/section-1.1012-1#p-1.1012-1(j)) "apply the specific identification or FIFO rules to units held within a single wallet or account" ([Rev. Proc. 2024-28](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=5), section 2), and they apply to "all acquisitions and dispositions of digital assets on or after January 1, 2025" ([§1.1012-1(j)(6)](https://www.ecfr.gov/current/title-26/section-1.1012-1#p-1.1012-1(j)(6))). RP2 uses universal application until 2024 and per-wallet application from 2025. A per-wallet history before 2025 is not supported.
* **The switch**: "as of January 1, 2025" means "immediately after the close of the taxpayer's day on December 31, 2024" ([Rev. Proc. 2024-28](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=8), section 3.10), so the `timezone` field of the `country.us` section is your time zone. Form 1099-DA reports the date of a sale without a time zone ([Instructions for Form 1099-DA](https://www.irs.gov/instructions/i1099da), box 1e), so a broker's dates near midnight can differ from RP2's.
* **Opening allocation**: RP2 implements the "global allocation" of Rev. Proc. 2024-28 ([section 5.02(2)(b)](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=12)): a rule that orders the unused basis and assigns it to the wallets (`unused_basis_allocation_method` and `unused_basis_allocation_wallet_order`). The safe harbor applies to each type of digital asset separately ([section 4.01(4)](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=9)), so the rule can be overridden for each coin. Each allocated unit keeps its original basis and acquisition date ([sections 3.03](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=6) and [3.04](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=7)). The "specific unit allocation" (section 5.02(2)(a)) and importing an allocation made elsewhere are not supported. RP2 can't check these requirements, which depend on your records:
  * the global allocation method must be described in your books and records before January 1, 2025 ([section 5.02(5)(a)](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=14)): configure the rule you recorded then;
  * the allocation must be completed before the later of the first sale, disposition or transfer of the coin on or after January 1, 2025 and the due date (with extensions) of your 2025 return ([sections 5.02(4)](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=13) and [5.02(5)(b)](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=14)). Until then, the units held since before 2025 can be specifically identified only with a standing order ([section 5.02(5)(c)](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=14));
  * you must keep records of the units in each wallet and of the unused basis (units, original cost basis and acquisition date), and the allocation is irrevocable ([section 4.02(4)-(6)](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=10));
  * the safe harbor covers how the unused basis is allocated, not its amount, which must be substantiated separately ([section 5.04](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf#page=16)). RP2 computes the unused basis from your transactions, so it's only as accurate as your input.
* **Transfers between your wallets**: they aren't taxable, "except to the extent of any digital assets you use, or are withheld, to pay for transaction services to effect the transfer" ([IRS FAQ](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions) A81), and those units are disposed of, with a gain or loss (A97): RP2 reports the fee as a disposal. A fee for a transfer between your own wallets is not a digital asset transaction cost (A53), so RP2 doesn't add it to the basis of the units that arrive. Without a specific identification, units are disposed of in order of time from the earliest acquisition date, and the date units were transferred into the wallet, or into the custody of the broker, is disregarded ([§1.1012-1(j)(1)](https://www.ecfr.gov/current/title-26/section-1.1012-1#p-1.1012-1(j)(1)) and [(j)(3)(i)](https://www.ecfr.gov/current/title-26/section-1.1012-1#p-1.1012-1(j)(3)(i))): RP2's per-wallet FIFO orders lots by their original acquisition date.
* **LIFO, HIFO and LOFO** select specific units, which needs an identification no later than the date and time of the sale, disposition or transfer: on your books and records for units not held by a broker ([§1.1012-1(j)(2)](https://www.ecfr.gov/current/title-26/section-1.1012-1#p-1.1012-1(j)(2))), to the broker for units held by a broker, e.g. with a standing order ([(j)(3)(ii)](https://www.ecfr.gov/current/title-26/section-1.1012-1#p-1.1012-1(j)(3)(ii))). For units held by a broker, [Notice 2025-7](https://www.irs.gov/pub/irs-drop/n-25-07.pdf) and [Notice 2026-20](https://www.irs.gov/pub/irs-drop/n-26-20.pdf) also accept an identification (or a standing order) on your own books and records, from January 1, 2025 through December 31, 2026, under their conditions: with the safe harbor of Rev. Proc. 2024-28, only after its requirements are met (Notice 2026-20, section 4.04). The notices don't postpone per-wallet application. RP2 can't make an identification after the fact: the method you configure must be the one you identified at the time.
* **What a wallet is**: "a means of storing, electronically or otherwise, a user's private keys to digital assets held by or for the user", and a digital asset is held in a wallet if the wallet "stores the private keys necessary to transfer control" of it, including assets at addresses generated by the wallet and in its sub-ledger accounts ([Treas. Reg. §1.6045-1(a)(25)](https://www.ecfr.gov/current/title-26/section-1.6045-1#p-1.6045-1(a)(25)), (i) and (iv); see also [IRS FAQ](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions) A54). Enter each wallet or account as its own exchange/holder pair (see [What Counts as a Wallet?](user_faq.md#what-counts-as-a-wallet)).
* **Current limitations**: the reports don't show yet the wallet of each lot and disposal, nor distinguish covered from noncovered assets, which are needed to reconcile with Form 1099-DA and to fill the Form 8949 boxes. Transfers between holders are treated as transfers between wallets (the lots keep their basis), not as gifts.

#### US Sources
Checked on November 3, 2026, with the date of each source:
* [Treas. Reg. §1.1012-1(j)](https://www.ecfr.gov/current/title-26/section-1.1012-1#p-1.1012-1(j)) and [§1.6045-1(a)(25)](https://www.ecfr.gov/current/title-26/section-1.6045-1#p-1.6045-1(a)(25)): added by T.D. 10000, published on July 9, 2024. §1.1012-1(j) applies to acquisitions and dispositions on or after January 1, 2025.
* [Rev. Proc. 2024-28](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf): released on June 28, 2024 (2024-31 I.R.B. 326). It covers the allocation as of January 1, 2025 of units acquired before that date.
* [Notice 2025-7](https://www.irs.gov/pub/irs-drop/n-25-07.pdf): 2025-5 I.R.B. 524 (January 27, 2025), relief for 2025. [Notice 2026-20](https://www.irs.gov/pub/irs-drop/n-26-20.pdf): 2026-15 I.R.B. 800 (April 6, 2026), extends the relief through December 31, 2026.
* [IRS FAQ on digital asset transactions](https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions): answers 53, 54, 81 and 97 added on December 15, 2025 (page updated on June 29, 2026).
* [IRC §1222](https://www.law.cornell.edu/uscode/text/26/1222) and [Publication 544](https://www.irs.gov/publications/p544) (2025 edition, page updated on April 30, 2026).
* [Instructions for Form 1099-DA](https://www.irs.gov/instructions/i1099da) (2026 edition, page updated on April 30, 2026).

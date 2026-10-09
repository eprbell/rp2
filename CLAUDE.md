<!--- Copyright 2026 Neal Chambers --->

<!--- Licensed under the Apache License, Version 2.0 (the "License"); --->
<!--- you may not use this file except in compliance with the License. --->
<!--- You may obtain a copy of the License at --->

<!---     http://www.apache.org/licenses/LICENSE-2.0 --->

<!--- Unless required by applicable law or agreed to in writing, software --->
<!--- distributed under the License is distributed on an "AS IS" BASIS, --->
<!--- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. --->
<!--- See the License for the specific language governing permissions and --->
<!--- limitations under the License. --->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RP2 is a privacy-focused, open-source cryptocurrency tax calculator written in Python 3.8+. It computes capital gains/losses from crypto transactions using pluggable accounting methods (FIFO, LIFO, HIFO, LOFO) and generates country-specific tax reports. All computation runs locally — no network calls.

## Development Setup

```bash
virtualenv -p python3 .venv
. .venv/bin/activate
.venv/bin/pip3 install -e '.[dev]'
```

## Common Commands

```bash
# Tests
pytest --tb=native --verbose              # all tests
pytest tests/test_accounting_method.py -v # single file
pytest tests/ -k "test_fifo" -v           # by pattern

# Static analysis
mypy src/ tests/
pylint -r y src tests/*.py
bandit -r src/

# Formatting
black src/ tests/
isort .

# Make targets
make all               # build virtualenv
make check             # run all tests
make static_analysis   # mypy + pylint + bandit
make run               # run example files
```

## Architecture

### Data Flow

#### Universal (single global lot pool — existing path)

```
Config file (INI) + Input ODS spreadsheet
  ↓
configuration.py → rp2_configuration_translator (optional migration)
  ↓
ods_parser.py → InputData (all transactions by asset, single pool)
  ↓
tax_engine.compute_tax(): for each asset:
  - InputData.create_unfiltered_taxable_event_set() builds taxable event set
  - AccountingEngine pairs in/out lots via selected accounting method
  - produces GainLoss objects
  ↓
ComputedData (asset → GainLossSet)
  ↓
plugin/report/ generators → ODS output files + logs
```

#### Per-Wallet (selected by the country's application policy, e.g. US from 2025; no CLI flag)

```
Config file (INI, with [country.us] section) + Input ODS spreadsheet
  ↓
ods_parser.py → InputData (universal: all transactions by asset)
  ↓
tax_engine.compute_tax_per_wallet():
  - rp2_main resolves each asset's mode per year from country.get_application_policy() (ApplicationPolicy) and the optional
    application_mode choice; per-wallet years need the [country.us] per-wallet fields (else RP2ValueError, no silent fallback)
  - switch instant = Jan 1 of the first per-wallet policy period, in [country.us] timezone;
    transactions whose own-timestamp year disagrees with the switch → RP2ValueError (never guessed)
  - before the switch: universal application, identical to compute_tax()
  - at the switch: UnusedBasisAllocator assigns the lots still unused under universal application to the
    wallets holding funds (Rev. Proc. 2024-28 global allocation; explicit config if > 1 funded wallet),
    as artificial InTransactions (from_lot = original lot, same per-unit basis and acquisition date)
  - after the switch: TransferAnalyzer(...).analyze_and_pair() processes transactions chronologically
    (same timestamp: In, Intra, Out, then row), per wallet, with the accounting method of each year:
      InTransaction → lot added to its wallet (earn types → income GainLoss)
      OutTransaction → lots taken from its wallet only → GainLoss per lot piece
      IntraTransaction → fee paid first (always a disposal GainLoss: IRS FAQ A81/A97), received units
        become artificial InTransactions in the destination
        (cycles A→B→A return units to the lot they left A from, e.g. the lot allocated to A at the switch)
  - TransferAnalyzer also records what each wallet holds at the end of the report's to_date (WalletLot list, only if to_date is on or
    after the switch): ComputedData.wallet_lots, used by the open positions report for each wallet's actual cost basis
  ↓
ComputedData (asset → GainLossSet: universal pre-switch + per-wallet post-switch; wallet_lots)
  ↓
plugin/report/ generators → ODS output files + logs
```

### Plugin Architecture

Plugins are auto-discovered via `pkgutil.iter_modules()`:

- `src/rp2/plugin/accounting_method/` — one file per method (fifo.py, lifo.py, etc.)
- `src/rp2/plugin/country/` — country entry points and country-specific report configs
- `src/rp2/plugin/report/` — report generators (abstract_report_generator.py + concrete implementations)

Country-specific CLI entry points (e.g., `rp2_us`, `rp2_jp`) each call `rp2_main()` with a country object that specifies which report generators and accounting methods apply.

### Key Classes

| Class | File | Role |
|---|---|---|
| `AbstractEntry` | `abstract_entry.py` | Base for all entries; immutable |
| `InTransaction` | `in_transaction.py` | Acquisitions (BUY, MINING, STAKING, etc.) |
| `OutTransaction` | `out_transaction.py` | Sales/disposals |
| `IntraTransaction` | `intra_transaction.py` | Internal transfers |
| `GainLoss` | `gain_loss.py` | A computed gain/loss for one lot fraction |
| `AccountingEngine` | `accounting_engine.py` | Pairs lots using accounting method |
| `TaxEngine` | `tax_engine.py` | Orchestrates per-asset computation |
| `RP2Decimal` | `rp2_decimal.py` | High-precision Decimal subclass; use for all math |
| `Account` | `account.py` | Frozen `(exchange, holder)` wallet identity; key in per-wallet dicts |
| `PerWalletTransactions` | `transfer_analyzer.py` | Lots (with per-method heaps), actual amounts and out/intra sets of one wallet during transfer analysis |
| `TransferAnalyzer` | `transfer_analyzer.py` | Per-wallet engine: decomposes `InputData` into per-wallet `InputData` and pairs taxable events with lots of their wallet (`analyze_and_pair()`) |
| `AcquisitionDateFifo` | `acquisition_date_fifo.py` | Per-wallet FIFO: orders lots by original acquisition date (`cost_basis_timestamp`), not arrival date |
| `WalletLot` | `wallet_lot.py` | Per-wallet inventory: the units of one lot held by one wallet at the report's to_date (amount, cost basis, original acquisition date and lot); `ComputedData.wallet_lots` (None in universal application) |
| `UnusedBasisAllocator` | `unused_basis_allocator.py` | [Rev. Proc. 2024-28](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf) global allocation of unused lots to wallets at the per-wallet switch |
| `PerWalletConfiguration` | `per_wallet_configuration.py` | per-wallet fields of the `[country.<code>]` config section: timezone, unused basis allocation rule (default plus per-asset overrides, `<field>.<asset>`) |
| `ApplicationPolicy` | `application_policy.py` | Per-year allowed/default `ApplicationMode` (universal, per-wallet) of a country (`AbstractCountry.get_application_policy()`); resolves the user's optional `application_mode` and the per-wallet switch year |
| `GlobalAllocator` | `global_allocation.py` | Earlier, unwired prototype of global allocation (superseded by `UnusedBasisAllocator`) |

### Design Conventions

- **Immutability**: dataclasses use `frozen=True`; fields are private (`__field`) with read-only `@property` accessors.
- **Runtime type checking**: every public method calls `type_check_*()` helpers at entry; don't skip these.
- **Precision**: all monetary/quantity values use `RP2Decimal`, never plain `float`.
- **14 transaction types** are defined in `entry_types.py` as `TransactionType` enum — understand these before adding logic.

### Testing

- `input/golden/` holds expected ODS outputs for regression tests.
- `tests/rp2_test_output.py` provides helpers for comparing actual vs. expected output.
- Output-diff tests (`test_ods_output_diff_*.py`) are per-country and catch report formatting regressions.
- `tests/test_gain_loss.py` contains unit tests that verify IRS-rule-level correctness. Each test cites the governing IRS authority:
  - `test_ltcg_boundary` — IRS FAQ Q50 / [IRC §1222](https://www.law.cornell.edu/uscode/text/26/1222) (holding period >365 days for LTCG)
  - `test_earn_type_income_recognition` — earn types (HARDFORK, AIRDROP, MINING, STAKING, WAGES, INCOME) produce ordinary income at FMV with no cost basis ([Rev. Rul. 2019-24](https://www.irs.gov/pub/irs-drop/rr-19-24.pdf), [Notice 2014-21](https://www.irs.gov/pub/irs-drop/n-14-21.pdf), [Rev. Rul. 2023-14](https://www.irs.gov/pub/irs-drop/rr-23-14.pdf), FAQ Q57-61, [IRC §61](https://www.law.cornell.edu/uscode/text/26/61))
  - `test_donate_gift_disposal_gain_loss` — DONATE/GIFT disposals compute gain/loss identically to SELL (IRS FAQ Q75-78, [Notice 2014-21](https://www.irs.gov/pub/irs-drop/n-14-21.pdf))
  - `test_holding_period_resets_after_exchange` — received asset's holding period starts fresh on exchange date (IRS FAQ Q74)
  - `test_fee_out_transaction_gain_loss` — FEE-typed disposal recognises gain/loss on crypto used to pay fees (IRS FAQ Q97, [Notice 2014-21](https://www.irs.gov/pub/irs-drop/n-14-21.pdf))
  - `test_good_non_interest_gain_loss` — intra-transaction crypto fee is a taxable disposal (IRS FAQ Q81/Q97, [Notice 2014-21](https://www.irs.gov/pub/irs-drop/n-14-21.pdf))

#### Per-Wallet and Global Allocation Tests (new)

- `tests/test_per_wallet_tax_engine.py` — end-to-end, hand-computed examples for `compute_tax_per_wallet` (edge cases: fees, #149, holding period, allocation, timezone boundary, same-timestamp order, cycles, method change, dust).
- `tests/test_per_wallet_reports.py` — per-wallet report output, checked in actual ODS cells (transfer fees, remaining basis, artificial lots).
- `tests/per_wallet_common.py` — shared helpers of the two files above: short-form transactions (`_In`, `_Out`, `_Intra`), expected gain/losses, wallets and `AbstractPerWalletTest`.
- `tests/test_per_wallet_properties.py` — hypothesis property tests: wallet lots = wallet balance after each step, basis/lot conservation, single wallet per-wallet == universal, JP universal results unaffected.
- `tests/test_ods_output_diff_per_wallet.py` — CLI: country section doesn't change pre-2025 output; 2025 data needs `[country.us]`; conflicting `application_mode` and other countries' sections are rejected; `-w` no longer exists.
- `tests/test_application_policy.py` — `ApplicationPolicy`: per-year modes, explicit choices, switch year, policy validation.

- `tests/test_transfer_analysis_semantics_independent.py` — transfer analysis tests whose expected results do not depend on which accounting method is used for transfer semantics (e.g., single-lot transfers).
- `tests/test_transfer_analysis_semantics_dependent.py` — transfer analysis tests whose results differ based on FIFO vs. LIFO vs. HIFO transfer semantics.
- `tests/test_global_allocation.py` — end-to-end tests for `GlobalAllocator`, verifying that the generated artificial IntraTransactions correctly reallocate lots across wallets.
- `tests/transfer_analysis_common.py` — shared helpers for building `TransferAnalyzer` test fixtures.
- `tests/global_allocation_common.py` — shared helpers for building `GlobalAllocator` test fixtures.
- `tests/transaction_processing_common.py` — low-level helpers for constructing transactions and per-wallet InputData from descriptor dicts.

## Known Limitations and Tax Law Notes

These are intentional design decisions or known constraints to keep in mind when modifying the engine.

### LTCG Holding Period (fixed)
`GainLoss.is_long_term_capital_gains()` delegates to `AbstractCountry.is_long_term_capital_gain(acquisition, disposal)`. The default compares whole days with `get_long_term_capital_gain_period()` (strictly greater). The US overrides it with the calendar rule of [IRC §1222](https://www.law.cornell.edu/uscode/text/26/1222) / [IRS Publication 544](https://www.irs.gov/publications/p544): counting starts the day after acquisition and includes the day of disposal, so a sale is long-term only if its date is after the first anniversary of the acquisition date. Exactly one year is short-term even when it spans February 29th (366 days); time of day doesn't matter.

### DONATE and GIFT Tax Treatment
RP2 computes gain/loss for `DONATE` and `GIFT` out-transactions using the same formula as `SELL`. This is intentional — the output tabs give tax professionals the data they need. However, the actual tax treatment differs from a sale:
- **DONATE to 501(c)(3):** No capital gains tax; the donor may instead deduct the FMV as a charitable contribution.
- **GIFT:** No capital gains tax for the giver; recipient inherits the giver's cost basis.

Do not change `OutTransaction.is_taxable()` to return `False` for these types without also updating all downstream report generators to handle them differently.

### IntraTransaction Fees Are Taxable Events
When `crypto_sent > crypto_received`, `IntraTransaction.is_taxable()` returns `True` and the fee generates a gain/loss entry. This is correct under IRS [Notice 2014-21](https://www.irs.gov/pub/irs-drop/n-14-21.pdf) but surprises users who expect wallet-to-wallet transfers to be tax-free. See `user_faq.md` for the user-facing explanation.

### Slashing / Negative Staking Income
RP2 has no dedicated slash transaction type. Involuntary stake losses (slashing) must be entered as an `OutTransaction` with `transaction_type = STAKING`. In-transaction amounts must be positive — do not enter negative `crypto_in` values.

### Crypto Precision
`RP2Decimal` uses 13 decimal places for crypto amounts (`CRYPTO_DECIMALS = 13`). Ethereum and other EVM chains use 18 decimal places (wei). Transaction amounts with more than 13 significant decimal digits will be truncated. For dust amounts this may cause minor discrepancies against on-chain records.

### Same-Timestamp Ordering
When two transactions share the same timestamp, their relative order is determined by their row number in the input spreadsheet. For LIFO and HIFO methods, swapping same-timestamp rows changes which lot is selected, potentially altering the tax outcome with no warning. In per-wallet application `TransferAnalyzer` orders same-timestamp transactions as In, Intra, Out, then by row, so funds that arrive at an instant can be disposed of at the same instant.

### Universal Lot Pool (default path)
All accounting methods (FIFO, LIFO, HIFO, LOFO) operate on a single global pool of lots per asset, regardless of which exchange or wallet the lots are held in. Per-wallet application is selected per year by the country's `get_application_policy()` (currently only the US allows it, from 2025) and needs the `[country.us]` config section. Balance enforcement IS per-account (via `BalanceSet`), but lot selection is global in the universal path.

### Artificial InTransactions (per-wallet path only)
`TransferAnalyzer` creates artificial `InTransaction` objects to model the "to" side of each `IntraTransaction`. These artificial transactions exist only in per-wallet `InputData` objects — they are never present in the original universal `InputData` returned by `ods_parser.py`. Identifying fields: `from_lot is not None`. The fields `from_lot`, `to_lots`, and `originates_from` are only meaningful on artificial InTransactions. `from_lot` is the cost-basis history (it continues past an allocated lot to the input lot bought before the switch); `originates_from` is the lot each earlier wallet actually held, used to return units at the end of a round trip, and never goes past an allocated lot.

### cost_basis_timestamp and LTCG (per-wallet path)
`InTransaction.cost_basis_timestamp` is the original acquisition date: artificial InTransactions are created with the timestamp of their `original_lot` (the root of the `from_lot` chain). `GainLoss.is_long_term_capital_gains()` uses `cost_basis_timestamp` (not `timestamp`) so that the holding period survives wallet-to-wallet transfers. In the universal path all InTransactions are real (no `from_lot`), so `cost_basis_timestamp` falls back to `timestamp` and behavior is unchanged.

### TransferAnalyzer Enforces Per-Wallet Balances
`TransferAnalyzer` raises `RP2ValueError` ("Insufficient balance on ...") if an `OutTransaction` or `IntraTransaction` needs more funds than its wallet holds at that moment, even if other wallets have funds. The analyzer processes everything chronologically in a single pass.

### GlobalAllocator Is Superseded
`global_allocation.py` is an earlier prototype that is not wired into the CLI (TODOs: fee splitting, spot price). The per-wallet pipeline uses `UnusedBasisAllocator`, which allocates the lots left unused by universal application (the [Rev. Proc. 2024-28](https://www.irs.gov/pub/irs-drop/rp-24-28.pdf) definition of unused basis) rather than lots traced per wallet.

### Japan and Other Universal-Only Countries
`get_application_policy()` returns `UNIVERSAL_APPLICATION_POLICY` by default: per-wallet settings in the config file are rejected and `compute_tax_per_wallet()` raises. Note that the JP plugin only offers FIFO, although Japanese law prescribes 総平均法 (default) or 移動平均法 for individuals (docs/supported_countries.md claims total average): this is a known, pre-existing gap.

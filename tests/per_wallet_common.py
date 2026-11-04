# Copyright 2025 eprbell
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

# Shared helpers of the per-wallet application tests (test_per_wallet_tax_engine.py and test_per_wallet_reports.py): short-form transaction
# descriptions, expected gain/losses, wallets, and an abstract test case that builds input data and accounting engines from them.

import hashlib
import unittest
from datetime import date
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

from prezzemolo.avl_tree import AVLTree

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.abstract_country import AbstractCountry
from rp2.account import Account
from rp2.accounting_engine import AccountingEngine
from rp2.configuration import MAX_DATE, MIN_DATE, Configuration
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.input_data import InputData
from rp2.intra_transaction import IntraTransaction
from rp2.out_transaction import OutTransaction
from rp2.per_wallet_configuration import PerWalletConfiguration
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.country.us import US
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.transaction_set import TransactionSet
from rp2.wallet_lot import WalletLot

_ASSET = "B1"
_CONFIGURATION_PATH = "./config/test_data.ini"
_UTC = PerWalletConfiguration(timezone_name="UTC")
_CONFIGURATION_DIR = Path("output") / Path("per_wallet_configurations")


# Short-form transaction descriptions.
class _In(NamedTuple):
    unique_id: str
    timestamp: str
    exchange: str
    transaction_type: str
    spot_price: str
    crypto_in: str
    fiat_fee: Optional[str] = None
    holder: str = "Bob"


class _Out(NamedTuple):
    unique_id: str
    timestamp: str
    exchange: str
    spot_price: str
    crypto_out_no_fee: str
    crypto_fee: str = "0"
    # Optional input field: if None, it's crypto_out_no_fee + crypto_fee.
    crypto_out_with_fee: Optional[str] = None
    holder: str = "Bob"


class _Intra(NamedTuple):
    unique_id: str
    timestamp: str
    from_exchange: str
    to_exchange: str
    spot_price: str
    crypto_sent: str
    crypto_received: str
    from_holder: str = "Bob"
    to_holder: str = "Bob"


# Expected gain/loss: acquired_lot_unique_id is the unique id of the original (input) lot, even when the gain/loss refers to an artificial
# lot created by a transfer or by the unused basis allocation.
class _GainLoss(NamedTuple):
    taxable_event_unique_id: str
    acquired_lot_unique_id: Optional[str]
    crypto_amount: str
    fiat_cost_basis: str
    fiat_gain: str
    is_long_term: bool


_GainLossTuple = Tuple[str, Optional[str], RP2Decimal, RP2Decimal, RP2Decimal, bool]
# What a wallet holds at the end: (wallet, original lot, amount, cost basis, acquisition date).
_Holding = Tuple[str, str, RP2Decimal, RP2Decimal, str]


def _sorted(gain_losses: List[_GainLossTuple]) -> List[_GainLossTuple]:
    return sorted(gain_losses, key=str)


# What the wallets hold (ComputedData.wallet_lots), merged by wallet and original lot: (wallet, original lot, amount, cost basis, acquisition
# date), sorted.
def _holdings(wallet_lots: List[WalletLot]) -> List[_Holding]:
    holdings: Dict[Tuple[str, str, str], Tuple[RP2Decimal, RP2Decimal]] = {}
    for wallet_lot in wallet_lots:
        key = (wallet_lot.account.exchange, wallet_lot.original_lot.unique_id, str(wallet_lot.acquisition_timestamp.date()))
        held_amount, held_basis = holdings.get(key, (ZERO, ZERO))
        holdings[key] = (held_amount + wallet_lot.amount, held_basis + wallet_lot.cost_basis)
    return sorted((key[0], key[1], amount, basis, key[2]) for key, (amount, basis) in holdings.items())


# Per-wallet settings in UTC with an unused basis allocation rule: the allocation method (by name, as in the configuration file) and the
# wallet order.
def _allocation_config(order: Tuple[Account, ...], method_name: str = "fifo") -> PerWalletConfiguration:
    return PerWalletConfiguration(timezone_name="UTC", unused_basis_allocation_method=method_name, unused_basis_allocation_wallet_order=order)


# Configuration of the per-wallet tests: the test configuration file plus, if per_wallet_configuration isn't None, a country section with its
# settings (e.g. [country.us] with timezone = UTC). compute_tax_per_wallet() takes the settings from the configuration, so they are written
# to a configuration file in the output directory and parsed and checked like those of a user's file.
def _create_configuration(
    per_wallet_configuration: Optional[PerWalletConfiguration] = _UTC,
    country: Optional[AbstractCountry] = None,
    from_date: date = MIN_DATE,
    to_date: date = MAX_DATE,
    allow_negative_balances: bool = False,
) -> Configuration:
    country = country or US()
    text = Path(_CONFIGURATION_PATH).read_text(encoding="utf-8")
    if per_wallet_configuration is not None:
        text += _get_country_section(country, per_wallet_configuration)
    _CONFIGURATION_DIR.mkdir(parents=True, exist_ok=True)
    path = _CONFIGURATION_DIR / Path(f"{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}.ini")
    path.write_text(text, encoding="utf-8")
    result = Configuration(str(path), country, from_date=from_date, to_date=to_date, allow_negative_balances=allow_negative_balances)
    if result.per_wallet_configuration != per_wallet_configuration:
        raise ValueError(f"The configuration file changed the per-wallet settings: {per_wallet_configuration} -> {result.per_wallet_configuration}")
    return result


# The country section with the given per-wallet settings, in the format of the configuration file (see docs/input_files.md).
def _get_country_section(country: AbstractCountry, per_wallet_configuration: PerWalletConfiguration) -> str:
    lines = ["", f"[country.{country.country_iso_code}]", f"timezone = {per_wallet_configuration.timezone_name}"]
    if per_wallet_configuration.unused_basis_allocation_method:
        lines.append(f"unused_basis_allocation_method = {per_wallet_configuration.unused_basis_allocation_method}")
    if per_wallet_configuration.unused_basis_allocation_wallet_order:
        lines.append(f"unused_basis_allocation_wallet_order = {_get_wallet_list(per_wallet_configuration.unused_basis_allocation_wallet_order)}")
    for asset, method in sorted(per_wallet_configuration.asset_2_unused_basis_allocation_method.items()):
        lines.append(f"unused_basis_allocation_method.{asset} = {method}")
    for asset, wallet_order in sorted(per_wallet_configuration.asset_2_unused_basis_allocation_wallet_order.items()):
        lines.append(f"unused_basis_allocation_wallet_order.{asset} = {_get_wallet_list(wallet_order)}")
    return "\n".join(lines) + "\n"


def _get_wallet_list(wallet_order: Tuple[Account, ...]) -> str:
    return ", ".join(f"{account.exchange}/{account.holder}" for account in wallet_order)


_COINBASE = Account("Coinbase", "Bob")
_KRAKEN = Account("Kraken", "Bob")
_BLOCKFI = Account("BlockFi", "Bob")


# Base class of the per-wallet application tests: it builds input data and accounting engines from short-form descriptions and converts
# gain/losses to comparable tuples.
class AbstractPerWalletTest(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    @staticmethod
    def _create_input_data(configuration: Configuration, transactions: List[object], asset: str = _ASSET) -> InputData:
        sets = {name: TransactionSet(configuration, name, asset) for name in ("IN", "OUT", "INTRA")}
        for row, transaction in enumerate(transactions, start=1):
            if isinstance(transaction, _In):
                sets["IN"].add_entry(
                    InTransaction(
                        configuration,
                        transaction.timestamp,
                        asset,
                        transaction.exchange,
                        transaction.holder,
                        transaction.transaction_type,
                        RP2Decimal(transaction.spot_price),
                        RP2Decimal(transaction.crypto_in),
                        fiat_fee=RP2Decimal(transaction.fiat_fee) if transaction.fiat_fee else None,
                        row=row,
                        unique_id=transaction.unique_id,
                    )
                )
            elif isinstance(transaction, _Out):
                sets["OUT"].add_entry(
                    OutTransaction(
                        configuration,
                        transaction.timestamp,
                        asset,
                        transaction.exchange,
                        transaction.holder,
                        "Sell",
                        RP2Decimal(transaction.spot_price),
                        RP2Decimal(transaction.crypto_out_no_fee),
                        RP2Decimal(transaction.crypto_fee),
                        crypto_out_with_fee=RP2Decimal(transaction.crypto_out_with_fee) if transaction.crypto_out_with_fee else None,
                        row=row,
                        unique_id=transaction.unique_id,
                    )
                )
            elif isinstance(transaction, _Intra):
                sets["INTRA"].add_entry(
                    IntraTransaction(
                        configuration,
                        transaction.timestamp,
                        asset,
                        transaction.from_exchange,
                        transaction.from_holder,
                        transaction.to_exchange,
                        transaction.to_holder,
                        RP2Decimal(transaction.spot_price),
                        RP2Decimal(transaction.crypto_sent),
                        RP2Decimal(transaction.crypto_received),
                        row=row,
                        unique_id=transaction.unique_id,
                    )
                )
        # Like the input parser, the input data is filtered with the dates of the configuration.
        return InputData(asset, sets["IN"], sets["OUT"], sets["INTRA"], from_date=configuration.from_date, to_date=configuration.to_date)

    @staticmethod
    def _create_accounting_engine(years_2_methods: Optional[Dict[int, AbstractAccountingMethod]]) -> AccountingEngine:
        tree: AVLTree[int, AbstractAccountingMethod] = AVLTree()
        for year, method in (years_2_methods or {1970: AccountingMethodFIFO()}).items():
            tree.insert_node(year, method)
        return AccountingEngine(tree)

    @staticmethod
    def _to_tuples(gain_losses: List[GainLoss]) -> List[_GainLossTuple]:
        return [
            (
                gain_loss.taxable_event.unique_id,
                gain_loss.acquired_lot.original_lot.unique_id if gain_loss.acquired_lot else None,
                gain_loss.crypto_amount,
                gain_loss.fiat_cost_basis,
                gain_loss.fiat_gain,
                gain_loss.is_long_term_capital_gains(),
            )
            for gain_loss in gain_losses
        ]

    @staticmethod
    def _want_tuples(want: List[_GainLoss]) -> List[_GainLossTuple]:
        return [
            (
                w.taxable_event_unique_id,
                w.acquired_lot_unique_id,
                RP2Decimal(w.crypto_amount),
                RP2Decimal(w.fiat_cost_basis),
                RP2Decimal(w.fiat_gain),
                w.is_long_term,
            )
            for w in want
        ]

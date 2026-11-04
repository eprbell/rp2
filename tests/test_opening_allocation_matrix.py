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

# R11 from the review of eprbell/rp2#155: the opening-allocation scenarios of test_global_allocation.py, run through the production path.
#
# test_global_allocation.py tests GlobalAllocator, an earlier prototype that RP2 doesn't use: it received lots already tracked wallet by
# wallet before 2025 and produced artificial transfers. RP2 instead uses universal application until the switch (January 1st, 2025), then
# UnusedBasisAllocator assigns the lots that universal application left unused to the wallets that hold units (Rev. Proc. 2024-28 global
# allocation). So the same scenarios are run here through compute_tax_per_wallet(): their transactions happen in 2024 (day N of the
# prototype is January 1st, 2024 plus N days) and the expected allocation is recomputed by hand from the unused universal basis, for each
# method (FIFO, LIFO, HIFO and LOFO, used both for 2024 and as the allocation method). The prototype's per-wallet remaining amounts, prices
# of its artificial transfers, artificial transfers and artificial ids are not used: they don't exist in the production path.
#
# Example ("Mixed" below): buy 10 coins for $110 each on Coinbase (lot 1) and 20 for $120 each on Kraken (lot 2), send 5 from Kraken to
# BlockFi receiving 4 (1 coin of fee), and sell 2 on BlockFi. With FIFO, universal application pays the fee and the sale with lot 1, so the
# unused lots are 7 coins of lot 1 and 20 of lot 2. At the switch BlockFi holds 2, Kraken 15 and Coinbase 10. With the wallet order BlockFi,
# Kraken, Coinbase: BlockFi gets 2 coins of lot 1, Kraken the other 5 of lot 1 and 10 of lot 2, Coinbase the last 10 of lot 2.
#
# Migration map: what replaces each scenario of test_global_allocation.py (for R14, which removes the prototype).
# | Prototype scenario (x FIFO, LIFO, HIFO, LOFO)  | Disposition | Replacement                                                            |
# |-----------------------------------------------|-------------|------------------------------------------------------------------------|
# | Simple test                                   | adapted     | test_opening_allocation_matrix: "Simple"                               |
# | Simple test with unsorted values              | adapted     | test_opening_allocation_matrix: "Unsorted values"                      |
# | Mixed test with in, intra, out transactions   | adapted     | test_opening_allocation_matrix: "Mixed"                                |
# | Larger test with in, intra, out transactions  | adapted     | test_opening_allocation_matrix: "Larger"                               |
# | Interlaced in and intra transactions          | adapted     | test_opening_allocation_matrix: "Interlaced" (one funded wallet)       |
# | Two in-lots, three transfers: CB->Kraken      | adapted     | test_opening_allocation_matrix: "Two lots, three transfers to Alice"   |
# | Reciprocal transfer: CB->Kraken, Kraken->CB   | adapted     | test_opening_allocation_matrix: "Reciprocal transfers"                 |
# | Reciprocal transfer + sales                   | adapted     | test_opening_allocation_matrix: "Reciprocal transfers and sales"       |
# | Empty input_per_wallet_transactions (error)   | replaced    | test_nothing_to_allocate: no holdings before the switch, no allocation |
# | Missing account from account order list       | preserved   | test_allocation_errors: "a funded wallet missing from the order"       |
# | Extra account in account order list (error)   | changed     | test_wallet_without_funds_in_the_order: allowed, it gets nothing (R10) |
# "adapted": same transactions and wallet order, expectations recomputed from universal application. The prototype's empty-input error
# belongs to its API (a map of per-wallet inputs), which RP2 doesn't have. An extra wallet in the order used to be an error: R10 allows
# a known wallet without funds in the order (it gets nothing), and a wallet that isn't in the configuration is still an error.

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

from per_wallet_common import (
    _BLOCKFI,
    _COINBASE,
    _CONFIGURATION_PATH,
    _KRAKEN,
    AbstractPerWalletTest,
    _create_configuration,
    _In,
    _Intra,
    _Out,
)

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.account import Account
from rp2.configuration import Configuration
from rp2.in_transaction import InTransaction
from rp2.opening_allocation import OpeningAllocation, UnusedLot
from rp2.per_wallet_configuration import PerWalletConfiguration
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO
from rp2.plugin.country.us import US
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2ValueError
from rp2.tax_engine import _check_balances_match_unused_lots, compute_tax_per_wallet
from rp2.unused_basis_allocator import UnusedBasisAllocator

_KRAKEN_ALICE = Account("Kraken", "Alice")
_METHODS: Dict[str, AbstractAccountingMethod] = {
    "fifo": AccountingMethodFIFO(),
    "lifo": AccountingMethodLIFO(),
    "hifo": AccountingMethodHIFO(),
    "lofo": AccountingMethodLOFO(),
}
_SWITCH = datetime(2025, 1, 1, tzinfo=timezone.utc)


# Timestamp of day N of a prototype scenario: January 1st, 2024 plus N days (day 1 is January 2nd).
def _day(day: int) -> str:
    return (datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)).isoformat()


# A scenario: transactions (all in 2024), wallet order and, for each method, the expected unused lots in the order of the method (lot, coins)
# and the expected allocated pieces in the order they are allocated (wallet, lot, coins). Lots are named by their unique id.
class _Scenario(NamedTuple):
    description: str
    transactions: List[object]
    wallet_order: Tuple[Account, ...]
    method_2_unused_lots: Dict[str, List[Tuple[str, str]]]
    method_2_pieces: Dict[str, List[Tuple[Account, str, str]]]
    # True if only one wallet holds units at the switch: the allocation needs no rule.
    automatic: bool = False


# Expected allocated piece: (wallet, lot, coins, cost basis, acquisition date).
_Piece = Tuple[Account, str, RP2Decimal, RP2Decimal, str]

_SCENARIOS: List[_Scenario] = [
    _Scenario(
        description="Simple",
        transactions=[
            _In("1", _day(1), "Coinbase", "Buy", "110", "10"),
            _In("2", _day(2), "Kraken", "Buy", "120", "20"),
            _In("3", _day(3), "BlockFi", "Buy", "130", "30"),
        ],
        wallet_order=(_COINBASE, _KRAKEN, _BLOCKFI),
        # Nothing is sold: every lot is unused. FIFO and LOFO sort them as 1, 2, 3 (each wallet gets its own lot back), LIFO and HIFO as
        # 3, 2, 1 (Coinbase and Kraken get lot 3, BlockFi gets lots 2 and 1).
        method_2_unused_lots={
            "fifo": [("1", "10"), ("2", "20"), ("3", "30")],
            "lifo": [("3", "30"), ("2", "20"), ("1", "10")],
            "hifo": [("3", "30"), ("2", "20"), ("1", "10")],
            "lofo": [("1", "10"), ("2", "20"), ("3", "30")],
        },
        method_2_pieces={
            "fifo": [(_COINBASE, "1", "10"), (_KRAKEN, "2", "20"), (_BLOCKFI, "3", "30")],
            "lifo": [(_COINBASE, "3", "10"), (_KRAKEN, "3", "20"), (_BLOCKFI, "2", "20"), (_BLOCKFI, "1", "10")],
            "hifo": [(_COINBASE, "3", "10"), (_KRAKEN, "3", "20"), (_BLOCKFI, "2", "20"), (_BLOCKFI, "1", "10")],
            "lofo": [(_COINBASE, "1", "10"), (_KRAKEN, "2", "20"), (_BLOCKFI, "3", "30")],
        },
    ),
    _Scenario(
        description="Unsorted values",
        transactions=[
            _In("1", _day(1), "Coinbase", "Buy", "120", "30"),
            _In("2", _day(2), "Kraken", "Buy", "130", "10"),
            _In("3", _day(3), "BlockFi", "Buy", "110", "20"),
        ],
        wallet_order=(_BLOCKFI, _KRAKEN, _COINBASE),
        # Dates and prices sort the lots differently: FIFO 1, 2, 3; LIFO 3, 2, 1; HIFO 2 ($130), 1 ($120), 3 ($110); LOFO 3, 1, 2.
        method_2_unused_lots={
            "fifo": [("1", "30"), ("2", "10"), ("3", "20")],
            "lifo": [("3", "20"), ("2", "10"), ("1", "30")],
            "hifo": [("2", "10"), ("1", "30"), ("3", "20")],
            "lofo": [("3", "20"), ("1", "30"), ("2", "10")],
        },
        method_2_pieces={
            "fifo": [(_BLOCKFI, "1", "20"), (_KRAKEN, "1", "10"), (_COINBASE, "2", "10"), (_COINBASE, "3", "20")],
            "lifo": [(_BLOCKFI, "3", "20"), (_KRAKEN, "2", "10"), (_COINBASE, "1", "30")],
            "hifo": [(_BLOCKFI, "2", "10"), (_BLOCKFI, "1", "10"), (_KRAKEN, "1", "10"), (_COINBASE, "1", "10"), (_COINBASE, "3", "20")],
            "lofo": [(_BLOCKFI, "3", "20"), (_KRAKEN, "1", "10"), (_COINBASE, "1", "20"), (_COINBASE, "2", "10")],
        },
    ),
    _Scenario(
        description="Mixed",
        transactions=[
            _In("1", _day(1), "Coinbase", "Buy", "110", "10"),
            _In("2", _day(2), "Kraken", "Buy", "120", "20"),
            _Intra("3", _day(3), "Kraken", "BlockFi", "130", "5", "4"),
            _Out("4", _day(4), "BlockFi", "140", "2"),
        ],
        wallet_order=(_BLOCKFI, _KRAKEN, _COINBASE),
        # At the switch BlockFi holds 2, Kraken 15, Coinbase 10. The fee (1) and the sale (2) are paid with lot 1 by FIFO and LOFO (oldest,
        # cheapest) and with lot 2 by LIFO and HIFO (newest, most expensive).
        method_2_unused_lots={
            "fifo": [("1", "7"), ("2", "20")],
            "lifo": [("2", "17"), ("1", "10")],
            "hifo": [("2", "17"), ("1", "10")],
            "lofo": [("1", "7"), ("2", "20")],
        },
        method_2_pieces={
            "fifo": [(_BLOCKFI, "1", "2"), (_KRAKEN, "1", "5"), (_KRAKEN, "2", "10"), (_COINBASE, "2", "10")],
            "lifo": [(_BLOCKFI, "2", "2"), (_KRAKEN, "2", "15"), (_COINBASE, "1", "10")],
            "hifo": [(_BLOCKFI, "2", "2"), (_KRAKEN, "2", "15"), (_COINBASE, "1", "10")],
            "lofo": [(_BLOCKFI, "1", "2"), (_KRAKEN, "1", "5"), (_KRAKEN, "2", "10"), (_COINBASE, "2", "10")],
        },
    ),
    _Scenario(
        description="Larger",
        transactions=[
            _In("1", _day(1), "Coinbase", "Buy", "130", "10"),
            _Intra("2", _day(2), "Coinbase", "BlockFi", "130", "5", "3"),
            _In("3", _day(3), "Coinbase", "Buy", "120", "15"),
            _Intra("4", _day(4), "Coinbase", "BlockFi", "130", "17", "16"),
            _In("5", _day(5), "Kraken", "Buy", "110", "20"),
            _Intra("6", _day(6), "Kraken", "BlockFi", "130", "15", "14"),
            _In("7", _day(7), "Kraken", "Buy", "140", "25"),
            _Out("8", _day(8), "BlockFi", "140", "2"),
            _Intra("9", _day(9), "BlockFi", "Coinbase", "130", "5", "4"),
        ],
        wallet_order=(_BLOCKFI, _COINBASE, _KRAKEN),
        # At the switch BlockFi holds 26, Coinbase 7, Kraken 30. Universal application pays the fees (2 on day 2, then 1 on days 4, 6 and
        # 9) and the sale (2 on day 8) with the lots available at that time:
        # - FIFO: all with lot 1 (3 of its 10 coins left);
        # - LIFO: day 2 lot 1 (the only one), day 4 lot 3, day 6 lot 5, days 8 and 9 lot 7;
        # - HIFO: days 2, 4 and 6 lot 1 ($130, the highest until day 7), days 8 and 9 lot 7 ($140);
        # - LOFO: day 2 lot 1, day 4 lot 3 ($120), days 6, 8 and 9 lot 5 ($110).
        method_2_unused_lots={
            "fifo": [("1", "3"), ("3", "15"), ("5", "20"), ("7", "25")],
            "lifo": [("7", "22"), ("5", "19"), ("3", "14"), ("1", "8")],
            "hifo": [("7", "22"), ("1", "6"), ("3", "15"), ("5", "20")],
            "lofo": [("5", "16"), ("3", "14"), ("1", "8"), ("7", "25")],
        },
        method_2_pieces={
            "fifo": [(_BLOCKFI, "1", "3"), (_BLOCKFI, "3", "15"), (_BLOCKFI, "5", "8"), (_COINBASE, "5", "7"), (_KRAKEN, "5", "5"), (_KRAKEN, "7", "25")],
            "lifo": [(_BLOCKFI, "7", "22"), (_BLOCKFI, "5", "4"), (_COINBASE, "5", "7"), (_KRAKEN, "5", "8"), (_KRAKEN, "3", "14"), (_KRAKEN, "1", "8")],
            "hifo": [(_BLOCKFI, "7", "22"), (_BLOCKFI, "1", "4"), (_COINBASE, "1", "2"), (_COINBASE, "3", "5"), (_KRAKEN, "3", "10"), (_KRAKEN, "5", "20")],
            "lofo": [(_BLOCKFI, "5", "16"), (_BLOCKFI, "3", "10"), (_COINBASE, "3", "4"), (_COINBASE, "1", "3"), (_KRAKEN, "1", "5"), (_KRAKEN, "7", "25")],
        },
    ),
    _Scenario(
        description="Interlaced",
        transactions=[
            _In("1", _day(1), "Coinbase", "Buy", "110", "10"),
            _Intra("2", _day(2), "Coinbase", "Kraken", "120", "4", "4"),
            _In("3", _day(3), "Coinbase", "Buy", "130", "4"),
            _Intra("4", _day(4), "Coinbase", "Kraken", "140", "10", "10"),
        ],
        wallet_order=(_COINBASE, _KRAKEN),
        # Everything ends up on Kraken (14 coins), Coinbase holds nothing: the allocation is automatic, both lots go to Kraken.
        method_2_unused_lots={
            "fifo": [("1", "10"), ("3", "4")],
            "lifo": [("3", "4"), ("1", "10")],
            "hifo": [("3", "4"), ("1", "10")],
            "lofo": [("1", "10"), ("3", "4")],
        },
        method_2_pieces={
            "fifo": [(_KRAKEN, "1", "10"), (_KRAKEN, "3", "4")],
            "lifo": [(_KRAKEN, "3", "4"), (_KRAKEN, "1", "10")],
            "hifo": [(_KRAKEN, "3", "4"), (_KRAKEN, "1", "10")],
            "lofo": [(_KRAKEN, "1", "10"), (_KRAKEN, "3", "4")],
        },
        automatic=True,
    ),
    _Scenario(
        description="Two lots, three transfers to Alice",
        transactions=[
            _In("1", _day(1), "Coinbase", "Buy", "110", "10"),
            _In("2", _day(2), "Coinbase", "Buy", "120", "20"),
            _Intra("3", _day(3), "Coinbase", "Kraken", "130", "8", "7", to_holder="Alice"),
            _Intra("4", _day(4), "Coinbase", "Kraken", "140", "10", "10", to_holder="Alice"),
            _Intra("5", _day(5), "Coinbase", "Kraken", "150", "12", "12", to_holder="Alice"),
        ],
        wallet_order=(_KRAKEN_ALICE, _COINBASE),
        # Alice's Kraken wallet holds all 29 coins (automatic allocation). The fee of the first transfer (1 coin) is paid with lot 1 by FIFO
        # and LOFO, with lot 2 by LIFO and HIFO.
        method_2_unused_lots={
            "fifo": [("1", "9"), ("2", "20")],
            "lifo": [("2", "19"), ("1", "10")],
            "hifo": [("2", "19"), ("1", "10")],
            "lofo": [("1", "9"), ("2", "20")],
        },
        method_2_pieces={
            "fifo": [(_KRAKEN_ALICE, "1", "9"), (_KRAKEN_ALICE, "2", "20")],
            "lifo": [(_KRAKEN_ALICE, "2", "19"), (_KRAKEN_ALICE, "1", "10")],
            "hifo": [(_KRAKEN_ALICE, "2", "19"), (_KRAKEN_ALICE, "1", "10")],
            "lofo": [(_KRAKEN_ALICE, "1", "9"), (_KRAKEN_ALICE, "2", "20")],
        },
        automatic=True,
    ),
    _Scenario(
        # From the discussion at https://github.com/eprbell/rp2/issues/135#issuecomment-2557660925.
        description="Reciprocal transfers",
        transactions=[
            _In("1", _day(1), "Coinbase", "Buy", "110", "10"),
            _In("2", _day(2), "Kraken", "Buy", "120", "10"),
            _Intra("3", _day(3), "Coinbase", "Kraken", "130", "4", "3"),
            _Intra("4", _day(4), "Kraken", "Coinbase", "140", "7", "6"),
        ],
        wallet_order=(_KRAKEN, _COINBASE),
        # At the switch Kraken holds 6 and Coinbase 12. The two fees (1 coin each) are paid with lot 1 by FIFO and LOFO, with lot 2 by LIFO
        # and HIFO.
        method_2_unused_lots={
            "fifo": [("1", "8"), ("2", "10")],
            "lifo": [("2", "8"), ("1", "10")],
            "hifo": [("2", "8"), ("1", "10")],
            "lofo": [("1", "8"), ("2", "10")],
        },
        method_2_pieces={
            "fifo": [(_KRAKEN, "1", "6"), (_COINBASE, "1", "2"), (_COINBASE, "2", "10")],
            "lifo": [(_KRAKEN, "2", "6"), (_COINBASE, "2", "2"), (_COINBASE, "1", "10")],
            "hifo": [(_KRAKEN, "2", "6"), (_COINBASE, "2", "2"), (_COINBASE, "1", "10")],
            "lofo": [(_KRAKEN, "1", "6"), (_COINBASE, "1", "2"), (_COINBASE, "2", "10")],
        },
    ),
    _Scenario(
        description="Reciprocal transfers and sales",
        transactions=[
            _In("1", _day(1), "Coinbase", "Buy", "110", "10"),
            _In("2", _day(2), "Kraken", "Buy", "120", "10"),
            _Intra("3", _day(3), "Coinbase", "Kraken", "130", "4", "3"),
            _Intra("4", _day(4), "Kraken", "Coinbase", "140", "2", "1"),
            _Out("5", _day(5), "Kraken", "150", "2", "1"),
            _Out("6", _day(6), "Coinbase", "150", "3", "2"),
        ],
        wallet_order=(_KRAKEN, _COINBASE),
        # At the switch Kraken holds 8 and Coinbase 2. Fees and sales dispose of 10 coins: all of lot 1 with FIFO and LOFO, all of lot 2
        # with LIFO and HIFO (a lot completely used up before the switch), so a single lot is left.
        method_2_unused_lots={
            "fifo": [("2", "10")],
            "lifo": [("1", "10")],
            "hifo": [("1", "10")],
            "lofo": [("2", "10")],
        },
        method_2_pieces={
            "fifo": [(_KRAKEN, "2", "8"), (_COINBASE, "2", "2")],
            "lifo": [(_KRAKEN, "1", "8"), (_COINBASE, "1", "2")],
            "hifo": [(_KRAKEN, "1", "8"), (_COINBASE, "1", "2")],
            "lofo": [(_KRAKEN, "2", "8"), (_COINBASE, "2", "2")],
        },
    ),
]


def _per_wallet_configuration(method_name: str, wallet_order: Tuple[Account, ...]) -> PerWalletConfiguration:
    return PerWalletConfiguration(timezone_name="UTC", unused_basis_allocation_method=method_name, unused_basis_allocation_wallet_order=wallet_order)


class TestOpeningAllocationMatrix(AbstractPerWalletTest):
    def _allocate(
        self, transactions: List[object], method_name: str, wallet_order: Tuple[Account, ...]
    ) -> Tuple[Optional[OpeningAllocation], Dict[Tuple[Account, str], Tuple[RP2Decimal, RP2Decimal, str]]]:
        configuration = _create_configuration(_per_wallet_configuration(method_name, wallet_order))
        input_data = self._create_input_data(configuration, transactions)
        method = _METHODS[method_name]
        computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine({1970: method}), input_data)
        # What each wallet holds at the end, merged by original lot: (coins, cost basis, acquisition date).
        holdings: Dict[Tuple[Account, str], Tuple[RP2Decimal, RP2Decimal, str]] = {}
        for wallet_lot in computed_data.wallet_lots or []:
            key = (wallet_lot.account, wallet_lot.original_lot.unique_id)
            amount, basis, _ = holdings.get(key, (ZERO, ZERO, ""))
            holdings[key] = (amount + wallet_lot.amount, basis + wallet_lot.cost_basis, str(wallet_lot.acquisition_timestamp.date()))
        return computed_data.opening_allocation, holdings

    # Each scenario with each method: the unused lots (in the order of the method), the allocated pieces (in the order they are allocated,
    # with the cost basis and acquisition date of their lot), whether the allocation is automatic, and what the wallets hold afterwards.
    def test_opening_allocation_matrix(self) -> None:
        for scenario in _SCENARIOS:
            lot_2_price_and_date = {
                transaction.unique_id: (RP2Decimal(transaction.spot_price), transaction.timestamp[:10])
                for transaction in scenario.transactions
                if isinstance(transaction, _In)
            }
            for method_name in _METHODS:
                with self.subTest(scenario=scenario.description, method=method_name):
                    opening_allocation, holdings = self._allocate(scenario.transactions, method_name, scenario.wallet_order)
                    assert opening_allocation is not None

                    got_unused_lots: List[Tuple[str, RP2Decimal]] = [(lot.acquired_lot.unique_id, lot.amount) for lot in opening_allocation.unused_lots]
                    want_unused_lots: List[Tuple[str, RP2Decimal]] = [(lot, RP2Decimal(coins)) for lot, coins in scenario.method_2_unused_lots[method_name]]
                    self.assertEqual(got_unused_lots, want_unused_lots)

                    got_pieces: List[_Piece] = [
                        (
                            Account(piece.exchange, piece.holder),
                            piece.original_lot.unique_id,
                            piece.crypto_in,
                            piece.fiat_in_with_fee,
                            str(piece.cost_basis_timestamp.date()),
                        )
                        for piece in opening_allocation.allocated_lots
                    ]
                    want_pieces: List[_Piece] = [
                        (wallet, lot, RP2Decimal(coins), lot_2_price_and_date[lot][0] * RP2Decimal(coins), lot_2_price_and_date[lot][1])
                        for wallet, lot, coins in scenario.method_2_pieces[method_name]
                    ]
                    self.assertEqual(got_pieces, want_pieces)
                    self.assertEqual(opening_allocation.is_automatic, scenario.automatic)
                    self.assertEqual(opening_allocation.allocation_method_name, method_name)

                    # The allocated pieces account for all the unused coins and basis, and each wallet gets exactly what it held.
                    self.assertEqual(opening_allocation.allocated_crypto, opening_allocation.unused_crypto)
                    self.assertEqual(opening_allocation.allocated_cost_basis, opening_allocation.unused_cost_basis)
                    for wallet in opening_allocation.wallets:
                        received = RP2Decimal(
                            sum((RP2Decimal(coins) for piece_wallet, _, coins in scenario.method_2_pieces[method_name] if piece_wallet == wallet), ZERO)
                        )
                        self.assertEqual(opening_allocation.get_opening_balance(wallet), received, msg=f"{wallet}")

                    # Without transactions after the switch, the wallets hold their pieces, merged by lot.
                    want_holdings: Dict[Tuple[Account, str], Tuple[RP2Decimal, RP2Decimal, str]] = {}
                    for wallet, lot, amount, basis, day in want_pieces:
                        held_amount, held_basis, _ = want_holdings.get((wallet, lot), (ZERO, ZERO, ""))
                        want_holdings[(wallet, lot)] = (held_amount + amount, held_basis + basis, day)
                    self.assertEqual(holdings, want_holdings)

    # The prototype rejected an empty input. RP2 has no such input: an asset without transactions before the switch has nothing to allocate.
    def test_nothing_to_allocate(self) -> None:
        for method_name in _METHODS:
            with self.subTest(method=method_name):
                transactions: List[object] = [
                    _In("1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "110", "10"),
                    _In("2", "2025-01-03T00:00:00+00:00", "Kraken", "Buy", "120", "20"),
                ]
                opening_allocation, _ = self._allocate(transactions, method_name, (_COINBASE, _KRAKEN))
                self.assertIsNone(opening_allocation)
                # The same holds if everything bought before the switch was sold before it.
                transactions = [
                    _In("1", _day(1), "Coinbase", "Buy", "110", "10"),
                    _Out("2", _day(2), "Coinbase", "120", "10"),
                    _In("3", "2025-01-03T00:00:00+00:00", "Kraken", "Buy", "130", "20"),
                ]
                opening_allocation, _ = self._allocate(transactions, method_name, (_COINBASE, _KRAKEN))
                self.assertIsNone(opening_allocation)

    # The prototype rejected a wallet in the order without transactions. R10 allows a known wallet that holds nothing at the switch to stay
    # in the order: it gets nothing. Here BlockFi has no transactions at all.
    def test_wallet_without_funds_in_the_order(self) -> None:
        transactions: List[object] = [
            _In("1", _day(1), "Coinbase", "Buy", "110", "10"),
            _In("2", _day(2), "Kraken", "Buy", "120", "20"),
        ]
        method_2_pieces: Dict[str, List[Tuple[Account, str, str]]] = {
            "fifo": [(_COINBASE, "1", "10"), (_KRAKEN, "2", "20")],
            "lifo": [(_COINBASE, "2", "10"), (_KRAKEN, "2", "10"), (_KRAKEN, "1", "10")],
            "hifo": [(_COINBASE, "2", "10"), (_KRAKEN, "2", "10"), (_KRAKEN, "1", "10")],
            "lofo": [(_COINBASE, "1", "10"), (_KRAKEN, "2", "20")],
        }
        for method_name, pieces in method_2_pieces.items():
            with self.subTest(method=method_name):
                opening_allocation, _ = self._allocate(transactions, method_name, (_COINBASE, _BLOCKFI, _KRAKEN))
                assert opening_allocation is not None
                got: List[Tuple[Account, str, RP2Decimal]] = [
                    (Account(piece.exchange, piece.holder), piece.original_lot.unique_id, piece.crypto_in) for piece in opening_allocation.allocated_lots
                ]
                want: List[Tuple[Account, str, RP2Decimal]] = [(wallet, lot, RP2Decimal(coins)) for wallet, lot, coins in pieces]
                self.assertEqual(got, want)
                self.assertEqual(opening_allocation.wallet_order, (_COINBASE, _BLOCKFI, _KRAKEN))
                self.assertEqual(opening_allocation.get_opening_balance(_BLOCKFI), ZERO)
                self.assertEqual(len(opening_allocation.get_allocated_lots(_BLOCKFI)), 0)

    # The checks of the allocation input (R10: unknown or missing funded wallets, duplicate entries, negative balances and quantity
    # mismatch), with every method where the method is involved.
    def test_allocation_errors(self) -> None:
        simple = _SCENARIOS[0].transactions
        for method_name, method in _METHODS.items():
            with self.subTest(name="a funded wallet missing from the order", method=method_name):
                with self.assertRaisesRegex(
                    RP2ValueError, "Wallets holding funds at the per-wallet switch are missing from 'unused_basis_allocation_wallet_order': Kraken/Bob"
                ):
                    self._allocate(simple, method_name, (_COINBASE, _BLOCKFI))
            with self.subTest(name="more than one funded wallet and no rule", method=method_name):
                configuration = _create_configuration(PerWalletConfiguration(timezone_name="UTC"))
                input_data = self._create_input_data(configuration, simple)
                engine = self._create_accounting_engine({1970: method})
                with self.assertRaisesRegex(RP2ValueError, "Unused basis allocation is needed at 2025-01-01 00:00:00\\+00:00 \\(3 wallets hold B1 funds"):
                    compute_tax_per_wallet(configuration, engine, input_data)
            with self.subTest(name="a negative wallet balance at the switch", method=method_name):
                # Kraken sells 5 coins it never received: universal application accepts it (the coins come from Coinbase's lot), but a wallet
                # can't hold a negative balance at the switch.
                transactions: List[object] = [_In("1", _day(1), "Coinbase", "Buy", "110", "10"), _Out("2", _day(2), "Kraken", "120", "5")]
                with self.assertRaisesRegex(RP2ValueError, "Balance of Kraken/Bob is negative \\(-5"):
                    self._allocate(transactions, method_name, (_COINBASE, _KRAKEN))

        # Wallets that aren't in the configuration, and duplicates, are rejected when the configuration file is read.
        for name, wallet_order, error in [
            ("a wallet that isn't in the configuration", "Coinbase/Bob, Gemini/Bob", "invalid wallet 'Gemini/Bob'"),
            ("a wallet twice in the order", "Coinbase/Bob, Kraken/Bob, Coinbase/Bob", "wallet order contains duplicates"),
        ]:
            with self.subTest(name=name):
                text = Path(_CONFIGURATION_PATH).read_text(encoding="utf-8")
                text += f"\n[country.us]\ntimezone = UTC\nunused_basis_allocation_method = fifo\nunused_basis_allocation_wallet_order = {wallet_order}\n"
                path = Path("output") / Path("per_wallet_configurations") / Path(f"r11_{name.replace(' ', '_').replace(chr(39), '')}.ini")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(RP2ValueError, error):
                    Configuration(str(path), US())

        # Wallet balances that don't match the unused lots mean the input is inconsistent: the totals are checked before the allocation, and
        # the allocator stops if the lots run out before every wallet is filled.
        configuration = _create_configuration()
        lot = InTransaction(configuration, _day(1), "B1", "Coinbase", "Bob", "Buy", RP2Decimal("110"), RP2Decimal("10"), row=1, unique_id="1")
        unused_lots = [UnusedLot(lot, RP2Decimal("10"))]
        with self.subTest(name="wallet balances don't match the unused lots"):
            with self.assertRaisesRegex(RP2ValueError, "Total wallet balance \\(15\\) doesn't match unused lot amount \\(10\\)"):
                _check_balances_match_unused_lots({_COINBASE: RP2Decimal("10"), _KRAKEN: RP2Decimal("5")}, unused_lots)
        with self.subTest(name="unused lots insufficient to fill the wallets"):
            allocator = UnusedBasisAllocator(
                configuration, "B1", _SWITCH, unused_lots, {_COINBASE: RP2Decimal("10"), _KRAKEN: RP2Decimal("5")}, AccountingMethodFIFO(), [_COINBASE, _KRAKEN]
            )
            with self.assertRaisesRegex(RP2ValueError, "Unused lots are insufficient to cover the balance of Kraken/Bob"):
                allocator.allocate()


if __name__ == "__main__":
    unittest.main()

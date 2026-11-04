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

# The lot consumption and pairing rules, shared by universal and per-wallet application: both take coins from lots with take_lots() and
# turn what they took into gain/losses with pair_with_lots() (and pair_earning() for income, which takes no lot). The two applications
# differ only in the lots they let take_lots() choose from (the "lot pool"):
# - universal application: every lot acquired up to the taxable event, in any wallet (see AccountingEngine.take());
# - per-wallet application: only the lots held by the wallet that sells or sends the coins (see PerWalletTransactions.take()).
# Example: Coinbase holds lot A (bought 2024-01-01) and Kraken holds lot B (bought 2024-02-01), 1 coin each, and Kraken sells 1 coin with
# FIFO. Universal application takes it from A, the oldest lot of all; per-wallet application takes it from B, the only lot Kraken holds.
# Transfers between wallets (where the coins arrive, the links to the lots they come from, the return of coins at the end of a round trip)
# are not part of these rules: they stay in TransferAnalyzer.

from typing import List, NamedTuple

from rp2.abstract_accounting_method import (
    AbstractAccountingMethod,
    AbstractAcquiredLotCandidates,
)
from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import Configuration
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2RuntimeError, RP2TypeError


# A piece of an acquired lot consumed by a disposal, a transfer or a fee.
class LotPiece(NamedTuple):
    acquired_lot: InTransaction
    amount: RP2Decimal


# Result of taking coins from a lot pool: the pieces taken, in order, and the part of the amount that the pool couldn't cover (zero if it
# had enough coins). The caller decides what a missing amount means (it's an error in both applications).
class TakeResult(NamedTuple):
    pieces: List[LotPiece]
    missing_amount: RP2Decimal


# Takes amount coins from the lot pool, lot by lot, in the order of accounting_method: lot_candidates are the lots the caller allows (its
# pool) and the coins each one has left (see AbstractAcquiredLotCandidates). The rules:
# - the next lot is the first one, in the method's order, that still has coins (accounting_method.seek_non_exhausted_acquired_lot());
# - partial consumption: if the lot has at least the coins still needed, they are taken from it and the lot keeps the rest;
# - exhausted lot: otherwise the lot is taken whole (it's left with zero coins) and the rest comes from the next lots;
# - the coins left in each lot are written back to lot_candidates, so the next take sees them.
# Coins are compared with RP2Decimal's precision (13 decimals): a lot with 1 coin covers a need of 1.00000000000001 coins. The piece is
# then the amount needed (1.00000000000001) and the lot keeps the difference (-0.00000000000001), which counts as zero.
# Example: lots A (2 coins) and B (5 coins), FIFO, take 3 coins: the pieces are A 2 coins (A is exhausted) and B 1 coin (B keeps 4).
def take_lots(accounting_method: AbstractAccountingMethod, lot_candidates: AbstractAcquiredLotCandidates, amount: RP2Decimal) -> TakeResult:
    if not isinstance(accounting_method, AbstractAccountingMethod):
        raise RP2TypeError(f"Parameter 'accounting_method' is not of type AbstractAccountingMethod: {accounting_method}")
    if not isinstance(lot_candidates, AbstractAcquiredLotCandidates):
        raise RP2TypeError(f"Parameter 'lot_candidates' is not of type AbstractAcquiredLotCandidates: {lot_candidates}")
    # The lot candidates are ordered by the method that created them (e.g. a heap sorted by price): taking from them with a method of
    # another class would select lots in the wrong order.
    if type(lot_candidates.accounting_method) is not type(accounting_method):
        raise RP2RuntimeError(f"Internal error: lot candidates of {lot_candidates.accounting_method} used with accounting method {accounting_method}")
    Configuration.type_check_positive_decimal("amount", amount)

    pieces: List[LotPiece] = []
    amount_left: RP2Decimal = amount
    while amount_left > ZERO:
        lot_and_amount = accounting_method.seek_non_exhausted_acquired_lot(lot_candidates, amount_left)
        if lot_and_amount is None:
            return TakeResult(pieces, amount_left)
        # The method is a plugin: check what it returns. It sets the lot's coins to zero while the lot is in use: they are written back below.
        acquired_lot: InTransaction = InTransaction.type_check("acquired_lot", lot_and_amount.acquired_lot)
        acquired_lot_amount: RP2Decimal = Configuration.type_check_positive_decimal("acquired_lot_amount", lot_and_amount.amount, non_zero=True)
        if amount_left > acquired_lot_amount:
            # Exhausted lot: all its coins are taken.
            piece_amount = acquired_lot_amount
            lot_candidates.set_partial_amount(acquired_lot, ZERO)
        else:
            # Partial consumption: the lot covers what's left and keeps the rest.
            piece_amount = amount_left
            lot_candidates.set_partial_amount(acquired_lot, acquired_lot_amount - amount_left)
        pieces.append(LotPiece(acquired_lot, piece_amount))
        amount_left -= piece_amount
    return TakeResult(pieces, ZERO)


# The pairing rule: each piece taken for a taxable event (a disposal or a fee) becomes a gain/loss of the piece's coins, with the piece's lot
# as cost basis. Example: selling 3 coins taken as A 2 coins and B 1 coin gives two gain/losses: 2 coins with A's basis and 1 with B's.
def pair_with_lots(configuration: Configuration, taxable_event: AbstractTransaction, pieces: List[LotPiece]) -> List[GainLoss]:
    return [GainLoss(configuration, piece.amount, taxable_event, piece.acquired_lot) for piece in pieces]


# Income (e.g. staking or interest) is taxable when received and uses no lot: its gain/loss has no acquired lot.
def pair_earning(configuration: Configuration, earning: AbstractTransaction) -> GainLoss:
    return GainLoss(configuration, earning.crypto_balance_change, earning, None)

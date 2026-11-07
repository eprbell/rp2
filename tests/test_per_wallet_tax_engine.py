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

# End-to-end tests of per-wallet application (compute_tax_per_wallet). Expected values are computed by hand: each test explains the rule it
# checks. Regulatory references:
# - Treas. Reg. §1.1012-1(j): from 2025 basis is identified per wallet/account; absent specific identification, units are disposed of
#   "in order of time from the earliest date on which units ... were acquired by the taxpayer" (FIFO by original acquisition date);
# - Rev. Proc. 2024-28: unused basis at 2025-01-01 is allocated to wallets (global allocation or specific unit allocation);
# - IRC §1223: the holding period of transferred units includes the period they were held in the source wallet;
# - IRS FAQ Q13 / Rev. Rul. 2023-14: earned crypto is income at receipt, once.

import unittest
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, NamedTuple, Optional, Tuple

from per_wallet_common import (
    _ASSET,
    _BLOCKFI,
    _COINBASE,
    _CONFIGURATION_PATH,
    _KRAKEN,
    _UTC,
    AbstractPerWalletTest,
    _allocation_config,
    _create_configuration,
    _GainLoss,
    _GainLossTuple,
    _Holding,
    _holdings,
    _In,
    _Intra,
    _Out,
    _sorted,
)

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.abstract_country import AbstractCountry
from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import MAX_DATE, Configuration
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.per_wallet_configuration import PerWalletConfiguration
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO
from rp2.plugin.country.jp import JP
from rp2.plugin.country.us import US
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError
from rp2.tax_engine import compute_tax, compute_tax_per_wallet
from rp2.transfer_analyzer import TransferAnalyzer
from rp2.wallet_lot import WalletLot


@dataclass(frozen=True)
class _Test:
    description: str
    transactions: List[object]
    want: List[_GainLoss] = field(default_factory=list)
    want_error: str = ""
    per_wallet_configuration: Optional[PerWalletConfiguration] = _UTC
    years_2_methods: Optional[Dict[int, AbstractAccountingMethod]] = None
    # With a single wallet per-wallet and universal application must produce the same result.
    same_as_universal: bool = False


# Result of a per-wallet run with an unused basis allocation (see TestPerWalletTaxEngine._run_with_allocation()).
class _AllocationRun(NamedTuple):
    gain_losses: List[_GainLossTuple]
    holdings: List[_Holding]


class TestPerWalletTaxEngine(AbstractPerWalletTest):
    def _run_test(self, test: _Test, country: Optional[AbstractCountry] = None) -> None:
        configuration = _create_configuration(test.per_wallet_configuration, country)
        input_data = self._create_input_data(configuration, test.transactions)
        engine = self._create_accounting_engine(test.years_2_methods)
        if test.want_error:
            with self.assertRaisesRegex(RP2ValueError, test.want_error):
                compute_tax_per_wallet(configuration, engine, input_data)
            return
        computed_data = compute_tax_per_wallet(configuration, engine, input_data)
        got: List[_GainLossTuple] = self._to_tuples([gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)])
        self.assertEqual(_sorted(got), _sorted(self._want_tuples(test.want)))
        if test.same_as_universal:
            universal_computed_data = compute_tax(configuration, self._create_accounting_engine(test.years_2_methods), input_data)
            universal = self._to_tuples([gain_loss for gain_loss in universal_computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)])
            self.assertEqual(_sorted(got), _sorted(universal))

    def test_per_wallet(self) -> None:
        tests: List[_Test] = [
            _Test(
                description="Single wallet: a sale that exhausts a lot (this failed before the fix)",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Coinbase", "200", "10"),
                ],
                want=[_GainLoss("o1", "i1", "10", "1000", "1000", False)],
                same_as_universal=True,
            ),
            _Test(
                description="Single wallet: two sales exhausting one lot",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Coinbase", "200", "4"),
                    _Out("o2", "2025-03-01T00:00:00+00:00", "Coinbase", "200", "6"),
                ],
                want=[_GainLoss("o1", "i1", "4", "400", "400", False), _GainLoss("o2", "i1", "6", "600", "600", False)],
                same_as_universal=True,
            ),
            _Test(
                description="Earned crypto is income once: moving it to another wallet doesn't create income again",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Income", "100", "10"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "4", "4"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "200", "4"),
                ],
                want=[_GainLoss("i1", None, "10", "0", "1000", False), _GainLoss("o1", "i1", "4", "400", "400", False)],
            ),
            _Test(
                description="Purchase fee stays in the cost basis after a transfer",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10", fiat_fee="10"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "10", "10"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "200", "10"),
                ],
                want=[_GainLoss("o1", "i1", "10", "1010", "990", False)],
            ),
            _Test(
                description="FIFO within a wallet uses the original acquisition date, not the arrival date (Treas. Reg. §1.1012-1(j))",
                transactions=[
                    _In("i1", "2025-01-01T12:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _In("i2", "2025-04-10T00:00:00+00:00", "Kraken", "Buy", "500", "1"),
                    _Intra("t1", "2025-07-19T00:00:00+00:00", "Coinbase", "Kraken", "550", "1", "1"),
                    _Out("o1", "2025-10-27T00:00:00+00:00", "Kraken", "600", "1"),
                ],
                want=[_GainLoss("o1", "i1", "1", "100", "500", False)],
            ),
            # The next three cases are worked examples from the Reddit threads linked in eprbell/rp2#135, with the answers given there by
            # a CPA (JustinCPA). Kraken and BlockFi stand in for hardware wallets.
            _Test(
                description="eprbell's question (reddit.com/r/CryptoTax/comments/1gbvfic/comment/ltvfqy7): with FIFO the round trip sells the $11000 lot",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "10000", "1"),
                    _In("i2", "2025-02-01T00:00:00+00:00", "Coinbase", "Buy", "11000", "1"),
                    _Intra("t1", "2025-03-01T00:00:00+00:00", "Coinbase", "Kraken", "12000", "1", "1"),
                    _Intra("t2", "2025-04-01T00:00:00+00:00", "Coinbase", "BlockFi", "13000", "1", "1"),
                    _Intra("t3", "2025-05-01T00:00:00+00:00", "BlockFi", "Coinbase", "14000", "1", "1"),
                    _Out("o1", "2025-06-01T00:00:00+00:00", "Coinbase", "20000", "1"),
                ],
                want=[_GainLoss("o1", "i2", "1", "11000", "9000", False)],
            ),
            _Test(
                description="eprbell's question with HIFO: transfers use the method of the year, so the $10000 lot comes back and is sold",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "10000", "1"),
                    _In("i2", "2025-02-01T00:00:00+00:00", "Coinbase", "Buy", "11000", "1"),
                    _Intra("t1", "2025-03-01T00:00:00+00:00", "Coinbase", "Kraken", "12000", "1", "1"),
                    _Intra("t2", "2025-04-01T00:00:00+00:00", "Coinbase", "BlockFi", "13000", "1", "1"),
                    _Intra("t3", "2025-05-01T00:00:00+00:00", "BlockFi", "Coinbase", "14000", "1", "1"),
                    _Out("o1", "2025-06-01T00:00:00+00:00", "Coinbase", "20000", "1"),
                ],
                years_2_methods={1970: AccountingMethodHIFO()},
                want=[_GainLoss("o1", "i1", "1", "10000", "10000", False)],
            ),
            _Test(
                description="gurtz135's question (reddit.com/r/CryptoTax/comments/1gbvfic/comment/m310q4a): units moved to Kraken keep their date",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _In("i2", "2025-02-01T00:00:00+00:00", "Kraken", "Buy", "200", "5"),
                    _Intra("t1", "2025-03-01T00:00:00+00:00", "Coinbase", "Kraken", "300", "4", "4"),
                    _Out("o1", "2025-04-01T00:00:00+00:00", "Kraken", "400", "2"),
                ],
                # "They retain their original holding period. So the 2BTC sold would be from Coinbase."
                want=[_GainLoss("o1", "i1", "2", "200", "600", False)],
            ),
            _Test(
                description="Metal450's question (reddit.com/r/CryptoTax/comments/1hk31yd/comment/m4w1hll): sale order A1, B, A2 by acquisition date",
                transactions=[
                    _In("a1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _In("b1", "2025-02-01T00:00:00+00:00", "Kraken", "Buy", "200", "1"),
                    _In("a2", "2025-03-01T00:00:00+00:00", "Coinbase", "Buy", "300", "1"),
                    _Intra("t1", "2025-04-01T00:00:00+00:00", "Coinbase", "Kraken", "400", "2", "2"),
                    _Out("o1", "2025-05-01T00:00:00+00:00", "Kraken", "500", "1"),
                    _Out("o2", "2025-05-02T00:00:00+00:00", "Kraken", "500", "1"),
                    _Out("o3", "2025-05-03T00:00:00+00:00", "Kraken", "500", "1"),
                ],
                want=[
                    _GainLoss("o1", "a1", "1", "100", "400", False),
                    _GainLoss("o2", "b1", "1", "200", "300", False),
                    _GainLoss("o3", "a2", "1", "300", "200", False),
                ],
            ),
            _Test(
                # IRS FAQ A81 and A97: the fee is disposed of (no setting needed); A53: its basis is not added to the received units.
                description="Transfer fee paid in the transferred asset is a disposal; the received units keep their own basis",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "10", "9"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "200", "9"),
                ],
                want=[_GainLoss("t1", "i1", "1", "100", "50", False), _GainLoss("o1", "i1", "9", "900", "900", False)],
            ),
            _Test(
                description="Transfer fee spanning two lots (https://github.com/eprbell/rp2/issues/149)",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "5", "100"),
                    _In("i2", "2025-01-03T00:00:00+00:00", "Coinbase", "Buy", "3", "110"),
                    _Out("o0", "2025-01-04T00:00:00+00:00", "Coinbase", "6", "95"),
                    _Intra("t1", "2025-01-05T00:00:00+00:00", "Coinbase", "Kraken", "6", "7", "4"),
                    _Out("o1", "2025-01-06T00:00:00+00:00", "Kraken", "7", "4"),
                ],
                # FIFO: i1 has 5 left after o0: the fee (3, proceeds 3 * 6 = 18) is paid first, with i1 units; the 4 received units are the
                # remaining 2 of i1 and 2 of i2.
                want=[
                    _GainLoss("o0", "i1", "95", "475", "95", False),
                    _GainLoss("t1", "i1", "3", "15", "3", False),
                    _GainLoss("o1", "i1", "2", "10", "4", False),
                    _GainLoss("o1", "i2", "2", "6", "8", False),
                ],
            ),
            _Test(
                description="Holding period is preserved through transfers: sold the day after the first anniversary is long term",
                transactions=[
                    _In("i1", "2024-03-01T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "1", "1"),
                    _Out("o1", "2025-03-02T00:00:00+00:00", "Kraken", "200", "1"),
                ],
                want=[_GainLoss("o1", "i1", "1", "100", "100", True)],
            ),
            _Test(
                description="Holding period is preserved through transfers: sold on the first anniversary is short term",
                transactions=[
                    _In("i1", "2024-03-01T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "1", "1"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "200", "1"),
                ],
                want=[_GainLoss("o1", "i1", "1", "100", "100", False)],
            ),
            _Test(
                description="A sale larger than the wallet balance is an error, even if another wallet has funds",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _In("i2", "2025-01-02T00:00:00+00:00", "Kraken", "Buy", "100", "10"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "200", "15"),
                ],
                want_error=r"Insufficient balance on Account\(exchange='Kraken', holder='Bob'\) to cover out transaction \(missing 5 of 15 B1\)",
            ),
            _Test(
                description="A transfer from a wallet that never received funds is an error (send with no prior receive)",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Kraken", "Coinbase", "150", "1", "1"),
                ],
                want_error=r"Insufficient balance on Account\(exchange='Kraken', holder='Bob'\): no funds were ever received",
            ),
            _Test(
                description="Unused basis in two wallets at the switch without an allocation rule: error (Rev. Proc. 2024-28)",
                transactions=[
                    _In("i1", "2024-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _In("i2", "2024-01-03T00:00:00+00:00", "Kraken", "Buy", "200", "10"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "300", "5"),
                ],
                want_error="Unused basis allocation is needed",
            ),
            _Test(
                description="Unused basis allocation: FIFO lots, Kraken filled first, so Kraken gets the oldest lot (i1)",
                transactions=[
                    _In("i1", "2024-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _In("i2", "2024-01-03T00:00:00+00:00", "Kraken", "Buy", "200", "10"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "300", "5"),
                ],
                per_wallet_configuration=_allocation_config((_KRAKEN, _COINBASE)),
                want=[_GainLoss("o1", "i1", "5", "500", "1000", True)],
            ),
            _Test(
                description="Unused basis allocation: HIFO lots, Kraken filled first, so Kraken gets the most expensive lot (i2)",
                transactions=[
                    _In("i1", "2024-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _In("i2", "2024-01-03T00:00:00+00:00", "Kraken", "Buy", "200", "10"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "300", "5"),
                ],
                per_wallet_configuration=_allocation_config((_KRAKEN, _COINBASE), "hifo"),
                want=[_GainLoss("o1", "i2", "5", "1000", "500", True)],
            ),
            _Test(
                # Rev. Proc. 2024-28 §3.04: "The acquisition date of a unit of unused basis is the acquisition date of the digital asset unit
                # to which the unit of unused basis was originally attached." Allocation moves basis and date together: it can't attach the
                # highest basis to the earliest date (as some allocation plans suggested in the threads linked in eprbell/rp2#135).
                description="Unused basis allocation keeps each basis with its own acquisition date: HIFO gives Kraken i2, sold short term",
                transactions=[
                    _In("i1", "2024-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _In("i2", "2024-06-01T00:00:00+00:00", "Kraken", "Buy", "200", "10"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "300", "5"),
                ],
                per_wallet_configuration=_allocation_config((_KRAKEN, _COINBASE), "hifo"),
                want=[_GainLoss("o1", "i2", "5", "1000", "500", False)],
            ),
            _Test(
                description="Per-asset wallet order override: B1 fills Coinbase first even though the default order fills Kraken first",
                transactions=[
                    _In("i1", "2024-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _In("i2", "2024-01-03T00:00:00+00:00", "Kraken", "Buy", "200", "10"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "300", "5"),
                ],
                per_wallet_configuration=PerWalletConfiguration(
                    timezone_name="UTC",
                    unused_basis_allocation_method="fifo",
                    unused_basis_allocation_wallet_order=(_KRAKEN, _COINBASE),
                    asset_2_unused_basis_allocation_wallet_order={_ASSET: (_COINBASE, _KRAKEN)},
                ),
                # Coinbase is filled first with the oldest lot (i1), so Kraken gets i2.
                want=[_GainLoss("o1", "i2", "5", "1000", "500", True)],
            ),
            _Test(
                description="A per-asset override for another asset doesn't affect this one (the default order fills Kraken first)",
                transactions=[
                    _In("i1", "2024-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _In("i2", "2024-01-03T00:00:00+00:00", "Kraken", "Buy", "200", "10"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "300", "5"),
                ],
                per_wallet_configuration=PerWalletConfiguration(
                    timezone_name="UTC",
                    unused_basis_allocation_method="fifo",
                    unused_basis_allocation_wallet_order=(_KRAKEN, _COINBASE),
                    asset_2_unused_basis_allocation_wallet_order={"B2": (_COINBASE, _KRAKEN)},
                ),
                want=[_GainLoss("o1", "i1", "5", "500", "1000", True)],
            ),
            _Test(
                description="Before the switch universal application is unchanged (the 2023 Kraken sale uses the Coinbase lot)",
                transactions=[
                    _In("i1", "2023-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                    _In("i2", "2023-02-02T00:00:00+00:00", "Kraken", "Buy", "300", "2"),
                    _Out("o1", "2023-06-01T00:00:00+00:00", "Kraken", "200", "1"),
                    _Out("o2", "2025-06-01T00:00:00+00:00", "Kraken", "400", "1"),
                ],
                per_wallet_configuration=_allocation_config((_COINBASE, _KRAKEN)),
                # At the switch: unused i1 = 1, i2 = 2; Coinbase (balance 2) gets i1 (1) + i2 (1), Kraken (balance 1) gets i2 (1).
                want=[_GainLoss("o1", "i1", "1", "100", "100", False), _GainLoss("o2", "i2", "1", "300", "100", True)],
            ),
            _Test(
                description="Transfer in flight across the year boundary: its timestamp decides the wallet that holds the funds at the switch",
                transactions=[
                    _In("i1", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _Intra("t1", "2024-12-31T23:30:00+00:00", "Coinbase", "Kraken", "150", "1", "1"),
                    _Out("o1", "2025-01-01T00:30:00+00:00", "Kraken", "200", "1"),
                ],
                want=[_GainLoss("o1", "i1", "1", "100", "100", False)],
            ),
            _Test(
                description="Time zone: 2025-01-01 03:00 in Tokyo is still 2024 in New York, so the sale is universal (FIFO uses the Coinbase lot)",
                transactions=[
                    _In("i1", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _In("i2", "2024-07-01T00:00:00+00:00", "Kraken", "Buy", "300", "1"),
                    _Out("o1", "2025-01-01T03:00:00+09:00", "Kraken", "500", "1"),
                ],
                per_wallet_configuration=PerWalletConfiguration(
                    timezone_name="America/New_York", unused_basis_allocation_method="fifo", unused_basis_allocation_wallet_order=(_COINBASE, _KRAKEN)
                ),
                want=[_GainLoss("o1", "i1", "1", "100", "400", False)],
            ),
            _Test(
                description="Time zone: in Tokyo time the same sale is after the switch, so it can only use the lot allocated to Kraken",
                transactions=[
                    _In("i1", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _In("i2", "2024-07-01T00:00:00+00:00", "Kraken", "Buy", "300", "1"),
                    _Out("o1", "2025-01-01T03:00:00+09:00", "Kraken", "500", "1"),
                ],
                per_wallet_configuration=PerWalletConfiguration(
                    timezone_name="Asia/Tokyo", unused_basis_allocation_method="fifo", unused_basis_allocation_wallet_order=(_COINBASE, _KRAKEN)
                ),
                want=[_GainLoss("o1", "i2", "1", "300", "200", False)],
            ),
            _Test(
                description="Same timestamp: a transfer arriving at the same instant as a sale is available to the sale (In, Intra, Out order)",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "200", "1"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "1", "1"),
                ],
                want=[_GainLoss("o1", "i1", "1", "100", "100", False)],
            ),
            _Test(
                description="Multi-hop (CB->Kraken->BlockFi) and round trip (CB->Kraken->CB) on the same day keep basis and acquisition date",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
                    _Intra("t1", "2025-02-01T01:00:00+00:00", "Coinbase", "Kraken", "150", "2", "2"),
                    _Intra("t2", "2025-02-01T02:00:00+00:00", "Kraken", "BlockFi", "150", "1", "1"),
                    _Intra("t3", "2025-02-01T03:00:00+00:00", "Kraken", "Coinbase", "150", "1", "1"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "BlockFi", "200", "1"),
                    _Out("o2", "2025-03-02T00:00:00+00:00", "Coinbase", "300", "1"),
                ],
                want=[_GainLoss("o1", "i1", "1", "100", "100", False), _GainLoss("o2", "i1", "1", "100", "200", False)],
            ),
            _Test(
                description="Accounting method change across years: FIFO in 2025, HIFO in 2026",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "1"),
                    _In("i2", "2025-02-01T00:00:00+00:00", "Coinbase", "Buy", "300", "1"),
                    _In("i3", "2025-03-01T00:00:00+00:00", "Coinbase", "Buy", "200", "1"),
                    _Out("o1", "2025-06-01T00:00:00+00:00", "Coinbase", "400", "1"),
                    _Out("o2", "2026-06-01T00:00:00+00:00", "Coinbase", "400", "1"),
                ],
                years_2_methods={1970: AccountingMethodFIFO(), 2026: AccountingMethodHIFO()},
                want=[_GainLoss("o1", "i1", "1", "100", "300", False), _GainLoss("o2", "i2", "1", "300", "100", True)],
                same_as_universal=True,
            ),
            _Test(
                description="Staking income after the switch, then sold",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Staking", "10", "2"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Coinbase", "15", "2"),
                ],
                want=[_GainLoss("i1", None, "2", "0", "20", False), _GainLoss("o1", "i1", "2", "20", "10", False)],
                same_as_universal=True,
            ),
            _Test(
                description="Decimal precision: dust transfers (3 x 0.1) are tracked exactly",
                transactions=[
                    _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "3", "1"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "5", "0.1", "0.1"),
                    _Intra("t2", "2025-02-02T00:00:00+00:00", "Coinbase", "Kraken", "5", "0.1", "0.1"),
                    _Intra("t3", "2025-02-03T00:00:00+00:00", "Coinbase", "Kraken", "5", "0.1", "0.1"),
                    _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "10", "0.3"),
                    _Out("o2", "2025-03-01T00:00:00+00:00", "Coinbase", "10", "0.7"),
                ],
                want=[
                    _GainLoss("o1", "i1", "0.1", "0.3", "0.7", False),
                    _GainLoss("o1", "i1", "0.1", "0.3", "0.7", False),
                    _GainLoss("o1", "i1", "0.1", "0.3", "0.7", False),
                    _GainLoss("o2", "i1", "0.7", "2.1", "4.9", False),
                ],
            ),
        ]
        for test in tests:
            with self.subTest(name=test.description):
                self._run_test(test)

    # Runs per-wallet application with an unused basis allocation at the switch (wallet order: Coinbase, Kraken, BlockFi) and returns its
    # gain/losses and what each wallet holds at the end (see _holdings()).
    def _run_with_allocation(self, transactions: List[object], method: AbstractAccountingMethod) -> _AllocationRun:
        configuration = _create_configuration(_allocation_config((_COINBASE, _KRAKEN, _BLOCKFI)))
        computed_data = compute_tax_per_wallet(
            configuration,
            self._create_accounting_engine({1970: method}),
            self._create_input_data(configuration, transactions),
        )
        gain_losses = self._to_tuples([gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)])
        wallet_lots = computed_data.wallet_lots
        assert wallet_lots is not None
        return _AllocationRun(gain_losses, _holdings(wallet_lots))

    # R03 from the review of eprbell/rp2#155: lots allocated at the switch must survive round trips between wallets.
    #
    # The rule in plain English: moving coins between your own wallets changes nothing for tax purposes (IRS FAQ A81), except that the
    # coins paid as a fee are sold (A97). The coins keep their cost and purchase date wherever they go (Treas. Reg. §1.1012-1(j)(1): the
    # date units were transferred into a wallet is disregarded), and at the switch each wallet is given lots that keep the original cost and
    # purchase date of the unused basis (Rev. Proc. 2024-28 §3.04). So when coins come back to a wallet, the wallet must end up with exactly
    # the coins, cost and dates it had before, minus whatever was sold or paid as fees on the way.
    #
    # Example (from the review): buy 10 coins in Coinbase in 2024. At the switch they are allocated to Coinbase. In 2025 move 4 coins to
    # Kraken and then back. Coinbase must hold 10 coins with their $1,000 cost and 2024 purchase date, and Kraken none. Before the fix the
    # returning coins were added to the 2024 purchase (which no wallet holds after the switch) instead of the allocated lot, and the
    # calculation stopped with "returned amount exceeds its crypto_in: 14 > 10".
    #
    # Every case runs with each accounting method: the expected results are the same for all of them.
    def test_allocated_lots_survive_transfer_cycles(self) -> None:
        class _Case(NamedTuple):
            description: str
            transactions: List[object]
            want_gain_losses: List[_GainLoss]
            # (wallet, original lot, amount, cost basis, acquisition date) of what each wallet holds at the end.
            want_holdings: List[Tuple[str, str, str, str, str]]

        buy_10 = _In("i1", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "100", "10")
        coinbase_to_kraken = _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "4", "4")
        kraken_to_coinbase = _Intra("t2", "2025-03-01T00:00:00+00:00", "Kraken", "Coinbase", "150", "4", "4")
        all_in_coinbase = [("Coinbase", "i1", "10", "1000", "2024-06-01")]
        cases = [
            _Case(
                description="the review's example: 4 coins to Kraken and back",
                transactions=[buy_10, coinbase_to_kraken, kraken_to_coinbase],
                want_gain_losses=[],
                want_holdings=all_in_coinbase,
            ),
            _Case(
                description="partial return: 3 of the 4 coins come back",
                transactions=[buy_10, coinbase_to_kraken, _Intra("t2", "2025-03-01T00:00:00+00:00", "Kraken", "Coinbase", "150", "3", "3")],
                want_gain_losses=[],
                want_holdings=[("Coinbase", "i1", "9", "900", "2024-06-01"), ("Kraken", "i1", "1", "100", "2024-06-01")],
            ),
            _Case(
                description="a sale in between: 1 of the 4 coins is sold in Kraken, the other 3 come back",
                transactions=[
                    buy_10,
                    coinbase_to_kraken,
                    _Out("o1", "2025-02-15T00:00:00+00:00", "Kraken", "200", "1"),
                    _Intra("t2", "2025-03-01T00:00:00+00:00", "Kraken", "Coinbase", "150", "3", "3"),
                ],
                want_gain_losses=[_GainLoss("o1", "i1", "1", "100", "100", False)],
                want_holdings=[("Coinbase", "i1", "9", "900", "2024-06-01")],
            ),
            _Case(
                # Each transfer pays a 0.1 coin fee when coins are worth $150: a sale of 0.1 coin for $15 with $10 of cost ($5 gain).
                description="fees on both legs: 4 coins leave, 3.9 arrive in Kraken, 3.8 come back",
                transactions=[
                    buy_10,
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "4", "3.9"),
                    _Intra("t2", "2025-03-01T00:00:00+00:00", "Kraken", "Coinbase", "150", "3.9", "3.8"),
                ],
                want_gain_losses=[_GainLoss("t1", "i1", "0.1", "10", "5", False), _GainLoss("t2", "i1", "0.1", "10", "5", False)],
                want_holdings=[("Coinbase", "i1", "9.8", "980", "2024-06-01")],
            ),
            _Case(
                description="multiple hops: Coinbase -> Kraken -> BlockFi -> Coinbase",
                transactions=[
                    buy_10,
                    coinbase_to_kraken,
                    _Intra("t2", "2025-02-15T00:00:00+00:00", "Kraken", "BlockFi", "150", "4", "4"),
                    _Intra("t3", "2025-03-01T00:00:00+00:00", "BlockFi", "Coinbase", "150", "4", "4"),
                ],
                want_gain_losses=[],
                want_holdings=all_in_coinbase,
            ),
            _Case(
                description="two round trips in a row",
                transactions=[
                    buy_10,
                    coinbase_to_kraken,
                    kraken_to_coinbase,
                    _Intra("t3", "2025-04-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "4", "4"),
                    _Intra("t4", "2025-05-01T00:00:00+00:00", "Kraken", "Coinbase", "150", "4", "4"),
                ],
                want_gain_losses=[],
                want_holdings=all_in_coinbase,
            ),
            _Case(
                # 4 of the 10 coins were moved to Kraken in 2024, so the allocation splits the purchase: 6 coins to Coinbase, 4 to Kraken.
                # In 2025 Kraken's 4 coins go to Coinbase (10 there), all 10 make a trip to BlockFi and back, then 2 go to Kraken.
                # The 4 coins from Kraken were bought in Coinbase: before the fix, on their way back from BlockFi they were returned to the
                # 2024 purchase instead of the lot they left Coinbase from.
                description="split allocation: one purchase allocated to two wallets, then moved between them",
                transactions=[
                    buy_10,
                    _Intra("t0", "2024-09-01T00:00:00+00:00", "Coinbase", "Kraken", "120", "4", "4"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Kraken", "Coinbase", "150", "4", "4"),
                    _Intra("t2", "2025-03-01T00:00:00+00:00", "Coinbase", "BlockFi", "150", "10", "10"),
                    _Intra("t3", "2025-04-01T00:00:00+00:00", "BlockFi", "Coinbase", "150", "10", "10"),
                    _Intra("t4", "2025-05-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "2", "2"),
                ],
                want_gain_losses=[],
                want_holdings=[("Coinbase", "i1", "8", "800", "2024-06-01"), ("Kraken", "i1", "2", "200", "2024-06-01")],
            ),
            _Case(
                # Two purchases at different prices: whatever order the accounting method picks the coins in, each coin comes back to its
                # own lot, with its own cost and date.
                description="two purchases at different prices: all 10 coins to Kraken and back",
                transactions=[
                    _In("i1", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "100", "5"),
                    _In("i2", "2024-07-01T00:00:00+00:00", "Coinbase", "Buy", "300", "5"),
                    _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "10", "10"),
                    _Intra("t2", "2025-03-01T00:00:00+00:00", "Kraken", "Coinbase", "150", "10", "10"),
                ],
                want_gain_losses=[],
                want_holdings=[("Coinbase", "i1", "5", "500", "2024-06-01"), ("Coinbase", "i2", "5", "1500", "2024-07-01")],
            ),
            _Case(
                # The purchase date survives the round trip: a sale more than a year after the 2024 purchase is long-term.
                description="sale after the round trip keeps the 2024 purchase date",
                transactions=[buy_10, coinbase_to_kraken, kraken_to_coinbase, _Out("o1", "2025-07-01T00:00:00+00:00", "Coinbase", "200", "10")],
                want_gain_losses=[_GainLoss("o1", "i1", "10", "1000", "1000", True)],
                want_holdings=[],
            ),
        ]

        methods: Dict[str, AbstractAccountingMethod] = {
            "fifo": AccountingMethodFIFO(),
            "lifo": AccountingMethodLIFO(),
            "hifo": AccountingMethodHIFO(),
            "lofo": AccountingMethodLOFO(),
        }
        for case in cases:
            for method_name, method in methods.items():
                with self.subTest(name=case.description, method=method_name):
                    got_gain_losses, got_holdings = self._run_with_allocation(case.transactions, method)
                    self.assertEqual(_sorted(got_gain_losses), _sorted(self._want_tuples(case.want_gain_losses)))
                    want_holdings: List[_Holding] = [
                        _Holding(wallet, lot, RP2Decimal(amount), RP2Decimal(basis), date) for wallet, lot, amount, basis, date in case.want_holdings
                    ]
                    self.assertEqual(got_holdings, want_holdings)

    # R09 from the review of eprbell/rp2#155: a transfer that receives nothing, e.g. 1 coin sent and 0 received because the whole coin went to
    # fees.
    #
    # The rule in plain English: the coins sent minus the coins received are the transfer fee, and the coins used to pay a transfer fee are
    # disposed of (IRS FAQ A81 and A97). If nothing is received, the whole amount sent is the fee: it's a disposal from the source wallet, and
    # the destination wallet gets nothing. This used to create an empty destination wallet, and the run stopped with "IN transaction set is
    # empty".
    #
    # Example: buy 2 coins for $100 each on Coinbase, then send 1 to Kraken when it's worth $150 and receive 0. The fee is the whole coin: $150
    # of proceeds, $100 of cost basis, $50 of gain. Coinbase still holds the other coin, and Kraken gets nothing (it isn't even created if it
    # never received anything before), as in universal application.
    def test_zero_receipt_transfer(self) -> None:
        class _Case(NamedTuple):
            description: str
            transactions: List[object]
            # What each wallet holds at the end: (wallet, original lot, amount, cost basis, acquisition date).
            want_holdings: List[Tuple[str, str, str, str, str]]
            # The wallets of the transfer analysis.
            want_wallets: List[str]

        purchase = _In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "2")
        zero_receipt = _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "150", "1", "0")
        coinbase_holding = ("Coinbase", "i1", "1", "100", "2025-01-02")
        cases = [
            _Case("a destination that never received anything isn't created", [purchase, zero_receipt], [coinbase_holding], ["Coinbase"]),
            _Case(
                "a destination with funds gets no new lot",
                [purchase, _In("i2", "2025-01-03T00:00:00+00:00", "Kraken", "Buy", "120", "1"), zero_receipt],
                [coinbase_holding, ("Kraken", "i2", "1", "120", "2025-01-03")],
                ["Coinbase", "Kraken"],
            ),
            _Case(
                "a transfer to the same wallet",
                [purchase, _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Coinbase", "150", "1", "0")],
                [coinbase_holding],
                ["Coinbase"],
            ),
        ]
        want = _sorted(self._want_tuples([_GainLoss("t1", "i1", "1", "100", "50", False)]))
        for case in cases:
            with self.subTest(name=case.description):
                configuration = _create_configuration()
                input_data = self._create_input_data(configuration, case.transactions)
                computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
                got = self._to_tuples([gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)])
                self.assertEqual(_sorted(got), want)
                universal_computed_data = compute_tax(configuration, self._create_accounting_engine(None), input_data)
                universal = self._to_tuples([gain_loss for gain_loss in universal_computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)])
                self.assertEqual(_sorted(universal), want)
                wallet_lots = computed_data.wallet_lots
                assert wallet_lots is not None
                want_holdings: List[_Holding] = [
                    _Holding(wallet, lot, RP2Decimal(amount), RP2Decimal(basis), day) for wallet, lot, amount, basis, day in case.want_holdings
                ]
                self.assertEqual(_holdings(wallet_lots), want_holdings)
                wallets = sorted(
                    account.exchange for account in TransferAnalyzer(configuration, AccountingMethodFIFO(), input_data).analyze_and_pair().wallet_2_input_data
                )
                self.assertEqual(wallets, case.want_wallets)

        # Nothing arrived on Kraken, so it has nothing to sell.
        configuration = _create_configuration()
        input_data = self._create_input_data(configuration, [purchase, zero_receipt, _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "200", "0.5")])
        with self.assertRaisesRegex(
            RP2ValueError, r"Insufficient balance on Account\(exchange='Kraken', holder='Bob'\): no funds were ever received by this account"
        ):
            compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)

    def test_per_wallet_is_rejected_for_japan(self) -> None:
        # Japan uses universal application (total/moving average, pooled across all wallets): per-wallet code must never run.
        self._run_test(
            _Test(
                description="JP",
                transactions=[_In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "1")],
                per_wallet_configuration=None,
                want_error="Per-wallet application is not supported for country 'jp'",
            ),
            country=JP(),
        )

    # The per-wallet settings come from the country section of the configuration: without them per-wallet application stops with an error.
    def test_per_wallet_settings_are_required(self) -> None:
        self._run_test(
            _Test(
                description="US without per-wallet settings",
                transactions=[_In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "1")],
                per_wallet_configuration=None,
                want_error=r"B1: per-wallet application needs the per-wallet settings \(at least 'timezone'\) in the 'country.us' section",
            )
        )

    def test_per_wallet_start_year_must_match_the_country_policy(self) -> None:
        # The US policy switches to per-wallet application at the start of 2025: no other switch year is accepted.
        configuration = _create_configuration()
        input_data = self._create_input_data(configuration, [_In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "1")])
        engine = self._create_accounting_engine(None)
        for year in (2024, 2026):
            with self.subTest(year=year):
                with self.assertRaisesRegex(RP2ValueError, f"Per-wallet application can't start in {year} for country 'us'"):
                    compute_tax_per_wallet(configuration, engine, input_data, per_wallet_start_year=year)
        computed_data = compute_tax_per_wallet(configuration, engine, input_data, per_wallet_start_year=2025)
        self.assertEqual(len(list(computed_data.gain_loss_set)), 0)

    # R10 from the review of eprbell/rp2#155: the opening allocation doesn't depend on what happens after the switch, and a report that ends
    # before the switch doesn't need the per-wallet settings.
    #
    # The rule in plain English: the coins held at the start of 2025 get the unused basis of their lots assigned to the wallets that hold them
    # (Rev. Proc. 2024-28), whether or not they are sold or moved later. Example: buy 10 coins for $100 each on Coinbase in 2024 and never sell
    # them. A report that reaches 2025 shows Coinbase holding 10 coins with $1,000 of cost basis and the 2024 purchase date. Before the fix
    # the allocation only ran if the coin had transactions after the switch, so this report used universal application instead.
    def test_opening_allocation_needs_no_later_transactions(self) -> None:
        class _Case(NamedTuple):
            description: str
            transactions: List[object]
            per_wallet_configuration: Optional[PerWalletConfiguration] = _UTC
            to_date: date = MAX_DATE
            # What the wallets hold at the to date: (wallet, original lot, amount, cost basis, acquisition date). None: the report ends before
            # the switch, so it uses universal application, which doesn't track wallets (see ComputedData.wallet_lots).
            want_holdings: Optional[List[Tuple[str, str, str, str, str]]] = None
            want_error: str = ""

        buy_coinbase = _In("i1", "2024-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10")
        buy_kraken = _In("i2", "2024-01-03T00:00:00+00:00", "Kraken", "Buy", "200", "10")
        cases = [
            _Case(
                description="one wallet: its coins are allocated to it automatically",
                transactions=[buy_coinbase],
                want_holdings=[("Coinbase", "i1", "10", "1000", "2024-01-02")],
            ),
            _Case(
                description="a report that ends on the day of the switch",
                transactions=[buy_coinbase],
                to_date=date(2025, 1, 1),
                want_holdings=[("Coinbase", "i1", "10", "1000", "2024-01-02")],
            ),
            _Case(
                # Universal FIFO pairs the 2024 sale with i1: 6 of its 10 coins are unused at the switch, with $600 of basis.
                description="a lot partly sold before the switch: only its unused part is allocated",
                transactions=[buy_coinbase, _Out("o1", "2024-06-01T00:00:00+00:00", "Coinbase", "150", "4")],
                want_holdings=[("Coinbase", "i1", "6", "600", "2024-01-02")],
            ),
            _Case(
                description="two wallets: the configured rule decides (FIFO lots, Kraken filled first, so Kraken gets the oldest lot)",
                transactions=[buy_coinbase, buy_kraken],
                per_wallet_configuration=_allocation_config((_KRAKEN, _COINBASE)),
                want_holdings=[("Coinbase", "i2", "10", "2000", "2024-01-03"), ("Kraken", "i1", "10", "1000", "2024-01-02")],
            ),
            _Case(
                description="two wallets without an allocation rule: an error, even without later transactions",
                transactions=[buy_coinbase, buy_kraken],
                want_error="Unused basis allocation is needed",
            ),
            _Case(
                # Two funded wallets and no per-wallet settings at all: they would be needed for 2025, but the report ends in 2024.
                description="a report that ends before the switch: universal application, without the per-wallet settings",
                transactions=[buy_coinbase, buy_kraken, _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "300", "5")],
                per_wallet_configuration=None,
                to_date=date(2024, 12, 31),
            ),
        ]
        for case in cases:
            with self.subTest(name=case.description):
                configuration = _create_configuration(case.per_wallet_configuration, to_date=case.to_date)
                input_data = self._create_input_data(configuration, case.transactions)
                if case.want_error:
                    with self.assertRaisesRegex(RP2ValueError, case.want_error):
                        compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
                    continue
                computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
                # Nothing after the switch is reported, so the reported gain/losses are those of universal application.
                got = self._to_tuples([gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)])
                universal_computed_data = compute_tax(configuration, self._create_accounting_engine(None), input_data)
                universal = self._to_tuples([gain_loss for gain_loss in universal_computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)])
                self.assertEqual(_sorted(got), _sorted(universal))
                wallet_lots = computed_data.wallet_lots
                if case.want_holdings is None:
                    self.assertIsNone(wallet_lots)
                    continue
                assert wallet_lots is not None
                want_holdings: List[_Holding] = [
                    _Holding(wallet, lot, RP2Decimal(amount), RP2Decimal(basis), day) for wallet, lot, amount, basis, day in case.want_holdings
                ]
                self.assertEqual(_holdings(wallet_lots), want_holdings)

    def test_artificial_in_transaction_is_not_income(self) -> None:
        configuration = Configuration(_CONFIGURATION_PATH, US())
        income = InTransaction(configuration, "2025-01-02T00:00:00+00:00", _ASSET, "Coinbase", "Bob", "Income", RP2Decimal("1"), RP2Decimal("1"))
        artificial = InTransaction(
            configuration, "2025-01-03T00:00:00+00:00", _ASSET, "Kraken", "Bob", "Income", RP2Decimal("1"), RP2Decimal("1"), from_lot=income
        )
        self.assertTrue(income.is_taxable())
        self.assertFalse(artificial.is_taxable())
        self.assertIs(artificial.original_lot, income)
        transactions: List[AbstractTransaction] = [artificial]
        self.assertFalse(any(transaction.is_earning() for transaction in transactions))

    # WalletLot (what a wallet holds of a lot, see ComputedData.wallet_lots): its derived values and checks. Example: 2 coins bought for
    # $200 plus a $2 fee in 2024, 1 of them moved to Kraken in 2025 (a lot with $101 of cost basis, fee included): half of it costs $50.50
    # and keeps the 2024 purchase date.
    def test_wallet_lot(self) -> None:
        configuration = Configuration(_CONFIGURATION_PATH, US())
        purchase = InTransaction(
            configuration, "2024-06-01T00:00:00+00:00", _ASSET, "Coinbase", "Bob", "Buy", RP2Decimal("100"), RP2Decimal("2"), fiat_fee=RP2Decimal("2")
        )
        moved = InTransaction(
            configuration,
            "2025-02-01T00:00:00+00:00",
            _ASSET,
            "Kraken",
            "Bob",
            "Buy",
            RP2Decimal("100"),
            RP2Decimal("1"),
            fiat_in_no_fee=RP2Decimal("100"),
            fiat_fee=RP2Decimal("1"),
            from_lot=purchase,
            cost_basis_timestamp="2024-06-01T00:00:00+00:00",
        )
        wallet_lot = WalletLot(_KRAKEN, moved, RP2Decimal("0.5"))
        self.assertEqual(wallet_lot.cost_basis, RP2Decimal("50.5"))
        self.assertEqual(wallet_lot.acquisition_timestamp, purchase.timestamp)
        self.assertIs(wallet_lot.original_lot, purchase)
        # Equal wallet lots can be used in sets and as dictionary keys.
        self.assertEqual(len({wallet_lot, WalletLot(_KRAKEN, moved, RP2Decimal("0.5"))}), 1)
        with self.assertRaisesRegex(RP2ValueError, "Wallet lot amount 1.5 exceeds the lot amount 1"):
            WalletLot(_KRAKEN, moved, RP2Decimal("1.5"))
        with self.assertRaisesRegex(RP2ValueError, "Parameter 'amount' has zero value"):
            WalletLot(_KRAKEN, moved, ZERO)
        with self.assertRaisesRegex(RP2TypeError, "Parameter 'account' is not of type Account"):
            WalletLot("Kraken", moved, RP2Decimal("1"))  # type: ignore

    # The holdings date of TransferAnalyzer.analyze_and_pair() must be a date: a string or a datetime is rejected right away.
    def test_holdings_date_must_be_a_date(self) -> None:
        configuration = Configuration(_CONFIGURATION_PATH, US())
        input_data = self._create_input_data(configuration, [_In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "1")])
        analyzer = TransferAnalyzer(configuration, AccountingMethodFIFO(), input_data)
        invalid_dates: List[object] = ["2025-04-30", datetime(2025, 4, 30)]
        for invalid_date in invalid_dates:
            with self.subTest(holdings_date=invalid_date):
                with self.assertRaisesRegex(RP2TypeError, "Parameter 'holdings_date' is not of type date"):
                    analyzer.analyze_and_pair(holdings_date=invalid_date)  # type: ignore
        self.assertEqual(len(analyzer.analyze_and_pair(holdings_date=date(2025, 4, 30)).wallet_lots), 1)

    # compute_tax_per_wallet() can run more than once on the same input data (e.g. in a program that uses RP2 as a library). Each run creates
    # new lots for the opening allocation and the transfers, with new ids, but the input lots are the same objects: their to_lots (where
    # their coins went) must only list the lots of the latest run, not also those of the earlier runs, which no wallet holds. The results are
    # the same in every run. Example: 2 coins bought in 2024 (lot i1, allocated to Coinbase at the switch) and 1 coin bought in 2025 (lot i2)
    # are all sent to Kraken, where 1 coin of i1 is sold. Without the fix, after the second run i1.to_lots listed two Kraken lots: the one of
    # the first run and the one of the second run.
    def test_repeated_computation_keeps_only_its_own_links(self) -> None:
        configuration = _create_configuration()
        transactions: List[object] = [
            _In("i1", "2024-06-01T00:00:00+00:00", "Coinbase", "Buy", "100", "2"),
            _In("i2", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "150", "1"),
            _Intra("t1", "2025-02-01T00:00:00+00:00", "Coinbase", "Kraken", "200", "3", "3"),
            _Out("o1", "2025-03-01T00:00:00+00:00", "Kraken", "250", "1"),
        ]
        input_data = self._create_input_data(configuration, transactions)
        input_lots: List[InTransaction] = [lot for lot in input_data.unfiltered_in_transaction_set if isinstance(lot, InTransaction)]
        want_gain_losses = self._want_tuples([_GainLoss("o1", "i1", "1", "100", "150", False)])
        for run in (1, 2):
            with self.subTest(run=run):
                computed_data = compute_tax_per_wallet(configuration, self._create_accounting_engine(None), input_data)
                self.assertEqual(self._to_tuples([gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)]), want_gain_losses)
                wallet_lots = computed_data.wallet_lots
                assert wallet_lots is not None
                for input_lot in input_lots:
                    # Kraken holds 1 coin of each input lot, in the lot that this run created there.
                    kraken_lots = [wallet_lot.lot for wallet_lot in wallet_lots if wallet_lot.account == _KRAKEN and wallet_lot.original_lot is input_lot]
                    want_to_lots: Dict[str, List[str]] = {"Kraken": [lot.unique_id for lot in kraken_lots]}
                    got_to_lots: Dict[str, List[str]] = {account.exchange: [lot.unique_id for lot in lots] for account, lots in input_lot.to_lots.items()}
                    self.assertEqual(got_to_lots, want_to_lots, msg=f"to_lots of {input_lot.unique_id}")


if __name__ == "__main__":
    unittest.main()

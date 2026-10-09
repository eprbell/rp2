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
from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import Configuration
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
    per_wallet_configuration: PerWalletConfiguration = _UTC
    allocation_method: Optional[AbstractAccountingMethod] = None
    years_2_methods: Optional[Dict[int, AbstractAccountingMethod]] = None
    # With a single wallet per-wallet and universal application must produce the same result.
    same_as_universal: bool = False


class TestPerWalletTaxEngine(AbstractPerWalletTest):
    def _run_test(self, test: _Test, country: object = None) -> None:
        configuration = Configuration(_CONFIGURATION_PATH, country or US())  # type: ignore
        input_data = self._create_input_data(configuration, test.transactions)
        engine = self._create_accounting_engine(test.years_2_methods)
        if test.want_error:
            with self.assertRaisesRegex(RP2ValueError, test.want_error):
                compute_tax_per_wallet(configuration, engine, input_data, test.per_wallet_configuration, test.allocation_method)
            return
        computed_data = compute_tax_per_wallet(configuration, engine, input_data, test.per_wallet_configuration, test.allocation_method)
        got: List[_GainLossTuple] = self._to_tuples([gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)])
        self.assertEqual(_sorted(got), _sorted(self._want_tuples(test.want)))
        if test.same_as_universal:
            universal_computed_data = compute_tax(configuration, self._create_accounting_engine(test.years_2_methods), input_data)
            universal = self._to_tuples([gain_loss for gain_loss in universal_computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)])
            self.assertEqual(_sorted(got), _sorted(universal))

    def test_per_wallet(self) -> None:  # pylint: disable=too-many-statements
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
                allocation_method=AccountingMethodFIFO(),
                want=[_GainLoss("o1", "i1", "5", "500", "1000", True)],
            ),
            _Test(
                description="Unused basis allocation: HIFO lots, Kraken filled first, so Kraken gets the most expensive lot (i2)",
                transactions=[
                    _In("i1", "2024-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "10"),
                    _In("i2", "2024-01-03T00:00:00+00:00", "Kraken", "Buy", "200", "10"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Kraken", "300", "5"),
                ],
                per_wallet_configuration=_allocation_config((_KRAKEN, _COINBASE)),
                allocation_method=AccountingMethodHIFO(),
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
                per_wallet_configuration=_allocation_config((_KRAKEN, _COINBASE)),
                allocation_method=AccountingMethodHIFO(),
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
                allocation_method=AccountingMethodFIFO(),
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
                allocation_method=AccountingMethodFIFO(),
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
                allocation_method=AccountingMethodFIFO(),
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
                description="Timezone: 2025-01-01 03:00 JST is 2024 in New York: the transaction is ambiguous and must be fixed by the user",
                transactions=[
                    _In("i1", "2025-01-01T03:00:00+09:00", "Coinbase", "Buy", "100", "1"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Coinbase", "200", "1"),
                ],
                per_wallet_configuration=PerWalletConfiguration(timezone_name="America/New_York"),
                want_error="fall in tax year 2025 .* but before the switch to per-wallet application",
            ),
            _Test(
                description="Timezone: 2025-01-01 03:00 JST with the switch in Tokyo time is per-wallet",
                transactions=[
                    _In("i1", "2025-01-01T03:00:00+09:00", "Coinbase", "Buy", "100", "1"),
                    _Out("o1", "2025-02-01T00:00:00+00:00", "Coinbase", "200", "1"),
                ],
                per_wallet_configuration=PerWalletConfiguration(timezone_name="Asia/Tokyo"),
                want=[_GainLoss("o1", "i1", "1", "100", "100", False)],
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
    def _run_with_allocation(self, transactions: List[object], method: AbstractAccountingMethod) -> Tuple[List[_GainLossTuple], List[_Holding]]:
        configuration = Configuration(_CONFIGURATION_PATH, US())
        computed_data = compute_tax_per_wallet(
            configuration,
            self._create_accounting_engine({1970: method}),
            self._create_input_data(configuration, transactions),
            _allocation_config((_COINBASE, _KRAKEN, _BLOCKFI)),
            AccountingMethodFIFO(),
        )
        gain_losses = self._to_tuples([gain_loss for gain_loss in computed_data.gain_loss_set if isinstance(gain_loss, GainLoss)])
        wallet_lots = computed_data.wallet_lots
        assert wallet_lots is not None
        return gain_losses, _holdings(wallet_lots)

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
                        (wallet, lot, RP2Decimal(amount), RP2Decimal(basis), date) for wallet, lot, amount, basis, date in case.want_holdings
                    ]
                    self.assertEqual(got_holdings, want_holdings)

    def test_per_wallet_is_rejected_for_japan(self) -> None:
        # Japan uses universal application (total/moving average, pooled across all wallets): per-wallet code must never run.
        self._run_test(
            _Test(
                description="JP",
                transactions=[_In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "1")],
                want_error="Per-wallet application is not supported for country 'jp'",
            ),
            country=JP(),
        )

    def test_per_wallet_start_year_must_match_the_country_policy(self) -> None:
        # The US policy switches to per-wallet application at the start of 2025: no other switch year is accepted.
        configuration = Configuration(_CONFIGURATION_PATH, US())
        input_data = self._create_input_data(configuration, [_In("i1", "2025-01-02T00:00:00+00:00", "Coinbase", "Buy", "100", "1")])
        engine = self._create_accounting_engine(None)
        for year in (2024, 2026):
            with self.subTest(year=year):
                with self.assertRaisesRegex(RP2ValueError, f"Per-wallet application can't start in {year} for country 'us'"):
                    compute_tax_per_wallet(configuration, engine, input_data, _UTC, per_wallet_start_year=year)
        computed_data = compute_tax_per_wallet(configuration, engine, input_data, _UTC, per_wallet_start_year=2025)
        self.assertEqual(len(list(computed_data.gain_loss_set)), 0)

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


if __name__ == "__main__":
    unittest.main()

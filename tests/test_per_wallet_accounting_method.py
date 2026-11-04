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

# The two module-level rules that per-wallet application shares (R13): which accounting method per-wallet application uses for a configured
# one (used by both TransferAnalyzer and UnusedBasisAllocator), and how a method name becomes a method (used by the command line and by the
# per-wallet tax engine).

import unittest
from typing import cast

from rp2.abstract_accounting_method import (
    AbstractAccountingMethod,
    AbstractChronologicalAccountingMethod,
    AcquiredLotCandidatesOrder,
)
from rp2.accounting_method_loader import load_accounting_method
from rp2.acquisition_date_fifo import AcquisitionDateFifo
from rp2.per_wallet_accounting_method import get_per_wallet_accounting_method
from rp2.plugin.accounting_method.fifo import AccountingMethod as AccountingMethodFIFO
from rp2.plugin.accounting_method.hifo import AccountingMethod as AccountingMethodHIFO
from rp2.plugin.accounting_method.lifo import AccountingMethod as AccountingMethodLIFO
from rp2.plugin.accounting_method.lofo import AccountingMethod as AccountingMethodLOFO
from rp2.rp2_error import RP2TypeError, RP2ValueError


# A chronological method that selects the newest lot first: per-wallet application replaces it with the feature-based LIFO, which sorts lots
# by original acquisition date.
class _ChronologicalNewestFirst(AbstractChronologicalAccountingMethod):
    def lot_candidates_order(self) -> AcquiredLotCandidatesOrder:
        return AcquiredLotCandidatesOrder.NEWER_TO_OLDER


class TestPerWalletAccountingMethod(unittest.TestCase):
    def test_get_per_wallet_accounting_method(self) -> None:
        # FIFO selects lots by position, i.e. by arrival in the wallet: per-wallet application uses FIFO by acquisition date instead.
        per_wallet_fifo = get_per_wallet_accounting_method(AccountingMethodFIFO())
        self.assertIsInstance(per_wallet_fifo, AcquisitionDateFifo)
        self.assertEqual(per_wallet_fifo.name, "fifo")
        self.assertIsInstance(get_per_wallet_accounting_method(_ChronologicalNewestFirst()), AccountingMethodLIFO)
        # Feature-based methods sort lots by a feature of the lot (price or acquisition date): they are used as they are.
        for method in (AccountingMethodHIFO(), AccountingMethodLOFO(), AccountingMethodLIFO()):
            with self.subTest(method=method.name):
                self.assertIs(get_per_wallet_accounting_method(method), method)
        with self.assertRaisesRegex(RP2TypeError, "Unsupported accounting method for per-wallet application"):
            get_per_wallet_accounting_method(AbstractAccountingMethod())

    def test_load_accounting_method(self) -> None:
        for name, method_class in (
            ("fifo", AccountingMethodFIFO),
            ("hifo", AccountingMethodHIFO),
            ("lifo", AccountingMethodLIFO),
            ("lofo", AccountingMethodLOFO),
        ):
            with self.subTest(name=name):
                method = load_accounting_method(name)
                self.assertIsInstance(method, method_class)
                self.assertEqual(method.name, name)
        with self.assertRaisesRegex(RP2ValueError, "Invalid/unsupported accounting method: fifi"):
            load_accounting_method("fifi")
        with self.assertRaisesRegex(RP2TypeError, "not a non-empty string"):
            load_accounting_method(cast(str, None))


if __name__ == "__main__":
    unittest.main()

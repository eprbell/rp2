# Copyright 2021 eprbell
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

from datetime import datetime
from decimal import Decimal
from typing import Optional, cast

from abstract_entry import AbstractEntry
from abstract_transaction import AbstractTransaction
from configuration import Configuration
from entry_types import TransactionType
from in_transaction import InTransaction
from rp2_decimal import ZERO
from rp2_error import RP2TypeError, RP2ValueError


class GainLoss(AbstractEntry):
    def __init__(
        self,
        configuration: Configuration,
        crypto_amount: Decimal,
        taxable_event: AbstractTransaction,
        from_lot: Optional[InTransaction],
    ) -> None:

        self.__taxable_event: AbstractTransaction = cast(AbstractTransaction, AbstractTransaction.type_check("taxable_event", taxable_event))
        if not taxable_event.is_taxable():
            raise RP2ValueError(f"Parameter 'taxable_event' of class {taxable_event.__class__.__name__} is not taxable: {taxable_event}")

        super().__init__(configuration, taxable_event.asset)

        self.__crypto_amount: Decimal = configuration.type_check_positive_decimal("crypto_amount", crypto_amount, non_zero=True)

        if taxable_event.transaction_type != TransactionType.EARN:
            if from_lot is None:
                raise RP2TypeError("from_lot must not be None for non-EARN-typed taxable_events")
            InTransaction.type_check("from_lot", from_lot)
        else:
            if crypto_amount != taxable_event.crypto_balance_change:
                raise RP2ValueError(
                    f"crypto_amount must be == taxable_event.crypto_balance_change for EARN-typed taxable events, "
                    f"but they differ {crypto_amount} != {taxable_event.crypto_balance_change}"
                )
            if from_lot is not None:
                raise RP2TypeError(f"from_lot must be None for EARN-typed taxable_events, instead it's {from_lot}")
        self.__from_lot: Optional[InTransaction] = from_lot

        if self.__crypto_amount > self.__taxable_event.crypto_balance_change or (self.__from_lot and self.__crypto_amount > self.__from_lot.crypto_in):
            raise RP2ValueError(
                f"crypto_amount ({self.__crypto_amount}) is greater than taxable event amount ({self.__taxable_event.crypto_balance_change}) "
                f"or from-lot amount ({self.__from_lot.crypto_in if self.__from_lot else 0}): {self}"
            )

        if from_lot is not None and taxable_event.timestamp <= from_lot.timestamp:
            raise RP2ValueError(f"Timestamp of taxable_event <= timestamp of from_lot: {self}")

        if from_lot is not None and taxable_event.asset != from_lot.asset:
            raise RP2ValueError(f"taxable_event.asset ({taxable_event.asset}) != from_lot.asset ({from_lot.asset})")

    @classmethod
    def type_check(cls, name: str, instance: "AbstractEntry") -> "GainLoss":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, GainLoss):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __str__(self) -> str:
        return (
            "{}:\n  id={}\n  crypto_amount={:.8f}\n  usd_cost_basis={:.4f}\n  usd_gain={:.4f}\n  is_long_term_capital_gains={}\n  taxable_event_usd_amount_with_fee_fraction={:.4f}\n  taxable_event_fraction_percentage={:.4%}\n  taxable_event={}\n  from_lot_usd_amount_with_fee_fraction={:.4f}\n  from_lot_fraction_percentage={:.4%}\n  from_lot={}"
        ).format(
            type(self).__name__,
            repr(self.id),
            self.crypto_amount,
            self.usd_cost_basis,
            self.usd_gain,
            self.is_long_term_capital_gains(),
            self.taxable_event_usd_amount_with_fee_fraction,
            self.taxable_event_fraction_percentage,
            str(self.taxable_event).replace("  ", "    "),
            self.from_lot_usd_amount_with_fee_fraction,
            self.from_lot_fraction_percentage,
            str(self.from_lot).replace("  ", "    "),
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"(id={repr(self.id)}, "
            f"crypto_amount={self.crypto_amount:.8f}, "
            f"usd_cost_basis={self.usd_cost_basis:.4f}, "
            f"usd_gain={self.usd_gain:.4f}, "
            f"is_long_term_capital_gains={self.is_long_term_capital_gains()}, "
            f"taxable_event_usd_amount_with_fee_fraction={self.taxable_event_usd_amount_with_fee_fraction:.4f}, "
            f"taxable_event_fraction_percentage={self.taxable_event_fraction_percentage:.4%}, "
            f"taxable_event={repr(self.taxable_event)}, "
            f"from_lot_usd_amount_with_fee_fraction={self.from_lot_usd_amount_with_fee_fraction:.4f}, "
            f"from_lot_fraction_percentage={self.from_lot_fraction_percentage:.4%}, "
            f"from_lot={repr(self.from_lot)})"
        )

    @property
    def id(self) -> str:
        if not self.from_lot:
            # EARN taxable event doesn't have from lot
            return f"{self.taxable_event.line}->None"
        return f"{self.taxable_event.line}->{self.from_lot.line}"

    @property
    def timestamp(self) -> datetime:
        return self.taxable_event.timestamp

    @property
    def taxable_event(self) -> AbstractTransaction:
        return self.__taxable_event

    @property
    def from_lot(self) -> Optional[InTransaction]:
        return self.__from_lot

    @property
    def crypto_amount(self) -> Decimal:
        return self.__crypto_amount

    @property
    def crypto_balance_change(self) -> Decimal:
        return self.crypto_amount

    @property
    def usd_balance_change(self) -> Decimal:
        return self.taxable_event.usd_balance_change

    @property
    def taxable_event_usd_amount_with_fee_fraction(self) -> Decimal:
        # We don't simply multiply by taxable_event_fraction_percentage to avoid potential precision loss with small percentages
        return (self.taxable_event.usd_taxable_amount * self.crypto_amount) / self.taxable_event.crypto_balance_change

    @property
    def from_lot_usd_amount_with_fee_fraction(self) -> Decimal:
        if not self.from_lot:
            return ZERO
        # We don't simply multiply by from_lot_fraction_percentage to avoid potential precision loss with small percentages
        return (self.from_lot.usd_in_with_fee * self.crypto_amount) / self.from_lot.crypto_balance_change

    @property
    def taxable_event_fraction_percentage(self) -> Decimal:
        return self.crypto_amount / self.taxable_event.crypto_balance_change

    @property
    def from_lot_fraction_percentage(self) -> Decimal:
        if not self.from_lot:
            # Earn taxable events don't have a from_lot
            if self.taxable_event.transaction_type != TransactionType.EARN:
                raise Exception("Internal error: from lot is None but taxable event is not of type EARN")
            return ZERO
        return self.crypto_amount / self.from_lot.crypto_balance_change

    @property
    def usd_cost_basis(self) -> Decimal:
        if not self.from_lot:
            # Earn taxable events don't have a from_lot and their cost basis is 0
            if self.taxable_event.transaction_type != TransactionType.EARN:
                raise Exception("Internal error: from lot is None but taxable event is not of type EARN")
            return ZERO
        # We don't simply multiply by from_lot_fraction_percentage to avoid potential precision loss with small percentages
        return (self.from_lot.usd_in_with_fee * self.crypto_amount) / self.from_lot.crypto_balance_change

    @property
    def usd_gain(self) -> Decimal:
        return self.taxable_event_usd_amount_with_fee_fraction - self.usd_cost_basis

    def is_long_term_capital_gains(self) -> bool:
        if not self.from_lot:
            # Earn taxable events don't have a from lot and are always considered short term capital gains
            if self.taxable_event.transaction_type != TransactionType.EARN:
                raise Exception("Internal error: from lot is None but taxable event is not of type EARN")
            return False
        return (self.taxable_event.timestamp - self.from_lot.timestamp).days >= 365

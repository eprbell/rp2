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
from typing import Callable, List, Optional, cast

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.abstract_entry import AbstractEntry
from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import Configuration
from rp2.in_transaction import InTransaction
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError


class GainLoss(AbstractEntry):
    def __init__(
        self,
        configuration: Configuration,
        accounting_method: AbstractAccountingMethod,
        crypto_amount: RP2Decimal,
        taxable_event: AbstractTransaction,
        acquired_lot: Optional[InTransaction],
    ) -> None:

        AbstractAccountingMethod.type_check("accounting_method", accounting_method)
        self.__taxable_event: AbstractTransaction = cast(AbstractTransaction, AbstractTransaction.type_check("taxable_event", taxable_event))
        if not taxable_event.is_taxable():
            raise RP2ValueError(f"Parameter 'taxable_event' of class {taxable_event.__class__.__name__} is not taxable: {taxable_event}")

        super().__init__(configuration, taxable_event.asset)

        self.__crypto_amount: RP2Decimal = configuration.type_check_positive_decimal("crypto_amount", crypto_amount, non_zero=True)

        if not taxable_event.transaction_type.is_earn_type():
            if acquired_lot is None:
                raise RP2TypeError("acquired_lot must not be None for non-earn-typed taxable_events")
            InTransaction.type_check("acquired_lot", acquired_lot)
        else:
            if crypto_amount != taxable_event.crypto_balance_change:
                raise RP2ValueError(
                    f"crypto_amount must be == taxable_event.crypto_balance_change for earn-typed taxable events, "
                    f"but they differ {crypto_amount} != {taxable_event.crypto_balance_change}"
                )
            if acquired_lot is not None:
                raise RP2TypeError(f"acquired_lot must be None for earn-typed taxable_events, instead it's {acquired_lot}")
        self.__acquired_lot: Optional[InTransaction] = acquired_lot

        if self.__crypto_amount > self.__taxable_event.crypto_balance_change or (self.__acquired_lot and self.__crypto_amount > self.__acquired_lot.crypto_in):
            raise RP2ValueError(
                f"crypto_amount ({self.__crypto_amount}) is greater than taxable event amount ({self.__taxable_event.crypto_balance_change}) "
                f"or acquired-lot amount ({self.__acquired_lot.crypto_in if self.__acquired_lot else 0}): {self}"
            )

        if acquired_lot is not None and taxable_event.timestamp < acquired_lot.timestamp:
            raise RP2ValueError(
                f"Timestamp {taxable_event.timestamp} of taxable_event is earlier than timestamp {acquired_lot.timestamp} " f"of acquired_lot: {self}"
            )

        if acquired_lot is not None and taxable_event.asset != acquired_lot.asset:
            raise RP2ValueError(f"taxable_event.asset ({taxable_event.asset}) != acquired_lot.asset ({acquired_lot.asset})")

    @classmethod
    def type_check(cls, name: str, instance: "AbstractEntry") -> "GainLoss":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __eq__(self, other: object) -> bool:
        if not other:
            return False
        if not isinstance(other, GainLoss):
            raise RP2TypeError(f"Operand has non-GainLoss value {repr(other)}")
        self_acquired_lot_internal_id: Optional[str] = self.acquired_lot.internal_id if self.acquired_lot else None
        other_acquired_lot_internal_id: Optional[str] = other.acquired_lot.internal_id if other.acquired_lot else None
        # By definition, internal_id can uniquely identify a transaction: this works even if it's the ODS line from the spreadsheet,
        # since there are no cross-asset transactions (so a spreadsheet line points to a unique transaction for that asset).
        result: bool = self.taxable_event.internal_id == other.taxable_event.internal_id and self_acquired_lot_internal_id == other_acquired_lot_internal_id
        return result

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        # By definition, internal_id can uniquely identify a transaction: this works even if it's the ODS line from the spreadsheet,
        # since there are no cross-asset transactions (so a spreadsheet line points to a unique transaction for that asset).
        return hash((self.taxable_event.internal_id, self.acquired_lot.internal_id if self.acquired_lot else None))

    def to_string(self, indent: int = 0, repr_format: bool = True, extra_data: Optional[List[str]] = None) -> str:
        self.configuration.type_check_positive_int("indent", indent)
        self.configuration.type_check_bool("repr_format", repr_format)
        if extra_data and not isinstance(extra_data, List):
            raise RP2TypeError(f"Parameter 'extra_data' is not of type List: {extra_data}")

        class_specific_data: List[str] = []
        stringify: Callable[[object], str] = str
        if repr_format:
            stringify = repr
        class_specific_data = [
            f"crypto_amount={self.crypto_amount:.8f}",
            f"fiat_cost_basis={self.fiat_cost_basis:.4f}",
            f"fiat_gain={self.fiat_gain:.4f}",
            f"is_long_term_capital_gains={stringify(self.is_long_term_capital_gains())}",
            f"taxable_event_fiat_amount_with_fee_fraction={self.taxable_event_fiat_amount_with_fee_fraction:.4f}",
            f"taxable_event_fraction_percentage={self.taxable_event_fraction_percentage:.4%}",
            f"taxable_event={self.taxable_event.to_string(indent=indent + 1, repr_format=repr_format).lstrip()}",
            f"acquired_lot_fiat_amount_with_fee_fraction={self.acquired_lot_fiat_amount_with_fee_fraction:.4f}",
            f"acquired_lot_fraction_percentage={self.acquired_lot_fraction_percentage:.4%}",
            f"acquired_lot={self.acquired_lot.to_string(indent=indent + 1, repr_format=repr_format).lstrip() if self.acquired_lot else 'None'}",
        ]
        if extra_data:
            class_specific_data.extend(extra_data)

        return super().to_string(indent=indent, repr_format=repr_format, extra_data=class_specific_data)

    @property
    def internal_id(self) -> str:
        if not self.acquired_lot:
            # earn-typed taxable event doesn't have acquired lot
            return f"{self.taxable_event.internal_id}->None"
        return f"{self.taxable_event.internal_id}->{self.acquired_lot.internal_id}"

    @property
    def timestamp(self) -> datetime:
        return self.taxable_event.timestamp

    @property
    def taxable_event(self) -> AbstractTransaction:
        return self.__taxable_event

    @property
    def acquired_lot(self) -> Optional[InTransaction]:
        return self.__acquired_lot

    @property
    def crypto_amount(self) -> RP2Decimal:
        return self.__crypto_amount

    @property
    def crypto_balance_change(self) -> RP2Decimal:
        return self.crypto_amount

    @property
    def fiat_balance_change(self) -> RP2Decimal:
        return self.taxable_event.fiat_balance_change

    @property
    def taxable_event_fiat_amount_with_fee_fraction(self) -> RP2Decimal:
        # We don't simply multiply by taxable_event_fraction_percentage to avoid potential precision loss with small percentages
        return (self.taxable_event.fiat_taxable_amount * self.crypto_amount) / self.taxable_event.crypto_balance_change

    @property
    def acquired_lot_fiat_amount_with_fee_fraction(self) -> RP2Decimal:
        if not self.acquired_lot:
            return ZERO
        # We don't simply multiply by acquired_lot_fraction_percentage to avoid potential precision loss with small percentages
        return (self.acquired_lot.fiat_in_with_fee * self.crypto_amount) / self.acquired_lot.crypto_balance_change

    @property
    def taxable_event_fraction_percentage(self) -> RP2Decimal:
        return self.crypto_amount / self.taxable_event.crypto_balance_change

    @property
    def acquired_lot_fraction_percentage(self) -> RP2Decimal:
        if not self.acquired_lot:
            # Earn-typed taxable events don't have a acquired_lot
            if not self.taxable_event.transaction_type.is_earn_type():
                raise Exception("Internal error: acquired lot is None but taxable event is not earn-typed")
            return ZERO
        return self.crypto_amount / self.acquired_lot.crypto_balance_change

    @property
    def fiat_cost_basis(self) -> RP2Decimal:
        if not self.acquired_lot:
            # Earn-typed taxable events don't have a acquired_lot and their cost basis is 0
            if not self.taxable_event.transaction_type.is_earn_type():
                raise Exception("Internal error: acquired lot is None but taxable event is not earn-typed")
            return ZERO
        # The cost basis is fiat_in + fee (as explained in https://www.irs.gov/publications/p544 and
        # https://taxbit.com/cryptocurrency-tax-guide).
        # Also note that we don't simply multiply by acquired_lot_fraction_percentage to avoid potential precision loss
        # with small percentages.
        return (self.acquired_lot.fiat_in_with_fee * self.crypto_amount) / self.acquired_lot.crypto_balance_change

    @property
    def fiat_gain(self) -> RP2Decimal:
        return self.taxable_event_fiat_amount_with_fee_fraction - self.fiat_cost_basis

    def is_long_term_capital_gains(self) -> bool:
        if not self.acquired_lot:
            # Earn-typed taxable events don't have a acquired lot and are always considered short term capital gains
            if not self.taxable_event.transaction_type.is_earn_type():
                raise Exception("Internal error: acquired lot is None but taxable event is not earn-typed")
            return False
        return (self.taxable_event.timestamp - self.acquired_lot.timestamp).days >= self.configuration.country.long_term_capital_gain_period()

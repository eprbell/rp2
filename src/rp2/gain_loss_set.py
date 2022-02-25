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

from datetime import date
from typing import Dict, List, Optional, cast

from rp2.abstract_accounting_method import AbstractAccountingMethod
from rp2.abstract_entry import AbstractEntry
from rp2.abstract_entry_set import AbstractEntrySet
from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import MAX_DATE, MIN_DATE, Configuration
from rp2.entry_types import TransactionType
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.logger import LOGGER
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError


class GainLossSet(AbstractEntrySet):
    @classmethod
    def type_check(cls, name: str, instance: "GainLossSet") -> "GainLossSet":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def __init__(
        self,
        configuration: Configuration,
        accounting_method: AbstractAccountingMethod,
        asset: str,
        from_date: date = MIN_DATE,
        to_date: date = MAX_DATE,
    ) -> None:
        super().__init__(configuration, "MIXED", asset, from_date, to_date)
        self.__accounting_method = AbstractAccountingMethod.type_check("accounting_method", accounting_method)
        self.__taxable_events_to_fraction: Dict[GainLoss, int] = {}
        self.__acquired_lots_to_fraction: Dict[GainLoss, int] = {}
        self.__taxable_events_to_number_of_fractions: Dict[AbstractTransaction, int] = {}
        self.__acquired_lots_to_number_of_fractions: Dict[InTransaction, int] = {}
        self.__transaction_type_2_count: Dict[TransactionType, int] = {transaction_type: 0 for transaction_type in TransactionType}

    def add_entry(self, entry: AbstractEntry) -> None:
        GainLoss.type_check("entry", entry)
        super().add_entry(entry)

    def get_transaction_type_count(self, transaction_type: TransactionType) -> int:
        TransactionType.type_check("transaction_type", transaction_type)
        self._check_sort()
        return self.__transaction_type_2_count[transaction_type]

    def get_taxable_event_fraction(self, entry: GainLoss) -> int:
        self._validate_entry(entry)
        self._check_sort()
        return self.__taxable_events_to_fraction[entry]

    def get_acquired_lot_fraction(self, entry: GainLoss) -> int:
        self._validate_entry(entry)
        self._check_sort()
        return self.__acquired_lots_to_fraction[entry]

    def get_taxable_event_number_of_fractions(self, transaction: AbstractTransaction) -> int:
        AbstractTransaction.type_check("transaction", transaction)
        if transaction not in self.__taxable_events_to_number_of_fractions:
            raise RP2ValueError(f"Unknown transaction:\n{transaction}")
        self._check_sort()
        return self.__taxable_events_to_number_of_fractions[transaction]

    def get_acquired_lot_number_of_fractions(self, transaction: InTransaction) -> int:
        InTransaction.type_check("transaction", transaction)
        if transaction not in self.__acquired_lots_to_number_of_fractions:
            raise RP2ValueError(f"Unknown transaction:\n{transaction}")
        self._check_sort()
        return self.__acquired_lots_to_number_of_fractions[transaction]

    def _validate_entry(self, entry: AbstractEntry) -> None:
        GainLoss.type_check("entry", entry)
        super()._validate_entry(entry)

    def _sort_entries(self) -> None:  # pylint: disable=too-many-branches
        LOGGER.debug("Sort Gain-Loss Set:")
        super()._sort_entries()
        entry: AbstractEntry
        gain_loss: Optional[GainLoss] = None
        # Taxable events are always monotonic over time (sorted by ascending date), so we just need scalars to keep
        # track of amount and fraction (see also acquired-lot comment below). On the other hand acquired lots are not always
        # monotonic over time (they can be in any order, depending on the accounting method), so we need dictionaries
        # to keep track of amount and fraction for each lot.
        current_taxable_event_amount: RP2Decimal = ZERO
        current_taxable_event_fraction: int = 0
        current_acquired_lot_amount: Dict[InTransaction, RP2Decimal] = {}
        current_acquired_lot_fraction: Dict[InTransaction, int] = {}

        last_gain_loss_with_acquired_lot: Optional[GainLoss] = None

        # Reset fields that are recomputed at sort time
        self.__taxable_events_to_fraction = {}
        self.__taxable_events_to_number_of_fractions = {}
        self.__acquired_lots_to_fraction = {}
        self.__acquired_lots_to_number_of_fractions = {}
        self.__transaction_type_2_count = {transaction_type: 0 for transaction_type in TransactionType}

        for entry in self._entry_list:
            gain_loss = cast(GainLoss, entry)

            # We're not using the iterator to avoid infinite recursion (we're looping over
            # _entry_list directly), so we need to check time filters manually: stop after
            # to_date so that number of fractions is not affected by lots outside the time filter
            if gain_loss.timestamp.date() > self.to_date:
                break

            count: int = self.__transaction_type_2_count[gain_loss.taxable_event.transaction_type]
            self.__transaction_type_2_count[gain_loss.taxable_event.transaction_type] = count + 1

            if gain_loss.acquired_lot:
                # Ensure acquired_lot timestamp and its ancestor's validate against accounting method rules.
                if (
                    last_gain_loss_with_acquired_lot
                    and last_gain_loss_with_acquired_lot.acquired_lot
                    and not self.__accounting_method.validate_acquired_lot_ancestor_timestamp(
                        gain_loss.acquired_lot, last_gain_loss_with_acquired_lot.acquired_lot
                    )
                ):
                    raise RP2ValueError(
                        f"Timestamp {gain_loss.acquired_lot.timestamp} of acquired_lot entry (id {gain_loss.acquired_lot.internal_id}) "
                        f"is incompatible with timestamp {last_gain_loss_with_acquired_lot.acquired_lot.timestamp} of its ancestor "
                        f"(id {last_gain_loss_with_acquired_lot.acquired_lot.internal_id}) using {self.__accounting_method} accounting method: {gain_loss}"
                    )
                last_gain_loss_with_acquired_lot = gain_loss

            current_taxable_event_amount += gain_loss.crypto_amount
            self.__taxable_events_to_fraction[gain_loss] = current_taxable_event_fraction
            if current_taxable_event_amount == gain_loss.taxable_event.crypto_balance_change:
                # Expected amount reached: reset both fraction and amount
                if gain_loss.taxable_event in self.__taxable_events_to_number_of_fractions:
                    raise RP2ValueError(f"Taxable event crypto amount already exhausted for {gain_loss.taxable_event}")
                self.__taxable_events_to_number_of_fractions[gain_loss.taxable_event] = current_taxable_event_fraction + 1
                LOGGER.debug(
                    "%s (%d - %d): current amount == taxable event (%.16f)",
                    gain_loss.internal_id,
                    current_acquired_lot_fraction[gain_loss.acquired_lot] if gain_loss.acquired_lot in current_acquired_lot_fraction else 0,
                    current_taxable_event_fraction,
                    current_taxable_event_amount,
                )
                current_taxable_event_fraction = 0
                current_taxable_event_amount = ZERO
            elif current_taxable_event_amount < gain_loss.taxable_event.crypto_balance_change:
                LOGGER.debug(
                    "%s (%d - %d): current amount < taxable event (%.16f < %.16f)",
                    gain_loss.internal_id,
                    current_acquired_lot_fraction[gain_loss.acquired_lot] if gain_loss.acquired_lot in current_acquired_lot_fraction else 0,
                    current_taxable_event_fraction,
                    current_taxable_event_amount,
                    gain_loss.taxable_event.crypto_balance_change,
                )
                current_taxable_event_fraction += 1
            else:
                raise RP2ValueError(
                    f"Current taxable event amount ({current_taxable_event_amount})"
                    f" exceeded crypto balance change of taxable event ({gain_loss.taxable_event.crypto_balance_change})"
                    f". {gain_loss}"
                )

            if gain_loss.acquired_lot:
                current_acquired_lot_amount[gain_loss.acquired_lot] = (
                    current_acquired_lot_amount.setdefault(gain_loss.acquired_lot, ZERO) + gain_loss.crypto_amount
                )
                self.__acquired_lots_to_fraction[gain_loss] = current_acquired_lot_fraction.setdefault(gain_loss.acquired_lot, 0)
                if current_acquired_lot_amount[gain_loss.acquired_lot] == gain_loss.acquired_lot.crypto_balance_change:
                    # Expected amount reached: delete both fraction and amount from "current" dictionaries
                    if gain_loss.acquired_lot in self.__acquired_lots_to_number_of_fractions:
                        raise RP2ValueError(f"Acquired lot crypto amount already exhausted for {gain_loss.acquired_lot}")
                    self.__acquired_lots_to_number_of_fractions[gain_loss.acquired_lot] = current_acquired_lot_fraction[gain_loss.acquired_lot] + 1
                    LOGGER.debug(
                        "%s (%d - %d): current amount == acquired lot amount (%.16f)",
                        gain_loss.internal_id,
                        current_acquired_lot_fraction[gain_loss.acquired_lot],
                        current_taxable_event_fraction,
                        current_acquired_lot_amount[gain_loss.acquired_lot],
                    )
                    del current_acquired_lot_amount[gain_loss.acquired_lot]
                    del current_acquired_lot_fraction[gain_loss.acquired_lot]
                elif current_acquired_lot_amount[gain_loss.acquired_lot] < gain_loss.acquired_lot.crypto_balance_change:
                    LOGGER.debug(
                        "%s (%d - %d): current amount < acquired lot amount (%.16f < %.16f)",
                        gain_loss.internal_id,
                        current_acquired_lot_fraction[gain_loss.acquired_lot],
                        current_taxable_event_fraction,
                        current_acquired_lot_amount[gain_loss.acquired_lot],
                        gain_loss.acquired_lot.crypto_balance_change,
                    )
                    current_acquired_lot_fraction[gain_loss.acquired_lot] = current_acquired_lot_fraction[gain_loss.acquired_lot] + 1
                else:
                    raise RP2ValueError(
                        f"Current acquired lot amount ({current_acquired_lot_amount[gain_loss.acquired_lot]}) "
                        f"exceeded crypto balance change of acquired lot ({gain_loss.acquired_lot.crypto_balance_change})"
                        f". {gain_loss}"
                    )

        # Final housekeeping

        # Taxable event: update fractions for last non-exhausted transaction (if any)
        if last_gain_loss_with_acquired_lot:
            if current_taxable_event_amount > ZERO:
                if last_gain_loss_with_acquired_lot.taxable_event in self.__taxable_events_to_number_of_fractions:
                    raise RP2ValueError(f"Taxable event crypto amount already exhausted for {last_gain_loss_with_acquired_lot.taxable_event}")
                self.__taxable_events_to_number_of_fractions[last_gain_loss_with_acquired_lot.taxable_event] = current_taxable_event_fraction
                LOGGER.debug(
                    "%s (%d - %d): taxable event housekeeping",
                    last_gain_loss_with_acquired_lot.internal_id,
                    current_acquired_lot_fraction[last_gain_loss_with_acquired_lot.acquired_lot]
                    if last_gain_loss_with_acquired_lot.acquired_lot in current_acquired_lot_fraction
                    else 0,
                    current_taxable_event_fraction,
                )

        # Acquired lot: update fractions for non-exhausted transactions (if any)
        for acquired_lot, fraction in current_acquired_lot_fraction.items():
            if acquired_lot:
                if acquired_lot in self.__acquired_lots_to_number_of_fractions:
                    raise RP2ValueError(f"Acquired lot crypto amount already exhausted for {acquired_lot}")
                self.__acquired_lots_to_number_of_fractions[acquired_lot] = fraction
                LOGGER.debug(
                    "%s (%d): acquired_lot housekeeping",
                    acquired_lot.internal_id,
                    current_acquired_lot_fraction[acquired_lot],
                )

    def __str__(self) -> str:
        output: List[str] = []
        output.append(f"{type(self).__name__}:")
        output.append(f"  configuration={self.configuration.configuration_path}")
        output.append(f"  asset={self.asset}")
        output.append(f"  from_date={str(self.from_date) if self.from_date > MIN_DATE else 'non-specified'}")
        output.append(f"  to_date={str(self.to_date) if self.to_date < MAX_DATE else 'non-specified'}")
        output.append("  entries=")
        for entry in self:
            parent: Optional[AbstractEntry]
            gain_loss: GainLoss = cast(GainLoss, entry)
            output.append(entry.to_string(indent=2, repr_format=False))
            parent = self.get_parent(entry)
            output.append(
                f"      taxable_event_fraction={self.get_taxable_event_fraction(gain_loss) + 1} of "
                f"{self.get_taxable_event_number_of_fractions(gain_loss.taxable_event)}"
            )
            if gain_loss.acquired_lot:
                output.append(
                    f"      acquired_lot_fraction={self.get_acquired_lot_fraction(gain_loss) + 1} of "
                    f"{self.get_acquired_lot_number_of_fractions(gain_loss.acquired_lot)}"
                )
            output.append(f"      parent={parent.internal_id if parent else None}")
        return "\n".join(output)

    def __repr__(self) -> str:
        output: List[str] = []
        output.append(f"{type(self).__name__}(")
        output.append(f"configuration={repr(self.configuration.configuration_path)}")
        output.append(f", asset={repr(self.asset)}")
        output.append(f", from_date={repr(self.from_date) if self.from_date > MIN_DATE else 'non-specified'}")
        output.append(f", to_date={repr(self.to_date) if self.to_date < MAX_DATE else 'non-specified'}")
        output.append(", entries=[")
        count: int = 0
        for entry in self:
            parent: Optional[AbstractEntry]
            gain_loss: GainLoss = cast(GainLoss, entry)
            if count > 0:
                output.append(", ")
            entry_string = repr(entry)
            # Remove trailing ')' to add set-specific information like parent
            if entry_string[-1] != ")":
                raise Exception("Internal error: repr() of transaction doesn't end with ')'")
            output.append(entry_string[:-1])
            parent = self.get_parent(entry)
            output.append(
                f", taxable_event_fraction={self.get_taxable_event_fraction(gain_loss) + 1} of "
                f"{self.get_taxable_event_number_of_fractions(gain_loss.taxable_event)}"
            )
            if gain_loss.acquired_lot:
                output.append(
                    f", acquired_lot_fraction={self.get_acquired_lot_fraction(gain_loss) + 1} of "
                    f"{self.get_acquired_lot_number_of_fractions(gain_loss.acquired_lot)}"
                )
            output.append(f", parent={parent.internal_id if parent else None}")
            # Add back trailing ')'
            output.append(")")
            count += 1
        output.append("]")
        return "".join(output)

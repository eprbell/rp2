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

from typing import Dict, List, Optional, cast

from rp2.abstract_entry import AbstractEntry
from rp2.abstract_entry_set import AbstractEntrySet
from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import MAX_YEAR, Configuration
from rp2.entry_types import TransactionType
from rp2.gain_loss import GainLoss
from rp2.in_transaction import InTransaction
from rp2.logger import LOGGER
from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError


class GainLossSet(AbstractEntrySet):
    def __init__(
        self,
        configuration: Configuration,
        asset: str,
        from_year: int = 0,
        to_year: int = MAX_YEAR,
    ) -> None:
        super().__init__(configuration, "MIXED", asset, from_year, to_year)
        self.__taxable_events_to_fraction: Dict[GainLoss, int] = {}
        self.__from_lots_to_fraction: Dict[GainLoss, int] = {}
        self.__taxable_events_to_number_of_fractions: Dict[AbstractTransaction, int] = {}
        self.__from_lots_to_number_of_fractions: Dict[InTransaction, int] = {}
        self.__transaction_type_2_count: Dict[TransactionType, int] = {transaction_type: 0 for transaction_type in TransactionType}

    @classmethod
    def type_check(cls, name: str, instance: "GainLossSet") -> "GainLossSet":
        Configuration.type_check_parameter_name(name)
        if not isinstance(instance, cls):
            raise RP2TypeError(f"Parameter '{name}' is not of type {cls.__name__}: {instance}")
        return instance

    def add_entry(self, entry: AbstractEntry) -> None:
        gain_loss: GainLoss = GainLoss.type_check("entry", entry)

        if entry.timestamp.year > self.to_year:
            return

        super().add_entry(entry)
        count: int = self.__transaction_type_2_count[gain_loss.taxable_event.transaction_type]
        self.__transaction_type_2_count[gain_loss.taxable_event.transaction_type] = count + 1

    def get_transaction_type_count(self, transaction_type: TransactionType) -> int:
        return self.__transaction_type_2_count[transaction_type]

    def get_taxable_event_fraction(self, entry: GainLoss) -> int:
        self._validate_entry(entry)
        self._check_sort()
        return self.__taxable_events_to_fraction[entry]

    def get_from_lot_fraction(self, entry: GainLoss) -> int:
        self._validate_entry(entry)
        self._check_sort()
        return self.__from_lots_to_fraction[entry]

    def get_taxable_event_number_of_fractions(self, transaction: AbstractTransaction) -> int:
        AbstractTransaction.type_check("transaction", transaction)
        if transaction not in self.__taxable_events_to_number_of_fractions:
            raise RP2ValueError(f"Unknown transaction:\n{transaction}")
        self._check_sort()
        return self.__taxable_events_to_number_of_fractions[transaction]

    def get_from_lot_number_of_fractions(self, transaction: InTransaction) -> int:
        InTransaction.type_check("transaction", transaction)
        if transaction not in self.__from_lots_to_number_of_fractions:
            raise RP2ValueError(f"Unknown transaction:\n{transaction}")
        self._check_sort()
        return self.__from_lots_to_number_of_fractions[transaction]

    def _validate_entry(self, entry: AbstractEntry) -> None:
        GainLoss.type_check("entry", entry)
        super()._validate_entry(entry)

    def _sort_entries(self) -> None:  # pylint: disable=too-many-branches
        LOGGER.debug("Sort Gain-Loss Set:")
        super()._sort_entries()
        entry: AbstractEntry
        gain_loss: Optional[GainLoss] = None
        current_taxable_event_amount: RP2Decimal = ZERO
        current_from_lot_amount: RP2Decimal = ZERO
        current_taxable_event_fraction: int = 0
        current_from_lot_fraction: int = 0
        last_gain_loss_with_from_lot: Optional[GainLoss] = None
        for entry in self._entry_list:
            gain_loss = cast(GainLoss, entry)
            # Access the parent directly via _entry_to_parent because using the get_parent()
            # accessor would cause _sort_entries to be called in an infinite recursive loop
            if gain_loss.from_lot:
                if (
                    last_gain_loss_with_from_lot
                    and last_gain_loss_with_from_lot.from_lot
                    and gain_loss.from_lot.timestamp < last_gain_loss_with_from_lot.from_lot.timestamp
                ):
                    # Ensure timestamp of from lot is >= timestamp of its ancestor.
                    raise RP2ValueError(
                        f"Date of from_lot entry (id {gain_loss.from_lot.unique_id}) is < the date of its ancestor "
                        f"(id {last_gain_loss_with_from_lot.from_lot.unique_id}): {gain_loss}"
                    )
                last_gain_loss_with_from_lot = gain_loss

            current_taxable_event_amount += gain_loss.crypto_amount
            self.__taxable_events_to_fraction[gain_loss] = current_taxable_event_fraction
            if current_taxable_event_amount == gain_loss.taxable_event.crypto_balance_change:
                # Expected amount reached: reset both fraction and amount
                if gain_loss.taxable_event in self.__taxable_events_to_number_of_fractions:
                    raise RP2ValueError(f"Taxable event crypto amount already exhausted for {gain_loss.taxable_event}")
                self.__taxable_events_to_number_of_fractions[gain_loss.taxable_event] = current_taxable_event_fraction + 1
                LOGGER.debug(
                    "%s (%d - %d): current amount == taxable event (%.16f)",
                    gain_loss.unique_id,
                    current_from_lot_fraction,
                    current_taxable_event_fraction,
                    current_taxable_event_amount,
                )
                current_taxable_event_fraction = 0
                current_taxable_event_amount = ZERO
            elif current_taxable_event_amount < gain_loss.taxable_event.crypto_balance_change:
                LOGGER.debug(
                    "%s (%d - %d): current amount < taxable event (%.16f < %.16f)",
                    gain_loss.unique_id,
                    current_from_lot_fraction,
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

            if gain_loss.from_lot:
                current_from_lot_amount += gain_loss.crypto_amount
                self.__from_lots_to_fraction[gain_loss] = current_from_lot_fraction
                if current_from_lot_amount == gain_loss.from_lot.crypto_balance_change:
                    # Expected amount reached: reset both fraction and amount
                    if gain_loss.from_lot in self.__from_lots_to_number_of_fractions:
                        raise RP2ValueError(f"From-lot crypto amount already exhausted for {gain_loss.from_lot}")
                    self.__from_lots_to_number_of_fractions[gain_loss.from_lot] = current_from_lot_fraction + 1
                    LOGGER.debug(
                        "%s (%d - %d): current amount == from-lot (%.16f)",
                        gain_loss.unique_id,
                        current_from_lot_fraction,
                        current_taxable_event_fraction,
                        current_from_lot_amount,
                    )
                    current_from_lot_fraction = 0
                    current_from_lot_amount = ZERO
                elif current_from_lot_amount < gain_loss.from_lot.crypto_balance_change:
                    LOGGER.debug(
                        "%s (%d - %d): current amount < from-lot (%.16f < %.16f)",
                        gain_loss.unique_id,
                        current_from_lot_fraction,
                        current_taxable_event_fraction,
                        current_from_lot_amount,
                        gain_loss.from_lot.crypto_balance_change,
                    )
                    current_from_lot_fraction += 1
                else:
                    raise RP2ValueError(
                        f"Current from-lot amount ({current_from_lot_amount}) "
                        f"exceeded crypto balance change of from-lot ({gain_loss.from_lot.crypto_balance_change})"
                        f". {gain_loss}"
                    )

        # Final housekeeping
        if last_gain_loss_with_from_lot:
            # Update fractions for last transaction that is not exhausted (if any)
            if current_taxable_event_amount > ZERO:
                if last_gain_loss_with_from_lot.taxable_event in self.__taxable_events_to_number_of_fractions:
                    raise RP2ValueError(f"Taxable event crypto amount already exhausted for {last_gain_loss_with_from_lot.taxable_event}")
                self.__taxable_events_to_number_of_fractions[last_gain_loss_with_from_lot.taxable_event] = current_taxable_event_fraction
                LOGGER.debug(
                    "%s (%d - %d): taxable event housekeeping",
                    last_gain_loss_with_from_lot.unique_id,
                    current_from_lot_fraction,
                    current_taxable_event_fraction,
                )

            if last_gain_loss_with_from_lot.from_lot and current_from_lot_amount > ZERO:
                if last_gain_loss_with_from_lot.from_lot in self.__from_lots_to_number_of_fractions:
                    raise RP2ValueError(f"From-lot crypto amount already exhausted for {last_gain_loss_with_from_lot.from_lot}")
                self.__from_lots_to_number_of_fractions[last_gain_loss_with_from_lot.from_lot] = current_from_lot_fraction
                LOGGER.debug(
                    "%s (%d - %d): from_lot housekeeping",
                    last_gain_loss_with_from_lot.unique_id,
                    current_from_lot_fraction,
                    current_taxable_event_fraction,
                )

    def __str__(self) -> str:
        output: List[str] = []
        output.append(f"{type(self).__name__}:")
        output.append(f"  configuration={self.configuration.configuration_path}")
        output.append(f"  asset={self.asset}")
        output.append(f"  from_year={str(self.from_year) if self.from_year > 0 else 'non-specified'}")
        output.append(f"  to_year={str(self.to_year) if self.to_year < MAX_YEAR else 'non-specified'}")
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
            if gain_loss.from_lot:
                output.append(
                    f"      from_lot_fraction={self.get_from_lot_fraction(gain_loss) + 1} of " f"{self.get_from_lot_number_of_fractions(gain_loss.from_lot)}"
                )
            output.append(f"      parent={parent.unique_id if parent else None}")
        return "\n".join(output)

    def __repr__(self) -> str:
        output: List[str] = []
        output.append(f"{type(self).__name__}(")
        output.append(f"configuration={repr(self.configuration.configuration_path)}")
        output.append(f", asset={repr(self.asset)}")
        output.append(f", from_year={repr(self.from_year) if self.from_year > 0 else 'non-specified'}")
        output.append(f", to_year={repr(self.to_year) if self.to_year < MAX_YEAR else 'non-specified'}")
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
            if gain_loss.from_lot:
                output.append(
                    f", from_lot_fraction={self.get_from_lot_fraction(gain_loss) + 1} of " f"{self.get_from_lot_number_of_fractions(gain_loss.from_lot)}"
                )
            output.append(f", parent={parent.unique_id if parent else None}")
            # Add back trailing ')'
            output.append(")")
            count += 1
        output.append("]")
        return "".join(output)

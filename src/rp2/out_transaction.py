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

from typing import Callable, List, Optional

from rp2.abstract_transaction import AbstractTransaction
from rp2.configuration import Configuration
from rp2.entry_types import TransactionType
from rp2.logger import LOGGER
from rp2.rp2_decimal import FIAT_DECIMAL_MASK, ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError, RP2ValueError

# pylint: disable=too-many-branches
class OutTransaction(AbstractTransaction):
    def __init__(
        self,
        configuration: Configuration,
        timestamp: str,
        asset: str,
        exchange: str,
        holder: str,
        transaction_type: str,
        spot_price: RP2Decimal,
        crypto_out_no_fee: RP2Decimal,
        crypto_fee: RP2Decimal,
        crypto_out_with_fee: Optional[RP2Decimal] = None,
        fiat_out_no_fee: Optional[RP2Decimal] = None,
        fiat_fee: Optional[RP2Decimal] = None,
        internal_id: Optional[int] = None,
        unique_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        super().__init__(configuration, timestamp, asset, transaction_type, spot_price, internal_id, unique_id, notes)

        self.__exchange: str = configuration.type_check_exchange("exchange", exchange)
        self.__holder: str = configuration.type_check_holder("holder", holder)
        self.__crypto_out_no_fee: RP2Decimal
        self.__crypto_fee: RP2Decimal
        self.__fiat_out_with_fee: RP2Decimal
        self.__fiat_out_no_fee: RP2Decimal

        if self.transaction_type == TransactionType.FEE:
            self.__crypto_out_no_fee = configuration.type_check_positive_decimal("crypto_out_no_fee", crypto_out_no_fee)
            if self.__crypto_out_no_fee != ZERO:
                raise RP2ValueError(
                    f"{self.asset} {type(self).__name__} ({self.timestamp}, id {self.internal_id}): fee-typed transaction has non-zero 'crypto_out_no_fee'"
                )
            self.__crypto_fee = configuration.type_check_positive_decimal("crypto_fee", crypto_fee, non_zero=True)
        else:
            if spot_price == ZERO:
                raise RP2ValueError(f"{self.asset} {type(self).__name__} ({self.timestamp}, id {self.internal_id}): parameter 'spot_price' cannot be 0")
            self.__crypto_out_no_fee = configuration.type_check_positive_decimal("crypto_out_no_fee", crypto_out_no_fee, non_zero=True)
            self.__crypto_fee = configuration.type_check_positive_decimal("crypto_fee", crypto_fee)

        # Crypto out with fee is optional. It can be derived from crypto out (no fee) and crypto fee, however some exchanges
        # provide it anyway. If it is provided use it as given by the exchange, if not compute it.
        if crypto_out_with_fee is None:
            self.__crypto_out_with_fee = self.__crypto_out_no_fee + self.crypto_fee
        else:
            self.__crypto_out_with_fee = configuration.type_check_positive_decimal("crypto_out_with_fee", crypto_out_with_fee, non_zero=True)

        # Fiat out without fee and fiat fee are optional. They can be derived from crypto out (no fee), spot price and crypto fee,
        # however some exchanges provide them anyway. If they are provided use them as given by the exchange, if not compute them.
        if fiat_out_no_fee is None:
            self.__fiat_out_no_fee = self.__crypto_out_no_fee * self.spot_price
        else:
            self.__fiat_out_no_fee = configuration.type_check_positive_decimal("fiat_out_no_fee", fiat_out_no_fee, non_zero=True)
        if fiat_fee is None:
            self.__fiat_fee = self.__crypto_fee * self.spot_price
        else:
            self.__fiat_fee = configuration.type_check_positive_decimal("fiat_fee", fiat_fee)
        self.__fiat_out_with_fee = self.__fiat_out_no_fee + self.__fiat_fee

        if self.transaction_type not in (TransactionType.DONATE, TransactionType.FEE, TransactionType.GIFT, TransactionType.SELL):
            raise RP2ValueError(
                f"{self.asset} {type(self).__name__} ({self.timestamp}, id {self.internal_id}): invalid transaction type {self.transaction_type}"
            )

        # If the values provided by the exchange doesn't match the computed one, log a warning.
        if not RP2Decimal.is_equal_within_precision(self.__crypto_out_with_fee, self.__crypto_out_no_fee + self.__crypto_fee, FIAT_DECIMAL_MASK):
            LOGGER.warning(
                "%s %s (%s, id %s): crypto_out_with_fee != crypto_out_no_fee + crypto_fee: %f != %f",
                self.asset,
                type(self).__name__,
                self.timestamp,
                self.internal_id,
                self.__crypto_out_with_fee,
                self.__crypto_out_no_fee + self.__crypto_fee,
            )

        if not RP2Decimal.is_equal_within_precision(self.__crypto_fee * self.spot_price, self.__fiat_fee, FIAT_DECIMAL_MASK):
            LOGGER.warning(
                "%s %s (%s, id %s): crypto_fee * spot_price != fiat_fee: %f != %f",
                self.asset,
                type(self).__name__,
                self.timestamp,
                self.internal_id,
                self.__crypto_fee * self.spot_price,
                self.__fiat_fee,
            )

        if not RP2Decimal.is_equal_within_precision(self.__crypto_out_no_fee * self.spot_price, self.__fiat_out_no_fee, FIAT_DECIMAL_MASK):
            LOGGER.warning(
                "%s %s (%s, id %s): crypto_out_no_fee * spot_price != fiat_out_no_fee: %f != %f",
                self.asset,
                type(self).__name__,
                self.timestamp,
                self.internal_id,
                self.__crypto_out_no_fee * self.spot_price,
                self.__fiat_out_no_fee,
            )

    def to_string(self, indent: int = 0, repr_format: bool = True, extra_data: Optional[List[str]] = None) -> str:
        self.configuration.type_check_positive_int("indent", indent)
        self.configuration.type_check_bool("repr_format", repr_format)
        if extra_data and not isinstance(extra_data, List):
            raise RP2TypeError(f"Parameter 'extra_data' is not of type List: {extra_data}")

        class_specific_data: List[str] = []
        stringify: Callable[[object], str] = repr
        if not repr_format:
            stringify = str
        class_specific_data = [
            f"exchange={stringify(self.exchange)}",
            f"holder={stringify(self.holder)}",
            f"transaction_type={stringify(self.transaction_type)}",
            f"spot_price={self.spot_price:.4f}",
            f"crypto_out_no_fee={self.crypto_out_no_fee:.8f}",
            f"crypto_fee={self.crypto_fee:.8f}",
            f"unique_id={self.unique_id}",
            f"is_taxable={stringify(self.is_taxable())}",
            f"fiat_taxable_amount={self.fiat_taxable_amount:.4f}",
        ]
        if extra_data:
            class_specific_data.extend(extra_data)

        return super().to_string(indent=indent, repr_format=repr_format, extra_data=class_specific_data)

    @property
    def exchange(self) -> str:
        return self.__exchange

    @property
    def holder(self) -> str:
        return self.__holder

    @property
    def crypto_out_no_fee(self) -> RP2Decimal:
        return self.__crypto_out_no_fee

    @property
    def crypto_out_with_fee(self) -> RP2Decimal:
        return self.__crypto_out_with_fee

    @property
    def crypto_fee(self) -> RP2Decimal:
        return self.__crypto_fee

    @property
    def fiat_out_no_fee(self) -> RP2Decimal:
        return self.__fiat_out_no_fee

    @property
    def fiat_out_with_fee(self) -> RP2Decimal:
        return self.__fiat_out_with_fee

    @property
    def fiat_fee(self) -> RP2Decimal:
        return self.__fiat_fee

    # IRS Publication 544 (https://www.irs.gov/publications/p544) explains that sale expenses are deducted from the sale price
    # (see "Example 1" in the "Gain or Loss From Sales and Exchanges" section). A less formal explanation:
    # https://taxbit.com/cryptocurrency-tax-guide. Therefore the fee is considered a deduction and the outgoing amount is not.
    @property
    def crypto_taxable_amount(self) -> RP2Decimal:
        if self.transaction_type == TransactionType.FEE:
            return self.crypto_fee
        return self.crypto_out_no_fee

    @property
    def fiat_taxable_amount(self) -> RP2Decimal:
        if self.transaction_type == TransactionType.FEE:
            return self.fiat_fee
        return self.fiat_out_no_fee

    @property
    def crypto_deduction(self) -> RP2Decimal:
        return self.crypto_fee

    @property
    def fiat_deduction(self) -> RP2Decimal:
        return self.fiat_fee

    @property
    def crypto_balance_change(self) -> RP2Decimal:
        return self.crypto_out_with_fee

    @property
    def fiat_balance_change(self) -> RP2Decimal:
        return self.fiat_out_with_fee

    def is_taxable(self) -> bool:
        return True

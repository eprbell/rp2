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

from decimal import Decimal, FloatOperation, getcontext

from rp2.rp2_error import RP2TypeError

CRYPTO_DECIMALS: int = 13
CRYPTO_DECIMAL_MASK: Decimal = Decimal("1." + "0" * int(CRYPTO_DECIMALS))

FIAT_DECIMALS: int = 2
FIAT_DECIMAL_MASK: Decimal = Decimal("1." + "0" * int(FIAT_DECIMALS))


class RP2Decimal(Decimal):

    # RP2Decimal initialization code. In Python there is no static constructor: the closest alternative is to add static initialization code
    # directly inside the class. Use arbitrarily high precision (quintillion + CRYPTO_DECIMALS digits)
    getcontext().prec = CRYPTO_DECIMALS + 18
    getcontext().traps[FloatOperation] = True

    @classmethod
    def is_equal_within_precision(cls, first: "RP2Decimal", second: "RP2Decimal", precision_mask: Decimal) -> bool:
        return (first - second).quantize(precision_mask) == ZERO

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return (self - other).quantize(CRYPTO_DECIMAL_MASK).__eq__(ZERO)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return (self - other).quantize(CRYPTO_DECIMAL_MASK).__ge__(ZERO)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return (self - other).quantize(CRYPTO_DECIMAL_MASK).__gt__(ZERO)

    def __le__(self, other: object) -> bool:
        return not self.__gt__(other)

    def __lt__(self, other: object) -> bool:
        return not self.__ge__(other)

    def __add__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__add__(self, other))

    def __sub__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__sub__(self, other))

    def __mul__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__mul__(self, other))

    def __truediv__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__truediv__(self, other))

    def __floordiv__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__floordiv__(self, other))

    def __pow__(self, other: object, modulo: object = None) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        if modulo is not None and not isinstance(modulo, Decimal):
            raise RP2TypeError(f"Modulo has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__pow__(self, other, modulo))

    def __mod__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__mod__(self, other))

    # Reflected operand overrides
    def __radd__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__radd__(self, other))

    def __rsub__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__rsub__(self, other))

    def __rmul__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__rmul__(self, other))

    def __rtruediv__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__rtruediv__(self, other))

    def __rfloordiv__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__rfloordiv__(self, other))

    def __rmod__(self, other: object) -> "RP2Decimal":
        if not isinstance(other, Decimal):
            raise RP2TypeError(f"Operand has non-Decimal value {repr(other)}")
        return RP2Decimal(Decimal.__rmod__(self, other))


ZERO: RP2Decimal = RP2Decimal("0")

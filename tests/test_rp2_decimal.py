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

import unittest

from rp2.rp2_decimal import ZERO, RP2Decimal
from rp2.rp2_error import RP2TypeError


class TestRP2Decimal(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_rp2_decimal(self) -> None:
        decimal1: RP2Decimal = RP2Decimal("0.2")
        decimal2: RP2Decimal = RP2Decimal("0.2")
        decimal3: RP2Decimal = RP2Decimal("0.20000000000001")
        decimal4: RP2Decimal = RP2Decimal("0.2000000000001")

        decimal5: RP2Decimal = RP2Decimal("0.1")
        decimal6: RP2Decimal = RP2Decimal("0.1")
        decimal7: RP2Decimal = RP2Decimal("0.10000000000001")
        decimal8: RP2Decimal = RP2Decimal("0.1000000000001")

        zero_point_twelve = RP2Decimal("0.12")
        one: RP2Decimal = RP2Decimal("1")
        two: RP2Decimal = RP2Decimal("2")
        three: RP2Decimal = RP2Decimal("3")
        nine: RP2Decimal = RP2Decimal("9")

        self.assertTrue(decimal1 == decimal2)
        self.assertTrue(decimal1 == decimal3)
        self.assertFalse(decimal1 == decimal4)

        self.assertFalse(decimal1 != decimal2)
        self.assertFalse(decimal1 != decimal3)
        self.assertTrue(decimal1 != decimal4)

        self.assertFalse(decimal1 > decimal2)
        self.assertFalse(decimal1 > decimal3)
        self.assertFalse(decimal1 > decimal4)

        self.assertTrue(decimal1 >= decimal2)
        self.assertTrue(decimal1 >= decimal3)
        self.assertFalse(decimal1 >= decimal4)

        self.assertFalse(decimal1 < decimal2)
        self.assertFalse(decimal1 < decimal3)
        self.assertTrue(decimal1 < decimal4)

        self.assertTrue(decimal1 <= decimal2)
        self.assertTrue(decimal1 <= decimal3)
        self.assertTrue(decimal1 <= decimal4)

        # Check that overridden operators return RP2Decimal (these tests would fail without the custom precision built into RP2Decimal comparison operators)
        self.assertTrue(decimal5 + decimal6 == decimal1)
        self.assertTrue(decimal6 + decimal5 == decimal1)
        self.assertTrue(decimal5 + decimal7 == decimal1)
        self.assertTrue(decimal7 + decimal5 == decimal1)
        self.assertFalse(decimal5 + decimal8 == decimal1)
        self.assertFalse(decimal8 + decimal5 == decimal1)
        self.assertTrue(decimal5 + decimal7 == decimal5 + decimal6)
        self.assertFalse(decimal5 + decimal8 == decimal5 + decimal6)

        self.assertTrue(decimal1 - decimal2 == ZERO)
        self.assertTrue(decimal3 - decimal1 == ZERO)
        self.assertTrue(decimal4 - decimal1 > ZERO)

        self.assertTrue(decimal1 * three * decimal2 == zero_point_twelve)
        self.assertTrue(decimal1 * three * decimal3 == zero_point_twelve)
        self.assertTrue(decimal1 * three * decimal4 > zero_point_twelve)

        self.assertTrue(decimal2 / decimal1 == one)
        self.assertTrue(decimal3 / decimal1 == one)
        self.assertTrue(decimal4 / decimal1 > one)

        self.assertTrue(three // two == one)
        self.assertTrue((three // two) + decimal3 - decimal1 == one)
        self.assertTrue((three // two) + decimal4 - decimal1 > one)

        self.assertTrue(pow(three, two) == nine)
        self.assertTrue(pow(three, two) + decimal3 - decimal1 == nine)
        self.assertTrue(pow(three, two) + decimal4 - decimal1 > nine)

        self.assertTrue(nine % two == one)
        self.assertTrue(nine % two + decimal3 - decimal1 == one)
        self.assertTrue(nine % two + decimal4 - decimal1 > one)

    def test_bad_rp2_decimal(self) -> None:
        # pylint: disable=pointless-statement
        one: RP2Decimal = RP2Decimal("1")

        # Test comparison operators
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one == 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 == one
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one != -1.1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1.1 != one
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one > 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 > one
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one < 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 < one
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one >= 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 >= one
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one <= 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 <= one

        # Test arithmetic operators
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one + 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 + one
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one - 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 - one
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one * 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 * one
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one / 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 / one
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one // 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 // one

        # Test power
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one**1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            pow(one, 1)
        with self.assertRaisesRegex(RP2TypeError, "Modulo has non-Decimal value "):
            pow(one, one, 1)

        # Test modulo
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one % 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 % one


if __name__ == "__main__":
    unittest.main()

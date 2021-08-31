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

from decimal import Decimal

from rp2_decimal import ZERO, RP2Decimal, RP2TypeError


class TestRP2Decimal(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None

    def test_rp2_decimal(self) -> None:
        n1: RP2Decimal = RP2Decimal("0.2")
        n2: RP2Decimal = RP2Decimal("0.2")
        n3: RP2Decimal = RP2Decimal("0.20000000000001")
        n4: RP2Decimal = RP2Decimal("0.2000000000001")

        n11: RP2Decimal = RP2Decimal("0.1")
        n12: RP2Decimal = RP2Decimal("0.1")
        n13: RP2Decimal = RP2Decimal("0.10000000000001")
        n14: RP2Decimal = RP2Decimal("0.1000000000001")

        zero_point_twelve = RP2Decimal("0.12")
        one: RP2Decimal = RP2Decimal("1")
        two: RP2Decimal = RP2Decimal("2")
        three: RP2Decimal = RP2Decimal("3")
        nine: RP2Decimal = RP2Decimal("9")

        self.assertTrue(n1 == n2)
        self.assertTrue(n1 == n3)
        self.assertFalse(n1 == n4)

        self.assertFalse(n1 != n2)
        self.assertFalse(n1 != n3)
        self.assertTrue(n1 != n4)

        self.assertFalse(n1 > n2)
        self.assertFalse(n1 > n3)
        self.assertFalse(n1 > n4)

        self.assertTrue(n1 >= n2)
        self.assertTrue(n1 >= n3)
        self.assertFalse(n1 >= n4)

        self.assertFalse(n1 < n2)
        self.assertFalse(n1 < n3)
        self.assertTrue(n1 < n4)

        self.assertTrue(n1 <= n2)
        self.assertTrue(n1 <= n3)
        self.assertTrue(n1 <= n4)

        # Check that overridden operators return RP2Decimal (these tests would fail without the custom precision built into RP2Decimal comparison operators)
        self.assertTrue(n11 + n12 == n1)
        self.assertTrue(n12 + n11 == n1)
        self.assertTrue(n11 + n13 == n1)
        self.assertTrue(n13 + n11 == n1)
        self.assertFalse(n11 + n14 == n1)
        self.assertFalse(n14 + n11 == n1)
        self.assertTrue(n11 + n13 == n11 + n12)
        self.assertFalse(n11 + n14 == n11 + n12)

        self.assertTrue(n1 - n2 == ZERO)
        self.assertTrue(n3 - n1 == ZERO)
        self.assertTrue(n4 - n1 > ZERO)

        self.assertTrue(n1 * three * n2 == zero_point_twelve)
        self.assertTrue(n1 * three * n3 == zero_point_twelve)
        self.assertTrue(n1 * three * n4 > zero_point_twelve)

        self.assertTrue(n2 / n1 == one)
        self.assertTrue(n3 / n1 == one)
        self.assertTrue(n4 / n1 > one)

        self.assertTrue(three // two == one)
        self.assertTrue((three // two) + n3 - n1 == one)
        self.assertTrue((three // two) + n4 - n1 > one)

        self.assertTrue(pow(three, two) == nine)
        self.assertTrue(pow(three, two) + n3 - n1 == nine)
        self.assertTrue(pow(three, two) + n4 - n1 > nine)

        self.assertTrue(nine % two == one)
        self.assertTrue(nine % two + n3 - n1 == one)
        self.assertTrue(nine % two + n4 - n1 > one)

    def test_bad_rp2_decimal(self) -> None:
        # pylint: disable=pointless-statement
        # pylint: disable=misplaced-comparison-constant
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
            one ** 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 ** one
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            pow(one, 1)
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            pow(1, one)
        with self.assertRaisesRegex(RP2TypeError, "Modulo has non-Decimal value "):
            pow(one, one, 1)

        # Test modulo
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            one % 1
        with self.assertRaisesRegex(RP2TypeError, "Operand has non-Decimal value "):
            1 % one


if __name__ == "__main__":
    unittest.main()

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

import logging
import sys
import unittest
from typing import List, Optional

from rp2.avl_tree import AVLTree


class TestRP2Decimal(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_insert(self) -> None:
        values: List[int]
        expected_representation: str
        for values, expected_representation in [
            ([10], "AVLTree(root=AVLNode(key=10, value=10, height=1, left=None, right=None))"),
            ([10, 20], "AVLTree(root=AVLNode(key=10, value=10, height=2, left=None, right=AVLNode(key=20, value=20, height=1, left=None, right=None)))"),
            (
                [10, 20, 30],
                (
                    "AVLTree(root=AVLNode(key=20, value=20, height=2, left=AVLNode(key=10, value=10, height=1, left=None, right=None), right=AVLNode(key=30, "
                    "value=30, height=1, left=None, right=None)))"
                ),
            ),
            (
                [10, 30, 20],
                (
                    "AVLTree(root=AVLNode(key=20, value=20, height=2, left=AVLNode(key=10, value=10, height=1, left=None, right=None), right=AVLNode(key=30, "
                    "value=30, height=1, left=None, right=None)))"
                ),
            ),
            (
                [20, 10, 30],
                (
                    "AVLTree(root=AVLNode(key=20, value=20, height=2, left=AVLNode(key=10, value=10, height=1, left=None, right=None), right=AVLNode(key=30, "
                    "value=30, height=1, left=None, right=None)))"
                ),
            ),
            (
                [20, 30, 10],
                (
                    "AVLTree(root=AVLNode(key=20, value=20, height=2, left=AVLNode(key=10, value=10, height=1, left=None, right=None), right=AVLNode(key=30, "
                    "value=30, height=1, left=None, right=None)))"
                ),
            ),
            (
                [30, 10, 20],
                (
                    "AVLTree(root=AVLNode(key=20, value=20, height=2, left=AVLNode(key=10, value=10, height=1, left=None, right=None), right=AVLNode(key=30, "
                    "value=30, height=1, left=None, right=None)))"
                ),
            ),
            (
                [30, 20, 10],
                (
                    "AVLTree(root=AVLNode(key=20, value=20, height=2, left=AVLNode(key=10, value=10, height=1, left=None, right=None), right=AVLNode(key=30, "
                    "value=30, height=1, left=None, right=None)))"
                ),
            ),
            (
                [10, 20, 30, 40],
                (
                    "AVLTree(root=AVLNode(key=20, value=20, height=3, left=AVLNode(key=10, value=10, height=1, left=None, right=None), right=AVLNode(key=30, "
                    "value=30, height=2, left=None, right=AVLNode(key=40, value=40, height=1, left=None, right=None))))"
                ),
            ),
            (
                [40, 30, 20, 10],
                (
                    "AVLTree(root=AVLNode(key=30, value=30, height=3, left=AVLNode(key=20, value=20, height=2, left=AVLNode(key=10, value=10, height=1, "
                    "left=None, right=None), right=None), right=AVLNode(key=40, value=40, height=1, left=None, right=None)))"
                ),
            ),
            (
                [10, 20, 30, 40, 50, 60, 70],
                (
                    "AVLTree(root=AVLNode(key=40, value=40, height=3, left=AVLNode(key=20, value=20, height=2, left=AVLNode(key=10, value=10, height=1, "
                    "left=None, right=None), right=AVLNode(key=30, value=30, height=1, left=None, right=None)), right=AVLNode(key=60, value=60, height=2, "
                    "left=AVLNode(key=50, value=50, height=1, left=None, right=None), right=AVLNode(key=70, value=70, height=1, left=None, right=None))))"
                ),
            ),
            (
                [48, 13, 92, 99, 2, 12, 6, 57, 22],
                (
                    "AVLTree(root=AVLNode(key=48, value=48, height=4, left=AVLNode(key=12, value=12, height=3, left=AVLNode(key=2, value=2, height=2, "
                    "left=None, right=AVLNode(key=6, value=6, height=1, left=None, right=None)), right=AVLNode(key=13, value=13, height=2, left=None, "
                    "right=AVLNode(key=22, value=22, height=1, left=None, right=None))), right=AVLNode(key=92, value=92, height=2, left=AVLNode(key=57, "
                    "value=57, height=1, left=None, right=None), right=AVLNode(key=99, value=99, height=1, left=None, right=None))))"
                ),
            ),
        ]:
            self._populate_with_numbers(values, expected_representation)

    def _populate_with_numbers(self, values: List[int], expected_representation: Optional[str] = None) -> AVLTree[int, int]:
        tree: AVLTree[int, int] = AVLTree()
        value: int
        for value in values:
            tree.insert_node(value, value)
        if expected_representation:
            self.assertEqual(repr(tree), expected_representation, f"{repr(tree)} != {expected_representation}")
        return tree

    def test_avl_tree_find(self) -> None:
        tree: AVLTree[int, int] = AVLTree()
        values: List[int] = [48, 13, 92, 99, 2, 12, 6, 57, 22]
        for value in values:
            tree.insert_node(value, value)

        for threshold, expected_value in [
            (0, None),
            (1, None),
            (2, 2),
            (9, 6),
            (22, 22),
            (72, 57),
            (98, 92),
            (100, 99),
            (1000, 99),
        ]:
            self.assertEqual(tree.find_max_value_less_than(threshold), expected_value, f"result != {expected_value}")


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr)
    logging.getLogger("abc").setLevel(logging.DEBUG)
    unittest.main()

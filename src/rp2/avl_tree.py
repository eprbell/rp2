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
from typing import Generic, Optional, TypeVar

KeyType = TypeVar("KeyType", int, datetime, Decimal, float, str)  # pylint: disable=invalid-name
ValueType = TypeVar("ValueType")  # pylint: disable=invalid-name


class AVLNode(Generic[KeyType, ValueType]):
    def __init__(self, key: KeyType, value: ValueType):
        self.__key: KeyType = key
        self.__value: ValueType = value
        self.__height: int = 1

        self.__left: Optional[AVLNode[KeyType, ValueType]] = None
        self.__right: Optional[AVLNode[KeyType, ValueType]] = None

    def __repr__(self) -> str:
        return f"{self.to_string()}"

    def to_string(self) -> str:
        return (
            f"{type(self).__name__}(key={repr(self.key)}, "
            f"value={repr(self.value)}, height={repr(self.height)}, "
            f"left={self.left.to_string() if self.left else None}, "
            f"right={self.right.to_string() if self.right else None})"
        )

    @property
    def key(self) -> KeyType:
        return self.__key

    @property
    def value(self) -> ValueType:
        return self.__value

    @property
    def left(self) -> "Optional[AVLNode[KeyType, ValueType]]":
        return self.__left

    @left.setter
    def left(self, node: "Optional[AVLNode[KeyType, ValueType]]") -> None:
        self.__left = node

    @property
    def right(self) -> "Optional[AVLNode[KeyType, ValueType]]":
        return self.__right

    @right.setter
    def right(self, node: "Optional[AVLNode[KeyType, ValueType]]") -> None:
        self.__right = node

    @property
    def height(self) -> int:
        return self.__height

    @height.setter
    def height(self, height: int) -> None:
        self.__height = height


class AVLTree(Generic[KeyType, ValueType]):
    def __init__(self) -> None:
        self.__root: Optional[AVLNode[KeyType, ValueType]] = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(root={repr(self.__root)})"

    def find_max_value_less_than(self, key: KeyType) -> Optional[ValueType]:
        result: Optional[AVLNode[KeyType, ValueType]]
        result = self.find_max_node_less_than_at_node(self.__root, key) if self.__root else None
        return result.value if result is not None else None

    def insert_node(self, key: KeyType, value: ValueType) -> None:
        new_node: AVLNode[KeyType, ValueType]
        new_node = self.insert_node_at_node(self.__root, key, value)
        if self.__root != new_node:
            self.__root = new_node

    @staticmethod
    def find_max_node_less_than_at_node(root: AVLNode[KeyType, ValueType], key: KeyType) -> Optional[AVLNode[KeyType, ValueType]]:
        current_node: Optional[AVLNode[KeyType, ValueType]] = root
        result: Optional[AVLNode[KeyType, ValueType]] = None
        while current_node is not None:
            current_key: KeyType = current_node.key
            try:
                if current_key > key:
                    current_node = current_node.left
                elif current_key < key:
                    result = current_node
                    current_node = current_node.right
                elif current_key == key:
                    result = current_node
                    break
            except TypeError as exc:
                raise TypeError("AVLTree: keys are not comparable") from exc
        return result

    def insert_node_at_node(self, root: Optional[AVLNode[KeyType, ValueType]], key: KeyType, value: ValueType) -> AVLNode[KeyType, ValueType]:
        if not root:
            return AVLNode(key, value)

        if key < root.key:
            root.left = self.insert_node_at_node(root.left, key, value)
        else:
            root.right = self.insert_node_at_node(root.right, key, value)

        root.height = 1 + max(self._get_height(root.left), self._get_height(root.right))

        balance_factor: int = self._get_balance_factor(root)
        if balance_factor > 1:
            # Disable mypy on the next few lines: it complains about root.left possibly being None (and therefore not having
            # attribute "key"). However since balance_factor is > 1 root.left is guaranteed not to be None.
            if key < root.left.key:  # type: ignore
                return self._rotate_right(root)
            root.left = self._rotate_left(root.left)  # type: ignore
            return self._rotate_right(root)
        if balance_factor < -1:
            # Disable mypy on the next few lines: it complains about root.right possibly being None (and therefore not having
            # attribute "key"). However since balance_factor is < -1 root.right is guaranteed not to be None.
            if key > root.right.key:  # type: ignore
                return self._rotate_left(root)
            root.right = self._rotate_right(root.right)  # type: ignore
            return self._rotate_left(root)

        return root

    # Rotation implementation based on: https://en.wikipedia.org/wiki/Tree_rotation
    def _rotate_left(self, root: AVLNode[KeyType, ValueType]) -> AVLNode[KeyType, ValueType]:
        # Disable mypy on the next few lines: it complains that variables possibly being None (and therefore not having accessible
        # attributes). However unless there is a bug, this should never occur.
        pivot: Optional[AVLNode[KeyType, ValueType]] = root.right
        root.right = pivot.left  # type: ignore
        pivot.left = root  # type: ignore
        root.height = 1 + max(self._get_height(root.left), self._get_height(root.right))  # type: ignore
        pivot.height = 1 + max(self._get_height(pivot.left), self._get_height(pivot.right))  # type: ignore
        return pivot  # type: ignore

    def _rotate_right(self, root: AVLNode[KeyType, ValueType]) -> AVLNode[KeyType, ValueType]:
        # Disable mypy on the next few lines: it complains that variables possibly being None (and therefore not having accessible
        # attributes). However unless there is a bug, this should never occur.
        pivot: Optional[AVLNode[KeyType, ValueType]] = root.left
        root.left = pivot.right  # type: ignore
        pivot.right = root  # type: ignore
        root.height = 1 + max(self._get_height(root.left), self._get_height(root.right))  # type: ignore
        pivot.height = 1 + max(self._get_height(pivot.left), self._get_height(pivot.right))  # type: ignore
        return pivot  # type: ignore

    @staticmethod
    def _get_height(root: Optional[AVLNode[KeyType, ValueType]]) -> int:
        return root.height if root else 0

    def _get_balance_factor(self, root: AVLNode[KeyType, ValueType]) -> int:
        return self._get_height(root.left) - self._get_height(root.right) if root else 0

    @property
    def root(self) -> Optional[AVLNode[KeyType, ValueType]]:
        return self.__root

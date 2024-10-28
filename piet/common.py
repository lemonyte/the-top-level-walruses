from copy import deepcopy
from typing import Iterable, NamedTuple, TypeVar, overload

T = TypeVar("T")


class SelfExpandingList(list[T]):
    def __init__(self, iterable: Iterable[T] = (), /, *, default: T = None):
        self._default = deepcopy(default)
        super().__init__(iterable)

    @overload
    def __getitem__(self, index: int, /) -> T: ...

    @overload
    def __getitem__(self, index: slice, /) -> "SelfExpandingList[T]": ...

    def __getitem__(self, index: int | slice, /) -> T | "SelfExpandingList[T]":
        try:
            if isinstance(index, slice):
                items = []
                for i in range(index.start or 0, index.stop or len(self), index.step or 1):
                    try:
                        items.append(super().__getitem__(i))
                    except IndexError:
                        items.append(deepcopy(self._default))
                return self.__class__(items, default=deepcopy(self._default))
            if index < -1:
                raise IndexError("SelfExpandingList index out of range")
            return super().__getitem__(index)
        except IndexError:
            if isinstance(index, slice):
                i: int = index.stop
            else:
                i = index
            self.extend([deepcopy(self._default) for _ in range((i - len(self) + 1))])
            return self.__getitem__(index)

    @overload
    def __setitem__(self, index: int, value: T, /): ...

    @overload
    def __setitem__(self, index: slice, value: T | Iterable[T], /): ...

    def __setitem__(self, index, value, /):
        try:
            if isinstance(index, slice):
                indices = range(index.start or 0, index.stop or len(self), index.step or 1)
                for i in indices:
                    self.__setitem__(i, value)
            else:
                if index < -1:
                    raise IndexError("SelfExpandingList index out of range")
                super().__setitem__(index, value)
        except IndexError:
            if isinstance(index, slice):
                i = index.stop
            else:
                i = index
            self.extend([deepcopy(self._default) for _ in range((i - len(self) + 1))])
            self.__setitem__(index, value)


class OrderedPair(NamedTuple):
    y: int
    x: int

    def __add__(self, other: "OrderedPair | tuple[int, int]", /) -> "OrderedPair":
        return OrderedPair(self.y + other[0], self.x + other[1])

    def __sub__(self, other: "OrderedPair | tuple[int, int]", /) -> "OrderedPair":
        return OrderedPair(self.y - other[0], self.x - other[1])

    def __mul__(self, other: "OrderedPair | tuple[int, int]", /) -> "OrderedPair":
        return OrderedPair(self.y * other[0], self.x * other[1])

    def __floordiv__(self, other: "OrderedPair | tuple[int, int]", /) -> "OrderedPair":
        return OrderedPair(self.y // other[0], self.x // other[1])

    def __mod__(self, other: "OrderedPair | tuple[int, int]", /) -> "OrderedPair":
        return OrderedPair(self.y % other[0], self.x % other[1])

    def __pow__(self, other: "OrderedPair | tuple[int, int]", /) -> "OrderedPair":
        return OrderedPair(self.y ** other[0], self.x ** other[1])


class Color(NamedTuple):
    r: int
    g: int
    b: int

    def __eq__(self, other: "Color | tuple[int, int, int] | int", /) -> bool:
        if isinstance(other, (Color, tuple)):
            if len(other) != 3:
                return False
            return self.r == other[0] and self.g == other[1] and self.b == other[2]
        if isinstance(other, int):
            return int(self) == other
        return False

    def __int__(self) -> int:
        return (self.r << 0) + (self.g << 8) + (self.b << 16)


class ColorChange(NamedTuple):
    lightness: int
    hue: int


#         lightness hue
#              v     v
PIET_COLORS: tuple[tuple[Color, ...], ...] = (
    (
        Color(255, 192, 192),
        Color(255, 255, 192),
        Color(192, 255, 192),
        Color(192, 255, 255),
        Color(192, 192, 255),
        Color(255, 192, 255),
    ),
    (
        Color(255, 000, 000),
        Color(255, 255, 000),
        Color(000, 255, 000),
        Color(000, 255, 255),
        Color(000, 000, 255),
        Color(255, 000, 255),
    ),
    (
        Color(192, 000, 000),
        Color(192, 192, 000),
        Color(000, 192, 000),
        Color(000, 192, 192),
        Color(000, 000, 192),
        Color(192, 000, 192),
    ),
)
WHITE = Color(255, 255, 255)
BLACK = Color(0, 0, 0)

import math
import sys
import time
from typing import Callable, Iterable, NamedTuple

from PIL import Image

from .common import BLACK, PIET_COLORS, WHITE, Color, ColorChange, OrderedPair
from .reader import Codel, ImageReader
from .runtime import CodelChooserDirection, DirectionPointer, PietRuntime, PietStack, PointerDirection


class EndOfProgram(BaseException):
    pass


class StepLimitReached(EndOfProgram):
    pass


class StepTrace(NamedTuple):
    iteration: int
    position: OrderedPair
    instruction: Callable
    did_flip: bool
    last_codel: Codel
    current_codel: Codel

    def __repr__(self) -> str:
        return (
            f"StepTrace({self.iteration:0>4},"
            f" instruction={self.instruction.__name__},"
            f" position={self.position},"
            f" did_flip={self.did_flip},"
            f" last_codel={self.last_codel},"
            f" current_codel={self.current_codel})"
        )


class PietInterpreter:
    def __init__(
        self,
        image: Image.Image,
        *,
        step_limit: int = 1_0000000000_000,
        debug: bool = False,
        runtime: PietRuntime | None = None,
    ):
        self.step_limit = step_limit
        self.debug = debug
        self.reader = ImageReader(image)
        self.runtime = runtime or PietRuntime()
        self.iteration = 0
        self.steps: list[StepTrace] = []
        self._last_codel = self.reader.codel_info(self.position)
        self._current_codel = self.reader.codel_info(self.position)
        self._flips = 0
        self._move_to_furthest_pixel()

    @property
    def stack(self) -> PietStack:
        return self.runtime.stack

    @property
    def pointer(self) -> DirectionPointer:
        return self.runtime.pointer

    @property
    def position(self) -> OrderedPair:
        return self.runtime.pointer.position

    @property
    def last_step(self) -> StepTrace | None:
        try:
            return self.steps[-1]
        except IndexError:
            return None

    @staticmethod
    def _find_color_position(color: Color) -> OrderedPair:
        row = next(
            i for i, v in enumerate((color in PIET_COLORS[0], color in PIET_COLORS[1], color in PIET_COLORS[2])) if v
        )
        column = next(
            i
            for i, v in enumerate(
                (
                    color == PIET_COLORS[row][0],
                    color == PIET_COLORS[row][1],
                    color == PIET_COLORS[row][2],
                    color == PIET_COLORS[row][3],
                    color == PIET_COLORS[row][4],
                    color == PIET_COLORS[row][5],
                )
            )
            if v
        )
        return OrderedPair(row, column)

    def _determine_color_change(self) -> ColorChange:
        c1_pos = self._find_color_position(self._last_codel.color)
        c2_pos = self._find_color_position(self._current_codel.color)
        lightness, hue = c2_pos[0] - c1_pos[0], c2_pos[1] - c1_pos[1]

        if lightness < 0:
            lightness += 3
        if hue < 0:
            hue += 6

        return ColorChange(lightness, hue)

    def _get_polars(self, coords: Iterable[OrderedPair]) -> tuple[OrderedPair, OrderedPair]:
        largest_x = max(coords, key=lambda coord: coord.x).x
        largest_y = max(coords, key=lambda coord: coord.y).y
        smallest_x = min(coords, key=lambda coord: coord.x).x
        smallest_y = min(coords, key=lambda coord: coord.y).y
        return (
            OrderedPair(largest_y, largest_x),
            OrderedPair(smallest_y, smallest_x),
        )

    def _determine_farthest_pixel(self, codel: Codel) -> OrderedPair:
        largest, smallest = self._get_polars(codel.pixels)
        if self.runtime.pointer.direction is PointerDirection.RIGHT:
            largest_x_places = [pos for pos in codel.pixels if pos.x == largest.x]
            largest, smallest = self._get_polars(largest_x_places)
            if self.runtime.codel_chooser.direction is CodelChooserDirection.LEFT:
                return OrderedPair(smallest.y, largest.x)
            return largest
        if self.runtime.pointer.direction is PointerDirection.DOWN:
            largest_y_places = [pos for pos in codel.pixels if pos.y == largest.y]
            largest, smallest = self._get_polars(largest_y_places)
            if self.runtime.codel_chooser.direction is CodelChooserDirection.LEFT:
                return largest
            return OrderedPair(largest.y, smallest.x)
        if self.runtime.pointer.direction is PointerDirection.LEFT:
            smallest_x_places = [pos for pos in codel.pixels if pos.x == smallest.x]
            largest, smallest = self._get_polars(smallest_x_places)
            if self.runtime.codel_chooser.direction is CodelChooserDirection.LEFT:
                return OrderedPair(largest.y, smallest.x)
            return smallest
        if self.runtime.pointer.direction is PointerDirection.UP:
            smallest_y_places = [pos for pos in codel.pixels if pos.y == smallest.y]
            largest, smallest = self._get_polars(smallest_y_places)
            if self.runtime.codel_chooser.direction is CodelChooserDirection.LEFT:
                return smallest
            return OrderedPair(smallest.y, largest.x)
        return OrderedPair(-1, -1)

    def _move_to_furthest_pixel(self):
        # move to farthest pixel in current codel
        if self._current_codel.color != WHITE:
            farthest_pixel = self._determine_farthest_pixel(self._current_codel)
            self.runtime.pointer.position = farthest_pixel

    def step(self):
        "Execute a single step."
        if self.iteration >= self.step_limit:
            raise StepLimitReached("Step limit reached.")
        if self._flips >= 4:
            raise EndOfProgram("End of program reached.")

        args = []
        did_flip = False

        next_y, next_x = self.pointer.next_position()
        try:
            blocked = self.reader.colors[next_y][next_x] == BLACK or next_y < 0 or next_x < 0
        except IndexError:
            blocked = True

        if not blocked:
            # move one pixel over to next codel
            self._last_codel = self._current_codel
            self.pointer.move_to_next()
            if self.reader.colors[self.position.y][self.position.x] == WHITE:
                # Skip the codel_info call if the current codel is white for performance reasons.
                self._current_codel = Codel(WHITE, {self.position})
                # Skip to the last white pixel in the direction of the DP.
                next_pos = self.pointer.next_position()
                while self.reader.colors[next_pos.y][next_pos.x] == WHITE:
                    self._current_codel.pixels.add(next_pos)
                    self.pointer.move_to_next()
                    next_pos = self.pointer.next_position()
            else:
                self._current_codel = self.reader.codel_info(self.position)
                self._move_to_furthest_pixel()

            # determine color delta between current and previous codel
            # and execute relevant instruction
            if WHITE in (self._last_codel.color, self._current_codel.color):
                instruction = self.runtime.p_noop
                if self._last_codel.color != self._current_codel.color:
                    self._flips = 0
            else:
                delta = self._determine_color_change()
                instruction = self.runtime.delta_map[delta]
                if delta == (1, 0):
                    args.append(len(self._last_codel))
                self._flips = 0
        else:
            if self.last_step and not self.last_step.did_flip:
                self.runtime.codel_chooser.flip()
                self._move_to_furthest_pixel()
                instruction = self.runtime.p_blocked
                did_flip = True
                self._flips += 1
            else:
                self.runtime.pointer.rotate()
                self._move_to_furthest_pixel()
                instruction = self.runtime.p_blocked
        instruction(*args)
        step = StepTrace(
            self.iteration,
            self.position,
            instruction,
            did_flip,
            self._last_codel,
            self._current_codel,
        )
        self.steps.append(step)
        self.iteration += 1
        if self.debug:
            print(step, file=sys.stderr)

    def run(self, speed: int = -1) -> EndOfProgram:
        """Start execution at pos(0,0). Run at `speed` steps/sec (-1 is unlimited (default))."""

        last_second = math.floor(time.time())
        steps_this_second = 0
        while True:
            this_second = math.floor(time.time())
            if this_second > last_second:
                last_second = this_second
                steps_this_second = 0
            if speed != -1 and steps_this_second == speed:
                continue

            try:
                self.step()
            except EndOfProgram as exc:
                return exc
            steps_this_second += 1

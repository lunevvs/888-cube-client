"""Several horizontal wire shapes falling from the top of the cube."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .base import AnimationAlgorithm
from .common import empty_frame, set_voxels


def square() -> set[tuple[int, int]]:
    return {
        (x, y)
        for x in range(1, 7)
        for y in range(1, 7)
        if x in (1, 6) or y in (1, 6)
    }


def cross() -> set[tuple[int, int]]:
    return {(3, value) for value in range(8)} | {(4, value) for value in range(8)} | {
        (value, 3) for value in range(8)
    } | {(value, 4) for value in range(8)}


def diamond() -> set[tuple[int, int]]:
    return {
        (x, y)
        for x in range(8)
        for y in range(8)
        if abs(x - 3.5) + abs(y - 3.5) in (3.0, 4.0)
    }


class FallingShapes(AnimationAlgorithm):
    name = "falling_shapes"
    description = "Контуры квадрата, креста и ромба, падающие сверху"
    recommended_fps = 8.0

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        frames = []
        shapes: Iterable[set[tuple[int, int]]] = (square(), cross(), diamond())
        for shape in shapes:
            for z in range(7, -1, -1):
                frame = empty_frame()
                set_voxels(frame, ((x, y, z) for x, y in shape))
                frames.append(bytes(frame))
            frames.extend((frames[-1], bytes(64)))
        return frames


ALGORITHM = FallingShapes()

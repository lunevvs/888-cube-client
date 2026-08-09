"""Coordinate and rasterization helpers shared by animation algorithms."""

from __future__ import annotations

import math
from collections.abc import Iterable


CUBE_SIZE = 8
FRAME_SIZE = CUBE_SIZE * CUBE_SIZE


def empty_frame() -> bytearray:
    return bytearray(FRAME_SIZE)


def set_voxel(frame: bytearray, x: int, y: int, z: int) -> None:
    if 0 <= x < CUBE_SIZE and 0 <= y < CUBE_SIZE and 0 <= z < CUBE_SIZE:
        frame[x * CUBE_SIZE + y] |= 1 << z


def set_voxels(frame: bytearray, voxels: Iterable[tuple[int, int, int]]) -> None:
    for x, y, z in voxels:
        set_voxel(frame, x, y, z)


def clamp_coordinate(value: float) -> int:
    return max(0, min(CUBE_SIZE - 1, round(value)))


def triangle_position(
    frame: int, period: int, minimum: float = 1.25, maximum: float = 5.75
) -> float:
    phase = (frame % period) / period
    unit = 2.0 * phase if phase < 0.5 else 2.0 * (1.0 - phase)
    return minimum + (maximum - minimum) * unit


def line_2d(start: tuple[int, int], end: tuple[int, int]) -> set[tuple[int, int]]:
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    step_x = 1 if x0 < x1 else -1
    step_y = 1 if y0 < y1 else -1
    error = dx + dy
    points = set()

    while True:
        points.add((x0, y0))
        if x0 == x1 and y0 == y1:
            return points
        doubled = 2 * error
        if doubled >= dy:
            error += dy
            x0 += step_x
        if doubled <= dx:
            error += dx
            y0 += step_y


def angle_point(angle: float, radius: float) -> tuple[int, int]:
    center = 3.5
    return (
        clamp_coordinate(center + radius * math.cos(angle)),
        clamp_coordinate(center + radius * math.sin(angle)),
    )

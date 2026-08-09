#!/usr/bin/env python3
"""Generate a rotating line animation for the cube's front face."""

from __future__ import annotations

import math
from pathlib import Path


FRAME_COUNT = 14
OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "draw-series" / "rotating-diagonal"


def line_endpoints(angle: float) -> tuple[tuple[int, int], tuple[int, int]]:
    center = 3.5
    dx = math.cos(angle)
    dz = math.sin(angle)
    scale = min(
        center / abs(dx) if abs(dx) > 1e-12 else math.inf,
        center / abs(dz) if abs(dz) > 1e-12 else math.inf,
    )
    return (
        (round(center - scale * dx), round(center - scale * dz)),
        (round(center + scale * dx), round(center + scale * dz)),
    )


def rasterize_line(start: tuple[int, int], end: tuple[int, int]) -> set[tuple[int, int]]:
    x0, z0 = start
    x1, z1 = end
    dx = abs(x1 - x0)
    dz = -abs(z1 - z0)
    step_x = 1 if x0 < x1 else -1
    step_z = 1 if z0 < z1 else -1
    error = dx + dz
    points = set()

    while True:
        points.add((x0, z0))
        if x0 == x1 and z0 == z1:
            return points
        doubled = 2 * error
        if doubled >= dz:
            error += dz
            x0 += step_x
        if doubled <= dx:
            error += dx
            z0 += step_z


def make_frame(index: int) -> bytes:
    # A line repeats after 180 degrees. Frame zero is right-bottom to left-top.
    angle = math.pi / 4 + index * math.pi / FRAME_COUNT
    points = rasterize_line(*line_endpoints(angle))
    frame = bytearray(64)
    for x, z in points:
        frame[x * 8] |= 1 << z
    return bytes(frame)


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for index in range(FRAME_COUNT):
        path = OUTPUT_DIRECTORY / f"frame-{index:03d}.bin"
        path.write_bytes(make_frame(index))


if __name__ == "__main__":
    main()

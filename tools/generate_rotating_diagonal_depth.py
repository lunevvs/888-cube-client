#!/usr/bin/env python3
"""Generate a rotating diagonal that travels into the cube and back."""

from __future__ import annotations

import math
from pathlib import Path

from generate_rotating_diagonal import FRAME_COUNT, line_endpoints, rasterize_line


OUTPUT_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "draw-series"
    / "rotating-diagonal-depth"
)
DEPTH_PATH = tuple(range(8)) + tuple(range(6, 0, -1))
FRAMES_PER_DEPTH = 2


def make_frame(index: int, depth: int) -> bytes:
    angle = math.pi / 4 + index * math.pi / FRAME_COUNT
    points = rasterize_line(*line_endpoints(angle))
    frame = bytearray(64)
    for x, z in points:
        frame[x * 8 + depth] |= 1 << z
    return bytes(frame)


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    frame_index = 0
    for depth in DEPTH_PATH:
        for _ in range(FRAMES_PER_DEPTH):
            path = OUTPUT_DIRECTORY / f"frame-{frame_index:03d}.bin"
            path.write_bytes(make_frame(frame_index, depth))
            frame_index += 1


if __name__ == "__main__":
    main()

"""Two crossing sine waves represented by one voxel per vertical column."""

from __future__ import annotations

import math
from collections.abc import Mapping

from .base import AnimationAlgorithm
from .common import clamp_coordinate, empty_frame, set_voxel


class WaterSurface(AnimationAlgorithm):
    name = "water_surface"
    description = "Пересекающиеся волны на водной поверхности"
    recommended_fps = 8.0
    frame_count = 32

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        frames = []
        for index in range(self.frame_count):
            phase = 2.0 * math.pi * index / self.frame_count
            frame = empty_frame()
            for x in range(8):
                for y in range(8):
                    height = (
                        3.5
                        + 1.45 * math.sin(2.0 * math.pi * x / 8.0 + phase)
                        + 1.15 * math.sin(2.0 * math.pi * y / 8.0 - phase * 1.5)
                    )
                    set_voxel(frame, x, y, clamp_coordinate(height))
            frames.append(bytes(frame))
        return frames


ALGORITHM = WaterSurface()

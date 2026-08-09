"""A rotating double helix with occasional connecting rungs."""

from __future__ import annotations

import math
from collections.abc import Mapping

from .base import AnimationAlgorithm
from .common import angle_point, empty_frame, line_2d, set_voxel


class DoubleHelix(AnimationAlgorithm):
    name = "double_helix"
    description = "Вращающаяся двойная спираль"
    recommended_fps = 8.0
    frame_count = 24

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        frames = []
        for index in range(self.frame_count):
            # Two opposite strands repeat after 180 degrees, not 360.
            phase = math.pi * index / self.frame_count
            frame = empty_frame()
            for z in range(8):
                angle = phase + z * math.pi / 3.5
                first = angle_point(angle, 2.8)
                second = angle_point(angle + math.pi, 2.8)
                set_voxel(frame, first[0], first[1], z)
                set_voxel(frame, second[0], second[1], z)
                if z % 2 == 0:
                    for x, y in line_2d(first, second):
                        set_voxel(frame, x, y, z)
            frames.append(bytes(frame))
        return frames


ALGORITHM = DoubleHelix()

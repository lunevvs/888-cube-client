"""A rotating funnel whose radius increases with height."""

from __future__ import annotations

import math
from collections.abc import Mapping

from .base import AnimationAlgorithm
from .common import angle_point, empty_frame, set_voxel


class Tornado(AnimationAlgorithm):
    name = "tornado"
    description = "Вращающаяся воронка с расширением к верхней грани"
    recommended_fps = 10.0
    frame_count = 32

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        frames = []
        for index in range(self.frame_count):
            phase = 2.0 * math.pi * index / self.frame_count
            frame = empty_frame()
            for z in range(8):
                radius = 0.6 + z * 0.43
                base_angle = phase + z * 0.82
                for trail in range(3):
                    x, y = angle_point(base_angle - trail * 0.28, radius)
                    set_voxel(frame, x, y, z)
            frames.append(bytes(frame))
        return frames


ALGORITHM = Tornado()

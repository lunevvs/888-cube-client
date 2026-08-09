"""A quiet central bloom followed by a small orbit."""

from __future__ import annotations

import math
from collections.abc import Mapping

from .base import AnimationAlgorithm
from .common import angle_point, empty_frame, set_voxel
from ._notification_common import sphere_shell


class NotificationSoft(AnimationAlgorithm):
    name = "notification_soft"
    description = "Мягкое уведомление: центральный импульс и спокойная орбита"
    recommended_fps = default_fps = 4.0
    default_cycles = 1
    priority = "low"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        frames = [sphere_shell(radius) for radius in (0.7, 1.5, 2.3)]
        for index in range(9):
            frame = empty_frame()
            phase = 2.0 * math.pi * index / 9
            for offset in range(4):
                x, y = angle_point(phase + offset * math.pi / 2, 1.8)
                set_voxel(frame, x, y, 3 + offset % 2)
            frames.append(bytes(frame))
        return frames


ALGORITHM = NotificationSoft()

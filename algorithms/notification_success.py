"""A rising plane ending in a short full-cube confirmation."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from .common import empty_frame, set_voxel


class NotificationSuccess(AnimationAlgorithm):
    name = "notification_success"
    description = "Успех: восходящая плоскость и короткое подтверждение"
    recommended_fps = default_fps = 8.0
    default_cycles = 1
    priority = "normal"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        frames = []
        for z in range(8):
            frame = empty_frame()
            for x in range(8):
                for y in range(8):
                    set_voxel(frame, x, y, z)
            frames.append(bytes(frame))
        frames.extend((bytes([0xFF] * 64), bytes(64)))
        return frames


ALGORITHM = NotificationSuccess()

"""A collapsing shell followed by two front-face X pulses."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from ._notification_common import cube_shell, front_x


class NotificationError(AnimationAlgorithm):
    name = "notification_error"
    description = "Ошибка: схлопывание куба и двойной импульс X"
    recommended_fps = default_fps = 8.0
    default_cycles = 2
    priority = "high"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        empty = bytes(64)
        return [
            cube_shell(0),
            cube_shell(1),
            cube_shell(2),
            cube_shell(3),
            front_x(),
            empty,
            front_x(),
            empty,
        ]


ALGORITHM = NotificationError()

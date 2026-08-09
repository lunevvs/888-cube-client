"""A front plane enters the cube and folds into a compact marker."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from ._notification_common import cube_wireframe, vertical_square


class NotificationIncoming(AnimationAlgorithm):
    name = "notification_incoming"
    description = "Обычное событие: входящая плоскость складывается в маркер"
    recommended_fps = default_fps = 6.0
    default_cycles = 2
    priority = "normal"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        return [
            *(vertical_square(depth) for depth in range(4)),
            vertical_square(3, 1),
            vertical_square(3, 2),
            cube_wireframe(3),
            cube_wireframe(3),
        ]


ALGORITHM = NotificationIncoming()

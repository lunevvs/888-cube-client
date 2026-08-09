"""A recognizable double pulse of the outer wireframe."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from ._notification_common import cube_wireframe


class NotificationWarning(AnimationAlgorithm):
    name = "notification_warning"
    description = "Предупреждение: двойной импульс внешнего каркаса"
    recommended_fps = default_fps = 6.0
    default_cycles = 3
    priority = "high"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        pulse = cube_wireframe(0)
        empty = bytes(64)
        return [pulse, empty, pulse, empty, empty, empty]


ALGORITHM = NotificationWarning()

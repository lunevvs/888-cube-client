"""A slow breathing wireframe cube."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from ._notification_common import cube_wireframe


class NotificationReminder(AnimationAlgorithm):
    name = "notification_reminder"
    description = "Напоминание: медленно расширяющийся и сжимающийся каркас"
    recommended_fps = default_fps = 3.0
    default_cycles = 3
    priority = "low"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        return [cube_wireframe(offset) for offset in (3, 2, 1, 0, 1, 2)]


ALGORITHM = NotificationReminder()

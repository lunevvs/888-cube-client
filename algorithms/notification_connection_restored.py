"""Fallen particles reconstruct the cube wireframe."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from ._notification_common import connection_loss_frames


class NotificationConnectionRestored(AnimationAlgorithm):
    name = "notification_connection_restored"
    description = "Восстановление соединения: частицы собираются в каркас"
    recommended_fps = default_fps = 7.0
    default_cycles = 1
    priority = "normal"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        return list(reversed(connection_loss_frames()))


ALGORITHM = NotificationConnectionRestored()

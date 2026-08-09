"""The cube wireframe breaks into falling particles."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from ._notification_common import connection_loss_frames


class NotificationConnectionLost(AnimationAlgorithm):
    name = "notification_connection_lost"
    description = "Потеря соединения: каркас рассыпается и падает"
    recommended_fps = default_fps = 7.0
    default_cycles = 2
    priority = "high"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        return connection_loss_frames()


ALGORITHM = NotificationConnectionLost()

"""Fast repeated shell motion for critical notifications."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from ._notification_common import cube_shell


class NotificationUrgent(AnimationAlgorithm):
    name = "notification_urgent"
    description = "Срочное уведомление: быстрое схлопывание и раскрытие граней"
    recommended_fps = default_fps = 10.0
    default_cycles = 3
    priority = "critical"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        return [cube_shell(offset) for offset in (0, 1, 2, 3, 2, 1)]


ALGORITHM = NotificationUrgent()

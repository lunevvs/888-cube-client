"""Two expanding spherical waves, repeated until stopped."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from ._notification_common import sphere_shell


class NotificationIncomingCall(AnimationAlgorithm):
    name = "notification_incoming_call"
    description = "Входящий звонок: повторяющиеся двойные сферические волны"
    recommended_fps = default_fps = 8.0
    default_cycles = None
    priority = "high"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        wave = [sphere_shell(radius) for radius in (0.7, 1.5, 2.3, 3.1, 4.0)]
        pause = [bytes(64), bytes(64)]
        return wave + pause + wave + pause * 2


ALGORITHM = NotificationIncomingCall()

"""Particles converge from the corners and burst from the center."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from ._notification_common import frame_from_voxels, sphere_shell


class NotificationBackgroundComplete(AnimationAlgorithm):
    name = "notification_background_complete"
    description = "Завершение задачи: частицы сходятся в центр и расходятся волной"
    recommended_fps = default_fps = 8.0
    default_cycles = 1
    priority = "normal"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        corners = [
            (x, y, z)
            for x in (0, 7)
            for y in (0, 7)
            for z in (0, 7)
        ]
        frames = []
        for step in range(7):
            amount = step / 6
            frames.append(
                frame_from_voxels(
                    (
                        round(x + (3.5 - x) * amount),
                        round(y + (3.5 - y) * amount),
                        round(z + (3.5 - z) * amount),
                    )
                    for x, y, z in corners
                )
            )
        frames.extend(sphere_shell(radius) for radius in (1.5, 2.3, 3.1, 4.0))
        frames.append(bytes(64))
        return frames


ALGORITHM = NotificationBackgroundComplete()

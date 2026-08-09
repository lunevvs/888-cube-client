"""A short luminous trail moving around the cube's outer edges."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from ._notification_common import frame_from_voxels


def edge_path() -> list[tuple[int, int, int]]:
    path = []
    path.extend((x, 0, 0) for x in range(8))
    path.extend((7, 0, z) for z in range(1, 8))
    path.extend((7, y, 7) for y in range(1, 8))
    path.extend((x, 7, 7) for x in range(6, -1, -1))
    path.extend((0, 7, z) for z in range(6, -1, -1))
    path.extend((0, y, 0) for y in range(6, 0, -1))
    return path


class NotificationWaiting(AnimationAlgorithm):
    name = "notification_waiting"
    description = "Ожидание: светящийся след обходит внешний каркас"
    recommended_fps = default_fps = 8.0
    default_cycles = None
    priority = "status"

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        path = edge_path()
        return [
            frame_from_voxels(path[(index - trail) % len(path)] for trail in range(3))
            for index in range(len(path))
        ]


ALGORITHM = NotificationWaiting()

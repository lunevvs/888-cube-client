"""A small filled ball following a closed reflected path."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from .common import empty_frame, set_voxel, triangle_position


class BouncingBall(AnimationAlgorithm):
    name = "bouncing_ball"
    description = "Шар, отражающийся от стенок куба"
    recommended_fps = 10.0
    frame_count = 72
    radius_squared = 2.0

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        frames = []
        for index in range(self.frame_count):
            center = (
                triangle_position(index, 24),
                triangle_position(index + 7, 36),
                triangle_position(index + 3, 18),
            )
            frame = empty_frame()
            for x in range(8):
                for y in range(8):
                    for z in range(8):
                        distance_squared = sum(
                            (coordinate - origin) ** 2
                            for coordinate, origin in zip((x, y, z), center)
                        )
                        if distance_squared <= self.radius_squared:
                            set_voxel(frame, x, y, z)
            frames.append(bytes(frame))
        return frames


ALGORITHM = BouncingBall()

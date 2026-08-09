"""A bottom-up volume fill representing 0 to 100 percent progress."""

from __future__ import annotations

from collections.abc import Mapping

from .base import AnimationAlgorithm
from .common import empty_frame, set_voxel


class NotificationProgress(AnimationAlgorithm):
    name = "notification_progress"
    description = "Прогресс: заполнение объёма снизу вверх"
    recommended_fps = default_fps = 8.0
    default_cycles = 1
    clear_after = False
    priority = "status"
    option_descriptions = {"progress": "степень заполнения от 0 до 100 (по умолчанию 50)"}

    def generate_frames(self, options: Mapping[str, str]) -> list[bytes]:
        raw_progress = options.get("progress", "50")
        try:
            progress = float(raw_progress)
        except ValueError as error:
            raise ValueError("progress must be a number from 0 to 100") from error
        if not 0 <= progress <= 100:
            raise ValueError("progress must be from 0 to 100")

        target = round(512 * progress / 100)
        order = [
            (x, y, z)
            for z in range(8)
            for y in range(8)
            for x in range(8)
        ]
        steps = max(1, min(8, (target + 63) // 64))
        frames = []

        def frame_with_count(count: int) -> bytes:
            frame = empty_frame()
            for voxel in order[:count]:
                set_voxel(frame, *voxel)
            return bytes(frame)

        for step in range(1, steps + 1):
            count = round(target * step / steps)
            frames.append(frame_with_count(count))

        full_frame = frame_with_count(target)
        if progress == 100:
            interior = empty_frame()
            for x in range(1, 7):
                for y in range(1, 7):
                    for z in range(1, 7):
                        set_voxel(interior, x, y, z)
            stable_frame = bytes(interior)
        else:
            stable_progress = max(0.0, progress - 10.0)
            stable_count = round(512 * stable_progress / 100)
            stable_frame = frame_with_count(stable_count)

        if stable_frame != full_frame:
            # Two frames per state at 8 FPS produce a 2 Hz blink. The last
            # state is always the complete progress value and remains visible.
            frames.extend(
                [stable_frame] * 2
                + [full_frame] * 2
                + [stable_frame] * 2
                + [full_frame] * 3
            )
        else:
            frames.extend([full_frame] * 3)
        return frames


ALGORITHM = NotificationProgress()

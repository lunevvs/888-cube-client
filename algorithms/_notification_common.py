"""Geometry shared by notification animations."""

from __future__ import annotations

import math

from .common import empty_frame, set_voxel


CENTER = (3.5, 3.5, 3.5)


def frame_from_voxels(voxels) -> bytes:
    frame = empty_frame()
    for x, y, z in voxels:
        set_voxel(frame, x, y, z)
    return bytes(frame)


def sphere_shell(radius: float, thickness: float = 0.7) -> bytes:
    voxels = []
    for x in range(8):
        for y in range(8):
            for z in range(8):
                distance = math.sqrt(
                    (x - CENTER[0]) ** 2
                    + (y - CENTER[1]) ** 2
                    + (z - CENTER[2]) ** 2
                )
                if abs(distance - radius) <= thickness:
                    voxels.append((x, y, z))
    return frame_from_voxels(voxels)


def cube_wireframe(offset: int) -> bytes:
    low = offset
    high = 7 - offset
    voxels = []
    for x in range(low, high + 1):
        for y in range(low, high + 1):
            for z in range(low, high + 1):
                boundaries = sum(
                    coordinate in (low, high) for coordinate in (x, y, z)
                )
                if boundaries >= 2:
                    voxels.append((x, y, z))
    return frame_from_voxels(voxels)


def cube_shell(offset: int) -> bytes:
    low = offset
    high = 7 - offset
    return frame_from_voxels(
        (x, y, z)
        for x in range(low, high + 1)
        for y in range(low, high + 1)
        for z in range(low, high + 1)
        if low in (x, y, z) or high in (x, y, z)
    )


def vertical_square(depth: int, inset: int = 0) -> bytes:
    low = inset
    high = 7 - inset
    return frame_from_voxels(
        (x, depth, z)
        for x in range(low, high + 1)
        for z in range(low, high + 1)
        if x in (low, high) or z in (low, high)
    )


def front_x() -> bytes:
    return frame_from_voxels(
        (x, 0, z)
        for x in range(8)
        for z in range(8)
        if z in (x, 7 - x)
    )


def connection_loss_frames() -> list[bytes]:
    particles = [
        (x, y, z)
        for x in range(8)
        for y in range(8)
        for z in range(8)
        if sum(coordinate in (0, 7) for coordinate in (x, y, z)) >= 2
    ]
    frames = []
    for step in range(14):
        voxels = []
        for index, (x, y, z) in enumerate(particles):
            delay = index % 5
            age = step - delay
            if age < 0:
                voxels.append((x, y, z))
            elif age < 8:
                drift_x = -1 if index % 3 == 0 else 1 if index % 3 == 1 else 0
                drift_y = -1 if index % 4 == 0 else 1 if index % 4 == 1 else 0
                voxels.append(
                    (
                        max(0, min(7, x + drift_x * age // 3)),
                        max(0, min(7, y + drift_y * age // 3)),
                        max(0, z - age),
                    )
                )
        frames.append(frame_from_voxels(voxels))
    return frames

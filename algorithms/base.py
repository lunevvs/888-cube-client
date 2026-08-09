"""Interface implemented by every procedural animation algorithm."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence


class AnimationAlgorithm(ABC):
    """Generate one finite, seamlessly repeatable animation cycle."""

    name: str
    description: str
    recommended_fps: float
    priority: str = "ambient"
    default_fps: float = 4.0
    default_cycles: int | None = None
    clear_after: bool = True
    option_descriptions: Mapping[str, str] = {}

    @abstractmethod
    def generate_frames(self, options: Mapping[str, str]) -> Sequence[bytes]:
        """Return a non-empty sequence of raw 64-byte frames."""

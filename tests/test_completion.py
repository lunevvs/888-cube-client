import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPLETION = ROOT / "completions" / "draw.py.bash"


def complete(*words: str) -> list[str]:
    command = r'''
source "$1"
shift
COMP_WORDS=("$@")
COMP_CWORD=$((${#COMP_WORDS[@]} - 1))
_888_cube_client
printf '%s\n' "${COMPREPLY[@]}"
'''
    result = subprocess.run(
        ["bash", "-c", command, "bash", str(COMPLETION), *words],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.splitlines()


class CompletionTests(unittest.TestCase):
    def test_completes_arguments(self):
        self.assertEqual(complete("draw.py", "--fro"), ["--front", "--front-face"])

    def test_completes_algorithm_names(self):
        self.assertIn(
            "notification_warning",
            complete("draw.py", "--algorithm", "notification_w"),
        )

    def test_completes_only_adjacent_bottom_faces(self):
        values = complete("draw.py", "--front", "up", "--bottom", "")
        self.assertEqual(values, ["front", "back", "left", "right"])

    def test_completes_frame_files_and_directories(self):
        values = complete("draw.py", "draw-example/draw-")
        self.assertEqual(
            values,
            [
                "draw-example/draw-bottom-layer",
                "draw-example/draw-front-diagonal",
                "draw-example/draw-top-layer",
            ],
        )


if __name__ == "__main__":
    unittest.main()

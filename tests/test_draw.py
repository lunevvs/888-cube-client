import importlib.util
import io
import os
import tempfile
import time
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cube_draw", ROOT / "draw.py")
assert SPEC is not None and SPEC.loader is not None
draw = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(draw)


class DrawTests(unittest.TestCase):
    def test_loads_exactly_64_binary_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frame"
            expected = bytes(range(64))
            path.write_bytes(expected)
            self.assertEqual(draw.load_frame(path), expected)

    def test_rejects_wrong_frame_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "frame"
            path.write_bytes(bytes(63))
            with self.assertRaisesRegex(draw.DrawError, "exactly 64 bytes"):
                draw.load_frame(path)

    def test_builds_binary_safe_command(self):
        data = bytes(range(64))
        self.assertEqual(draw.build_command(data), b"draw " + data)

    def test_front_face_is_not_rotated(self):
        data = bytes(range(64))
        self.assertIs(draw.orient_frame(data, "front"), data)

    def test_frame_can_be_oriented_toward_every_cube_face(self):
        frame = bytearray(64)
        frame[1 * 8 + 2] = 1 << 3
        expected_positions = {
            "front": (1, 2, 3),
            "back": (6, 5, 3),
            "left": (5, 1, 3),
            "right": (2, 6, 3),
            "up": (1, 3, 5),
            "down": (1, 4, 2),
        }

        for face, (x, y, z) in expected_positions.items():
            with self.subTest(face=face):
                expected = bytearray(64)
                expected[x * 8 + y] = 1 << z
                self.assertEqual(draw.orient_frame(bytes(frame), face), expected)

    def test_bottom_face_selects_all_24_cube_orientations(self):
        frame = bytearray(64)
        frame[1 * 8 + 0] = 1 << 0
        oriented_positions = set()

        for front in draw.FRONT_FACES:
            for bottom in draw.FRONT_FACES:
                if bottom in (front, draw.OPPOSITE_FACES[front]):
                    continue
                with self.subTest(front=front, bottom=bottom):
                    oriented = draw.orient_frame(bytes(frame), front, bottom)
                    positions = [
                        (x, y, z)
                        for x in range(8)
                        for y in range(8)
                        for z in range(8)
                        if oriented[x * 8 + y] & (1 << z)
                    ]
                    self.assertEqual(len(positions), 1)
                    position = positions[0]
                    oriented_positions.add(position)

                    front_axis = draw.FACE_VECTORS[front].index(
                        next(value for value in draw.FACE_VECTORS[front] if value)
                    )
                    bottom_axis = draw.FACE_VECTORS[bottom].index(
                        next(value for value in draw.FACE_VECTORS[bottom] if value)
                    )
                    front_boundary = (
                        7 if draw.FACE_VECTORS[front][front_axis] > 0 else 0
                    )
                    bottom_boundary = (
                        7 if draw.FACE_VECTORS[bottom][bottom_axis] > 0 else 0
                    )
                    self.assertEqual(position[front_axis], front_boundary)
                    self.assertEqual(position[bottom_axis], bottom_boundary)

        self.assertEqual(len(oriented_positions), 24)

    def test_bottom_face_must_be_adjacent_to_front(self):
        for bottom in ("front", "back"):
            with self.subTest(bottom=bottom):
                with self.assertRaisesRegex(draw.DrawError, "is not adjacent"):
                    draw.orient_frame(bytes(64), "front", bottom)

    def test_default_bottom_faces_preserve_previous_orientations(self):
        self.assertEqual(
            draw.DEFAULT_BOTTOM_FACES,
            {
                "front": "down",
                "back": "down",
                "left": "down",
                "right": "down",
                "up": "front",
                "down": "back",
            },
        )

    def test_front_parameter_accepts_all_six_faces(self):
        for face in draw.FRONT_FACES:
            with self.subTest(face=face):
                arguments = draw.create_parser().parse_args(
                    ["--front", face, "frame.bin"]
                )
                self.assertEqual(arguments.front, face)

    def test_front_face_alias_is_supported(self):
        arguments = draw.create_parser().parse_args(
            ["--front-face", "left", "frame.bin"]
        )
        self.assertEqual(arguments.front, "left")

    def test_bottom_parameter_and_alias_are_supported(self):
        for option in ("--bottom", "--bottom-face"):
            with self.subTest(option=option):
                arguments = draw.create_parser().parse_args(
                    ["--front", "up", option, "left", "frame.bin"]
                )
                self.assertEqual(arguments.bottom, "left")

    def test_accepts_current_firmware_response(self):
        self.assertTrue(draw.response_confirms_frame(b"draw\r\n64\r\n"))

    def test_accepts_planned_firmware_response(self):
        self.assertTrue(draw.response_confirms_frame(b"OK draw 64\r\n"))

    def test_rejects_partial_frame_response(self):
        self.assertFalse(draw.response_confirms_frame(b"draw\r\n17\r\n"))

    def test_fast_mode_is_the_default(self):
        arguments = draw.create_parser().parse_args(["frame.bin"])
        self.assertEqual(arguments.port, "auto")
        self.assertEqual(arguments.reset_delay, 0.0)
        self.assertFalse(arguments.require_ack)

    def test_explicit_serial_port_overrides_discovery(self):
        self.assertEqual(
            draw.resolve_serial_port("/dev/cu.custom", ["/dev/cu.other"]),
            "/dev/cu.custom",
        )

    def test_only_discovered_serial_port_is_selected(self):
        self.assertEqual(
            draw.resolve_serial_port("auto", ["/dev/cu.usbmodem101"]),
            "/dev/cu.usbmodem101",
        )

    def test_missing_serial_port_is_reported(self):
        with self.assertRaisesRegex(draw.DrawError, "no Arduino-compatible"):
            draw.resolve_serial_port("auto", [])

    def test_ambiguous_serial_ports_are_reported(self):
        with self.assertRaisesRegex(draw.DrawError, "multiple Arduino-compatible"):
            draw.resolve_serial_port(
                "auto", ["/dev/cu.usbmodem101", "/dev/cu.usbmodem102"]
            )

    def test_discovery_deduplicates_linux_by_id_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            device = root / "ttyACM0"
            device.touch()
            by_id = root / "usb-Arduino_Micro"
            by_id.symlink_to(device)

            ports = draw.discover_serial_ports(
                (str(root / "usb-Arduino*"), str(root / "ttyACM*"))
            )

        self.assertEqual(ports, [str(by_id)])

    @patch.object(draw, "discover_serial_ports", return_value=["/dev/cu.usbmodem101"])
    def test_list_ports_does_not_require_frame_source(self, discover_mock):
        output = io.StringIO()
        with redirect_stdout(output):
            result = draw.main(["--list-ports"])

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "/dev/cu.usbmodem101\n")
        discover_mock.assert_called_once_with()

    def test_ack_can_be_enabled(self):
        arguments = draw.create_parser().parse_args(["--ack", "frame.bin"])
        self.assertTrue(arguments.require_ack)

    def test_series_defaults_to_four_fps(self):
        arguments = draw.create_parser().parse_args(["frames"])
        self.assertIsNone(arguments.fps)
        self.assertIsNone(arguments.cycles)

    def test_cycle_count_can_be_set(self):
        arguments = draw.create_parser().parse_args(["--cycles", "3", "frames"])
        self.assertEqual(arguments.cycles, 3)

    def test_algorithm_can_be_selected_without_source(self):
        arguments = draw.create_parser().parse_args(
            ["--algorithm", "water_surface"]
        )
        self.assertIsNone(arguments.source)
        self.assertEqual(arguments.algorithm, "water_surface")

    def test_cycle_count_must_be_positive(self):
        with self.assertRaisesRegex(draw.argparse.ArgumentTypeError, "greater than zero"):
            draw.positive_int("0")

    def test_directory_frames_are_sorted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "frame-002.bin").write_bytes(bytes([2]) * 64)
            (path / "frame-001.bin").write_bytes(bytes([1]) * 64)
            (path / "README.md").write_text("ignored")

            frames = draw.load_frames(path)

        self.assertEqual(
            [frame_path.name for frame_path, _ in frames],
            ["frame-001.bin", "frame-002.bin"],
        )
        self.assertEqual([data[0] for _, data in frames], [1, 2])

    def test_empty_frame_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(draw.DrawError, r"no \*\.bin files"):
                draw.load_frames(Path(directory))

    def test_generated_rotating_diagonal_series(self):
        frames = draw.load_frames(ROOT / "draw-series" / "rotating-diagonal")
        first_frame = draw.load_frame(ROOT / "draw-example" / "draw-front-diagonal")
        self.assertEqual(len(frames), 14)
        self.assertEqual(len({data for _, data in frames}), 14)
        self.assertEqual(frames[0][1], first_frame)

    def test_generated_diagonal_depth_series(self):
        frames = draw.load_frames(
            ROOT / "draw-series" / "rotating-diagonal-depth"
        )
        expected_depths = [
            depth
            for depth in list(range(8)) + list(range(6, 0, -1))
            for _ in range(2)
        ]

        self.assertEqual(len(frames), 28)
        self.assertEqual(len({data for _, data in frames}), 28)
        for (_, data), expected_depth in zip(frames, expected_depths):
            active_depths = {index % 8 for index, value in enumerate(data) if value}
            self.assertEqual(active_depths, {expected_depth})

    def test_all_procedural_algorithms_implement_interface(self):
        expected_effects = {
            "bouncing_ball",
            "double_helix",
            "falling_shapes",
            "tornado",
            "water_surface",
        }
        expected_notifications = {
            "notification_background_complete",
            "notification_connection_lost",
            "notification_connection_restored",
            "notification_error",
            "notification_incoming",
            "notification_incoming_call",
            "notification_progress",
            "notification_reminder",
            "notification_soft",
            "notification_success",
            "notification_urgent",
            "notification_waiting",
            "notification_warning",
        }
        expected = expected_effects | expected_notifications
        self.assertEqual(set(draw.algorithm_names()), expected)

        for name in expected:
            algorithm, frames = draw.load_algorithm(name)
            self.assertIsInstance(algorithm, draw.AnimationAlgorithm)
            self.assertEqual(algorithm.name, name)
            self.assertGreater(algorithm.recommended_fps, 0)
            self.assertTrue(frames)
            self.assertTrue(all(len(frame) == 64 for frame in frames))
            if name in expected_effects:
                self.assertGreaterEqual(len(set(frames)), int(len(frames) * 0.75))

    def test_notification_metadata_is_valid(self):
        notifications = [
            name for name in draw.algorithm_names() if name.startswith("notification_")
        ]
        self.assertEqual(len(notifications), 13)
        for name in notifications:
            algorithm, _ = draw.load_algorithm(name)
            self.assertIn(
                algorithm.priority, {"low", "normal", "high", "critical", "status"}
            )
            self.assertGreater(algorithm.default_fps, 0)
            if algorithm.default_cycles is not None:
                self.assertGreater(algorithm.default_cycles, 0)

    def test_progress_option_controls_filled_voxels(self):
        _, empty_frames = draw.load_algorithm(
            "notification_progress", {"progress": "0"}
        )
        _, full_frames = draw.load_algorithm(
            "notification_progress", {"progress": "100"}
        )
        self.assertEqual(sum(byte.bit_count() for byte in empty_frames[-1]), 0)
        self.assertEqual(sum(byte.bit_count() for byte in full_frames[-1]), 512)

    def test_invalid_progress_is_rejected(self):
        with self.assertRaisesRegex(draw.DrawError, "progress must be from 0 to 100"):
            draw.load_algorithm("notification_progress", {"progress": "101"})

    def test_unsupported_algorithm_option_is_rejected(self):
        with self.assertRaisesRegex(draw.DrawError, "does not support option"):
            draw.load_algorithm("notification_success", {"progress": "50"})

    def test_algorithm_defaults_and_overrides_are_reported(self):
        default_output = io.StringIO()
        with redirect_stdout(default_output):
            result = draw.main(
                ["--dry-run", "--algorithm", "notification_warning"]
            )
        self.assertEqual(result, 0)
        self.assertIn("6 fps, for 3 cycles", default_output.getvalue())

        override_output = io.StringIO()
        with redirect_stdout(override_output):
            result = draw.main(
                [
                    "--dry-run",
                    "--algorithm",
                    "notification_warning",
                    "--fps",
                    "2",
                    "--cycles",
                    "1",
                ]
            )
        self.assertEqual(result, 0)
        self.assertIn("2 fps, for 1 cycles", override_output.getvalue())

    def test_unknown_algorithm_is_rejected(self):
        with self.assertRaisesRegex(draw.DrawError, "unknown algorithm"):
            draw.load_algorithm("missing_effect")

    @patch.object(draw.time, "sleep")
    @patch.object(draw.time, "monotonic", return_value=0.0)
    def test_finite_series_ends_with_empty_frame(self, monotonic_mock, sleep_mock):
        class Connection:
            def __init__(self):
                self.commands = []

            def send(self, command):
                self.commands.append(command)

        connection = Connection()
        commands = [draw.build_command(bytes([value]) * 64) for value in (1, 2)]

        draw.play_frames(connection, commands, fps=4.0, cycles=3)

        self.assertEqual(connection.commands[:-1], commands * 3)
        self.assertEqual(connection.commands[-1], draw.EMPTY_COMMAND)

    @patch.object(draw.time, "sleep")
    @patch.object(draw.time, "monotonic", return_value=0.0)
    def test_progress_can_leave_its_last_frame_visible(
        self, monotonic_mock, sleep_mock
    ):
        class Connection:
            def __init__(self):
                self.commands = []

            def send(self, command):
                self.commands.append(command)

        algorithm, frames = draw.load_algorithm(
            "notification_progress", {"progress": "75"}
        )
        commands = [draw.build_command(frame) for frame in frames]
        connection = Connection()

        draw.play_frames(
            connection,
            commands,
            fps=algorithm.default_fps,
            cycles=algorithm.default_cycles,
            clear_after=algorithm.clear_after,
        )

        self.assertFalse(algorithm.clear_after)
        self.assertEqual(connection.commands, commands)
        self.assertNotEqual(connection.commands[-1], draw.EMPTY_COMMAND)

    def test_only_last_ten_percent_of_progress_blinks(self):
        _, frames = draw.load_algorithm(
            "notification_progress", {"progress": "75"}
        )
        blink_frames = frames[-9:]
        voxel_counts = {
            sum(byte.bit_count() for byte in frame) for frame in blink_frames
        }
        stable_count = round(512 * 0.65)
        full_count = round(512 * 0.75)

        self.assertEqual(voxel_counts, {stable_count, full_count})
        self.assertEqual(
            sum(byte.bit_count() for byte in frames[-1]), full_count
        )

        stable_frame = next(
            frame
            for frame in blink_frames
            if sum(byte.bit_count() for byte in frame) == stable_count
        )
        full_frame = frames[-1]
        self.assertTrue(
            all(stable_byte & ~full_byte == 0 for stable_byte, full_byte in zip(stable_frame, full_frame))
        )

    def test_full_progress_blinks_only_external_surfaces(self):
        _, frames = draw.load_algorithm(
            "notification_progress", {"progress": "100"}
        )
        blink_frames = frames[-9:]
        voxel_counts = {
            sum(byte.bit_count() for byte in frame) for frame in blink_frames
        }
        self.assertEqual(voxel_counts, {6 * 6 * 6, 8 * 8 * 8})

        interior_frame = next(
            frame
            for frame in blink_frames
            if sum(byte.bit_count() for byte in frame) == 6 * 6 * 6
        )
        for x in range(8):
            for y in range(8):
                for z in range(8):
                    enabled = bool(interior_frame[x * 8 + y] & (1 << z))
                    self.assertEqual(enabled, all(1 <= value <= 6 for value in (x, y, z)))

        self.assertEqual(
            sum(byte.bit_count() for byte in frames[-1]), 8 * 8 * 8
        )

    def test_response_read_stops_as_soon_as_ack_arrives(self):
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b"draw\r\n64\r\n")
            started = time.monotonic()
            response = draw.read_response(read_fd, 1.0)
            elapsed = time.monotonic() - started
        finally:
            os.close(read_fd)
            os.close(write_fd)

        self.assertEqual(response, b"draw\r\n64\r\n")
        self.assertLess(elapsed, 0.2)

    @patch.object(draw.termios, "tcdrain")
    @patch.object(draw.os, "write", return_value=69)
    @patch.object(draw.select, "select", return_value=([], [123], []))
    def test_write_uses_select_writable_result(self, select_mock, write_mock, drain_mock):
        command = b"draw " + bytes(64)
        draw.write_once(123, command, 2.0)
        select_mock.assert_called_once_with([], [123], [], 2.0)
        write_mock.assert_called_once_with(123, command)
        drain_mock.assert_called_once_with(123)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Send one frame or play a frame series on the 8x8x8 LED cube."""

from __future__ import annotations

import argparse
import glob
import importlib
import os
import re
import select
import sys
import termios
import time
import tty
from pathlib import Path

from algorithms.base import AnimationAlgorithm


DEFAULT_PORT = "auto"
DEFAULT_BAUD = 9600
FRAME_SIZE = 64
COMMAND_PREFIX = b"draw "
EMPTY_COMMAND = COMMAND_PREFIX + bytes(FRAME_SIZE)
FRONT_FACES = ("front", "back", "left", "right", "up", "down")
FACE_VECTORS = {
    "front": (0, -1, 0),
    "back": (0, 1, 0),
    "left": (1, 0, 0),
    "right": (-1, 0, 0),
    "up": (0, 0, 1),
    "down": (0, 0, -1),
}
OPPOSITE_FACES = {
    "front": "back",
    "back": "front",
    "left": "right",
    "right": "left",
    "up": "down",
    "down": "up",
}
DEFAULT_BOTTOM_FACES = {
    "front": "down",
    "back": "down",
    "left": "down",
    "right": "down",
    "up": "front",
    "down": "back",
}


class DrawError(Exception):
    """A user-facing error while preparing or sending a frame."""


def serial_port_patterns(platform: str | None = None) -> tuple[str, ...]:
    """Return likely USB serial device patterns for the current POSIX system."""
    platform = platform or sys.platform
    if platform == "darwin":
        return ("/dev/cu.usbmodem*", "/dev/cu.usbserial*")
    if platform.startswith("linux"):
        return (
            "/dev/serial/by-id/*Arduino*",
            "/dev/serial/by-id/*arduino*",
            "/dev/serial/by-id/*SparkFun*",
            "/dev/ttyACM*",
            "/dev/ttyUSB*",
        )
    if platform.startswith("freebsd"):
        return ("/dev/cuaU*",)
    return ()


def discover_serial_ports(patterns: tuple[str, ...] | None = None) -> list[str]:
    """Find likely Arduino-compatible serial ports without opening them."""
    patterns = patterns if patterns is not None else serial_port_patterns()
    ports = []
    real_paths = set()
    for pattern in patterns:
        for port in sorted(glob.glob(pattern)):
            real_path = os.path.realpath(port)
            if real_path in real_paths:
                continue
            real_paths.add(real_path)
            ports.append(port)
    return ports


def resolve_serial_port(
    requested_port: str, candidates: list[str] | None = None
) -> str:
    """Resolve an explicit port or safely select the only discovered port."""
    if requested_port != "auto":
        return requested_port
    candidates = discover_serial_ports() if candidates is None else candidates
    if not candidates:
        raise DrawError(
            "no Arduino-compatible serial port found; connect the cube or use "
            "--port PATH"
        )
    if len(candidates) > 1:
        raise DrawError(
            "multiple Arduino-compatible serial ports found: "
            f"{', '.join(candidates)}; select one with --port PATH"
        )
    return candidates[0]


def algorithm_names() -> list[str]:
    directory = Path(__file__).resolve().parent / "algorithms"
    ignored = {"__init__", "base", "common"}
    return sorted(
        path.stem
        for path in directory.glob("*.py")
        if path.stem not in ignored and not path.stem.startswith("_")
    )


def parse_algorithm_options(values: list[str]) -> dict[str, str]:
    options = {}
    for value in values:
        key, separator, option_value = value.partition("=")
        if not separator or not key or not option_value:
            raise DrawError(
                f"invalid algorithm option {value!r}; expected KEY=VALUE"
            )
        if key in options:
            raise DrawError(f"algorithm option {key!r} was specified more than once")
        options[key] = option_value
    return options


def load_algorithm(
    name: str, options: dict[str, str] | None = None
) -> tuple[AnimationAlgorithm, list[bytes]]:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise DrawError(
            "algorithm name may contain only lowercase letters, digits, and underscores"
        )
    if name not in algorithm_names():
        available = ", ".join(algorithm_names())
        raise DrawError(f"unknown algorithm {name!r}; available: {available}")

    try:
        module = importlib.import_module(f"algorithms.{name}")
    except (ImportError, RuntimeError) as error:
        raise DrawError(f"cannot load algorithm {name!r}: {error}") from error

    algorithm = getattr(module, "ALGORITHM", None)
    if not isinstance(algorithm, AnimationAlgorithm):
        raise DrawError(
            f"algorithms/{name}.py must export ALGORITHM implementing "
            "AnimationAlgorithm"
        )
    if algorithm.name != name:
        raise DrawError(
            f"algorithm name {algorithm.name!r} must match its file name {name!r}"
        )

    supplied_options = options or {}
    unknown_options = sorted(set(supplied_options) - set(algorithm.option_descriptions))
    if unknown_options:
        available = ", ".join(algorithm.option_descriptions) or "none"
        raise DrawError(
            f"algorithm {name!r} does not support option(s): "
            f"{', '.join(unknown_options)}; available: {available}"
        )

    try:
        frames = list(algorithm.generate_frames(supplied_options))
    except Exception as error:
        raise DrawError(f"algorithm {name!r} failed to generate frames: {error}") from error
    if not frames:
        raise DrawError(f"algorithm {name!r} generated no frames")
    for index, frame in enumerate(frames):
        if not isinstance(frame, bytes) or len(frame) != FRAME_SIZE:
            size = len(frame) if isinstance(frame, (bytes, bytearray)) else "not bytes"
            raise DrawError(
                f"algorithm {name!r} frame {index} must be {FRAME_SIZE} bytes; "
                f"got {size}"
            )
    return algorithm, frames


def load_frame(path: Path) -> bytes:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise DrawError(f"cannot read frame file {path}: {error}") from error

    if len(data) != FRAME_SIZE:
        raise DrawError(
            f"frame file must contain exactly {FRAME_SIZE} bytes; "
            f"{path} contains {len(data)}"
        )
    return data


def load_frames(source: Path) -> list[tuple[Path, bytes]]:
    if source.is_file():
        return [(source, load_frame(source))]
    if not source.exists():
        raise DrawError(f"frame source does not exist: {source}")
    if not source.is_dir():
        raise DrawError(f"frame source is neither a file nor a directory: {source}")

    paths = sorted(source.glob("*.bin"))
    if not paths:
        raise DrawError(f"frame directory contains no *.bin files: {source}")
    return [(path, load_frame(path)) for path in paths]


def build_command(data: bytes) -> bytes:
    if len(data) != FRAME_SIZE:
        raise DrawError(
            f"binary data must contain exactly {FRAME_SIZE} bytes; got {len(data)}"
        )
    return COMMAND_PREFIX + data


def resolve_bottom_face(front: str, bottom: str | None = None) -> str:
    """Validate an orientation and return its physical bottom face."""
    if front not in FRONT_FACES:
        raise DrawError(
            f"unknown front face {front!r}; available: {', '.join(FRONT_FACES)}"
        )
    if bottom is None:
        return DEFAULT_BOTTOM_FACES[front]
    if bottom not in FRONT_FACES:
        raise DrawError(
            f"unknown bottom face {bottom!r}; available: {', '.join(FRONT_FACES)}"
        )
    if bottom == front or bottom == OPPOSITE_FACES[front]:
        available = (
            face
            for face in FRONT_FACES
            if face != front and face != OPPOSITE_FACES[front]
        )
        raise DrawError(
            f"bottom face {bottom!r} is not adjacent to front face {front!r}; "
            f"available: {', '.join(available)}"
        )
    return bottom


def cross_product(
    first: tuple[int, int, int], second: tuple[int, int, int]
) -> tuple[int, int, int]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def orient_coordinates(
    x: int, y: int, z: int, front: str, bottom: str
) -> tuple[int, int, int]:
    front_vector = FACE_VECTORS[front]
    bottom_vector = FACE_VECTORS[bottom]
    target_axes = (
        cross_product(front_vector, bottom_vector),
        tuple(-component for component in front_vector),
        tuple(-component for component in bottom_vector),
    )
    target = [0, 0, 0]
    for coordinate, axis_vector in zip((x, y, z), target_axes):
        for axis, direction in enumerate(axis_vector):
            if direction:
                target[axis] = coordinate if direction > 0 else 7 - coordinate
                break
    return target[0], target[1], target[2]


def orient_frame(data: bytes, front: str, bottom: str | None = None) -> bytes:
    """Rotate a frame toward the selected front and bottom cube faces."""
    if len(data) != FRAME_SIZE:
        raise DrawError(
            f"binary data must contain exactly {FRAME_SIZE} bytes; got {len(data)}"
        )
    bottom = resolve_bottom_face(front, bottom)
    if front == "front" and bottom == "down":
        return data

    oriented = bytearray(FRAME_SIZE)
    for x in range(8):
        for y in range(8):
            column = data[x * 8 + y]
            for z in range(8):
                if not column & (1 << z):
                    continue
                target_x, target_y, target_z = orient_coordinates(
                    x, y, z, front, bottom
                )
                oriented[target_x * 8 + target_y] |= 1 << target_z
    return bytes(oriented)


def baud_constant(baud: int) -> int:
    constant = getattr(termios, f"B{baud}", None)
    if constant is None:
        raise DrawError(f"baud rate {baud} is not supported on this system")
    return constant


def configure_serial(fd: int, baud: int) -> list:
    try:
        previous = termios.tcgetattr(fd)
        tty.setraw(fd, termios.TCSANOW)
        attributes = termios.tcgetattr(fd)
        speed = baud_constant(baud)
        attributes[4] = speed
        attributes[5] = speed
        attributes[2] &= ~(
            termios.PARENB | termios.CSTOPB | termios.CSIZE
        )
        attributes[2] |= termios.CS8 | termios.CREAD | termios.CLOCAL
        attributes[6][termios.VMIN] = 0
        attributes[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, attributes)
        return previous
    except (OSError, termios.error) as error:
        raise DrawError(f"cannot configure serial port: {error}") from error


def write_once(fd: int, command: bytes, timeout: float) -> None:
    _, writable, _ = select.select([], [fd], [], timeout)
    if not writable:
        raise DrawError(f"serial port was not writable within {timeout:g} seconds")

    try:
        written = os.write(fd, command)
    except OSError as error:
        raise DrawError(f"cannot write to serial port: {error}") from error

    if written != len(command):
        raise DrawError(
            f"partial serial write: wrote {written} of {len(command)} bytes; "
            "the frame was not retried to avoid splitting it"
        )

    try:
        termios.tcdrain(fd)
    except (OSError, termios.error) as error:
        raise DrawError(f"cannot finish serial write: {error}") from error


def read_response(fd: int, timeout: float) -> bytes:
    deadline = time.monotonic() + timeout
    response = bytearray()

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        readable, _, _ = select.select([fd], [], [], remaining)
        if not readable:
            break
        try:
            chunk = os.read(fd, 1024)
        except BlockingIOError:
            continue
        except OSError as error:
            raise DrawError(f"cannot read serial response: {error}") from error
        if not chunk:
            break
        response.extend(chunk)
        if response_confirms_frame(response):
            break

    return bytes(response)


def response_confirms_frame(response: bytes) -> bool:
    lines = [line.strip() for line in response.replace(b"\r", b"").split(b"\n")]
    return b"64" in lines or b"OK draw 64" in lines


class SerialConnection:
    def __init__(
        self,
        port: str,
        baud: int,
        reset_delay: float,
        write_timeout: float,
        response_timeout: float,
        require_ack: bool,
    ) -> None:
        self.port = port
        self.baud = baud
        self.reset_delay = reset_delay
        self.write_timeout = write_timeout
        self.response_timeout = response_timeout
        self.require_ack = require_ack
        self.fd: int | None = None
        self.previous_attributes: list | None = None

    def __enter__(self) -> "SerialConnection":
        flags = os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK
        try:
            self.fd = os.open(self.port, flags)
            self.previous_attributes = configure_serial(self.fd, self.baud)
            if self.reset_delay:
                time.sleep(self.reset_delay)
            termios.tcflush(self.fd, termios.TCIOFLUSH)
            return self
        except (OSError, termios.error, DrawError) as error:
            self.close()
            if isinstance(error, DrawError):
                raise
            raise DrawError(f"cannot open serial port {self.port}: {error}") from error

    def send(self, command: bytes) -> bytes:
        if self.fd is None:
            raise DrawError("serial port is not open")

        if not self.require_ack:
            try:
                termios.tcflush(self.fd, termios.TCIFLUSH)
            except (OSError, termios.error) as error:
                raise DrawError(f"cannot clear serial input: {error}") from error

        write_once(self.fd, command, self.write_timeout)
        if not self.require_ack:
            return b""

        response = read_response(self.fd, self.response_timeout)
        if not response:
            raise DrawError(
                "cube did not respond; the current firmware may be blocked in "
                "Serial.flush() or may not have received a complete frame"
            )
        if not response_confirms_frame(response):
            printable = response.decode("ascii", errors="backslashreplace").strip()
            raise DrawError(f"cube did not confirm 64 bytes; response: {printable!r}")
        return response

    def close(self) -> None:
        if self.fd is None:
            return
        if self.previous_attributes is not None:
            try:
                termios.tcsetattr(
                    self.fd, termios.TCSANOW, self.previous_attributes
                )
            except (OSError, termios.error):
                pass
        os.close(self.fd)
        self.fd = None

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def send_frame(
    port: str,
    baud: int,
    command: bytes,
    reset_delay: float,
    write_timeout: float,
    response_timeout: float,
    require_ack: bool,
) -> bytes:
    with SerialConnection(
        port=port,
        baud=baud,
        reset_delay=reset_delay,
        write_timeout=write_timeout,
        response_timeout=response_timeout,
        require_ack=require_ack,
    ) as connection:
        return connection.send(command)


def play_frames(
    connection: SerialConnection,
    commands: list[bytes],
    fps: float,
    cycles: int | None = None,
    clear_after: bool = True,
) -> None:
    interval = 1.0 / fps
    next_frame_at = time.monotonic()
    completed_cycles = 0

    while cycles is None or completed_cycles < cycles:
        for command in commands:
            connection.send(command)
            next_frame_at += interval
            delay = next_frame_at - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                next_frame_at = time.monotonic()
        completed_cycles += 1

    if clear_after:
        connection.send(EMPTY_COMMAND)


def non_negative_float(value: str) -> float:
    try:
        result = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a number") from error
    if result < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return result


def positive_float(value: str) -> float:
    result = non_negative_float(value)
    if result == 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return result


def positive_int(value: str) -> int:
    try:
        result = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if result <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return result


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send one frame or loop over a frame directory on the 8x8x8 LED cube."
    )
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        help="raw 64-byte frame file or directory containing sorted *.bin frames",
    )
    parser.add_argument(
        "--algorithm",
        metavar="NAME",
        help="generate frames with algorithms/NAME.py instead of reading files",
    )
    parser.add_argument(
        "--algorithm-option",
        "-O",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="pass an algorithm-specific option; may be repeated",
    )
    parser.add_argument(
        "--list-algorithms",
        action="store_true",
        help="list available procedural algorithms and exit",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="list discovered Arduino-compatible serial ports and exit",
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        help="serial port path or 'auto' to detect it (default: auto)",
    )
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument(
        "--reset-delay",
        type=non_negative_float,
        default=0.0,
        metavar="SECONDS",
        help="delay after opening a port that resets the board (default: 0)",
    )
    parser.add_argument(
        "--write-timeout",
        type=positive_float,
        default=2.0,
        metavar="SECONDS",
        help="maximum wait for the port to become writable (default: 2)",
    )
    parser.add_argument(
        "--response-timeout",
        type=positive_float,
        default=1.5,
        metavar="SECONDS",
        help="maximum wait for firmware confirmation (default: 1.5)",
    )
    acknowledgement = parser.add_mutually_exclusive_group()
    acknowledgement.add_argument(
        "--ack",
        dest="require_ack",
        action="store_true",
        help="wait for firmware confirmation (disabled by default)",
    )
    acknowledgement.add_argument(
        "--no-ack",
        dest="require_ack",
        action="store_false",
        help="do not wait for firmware confirmation (default)",
    )
    parser.set_defaults(require_ack=False)
    parser.add_argument(
        "--fps",
        type=positive_float,
        help="override frame rate (files default to 4; algorithms define their own)",
    )
    repetition = parser.add_mutually_exclusive_group()
    repetition.add_argument(
        "--cycles",
        type=positive_int,
        metavar="N",
        help="play a series or algorithm N times, clear the cube, and exit",
    )
    repetition.add_argument(
        "--loop",
        action="store_true",
        help="override an algorithm's finite default and repeat until Ctrl+C",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and describe the frame without opening the serial port",
    )
    parser.add_argument(
        "--front",
        "--front-face",
        choices=FRONT_FACES,
        default="up",
        metavar="FACE",
        help=(
            "rotate frames so their front points at FACE: "
            "front, back, left, right, up, or down (default: front)"
        ),
    )
    parser.add_argument(
        "--bottom",
        "--bottom-face",
        choices=FRONT_FACES,
        metavar="FACE",
        default="back",
        help=(
            "orient frames by placing FACE below the selected front; FACE must "
            "be adjacent to --front (default preserves the original orientation)"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        if args.list_ports:
            ports = discover_serial_ports()
            if ports:
                print("\n".join(ports))
            else:
                print("no Arduino-compatible serial ports found")
            return 0
        if args.list_algorithms:
            for name in algorithm_names():
                algorithm, generated_frames = load_algorithm(name)
                cycles = (
                    "infinite"
                    if algorithm.default_cycles is None
                    else str(algorithm.default_cycles)
                )
                print(
                    f"{name}: {algorithm.description} "
                    f"({len(generated_frames)} frames, priority {algorithm.priority}, "
                    f"default {algorithm.default_fps:g} fps × {cycles} cycles)"
                )
            return 0
        if args.source is None and args.algorithm is None:
            raise DrawError("provide a frame source or --algorithm NAME")
        if args.source is not None and args.algorithm is not None:
            raise DrawError("frame source and --algorithm cannot be used together")
        if args.algorithm is None and args.algorithm_option:
            raise DrawError("--algorithm-option requires --algorithm")

        if args.algorithm is not None:
            algorithm_options = parse_algorithm_options(args.algorithm_option)
            algorithm, generated_frames = load_algorithm(
                args.algorithm, algorithm_options
            )
            frames = [
                (Path(f"{args.algorithm}/frame-{index:03d}"), frame)
                for index, frame in enumerate(generated_frames)
            ]
            is_series = True
            source_label = f"algorithm {algorithm.name}"
            fps = args.fps if args.fps is not None else algorithm.default_fps
            clear_after = algorithm.clear_after
            if args.loop:
                cycles = None
            elif args.cycles is not None:
                cycles = args.cycles
            else:
                cycles = algorithm.default_cycles
        else:
            assert args.source is not None
            frames = load_frames(args.source)
            is_series = args.source.is_dir()
            source_label = str(args.source)
            fps = args.fps if args.fps is not None else 4.0
            cycles = args.cycles
            clear_after = True

        bottom = resolve_bottom_face(args.front, args.bottom)
        commands = [
            build_command(orient_frame(data, args.front, bottom))
            for _, data in frames
        ]
        if (args.cycles is not None or args.loop) and not is_series:
            raise DrawError("--cycles can only be used with a series or algorithm")
        if args.dry_run:
            if not is_series:
                print(
                    f"valid frame: {frames[0][0]} ({FRAME_SIZE} data bytes, "
                    f"{len(commands[0])} command bytes, front: {args.front}, "
                    f"bottom: {bottom})"
                )
            else:
                cycle_description = (
                    "without a cycle limit" if cycles is None else f"for {cycles} cycles"
                )
                print(
                    f"valid series: {source_label} ({len(frames)} frames at "
                    f"{fps:g} fps, {cycle_description}, front: {args.front}, "
                    f"bottom: {bottom})"
                )
            return 0

        port = resolve_serial_port(args.port)
        connection = SerialConnection(
            port=port,
            baud=args.baud,
            reset_delay=args.reset_delay,
            write_timeout=args.write_timeout,
            response_timeout=args.response_timeout,
            require_ack=args.require_ack,
        )
        with connection:
            if not is_series:
                response = connection.send(commands[0])
                print(f"sent {FRAME_SIZE} data bytes to {port} at {args.baud} baud")
                if response:
                    printable = response.decode("ascii", errors="backslashreplace").strip()
                    print(f"cube response: {printable}")
            else:
                cycle_description = (
                    "continuously" if cycles is None else f"for {cycles} cycles"
                )
                print(
                    f"playing {len(frames)} frames from {source_label} at "
                    f"{fps:g} fps {cycle_description}; press Ctrl+C to stop"
                )
                try:
                    play_frames(
                        connection,
                        commands,
                        fps,
                        cycles,
                        clear_after=clear_after,
                    )
                except KeyboardInterrupt:
                    if clear_after:
                        connection.send(EMPTY_COMMAND)
                    print("\nstopped")
        return 0
    except DrawError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

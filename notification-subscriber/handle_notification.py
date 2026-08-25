#!/usr/bin/env python3
"""Match one notification JSON object and run a configured draw.py command."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # Report a focused setup error from load_config().
    yaml = None


REQUIRED_FIELDS = (
    "datetime",
    "appId",
    "appName",
    "notificationId",
    "notificationDatetime",
    "notificationHeader",
    "notificationBody",
)
SUPPORTED_OPERATORS = {"equals", "contains", "regex", "in"}
DEFAULT_CONFIG = Path(__file__).with_name("config.yaml")


class HandlerError(Exception):
    """A user-facing notification handler error."""


def load_json_object(raw_value: str, description: str) -> dict[str, Any]:
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise HandlerError(f"invalid {description} JSON: {error}") from error
    if not isinstance(value, dict):
        raise HandlerError(f"{description} JSON must be an object")
    return value


def load_notification(argument: str) -> dict[str, str]:
    raw_value = sys.stdin.read() if argument == "-" else argument
    notification = load_json_object(raw_value, "notification")

    missing = [field for field in REQUIRED_FIELDS if field not in notification]
    if missing:
        raise HandlerError(
            f"notification is missing required field(s): {', '.join(missing)}"
        )

    invalid = [
        field for field in REQUIRED_FIELDS if not isinstance(notification[field], str)
    ]
    if invalid:
        raise HandlerError(
            f"notification field(s) must be strings: {', '.join(invalid)}"
        )

    return {field: notification[field] for field in REQUIRED_FIELDS}


def load_config(path: Path) -> dict[str, Any]:
    try:
        raw_value = path.read_text(encoding="utf-8")
    except OSError as error:
        raise HandlerError(f"cannot read config {path}: {error}") from error

    if yaml is None:
        raise HandlerError(
            "PyYAML is not installed; run notification-subscriber/.venv/bin/pip "
            "install -r notification-subscriber/requirements.txt"
        )
    try:
        config = yaml.safe_load(raw_value)
    except yaml.YAMLError as error:
        raise HandlerError(f"invalid config YAML: {error}") from error
    if not isinstance(config, dict):
        raise HandlerError("config YAML must contain an object at the top level")
    rules = config.get("rules", [])
    if not isinstance(rules, list):
        raise HandlerError("config field 'rules' must be an array")
    if "defaultCommand" in config and not isinstance(config["defaultCommand"], list):
        raise HandlerError("config field 'defaultCommand' must be an array")
    return config


def matches_filter(actual: str, specification: Any) -> bool:
    if isinstance(specification, str):
        return actual == specification
    if not isinstance(specification, dict) or not specification:
        raise HandlerError("a filter must be a string or a non-empty object")

    unknown = set(specification) - SUPPORTED_OPERATORS
    if unknown:
        raise HandlerError(f"unsupported filter operator(s): {', '.join(sorted(unknown))}")

    for operator, expected in specification.items():
        if operator == "equals":
            if not isinstance(expected, str):
                raise HandlerError("filter operator 'equals' requires a string")
            if actual != expected:
                return False
        elif operator == "contains":
            if not isinstance(expected, str):
                raise HandlerError("filter operator 'contains' requires a string")
            if expected not in actual:
                return False
        elif operator == "regex":
            if not isinstance(expected, str):
                raise HandlerError("filter operator 'regex' requires a string")
            try:
                pattern = re.compile(expected)
                if pattern.search("") is not None:
                    raise HandlerError(
                        f"filter regex {expected!r} matches an empty string and would "
                        "match every notification"
                    )
                if pattern.search(actual) is None:
                    return False
            except re.error as error:
                raise HandlerError(f"invalid filter regex {expected!r}: {error}") from error
        elif operator == "in":
            if not isinstance(expected, list) or not all(
                isinstance(value, str) for value in expected
            ):
                raise HandlerError("filter operator 'in' requires an array of strings")
            if actual not in expected:
                return False
    return True


def rule_matches(rule: dict[str, Any], notification: dict[str, str]) -> bool:
    filters = rule.get("filters", {})
    if not isinstance(filters, dict):
        raise HandlerError("rule field 'filters' must be an object")

    for field, specification in filters.items():
        if field not in REQUIRED_FIELDS:
            raise HandlerError(f"rule filters unknown notification field {field!r}")
        if not matches_filter(notification[field], specification):
            return False
    return True


def select_command(
    config: dict[str, Any], notification: dict[str, str]
) -> tuple[str, list[str]] | None:
    for index, raw_rule in enumerate(config.get("rules", []), start=1):
        if not isinstance(raw_rule, dict):
            raise HandlerError(f"rule {index} must be an object")
        name = raw_rule.get("name", f"rule-{index}")
        if not isinstance(name, str) or not name:
            raise HandlerError(f"rule {index} field 'name' must be a non-empty string")
        command = raw_rule.get("command")
        if not isinstance(command, list) or not all(
            isinstance(argument, str) for argument in command
        ):
            raise HandlerError(f"rule {name!r} field 'command' must be an array of strings")
        if rule_matches(raw_rule, notification):
            return name, command

    default_command = config.get("defaultCommand")
    if default_command is None:
        return None
    if not all(isinstance(argument, str) for argument in default_command):
        raise HandlerError("config field 'defaultCommand' must contain only strings")
    return "default", default_command


def expand_arguments(arguments: list[str], notification: dict[str, str]) -> list[str]:
    expanded = []
    for argument in arguments:
        try:
            expanded.append(argument.format_map(notification))
        except KeyError as error:
            raise HandlerError(
                f"command template references unknown field {error.args[0]!r}"
            ) from error
        except ValueError as error:
            raise HandlerError(f"invalid command template {argument!r}: {error}") from error
    return expanded


def build_draw_command(
    config: dict[str, Any],
    config_path: Path,
    arguments: list[str],
    notification: dict[str, str],
) -> tuple[list[str], Path]:
    python_executable = config.get("pythonExecutable", sys.executable)
    draw_script_value = config.get("drawScript", "../draw.py")
    if not isinstance(python_executable, str) or not python_executable:
        raise HandlerError("config field 'pythonExecutable' must be a non-empty string")
    if not isinstance(draw_script_value, str) or not draw_script_value:
        raise HandlerError("config field 'drawScript' must be a non-empty string")

    draw_script = Path(draw_script_value).expanduser()
    if not draw_script.is_absolute():
        draw_script = (config_path.parent / draw_script).resolve()
    if not draw_script.is_file():
        raise HandlerError(f"draw script does not exist: {draw_script}")

    command = [python_executable, str(draw_script)]
    command.extend(expand_arguments(arguments, notification))
    return command, draw_script.parent


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Filter one notification JSON object and run draw.py"
    )
    parser.add_argument(
        "notification",
        help="notification JSON object, or '-' to read it from stdin",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"configuration file (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the selected command without executing it",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = create_parser().parse_args(argv)
    try:
        notification = load_notification(arguments.notification)
        config_path = arguments.config.expanduser().resolve()
        config = load_config(config_path)
        selected = select_command(config, notification)
        if selected is None:
            print("no matching notification rule", file=sys.stderr)
            return 0

        rule_name, draw_arguments = selected
        command, working_directory = build_draw_command(
            config, config_path, draw_arguments, notification
        )
        print(f"matched {rule_name}: {shlex.join(command)}", file=sys.stderr)
        if arguments.dry_run:
            print(shlex.join(command))
            return 0

        result = subprocess.run(command, cwd=working_directory, check=False)
        return result.returncode
    except HandlerError as error:
        print(f"notification handler: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

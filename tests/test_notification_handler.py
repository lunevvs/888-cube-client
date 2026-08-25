import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "notification_handler", ROOT / "notification-subscriber" / "handle_notification.py"
)
assert SPEC is not None and SPEC.loader is not None
handler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handler)


NOTIFICATION = {
    "datetime": "2026-08-25 13:40:02",
    "appId": "com.example.service",
    "appName": "Service",
    "notificationId": "notification-id",
    "notificationDatetime": "1 минуту назад",
    "notificationHeader": "Progress",
    "notificationBody": "75",
}


class NotificationHandlerTests(unittest.TestCase):
    def test_matches_supported_filters(self):
        rule = {
            "filters": {
                "appId": {"equals": "com.example.service"},
                "notificationHeader": {"contains": "ogre"},
                "notificationBody": {"regex": "^[0-9]+$", "in": ["50", "75"]},
            }
        }
        self.assertTrue(handler.rule_matches(rule, NOTIFICATION))

    def test_rejects_unknown_notification_field(self):
        with self.assertRaisesRegex(handler.HandlerError, "unknown notification field"):
            handler.rule_matches({"filters": {"missing": "value"}}, NOTIFICATION)

    def test_rejects_regex_that_matches_every_notification(self):
        with self.assertRaisesRegex(handler.HandlerError, "matches an empty string"):
            handler.matches_filter("ordinary notification", {"regex": "(warn|)"})

    def test_first_matching_rule_wins(self):
        config = {
            "rules": [
                {
                    "name": "first",
                    "filters": {"appId": "com.example.service"},
                    "command": ["--algorithm", "notification_success"],
                },
                {
                    "name": "second",
                    "filters": {},
                    "command": ["--algorithm", "notification_error"],
                },
            ]
        }
        self.assertEqual(
            handler.select_command(config, NOTIFICATION),
            ("first", ["--algorithm", "notification_success"]),
        )

    def test_expands_notification_fields_without_shell_parsing(self):
        self.assertEqual(
            handler.expand_arguments(
                ["--algorithm-option", "progress={notificationBody}"], NOTIFICATION
            ),
            ["--algorithm-option", "progress=75"],
        )

    def test_dry_run_prints_draw_command(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yaml"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "drawScript": str(ROOT / "draw.py"),
                        "rules": [],
                        "defaultCommand": [
                            "--algorithm",
                            "notification_progress",
                            "-O",
                            "progress={notificationBody}",
                        ],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = handler.main(
                    [json.dumps(NOTIFICATION), "--config", str(config_path), "--dry-run"]
                )

        self.assertEqual(result, 0)
        self.assertIn("notification_progress", stdout.getvalue())
        self.assertIn("progress=75", stdout.getvalue())
        self.assertIn("matched default", stderr.getvalue())

    @patch.object(handler.subprocess, "run")
    def test_returns_draw_exit_code(self, run_mock):
        run_mock.return_value.returncode = 7
        config = {
            "drawScript": str(ROOT / "draw.py"),
            "rules": [],
            "defaultCommand": ["--algorithm", "notification_incoming"],
        }
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yaml"
            config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                result = handler.main(
                    [json.dumps(NOTIFICATION), "--config", str(config_path)]
                )

        self.assertEqual(result, 7)
        run_mock.assert_called_once()
        self.assertFalse(run_mock.call_args.kwargs["check"])


if __name__ == "__main__":
    unittest.main()

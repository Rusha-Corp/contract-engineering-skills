import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "hooks/droid-session-start.sh"


class DroidAdapterTests(unittest.TestCase):
    def test_plugin_manifest_and_hook_are_bounded(self) -> None:
        root = ROOT
        manifest = json.loads((root / ".factory-plugin/plugin.json").read_text())
        self.assertEqual(manifest["name"], "contract-engineering-skills")
        self.assertNotIn("hooks", manifest)
        hook = json.loads((root / "hooks/hooks.json").read_text())
        command = hook["SessionStart"][0]["hooks"][0]
        self.assertEqual(command["timeout"], 10)
        self.assertEqual(
            command["command"],
            'node "${DROID_PLUGIN_ROOT}/hooks/droid-session-start.mjs"',
        )

    def _run(
        self, fake_bin: Path, *, timeout: str = "1", tm_command: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PATH"] = f"{fake_bin}:/usr/local/bin:/usr/bin:/bin"
        env["TM_CONTEXT_TIMEOUT_SECONDS"] = timeout
        env.pop("TASK_MASTER_PACKET_ID", None)
        if tm_command is not None:
            env["TM_CONTEXT_COMMAND"] = tm_command
        else:
            env.pop("TM_CONTEXT_COMMAND", None)
        return subprocess.run(
            [str(SCRIPT)],
            text=True,
            capture_output=True,
            timeout=10,
            env=env,
            input='{"session_id":"factory-session"}',
        )

    def _run_node(
        self, fake_bin: Path, *, timeout: str = "1", tm_command: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PATH"] = f"{fake_bin}:/usr/local/bin:/usr/bin:/bin"
        env["TM_CONTEXT_TIMEOUT_SECONDS"] = timeout
        env.pop("TASK_MASTER_PACKET_ID", None)
        if tm_command is not None:
            env["TM_CONTEXT_COMMAND"] = tm_command
        else:
            env.pop("TM_CONTEXT_COMMAND", None)
        return subprocess.run(
            [shutil.which("node") or "node", str(SCRIPT.with_suffix(".mjs"))],
            text=True,
            capture_output=True,
            timeout=10,
            env=env,
            input='{"session_id":"factory-session"}',
        )

    def test_node_launcher_enforces_deadline_without_timeout_utility(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            (fake_bin / "tm").write_text("#!/bin/sh\nexec sleep 2\n")
            (fake_bin / "tm").chmod(0o755)
            started = time.monotonic()
            result = self._run_node(fake_bin)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertLess(time.monotonic() - started, 1.8)

    def test_node_launcher_rejects_invalid_timeout_and_preserves_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            capture = root / "input.json"
            (fake_bin / "tm").write_text(
                f"#!/bin/sh\ncat > {capture}\nprintf '%s' '{{\"hookSpecificOutput\":{{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"portable\"}}}}'\n"
            )
            (fake_bin / "tm").chmod(0o755)
            result = self._run_node(fake_bin, timeout="0")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertFalse(capture.exists())
            result = self._run_node(fake_bin, timeout="2")
            self.assertEqual(result.returncode, 0)
            self.assertIn("portable", result.stdout)
            self.assertEqual(
                json.loads(capture.read_text()), {"session_id": "factory-session"}
            )

    def test_session_start_injects_context_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            capture = root / "input.json"
            (fake_bin / "tm").write_text(
                f"#!/bin/sh\ncat > {capture}\nprintf '%s' '{{\"hookSpecificOutput\":{{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"bounded packet context\"}}}}'\n"
            )
            (fake_bin / "tm").chmod(0o755)
            result = self._run(fake_bin)
            self.assertEqual(result.returncode, 0)
            self.assertIn("bounded packet context", result.stdout)
            self.assertEqual(
                json.loads(capture.read_text()), {"session_id": "factory-session"}
            )

    def test_invalid_timeout_and_failed_commands_are_advisory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake_bin = Path(directory) / "bin"
            fake_bin.mkdir()
            (fake_bin / "tm").write_text("#!/bin/sh\nexit 7\n")
            (fake_bin / "tm").chmod(0o755)
            for timeout in ("0", "11", "bad"):
                result = self._run(fake_bin, timeout=timeout)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
            result = self._run(fake_bin)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")

    def test_absolute_telemetry_command_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            tm = root / "custom tm"
            tm.write_text("#!/bin/sh\nprintf '%s' '{\"ok\":true}'\n")
            tm.chmod(0o755)
            result = self._run(fake_bin, tm_command=str(tm))
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '{"ok":true}')


if __name__ == "__main__":
    unittest.main()

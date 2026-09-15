#!/usr/bin/env python3
"""Tests for offline design artifact validation and preview serving."""

from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen


ROOT = Path(__file__).parents[1]


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preview = load_module("preview_design", "preview-design.py")
sanitize = load_module("sanitize_svg", "sanitize-svg.py")
render = load_module("render_mermaid", "render-mermaid.py")


class DesignPreviewTests(unittest.TestCase):
    def test_preview_binds_localhost_and_serves_only_design_root(self):
        root = ROOT / "tests/fixtures/designs/ui-basic"
        server, url = preview.create_preview_server(root)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            self.assertEqual(url.split("/")[2].split(":")[0], "127.0.0.1")
            with urlopen(url, timeout=2) as response:
                self.assertIn(b"Safe design preview", response.read())
            with self.assertRaises(HTTPError) as error:
                urlopen(url + "missing.html", timeout=2)
            self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_manifest_rejects_path_traversal_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "design"
            outside = Path(temporary) / "outside.txt"
            root.mkdir()
            outside.write_text("outside", encoding="utf-8")
            with self.assertRaises(preview.PreviewError):
                preview.validate_artifact_manifest(
                    root, [{"path": "../outside.txt", "kind": "html", "sha256": "x"}]
                )
            (root / "escape.html").symlink_to(outside)
            with self.assertRaises(preview.PreviewError):
                preview.validate_artifact_manifest(
                    root, [{"path": "escape.html", "kind": "html", "sha256": "x"}]
                )

    def test_manifest_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "artifact.mmd"
            path.write_text("flowchart LR\nA --> B\n", encoding="utf-8")
            with self.assertRaises(preview.PreviewError):
                preview.validate_artifact_manifest(
                    root, [{"path": "artifact.mmd", "kind": "mermaid", "sha256": "0" * 64}]
                )

    def test_svg_sanitizer_rejects_scripts_external_refs_and_handlers(self):
        unsafe = ROOT / "tests/fixtures/designs/unsafe/scripted.svg"
        with self.assertRaises(sanitize.SafetyError):
            sanitize.sanitize_svg(unsafe)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "handler.svg"
            path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" onload="x"></svg>',
                encoding="utf-8",
            )
            with self.assertRaises(sanitize.SafetyError):
                sanitize.sanitize_svg(path)

    def test_html_policy_rejects_remote_scripts_forms_and_network_urls(self):
        with self.assertRaises(preview.PreviewError):
            preview.validate_html(ROOT / "tests/fixtures/designs/unsafe/remote.html")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "unsafe.html"
            path.write_text("<form action='/submit'></form>", encoding="utf-8")
            with self.assertRaises(preview.PreviewError):
                preview.validate_html(path)

    def test_missing_renderer_does_not_report_visual_review_passed(self):
        source = ROOT / "tests/fixtures/designs/architecture-basic/system.mmd"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "system.svg"
            with self.assertRaises(RuntimeError):
                render.render_mermaid(source, output, cli="definitely-not-installed")
            self.assertFalse(output.exists())

    def test_safe_fixture_hashes_are_stable(self):
        path = ROOT / "tests/fixtures/designs/ui-basic/index.html"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "4cb35045c1d60325151e3200304df7ae9c16d7a4432e855274bcdd402287e676",
        )


if __name__ == "__main__":
    unittest.main()

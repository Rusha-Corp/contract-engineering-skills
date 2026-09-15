#!/usr/bin/env python3
"""Validate and serve a design directory on localhost only."""

from __future__ import annotations

import argparse
import hashlib
import html.parser
import http.server
import json
import re
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

import yaml

from importlib.util import module_from_spec, spec_from_file_location

_SANITIZER_SPEC = spec_from_file_location(
    "sanitize_svg", Path(__file__).with_name("sanitize-svg.py")
)
assert _SANITIZER_SPEC and _SANITIZER_SPEC.loader
_SANITIZER = module_from_spec(_SANITIZER_SPEC)
_SANITIZER_SPEC.loader.exec_module(_SANITIZER)
SafetyError = _SANITIZER.SafetyError
sanitize_svg = _SANITIZER.sanitize_svg

MAX_HTML_BYTES = 2 * 1024 * 1024
REMOTE_URL = re.compile(r"(?:(?:https?:)?//|data:|javascript:)", re.IGNORECASE)
FORBIDDEN_HTML_TAGS = {"script", "form", "iframe", "object", "embed", "applet"}
FORBIDDEN_HTML_TEXT = (
    "localstorage",
    "sessionstorage",
    "document.cookie",
    "fetch(",
    "xmlhttprequest",
    "websocket",
    "sendbeacon",
)


class PreviewError(ValueError):
    """Raised when a design cannot be safely previewed."""


class _HtmlPolicy(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[str] = []
        self._script_src: str | None = None

    def _check_attrs(self, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            lowered = name.lower()
            if lowered.startswith("on"):
                self.errors.append("event handler")
            if lowered in {"action", "src", "href", "poster"} and value:
                if REMOTE_URL.search(value) or value.lower().startswith("file:"):
                    self.errors.append("remote URL")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered_tag = tag.lower()
        if lowered_tag == "script":
            src = dict(attrs).get("src")
            if not src or REMOTE_URL.search(src) or src.lower().startswith(("file:", "/")):
                self.errors.append("inline or remote script")
            else:
                self._script_src = src
        elif lowered_tag in FORBIDDEN_HTML_TAGS - {"script"}:
            self.errors.append(f"forbidden tag: {tag.lower()}")
        self._check_attrs(attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        lowered = data.lower()
        if self._script_src is not None and data.strip():
            self.errors.append("inline script")
        if any(marker in lowered for marker in FORBIDDEN_HTML_TEXT):
            self.errors.append("credential, storage, or network API")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            self._script_src = None


def validate_html(path: Path) -> None:
    raw = path.read_bytes()
    if len(raw) > MAX_HTML_BYTES:
        raise PreviewError(f"HTML exceeds {MAX_HTML_BYTES} bytes")
    text = raw.decode("utf-8")
    if REMOTE_URL.search(text):
        raise PreviewError("HTML contains a remote or data URL")
    parser = _HtmlPolicy()
    parser.feed(text)
    parser.close()
    if parser.errors:
        raise PreviewError("HTML violates offline policy")


def _assert_inside(root: Path, candidate: Path) -> Path:
    root = root.resolve()
    if candidate.is_absolute():
        raise PreviewError("artifact path must be relative")
    raw = root / candidate
    for parent in [raw, *raw.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise PreviewError("symlinked artifact path is not allowed")
    resolved = raw.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PreviewError("artifact path escapes design root") from exc
    return resolved


def validate_artifact_manifest(
    design_root: Path, artifacts: list[dict[str, Any]]
) -> list[Path]:
    """Resolve, safety-check, and hash every manifest artifact."""
    root = design_root.resolve()
    if not root.is_dir():
        raise PreviewError("design root must be a directory")
    paths: list[Path] = []
    seen: set[str] = set()
    for artifact in artifacts:
        relative = Path(str(artifact.get("path", "")))
        key = relative.as_posix()
        if not key or key in seen:
            raise PreviewError("manifest contains an empty or duplicate path")
        seen.add(key)
        path = _assert_inside(root, relative)
        if not path.is_file():
            raise PreviewError("manifest references a missing artifact")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != artifact.get("sha256"):
            raise PreviewError("artifact hash does not match manifest")
        kind = artifact.get("kind")
        if kind == "html":
            validate_html(path)
        elif kind == "svg":
            sanitize_svg(path)
        elif kind not in {"mermaid", "architecture", "requirements", "tradeoffs"}:
            raise PreviewError("manifest contains an unsupported artifact kind")
        paths.append(path)
    return paths


def _load_manifest(root: Path, design_file: Path | None) -> tuple[dict[str, Any], list[Path]]:
    path = design_file or root / "design.yaml"
    try:
        design = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PreviewError("design manifest could not be loaded") from exc
    if not isinstance(design, dict) or not isinstance(design.get("artifacts"), list):
        raise PreviewError("design manifest has no artifact list")
    return design, validate_artifact_manifest(root, design["artifacts"])


class _PreviewHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str, allowed: set[str], **kwargs: Any) -> None:
        self.allowed = allowed
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self) -> None:
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        relative = Path(path.lstrip("/"))
        if path == "/":
            relative = Path("index.html")
        if relative.as_posix() not in self.allowed:
            self.send_error(404, "artifact not in validated manifest")
            return
        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        return


def create_preview_server(
    root: Path, port: int = 0, design_file: Path | None = None
) -> tuple[http.server.ThreadingHTTPServer, str]:
    """Create a localhost-only server after manifest validation."""
    root = root.resolve()
    _, paths = _load_manifest(root, design_file)
    allowed = {path.relative_to(root).as_posix() for path in paths}
    handler = lambda *args, **kwargs: _PreviewHandler(  # noqa: E731
        *args, directory=str(root), allowed=allowed, **kwargs
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    return server, f"http://127.0.0.1:{server.server_port}/"


def start_preview(
    root: Path, port: int = 0, no_open: bool = False, design_file: Path | None = None
) -> None:
    server, url = create_preview_server(root, port, design_file)
    print(f"Preview available at {url}")
    print("Press Ctrl-C to stop the foreground preview server.")
    if not no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--design", type=Path)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    try:
        start_preview(args.root, args.port, args.no_open, args.design)
    except (OSError, PreviewError, SafetyError) as exc:
        print(f"preview blocked: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

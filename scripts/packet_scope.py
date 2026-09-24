#!/usr/bin/env python3
"""Map changed paths to the packet scopes that claim them."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import yaml


def path_matches(candidate: str, rule: str) -> bool:
    candidate = candidate.rstrip("/")
    rule = str(rule).rstrip("/")
    return candidate == rule or candidate.startswith(rule + "/")


def packet_scope(packet_path: Path) -> list[str]:
    packet = yaml.safe_load(packet_path.read_text(encoding="utf-8"))
    return [str(rule) for rule in packet["scope"]["in"]]


def claimed_paths(packet_path: Path, changed_paths: Iterable[str]) -> list[str]:
    rules = packet_scope(packet_path)
    return [
        path
        for path in changed_paths
        if any(path_matches(path, rule) for rule in rules)
    ]


def unclaimed_paths(
    packet_paths: Iterable[Path], changed_paths: Iterable[str]
) -> list[str]:
    packets = list(packet_paths)
    return [
        path
        for path in changed_paths
        if not any(
            path_matches(path, rule)
            for packet in packets
            for rule in packet_scope(packet)
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", action="append", type=Path, required=True)
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--unclaimed", action="store_true")
    args = parser.parse_args()

    if args.unclaimed:
        paths = unclaimed_paths(args.packet, args.changed_path)
    else:
        if len(args.packet) != 1:
            parser.error("exactly one --packet is required without --unclaimed")
        paths = claimed_paths(args.packet[0], args.changed_path)
    if paths:
        print("\n".join(paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

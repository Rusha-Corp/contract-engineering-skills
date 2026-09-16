"""Canonical Contract Engineering identifier grammar."""

import re

PROGRAM_COMPONENT = r"[A-Z][A-Z0-9]*"
TASK_PATTERN = rf"^(?:{PROGRAM_COMPONENT}-)+T[0-9]{{3}}$"
PACKET_PATTERN = rf"^(?:{PROGRAM_COMPONENT}-)+T[0-9]{{3}}-P[0-9]{{3}}$"

TASK_ID = re.compile(TASK_PATTERN)
PACKET_ID = re.compile(PACKET_PATTERN)


def is_task_identifier(value: object) -> bool:
    return isinstance(value, str) and TASK_ID.fullmatch(value) is not None


def is_packet_identifier(value: object) -> bool:
    return isinstance(value, str) and PACKET_ID.fullmatch(value) is not None


def is_task_or_packet_identifier(value: object) -> bool:
    return is_task_identifier(value) or is_packet_identifier(value)

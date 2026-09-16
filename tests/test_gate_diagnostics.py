"""Tests for structured gate diagnostics and adapter conformance (CENG-T013-P005)."""
import json
import unittest

from scripts.gate_diagnostics import (
    DiagnosticEnvelope,
    DiagnosticCode,
    emit_diagnostic,
    format_diagnostic,
    ADAPTER_CONTRACT_FIELDS,
    conform_adapter,
    SECURITY_CODES,
)


class DiagnosticEnvelopeTests(unittest.TestCase):
    """AC001: Gate failures have stable machine-readable codes and remediation fields."""

    def test_all_codes_are_stable_strings(self):
        for code in DiagnosticCode:
            self.assertIsInstance(code.value, str)
            self.assertTrue(code.value.startswith("GATE-"))
            # Code must be machine-readable: uppercase, hyphens, digits only
            for ch in code.value:
                self.assertIn(ch, "GATE-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    def test_every_diagnostic_has_remediation(self):
        for code in DiagnosticCode:
            diag = emit_diagnostic(
                code=code,
                packet_id="CENG-T013-P005",
                gate_name="test-gate",
                message="test failure",
            )
            self.assertTrue(diag.remediation, f"{code.value} has empty remediation")

    def test_envelope_has_required_fields(self):
        diag = emit_diagnostic(
            code=DiagnosticCode.SCOPE_VIOLATION,
            packet_id="CENG-T013-P005",
            gate_name="scope-gate",
            message="packet edited outside scope.in",
        )
        self.assertEqual(diag.code, "GATE-SCOPE-001")
        self.assertIn(diag.severity, ("error", "warning", "info"))
        self.assertTrue(diag.message)
        self.assertTrue(diag.remediation)
        self.assertEqual(diag.packet_id, "CENG-T013-P005")
        self.assertEqual(diag.gate_name, "scope-gate")
        self.assertIsInstance(diag.blocking, bool)


class FailClosedTests(unittest.TestCase):
    """AC003: Security failures remain fail-closed."""

    def test_security_codes_are_always_blocking(self):
        for code in SECURITY_CODES:
            diag = emit_diagnostic(
                code=code,
                packet_id="CENG-T013-P005",
                gate_name="security-gate",
                message="security failure",
            )
            self.assertTrue(diag.blocking, f"{code.value} must be blocking (fail-closed)")

    def test_security_cannot_be_downgraded_to_non_blocking(self):
        diag = emit_diagnostic(
            code=DiagnosticCode.SECURITY_FINDING,
            packet_id="CENG-T013-P005",
            gate_name="security-gate",
            message="critical vulnerability found",
            blocking=False,  # attempt to downgrade
        )
        self.assertTrue(diag.blocking, "security diagnostic must remain blocking despite downgrade attempt")


class AdapterConformanceTests(unittest.TestCase):
    """AC002: Adapters conform to one diagnostic contract."""

    def test_all_adapters_emit_same_required_fields(self):
        adapters = ["factory-droid", "generic", "hermes"]
        for adapter_name in adapters:
            output = conform_adapter(
                adapter_name=adapter_name,
                code=DiagnosticCode.MISSING_EVIDENCE,
                packet_id="CENG-T013-P005",
                gate_name="evidence-gate",
                message="evidence record missing",
            )
            parsed = json.loads(output) if isinstance(output, str) else output
            for field in ADAPTER_CONTRACT_FIELDS:
                self.assertIn(field, parsed, f"{adapter_name} missing required field: {field}")

    def test_adapter_does_not_hide_gate_failure(self):
        """An adapter must not hide or downgrade a gate failure."""
        for adapter_name in ["factory-droid", "generic", "hermes"]:
            output = conform_adapter(
                adapter_name=adapter_name,
                code=DiagnosticCode.STATE_VIOLATION,
                packet_id="CENG-T013-P005",
                gate_name="state-gate",
                message="illegal state transition",
            )
            parsed = json.loads(output) if isinstance(output, str) else output
            self.assertTrue(parsed["blocking"], f"{adapter_name} must not hide blocking status")

    def test_adapter_preserves_security_blocking(self):
        for adapter_name in ["factory-droid", "generic", "hermes"]:
            output = conform_adapter(
                adapter_name=adapter_name,
                code=DiagnosticCode.SECURITY_FINDING,
                packet_id="CENG-T013-P005",
                gate_name="security-gate",
                message="critical security finding",
            )
            parsed = json.loads(output) if isinstance(output, str) else output
            self.assertEqual(parsed["severity"], "error")
            self.assertTrue(parsed["blocking"])


class FormatTests(unittest.TestCase):
    """Diagnostic formatting for different outputs."""

    def test_json_format_is_machine_readable(self):
        diag = emit_diagnostic(
            code=DiagnosticCode.HASH_MISMATCH,
            packet_id="CENG-T013-P005",
            gate_name="hash-gate",
            message="content hash mismatch",
        )
        formatted = format_diagnostic(diag, "json")
        parsed = json.loads(formatted)
        self.assertEqual(parsed["code"], "GATE-HASH-001")

    def test_human_format_is_readable(self):
        diag = emit_diagnostic(
            code=DiagnosticCode.SCOPE_VIOLATION,
            packet_id="CENG-T013-P005",
            gate_name="scope-gate",
            message="scope violation",
        )
        formatted = format_diagnostic(diag, "human")
        self.assertIn("GATE-SCOPE-001", formatted)
        self.assertIn("scope violation", formatted)


if __name__ == "__main__":
    unittest.main()

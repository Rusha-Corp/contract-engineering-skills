import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gate_diagnostics", ROOT / "scripts" / "gate_diagnostics.py"
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class GateDiagnosticTests(unittest.TestCase):
    def test_codes_are_stable_machine_readable(self):
        self.assertTrue(module.DIAGNOSTIC_CODES)
        for code in module.DIAGNOSTIC_CODES:
            self.assertRegex(code, r"^GATE-[A-Z]+-\d{3}$")

    def test_every_code_has_remediation_and_security_blocks(self):
        for code in module.DIAGNOSTIC_CODES:
            diagnostic = module.emit_diagnostic(
                code, "failure", ["fix the failure"], packet_id="CENG-T013-P005",
                gate_name="test",
            )
            self.assertTrue(diagnostic.remediation)
            self.assertIsInstance(diagnostic.blocking, bool)
            if code in module.SECURITY_CODES:
                self.assertTrue(diagnostic.blocking)

    def test_envelope_round_trips_and_formats(self):
        diagnostic = module.emit_diagnostic(
            "GATE-SCOPE-001", "out of scope", ["remove the change"],
            packet_id="CENG-T013-P005", gate_name="scope",
        )
        self.assertEqual(set(module.REQUIRED_FIELDS), set(diagnostic.to_dict()))
        self.assertIn("out of scope", module.format_diagnostic(diagnostic, "human"))
        self.assertIn('"code": "GATE-SCOPE-001"', module.format_diagnostic(diagnostic, "json"))
        self.assertIn("GATE-SCOPE-001", module.format_diagnostic(diagnostic, "markdown"))

    def test_security_cannot_be_downgraded(self):
        diagnostic = module.emit_diagnostic(
            "GATE-SECURITY-001", "security failure", ["restore approval"],
            severity="warning", blocking=False,
        )
        self.assertEqual("error", diagnostic.severity)
        self.assertTrue(diagnostic.blocking)

    def test_all_adapters_use_same_contract(self):
        adapter_dirs = ("factory-droid", "generic", "hermes")
        envelopes = []
        for name in adapter_dirs:
            path = ROOT / "adapters" / name / "diagnostics.py"
            spec = importlib.util.spec_from_file_location(f"{name}_diagnostics", path)
            self.assertIsNotNone(spec)
            assert spec and spec.loader
            adapter = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(adapter)
            result = adapter.emit_diagnostic(
                "GATE-SECURITY-001", "denied", ["obtain approval"],
                packet_id="CENG-T013-P005", gate_name="security",
            )
            envelopes.append(result.to_dict())
            self.assertEqual(set(module.REQUIRED_FIELDS), set(result.to_dict()))
            self.assertTrue(result.blocking)
        self.assertEqual(envelopes[0], envelopes[1])
        self.assertEqual(envelopes[1], envelopes[2])


if __name__ == "__main__":
    unittest.main()

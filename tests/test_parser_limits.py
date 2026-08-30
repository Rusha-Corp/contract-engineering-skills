import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate-contract-records.py"
SPEC = importlib.util.spec_from_file_location("validate_contract_records", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ParserLimitTests(unittest.TestCase):
    def load(self, content: str) -> object:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            return validator.load_yaml(Path(handle.name))

    def assertRejectedWithoutEcho(self, content: str, secret: str = "") -> None:
        with self.assertRaises(ValueError) as context:
            self.load(content)
        if secret:
            self.assertNotIn(secret, str(context.exception))

    def test_valid_yaml_remains_supported(self) -> None:
        self.assertEqual(self.load("packet_id: TEST-T001-P001\nitems:\n  - safe\n"), {
            "packet_id": "TEST-T001-P001",
            "items": ["safe"],
        })

    def test_oversized_yaml_is_rejected(self) -> None:
        self.assertRejectedWithoutEcho(
            "payload: " + ("x" * validator.MAX_YAML_BYTES),
            "synthetic-secret-value",
        )

    def test_deep_yaml_is_rejected(self) -> None:
        nested = "value: safe\n"
        for _ in range(validator.MAX_YAML_DEPTH + 1):
            nested = "level:\n  " + nested.replace("\n", "\n  ").rstrip() + "\n"
        self.assertRejectedWithoutEcho(nested)

    def test_alias_expansion_is_rejected(self) -> None:
        aliases = "root: &root\n  value: safe\nitems:\n"
        aliases += "  - *root\n" * (validator.MAX_YAML_ALIASES + 1)
        self.assertRejectedWithoutEcho(aliases)

    def test_malformed_yaml_is_rejected_without_echo(self) -> None:
        self.assertRejectedWithoutEcho(
            "token: synthetic-secret-value\nbroken: [unclosed",
            "synthetic-secret-value",
        )


if __name__ == "__main__":
    unittest.main()

"""Factory Droid adapter implementation of the shared diagnostic contract."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from gate_diagnostics import DiagnosticEnvelope, emit_diagnostic, format_diagnostic

__all__ = ["DiagnosticEnvelope", "emit_diagnostic", "format_diagnostic"]

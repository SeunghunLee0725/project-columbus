import importlib.util
from pathlib import Path

import pytest


LEGACY_DIR = Path("research/01_ontology")


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("filename", "module_name"),
    [
        ("causal_reasoning_engine.py", "legacy_causal_reasoning_engine"),
        ("causal_knowledge_base.py", "legacy_causal_knowledge_base"),
    ],
)
def test_legacy_scripts_import_without_runtime_pip_install(monkeypatch, filename, module_name):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("legacy module attempted runtime dependency installation")

    import subprocess

    monkeypatch.setattr(subprocess, "check_call", fail_if_called)

    module = _load_module(LEGACY_DIR / filename, module_name)

    assert module is not None


def test_production_calibrator_replaces_legacy_entrypoint_requirement():
    from project_columbus.calibration.evidence_calibrator import EvidenceCalibrator

    assert EvidenceCalibrator is not None

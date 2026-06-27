# Project Columbus Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current ontology/reasoning research prototype into a reproducible, tested, packageable Python knowledge-reasoning system suitable for research-platform production use.

**Architecture:** Keep research artifacts under `research/` as source data and legacy entry points, while introducing a focused `src/project_columbus/` package for validated ontology loading, causal reasoning, calibration, CLI, and later API service boundaries. Every production behavior is introduced test-first and backed by deterministic fixtures or snapshot-style assertions.

**Tech Stack:** Python 3.12+, rdflib, networkx, numpy, pandas, pytest, ruff, optional FastAPI in a later API phase.

---

## Current Baseline

- Repository state: no valid initial `HEAD` exists yet, so `git worktree add` cannot be used until an initial commit is created.
- Core ontology: `research/01_ontology/immune_care_ontology.owl`
  - Parses as RDF/XML.
  - `owl:versionInfo`: `0.2.0`.
  - Observed baseline: 821 triples, 109 OWL classes, 14 object properties, 10 datatype properties, 25 named individuals, 19 `ico:CausalPathway` individuals.
- Integrated KG: `research/01_ontology/integrated_knowledge_graph.ttl`
  - Currently fails rdflib Turtle parsing near the end of the file, likely due to truncation or invalid serialization.
- Existing scripts:
  - `research/01_ontology/causal_reasoning_engine.py`
  - `research/01_ontology/causal_knowledge_base.py`
  - `research/01_ontology/ico_evidence_calibrator.py`
  - `research/01_ontology/integrated_sparql_validator.py`
- Current operational risks:
  - No package metadata.
  - No formal tests.
  - No CI.
  - Legacy scripts mix library logic, demo output, dependency installation, and command-line behavior.
  - Some URI resolution paths can produce invalid URI warnings for labels with spaces.
  - `integrated_sparql_validator.py` can serialize `integrated_knowledge_graph.ttl` even when expected PMO/Bridge sources are missing or consistency checks fail.
  - Several legacy SPARQL queries are assembled with direct string interpolation, so production query APIs need input normalization, escaping, and tests for malformed labels/URIs/numeric thresholds.
  - Multi-hop reasoning semantics are not yet defined consistently: legacy chain search multiplies absolute correlations, while enrichment preserves signed composite correlations.

## File Structure Target

Create or modify these files over the hardening sequence:

- Create: `pyproject.toml`
  - Package metadata, dependencies, pytest config, ruff config, CLI entry point.
- Modify: `requirements.txt`
  - Keep compatible with package dependencies for users who still install via pip requirements.
- Create: `src/project_columbus/__init__.py`
- Create: `src/project_columbus/ontology/__init__.py`
- Create: `src/project_columbus/ontology/namespaces.py`
  - Central namespace constants.
- Create: `src/project_columbus/ontology/models.py`
  - Typed dataclasses for ontology stats, validation issues, causal pathways.
- Create: `src/project_columbus/ontology/loader.py`
  - Graph loading, label caches, safe URI resolution.
- Create: `src/project_columbus/ontology/validator.py`
  - OWL/TTL parse checks and structural ontology validation.
- Create: `src/project_columbus/reasoning/__init__.py`
- Create: `src/project_columbus/reasoning/engine.py`
  - Productionized causal graph queries migrated from legacy code.
- Create: `src/project_columbus/cli.py`
  - CLI commands for validation and initial smoke queries.
- Create: `tests/fixtures/README.md`
  - Fixture policy and baseline assumptions.
- Create: `tests/ontology/test_loader.py`
- Create: `tests/ontology/test_validator.py`
- Create: `tests/reasoning/test_engine.py`
- Create later: `src/project_columbus/calibration/evidence_calibrator.py`
- Create later: `src/project_columbus/api/app.py`

Legacy files under `research/01_ontology/` remain in place during the first hardening pass. After parity tests are green, replace their internals with wrappers or mark them as legacy CLI demos.

---

## Task 1: Packaging And Test Harness

**Files:**
- Create: `pyproject.toml`
- Create: `src/project_columbus/__init__.py`
- Create: `tests/fixtures/README.md`

- [x] **Step 1: Write the failing packaging smoke test**

Create `tests/test_package_import.py`:

```python
def test_project_columbus_imports():
    import project_columbus

    assert project_columbus.__version__
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_package_import.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'project_columbus'`.

- [x] **Step 3: Add minimal package metadata and package init**

Add `pyproject.toml` with:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "project-columbus"
version = "0.1.0"
description = "Production hardening package for Project Columbus immune care ontology reasoning."
requires-python = ">=3.12"
dependencies = [
  "numpy>=1.24",
  "pandas>=2.0",
  "rdflib>=7.0",
  "networkx>=3.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-cov>=5.0",
  "ruff>=0.5",
]

[project.scripts]
columbus = "project_columbus.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py312"
```

Add `src/project_columbus/__init__.py`:

```python
"""Project Columbus ontology reasoning package."""

__version__ = "0.1.0"
```

- [x] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_package_import.py -q
```

Expected: PASS.

- [x] **Step 5: Run initial full test discovery**

Run:

```bash
pytest -q
```

Expected: at least the import test passes. No unrelated tests should be collected from research scripts.

---

## Task 2: Ontology Loader Baseline

**Files:**
- Create: `src/project_columbus/ontology/namespaces.py`
- Create: `src/project_columbus/ontology/models.py`
- Create: `src/project_columbus/ontology/loader.py`
- Create: `tests/ontology/test_loader.py`

- [x] **Step 1: Write failing tests for OWL loading and stats**

Test behaviors:

```python
from pathlib import Path

from project_columbus.ontology.loader import OntologyLoader


OWL_PATH = Path("research/01_ontology/immune_care_ontology.owl")


def test_loads_core_owl_and_reports_baseline_stats():
    repo = OntologyLoader().load(OWL_PATH, rdf_format="xml")

    stats = repo.stats()

    assert stats.triples == 821
    assert stats.owl_classes == 109
    assert stats.object_properties == 14
    assert stats.datatype_properties == 10
    assert stats.named_individuals == 25
    assert stats.causal_pathways == 19
    assert stats.version_info == ["0.2.0"]


def test_resolves_labels_without_building_invalid_space_uris():
    repo = OntologyLoader().load(OWL_PATH, rdf_format="xml")

    assert repo.resolve("Nitric Oxide").endswith("#NitricOxide")
    assert repo.resolve("Hydroxyl Radical").endswith("#HydroxylRadical")
    assert repo.resolve("PM2.5").endswith("#PM2_5")
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/ontology/test_loader.py -q
```

Expected: FAIL because loader module does not exist.

- [x] **Step 3: Implement minimal loader**

Implementation requirements:

- `OntologyStats` dataclass.
- `OntologyRepository` with:
  - `graph`
  - `label_by_uri`
  - `korean_label_by_uri`
  - `uri_by_label`
  - `stats()`
  - `resolve(name: str) -> str | None`
  - `label(uri: str, lang: str = "en") -> str`
- `OntologyLoader.load(path: Path, rdf_format: str | None = None)`.
- URI resolution order:
  - full URI if present in graph;
  - exact English/Korean label match;
  - exact safe ICO local name;
  - known feature alias map for `PM2.5`, `pm25`, `Nitric Oxide`, `Hydroxyl Radical`;
  - never create a URI with spaces.

- [x] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/ontology/test_loader.py -q
```

Expected: PASS.

---

## Task 3: Ontology Structural Validator

**Files:**
- Create: `src/project_columbus/ontology/validator.py`
- Create: `tests/ontology/test_validator.py`

- [x] **Step 1: Write failing validation tests**

Required behaviors:

```python
from pathlib import Path

from project_columbus.ontology.validator import OntologyValidator


OWL_PATH = Path("research/01_ontology/immune_care_ontology.owl")
BROKEN_TTL = Path("research/01_ontology/integrated_knowledge_graph.ttl")


def test_core_owl_validation_passes():
    report = OntologyValidator().validate_file(OWL_PATH, rdf_format="xml")

    assert report.ok
    assert report.errors == []
    assert report.stats.causal_pathways == 19


def test_broken_integrated_ttl_validation_reports_parse_error():
    report = OntologyValidator().validate_file(BROKEN_TTL, rdf_format="turtle")

    assert not report.ok
    assert any(issue.code == "PARSE_ERROR" for issue in report.errors)
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/ontology/test_validator.py -q
```

Expected: FAIL because validator module does not exist.

- [x] **Step 3: Implement validator**

Validation requirements:

- Return a `ValidationReport` dataclass, not raw exceptions.
- Parse errors must be captured as `ValidationIssue(code="PARSE_ERROR", severity="error", message=...)`.
- Core OWL validation must enforce:
  - at least one `owl:versionInfo`;
  - required classes: `EnvironmentalFactor`, `Biomarker`, `ImmuneDisease`, `CausalPathway`;
  - required object properties: `hasSourceFactor`, `hasTargetFactor`, `involvesPathway`;
  - each `CausalPathway` has source and target except explicitly documented composite/trajectory path exceptions;
  - each `CausalPathway` with correlation has a numeric literal.
  - malformed user-facing labels must not be converted into invalid URIs.

- [x] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/ontology/test_validator.py -q
```

Expected: PASS.

---

## Task 4: CLI Validation Command

**Files:**
- Create: `src/project_columbus/cli.py`
- Create: `tests/test_cli.py`

- [x] **Step 1: Write failing CLI tests**

Test both success and parse failure:

```python
from pathlib import Path

from project_columbus.cli import main


def test_validate_ontology_cli_success(capsys):
    exit_code = main([
        "validate-ontology",
        "research/01_ontology/immune_care_ontology.owl",
        "--format",
        "xml",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK" in captured.out
    assert "causal_pathways=19" in captured.out


def test_validate_ontology_cli_failure(capsys):
    exit_code = main([
        "validate-ontology",
        "research/01_ontology/integrated_knowledge_graph.ttl",
        "--format",
        "turtle",
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "PARSE_ERROR" in captured.out
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_cli.py -q
```

Expected: FAIL because CLI module does not exist.

- [x] **Step 3: Implement minimal CLI**

CLI requirements:

- `main(argv: list[str] | None = None) -> int`.
- `validate-ontology PATH --format xml|turtle`.
- Print one-line summary on success:
  - `OK triples=821 classes=109 causal_pathways=19 version=0.2.0`
- Print validation issue lines on failure.
- Do not call `sys.exit()` inside tests; return exit code.

- [x] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_cli.py -q
```

Expected: PASS.

---

## Task 5: Causal Reasoning Engine Parity

**Files:**
- Create: `src/project_columbus/reasoning/engine.py`
- Create: `tests/reasoning/test_engine.py`

- [x] **Step 1: Write failing parity tests**

Test behaviors:

```python
from pathlib import Path

from project_columbus.ontology.loader import OntologyLoader
from project_columbus.reasoning.engine import CausalReasoningEngine


OWL_PATH = Path("research/01_ontology/immune_care_ontology.owl")


def test_pm25_outgoing_pathways_match_legacy_baseline():
    repo = OntologyLoader().load(OWL_PATH, rdf_format="xml")
    engine = CausalReasoningEngine(repo)

    results = engine.env_to_pathway("PM2.5")

    assert len(results) == 6
    assert results[0].causal_path == "PM2.5 → NF-κB → IL-6"
    assert results[0].correlation == 0.52


def test_pm25_to_psoriasis_chain_exists():
    repo = OntologyLoader().load(OWL_PATH, rdf_format="xml")
    engine = CausalReasoningEngine(repo)

    chains = engine.find_causal_chain("PM2.5", "Psoriasis")

    assert len(chains) == 1
    assert chains[0].path == ["PM2.5", "TNF-alpha", "Psoriasis"]
    assert chains[0].cumulative_correlation == 0.225


def test_pm25_to_atopic_dermatitis_chain_absence_is_explicit():
    repo = OntologyLoader().load(OWL_PATH, rdf_format="xml")
    engine = CausalReasoningEngine(repo)

    assert engine.find_causal_chain("PM2.5", "Atopic Dermatitis") == []
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/reasoning/test_engine.py -q
```

Expected: FAIL because production reasoning module does not exist.

- [x] **Step 3: Implement minimal parity engine**

Implementation requirements:

- Build a directed graph from `ico:CausalPathway`.
- Preserve edge attributes:
  - source
  - target
  - pathway
  - label
  - correlation
  - lag_hours
  - evidence
  - source_layer
  - target_layer
- Implement:
  - `env_to_pathway(env_factor: str) -> list[CausalPathwayResult]`
  - `find_causal_chain(source: str, target: str, max_depth: int = 10) -> list[CausalChain]`
- Sort `env_to_pathway` by descending correlation with `None` last.
- Sort causal chains by descending cumulative absolute correlation.
- Document and expose both:
  - `cumulative_abs_correlation` for legacy ranking parity;
  - `signed_correlation_product` for direction-aware interpretation.
- Validate user inputs before any SPARQL string construction. Prefer graph traversal APIs for production query paths; if SPARQL is still needed, escape literals and reject malformed numeric thresholds.

- [x] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/reasoning/test_engine.py -q
```

Expected: PASS.

---

## Task 6: Fix Or Regenerate Integrated Turtle Knowledge Graph

**Files:**
- Modify or regenerate: `research/01_ontology/integrated_knowledge_graph.ttl`
- Create: `tests/ontology/test_integrated_kg.py`
- Optionally create: `src/project_columbus/ontology/integrated_export.py`

- [x] **Step 1: Write failing TTL parse test**

```python
from pathlib import Path

from rdflib import Graph


def test_integrated_knowledge_graph_is_valid_turtle():
    graph = Graph()
    graph.parse(Path("research/01_ontology/integrated_knowledge_graph.ttl"), format="turtle")

    assert len(graph) > 0
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/ontology/test_integrated_kg.py -q
```

Expected: FAIL with current Turtle parse error.

- [x] **Step 3: Fix generation source or regenerate safely**

Preferred approach:

- Load valid sources with rdflib:
  - `research/01_ontology/immune_care_ontology.owl`
  - `research/02_data_pipeline/rdf_output/nhis_disease_instances.ttl` if valid
  - PMO/Bridge files only if present and parseable
- Serialize with `Graph.serialize(format="turtle")`.
- Do not hand-edit large Turtle content.
- If a required source is missing or invalid, hard-fail before writing output.
- If an optional source is missing or invalid, exclude it and write a generation report listing exclusions.
- Write output to a temporary file, parse it back with rdflib, then atomically replace `integrated_knowledge_graph.ttl`.
- Never serialize a new integrated KG when consistency checks fail.

- [x] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/ontology/test_integrated_kg.py -q
```

Expected: PASS.

---

## Task 7: Evidence Calibration Safety

**Files:**
- Create: `src/project_columbus/calibration/__init__.py`
- Create: `src/project_columbus/calibration/evidence_calibrator.py`
- Create: `tests/calibration/test_evidence_calibrator.py`
- Leave legacy: `research/01_ontology/ico_evidence_calibrator.py`

- [x] **Step 1: Write failing tests for non-destructive calibration**

Required behaviors:

- Calibration accepts source OWL and output OWL paths.
- It never overwrites source unless `--in-place` is explicitly passed.
- It creates `EvidenceBasedCorrelation` individuals from small CSV fixtures.
- It writes version `0.3.0` only to the output graph.

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/calibration/test_evidence_calibrator.py -q
```

Expected: FAIL because calibration module does not exist.

- [x] **Step 3: Implement safe calibrator**

Implementation requirements:

- Dataclass `CalibrationSummary`.
- Input validation for required CSV columns.
- Evidence level policy extracted into a pure function:
  - A: `abs(r) > 0.4 and pct_sig > 80`
  - B: `abs(r) > 0.2 and pct_sig > 50`
  - C: otherwise
- Output report includes counts per evidence level.
- Calibration date must be injectable for deterministic tests; default to current date only in CLI/runtime.
- Post-write validation must parse the output RDF/XML and report triple counts before returning success.

- [x] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/calibration/test_evidence_calibrator.py -q
```

Expected: PASS.

---

## Task 8: Legacy Script Compatibility Wrappers

**Files:**
- Modify: `research/01_ontology/causal_reasoning_engine.py`
- Modify: `research/01_ontology/causal_knowledge_base.py`
- Modify: `research/01_ontology/ico_evidence_calibrator.py`
- Create: `tests/legacy/test_legacy_entrypoints.py`

- [x] **Step 1: Write failing compatibility tests**

Required behaviors:

- Legacy scripts import without side effects.
- Legacy scripts no longer install packages at import time.
- Legacy demo execution remains available under `if __name__ == "__main__"`.

- [x] **Step 2: Run tests to verify they fail or expose current side effects**

Run:

```bash
pytest tests/legacy/test_legacy_entrypoints.py -q
```

- [x] **Step 3: Replace internals with wrappers**

Implementation requirements:

- Keep public class/function names where reasonable.
- Delegate to `project_columbus` package.
- Move demo-only output into `main()` functions.

- [x] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/legacy/test_legacy_entrypoints.py -q
```

Expected: PASS.

---

## Task 9: Read-Only API Service

**Files:**
- Modify: `pyproject.toml`
- Create: `src/project_columbus/api/__init__.py`
- Create: `src/project_columbus/api/schemas.py`
- Create: `src/project_columbus/api/app.py`
- Create: `tests/api/test_app.py`

- [x] **Step 1: Write failing API tests**

Endpoints:

- `GET /health`
- `GET /ontology/stats`
- `POST /query/env-to-pathway`
- `POST /reason/causal-chain`

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/api/test_app.py -q
```

- [x] **Step 3: Implement minimal FastAPI app**

Requirements:

- Read-only service.
- Ontology path injected by env var `COLUMBUS_ONTOLOGY_PATH`.
- Startup validates ontology; invalid ontology fails startup.
- Responses include ontology version.

- [x] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/api/test_app.py -q
```

Expected: PASS.

---

## Task 10: CI And Release Validation

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `docs/production_readiness.md`

- [x] **Step 1: Add CI workflow**

Workflow steps:

```yaml
name: CI
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest -q
      - run: columbus validate-ontology research/01_ontology/immune_care_ontology.owl --format xml
```

- [x] **Step 2: Add production readiness doc**

Include:

- Supported commands.
- Ontology artifact policy.
- Known non-goals.
- Current clinical-safety wording limitations.
- How to regenerate integrated KG.

- [x] **Step 3: Run local CI-equivalent verification**

Run:

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest -q
columbus validate-ontology research/01_ontology/immune_care_ontology.owl --format xml
```

Expected: all commands exit 0.

---

## Execution Notes

- Use TDD for every behavior-changing task.
- Do not rewrite large ontology artifacts by hand.
- Do not modify raw data under `data/` during production hardening.
- Keep clinical language conservative: outputs support mechanistic hypothesis and risk explanation, not diagnosis or treatment decisions.
- Do not delete legacy research scripts until compatibility wrappers and tests are in place.
- Because this repository currently lacks a valid `HEAD`, create an initial commit before attempting git worktrees or branch-based workflows.

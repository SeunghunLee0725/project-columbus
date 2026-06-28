# Production Readiness

Project Columbus is currently hardened for research-platform production use of the immune care
ontology and read-only reasoning workflows. It is not a clinical diagnosis or treatment decision
system.

## Supported Commands

```bash
columbus validate-ontology research/01_ontology/immune_care_ontology.owl --format xml
columbus validate-ontology research/01_ontology/integrated_knowledge_graph.ttl --format turtle
columbus export-integrated-kg
columbus generate-nhis-rdf --correlation-csv <correlation_summary.csv>
columbus calibrate-evidence --source-owl research/01_ontology/immune_care_ontology.owl \
  --correlation-csv <correlation_summary.csv> --output-owl <calibrated.owl> --report <report.json>
```

For local development, use:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
ruff check .
```

## Ontology Artifacts

- Canonical core ontology: `research/01_ontology/immune_care_ontology.owl`
- Generated integrated KG: `research/01_ontology/integrated_knowledge_graph.ttl`
- Integrated KG report: `research/01_ontology/integrated_knowledge_graph.report.json`

The integrated KG must be generated from parsed rdflib graphs. Do not hand-edit large Turtle
output. The exporter writes a temporary Turtle file, parses it back, validates it, and atomically
replaces the output.

Optional NHIS RDF input is generated under `research/02_data_pipeline/rdf_output/` with
`columbus generate-nhis-rdf`. That directory is a generated artifact location, so production tests
use small fixtures and the integrated exporter records missing, empty, or invalid optional sources
instead of silently loading them.

## Evidence Calibration

Evidence calibration is non-destructive by default. Use
`project_columbus.calibration.EvidenceCalibrator` to write a new OWL file and JSON report. The
source OWL is not overwritten unless `in_place=True` is explicitly passed.

The same workflow is available through `columbus calibrate-evidence`.

## API

The read-only API is created with:

```python
from project_columbus.api.app import create_app

app = create_app(ontology_path="research/01_ontology/immune_care_ontology.owl")
```

Endpoints:

- `GET /health`
- `GET /ontology/stats`
- `POST /query/env-to-pathway`
- `POST /reason/causal-chain`

Set `COLUMBUS_ONTOLOGY_PATH` to configure the default app instance.

## Known Non-Goals

- No patient-level clinical decision support.
- No diagnosis, prescription, or treatment recommendation.
- No mutable API endpoints.
- No RDF store dependency yet; rdflib file-based operation is the current baseline.

## Current Limitations

- The committed integrated KG currently contains the core OWL only. Local generated NHIS RDF can be
  added by regenerating `nhis_disease_instances.ttl` and then running `columbus export-integrated-kg`.
- Legacy research scripts are retained for compatibility but production code lives under `src/`.
- Clinical language must remain conservative: outputs support mechanistic hypothesis and risk
  explanation only.

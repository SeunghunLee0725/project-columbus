# Artifact Policy

Project Columbus separates production source, reproducible ontology snapshots, and generated
research artifacts.

## Tracked Source

Track these in git:

- `src/project_columbus/` production package code.
- `tests/` automated tests and small deterministic fixtures.
- `research/01_ontology/immune_care_ontology.owl` as the canonical ontology source.
- `research/01_ontology/integrated_knowledge_graph.ttl` and its report while tests depend on the
  reproducible integrated KG snapshot.
- Sanitized research scripts under `research/`.
- Sanitized documentation and Markdown reports.
- Editable diagram sources such as `research/project_architecture.svg`.

## Generated Or Restricted Artifacts

Keep these out of normal git history:

- Raw NHIS/public data under `data/`.
- Processed parquet files under `data/processed/`.
- Data-pipeline reports, plots, RDF exports, and end-to-end run outputs under
  `research/02_data_pipeline/`.
- Model result files under `research/03_ai_model/model_results/`.
- Rendered diagrams that can be regenerated from editable sources.
- IRB/NHIS submission documents containing controlled, private, or institution-specific content.

Use restricted document storage, object storage, DVC, or another artifact store for large or
controlled outputs.

## Knowledge Graph Inputs

`research/02_data_pipeline/rdf_output/nhis_disease_instances.ttl` is an optional integrated KG
input, not a canonical source file. Generate it with:

```bash
columbus generate-nhis-rdf \
  --correlation-csv research/02_data_pipeline/correlation_reports/correlation_summary.csv \
  --output research/02_data_pipeline/rdf_output/nhis_disease_instances.ttl \
  --report research/02_data_pipeline/rdf_output/nhis_disease_instances.report.json
```

The integrated exporter ignores missing optional inputs and rejects empty or invalid optional RDF.
Do not hand-edit Turtle outputs.

## Required Checks

Before committing ontology or KG changes, run:

```bash
ruff check .
python -m pytest -q
columbus validate-ontology research/01_ontology/immune_care_ontology.owl --format xml
columbus validate-ontology research/01_ontology/integrated_knowledge_graph.ttl --format turtle
```

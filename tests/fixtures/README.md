# Test Fixtures

Tests use the checked-in ontology artifacts under `research/` as baseline fixtures until smaller
purpose-built fixtures are introduced.

The canonical baseline for `research/01_ontology/immune_care_ontology.owl` is:

- RDF/XML parseable
- `owl:versionInfo` = `0.2.0`
- 821 triples
- 109 OWL classes
- 19 `ico:CausalPathway` individuals

`research/01_ontology/integrated_knowledge_graph.ttl` is currently a known broken generated
artifact and should fail Turtle validation until regenerated from validated sources.

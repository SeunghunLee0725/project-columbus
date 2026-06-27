from pathlib import Path

from project_columbus.ontology.validator import OntologyValidator


OWL_PATH = Path("research/01_ontology/immune_care_ontology.owl")
INTEGRATED_TTL = Path("research/01_ontology/integrated_knowledge_graph.ttl")


def test_core_owl_validation_passes():
    report = OntologyValidator().validate_file(OWL_PATH, rdf_format="xml")

    assert report.ok
    assert report.errors == []
    assert report.stats is not None
    assert report.stats.causal_pathways == 19


def test_integrated_ttl_validation_passes():
    report = OntologyValidator().validate_file(INTEGRATED_TTL, rdf_format="turtle")

    assert report.ok
    assert report.errors == []
    assert report.stats is not None
    assert report.stats.triples == 821


def test_required_terms_must_have_expected_rdf_types(tmp_path):
    malformed = tmp_path / "malformed.ttl"
    malformed.write_text(
        """
        @prefix ico: <http://purl.obolibrary.org/obo/ICO#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        ico:Ontology owl:versionInfo "test" .

        ico:EnvironmentalFactor a owl:NamedIndividual .
        ico:Biomarker a owl:Class .
        ico:ImmuneDisease a owl:Class .
        ico:CausalPathway a owl:Class .

        ico:hasSourceFactor a owl:DatatypeProperty .
        ico:hasTargetFactor a owl:ObjectProperty .
        ico:involvesPathway a owl:ObjectProperty .

        ico:path1 a ico:CausalPathway ;
            ico:hasSourceFactor ico:EnvironmentalFactor ;
            ico:hasTargetFactor ico:Biomarker ;
            ico:hasCorrelationCoefficient "0.1"^^xsd:float .
        """,
        encoding="utf-8",
    )

    report = OntologyValidator().validate_file(malformed, rdf_format="turtle")

    assert not report.ok
    assert any(issue.code == "MISSING_CLASS_TYPE" for issue in report.errors)
    assert any(issue.code == "MISSING_OBJECT_PROPERTY_TYPE" for issue in report.errors)

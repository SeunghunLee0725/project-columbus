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
    assert repo.resolve("not a real ontology label") is None


def test_duplicate_labels_prefer_ico_namespace(tmp_path):
    ontology = tmp_path / "duplicate-labels.ttl"
    ontology.write_text(
        """
        @prefix ico: <http://purl.obolibrary.org/obo/ICO#> .
        @prefix obo: <http://purl.obolibrary.org/obo/> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ico:NitricOxide a owl:Class ;
            rdfs:label "Nitric Oxide" .

        obo:CHEBI_16480 a owl:Class ;
            rdfs:label "Nitric Oxide" .
        """,
        encoding="utf-8",
    )

    repo = OntologyLoader().load(ontology, rdf_format="turtle")

    assert repo.resolve("Nitric Oxide") == "http://purl.obolibrary.org/obo/ICO#NitricOxide"

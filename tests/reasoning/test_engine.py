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
    assert chains[0].cumulative_abs_correlation == 0.225
    assert chains[0].signed_correlation_product == 0.225


def test_pm25_to_atopic_dermatitis_chain_absence_is_explicit():
    repo = OntologyLoader().load(OWL_PATH, rdf_format="xml")
    engine = CausalReasoningEngine(repo)

    assert engine.find_causal_chain("PM2.5", "Atopic Dermatitis") == []

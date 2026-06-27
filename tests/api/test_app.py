from fastapi.testclient import TestClient

from project_columbus.api.app import create_app


OWL_PATH = "research/01_ontology/immune_care_ontology.owl"


def test_health_includes_ontology_version():
    client = TestClient(create_app(ontology_path=OWL_PATH))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["ontology_version"] == ["0.2.0"]


def test_ontology_stats_endpoint():
    client = TestClient(create_app(ontology_path=OWL_PATH))

    response = client.get("/ontology/stats")

    assert response.status_code == 200
    assert response.json()["triples"] == 821
    assert response.json()["causal_pathways"] == 19


def test_env_to_pathway_endpoint():
    client = TestClient(create_app(ontology_path=OWL_PATH))

    response = client.post("/query/env-to-pathway", json={"env_factor": "PM2.5"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 6
    assert body["results"][0]["causal_path"] == "PM2.5 → NF-κB → IL-6"


def test_causal_chain_endpoint():
    client = TestClient(create_app(ontology_path=OWL_PATH))

    response = client.post(
        "/reason/causal-chain",
        json={"source": "PM2.5", "target": "Psoriasis"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chains"][0]["path"] == ["PM2.5", "TNF-alpha", "Psoriasis"]
    assert body["chains"][0]["cumulative_abs_correlation"] == 0.225

"""FastAPI read-only application."""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI

from project_columbus.api.schemas import CausalChainRequest, EnvToPathwayRequest
from project_columbus.ontology.loader import OntologyLoader
from project_columbus.ontology.validator import OntologyValidator
from project_columbus.reasoning.engine import CausalReasoningEngine


DEFAULT_ONTOLOGY_PATH = "research/01_ontology/immune_care_ontology.owl"


def create_app(ontology_path: str | Path | None = None) -> FastAPI:
    path = Path(ontology_path or os.environ.get("COLUMBUS_ONTOLOGY_PATH", DEFAULT_ONTOLOGY_PATH))
    validation = OntologyValidator().validate_file(path, rdf_format="xml")
    if not validation.ok:
        messages = "; ".join(issue.message for issue in validation.errors)
        raise ValueError(f"Invalid ontology at startup: {messages}")

    repo = OntologyLoader().load(path, rdf_format="xml")
    engine = CausalReasoningEngine(repo)
    stats = repo.stats()

    app = FastAPI(title="Project Columbus Ontology API", version="0.1.0")
    app.state.ontology_path = str(path)
    app.state.repo = repo
    app.state.engine = engine

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "ontology_path": str(path),
            "ontology_version": stats.version_info,
        }

    @app.get("/ontology/stats")
    def ontology_stats():
        return asdict(stats)

    @app.post("/query/env-to-pathway")
    def env_to_pathway(request: EnvToPathwayRequest):
        return {
            "ontology_version": stats.version_info,
            "results": [asdict(result) for result in engine.env_to_pathway(request.env_factor)],
        }

    @app.post("/reason/causal-chain")
    def causal_chain(request: CausalChainRequest):
        return {
            "ontology_version": stats.version_info,
            "chains": [
                asdict(chain)
                for chain in engine.find_causal_chain(
                    request.source,
                    request.target,
                    max_depth=request.max_depth,
                )
            ],
        }

    return app


app = create_app()

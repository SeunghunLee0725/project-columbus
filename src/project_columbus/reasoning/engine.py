"""Causal reasoning over ICO CausalPathway individuals."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
from rdflib import Literal
from rdflib.namespace import RDF, RDFS

from project_columbus.ontology.loader import OntologyRepository
from project_columbus.ontology.namespaces import ICO


@dataclass(frozen=True)
class PathwayResult:
    causal_path: str
    source: str
    target: str
    correlation: float | None
    lag_hours: float | None
    evidence: str | None
    source_layer: str | None
    target_layer: str | None


@dataclass(frozen=True)
class ChainEdge:
    source: str
    target: str
    correlation: float | None
    lag_hours: float | None
    evidence: str | None
    pathway: str | None


@dataclass(frozen=True)
class CausalChain:
    path: list[str]
    path_uris: list[str]
    cumulative_abs_correlation: float
    signed_correlation_product: float | None
    total_lag_hours: float
    edges: list[ChainEdge]


class CausalReasoningEngine:
    def __init__(self, repo: OntologyRepository) -> None:
        self.repo = repo
        self.graph = nx.DiGraph()
        self.pathways = self._load_pathways()
        self._build_graph()

    def env_to_pathway(self, env_factor: str) -> list[PathwayResult]:
        source_uri = self.repo.resolve(env_factor)
        if not source_uri:
            return []

        results = [
            PathwayResult(
                causal_path=data["label"],
                source=self.repo.label(source),
                target=self.repo.label(target),
                correlation=data["correlation"],
                lag_hours=data["lag_hours"],
                evidence=data["evidence"],
                source_layer=data["source_layer"],
                target_layer=data["target_layer"],
            )
            for source, target, data in self.graph.out_edges(source_uri, data=True)
        ]
        return sorted(results, key=lambda item: _sort_correlation(item.correlation))

    def find_causal_chain(
        self, source: str, target: str, max_depth: int = 10
    ) -> list[CausalChain]:
        source_uri = self.repo.resolve(source)
        target_uri = self.repo.resolve(target)
        if not source_uri or not target_uri:
            return []

        try:
            paths = nx.all_simple_paths(self.graph, source_uri, target_uri, cutoff=max_depth)
        except (nx.NetworkXError, nx.NodeNotFound):
            return []

        chains = [self._to_chain(path) for path in paths]
        return sorted(
            chains,
            key=lambda chain: chain.cumulative_abs_correlation,
            reverse=True,
        )

    def _load_pathways(self) -> list[dict]:
        pathways = []
        for pathway in set(self.repo.graph.subjects(RDF.type, ICO.CausalPathway)):
            source = _single_uri(self.repo.graph.objects(pathway, ICO.hasSourceFactor))
            target = _single_uri(self.repo.graph.objects(pathway, ICO.hasTargetFactor))
            pathways.append(
                {
                    "uri": str(pathway),
                    "label": _single_text(self.repo.graph.objects(pathway, RDFS.label)) or "",
                    "source": source,
                    "target": target,
                    "pathway": _single_uri(self.repo.graph.objects(pathway, ICO.involvesPathway)),
                    "correlation": _single_float(
                        self.repo.graph.objects(pathway, ICO.hasCorrelationCoefficient)
                    ),
                    "lag_hours": _single_float(self.repo.graph.objects(pathway, ICO.hasLagTime)),
                    "evidence": _single_text(
                        self.repo.graph.objects(pathway, ICO.hasEvidenceStrength)
                    ),
                    "source_layer": _single_text(self.repo.graph.objects(pathway, ICO.hasSourceLayer)),
                    "target_layer": _single_text(self.repo.graph.objects(pathway, ICO.hasTargetLayer)),
                }
            )
        return pathways

    def _build_graph(self) -> None:
        for pathway in self.pathways:
            if pathway["source"] and pathway["target"]:
                self.graph.add_edge(
                    pathway["source"],
                    pathway["target"],
                    label=pathway["label"],
                    pathway_uri=pathway["uri"],
                    pathway=pathway["pathway"],
                    correlation=pathway["correlation"],
                    lag_hours=pathway["lag_hours"],
                    evidence=pathway["evidence"],
                    source_layer=pathway["source_layer"],
                    target_layer=pathway["target_layer"],
                )

    def _to_chain(self, path: list[str]) -> CausalChain:
        cumulative_abs = 1.0
        signed_product: float | None = 1.0
        total_lag = 0.0
        edges = []

        for index in range(len(path) - 1):
            edge = self.graph.edges[path[index], path[index + 1]]
            correlation = edge.get("correlation")
            lag = edge.get("lag_hours") or 0.0

            if correlation is None:
                signed_product = None
            else:
                cumulative_abs *= abs(correlation)
                if signed_product is not None:
                    signed_product *= correlation
            total_lag += lag

            edges.append(
                ChainEdge(
                    source=self.repo.label(path[index]),
                    target=self.repo.label(path[index + 1]),
                    correlation=correlation,
                    lag_hours=lag,
                    evidence=edge.get("evidence"),
                    pathway=self.repo.label(edge["pathway"]) if edge.get("pathway") else None,
                )
            )

        return CausalChain(
            path=[self.repo.label(uri) for uri in path],
            path_uris=path,
            cumulative_abs_correlation=round(cumulative_abs, 4),
            signed_correlation_product=round(signed_product, 4)
            if signed_product is not None
            else None,
            total_lag_hours=total_lag,
            edges=edges,
        )


def _single_uri(values) -> str | None:
    value = next(iter(values), None)
    return str(value) if value is not None else None


def _single_text(values) -> str | None:
    value = next(iter(values), None)
    return str(value) if value is not None else None


def _single_float(values) -> float | None:
    value = next(iter(values), None)
    if value is None:
        return None
    if isinstance(value, Literal):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sort_correlation(value: float | None) -> tuple[int, float]:
    if value is None:
        return (1, 0.0)
    return (0, -value)

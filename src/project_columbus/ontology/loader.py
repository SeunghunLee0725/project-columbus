"""Ontology graph loading and safe resource lookup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from project_columbus.ontology.models import OntologyStats
from project_columbus.ontology.namespaces import ICO, OBO


ALIASES = {
    "pm2.5": "PM2_5",
    "pm25": "PM2_5",
    "nitric oxide": "NitricOxide",
    "hydroxyl radical": "HydroxylRadical",
}


@dataclass
class OntologyRepository:
    graph: Graph
    label_by_uri: dict[str, str]
    korean_label_by_uri: dict[str, str]
    uri_by_label: dict[str, str]

    def stats(self) -> OntologyStats:
        return OntologyStats(
            triples=len(self.graph),
            owl_classes=len(set(self.graph.subjects(RDF.type, OWL.Class))),
            object_properties=len(set(self.graph.subjects(RDF.type, OWL.ObjectProperty))),
            datatype_properties=len(set(self.graph.subjects(RDF.type, OWL.DatatypeProperty))),
            named_individuals=len(set(self.graph.subjects(RDF.type, OWL.NamedIndividual))),
            causal_pathways=len(set(self.graph.subjects(RDF.type, ICO.CausalPathway))),
            version_info=[str(o) for o in self.graph.objects(None, OWL.versionInfo)],
        )

    def resolve(self, name: str) -> str | None:
        if not name:
            return None

        candidate = name.strip()
        if not candidate:
            return None

        if candidate.startswith("http"):
            uri = URIRef(candidate)
            if (uri, None, None) in self.graph or (None, None, uri) in self.graph:
                return str(uri)
            return None

        lowered = candidate.lower()
        alias = ALIASES.get(lowered)
        if alias:
            uri = URIRef(str(ICO[alias]))
            if (uri, None, None) in self.graph or (None, None, uri) in self.graph:
                return str(uri)

        if lowered in self.uri_by_label:
            return self.uri_by_label[lowered]

        if _is_safe_local_name(candidate):
            uri = URIRef(str(ICO[candidate]))
            if (uri, None, None) in self.graph or (None, None, uri) in self.graph:
                return str(uri)

        return None

    def label(self, uri: str, lang: str = "en") -> str:
        if lang == "ko" and uri in self.korean_label_by_uri:
            return self.korean_label_by_uri[uri]
        if uri in self.label_by_uri:
            return self.label_by_uri[uri]
        return uri.split("#")[-1].split("/")[-1]


class OntologyLoader:
    def load(self, path: str | Path, rdf_format: str | None = None) -> OntologyRepository:
        graph = Graph()
        graph.parse(str(path), format=rdf_format)
        graph.bind("ico", ICO)
        graph.bind("obo", OBO)

        label_by_uri: dict[str, str] = {}
        korean_label_by_uri: dict[str, str] = {}
        uri_by_label: dict[str, str] = {}

        for subject, _, label in graph.triples((None, RDFS.label, None)):
            uri = str(subject)
            label_text = str(label)
            label_by_uri[uri] = label_text
            _add_label_uri(uri_by_label, label_text, uri)

        for subject, _, label in graph.triples((None, ICO.koreanLabel, None)):
            uri = str(subject)
            label_text = str(label)
            korean_label_by_uri[uri] = label_text
            _add_label_uri(uri_by_label, label_text, uri)

        return OntologyRepository(
            graph=graph,
            label_by_uri=label_by_uri,
            korean_label_by_uri=korean_label_by_uri,
            uri_by_label=uri_by_label,
        )


def _is_safe_local_name(value: str) -> bool:
    return bool(value) and all(ch.isalnum() or ch == "_" for ch in value)


def _add_label_uri(uri_by_label: dict[str, str], label: str, uri: str) -> None:
    key = label.lower()
    current = uri_by_label.get(key)
    if current is None or _prefer_uri(uri, current):
        uri_by_label[key] = uri


def _prefer_uri(candidate: str, current: str) -> bool:
    candidate_is_ico = candidate.startswith(str(ICO))
    current_is_ico = current.startswith(str(ICO))
    if candidate_is_ico != current_is_ico:
        return candidate_is_ico
    return candidate < current

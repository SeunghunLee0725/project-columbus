"""
Causal Reasoning Engine for Digital Columbus Immune Care Ontology.

Phase 1 deliverable: Causal Reasoning Tool Ver 1.0
Integrates OWL knowledge base with SPARQL queries, causal chain reasoning,
and SHAP-ontology bridging for explainable immune care AI.

Project: Digital Columbus — KIMS
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections import defaultdict, deque
from typing import Any, Optional

import numpy as np

# Ensure networkx is available
try:
    import networkx as nx
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "networkx"])
    import networkx as nx

from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, URIRef
from rdflib.namespace import XSD

# ═══════════════════════════════════════════════════════════════
# Namespace definitions
# ═══════════════════════════════════════════════════════════════

ICO = Namespace("http://purl.obolibrary.org/obo/ICO#")
OBO = Namespace("http://purl.obolibrary.org/obo/")
IAO = Namespace("http://purl.obolibrary.org/obo/IAO_")

PREFIXES = """
PREFIX ico: <http://purl.obolibrary.org/obo/ICO#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""


# ═══════════════════════════════════════════════════════════════
# A. OWL Knowledge Base Loading
# ═══════════════════════════════════════════════════════════════

class CausalReasoningEngine:
    """Causal reasoning engine over the Immune Care Ontology (ICO).

    Loads the OWL knowledge base, builds an in-memory causal graph,
    and provides SPARQL query execution, causal chain reasoning,
    and SHAP-ontology bridging capabilities.
    """

    def __init__(self, owl_path: str) -> None:
        """Initialize the engine by loading the OWL file and building the causal graph.

        Args:
            owl_path: Path to the ICO OWL file.
        """
        self.owl_path = owl_path
        self.rdf_graph = Graph()
        self.causal_graph: nx.DiGraph = nx.DiGraph()

        # Label caches
        self._label_cache: dict[str, str] = {}
        self._korean_label_cache: dict[str, str] = {}
        self._uri_by_label: dict[str, str] = {}

        # Causal pathway data keyed by individual URI
        self.pathways: dict[str, dict[str, Any]] = {}

        self._load_owl()
        self._build_causal_graph()

    def _load_owl(self) -> None:
        """Load the OWL file into the RDF graph."""
        self.rdf_graph.parse(self.owl_path, format="xml")
        self.rdf_graph.bind("ico", ICO)
        self.rdf_graph.bind("obo", OBO)

        # Cache labels
        for s, p, o in self.rdf_graph.triples((None, RDFS.label, None)):
            uri = str(s)
            label = str(o)
            self._label_cache[uri] = label
            self._uri_by_label[label.lower()] = uri

        for s, p, o in self.rdf_graph.triples((None, ICO.koreanLabel, None)):
            self._korean_label_cache[str(s)] = str(o)

    def _get_label(self, uri: str, lang: str = "en") -> str:
        """Get the human-readable label for a URI.

        Args:
            uri: The RDF resource URI.
            lang: Language code ('en' or 'ko').

        Returns:
            The label string, or the URI fragment if no label found.
        """
        if lang == "ko" and uri in self._korean_label_cache:
            return self._korean_label_cache[uri]
        if uri in self._label_cache:
            return self._label_cache[uri]
        # Fallback: extract fragment
        return uri.split("#")[-1].split("/")[-1]

    def _resolve_uri(self, name: str) -> Optional[str]:
        """Resolve a human-readable name or short ICO name to a full URI.

        Args:
            name: Either a full URI, ICO local name (e.g. 'PM2_5'), or label.

        Returns:
            The full URI string, or None if not found.
        """
        if name.startswith("http"):
            return name
        # Try ICO namespace
        candidate = str(ICO[name])
        if (URIRef(candidate), None, None) in self.rdf_graph:
            return candidate
        # Try label match
        lower = name.lower()
        if lower in self._uri_by_label:
            return self._uri_by_label[lower]
        # Fuzzy: partial match
        for label, uri in self._uri_by_label.items():
            if lower in label or label in lower:
                return uri
        return None

    def _build_causal_graph(self) -> None:
        """Parse CausalPathway instances and build a networkx DiGraph."""
        query = PREFIXES + """
        SELECT ?path ?label ?source ?target ?pathway ?corr ?lag ?evidence ?srcLayer ?tgtLayer
        WHERE {
            ?path a ico:CausalPathway .
            OPTIONAL { ?path rdfs:label ?label }
            OPTIONAL { ?path ico:hasSourceFactor ?source }
            OPTIONAL { ?path ico:hasTargetFactor ?target }
            OPTIONAL { ?path ico:involvesPathway ?pathway }
            OPTIONAL { ?path ico:hasCorrelationCoefficient ?corr }
            OPTIONAL { ?path ico:hasLagTime ?lag }
            OPTIONAL { ?path ico:hasEvidenceStrength ?evidence }
            OPTIONAL { ?path ico:hasSourceLayer ?srcLayer }
            OPTIONAL { ?path ico:hasTargetLayer ?tgtLayer }
        }
        """
        results = self.rdf_graph.query(query)

        for row in results:
            path_uri = str(row.path)
            data = {
                "uri": path_uri,
                "label": str(row.label) if row.label else "",
                "source": str(row.source) if row.source else None,
                "target": str(row.target) if row.target else None,
                "pathway": str(row.pathway) if row.pathway else None,
                "correlation": float(row.corr) if row.corr else None,
                "lag_hours": float(row.lag) if row.lag else None,
                "evidence": str(row.evidence) if row.evidence else None,
                "source_layer": str(row.srcLayer) if row.srcLayer else None,
                "target_layer": str(row.tgtLayer) if row.tgtLayer else None,
            }
            self.pathways[path_uri] = data

            if data["source"] and data["target"]:
                self.causal_graph.add_edge(
                    data["source"],
                    data["target"],
                    weight=abs(data["correlation"]) if data["correlation"] else 0.0,
                    correlation=data["correlation"],
                    lag_hours=data["lag_hours"],
                    evidence=data["evidence"],
                    pathway=data["pathway"],
                    pathway_uri=path_uri,
                    label=data["label"],
                )

    # ═══════════════════════════════════════════════════════════════
    # B. SPARQL Query Engine — 6 template queries
    # ═══════════════════════════════════════════════════════════════

    def query_env_to_pathway(self, env_factor: str) -> list[dict[str, Any]]:
        """Q1: What pathways does a given environmental factor activate?

        Args:
            env_factor: Name or URI of environmental factor (e.g. 'PM2.5').

        Returns:
            List of dicts with keys: env_factor, pathway_label, target_biomarker,
            correlation, lag_time, evidence.
        """
        uri = self._resolve_uri(env_factor)
        if not uri:
            return []

        query = PREFIXES + f"""
        SELECT ?path ?pathLabel ?target ?targetLabel ?pathway ?pathwayLabel ?corr ?lag ?evidence
        WHERE {{
            ?path a ico:CausalPathway ;
                  ico:hasSourceFactor <{uri}> .
            OPTIONAL {{ ?path rdfs:label ?pathLabel }}
            OPTIONAL {{ ?path ico:hasTargetFactor ?target .
                        ?target rdfs:label ?targetLabel }}
            OPTIONAL {{ ?path ico:involvesPathway ?pathway .
                        ?pathway rdfs:label ?pathwayLabel }}
            OPTIONAL {{ ?path ico:hasCorrelationCoefficient ?corr }}
            OPTIONAL {{ ?path ico:hasLagTime ?lag }}
            OPTIONAL {{ ?path ico:hasEvidenceStrength ?evidence }}
        }}
        ORDER BY DESC(?corr)
        """
        results = []
        for row in self.rdf_graph.query(query):
            results.append({
                "env_factor": self._get_label(uri),
                "causal_path": str(row.pathLabel) if row.pathLabel else "",
                "target_biomarker": str(row.targetLabel) if row.targetLabel else "",
                "signaling_pathway": str(row.pathwayLabel) if row.pathwayLabel else "",
                "correlation": float(row.corr) if row.corr else None,
                "lag_time_hours": float(row.lag) if row.lag else None,
                "evidence": str(row.evidence) if row.evidence else None,
            })
        return results

    def query_rons_immune_effect(self, rons_list: list[str]) -> list[dict[str, Any]]:
        """Q2: What immune effect does a combination of RONS have?

        Args:
            rons_list: List of RONS names (e.g. ['Nitric Oxide', 'Hydroxyl Radical']).

        Returns:
            List of dicts with keys: rons, pathway, target, evidence.
        """
        values_clause = "\n".join(f'("{r}")' for r in rons_list)
        query = PREFIXES + f"""
        SELECT ?rons ?ronsLabel ?path ?pathLabel ?target ?targetLabel ?pathway ?evidence
        WHERE {{
            VALUES (?ronsLabel) {{ {values_clause} }}
            ?rons rdfs:subClassOf* ico:ReactiveSpecies .
            ?rons rdfs:label ?ronsLabel .
            OPTIONAL {{
                ?path a ico:CausalPathway ;
                      ico:hasSourceFactor ?rons .
                OPTIONAL {{ ?path rdfs:label ?pathLabel }}
                OPTIONAL {{ ?path ico:hasTargetFactor ?target .
                            ?target rdfs:label ?targetLabel }}
                OPTIONAL {{ ?path ico:involvesPathway ?pathway }}
                OPTIONAL {{ ?path ico:hasEvidenceStrength ?evidence }}
            }}
        }}
        """
        results = []
        for row in self.rdf_graph.query(query):
            results.append({
                "rons": str(row.ronsLabel) if row.ronsLabel else "",
                "causal_path": str(row.pathLabel) if row.pathLabel else "",
                "target": str(row.targetLabel) if row.targetLabel else "",
                "evidence": str(row.evidence) if row.evidence else None,
            })

        # Also check pathways where RONS are sources (by ICO class URI)
        for rons_name in rons_list:
            uri = self._resolve_uri(rons_name)
            if uri:
                for _, target, data in self.causal_graph.out_edges(uri, data=True):
                    results.append({
                        "rons": rons_name,
                        "causal_path": data.get("label", ""),
                        "target": self._get_label(target),
                        "evidence": data.get("evidence"),
                    })

        # Deduplicate
        seen = set()
        unique = []
        for r in results:
            key = (r["rons"], r["causal_path"])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    def query_trajectory_stages(self, trajectory_type: str = "AllergicMarch") -> list[dict[str, Any]]:
        """Q3: What are the stages of a disease trajectory?

        Args:
            trajectory_type: Name of the trajectory class (default: 'AllergicMarch').

        Returns:
            Ordered list of dicts with keys: stage_uri, stage_label, next_stage.
        """
        query = PREFIXES + f"""
        SELECT ?stage ?stageLabel ?nextStage ?nextLabel
        WHERE {{
            ?stage a ico:TrajectoryStage .
            OPTIONAL {{ ?stage rdfs:label ?stageLabel }}
            OPTIONAL {{ ?stage ico:precedes ?nextStage .
                        ?nextStage rdfs:label ?nextLabel }}
        }}
        """
        raw = []
        for row in self.rdf_graph.query(query):
            raw.append({
                "stage_uri": str(row.stage),
                "stage_label": str(row.stageLabel) if row.stageLabel else "",
                "next_stage_uri": str(row.nextStage) if row.nextStage else None,
                "next_stage_label": str(row.nextLabel) if row.nextLabel else None,
            })

        # Order stages by following the precedes chain
        if not raw:
            return []

        # Build next-stage map
        next_map: dict[str, dict] = {}
        all_nexts = set()
        for r in raw:
            next_map[r["stage_uri"]] = r
            if r["next_stage_uri"]:
                all_nexts.add(r["next_stage_uri"])

        # Find the first stage (not a next of anyone)
        firsts = [uri for uri in next_map if uri not in all_nexts]
        ordered = []
        current = firsts[0] if firsts else raw[0]["stage_uri"]
        visited = set()
        while current and current in next_map and current not in visited:
            visited.add(current)
            ordered.append(next_map[current])
            current = next_map[current].get("next_stage_uri")
        # Append any remaining stages not in chain
        for r in raw:
            if r["stage_uri"] not in visited:
                ordered.append(r)

        return ordered

    def query_patient_multilayer(self, patient_id: str) -> list[dict[str, Any]]:
        """Q4: Get a patient's full multi-layer data.

        Args:
            patient_id: Patient identifier or URI.

        Returns:
            List of dicts with multi-layer observation data.
        """
        uri = self._resolve_uri(patient_id)
        if not uri:
            uri = str(ICO[patient_id])

        query = PREFIXES + f"""
        SELECT ?patient ?envExposure ?envLabel ?lifelog ?lifelogLabel
               ?biomarkerObs ?bioLabel ?value ?timestamp
        WHERE {{
            ?patient a ico:Patient .
            FILTER (?patient = <{uri}>)
            OPTIONAL {{
                ?patient ico:hasExposureTo ?envExposure .
                ?envExposure rdfs:label ?envLabel
            }}
            OPTIONAL {{
                ?patient ico:hasLifelogObservation ?lifelog .
                ?lifelog rdfs:label ?lifelogLabel
            }}
            OPTIONAL {{
                ?patient ico:hasBiomarkerLevel ?biomarkerObs .
                ?biomarkerObs rdfs:label ?bioLabel .
                OPTIONAL {{ ?biomarkerObs ico:hasValue ?value }}
                OPTIONAL {{ ?biomarkerObs ico:hasTimestamp ?timestamp }}
            }}
        }}
        ORDER BY DESC(?timestamp)
        """
        results = []
        for row in self.rdf_graph.query(query):
            results.append({
                "patient": str(row.patient),
                "env_exposure": str(row.envLabel) if row.envLabel else None,
                "lifelog": str(row.lifelogLabel) if row.lifelogLabel else None,
                "biomarker": str(row.bioLabel) if row.bioLabel else None,
                "value": float(row.value) if row.value else None,
                "timestamp": str(row.timestamp) if row.timestamp else None,
            })
        return results

    def query_treatment_protocol(self, disease: str) -> list[dict[str, Any]]:
        """Q5: What plasma treatment works for a given disease?

        Args:
            disease: Disease name or URI (e.g. 'Psoriasis').

        Returns:
            List of dicts with treatment protocol information.
        """
        uri = self._resolve_uri(disease)
        if not uri:
            return []

        # Query causal pathways from L4 targeting this disease
        query = PREFIXES + f"""
        SELECT ?path ?pathLabel ?source ?sourceLabel ?pathway ?pathwayLabel ?evidence
        WHERE {{
            ?path a ico:CausalPathway ;
                  ico:hasTargetFactor <{uri}> ;
                  ico:hasSourceLayer "L4" .
            OPTIONAL {{ ?path rdfs:label ?pathLabel }}
            OPTIONAL {{ ?path ico:hasSourceFactor ?source .
                        ?source rdfs:label ?sourceLabel }}
            OPTIONAL {{ ?path ico:involvesPathway ?pathway .
                        ?pathway rdfs:label ?pathwayLabel }}
            OPTIONAL {{ ?path ico:hasEvidenceStrength ?evidence }}
        }}
        """
        results = []
        for row in self.rdf_graph.query(query):
            results.append({
                "disease": self._get_label(uri),
                "treatment_path": str(row.pathLabel) if row.pathLabel else "",
                "plasma_source": str(row.sourceLabel) if row.sourceLabel else "",
                "signaling_pathway": str(row.pathwayLabel) if row.pathwayLabel else "",
                "evidence": str(row.evidence) if row.evidence else None,
            })

        # Also look for treatedBy relationships
        query2 = PREFIXES + f"""
        SELECT ?protocol ?protocolLabel ?device ?deviceLabel
        WHERE {{
            <{uri}> ico:treatedBy ?protocol .
            OPTIONAL {{ ?protocol rdfs:label ?protocolLabel }}
            OPTIONAL {{ ?protocol ico:usesDevice ?device .
                        ?device rdfs:label ?deviceLabel }}
        }}
        """
        for row in self.rdf_graph.query(query2):
            results.append({
                "disease": self._get_label(uri),
                "treatment_path": str(row.protocolLabel) if row.protocolLabel else "",
                "plasma_source": str(row.deviceLabel) if row.deviceLabel else "",
                "signaling_pathway": "",
                "evidence": "Protocol",
            })

        # If no direct L4 paths found, search for any L4 paths involving disease pathways
        if not results:
            for path_uri, pdata in self.pathways.items():
                if pdata.get("source_layer") == "L4":
                    results.append({
                        "disease": self._get_label(uri),
                        "treatment_path": pdata["label"],
                        "plasma_source": self._get_label(pdata["source"]) if pdata["source"] else "",
                        "signaling_pathway": self._get_label(pdata["pathway"]) if pdata["pathway"] else "",
                        "evidence": pdata["evidence"],
                    })
        return results

    def query_correlation_network(self, min_r: float = 0.3) -> list[dict[str, Any]]:
        """Q6: All correlations with |r| above a threshold.

        Args:
            min_r: Minimum absolute correlation coefficient.

        Returns:
            List of dicts sorted by descending |correlation|.
        """
        query = PREFIXES + f"""
        SELECT ?path ?pathLabel ?source ?sourceLabel ?target ?targetLabel
               ?corr ?lag ?srcLayer ?tgtLayer ?evidence
        WHERE {{
            ?path a ico:CausalPathway ;
                  ico:hasCorrelationCoefficient ?corr .
            FILTER (ABS(?corr) > {min_r})
            OPTIONAL {{ ?path rdfs:label ?pathLabel }}
            OPTIONAL {{ ?path ico:hasSourceFactor ?source .
                        ?source rdfs:label ?sourceLabel }}
            OPTIONAL {{ ?path ico:hasTargetFactor ?target .
                        ?target rdfs:label ?targetLabel }}
            OPTIONAL {{ ?path ico:hasLagTime ?lag }}
            OPTIONAL {{ ?path ico:hasSourceLayer ?srcLayer }}
            OPTIONAL {{ ?path ico:hasTargetLayer ?tgtLayer }}
            OPTIONAL {{ ?path ico:hasEvidenceStrength ?evidence }}
        }}
        ORDER BY DESC(ABS(?corr))
        """
        results = []
        for row in self.rdf_graph.query(query):
            results.append({
                "path_label": str(row.pathLabel) if row.pathLabel else "",
                "source": str(row.sourceLabel) if row.sourceLabel else "",
                "target": str(row.targetLabel) if row.targetLabel else "",
                "correlation": float(row.corr) if row.corr else None,
                "lag_time_hours": float(row.lag) if row.lag else None,
                "source_layer": str(row.srcLayer) if row.srcLayer else "",
                "target_layer": str(row.tgtLayer) if row.tgtLayer else "",
                "evidence": str(row.evidence) if row.evidence else None,
            })
        return results

    # ═══════════════════════════════════════════════════════════════
    # C. Causal Chain Reasoning
    # ═══════════════════════════════════════════════════════════════

    def find_causal_chain(
        self, source: str, target: str, max_depth: int = 10
    ) -> list[dict[str, Any]]:
        """Find all causal chains from source factor to target outcome.

        Uses BFS on the causal graph to find all simple paths.

        Args:
            source: Source factor name or URI (e.g. 'PM2_5').
            target: Target outcome name or URI (e.g. 'AtopicDermatitis').
            max_depth: Maximum chain length to search.

        Returns:
            List of chain dicts, each with 'path' (list of node labels),
            'path_uris', 'cumulative_correlation', 'total_lag_hours',
            and 'edges' (list of edge details).
        """
        src_uri = self._resolve_uri(source)
        tgt_uri = self._resolve_uri(target)
        if not src_uri or not tgt_uri:
            return []

        chains = []
        try:
            all_paths = list(nx.all_simple_paths(
                self.causal_graph, src_uri, tgt_uri, cutoff=max_depth
            ))
        except nx.NetworkXError:
            return []

        for path in all_paths:
            cumulative_corr = 1.0
            total_lag = 0.0
            edges = []

            for i in range(len(path) - 1):
                edge_data = self.causal_graph.edges[path[i], path[i + 1]]
                corr = edge_data.get("correlation")
                lag = edge_data.get("lag_hours") or 0.0

                if corr is not None:
                    cumulative_corr *= abs(corr)
                total_lag += lag

                edges.append({
                    "from": self._get_label(path[i]),
                    "to": self._get_label(path[i + 1]),
                    "correlation": corr,
                    "lag_hours": lag,
                    "evidence": edge_data.get("evidence"),
                    "pathway": self._get_label(edge_data["pathway"]) if edge_data.get("pathway") else None,
                })

            chains.append({
                "path": [self._get_label(n) for n in path],
                "path_uris": path,
                "cumulative_correlation": round(cumulative_corr, 4),
                "total_lag_hours": total_lag,
                "edges": edges,
            })

        # Sort by cumulative correlation (strongest first)
        chains.sort(key=lambda c: c["cumulative_correlation"], reverse=True)
        return chains

    def explain_why(self, env_factor: str, disease: str, lang: str = "both") -> dict[str, Any]:
        """Natural language explanation of why an environmental factor leads to a disease.

        Traverses causal chains and generates bilingual explanations.

        Args:
            env_factor: Environmental factor name or URI.
            disease: Disease name or URI.
            lang: 'en', 'ko', or 'both'.

        Returns:
            Dict with 'chains', 'explanation_en', 'explanation_ko',
            'evidence_summary', and 'total_chains_found'.
        """
        chains = self.find_causal_chain(env_factor, disease)

        env_label_en = self._get_label(self._resolve_uri(env_factor) or env_factor)
        disease_label_en = self._get_label(self._resolve_uri(disease) or disease)
        env_label_ko = self._get_label(self._resolve_uri(env_factor) or env_factor, "ko")
        disease_label_ko = self._get_label(self._resolve_uri(disease) or disease, "ko")

        explanation_en = ""
        explanation_ko = ""

        if not chains:
            explanation_en = (
                f"No direct causal chain found from {env_label_en} to {disease_label_en} "
                f"in the current ontology."
            )
            explanation_ko = (
                f"현재 온톨로지에서 {env_label_ko}에서 {disease_label_ko}까지의 "
                f"직접적인 인과 경로를 찾지 못했습니다."
            )
        else:
            # English explanation
            en_parts = [
                f"=== Why does {env_label_en} exposure increase {disease_label_en} risk? ===\n",
                f"Found {len(chains)} causal chain(s):\n",
            ]
            for i, chain in enumerate(chains, 1):
                path_str = " → ".join(chain["path"])
                en_parts.append(f"\nChain {i}: {path_str}")
                en_parts.append(
                    f"  Cumulative correlation strength: {chain['cumulative_correlation']:.4f}"
                )
                en_parts.append(
                    f"  Total estimated lag time: {chain['total_lag_hours']:.0f} hours "
                    f"({chain['total_lag_hours'] / 24:.1f} days)"
                )
                en_parts.append("  Step-by-step mechanism:")
                for edge in chain["edges"]:
                    direction = "increases" if (edge["correlation"] or 0) > 0 else "decreases"
                    en_parts.append(
                        f"    - {edge['from']} {direction} {edge['to']} "
                        f"(r={edge['correlation']}, lag={edge['lag_hours']}h, "
                        f"evidence={edge['evidence']})"
                    )
                    if edge["pathway"]:
                        en_parts.append(f"      via {edge['pathway']}")

            explanation_en = "\n".join(en_parts)

            # Korean explanation
            ko_parts = [
                f"=== {env_label_ko} 노출이 {disease_label_ko} 위험을 높이는 이유 ===\n",
                f"{len(chains)}개의 인과 경로를 발견했습니다:\n",
            ]
            for i, chain in enumerate(chains, 1):
                path_labels_ko = []
                for uri in chain["path_uris"]:
                    path_labels_ko.append(self._get_label(uri, "ko"))
                path_str = " → ".join(path_labels_ko)
                ko_parts.append(f"\n경로 {i}: {path_str}")
                ko_parts.append(
                    f"  누적 상관강도: {chain['cumulative_correlation']:.4f}"
                )
                ko_parts.append(
                    f"  총 예상 지연시간: {chain['total_lag_hours']:.0f}시간 "
                    f"({chain['total_lag_hours'] / 24:.1f}일)"
                )
                ko_parts.append("  단계별 메커니즘:")
                for edge in chain["edges"]:
                    direction_ko = "증가시킴" if (edge["correlation"] or 0) > 0 else "감소시킴"
                    from_ko = self._get_label(
                        self._resolve_uri(edge["from"]) or edge["from"], "ko"
                    )
                    to_ko = self._get_label(
                        self._resolve_uri(edge["to"]) or edge["to"], "ko"
                    )
                    ko_parts.append(
                        f"    - {from_ko} → {to_ko} {direction_ko} "
                        f"(r={edge['correlation']}, 지연={edge['lag_hours']}시간, "
                        f"근거={edge['evidence']})"
                    )

            explanation_ko = "\n".join(ko_parts)

        result: dict[str, Any] = {
            "chains": chains,
            "total_chains_found": len(chains),
        }
        if lang in ("en", "both"):
            result["explanation_en"] = explanation_en
        if lang in ("ko", "both"):
            result["explanation_ko"] = explanation_ko

        # Evidence summary
        evidence_levels = defaultdict(int)
        for chain in chains:
            for edge in chain["edges"]:
                if edge["evidence"]:
                    evidence_levels[edge["evidence"]] += 1
        result["evidence_summary"] = dict(evidence_levels)

        return result

    def get_intervention_points(self, disease: str) -> list[dict[str, Any]]:
        """Identify where plasma treatment can intervene in a disease's causal pathway.

        Cross-references L4 (plasma) pathways with disease pathways
        to find intervention opportunities.

        Args:
            disease: Disease name or URI.

        Returns:
            List of intervention opportunity dicts.
        """
        disease_uri = self._resolve_uri(disease)
        if not disease_uri:
            return []

        disease_label = self._get_label(disease_uri)

        # Find all pathways leading to this disease
        disease_pathways: list[dict] = []
        for path_uri, pdata in self.pathways.items():
            if pdata["target"] == disease_uri:
                disease_pathways.append(pdata)

        # Find all nodes on paths leading to disease
        disease_nodes: set[str] = set()
        for pdata in disease_pathways:
            if pdata["source"]:
                disease_nodes.add(pdata["source"])
            if pdata["target"]:
                disease_nodes.add(pdata["target"])
            if pdata["pathway"]:
                disease_nodes.add(pdata["pathway"])

        # Also find upstream nodes (nodes that eventually connect to disease)
        predecessors = set()
        try:
            for node in self.causal_graph.nodes():
                if nx.has_path(self.causal_graph, node, disease_uri):
                    predecessors.add(node)
        except nx.NetworkXError:
            pass
        disease_nodes.update(predecessors)

        # Find L4 (plasma) pathways
        plasma_pathways: list[dict] = []
        for path_uri, pdata in self.pathways.items():
            if pdata.get("source_layer") == "L4":
                plasma_pathways.append(pdata)

        # Cross-reference: find plasma pathways that target nodes in the disease chain
        interventions: list[dict[str, Any]] = []
        for pp in plasma_pathways:
            # Check if plasma pathway targets any node in disease pathway
            overlap_target = pp["target"] in disease_nodes if pp["target"] else False
            overlap_pathway = pp["pathway"] in disease_nodes if pp["pathway"] else False

            if overlap_target or overlap_pathway:
                mechanism_en = (
                    f"Plasma intervention via {pp['label']}: "
                    f"targets {self._get_label(pp['target']) if pp['target'] else 'unknown'}"
                )
                if pp["pathway"]:
                    mechanism_en += f" through {self._get_label(pp['pathway'])} pathway"

                mechanism_ko = (
                    f"플라즈마 개입: {pp['label']}: "
                    f"{self._get_label(pp['target'], 'ko') if pp['target'] else '미정'} 대상"
                )

                interventions.append({
                    "disease": disease_label,
                    "intervention": pp["label"],
                    "plasma_source": self._get_label(pp["source"]) if pp["source"] else None,
                    "target_node": self._get_label(pp["target"]) if pp["target"] else None,
                    "signaling_pathway": self._get_label(pp["pathway"]) if pp["pathway"] else None,
                    "mechanism_en": mechanism_en,
                    "mechanism_ko": mechanism_ko,
                    "evidence": pp["evidence"],
                })

        return interventions

    # ═══════════════════════════════════════════════════════════════
    # D. SHAP-Ontology Bridge
    # ═══════════════════════════════════════════════════════════════

    # Mapping from common SHAP feature names to ICO class local names
    FEATURE_TO_ICO_MAP: dict[str, str] = {
        "pm25": "PM2_5",
        "pm2.5": "PM2_5",
        "pm10": "PM10",
        "voc": "VolatileOrganicCompound",
        "vocs": "VolatileOrganicCompound",
        "btex": "BTEX",
        "formaldehyde": "Formaldehyde",
        "hcho": "Formaldehyde",
        "ozone": "Ozone",
        "o3": "Ozone",
        "co2": "CO2Level",
        "temperature": "Temperature",
        "humidity": "RelativeHumidity",
        "rh": "RelativeHumidity",
        "hrv": "HRVMeasurement",
        "hrv_sdnn": "HRVMeasurement",
        "spo2": "SpO2Measurement",
        "sleep_quality": "SleepQualityAssessment",
        "sleep": "SleepQualityAssessment",
        "activity": "PhysicalActivityLevel",
        "steps": "PhysicalActivityLevel",
        "skin_temp": "SkinTemperature",
        "il6": "IL6",
        "il-6": "IL6",
        "tnf_alpha": "TNFAlpha",
        "tnf-a": "TNFAlpha",
        "crp": "CRP",
        "ige": "IgE",
        "il4": "IL4",
        "il-4": "IL4",
        "il13": "IL13",
        "il-13": "IL13",
        "il17": "IL17",
        "il-17": "IL17",
        "il5": "IL5",
        "il-5": "IL5",
        "8ohdg": "OHdG_8",
        "mda": "MDA",
        "osl": "OxidativeStressLoad",
        "aes": "AllergenExposureScore",
    }

    def map_shap_to_ontology(
        self,
        shap_values: np.ndarray,
        feature_names: list[str],
    ) -> list[dict[str, Any]]:
        """Map SHAP feature attributions to CausalPathway instances.

        Matches feature names to ICO classes, compares SHAP attribution
        direction (+/-) with known causal direction, and returns hybrid
        explanations.

        Args:
            shap_values: 1D array of SHAP values for a single prediction.
            feature_names: Corresponding feature names.

        Returns:
            List of dicts with SHAP-ontology mapped explanations.
        """
        shap_values = np.atleast_1d(shap_values)
        mappings: list[dict[str, Any]] = []

        for i, (feat, shap_val) in enumerate(zip(feature_names, shap_values)):
            feat_lower = feat.lower().strip()

            # Resolve to ICO URI
            ico_name = self.FEATURE_TO_ICO_MAP.get(feat_lower)
            if not ico_name:
                # Try direct resolution
                ico_uri = self._resolve_uri(feat)
            else:
                ico_uri = str(ICO[ico_name])

            if not ico_uri:
                mappings.append({
                    "feature": feat,
                    "shap_value": float(shap_val),
                    "ico_class": None,
                    "causal_pathways": [],
                    "direction_consistent": None,
                    "hybrid_explanation": f"{feat}: SHAP={shap_val:+.4f} (no ontology mapping)",
                })
                continue

            ico_label = self._get_label(ico_uri)
            ico_label_ko = self._get_label(ico_uri, "ko")

            # Find causal pathways where this feature is the source
            related_pathways = []
            for _, target, data in self.causal_graph.out_edges(ico_uri, data=True):
                related_pathways.append({
                    "target": self._get_label(target),
                    "correlation": data.get("correlation"),
                    "pathway": self._get_label(data["pathway"]) if data.get("pathway") else None,
                    "evidence": data.get("evidence"),
                })

            # Check direction consistency
            shap_direction = "positive" if shap_val > 0 else "negative"
            consistent = None
            for rp in related_pathways:
                if rp["correlation"] is not None:
                    ontology_direction = "positive" if rp["correlation"] > 0 else "negative"
                    if shap_direction == ontology_direction:
                        consistent = True
                    else:
                        consistent = False

            # Generate hybrid explanation
            if related_pathways:
                pathway_desc = "; ".join(
                    f"{rp['target']} (r={rp['correlation']}, via {rp['pathway'] or 'unknown'})"
                    for rp in related_pathways
                )
                consistency_str = ""
                if consistent is True:
                    consistency_str = " [CONSISTENT with ontology]"
                elif consistent is False:
                    consistency_str = " [DIVERGENT from ontology — needs investigation]"
                hybrid = (
                    f"{ico_label} ({ico_label_ko}): SHAP={shap_val:+.4f}{consistency_str}. "
                    f"Known causal targets: {pathway_desc}"
                )
            else:
                hybrid = (
                    f"{ico_label} ({ico_label_ko}): SHAP={shap_val:+.4f}. "
                    f"No outgoing causal pathways in ontology."
                )

            mappings.append({
                "feature": feat,
                "shap_value": float(shap_val),
                "ico_class": ico_label,
                "ico_class_ko": ico_label_ko,
                "ico_uri": ico_uri,
                "causal_pathways": related_pathways,
                "direction_consistent": consistent,
                "hybrid_explanation": hybrid,
            })

        # Sort by absolute SHAP value
        mappings.sort(key=lambda m: abs(m["shap_value"]), reverse=True)
        return mappings

    def generate_explanation_report(
        self,
        patient_data: dict[str, float],
        shap_values: np.ndarray,
        target_disease: str = "AtopicDermatitis",
    ) -> dict[str, Any]:
        """Generate a structured explanation report combining SHAP and ontology reasoning.

        Args:
            patient_data: Dict of feature_name -> measured_value.
            shap_values: SHAP attribution values corresponding to patient_data keys.
            target_disease: The predicted disease.

        Returns:
            Structured report dict with top factors, causal pathways,
            and recommended interventions.
        """
        feature_names = list(patient_data.keys())
        shap_arr = np.array(shap_values) if not isinstance(shap_values, np.ndarray) else shap_values

        # Map SHAP to ontology
        mapped = self.map_shap_to_ontology(shap_arr, feature_names)

        # Top 5 contributing factors
        top5 = mapped[:5]

        # Get causal chains for top factors
        causal_explanations: list[dict[str, Any]] = []
        for m in top5:
            if m["ico_class"]:
                # Use the ICO class label (not the feature/path name) for chain lookup
                source_label = self._get_label(m["ico_class"])
                if not source_label:
                    source_label = m["ico_class"].split("#")[-1] if "#" in str(m["ico_class"]) else str(m["ico_class"])
                chains = self.find_causal_chain(source_label, target_disease)
                if chains:
                    causal_explanations.append({
                        "factor": m["ico_class"],
                        "shap_value": m["shap_value"],
                        "chains": chains,
                    })

        # Get intervention points
        interventions = self.get_intervention_points(target_disease)

        # Environmental recommendations
        env_recommendations_en: list[str] = []
        env_recommendations_ko: list[str] = []
        for m in top5:
            if m["shap_value"] > 0 and m["ico_class"]:
                env_recommendations_en.append(
                    f"Reduce exposure to {m['ico_class']} (current contribution: {m['shap_value']:+.4f})"
                )
                env_recommendations_ko.append(
                    f"{m.get('ico_class_ko', m['ico_class'])} 노출 감소 필요 "
                    f"(현재 기여도: {m['shap_value']:+.4f})"
                )

        disease_label = self._get_label(
            self._resolve_uri(target_disease) or target_disease
        )
        disease_label_ko = self._get_label(
            self._resolve_uri(target_disease) or target_disease, "ko"
        )

        report = {
            "report_title_en": f"Immune Risk Explanation Report — {disease_label}",
            "report_title_ko": f"면역 위험 설명 보고서 — {disease_label_ko}",
            "target_disease": disease_label,
            "top_5_factors": [
                {
                    "rank": i + 1,
                    "feature": m["feature"],
                    "ico_class": m["ico_class"],
                    "shap_value": m["shap_value"],
                    "direction_consistent": m["direction_consistent"],
                    "explanation": m["hybrid_explanation"],
                }
                for i, m in enumerate(top5)
            ],
            "causal_pathways": causal_explanations,
            "plasma_interventions": interventions,
            "environmental_recommendations_en": env_recommendations_en,
            "environmental_recommendations_ko": env_recommendations_ko,
        }

        return report


# ═══════════════════════════════════════════════════════════════
# E. Interactive Demo
# ═══════════════════════════════════════════════════════════════

def _print_section(title: str) -> None:
    """Print a formatted section header."""
    width = 70
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def _print_results(results: list | dict, max_items: int = 10) -> None:
    """Pretty-print query results."""
    if isinstance(results, dict):
        for k, v in results.items():
            if isinstance(v, (list, dict)):
                if isinstance(v, list) and len(v) > max_items:
                    print(f"  {k}: [{len(v)} items]")
                    for item in v[:max_items]:
                        print(f"    - {item}")
                    print(f"    ... ({len(v) - max_items} more)")
                else:
                    print(f"  {k}: {v}")
            elif isinstance(v, str) and "\n" in v:
                print(f"  {k}:")
                for line in v.split("\n"):
                    print(f"    {line}")
            else:
                print(f"  {k}: {v}")
    elif isinstance(results, list):
        if not results:
            print("  (no results)")
        for i, r in enumerate(results[:max_items]):
            print(f"  [{i + 1}] {r}")
        if len(results) > max_items:
            print(f"  ... ({len(results) - max_items} more)")


if __name__ == "__main__":
    # Determine OWL file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    owl_path = os.path.join(script_dir, "immune_care_ontology.owl")

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Causal Reasoning Tool Ver 1.0 — Digital Columbus / KIMS   ║")
    print("║  인과추론 도구 Ver 1.0 — 디지털 콜럼버스 / 재료연구원        ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # ─────────────────────────────────────────────────────────────
    # Step 1: Load the OWL file
    # ─────────────────────────────────────────────────────────────
    _print_section("Step 1: Loading ICO OWL Knowledge Base")
    engine = CausalReasoningEngine(owl_path)
    print(f"  RDF triples loaded: {len(engine.rdf_graph)}")
    print(f"  Causal pathways: {len(engine.pathways)}")
    print(f"  Causal graph nodes: {engine.causal_graph.number_of_nodes()}")
    print(f"  Causal graph edges: {engine.causal_graph.number_of_edges()}")

    # ─────────────────────────────────────────────────────────────
    # Step 2: Run the 6 SPARQL query templates
    # ─────────────────────────────────────────────────────────────

    # Q1: What pathways does PM2.5 activate?
    _print_section("Q1: PM2.5가 활성화하는 경로 (PM2.5 activated pathways)")
    results_q1 = engine.query_env_to_pathway("PM2_5")
    _print_results(results_q1)

    # Q2: What immune effect does NO + OH have?
    _print_section("Q2: NO + OH 면역 효과 (RONS immune effects)")
    results_q2 = engine.query_rons_immune_effect(["Nitric Oxide", "Hydroxyl Radical"])
    _print_results(results_q2)

    # Q3: Allergic march stages
    _print_section("Q3: 알레르기 마치 단계 (Allergic March stages)")
    results_q3 = engine.query_trajectory_stages("AllergicMarch")
    _print_results(results_q3)

    # Q4: Patient multi-layer data (demo — no patient instances in current OWL)
    _print_section("Q4: 환자 다층 데이터 (Patient multi-layer data)")
    results_q4 = engine.query_patient_multilayer("Patient001")
    if not results_q4:
        print("  (No patient instances in current ontology — placeholder for Phase 2)")
    else:
        _print_results(results_q4)

    # Q5: Plasma treatment for psoriasis
    _print_section("Q5: 건선 플라즈마 치료 프로토콜 (Psoriasis treatment)")
    results_q5 = engine.query_treatment_protocol("Psoriasis")
    _print_results(results_q5)

    # Q6: Correlation network (|r| > 0.3)
    _print_section("Q6: 상관관계 네트워크 |r| > 0.3 (Correlation network)")
    results_q6 = engine.query_correlation_network(0.3)
    _print_results(results_q6)

    # ─────────────────────────────────────────────────────────────
    # Step 3: Causal chain reasoning
    # ─────────────────────────────────────────────────────────────
    _print_section("Step 3: Causal Chain — PM2.5 → Atopic Dermatitis")
    chains = engine.find_causal_chain("PM2_5", "AtopicDermatitis")
    if chains:
        for i, chain in enumerate(chains, 1):
            print(f"\n  Chain {i}: {' → '.join(chain['path'])}")
            print(f"    Cumulative |r|: {chain['cumulative_correlation']:.4f}")
            print(f"    Total lag: {chain['total_lag_hours']:.0f}h ({chain['total_lag_hours']/24:.1f} days)")
    else:
        print("  No chains found (check ontology connectivity)")

    # ─────────────────────────────────────────────────────────────
    # Step 4: Explain why PM2.5 → Psoriasis
    # ─────────────────────────────────────────────────────────────
    _print_section("Step 4: Why does PM2.5 increase psoriasis risk?")
    explanation = engine.explain_why("PM2_5", "Psoriasis")
    if explanation.get("explanation_en"):
        print(explanation["explanation_en"])
    print()
    if explanation.get("explanation_ko"):
        print(explanation["explanation_ko"])
    print(f"\n  Evidence summary: {explanation.get('evidence_summary', {})}")

    # ─────────────────────────────────────────────────────────────
    # Step 5: Intervention points for psoriasis
    # ─────────────────────────────────────────────────────────────
    _print_section("Step 5: 건선 개입지점 (Psoriasis intervention points)")
    interventions = engine.get_intervention_points("Psoriasis")
    _print_results(interventions)

    # ─────────────────────────────────────────────────────────────
    # Step 6: SHAP-Ontology Bridge Demo
    # ─────────────────────────────────────────────────────────────
    _print_section("Step 6: SHAP-Ontology Bridge Demo")

    # Mock patient data and SHAP values
    mock_patient_data = {
        "pm25": 45.0,       # ug/m3 (elevated)
        "vocs": 220.0,      # VOC index
        "humidity": 75.0,   # %RH (high)
        "hrv": 32.0,        # SDNN ms (low)
        "sleep_quality": 35.0,  # % (poor)
        "spo2": 94.0,       # % (borderline)
        "temperature": 26.0,
        "activity": 2500.0,  # steps (low)
    }
    mock_shap_values = np.array([
        0.28,   # pm25 — strong positive (increases risk)
        0.12,   # vocs
        0.08,   # humidity
        -0.22,  # hrv — negative (low HRV = high risk, so negative SHAP means protective)
        -0.15,  # sleep_quality
        -0.05,  # spo2
        0.02,   # temperature
        -0.08,  # activity
    ])

    print("\n  --- Mock Patient Data ---")
    for feat, val in mock_patient_data.items():
        print(f"    {feat}: {val}")

    print("\n  --- SHAP-Ontology Mapping ---")
    mapped = engine.map_shap_to_ontology(mock_shap_values, list(mock_patient_data.keys()))
    for m in mapped[:5]:
        print(f"\n  {m['hybrid_explanation']}")

    print("\n  --- Full Explanation Report ---")
    report = engine.generate_explanation_report(
        mock_patient_data, mock_shap_values, target_disease="AtopicDermatitis"
    )
    print(f"  Title (EN): {report['report_title_en']}")
    print(f"  Title (KO): {report['report_title_ko']}")
    print(f"\n  Top 5 Contributing Factors:")
    for f in report["top_5_factors"]:
        print(f"    #{f['rank']} {f['feature']}: SHAP={f['shap_value']:+.4f} "
              f"({f['ico_class'] or 'unmapped'})")
    print(f"\n  Plasma Interventions: {len(report['plasma_interventions'])}")
    for intv in report["plasma_interventions"]:
        print(f"    - {intv['intervention']} (evidence: {intv['evidence']})")
    print(f"\n  Environmental Recommendations (EN):")
    for rec in report["environmental_recommendations_en"]:
        print(f"    - {rec}")
    print(f"\n  환경 권고사항 (KO):")
    for rec in report["environmental_recommendations_ko"]:
        print(f"    - {rec}")

    print("\n" + "=" * 70)
    print("  Causal Reasoning Tool Ver 1.0 — Demo Complete")
    print("  인과추론 도구 Ver 1.0 — 데모 완료")
    print("=" * 70)

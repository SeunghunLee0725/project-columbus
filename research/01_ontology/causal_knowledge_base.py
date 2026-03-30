"""
Causal Knowledge Base Enrichment for Digital Columbus Immune Care Ontology.

Supplementary module that enriches the OWL with additional causal knowledge,
validates consistency, and exports the causal correlation matrix.

Project: Digital Columbus — KIMS
"""

from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
from collections import defaultdict
from typing import Any, Optional

import numpy as np

try:
    import networkx as nx
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "networkx"])
    import networkx as nx

try:
    import pandas as pd
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])
    import pandas as pd

from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, URIRef, BNode
from rdflib.namespace import XSD

# ═══════════════════════════════════════════════════════════════
# Namespace definitions
# ═══════════════════════════════════════════════════════════════

ICO = Namespace("http://purl.obolibrary.org/obo/ICO#")
OBO = Namespace("http://purl.obolibrary.org/obo/")

PREFIXES = """
PREFIX ico: <http://purl.obolibrary.org/obo/ICO#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""


# ═══════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════

def _get_label(graph: Graph, uri: str) -> str:
    """Get the rdfs:label for a URI, or the URI fragment as fallback.

    Args:
        graph: The RDF graph.
        uri: The URI string.

    Returns:
        Human-readable label.
    """
    for _, _, o in graph.triples((URIRef(uri), RDFS.label, None)):
        return str(o)
    return uri.split("#")[-1].split("/")[-1]


def _load_graph(owl_path: str) -> Graph:
    """Load an OWL file into an rdflib Graph.

    Args:
        owl_path: Path to the OWL file.

    Returns:
        Loaded and namespace-bound rdflib Graph.
    """
    g = Graph()
    g.parse(owl_path, format="xml")
    g.bind("ico", ICO)
    g.bind("obo", OBO)
    return g


def _build_causal_edges(graph: Graph) -> list[dict[str, Any]]:
    """Extract all CausalPathway edges from the RDF graph.

    Args:
        graph: The RDF graph with CausalPathway individuals.

    Returns:
        List of edge dicts with source, target, correlation, lag, etc.
    """
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
    edges = []
    for row in graph.query(query):
        edges.append({
            "uri": str(row.path),
            "label": str(row.label) if row.label else "",
            "source": str(row.source) if row.source else None,
            "target": str(row.target) if row.target else None,
            "pathway": str(row.pathway) if row.pathway else None,
            "correlation": float(row.corr) if row.corr else None,
            "lag_hours": float(row.lag) if row.lag else None,
            "evidence": str(row.evidence) if row.evidence else None,
            "source_layer": str(row.srcLayer) if row.srcLayer else None,
            "target_layer": str(row.tgtLayer) if row.tgtLayer else None,
        })
    return edges


# ═══════════════════════════════════════════════════════════════
# Enrichment Functions
# ═══════════════════════════════════════════════════════════════

def enrich_ontology(owl_path: str) -> Graph:
    """Add inferred triples to the ontology for enhanced reasoning.

    Performs the following enrichments:
    1. Transitive closure of `precedes` for trajectory stages.
    2. Inverse relationships (activated_by from activatesPathway).
    3. Cross-layer path summaries (L1->L2->L3 composite paths with cumulative lag).

    Args:
        owl_path: Path to the ICO OWL file.

    Returns:
        Enriched rdflib Graph with additional inferred triples.
    """
    graph = _load_graph(owl_path)
    triples_added = 0

    # ── 1. Transitive closure of `precedes` ──────────────────────
    precedes = ICO.precedes
    # Collect existing precedes pairs
    precedes_pairs: list[tuple[URIRef, URIRef]] = []
    for s, p, o in graph.triples((None, precedes, None)):
        precedes_pairs.append((s, o))

    # Build transitive closure
    changed = True
    inferred_precedes: set[tuple[URIRef, URIRef]] = set(
        (s, o) for s, o in precedes_pairs
    )
    while changed:
        changed = False
        new_pairs: set[tuple[URIRef, URIRef]] = set()
        for a, b in inferred_precedes:
            for c, d in inferred_precedes:
                if b == c and (a, d) not in inferred_precedes:
                    new_pairs.add((a, d))
                    changed = True
        inferred_precedes |= new_pairs

    # Add new transitive precedes triples
    existing = set(precedes_pairs)
    for s, o in inferred_precedes:
        if (s, o) not in existing:
            graph.add((s, precedes, o))
            triples_added += 1

    # ── 2. Inverse relationships ─────────────────────────────────
    # Define inverse property ico:activatedBy (inverse of ico:activatesPathway)
    activated_by = ICO.activatedBy
    if (URIRef(str(activated_by)), RDF.type, OWL.ObjectProperty) not in graph:
        graph.add((URIRef(str(activated_by)), RDF.type, OWL.ObjectProperty))
        graph.add((
            URIRef(str(activated_by)),
            RDFS.label,
            Literal("activated by"),
        ))
        graph.add((
            URIRef(str(activated_by)),
            OWL.inverseOf,
            ICO.activatesPathway,
        ))
        triples_added += 3

    # Materialize inverse: for every (X activatesPathway Y), add (Y activatedBy X)
    for s, p, o in graph.triples((None, ICO.activatesPathway, None)):
        if (o, activated_by, s) not in graph:
            graph.add((o, activated_by, s))
            triples_added += 1

    # For CausalPathway source/target, add inverse references
    caused_by = ICO.causedBy
    if (URIRef(str(caused_by)), RDF.type, OWL.ObjectProperty) not in graph:
        graph.add((URIRef(str(caused_by)), RDF.type, OWL.ObjectProperty))
        graph.add((URIRef(str(caused_by)), RDFS.label, Literal("caused by")))
        triples_added += 2

    edges = _build_causal_edges(graph)
    for edge in edges:
        if edge["source"] and edge["target"]:
            src = URIRef(edge["source"])
            tgt = URIRef(edge["target"])
            if (tgt, caused_by, src) not in graph:
                graph.add((tgt, caused_by, src))
                triples_added += 1

    # ── 3. Cross-layer path summaries ────────────────────────────
    # Build a directed graph from edges and find multi-hop paths L1->L2->L3
    layer_order = {"L1": 0, "L2": 1, "L3": 2, "Disease": 3}
    # Group edges by layer transition
    layer_edges: dict[str, list[dict]] = defaultdict(list)
    for edge in edges:
        key = f"{edge['source_layer']}->{edge['target_layer']}"
        layer_edges[key].append(edge)

    # Find L1->L2 and L2->L3 edges to compose L1->L3 summaries
    l1_to_l2 = layer_edges.get("L1->L2", [])
    l2_to_l3 = layer_edges.get("L2->L3", [])

    composite_count = 0
    for e12 in l1_to_l2:
        for e23 in l2_to_l3:
            if e12["target"] == e23["source"]:
                # Create composite path summary
                composite_uri = ICO[f"Composite_L1L3_{composite_count}"]
                composite_label = f"{_get_label(graph, e12['source'])} → " \
                                  f"{_get_label(graph, e12['target'])} → " \
                                  f"{_get_label(graph, e23['target'])}"

                # Cumulative lag
                lag1 = e12["lag_hours"] or 0
                lag2 = e23["lag_hours"] or 0
                total_lag = lag1 + lag2

                # Cumulative correlation (product of absolutes, preserving sign)
                corr1 = e12["correlation"]
                corr2 = e23["correlation"]
                if corr1 is not None and corr2 is not None:
                    # Sign: negative * negative = positive boost, etc.
                    composite_corr = corr1 * corr2
                else:
                    composite_corr = None

                graph.add((composite_uri, RDF.type, ICO.CausalPathway))
                graph.add((composite_uri, RDFS.label, Literal(f"[Composite] {composite_label}")))
                graph.add((composite_uri, ICO.hasSourceLayer, Literal("L1")))
                graph.add((composite_uri, ICO.hasTargetLayer, Literal("L3")))
                graph.add((composite_uri, ICO.hasSourceFactor, URIRef(e12["source"])))
                graph.add((composite_uri, ICO.hasTargetFactor, URIRef(e23["target"])))
                graph.add((composite_uri, ICO.hasLagTime,
                           Literal(total_lag, datatype=XSD.float)))
                if composite_corr is not None:
                    graph.add((composite_uri, ICO.hasCorrelationCoefficient,
                               Literal(round(composite_corr, 4), datatype=XSD.float)))
                graph.add((composite_uri, ICO.hasEvidenceStrength, Literal("Inferred")))

                triples_added += 9 if composite_corr is not None else 8
                composite_count += 1

    print(f"  Enrichment complete: {triples_added} triples added")
    print(f"    - Transitive precedes closures: {len(inferred_precedes) - len(existing)}")
    print(f"    - Inverse relationships materialized")
    print(f"    - Cross-layer composite paths: {composite_count}")

    return graph


# ═══════════════════════════════════════════════════════════════
# Validation Functions
# ═══════════════════════════════════════════════════════════════

def validate_consistency(graph: Graph) -> dict[str, Any]:
    """Check the ontology for consistency issues.

    Checks:
    1. Circular causal paths (should not exist).
    2. Missing definitions (classes referenced but not defined).
    3. Orphan instances (instances not connected to any pathway).

    Args:
        graph: The RDF graph to validate.

    Returns:
        Dict with validation results: 'is_consistent', 'circular_paths',
        'missing_definitions', 'orphan_instances', and 'warnings'.
    """
    issues: dict[str, Any] = {
        "is_consistent": True,
        "circular_paths": [],
        "missing_definitions": [],
        "orphan_instances": [],
        "warnings": [],
    }

    # ── 1. Circular causal paths ─────────────────────────────────
    edges = _build_causal_edges(graph)
    G = nx.DiGraph()
    for edge in edges:
        if edge["source"] and edge["target"]:
            G.add_edge(edge["source"], edge["target"])

    cycles = list(nx.simple_cycles(G))
    if cycles:
        issues["is_consistent"] = False
        for cycle in cycles:
            cycle_labels = [_get_label(graph, n) for n in cycle]
            issues["circular_paths"].append({
                "cycle": cycle_labels,
                "cycle_uris": cycle,
            })
        issues["warnings"].append(
            f"Found {len(cycles)} circular causal path(s) — "
            f"causal graphs should be acyclic (DAG)."
        )

    # ── 2. Missing definitions ───────────────────────────────────
    # Find all URIs referenced as objects in triples but not defined as subjects
    defined_subjects: set[str] = set()
    referenced_objects: set[str] = set()

    for s, p, o in graph:
        if isinstance(s, URIRef):
            defined_subjects.add(str(s))
        if isinstance(o, URIRef) and str(o).startswith(str(ICO)):
            referenced_objects.add(str(o))

    missing = referenced_objects - defined_subjects
    # Filter out known external references and property URIs
    for uri in missing:
        local_name = uri.split("#")[-1]
        # Skip properties (already defined)
        if any(
            (URIRef(uri), RDF.type, t) in graph
            for t in [OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty]
        ):
            continue
        issues["missing_definitions"].append({
            "uri": uri,
            "local_name": local_name,
        })

    if issues["missing_definitions"]:
        issues["warnings"].append(
            f"Found {len(issues['missing_definitions'])} ICO URI(s) referenced "
            f"but not defined as class or individual."
        )

    # ── 3. Orphan instances ──────────────────────────────────────
    # Find named individuals not connected to any CausalPathway
    all_individuals: set[str] = set()
    for s, _, _ in graph.triples((None, RDF.type, None)):
        if isinstance(s, URIRef) and str(s).startswith(str(ICO)):
            # Check if it is a NamedIndividual
            if (s, RDF.type, OWL.NamedIndividual) in graph:
                all_individuals.add(str(s))

    connected_individuals: set[str] = set()
    for edge in edges:
        connected_individuals.add(edge["uri"])
        if edge["source"]:
            connected_individuals.add(edge["source"])
        if edge["target"]:
            connected_individuals.add(edge["target"])
    # Also include trajectory stages
    for s, _, _ in graph.triples((None, RDF.type, ICO.TrajectoryStage)):
        connected_individuals.add(str(s))
    for s, _, _ in graph.triples((None, RDF.type, ICO.AllergicMarch)):
        connected_individuals.add(str(s))

    orphans = all_individuals - connected_individuals
    for uri in orphans:
        label = _get_label(graph, uri)
        issues["orphan_instances"].append({
            "uri": uri,
            "label": label,
        })

    if issues["orphan_instances"]:
        issues["warnings"].append(
            f"Found {len(issues['orphan_instances'])} orphan instance(s) "
            f"not connected to any causal pathway or trajectory."
        )

    if not issues["warnings"]:
        issues["warnings"].append("No consistency issues found.")

    return issues


# ═══════════════════════════════════════════════════════════════
# Export Functions
# ═══════════════════════════════════════════════════════════════

def export_causal_matrix(
    graph: Graph,
    output_path: Optional[str] = None,
) -> pd.DataFrame:
    """Export the full causal correlation matrix as CSV.

    Rows: source factors, Columns: target factors,
    Values: correlation coefficients.

    Args:
        graph: The RDF graph containing CausalPathway instances.
        output_path: Optional file path for CSV output.

    Returns:
        pandas DataFrame of the correlation matrix.
    """
    edges = _build_causal_edges(graph)

    # Collect all unique source and target labels
    sources: set[str] = set()
    targets: set[str] = set()
    corr_data: dict[tuple[str, str], float] = {}

    for edge in edges:
        if edge["source"] and edge["target"] and edge["correlation"] is not None:
            src_label = _get_label(graph, edge["source"])
            tgt_label = _get_label(graph, edge["target"])
            sources.add(src_label)
            targets.add(tgt_label)
            corr_data[(src_label, tgt_label)] = edge["correlation"]

    # Build matrix
    all_labels = sorted(sources | targets)
    matrix = pd.DataFrame(
        np.nan,
        index=all_labels,
        columns=all_labels,
    )

    for (src, tgt), corr in corr_data.items():
        matrix.loc[src, tgt] = corr

    if output_path:
        matrix.to_csv(output_path)
        print(f"  Causal matrix exported to: {output_path}")

    return matrix


# ═══════════════════════════════════════════════════════════════
# Interactive Demo
# ═══════════════════════════════════════════════════════════════

def _print_section(title: str) -> None:
    """Print a formatted section header."""
    width = 70
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    owl_path = os.path.join(script_dir, "immune_care_ontology.owl")

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Causal Knowledge Base Enrichment — Digital Columbus / KIMS ║")
    print("║  인과 지식 베이스 보강 — 디지털 콜럼버스 / 재료연구원         ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # ─────────────────────────────────────────────────────────────
    # Step 1: Enrich the ontology
    # ─────────────────────────────────────────────────────────────
    _print_section("Step 1: Ontology Enrichment (온톨로지 보강)")
    enriched_graph = enrich_ontology(owl_path)
    print(f"  Total triples after enrichment: {len(enriched_graph)}")

    # ─────────────────────────────────────────────────────────────
    # Step 2: Validate consistency
    # ─────────────────────────────────────────────────────────────
    _print_section("Step 2: Consistency Validation (일관성 검증)")
    validation = validate_consistency(enriched_graph)

    print(f"  Is consistent: {validation['is_consistent']}")
    print(f"  Circular paths: {len(validation['circular_paths'])}")
    for cycle in validation["circular_paths"]:
        print(f"    - {' -> '.join(cycle['cycle'])}")
    print(f"  Missing definitions: {len(validation['missing_definitions'])}")
    for md in validation["missing_definitions"][:5]:
        print(f"    - {md['local_name']} ({md['uri']})")
    if len(validation["missing_definitions"]) > 5:
        print(f"    ... ({len(validation['missing_definitions']) - 5} more)")
    print(f"  Orphan instances: {len(validation['orphan_instances'])}")
    for oi in validation["orphan_instances"]:
        print(f"    - {oi['label']}")
    print(f"\n  Warnings:")
    for w in validation["warnings"]:
        print(f"    - {w}")

    # ─────────────────────────────────────────────────────────────
    # Step 3: Export causal matrix
    # ─────────────────────────────────────────────────────────────
    _print_section("Step 3: Causal Correlation Matrix (인과 상관 행렬)")
    csv_path = os.path.join(script_dir, "causal_correlation_matrix.csv")
    matrix = export_causal_matrix(enriched_graph, output_path=csv_path)

    print(f"\n  Matrix dimensions: {matrix.shape[0]} x {matrix.shape[1]}")
    print(f"  Non-null entries: {matrix.notna().sum().sum()}")
    print(f"\n  Preview (first 8 rows x 8 cols):")
    preview = matrix.iloc[:8, :8]
    # Format for display
    with pd.option_context("display.max_columns", 8, "display.width", 120,
                           "display.float_format", "{:.2f}".format):
        print(preview.to_string(na_rep="  -  "))

    # ─────────────────────────────────────────────────────────────
    # Step 4: Show enriched transitive precedes
    # ─────────────────────────────────────────────────────────────
    _print_section("Step 4: Transitive Trajectory Stages (전이적 궤적 단계)")
    precedes_query = PREFIXES + """
    SELECT ?stage ?stageLabel ?next ?nextLabel
    WHERE {
        ?stage ico:precedes ?next .
        ?stage rdfs:label ?stageLabel .
        ?next rdfs:label ?nextLabel .
    }
    ORDER BY ?stageLabel
    """
    for row in enriched_graph.query(precedes_query):
        print(f"  {row.stageLabel}  -->  {row.nextLabel}")

    # ─────────────────────────────────────────────────────────────
    # Step 5: Show composite cross-layer paths
    # ─────────────────────────────────────────────────────────────
    _print_section("Step 5: Cross-Layer Composite Paths (교차계층 복합경로)")
    composite_query = PREFIXES + """
    SELECT ?path ?label ?corr ?lag
    WHERE {
        ?path a ico:CausalPathway ;
              ico:hasEvidenceStrength "Inferred" .
        OPTIONAL { ?path rdfs:label ?label }
        OPTIONAL { ?path ico:hasCorrelationCoefficient ?corr }
        OPTIONAL { ?path ico:hasLagTime ?lag }
    }
    ORDER BY DESC(ABS(?corr))
    """
    for row in enriched_graph.query(composite_query):
        corr_str = f"r={float(row.corr):.4f}" if row.corr else "r=N/A"
        lag_str = f"lag={float(row.lag):.0f}h" if row.lag else "lag=N/A"
        print(f"  {row.label}")
        print(f"    {corr_str}, {lag_str}")

    print("\n" + "=" * 70)
    print("  Causal Knowledge Base Enrichment — Demo Complete")
    print("  인과 지식 베이스 보강 — 데모 완료")
    print("=" * 70)

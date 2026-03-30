"""
Ontology Mapper for Digital Columbus Immune Care Pipeline.

Converts processed sensor data and computed composite indices into RDF
triples (Turtle format) aligned with the Immune Care Ontology (ICO).

Uses rdflib for RDF generation.

Ontology: http://purl.obolibrary.org/obo/ICO#
OWL file: research/01_ontology/immune_care_ontology.owl
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
from rdflib import Graph, Literal, Namespace, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL


# ---------------------------------------------------------------------------
# Namespace definitions
# ---------------------------------------------------------------------------

ICO = Namespace("http://purl.obolibrary.org/obo/ICO#")
OBO = Namespace("http://purl.obolibrary.org/obo/")
BFO = Namespace("http://purl.obolibrary.org/obo/BFO_")

# Bind prefixes for readable Turtle output
_PREFIXES: dict[str, Namespace | URIRef] = {
    "ico": ICO,
    "obo": OBO,
    "bfo": BFO,
    "owl": OWL,
    "xsd": XSD,
}


# ---------------------------------------------------------------------------
# Mapping tables: sensor column -> ontology class
# ---------------------------------------------------------------------------

ENV_CLASS_MAP: dict[str, str] = {
    "pm25":        "PM2_5",
    "pm10":        "PM10",
    "voc_index":   "VolatileOrganicCompound",
    "co2":         "CO2Level",
    "temperature": "Temperature",
    "humidity":    "RelativeHumidity",
    "btex":        "BTEX",
    "o3":          "Ozone",
}

ENV_UNIT_MAP: dict[str, str] = {
    "pm25":        "ug/m3",
    "pm10":        "ug/m3",
    "voc_index":   "index",
    "co2":         "ppm",
    "temperature": "degC",
    "humidity":    "%RH",
    "btex":        "ppb",
    "o3":          "ppb",
}

LIFELOG_CLASS_MAP: dict[str, str] = {
    "hrv_sdnn":       "HRVMeasurement",
    "spo2":           "SpO2Measurement",
    "sleep_quality":  "SleepQualityAssessment",
    "activity_level": "PhysicalActivityLevel",
    "skin_temp":      "SkinTemperature",
}

LIFELOG_UNIT_MAP: dict[str, str] = {
    "hrv_sdnn":       "ms",
    "spo2":           "%",
    "sleep_quality":  "score",
    "activity_level": "steps/hr",
    "skin_temp":      "degC",
}

COMPOSITE_CLASS_MAP: dict[str, str] = {
    "osl": "OxidativeStressLoad",
    "aes": "AllergenExposureScore",
    "vi":  "VentilationIndex",
    "irs": "ImmuneRiskScore",
}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _make_observation_uri(
    kind: str,
    sensor_name: str,
    timestamp: datetime,
    patient_id: str = "P001",
) -> URIRef:
    """Generate a deterministic URI for an observation individual."""
    ts_str = timestamp.strftime("%Y%m%dT%H%M%S")
    return ICO[f"{kind}_{sensor_name}_{patient_id}_{ts_str}"]


def _add_env_observation(
    g: Graph,
    col: str,
    value: float,
    timestamp: datetime,
    patient_id: str,
) -> URIRef:
    """Add an environmental observation individual to the graph."""
    cls_name = ENV_CLASS_MAP.get(col)
    if cls_name is None:
        return URIRef("")  # skip unknown columns

    obs_uri = _make_observation_uri("env_obs", col, timestamp, patient_id)
    g.add((obs_uri, RDF.type, ICO[cls_name]))
    g.add((obs_uri, RDFS.label, Literal(f"{col} observation", lang="en")))
    g.add((obs_uri, ICO.hasTimestamp, Literal(timestamp.isoformat(), datatype=XSD.dateTime)))
    g.add((obs_uri, ICO.hasValue, Literal(float(value), datatype=XSD.float)))
    g.add((obs_uri, ICO.hasUnit, Literal(ENV_UNIT_MAP.get(col, ""), datatype=XSD.string)))
    g.add((obs_uri, ICO.hasSourceLayer, Literal("L1", datatype=XSD.string)))
    return obs_uri


def _add_lifelog_observation(
    g: Graph,
    col: str,
    value: float,
    timestamp: datetime,
    patient_id: str,
) -> URIRef:
    """Add a lifelog observation individual to the graph."""
    cls_name = LIFELOG_CLASS_MAP.get(col)
    if cls_name is None:
        return URIRef("")

    obs_uri = _make_observation_uri("lifelog_obs", col, timestamp, patient_id)
    g.add((obs_uri, RDF.type, ICO[cls_name]))
    g.add((obs_uri, RDFS.label, Literal(f"{col} observation", lang="en")))
    g.add((obs_uri, ICO.hasTimestamp, Literal(timestamp.isoformat(), datatype=XSD.dateTime)))
    g.add((obs_uri, ICO.hasValue, Literal(float(value), datatype=XSD.float)))
    g.add((obs_uri, ICO.hasUnit, Literal(LIFELOG_UNIT_MAP.get(col, ""), datatype=XSD.string)))
    g.add((obs_uri, ICO.hasSourceLayer, Literal("L2", datatype=XSD.string)))
    return obs_uri


def _add_composite_index(
    g: Graph,
    index_name: str,
    value: float,
    timestamp: datetime,
    patient_id: str,
    source_uris: list[URIRef] | None = None,
) -> URIRef:
    """Add a composite index or immune risk score individual."""
    cls_name = COMPOSITE_CLASS_MAP.get(index_name)
    if cls_name is None:
        return URIRef("")

    obs_uri = _make_observation_uri("index", index_name, timestamp, patient_id)
    g.add((obs_uri, RDF.type, ICO[cls_name]))
    g.add((obs_uri, RDFS.label, Literal(f"{cls_name} score", lang="en")))
    g.add((obs_uri, ICO.hasTimestamp, Literal(timestamp.isoformat(), datatype=XSD.dateTime)))
    g.add((obs_uri, ICO.hasValue, Literal(float(value), datatype=XSD.float)))
    g.add((obs_uri, ICO.hasUnit, Literal("score_0_100", datatype=XSD.string)))

    if source_uris:
        for src in source_uris:
            if str(src):
                g.add((obs_uri, ICO.hasSourceFactor, src))

    return obs_uri


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_graph() -> Graph:
    """Create a fresh RDF graph with ICO namespace bindings."""
    g = Graph()
    for prefix, ns in _PREFIXES.items():
        g.bind(prefix, ns)
    return g


def map_row_to_rdf(
    row: dict[str, Any],
    timestamp: datetime,
    patient_id: str = "P001",
    graph: Graph | None = None,
) -> Graph:
    """Convert a single row of sensor data + computed indices to RDF triples.

    Parameters
    ----------
    row : dict
        Dictionary with sensor column names as keys and measured/computed
        values as values.  Expected keys include the sensor columns from
        ``sensor_simulator`` plus composite index columns: osl, aes, vi, irs.
    timestamp : datetime
        Observation timestamp.
    patient_id : str
        Patient identifier for URI construction.
    graph : Graph or None
        Existing graph to add triples to. Creates a new one if None.

    Returns
    -------
    rdflib.Graph
        The graph with new triples added.
    """
    if graph is None:
        graph = create_graph()

    env_uris: list[URIRef] = []
    lifelog_uris: list[URIRef] = []

    # Environmental observations
    for col in ENV_CLASS_MAP:
        if col in row and not _is_nan(row[col]):
            uri = _add_env_observation(graph, col, row[col], timestamp, patient_id)
            env_uris.append(uri)

    # Lifelog observations
    for col in LIFELOG_CLASS_MAP:
        if col in row and not _is_nan(row[col]):
            uri = _add_lifelog_observation(graph, col, row[col], timestamp, patient_id)
            lifelog_uris.append(uri)

    # Composite indices
    for idx_name in COMPOSITE_CLASS_MAP:
        if idx_name in row and not _is_nan(row[idx_name]):
            sources = env_uris if idx_name in ("osl", "aes", "vi") else env_uris + lifelog_uris
            _add_composite_index(graph, idx_name, row[idx_name], timestamp, patient_id, sources)

    # Patient individual (link observations)
    patient_uri = ICO[f"patient_{patient_id}"]
    graph.add((patient_uri, RDF.type, ICO.Patient))
    for uri in env_uris:
        graph.add((patient_uri, ICO.hasExposureTo, uri))
    for uri in lifelog_uris:
        graph.add((patient_uri, ICO.hasLifelogObservation, uri))

    return graph


def map_dataframe_to_rdf(
    df: "pd.DataFrame",
    patient_id: str = "P001",
    max_rows: int | None = None,
) -> Graph:
    """Convert a DataFrame of sensor data to a single RDF graph.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with timestamp index and sensor/index columns.
    patient_id : str
        Patient identifier.
    max_rows : int or None
        Limit the number of rows converted (useful for demos).

    Returns
    -------
    rdflib.Graph
        Complete graph with all observation triples.
    """
    import pandas as pd  # noqa: F811 — deferred import to keep module light

    graph = create_graph()
    rows_to_process = df.head(max_rows) if max_rows else df

    for ts, row_series in rows_to_process.iterrows():
        timestamp = ts.to_pydatetime() if isinstance(ts, pd.Timestamp) else ts
        map_row_to_rdf(row_series.to_dict(), timestamp, patient_id, graph)

    return graph


def graph_to_turtle(graph: Graph) -> str:
    """Serialise the graph to Turtle format string."""
    return graph.serialize(format="turtle")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_nan(value: Any) -> bool:
    """Check if value is NaN (works for float and numpy types)."""
    try:
        return np.isnan(float(value))
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from datetime import datetime

    sample_row = {
        "pm25": 35.2, "pm10": 58.1, "voc_index": 180.0, "co2": 720.0,
        "temperature": 24.5, "humidity": 68.0, "btex": 12.3, "o3": 42.0,
        "hrv_sdnn": 42.0, "spo2": 96.5, "sleep_quality": 55.0,
        "activity_level": 320.0, "skin_temp": 33.8,
        "osl": 28.5, "aes": 45.2, "vi": 62.0, "irs": 38.7,
    }

    ts = datetime(2026, 3, 30, 14, 30, 0)
    g = map_row_to_rdf(sample_row, ts)
    turtle_str = graph_to_turtle(g)
    print(f"Generated {len(g)} triples for 1 observation row.\n")
    print(turtle_str[:3000])

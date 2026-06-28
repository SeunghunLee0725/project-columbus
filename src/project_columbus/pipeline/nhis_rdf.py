"""Generate de-identified NHIS correlation RDF for integrated KG input."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD

from project_columbus.ontology.namespaces import ICO


NHIS = Namespace("http://purl.obolibrary.org/obo/ICO/nhis#")

REQUIRED_CORRELATION_COLUMNS = {
    "disease",
    "env_var",
    "lag_months",
    "mean_pearson_r",
    "mean_spearman_r",
    "pct_significant",
}

DISEASE_ICO_MAP = {
    "asthma": ("Asthma", "천식"),
    "rhinitis": ("AllergicRhinitis", "알레르기비염"),
    "atopy": ("AtopicDermatitis", "아토피피부염"),
}

ENV_VAR_ICO_MAP = {
    "avg_temp": ("Temperature", "Average Temperature"),
    "avg_rh": ("RelativeHumidity", "Average Relative Humidity"),
    "avg_pm25": ("PM2_5", "Average PM2.5"),
    "avg_pm10": ("PM10", "Average PM10"),
    "avg_o3": ("Ozone", "Average Ozone"),
    "diurnal_range": ("Temperature", "Diurnal Temperature Range"),
    "osl": ("OxidativeStressLoad", "Oxidative Stress Load"),
    "aes": ("AllergenExposureScore", "Allergen Exposure Score"),
}


@dataclass(frozen=True)
class NHISRDFSummary:
    source_csv: str
    output: str
    report_path: str
    triples: int
    instances: int
    skipped_rows: int


class NHISRDFGenerator:
    """Convert sanitized NHIS correlation summaries into Turtle RDF."""

    def from_correlation_csv(
        self,
        correlation_csv: str | Path,
        *,
        output: str | Path,
        report_path: str | Path,
    ) -> NHISRDFSummary:
        correlation_csv = Path(correlation_csv)
        output = Path(output)
        report_path = Path(report_path)

        rows = self._load_rows(correlation_csv)
        graph = self._create_graph()
        instances = 0
        skipped_rows = 0

        for row in rows:
            if self._add_correlation(graph, row):
                instances += 1
            else:
                skipped_rows += 1

        output.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        temp_output = output.with_suffix(output.suffix + ".tmp")
        graph.serialize(destination=str(temp_output), format="turtle")

        reparsed = Graph()
        reparsed.parse(temp_output, format="turtle")
        if len(reparsed) == 0:
            temp_output.unlink(missing_ok=True)
            raise ValueError("Refusing to write empty NHIS RDF graph.")

        os.replace(temp_output, output)
        summary = NHISRDFSummary(
            source_csv=str(correlation_csv),
            output=str(output),
            report_path=str(report_path),
            triples=len(reparsed),
            instances=instances,
            skipped_rows=skipped_rows,
        )
        report_path.write_text(
            json.dumps(asdict(summary), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return summary

    def _create_graph(self) -> Graph:
        graph = Graph()
        graph.bind("ico", ICO)
        graph.bind("nhis", NHIS)
        graph.bind("owl", OWL)
        graph.bind("xsd", XSD)
        return graph

    def _load_rows(self, correlation_csv: Path) -> list[dict[str, str]]:
        with correlation_csv.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_CORRELATION_COLUMNS - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
            return list(reader)

    def _add_correlation(self, graph: Graph, row: dict[str, str]) -> bool:
        disease_info = DISEASE_ICO_MAP.get(row["disease"])
        env_info = ENV_VAR_ICO_MAP.get(row["env_var"])
        if not disease_info or not env_info:
            return False

        disease_class, disease_label = disease_info
        env_class, env_label = env_info
        lag = int(row["lag_months"])
        pearson_r = float(row["mean_pearson_r"])
        spearman_r = float(row["mean_spearman_r"])
        pct_significant = float(row["pct_significant"])

        instance = NHIS[f"corr_{row['disease']}_{row['env_var']}_lag{lag}"]
        graph.add((instance, RDF.type, ICO.EnvironmentalCorrelation))
        graph.add((instance, RDF.type, OWL.NamedIndividual))
        graph.add((instance, ICO.hasSourceFactor, ICO[env_class]))
        graph.add((instance, ICO.hasTargetDisease, ICO[disease_class]))
        graph.add((instance, ICO.hasPearsonR, Literal(pearson_r, datatype=XSD.float)))
        graph.add((instance, ICO.hasSpearmanRho, Literal(spearman_r, datatype=XSD.float)))
        graph.add((instance, ICO.hasLagMonths, Literal(lag, datatype=XSD.integer)))
        graph.add(
            (
                instance,
                ICO.hasSignificancePct,
                Literal(pct_significant, datatype=XSD.float),
            )
        )
        graph.add(
            (
                instance,
                ICO.hasCorrelationDirection,
                Literal("positive" if pearson_r > 0 else "negative", datatype=XSD.string),
            )
        )
        graph.add(
            (
                instance,
                ICO.hasCorrelationStrength,
                Literal(_correlation_strength(pearson_r), datatype=XSD.string),
            )
        )
        graph.add(
            (
                instance,
                RDFS.label,
                Literal(
                    f"{env_label} -> {disease_label}: r={pearson_r:+.4f} "
                    f"(lag={lag}m)",
                    lang="ko",
                ),
            )
        )
        return True


def _correlation_strength(value: float) -> str:
    abs_value = abs(value)
    if abs_value > 0.5:
        return "strong"
    if abs_value > 0.3:
        return "moderate"
    return "weak"

"""Non-destructive evidence calibration for ICO OWL artifacts."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from rdflib import Graph, Literal
from rdflib.namespace import OWL, RDF, RDFS, XSD

from project_columbus.ontology.namespaces import ICO


REQUIRED_COLUMNS = {
    "env_var",
    "disease",
    "lag_months",
    "mean_pearson_r",
    "mean_spearman_r",
    "pct_significant",
}

ENV_MAP = {
    "avg_pm25": "PM2_5",
    "avg_pm10": "PM10",
    "avg_o3": "Ozone",
    "avg_temp": "Temperature",
    "avg_rh": "RelativeHumidity",
    "diurnal_range": "DiurnalRange",
    "osl": "OxidativeStressLoad",
    "aes": "AllergenExposureScore",
}

DISEASE_MAP = {
    "asthma": "Asthma",
    "rhinitis": "AllergicRhinitis",
    "atopy": "AtopicDermatitis",
}


@dataclass(frozen=True)
class CalibrationSummary:
    source_owl: str
    output_owl: str
    report_path: str
    calibrated_count: int
    evidence_counts: dict[str, int]
    input_triples: int
    output_triples: int
    calibration_date: str


class EvidenceCalibrator:
    def __init__(self, calibration_date: str | None = None) -> None:
        self.calibration_date = calibration_date or date.today().isoformat()

    def calibrate(
        self,
        source_owl: str | Path,
        correlation_csv: str | Path,
        output_owl: str | Path,
        report_path: str | Path,
        *,
        in_place: bool = False,
    ) -> CalibrationSummary:
        source_owl = Path(source_owl)
        correlation_csv = Path(correlation_csv)
        output_owl = Path(output_owl)
        report_path = Path(report_path)

        if source_owl.resolve() == output_owl.resolve() and not in_place:
            raise ValueError("Refusing to overwrite source OWL without in_place=True.")

        rows = self._load_rows(correlation_csv)

        graph = Graph()
        graph.parse(source_owl, format="xml")
        input_triples = len(graph)

        self._declare_terms(graph)
        self._replace_version(graph, "0.3.0")

        evidence_counts = {"A": 0, "B": 0, "C": 0}
        calibrated_count = 0
        for row in rows:
            if int(row["lag_months"]) != 0:
                continue
            env_class = ENV_MAP.get(row["env_var"])
            disease_class = DISEASE_MAP.get(row["disease"])
            if not env_class or not disease_class:
                continue

            pearson_r = float(row["mean_pearson_r"])
            spearman_r = float(row["mean_spearman_r"])
            pct_significant = float(row["pct_significant"])
            level = evidence_level(pearson_r, pct_significant)
            evidence_counts[level] += 1

            instance = ICO[f"nhis_corr_{row['env_var']}_{row['disease']}"]
            graph.add((instance, RDF.type, ICO.EvidenceBasedCorrelation))
            graph.add((instance, RDF.type, OWL.NamedIndividual))
            graph.add((instance, ICO.hasSourceFactor, ICO[env_class]))
            graph.add((instance, ICO.hasTargetDisease, ICO[disease_class]))
            graph.add((instance, ICO.hasNHISPearsonR, Literal(pearson_r, datatype=XSD.float)))
            graph.add((instance, ICO.hasNHISSpearmanR, Literal(spearman_r, datatype=XSD.float)))
            graph.add(
                (
                    instance,
                    ICO.hasNHISSignificancePct,
                    Literal(pct_significant, datatype=XSD.float),
                )
            )
            graph.add((instance, ICO.hasEvidenceLevel, Literal(level, datatype=XSD.string)))
            graph.add(
                (
                    instance,
                    ICO.hasCalibrationDate,
                    Literal(self.calibration_date, datatype=XSD.date),
                )
            )
            graph.add((instance, ICO.hasDataSource, Literal("NHIS_public_correlation_csv")))
            graph.add(
                (
                    instance,
                    RDFS.label,
                    Literal(
                        f"{row['env_var']}→{row['disease']}: r={pearson_r:+.4f} "
                        f"(sig={pct_significant:.0f}%, level={level})"
                    ),
                )
            )
            calibrated_count += 1

        output_owl.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        temp_output = output_owl.with_suffix(output_owl.suffix + ".tmp")
        graph.serialize(destination=str(temp_output), format="xml")

        reparsed = Graph()
        reparsed.parse(temp_output, format="xml")
        os.replace(temp_output, output_owl)

        summary = CalibrationSummary(
            source_owl=str(source_owl),
            output_owl=str(output_owl),
            report_path=str(report_path),
            calibrated_count=calibrated_count,
            evidence_counts=evidence_counts,
            input_triples=input_triples,
            output_triples=len(reparsed),
            calibration_date=self.calibration_date,
        )
        report_path.write_text(
            json.dumps(asdict(summary), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return summary

    def _load_rows(self, correlation_csv: Path) -> list[dict[str, str]]:
        with correlation_csv.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
            return list(reader)

    def _declare_terms(self, graph: Graph) -> None:
        graph.add((ICO.EvidenceBasedCorrelation, RDF.type, OWL.Class))
        graph.add((ICO.EvidenceBasedCorrelation, RDFS.subClassOf, ICO.CausalPathway))
        for prop in (
            ICO.hasTargetDisease,
            ICO.hasNHISPearsonR,
            ICO.hasNHISSpearmanR,
            ICO.hasNHISSignificancePct,
            ICO.hasEvidenceLevel,
            ICO.hasCalibrationDate,
            ICO.hasDataSource,
        ):
            graph.add((prop, RDF.type, OWL.DatatypeProperty))

    def _replace_version(self, graph: Graph, version: str) -> None:
        for triple in list(graph.triples((None, OWL.versionInfo, None))):
            graph.remove(triple)
            graph.add((triple[0], OWL.versionInfo, Literal(version)))


def evidence_level(pearson_r: float, pct_significant: float) -> str:
    abs_r = abs(pearson_r)
    if abs_r > 0.4 and pct_significant > 80:
        return "A"
    if abs_r > 0.2 and pct_significant > 50:
        return "B"
    return "C"

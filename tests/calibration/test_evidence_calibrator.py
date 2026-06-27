from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.namespace import OWL, RDF

from project_columbus.calibration.evidence_calibrator import (
    EvidenceCalibrator,
    evidence_level,
)
from project_columbus.ontology.namespaces import ICO


OWL_PATH = Path("research/01_ontology/immune_care_ontology.owl")


def _write_csv(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "env_var,disease,lag_months,mean_pearson_r,mean_spearman_r,pct_significant",
                "avg_pm25,asthma,0,0.52,0.49,88",
                "avg_rh,atopy,0,0.31,0.28,60",
                "avg_temp,rhinitis,0,0.12,0.10,20",
                "avg_pm10,asthma,1,0.99,0.99,100",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_evidence_level_policy():
    assert evidence_level(0.52, 88) == "A"
    assert evidence_level(-0.31, 60) == "B"
    assert evidence_level(0.12, 20) == "C"
    assert evidence_level(0.4, 88) == "B"
    assert evidence_level(0.2, 88) == "C"
    assert evidence_level(-0.41, 81) == "A"


def test_calibration_writes_new_output_without_modifying_source(tmp_path):
    csv_path = tmp_path / "correlation_summary.csv"
    output_path = tmp_path / "calibrated.owl"
    report_path = tmp_path / "calibration.report.json"
    _write_csv(csv_path)
    source_before = OWL_PATH.read_bytes()

    summary = EvidenceCalibrator(calibration_date="2026-06-27").calibrate(
        source_owl=OWL_PATH,
        correlation_csv=csv_path,
        output_owl=output_path,
        report_path=report_path,
    )

    assert OWL_PATH.read_bytes() == source_before
    assert output_path.exists()
    assert report_path.exists()
    assert summary.calibrated_count == 3
    assert summary.evidence_counts == {"A": 1, "B": 1, "C": 1}
    assert summary.output_triples > 821

    graph = Graph()
    graph.parse(output_path, format="xml")
    assert "0.3.0" in {str(v) for v in graph.objects(None, OWL.versionInfo)}
    assert len(set(graph.subjects(RDF.type, ICO.EvidenceBasedCorrelation))) == 3


def test_calibration_rejects_missing_required_columns(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("env_var,disease\navg_pm25,asthma\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing required columns"):
        EvidenceCalibrator(calibration_date="2026-06-27").calibrate(
            source_owl=OWL_PATH,
            correlation_csv=bad_csv,
            output_owl=tmp_path / "out.owl",
            report_path=tmp_path / "report.json",
        )


def test_calibration_requires_explicit_in_place_flag(tmp_path):
    csv_path = tmp_path / "correlation_summary.csv"
    _write_csv(csv_path)

    with pytest.raises(ValueError, match="Refusing to overwrite"):
        EvidenceCalibrator(calibration_date="2026-06-27").calibrate(
            source_owl=OWL_PATH,
            correlation_csv=csv_path,
            output_owl=OWL_PATH,
            report_path=tmp_path / "report.json",
        )


def test_calibration_source_version_remains_unchanged(tmp_path):
    csv_path = tmp_path / "correlation_summary.csv"
    output_path = tmp_path / "calibrated.owl"
    report_path = tmp_path / "calibration.report.json"
    _write_csv(csv_path)

    EvidenceCalibrator(calibration_date="2026-06-27").calibrate(
        source_owl=OWL_PATH,
        correlation_csv=csv_path,
        output_owl=output_path,
        report_path=report_path,
    )

    source = Graph()
    source.parse(OWL_PATH, format="xml")
    output = Graph()
    output.parse(output_path, format="xml")

    assert "0.2.0" in {str(v) for v in source.objects(None, OWL.versionInfo)}
    assert "0.3.0" in {str(v) for v in output.objects(None, OWL.versionInfo)}

from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.namespace import RDF

from project_columbus.ontology.namespaces import ICO
from project_columbus.pipeline.nhis_rdf import NHISRDFGenerator


def _write_correlation_csv(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "disease,env_var,lag_months,mean_pearson_r,mean_spearman_r,pct_significant",
                "asthma,avg_pm25,0,0.52,0.49,88",
                "rhinitis,avg_rh,1,-0.31,-0.28,60",
                "unknown,avg_pm25,0,0.1,0.1,10",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_nhis_rdf_generator_writes_parseable_correlation_turtle(tmp_path):
    csv_path = tmp_path / "correlation_summary.csv"
    output = tmp_path / "nhis_disease_instances.ttl"
    report = tmp_path / "nhis_disease_instances.report.json"
    _write_correlation_csv(csv_path)

    summary = NHISRDFGenerator().from_correlation_csv(
        csv_path,
        output=output,
        report_path=report,
    )

    graph = Graph()
    graph.parse(output, format="turtle")

    assert summary.instances == 2
    assert summary.skipped_rows == 1
    assert summary.triples == len(graph)
    assert len(set(graph.subjects(RDF.type, ICO.EnvironmentalCorrelation))) == 2
    assert report.exists()


def test_nhis_rdf_generator_rejects_missing_columns(tmp_path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("disease,env_var\nasthma,avg_pm25\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing required columns"):
        NHISRDFGenerator().from_correlation_csv(
            csv_path,
            output=tmp_path / "out.ttl",
            report_path=tmp_path / "report.json",
        )

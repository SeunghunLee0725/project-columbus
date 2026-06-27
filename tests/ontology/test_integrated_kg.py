from pathlib import Path

import pytest
from rdflib import Graph

from project_columbus.ontology.integrated_export import IntegratedKGExporter


OUTPUT = Path("research/01_ontology/integrated_knowledge_graph.ttl")
REPORT = Path("research/01_ontology/integrated_knowledge_graph.report.json")


def test_integrated_knowledge_graph_is_valid_turtle():
    graph = Graph()
    graph.parse(OUTPUT, format="turtle")

    assert len(graph) == 821


def test_integrated_kg_exporter_writes_parseable_turtle_and_report(tmp_path):
    output = tmp_path / "integrated.ttl"
    report_path = tmp_path / "integrated.report.json"

    summary = IntegratedKGExporter().export(output=output, report_path=report_path)

    graph = Graph()
    graph.parse(output, format="turtle")

    assert len(graph) == 821
    assert summary.triples == 821
    assert summary.sources_loaded == ["research/01_ontology/immune_care_ontology.owl"]
    assert "research/02_data_pipeline/rdf_output/nhis_disease_instances.ttl" in summary.optional_missing
    assert report_path.exists()


def test_integrated_kg_exporter_reports_invalid_optional_source(tmp_path):
    invalid_optional = tmp_path / "invalid.ttl"
    invalid_optional.write_text("@prefix broken: <", encoding="utf-8")

    output = tmp_path / "integrated.ttl"
    report_path = tmp_path / "integrated.report.json"

    summary = IntegratedKGExporter(optional_sources=[invalid_optional]).export(
        output=output,
        report_path=report_path,
    )

    graph = Graph()
    graph.parse(output, format="turtle")

    assert len(graph) == 821
    assert summary.optional_invalid
    assert str(invalid_optional) in summary.optional_invalid[0]


def test_invalid_optional_source_does_not_partially_contaminate_graph(tmp_path):
    invalid_optional = tmp_path / "partially-invalid.ttl"
    invalid_optional.write_text(
        """
        @prefix ex: <http://example.org/> .
        ex:s ex:p ex:o .
        @prefix broken: <
        """,
        encoding="utf-8",
    )
    output = tmp_path / "integrated.ttl"
    report_path = tmp_path / "integrated.report.json"

    summary = IntegratedKGExporter(optional_sources=[invalid_optional]).export(
        output=output,
        report_path=report_path,
    )

    graph = Graph()
    graph.parse(output, format="turtle")

    assert summary.optional_invalid
    assert len(graph) == 821
    assert (None, None, None) in graph
    assert not any(str(subject).startswith("http://example.org/") for subject in graph.subjects())


def test_integrated_kg_exporter_hard_fails_missing_core_without_output(tmp_path):
    output = tmp_path / "integrated.ttl"
    report_path = tmp_path / "integrated.report.json"

    with pytest.raises(ValueError, match="Required source"):
        IntegratedKGExporter(core_source=tmp_path / "missing.owl").export(
            output=output,
            report_path=report_path,
        )

    assert not output.exists()
    assert not report_path.exists()

"""Integrated knowledge graph export from validated ontology sources."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from rdflib import Graph

from project_columbus.ontology.validator import OntologyValidator


CORE_OWL = Path("research/01_ontology/immune_care_ontology.owl")
OPTIONAL_SOURCES = (
    Path("research/02_data_pipeline/rdf_output/nhis_disease_instances.ttl"),
)


@dataclass(frozen=True)
class IntegratedKGSummary:
    output: str
    report_path: str
    triples: int
    sources_loaded: list[str]
    optional_missing: list[str]
    optional_invalid: list[str]


class IntegratedKGExporter:
    def __init__(
        self,
        core_source: str | Path = CORE_OWL,
        optional_sources: list[str | Path] | tuple[str | Path, ...] = OPTIONAL_SOURCES,
    ) -> None:
        self.core_source = Path(core_source)
        self.optional_sources = tuple(Path(source) for source in optional_sources)

    def export(
        self,
        output: str | Path = Path("research/01_ontology/integrated_knowledge_graph.ttl"),
        report_path: str | Path = Path("research/01_ontology/integrated_knowledge_graph.report.json"),
    ) -> IntegratedKGSummary:
        output = Path(output)
        report_path = Path(report_path)

        graph = Graph()
        sources_loaded: list[str] = []
        optional_missing: list[str] = []
        optional_invalid: list[str] = []

        self._load_required_core(graph, sources_loaded)
        self._load_optional_sources(graph, sources_loaded, optional_missing, optional_invalid)

        output.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        temp_output = output.with_suffix(output.suffix + ".tmp")
        graph.serialize(destination=str(temp_output), format="turtle")

        reparsed = Graph()
        reparsed.parse(temp_output, format="turtle")
        validation_report = OntologyValidator().validate_file(temp_output, rdf_format="turtle")
        if not validation_report.ok:
            messages = "; ".join(issue.message for issue in validation_report.errors)
            temp_output.unlink(missing_ok=True)
            raise ValueError(f"Integrated KG failed validation: {messages}")

        os.replace(temp_output, output)

        summary = IntegratedKGSummary(
            output=str(output),
            report_path=str(report_path),
            triples=len(reparsed),
            sources_loaded=sources_loaded,
            optional_missing=optional_missing,
            optional_invalid=optional_invalid,
        )
        report_path.write_text(
            json.dumps(asdict(summary), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return summary

    def _load_required_core(self, graph: Graph, sources_loaded: list[str]) -> None:
        report = OntologyValidator().validate_file(self.core_source, rdf_format="xml")
        if not report.ok:
            messages = "; ".join(issue.message for issue in report.errors)
            raise ValueError(f"Required source failed validation: {self.core_source}: {messages}")

        graph.parse(self.core_source, format="xml")
        sources_loaded.append(str(self.core_source))

    def _load_optional_sources(
        self,
        graph: Graph,
        sources_loaded: list[str],
        optional_missing: list[str],
        optional_invalid: list[str],
    ) -> None:
        for source in self.optional_sources:
            if not source.exists():
                optional_missing.append(str(source))
                continue
            if source.stat().st_size == 0:
                optional_invalid.append(f"{source}: empty RDF source")
                continue

            optional_graph = Graph()
            try:
                optional_graph.parse(source, format="turtle")
            except Exception as exc:  # noqa: BLE001 - rdflib raises parser-specific exceptions
                optional_invalid.append(f"{source}: {exc}")
                continue

            graph += optional_graph
            sources_loaded.append(str(source))

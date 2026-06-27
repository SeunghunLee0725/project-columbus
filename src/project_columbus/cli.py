"""Command-line interface for Project Columbus utilities."""

from __future__ import annotations

import argparse
from pathlib import Path

from project_columbus.ontology.integrated_export import IntegratedKGExporter
from project_columbus.ontology.validator import OntologyValidator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="columbus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-ontology")
    validate_parser.add_argument("path")
    validate_parser.add_argument("--format", dest="rdf_format", choices=("xml", "turtle"))

    export_parser = subparsers.add_parser("export-integrated-kg")
    export_parser.add_argument(
        "--output",
        default="research/01_ontology/integrated_knowledge_graph.ttl",
    )
    export_parser.add_argument(
        "--report",
        default="research/01_ontology/integrated_knowledge_graph.report.json",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if args.command == "validate-ontology":
        return _validate_ontology(Path(args.path), args.rdf_format)

    if args.command == "export-integrated-kg":
        return _export_integrated_kg(Path(args.output), Path(args.report))

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _validate_ontology(path: Path, rdf_format: str | None) -> int:
    report = OntologyValidator().validate_file(path, rdf_format=rdf_format)
    if report.ok and report.stats is not None:
        version = ",".join(report.stats.version_info) if report.stats.version_info else "unknown"
        print(
            "OK "
            f"triples={report.stats.triples} "
            f"classes={report.stats.owl_classes} "
            f"causal_pathways={report.stats.causal_pathways} "
            f"version={version}"
        )
        return 0

    for issue in report.errors:
        subject = f" subject={issue.subject}" if issue.subject else ""
        print(f"{issue.severity.upper()} {issue.code}: {issue.message}{subject}")
    return 1


def _export_integrated_kg(output: Path, report_path: Path) -> int:
    try:
        summary = IntegratedKGExporter().export(output=output, report_path=report_path)
    except ValueError as exc:
        print(f"ERROR EXPORT_FAILED: {exc}")
        return 1

    print(
        "OK "
        f"triples={summary.triples} "
        f"sources={len(summary.sources_loaded)} "
        f"optional_missing={len(summary.optional_missing)} "
        f"optional_invalid={len(summary.optional_invalid)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

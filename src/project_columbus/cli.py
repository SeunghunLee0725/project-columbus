"""Command-line interface for Project Columbus utilities."""

from __future__ import annotations

import argparse
from pathlib import Path

from project_columbus.ontology.validator import OntologyValidator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="columbus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-ontology")
    validate_parser.add_argument("path")
    validate_parser.add_argument("--format", dest="rdf_format", choices=("xml", "turtle"))

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if args.command == "validate-ontology":
        return _validate_ontology(Path(args.path), args.rdf_format)

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


if __name__ == "__main__":
    raise SystemExit(main())

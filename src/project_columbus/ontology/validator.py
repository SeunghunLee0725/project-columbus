"""Structural validation for ontology artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from rdflib import Literal, URIRef
from rdflib.namespace import OWL, RDF

from project_columbus.ontology.loader import OntologyLoader, OntologyRepository
from project_columbus.ontology.models import ValidationIssue, ValidationReport
from project_columbus.ontology.namespaces import ICO


REQUIRED_CLASSES = ("EnvironmentalFactor", "Biomarker", "ImmuneDisease", "CausalPathway")
REQUIRED_OBJECT_PROPERTIES = ("hasSourceFactor", "hasTargetFactor", "involvesPathway")


class OntologyValidator:
    def validate_file(self, path: str | Path, rdf_format: str | None = None) -> ValidationReport:
        try:
            repo = OntologyLoader().load(path, rdf_format=rdf_format)
        except Exception as exc:  # noqa: BLE001 - parser exceptions vary by rdflib backend
            issue = ValidationIssue(
                code="PARSE_ERROR",
                severity="error",
                message=f"Failed to parse {path}: {exc}",
            )
            return ValidationReport(ok=False, errors=[issue], warnings=[], stats=None)

        errors = list(self._validate_required_terms(repo))
        errors.extend(self._validate_causal_pathways(repo))

        return ValidationReport(
            ok=not errors,
            errors=errors,
            warnings=[],
            stats=repo.stats(),
        )

    def _validate_required_terms(self, repo: OntologyRepository) -> Iterable[ValidationIssue]:
        stats = repo.stats()
        if not stats.version_info:
            yield ValidationIssue(
                code="MISSING_VERSION",
                severity="error",
                message="Ontology has no owl:versionInfo.",
            )

        for local_name in REQUIRED_CLASSES:
            uri = URIRef(str(ICO[local_name]))
            if (uri, RDF.type, OWL.Class) not in repo.graph:
                yield ValidationIssue(
                    code="MISSING_CLASS_TYPE",
                    severity="error",
                    message=f"Required class ico:{local_name} is missing owl:Class type.",
                    subject=str(uri),
                )

        for local_name in REQUIRED_OBJECT_PROPERTIES:
            uri = URIRef(str(ICO[local_name]))
            if (uri, RDF.type, OWL.ObjectProperty) not in repo.graph:
                yield ValidationIssue(
                    code="MISSING_OBJECT_PROPERTY_TYPE",
                    severity="error",
                    message=(
                        f"Required object property ico:{local_name} is missing "
                        "owl:ObjectProperty type."
                    ),
                    subject=str(uri),
                )

    def _validate_causal_pathways(self, repo: OntologyRepository) -> Iterable[ValidationIssue]:
        for pathway in set(repo.graph.subjects(RDF.type, ICO.CausalPathway)):
            has_source = (pathway, ICO.hasSourceFactor, None) in repo.graph
            has_target = (pathway, ICO.hasTargetFactor, None) in repo.graph

            if not has_source and not _is_documented_source_exception(str(pathway)):
                yield ValidationIssue(
                    code="MISSING_SOURCE_FACTOR",
                    severity="error",
                    message="CausalPathway is missing ico:hasSourceFactor.",
                    subject=str(pathway),
                )

            if not has_target and not _is_documented_target_exception(str(pathway)):
                yield ValidationIssue(
                    code="MISSING_TARGET_FACTOR",
                    severity="error",
                    message="CausalPathway is missing ico:hasTargetFactor.",
                    subject=str(pathway),
                )

            for value in repo.graph.objects(pathway, ICO.hasCorrelationCoefficient):
                if not isinstance(value, Literal) or _literal_float(value) is None:
                    yield ValidationIssue(
                        code="INVALID_CORRELATION",
                        severity="error",
                        message="CausalPathway correlation is not numeric.",
                        subject=str(pathway),
                    )


def _is_documented_source_exception(uri: str) -> bool:
    local_name = uri.split("#")[-1]
    return local_name in {
        "CAP_Nrf2_Activation_Path",
        "CompositeScore_to_AllergicMarch_Path",
    }


def _is_documented_target_exception(uri: str) -> bool:
    local_name = uri.split("#")[-1]
    return local_name in {"CAP_Nrf2_Activation_Path"}


def _literal_float(value: Literal) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

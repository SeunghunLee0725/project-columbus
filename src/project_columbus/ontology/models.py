"""Typed models for ontology package boundaries."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OntologyStats:
    triples: int
    owl_classes: int
    object_properties: int
    datatype_properties: int
    named_individuals: int
    causal_pathways: int
    version_info: list[str]


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    message: str
    subject: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    stats: OntologyStats | None = None

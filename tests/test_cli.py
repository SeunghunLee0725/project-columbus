from project_columbus.cli import main


def test_validate_ontology_cli_success(capsys):
    exit_code = main(
        [
            "validate-ontology",
            "research/01_ontology/immune_care_ontology.owl",
            "--format",
            "xml",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK" in captured.out
    assert "causal_pathways=19" in captured.out


def test_validate_ontology_cli_failure(capsys):
    exit_code = main(
        [
            "validate-ontology",
            "research/01_ontology/integrated_knowledge_graph.ttl",
            "--format",
            "turtle",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "PARSE_ERROR" in captured.out


def test_validate_ontology_cli_rejects_unsupported_format(capsys):
    exit_code = main(
        [
            "validate-ontology",
            "research/01_ontology/immune_care_ontology.owl",
            "--format",
            "json-ld",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "invalid choice" in captured.err

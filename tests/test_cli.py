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


def test_validate_integrated_ontology_cli_success(capsys):
    exit_code = main(
        [
            "validate-ontology",
            "research/01_ontology/integrated_knowledge_graph.ttl",
            "--format",
            "turtle",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK" in captured.out
    assert "causal_pathways=19" in captured.out


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


def test_export_integrated_kg_cli_writes_output_and_report(tmp_path, capsys):
    output = tmp_path / "integrated.ttl"
    report = tmp_path / "integrated.report.json"

    exit_code = main(
        [
            "export-integrated-kg",
            "--output",
            str(output),
            "--report",
            str(report),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK" in captured.out
    assert "triples=821" in captured.out
    assert output.exists()
    assert report.exists()

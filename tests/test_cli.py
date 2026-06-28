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


def test_calibrate_evidence_cli_writes_output_and_report(tmp_path, capsys):
    csv_path = tmp_path / "correlation_summary.csv"
    csv_path.write_text(
        "\n".join(
            [
                "env_var,disease,lag_months,mean_pearson_r,mean_spearman_r,pct_significant",
                "avg_pm25,asthma,0,0.52,0.49,88",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "calibrated.owl"
    report = tmp_path / "calibration.report.json"

    exit_code = main(
        [
            "calibrate-evidence",
            "--source-owl",
            "research/01_ontology/immune_care_ontology.owl",
            "--correlation-csv",
            str(csv_path),
            "--output-owl",
            str(output),
            "--report",
            str(report),
            "--calibration-date",
            "2026-06-28",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK" in captured.out
    assert "calibrated=1" in captured.out
    assert output.exists()
    assert report.exists()


def test_generate_nhis_rdf_cli_writes_output_and_report(tmp_path, capsys):
    csv_path = tmp_path / "correlation_summary.csv"
    csv_path.write_text(
        "\n".join(
            [
                "disease,env_var,lag_months,mean_pearson_r,mean_spearman_r,pct_significant",
                "asthma,avg_pm25,0,0.52,0.49,88",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "nhis.ttl"
    report = tmp_path / "nhis.report.json"

    exit_code = main(
        [
            "generate-nhis-rdf",
            "--correlation-csv",
            str(csv_path),
            "--output",
            str(output),
            "--report",
            str(report),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK" in captured.out
    assert "instances=1" in captured.out
    assert output.exists()
    assert report.exists()

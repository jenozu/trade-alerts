from pathlib import Path

from scripts.archive_experiment import archive_experiment


def test_archive_experiment_copies_allowed_files_and_writes_manifest(tmp_path: Path) -> None:
    source = tmp_path / "reports"
    source.mkdir()
    (source / "report.md").write_text("# report\n", encoding="utf-8")
    (source / "metrics.json").write_text('{"trades": 10}\n', encoding="utf-8")
    (source / "table.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (source / "large.parquet").write_bytes(b"not-real-parquet")
    (source / "api_token.txt").write_text("do-not-copy", encoding="utf-8")

    destination_root = tmp_path / "research-archive"
    manifest = archive_experiment("EXP-999", source, destination_root)

    destination = destination_root / "EXP-999"
    assert (destination / "report.md").exists()
    assert (destination / "metrics.json").exists()
    assert (destination / "table.csv").exists()
    assert not (destination / "large.parquet").exists()
    assert not (destination / "api_token.txt").exists()
    assert (destination / "ARCHIVE_MANIFEST.json").exists()
    assert manifest["archived_file_count"] == 3
    skipped_reasons = {item["path"]: item["reason"] for item in manifest["skipped"]}
    assert skipped_reasons["large.parquet"] == "unsupported_suffix"
    assert skipped_reasons["api_token.txt"] == "sensitive_filename"


def test_archive_experiment_dry_run_does_not_write(tmp_path: Path) -> None:
    source = tmp_path / "reports"
    source.mkdir()
    (source / "report.md").write_text("# report\n", encoding="utf-8")

    destination_root = tmp_path / "research-archive"
    manifest = archive_experiment("EXP-998", source, destination_root, dry_run=True)

    assert manifest["archived_file_count"] == 1
    assert not destination_root.exists()

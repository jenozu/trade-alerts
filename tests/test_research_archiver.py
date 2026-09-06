from __future__ import annotations

from pathlib import Path

from scripts.archive_research_run import safe_label, sha256_file


def test_safe_label_sanitizes_spaces_and_symbols():
    assert safe_label("2025 baseline / warmup") == "2025-baseline-warmup"


def test_sha256_file_is_stable(tmp_path: Path):
    path = tmp_path / "sample.txt"
    path.write_text("trade-alerts\n", encoding="utf-8")
    assert sha256_file(path) == "6ab45581d07bcc809200ae327b2e17cf8d4d90d1c3f40baf5ff596182b3a2e96"

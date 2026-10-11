"""Static guard: the diagnostic MNQ reversal strategy preserves V2 trade logic.

This does NOT compile Pine or verify TradingView's broker emulator.
Run: python -m pytest tradingview/tests/test_v2_diagnostics_source_parity.py
"""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "strategies" / "nq_sweep_reversal_v2_research.pine"
DIAGNOSTIC = ROOT / "strategies" / "nq_sweep_reversal_v2_diagnostics.pine"
SECTIONS = ("INPUTS", "PRE_SNAPSHOT", "OBSERVATIONS")


def _section(source: str, name: str) -> str:
    matches = re.findall(
        rf"(?ms)^// DIAG-ONLY BEGIN: {name}\n(.*?)^// DIAG-ONLY END: {name}\n?",
        source,
    )
    assert len(matches) == 1, f"Missing/duplicate diagnostics section {name}"
    return matches[0]


def _strip(source: str) -> str:
    for name in SECTIONS:
        section = _section(source, name)
        source = source.replace(
            f"// DIAG-ONLY BEGIN: {name}\n{section}// DIAG-ONLY END: {name}\n",
            "",
            1,
        )
    source = source.replace(
        'strategy("MNQ Strategy V2 | Sweep Reversal (Diagnostics)", shorttitle="MNQ V2 DX",',
        'strategy("MNQ Strategy V2 | Sweep Reversal (Research)", shorttitle="MNQ REV v2",',
        1,
    )
    return re.sub(r"\n{3,}", "\n\n", source).rstrip() + "\n"


def test_trading_logic_exactly_matches_original_after_stripping_diagnostics() -> None:
    original = ORIGINAL.read_text(encoding="utf-8")
    diagnostic = DIAGNOSTIC.read_text(encoding="utf-8")
    normalized = re.sub(r"\n{3,}", "\n\n", original).rstrip() + "\n"
    assert _strip(diagnostic) == normalized


def test_no_order_or_base_state_writes_within_diagnostic_sections() -> None:
    source = DIAGNOSTIC.read_text(encoding="utf-8")
    for name in SECTIONS:
        body = _section(source, name)
        # Only diagnostics counters/variables may be assigned inside these blocks.
        assert not re.search(r"\bstrategy\s*\.\s*(?:entry|exit|close|order|cancel|cancel_all)\s*\(", body)
        assert not re.search(
            r"\b(?:longStage|shortStage|triggerLong|triggerShort|coreLong|coreShort|"
            r"longSweepBar|shortSweepBar|longMssBar|shortMssBar|longFvgBar|shortFvgBar|"
            r"longFvgLower|longFvgUpper|shortFvgLower|shortFvgUpper)\s*:=",
            body,
        )


def test_diagnostic_includes_terminal_and_nonterminal_failure_categories() -> None:
    source = DIAGNOSTIC.read_text(encoding="utf-8")
    for expected in (
        "diagLongExpired", "diagShortExpired",
        "diagLongInvalid", "diagShortInvalid",
        "diagLongWindowBlocked", "diagShortWindowBlocked",
        "diagLongPositionBlocked", "diagShortPositionBlocked",
        "diagLongRestart", "diagShortRestart",
        "diagRolloverLong", "diagRolloverShort",
        "diagLongDisplaced", "diagShortDisplaced",
        "diagLongFvg", "diagShortFvg",
        "display=display.data_window",
    ):
        assert expected in source

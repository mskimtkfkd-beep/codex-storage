from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.sheets_writer import format_run_sheet_title, parse_run_sheet_title, unique_sheet_title


KST = timezone(timedelta(hours=9), name="KST")


def test_format_run_sheet_title_uses_mmdd_hour_minute() -> None:
    now = datetime(2026, 5, 24, 8, 5, tzinfo=KST)

    assert format_run_sheet_title(now) == "0524 08:05"


def test_unique_sheet_title_adds_suffix_for_same_minute_runs() -> None:
    existing = {"0524 08:05", "0524 08:05 (2)"}

    assert unique_sheet_title("0524 08:05", existing) == "0524 08:05 (3)"


def test_parse_run_sheet_title_handles_suffix() -> None:
    now = datetime(2026, 5, 24, 8, 5, tzinfo=KST)

    assert parse_run_sheet_title("0524 08:05 (2)", now) == now

import pytest

from main import build_report, validate_row


def test_large_daily_change_creates_alert() -> None:
    rows = [
        {
            "timestamp": "2026-01-01",
            "open": "100",
            "high": "102",
            "low": "99",
            "close": "100",
            "volume": "1000",
        },
        {
            "timestamp": "2026-01-02",
            "open": "110",
            "high": "112",
            "low": "109",
            "close": "110",
            "volume": "1200",
        },
    ]

    report = build_report(rows, alert_threshold_pct=5.0)

    assert report[0]["alert"] == "none"
    assert report[1]["alert"] == "large_daily_change"


def test_inconsistent_ohlc_values_are_rejected() -> None:
    row = {
        "timestamp": "2026-01-01",
        "open": "100",
        "high": "99",
        "low": "98",
        "close": "100",
        "volume": "1000",
    }

    with pytest.raises(ValueError, match="Inconsistent OHLC"):
        validate_row(row, 2)


def test_invalid_window_is_rejected() -> None:
    with pytest.raises(ValueError, match="window"):
        build_report([], window=1)


def test_non_finite_market_values_are_rejected() -> None:
    row = {
        "timestamp": "2026-01-01",
        "open": "100",
        "high": "102",
        "low": "99",
        "close": "nan",
        "volume": "1000",
    }
    with pytest.raises(ValueError, match="finite"):
        validate_row(row, 2)


def test_non_finite_alert_threshold_is_rejected() -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        build_report([], alert_threshold_pct=float("inf"))

"""Educational OHLCV analytics with transparent, non-trading alerts."""

import argparse
import csv
from collections import deque
from pathlib import Path


REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain columns: {sorted(REQUIRED_COLUMNS)}")
        return list(reader)


def validate_row(row: dict[str, str], line_number: int) -> dict[str, float | str]:
    try:
        open_price = float(row["open"])
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])
        volume = float(row["volume"])
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid numeric value on CSV row {line_number}") from error

    if min(open_price, high, low, close) <= 0 or volume < 0:
        raise ValueError(f"Prices must be positive and volume non-negative on row {line_number}")
    if high < max(open_price, close) or low > min(open_price, close) or high < low:
        raise ValueError(f"Inconsistent OHLC values on row {line_number}")

    return {
        "timestamp": row["timestamp"],
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def build_report(
    rows: list[dict[str, str]], window: int = 3, alert_threshold_pct: float = 5.0
) -> list[dict[str, str | float]]:
    if window < 2:
        raise ValueError("Moving-average window must be at least 2.")
    if alert_threshold_pct <= 0:
        raise ValueError("Alert threshold must be positive.")

    validated = [validate_row(row, index + 2) for index, row in enumerate(rows)]
    closes: deque[float] = deque(maxlen=window)
    report = []
    previous_close = None

    for row in validated:
        close = float(row["close"])
        closes.append(close)
        moving_average = sum(closes) / len(closes)
        change_pct = (
            ((close - previous_close) / previous_close) * 100
            if previous_close is not None
            else 0.0
        )
        alert = (
            "large_daily_change"
            if abs(change_pct) >= alert_threshold_pct
            else "none"
        )

        report.append(
            {
                "timestamp": str(row["timestamp"]),
                "close": close,
                "volume": float(row["volume"]),
                "moving_average": moving_average,
                "change_pct": change_pct,
                "alert": alert,
            }
        )
        previous_close = close

    return report


def write_report(rows: list[dict[str, str | float]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "timestamp",
        "close",
        "volume",
        "moving_average",
        "change_pct",
        "alert",
    ]
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze historical OHLCV data.")
    parser.add_argument("input", type=Path, help="Input OHLCV CSV file")
    parser.add_argument("--output", type=Path, default=Path("reports/market_report.csv"))
    parser.add_argument("--window", type=int, default=3, help="Moving-average window")
    parser.add_argument(
        "--alert-threshold-pct",
        type=float,
        default=5.0,
        help="Absolute daily percentage change that triggers an alert",
    )
    args = parser.parse_args()

    report = build_report(
        read_rows(args.input),
        window=args.window,
        alert_threshold_pct=args.alert_threshold_pct,
    )
    write_report(report, args.output)
    print(f"Processed {len(report)} rows. Report saved to {args.output}")


if __name__ == "__main__":
    main()

# Market Intelligence & Risk Analytics

An educational data-processing project that reads OHLCV records and produces transparent monitoring indicators and rule-based alerts.

## Features

- Validate historical OHLCV rows
- Calculate moving averages and daily price changes
- Flag unusually large price changes using a configurable threshold
- Export a CSV report with the derived indicators
- Test input validation and alert behavior

## Run

Python 3.11+; no third-party packages are required.

    python main.py data/sample_ohlcv.csv --output reports/market_report.csv --window 3 --alert-threshold-pct 5

## Tests

Install pytest and run:

    python -m pip install pytest
    python -m pytest

## Data

The included CSV is synthetic sample data created for software testing. It is not live market data.

## Important note

This project is an engineering demonstration, not investment advice and not a trading system. Alerts describe data conditions only; they do not recommend buying or selling assets.

## Roadmap

- [ ] Add a FastAPI read-only reporting endpoint
- [ ] Add a dashboard after the data pipeline is verified

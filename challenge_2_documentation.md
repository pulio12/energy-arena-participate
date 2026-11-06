# Challenge Documentation: Real-time forecasting of day-ahead electricity prices in the Germany-Luxembourg bidding zone

Compiled by the Energy-Arena challenge generator for the Energy-Arena challenge team.

Generated from challenge configuration 2 (Day-Ahead Prices | Germany-Luxembourg | Point Forecast).

## Background

Forecasts of day-ahead electricity prices play an important role in modern power systems and electricity markets. In day-ahead auctions, electricity for the following delivery day is traded before physical delivery, so market participants must form expectations about future prices in advance of bidding. Accurate forecasts support trading, risk management, and resource allocation.

Electricity prices reflect the anticipated balance between demand and available generation and are shaped by renewable output, conventional generation, cross-border exchange, outages, and weather-dependent demand. These drivers can interact in highly nonlinear ways and can produce both negative prices and sharp price spikes. A transparent benchmark is therefore useful for comparing methods under realistic operational conditions.

The present project establishes a real-time forecasting challenge on the Energy-Arena platform. The aim is to create a standardized and transparent framework for collecting, comparing, and evaluating forecasts from different models under realistic operational constraints.

## Forecast targets and submission

### Online forecast platform

Forecasts are collected via the Energy-Arena platform through an API-based submission system. Participants generate forecasts with their own infrastructure and submit them to the platform for validation, storage, and scoring. Participants may additionally provide a short description of their approach through the dashboard.

### Forecast submission schedule

Forecasts are submitted on a daily basis. Submissions are accepted from 7 days before the deadline. The configured operational deadline label is 12:00 CET/CEST, and the first scheduled deadline is January 14, 2026 at 12:00 CET/CEST. The first configured target period starts on January 15, 2026 at 00:00 CET/CEST. Multiple submissions within this window are permitted, and the latest valid submission received before the deadline is used for evaluation. Late submissions are rejected.

### Forecast locations

The present challenge is restricted to the Germany-Luxembourg bidding zone (DE_LU). This keeps the benchmark focused on a single operational area and allows direct comparison of model performance under one consistent target definition.

### Forecast targets

The forecasting target is day-ahead electricity prices in the Germany-Luxembourg bidding zone. The target unit is EUR/MWh. Forecasts refer to the configured target period beginning at 00:00 CET/CEST and extending over 1 day. The target period is defined as a calendar day in the timezone Europe/Berlin, and the interval end is treated as exclusive.

Temporal resolution and the exact timestamp grid are not configured separately from the data source. Instead, they are implicitly defined by the ground-truth source and the platform's timezone-aware slicing of each target period. Daylight saving time transitions are therefore handled implicitly on the source-defined timestamp grid as well; target periods on DST transition days may contain fewer or more timestamps as implied by the published source data and the configured timezone.

Participants are required to submit one point forecast per timestamp.

### Data sources

Ground truth data are obtained from ENTSO-E using the dataset "ENTSO-E Energy Prices [12.1.D]". The configured request parameters are documentType=A44, contract_MarketAgreement.type=A01, classificationSequence_AttributeInstanceComponent.position=1. For DE_LU, the configured area mapping is in_Domain=10Y1001A1001A82H, out_Domain=10Y1001A1001A82H. This corresponds to article 12.1.D. For public browser views, the platform may additionally expose the configured SMARD Day-ahead Prices mirror described at https://www.smard.de/en/downloadcenter/download-market-data.

### Information set

Participants may use any information available before the submission deadline. The challenge is model-agnostic with respect to methods and input data, provided that forecasts are generated within the admissible real-time information set.

## Forecast evaluation

Forecasts are evaluated using RMSE and R2. The primary evaluation metric is RMSE, which determines leaderboard ranking. RMSE is used as the primary ranking metric because it assigns greater weight to large forecast errors and is therefore sensitive to extreme deviations. Scores are computed per target period and aggregated over time by arithmetic averaging within rolling leaderboard windows. The configured aggregation windows are Last day, Last 7 days, Last 30 days, Last 90 days, and Last 180 days.

For point forecasts, the reported error metrics compare the realized and predicted values over the full target period on the source-defined timestamp grid.

Missing submissions are not ignored. If a participant fails to provide a valid forecast for a scheduled deadline, the corresponding result is replaced by the performance of the configured baseline model. This prevents selective non-submission on difficult periods and preserves comparability across participants.

## Baseline model

The baseline model is a persistence benchmark in which the forecast for each target timestamp is given by the realized value from Day - 1, measured relative to the current target day or, more generally, relative to the start of the current target period rather than the submission time. This baseline also serves as the imputation rule for missing forecasts.

The phrase "Day - 1" refers to the start of the current target period. If the first candidate historical target period is missing or contains null ground-truth values, progressively older admissible target periods are tried. Under the current platform default used by generator-backed challenges, if no usable historical slice is available at all, the benchmark falls back to a zero-valued forecast on the canonical target grid.

## Handling of data revisions

Forecasts are evaluated against the latest available version of the configured ground truth data. If the underlying data provider revises historical values, the platform may recompute historical scores accordingly. This keeps the benchmark aligned with the authoritative source rather than a frozen snapshot.

## Submission format

Each submission must contain a complete and non-empty set of forecast values for the configured target period. Values must be finite numeric values expressed in EUR/MWh. The configured numeric precision is 2 decimal places, and negative values are allowed. Duplicate timestamps are not permitted, timestamps must match the configured target period, and submissions that violate the structural limits of the challenge are rejected. The challenge currently allows up to 100 forecast points per submission.

## Participation rules

Participants submit forecasts through the Energy-Arena API while the implementation of forecasting models remains external to the platform. The challenge is therefore model-agnostic with respect to methodology. Participants may update or refine their models over time, and they may optionally provide methodological descriptions or links through the dashboard. Forecast visibility can be configured as closed, open after evaluation, or open immediately so that aggregated performance can be reported even when underlying forecast values are not made public.

## Evaluation period

The challenge operates as a continuous real-time forecasting exercise. The first configured target period starts on January 15, 2026 at 00:00 CET/CEST, and evaluation continues on the configured cadence without a pre-specified end date. Leaderboard windows are rolling and are recomputed whenever newly scored target periods become available. Within each displayed rolling window, participant ranking is determined solely by the configured primary metric. Public reporting therefore emphasizes rolling performance windows rather than a single closed evaluation sample.

## Summary

This challenge documentation defines the operational rules for the challenge "Day-Ahead Prices | Germany-Luxembourg | Point Forecast". By fixing the target definition, submission schedule, validation rules, baseline handling, and evaluation metrics in advance, it provides a transparent and reproducible benchmark for comparing forecasting methods under live conditions.


 Run these from the repo root (C:\Users\Pulin\Desktop\energy-arena-participate) in PowerShell. They use the .venv that uv manages.

    1. Backtest (optional sanity check)
    .venv\Scripts\python run_backtest.py --start_date 01-10-2026 --days 30 --country DE_LU
    - It prints RMSE and R² for the ensemble against Day-1 and Day-7 persistence.
    - The first run for an area downloads about 18 months of history and caches it in data_cache\. That can take several minutes.
    - The ensemble should have a lower RMSE than persistence.

    2. See what's open and when it closes
    .venv\Scripts\python run_forecast_model.py --list_open_challenges
    - Note the challenge ID for the area you want. Challenge 2 is DE_LU day-ahead prices, point forecast.
    - Note the deadline: 12:00 CET on the day before the target day.

    3. Generate the forecast payload
    .venv\Scripts\python run_forecast_model.py --target_date 07-11-2026 --challenge_id 2 --save_payload payload_2026-11-07.json
    
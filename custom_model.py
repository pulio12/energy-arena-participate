from __future__ import annotations

from datetime import date, datetime
import traceback

import numpy as np
import pandas as pd

import data_cache
from forecast_core import TZ, Ensemble, build_rows


def _delivery_day(target_start: datetime) -> pd.Timestamp:
    ts = pd.Timestamp(target_start)
    ts = ts.tz_localize(TZ) if ts.tzinfo is None else ts.tz_convert(TZ)
    return ts.normalize().tz_localize(None)


def _step_hours(day: pd.Timestamp, n: int) -> np.ndarray:
    """Local hour-of-day for each of the n payload steps (handles 92/96/100-step DST days)."""
    start = day.tz_localize(TZ)
    end = (day + pd.Timedelta(days=1)).tz_localize(TZ)
    step = (end.tz_convert("UTC") - start.tz_convert("UTC")) / n
    stamps = [(start.tz_convert("UTC") + i * step).tz_convert(TZ) for i in range(n)]
    return np.array([t.hour for t in stamps])


def transform_payload(
    payload: dict,
    *,
    target_date: date,
    target_start: datetime,
    challenge_id: str,
    area: str,
    entsoe_api_key: str,
    api_base: str,
    data_source: str,
    challenge_context,
    challenge_detail: dict,
    forecast_objective: str,
    tz_name: str,
) -> dict:
    if forecast_objective != "point":
        return payload

    area = area or "DE_LU"
    try:
        day = _delivery_day(target_start)
        # Only data published before the D-1 deadline is used; train on fully known days (<= D-2).
        df = data_cache.load_area(area)
        days = list(pd.date_range(day - pd.Timedelta(days=500), day))
        rows = build_rows(df, days)
        train = rows[rows["date"] <= day - pd.Timedelta(days=2)]
        target = rows[rows["date"] == day]
        if len(train) < 24 * 60 or len(target) != 24:
            raise ValueError(f"insufficient data for {area} {day.date()}: train={len(train)}, target={len(target)}")

        by_hour = Ensemble().fit(train).predict(target)  # 24 values, local hour 0..23
        n = len(payload["values"])
        preds = by_hour[_step_hours(day, n)]
    except Exception:
        # Keep the starter baseline (Day-1 persistence) already in the payload rather than failing.
        print(f"\n--- MODEL ERROR ({area}): keeping baseline values ---")
        traceback.print_exc()
        return payload

    for i, original in enumerate(payload["values"]):
        v = round(float(preds[i]), 2)
        payload["values"][i] = [v for _ in original] if isinstance(original, list) else v
    return payload

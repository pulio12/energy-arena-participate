"""Hourly ENTSO-E dataset (prices + day-ahead forecasts) cached per area as parquet."""
from __future__ import annotations

import os
import time

import pandas as pd
from dotenv import load_dotenv
from entsoe import EntsoePandasClient

CACHE_DIR = "data_cache"
AREA_MAP = {"DK1": "DK_1", "DK2": "DK_2"}


def entsoe_code(area: str) -> str:
    return AREA_MAP.get(area, area)


def _hourly(obj) -> pd.DataFrame:
    if isinstance(obj, pd.Series):
        obj = obj.to_frame(obj.name or "value")
    obj = obj.copy()
    obj.index = pd.DatetimeIndex(obj.index).tz_convert("UTC")
    return obj.resample("1h").mean()


def _try(fn, *args, retries: int = 4, **kwargs):
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # missing series are common for small zones; 5xx are transient
            transient = "Server Error" in str(e)
            if not transient or attempt == retries - 1:
                print(f"  [warn] {fn.__name__} failed: {type(e).__name__}: {str(e)[:80]}")
                return None
            time.sleep(5 * 2 ** attempt)


def fetch_hourly(area: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Columns: price, load_fc, wind_fc, solar_fc (UTC hourly). Forecast columns may be NaN."""
    load_dotenv()
    client = EntsoePandasClient(api_key=os.environ["ENTSOE_API_KEY"])
    code = entsoe_code(area)
    out = pd.DataFrame()

    price = _try(client.query_day_ahead_prices, code, start=start, end=end)
    if price is None:
        raise RuntimeError(f"no price data for {code}")
    out["price"] = _hourly(price).iloc[:, 0]

    load = _try(client.query_load_forecast, code, start=start, end=end)
    if load is not None:
        out["load_fc"] = _hourly(load).iloc[:, 0]

    ws = _try(client.query_wind_and_solar_forecast, code, start=start, end=end, psr_type=None)
    if ws is not None:
        ws = _hourly(ws)
        out["solar_fc"] = ws[[c for c in ws.columns if "Solar" in str(c)]].sum(axis=1, min_count=1)
        out["wind_fc"] = ws[[c for c in ws.columns if "Wind" in str(c)]].sum(axis=1, min_count=1)
    return out


def load_area(area: str, end: pd.Timestamp | None = None, days: int = 540) -> pd.DataFrame:
    """Return cached hourly data, fetching only what is missing (in 90-day chunks)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{entsoe_code(area)}.csv")
    end = (end or pd.Timestamp.now(tz="UTC")).floor("h") + pd.Timedelta(days=2)
    cached = pd.read_csv(path, index_col=0, parse_dates=True) if os.path.exists(path) else pd.DataFrame()

    start = end - pd.Timedelta(days=days) if cached.empty else cached.index.max() - pd.Timedelta(days=3)
    frames = [cached] if not cached.empty else []
    cur = start
    while cur < end:
        nxt = min(cur + pd.Timedelta(days=90), end)
        print(f"fetching {area} {cur.date()} -> {nxt.date()}")
        frames.append(fetch_hourly(area, cur, nxt))
        cur = nxt
        part = pd.concat(frames)
        part[~part.index.duplicated(keep="last")].sort_index().to_csv(path)  # save progress per chunk
    df = pd.concat(frames)
    return df[~df.index.duplicated(keep="last")].sort_index()

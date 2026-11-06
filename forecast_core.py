"""Leak-free feature builder + models for day-ahead price forecasting.

One row = (delivery day D, hour h in Europe/Berlin). Only information available at the
12:00 CET deadline on D-1 is used: prices up to D-1, and day-ahead forecasts for D.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TZ = "Europe/Berlin"
FEATURES = [
    "p_d1", "p_d2", "p_d7", "d1_mean", "d1_min", "d1_max", "d7_mean",
    "load_fc", "wind_fc", "solar_fc", "resid_fc", "resid_d1",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos", "is_weekend",
]


def to_local_hourly(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.index = out.index.tz_convert(TZ)
    return out


def build_rows(df: pd.DataFrame, days: list[pd.Timestamp]) -> pd.DataFrame:
    """Feature rows for each local delivery day in `days` (tz-naive midnight dates).

    Prices are only read from days < D; forecast columns only for day D.
    """
    loc = to_local_hourly(df)
    loc["date"] = loc.index.normalize().tz_localize(None)
    loc["hour"] = loc.index.hour
    for c in ["load_fc", "wind_fc", "solar_fc"]:
        if c not in loc:
            loc[c] = np.nan
    loc["resid"] = loc["load_fc"] - loc["wind_fc"].fillna(0) - loc["solar_fc"].fillna(0)

    price = loc.pivot_table(index="date", columns="hour", values="price")
    resid = loc.pivot_table(index="date", columns="hour", values="resid")
    cols = {c: loc.pivot_table(index="date", columns="hour", values=c) for c in ["load_fc", "wind_fc", "solar_fc"]}

    rows = []
    for d in days:
        d = pd.Timestamp(d)
        d1, d2, d7 = d - pd.Timedelta(days=1), d - pd.Timedelta(days=2), d - pd.Timedelta(days=7)
        if d1 not in price.index:
            continue
        for h in range(24):
            def g(tbl, day):
                try:
                    return tbl.at[day, h]
                except KeyError:
                    return np.nan
            p1 = price.loc[d1]
            p7 = price.loc[d7] if d7 in price.index else pd.Series(dtype=float)
            dow = d.dayofweek
            r = {
                "date": d, "hour": h,
                "p_d1": g(price, d1), "p_d2": g(price, d2), "p_d7": g(price, d7),
                "d1_mean": p1.mean(), "d1_min": p1.min(), "d1_max": p1.max(),
                "d7_mean": p7.mean() if len(p7) else np.nan,
                "load_fc": g(cols["load_fc"], d), "wind_fc": g(cols["wind_fc"], d),
                "solar_fc": g(cols["solar_fc"], d),
                "resid_fc": g(resid, d), "resid_d1": g(resid, d1),
                "hour_sin": np.sin(2 * np.pi * h / 24), "hour_cos": np.cos(2 * np.pi * h / 24),
                "dow_sin": np.sin(2 * np.pi * dow / 7), "dow_cos": np.cos(2 * np.pi * dow / 7),
                "is_weekend": float(dow >= 5),
                "y": g(price, d),
            }
            rows.append(r)
    return pd.DataFrame(rows)


def _fill(X: pd.DataFrame, medians: pd.Series | None = None):
    medians = X.median() if medians is None else medians
    return X.fillna(medians).fillna(0.0), medians


class Ensemble:
    """LightGBM + ridge-style linear + small MLP, averaged. Trained on MSE (RMSE metric)."""

    def __init__(self, seeds: int = 3):
        self.seeds = seeds

    def fit(self, rows: pd.DataFrame):
        import lightgbm as lgb
        from sklearn.linear_model import RidgeCV
        from sklearn.preprocessing import StandardScaler

        rows = rows.dropna(subset=["y", "p_d1"])
        X, self.med = _fill(rows[FEATURES])
        y = rows["y"].values
        self.sc = StandardScaler().fit(X)
        self.ridge = RidgeCV(alphas=np.logspace(-1, 3, 9)).fit(self.sc.transform(X), y)
        self.gbms = [
            lgb.LGBMRegressor(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=30,
                              subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                              reg_lambda=5.0, random_state=s, verbose=-1).fit(X, y)
            for s in range(self.seeds)
        ]
        return self

    def predict_parts(self, rows: pd.DataFrame) -> dict[str, np.ndarray]:
        X, _ = _fill(rows[FEATURES], self.med)
        return {
            "lgbm": np.mean([m.predict(X) for m in self.gbms], axis=0),
            "ridge": self.ridge.predict(self.sc.transform(X)),
        }

    def predict(self, rows: pd.DataFrame) -> np.ndarray:
        p = self.predict_parts(rows)
        return 0.6 * p["lgbm"] + 0.4 * p["ridge"]

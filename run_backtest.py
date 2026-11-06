"""Leak-free walk-forward backtest. Scores RMSE/R2 vs Day-1 and weekly persistence.

Usage: python run_backtest.py --start_date 01-10-2026 --days 30 --country DE_LU
Each target day D is predicted by a model trained only on days < D (retrained every
--retrain days), using the same features as production (forecast_core.build_rows).
"""
import argparse

import numpy as np
import pandas as pd

import data_cache
from forecast_core import Ensemble, build_rows


def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def r2(y, p):
    y, p = np.asarray(y), np.asarray(p)
    return float(1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def evaluate_backtest(start_date_str: str, num_days: int, country: str, retrain: int = 7):
    start = pd.to_datetime(start_date_str, format="%d-%m-%Y")
    df = data_cache.load_area(country)
    first = df.index.min().tz_convert("Europe/Berlin").normalize().tz_localize(None) + pd.Timedelta(days=8)
    all_days = list(pd.date_range(first, start + pd.Timedelta(days=num_days - 1)))
    rows = build_rows(df, all_days)

    test_days = [start + pd.Timedelta(days=i) for i in range(num_days)]
    res = {k: [] for k in ["y", "model", "lgbm", "ridge", "p1", "p7"]}
    per_day = []
    model = None
    for i, d in enumerate(test_days):
        if model is None or i % retrain == 0:
            # target of day d-1 is only published at 12:00 on d-1, so train on days <= d-2 to be strict
            model = Ensemble().fit(rows[rows["date"] <= d - pd.Timedelta(days=2)])
        te = rows[(rows["date"] == d)].dropna(subset=["y"])
        if te.empty:
            continue
        parts = model.predict_parts(te)
        pred = 0.6 * parts["lgbm"] + 0.4 * parts["ridge"]
        res["y"] += list(te["y"]); res["model"] += list(pred)
        res["lgbm"] += list(parts["lgbm"]); res["ridge"] += list(parts["ridge"])
        res["p1"] += list(te["p_d1"].fillna(te["d1_mean"])); res["p7"] += list(te["p_d7"].fillna(te["d1_mean"]))
        per_day.append((d.date(), rmse(te["y"], pred), rmse(te["y"], te["p_d1"].fillna(te["d1_mean"]))))

    print(f"\nBacktest {country}: {len(per_day)} days from {start.date()}")
    for d, m, b in per_day:
        print(f"  {d}  model RMSE {m:7.2f}   persistence {b:7.2f}")
    print("\n  name          RMSE      R2")
    for k, label in [("model", "ensemble"), ("lgbm", "lightgbm"), ("ridge", "ridge"),
                     ("p1", "persist D-1"), ("p7", "persist D-7")]:
        print(f"  {label:<12} {rmse(res['y'], res[k]):7.2f} {r2(res['y'], res[k]):8.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start_date", default="01-10-2026", help="DD-MM-YYYY")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--country", default="DE_LU")
    ap.add_argument("--retrain", type=int, default=7)
    a = ap.parse_args()
    evaluate_backtest(a.start_date, a.days, a.country, a.retrain)

import os
import json
from datetime import datetime
import requests
import numpy as np
import pandas as pd
from supabase import create_client

# -----------------------------
# Config
# -----------------------------
FRED_API_KEY = os.getenv("FRED_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not (FRED_API_KEY and SUPABASE_URL and SUPABASE_KEY):
    raise ValueError("Missing env vars: FRED_API_KEY, SUPABASE_URL, SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

FRED_BASE = "https://api.stlouisfed.org/fred"

SERIES = {
    # inflación
    "CPIAUCSL": {"name": "CPI (level)", "freq": "m", "direction": -1},   # inflación ↑ es peor para equity
    # empleo
    "UNRATE": {"name": "Unemployment rate", "freq": "m", "direction": -1},  # desempleo ↑ es peor
    # política monetaria / tasas
    "FEDFUNDS": {"name": "Fed Funds", "freq": "m", "direction": -1},     # tasas ↑ es peor
    # curva
    "T10Y2Y": {"name": "10Y-2Y spread", "freq": "d", "direction": +1},   # spread ↑ suele ser mejor (menos inversión)
    # stress crédito
    "BAMLH0A0HYM2": {"name": "HY OAS", "freq": "d", "direction": -1},    # spreads ↑ es peor
    # benchmark (solo para referencia / validación futura)
    "SP500": {"name": "S&P 500", "freq": "d", "direction": +1},
}

TARGET_YEAR = 2026


# -----------------------------
# Helpers
# -----------------------------
def fred_observations(series_id: str) -> pd.DataFrame:
    url = f"{FRED_BASE}/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    obs = data.get("observations", [])
    df = pd.DataFrame(obs)
    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    return df[["date", "value"]]


def to_monthly(df: pd.DataFrame, how: str = "last") -> pd.DataFrame:
    """Resample a DF(date,value) to monthly index."""
    if df.empty:
        return df
    s = df.set_index("date")["value"]
    if how == "mean":
        m = s.resample("MS").mean()
    else:
        m = s.resample("MS").last()
    out = m.to_frame("value").reset_index()
    out.rename(columns={"date": "month"}, inplace=True)
    out["month"] = pd.to_datetime(out["month"])
    return out


def yoy_from_level(monthly_df: pd.DataFrame) -> pd.DataFrame:
    """Compute YoY % change from monthly level series."""
    x = monthly_df.copy()
    x = x.sort_values("month")
    x["yoy"] = x["value"].pct_change(12) * 100.0
    return x.dropna(subset=["yoy"])[["month", "yoy"]]


def zscore(series: pd.Series, window: int = 120) -> float:
    """z-score of last value vs trailing window (default 10y monthly = 120)."""
    s = series.dropna()
    if len(s) < max(24, window // 4):
        return float("nan")
    tail = s.iloc[-window:] if len(s) >= window else s
    mu = tail.mean()
    sd = tail.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return float("nan")
    return float((s.iloc[-1] - mu) / sd)


def clamp(x: float, lo: float, hi: float) -> float:
    if np.isnan(x):
        return 0.0
    return float(max(lo, min(hi, x)))


def regime_from_score(score: float) -> str:
    if score >= 0.5:
        return "bull"
    if score <= -0.5:
        return "bear"
    return "neutral"


def exp_decay_curve(score_now: float, months: int = 12, k: float = 0.22) -> list[float]:
    """Mean-reverting curve toward 0."""
    vals = []
    for m in range(months):
        val = (score_now) * float(np.exp(-k * m))
        vals.append(float(val))
    return vals


# -----------------------------
# Build features
# -----------------------------
def compute_macro_score_and_drivers() -> tuple[float, list[dict], dict]:
    """
    Returns:
      score_now in [-2,+2],
      drivers list with z and contribution,
      extras dict (for run log)
    """
    # pull data
    raw = {}
    for sid in SERIES.keys():
        df = fred_observations(sid)
        raw[sid] = df

    # monthly transforms
    monthly = {}
    # CPI -> YoY
    cpi_m = to_monthly(raw["CPIAUCSL"], how="last")
    cpi_yoy = yoy_from_level(cpi_m)
    monthly["CPI_YOY"] = cpi_yoy.set_index("month")["yoy"]

    # UNRATE, FEDFUNDS monthly as-is
    for sid in ["UNRATE", "FEDFUNDS"]:
        m = to_monthly(raw[sid], how="last")
        monthly[sid] = m.set_index("month")["value"]

    # daily -> monthly last for T10Y2Y, HY OAS, SP500
    for sid in ["T10Y2Y", "BAMLH0A0HYM2", "SP500"]:
        m = to_monthly(raw[sid], how="last")
        monthly[sid] = m.set_index("month")["value"]

    # compute z-scores (last vs trailing)
    driver_specs = [
        {"key": "CPI_YOY", "name": "Inflation (CPI YoY)", "direction": -1, "weight": 0.30},
        {"key": "UNRATE", "name": "Unemployment rate", "direction": -1, "weight": 0.25},
        {"key": "FEDFUNDS", "name": "Fed Funds", "direction": -1, "weight": 0.20},
        {"key": "T10Y2Y", "name": "Yield curve (10Y-2Y)", "direction": +1, "weight": 0.15},
        {"key": "BAMLH0A0HYM2", "name": "Credit stress (HY OAS)", "direction": -1, "weight": 0.10},
    ]

    drivers = []
    contribs = []
    for d in driver_specs:
        key = d["key"]
        s = monthly.get(key)
        z = zscore(s, window=120)
        z_adj = d["direction"] * z
        z_adj = clamp(z_adj, -3, 3)  # cap extremes
        contrib = d["weight"] * z_adj
        drivers.append({
            "key": key,
            "name": d["name"],
            "z_raw": None if np.isnan(z) else float(z),
            "z_adj": float(z_adj),
            "weight": d["weight"],
            "contribution": float(contrib),
            "latest_value": None if s is None or s.dropna().empty else float(s.dropna().iloc[-1]),
            "latest_month": None if s is None or s.dropna().empty else str(s.dropna().index[-1].date()),
        })
        contribs.append(contrib)

    score_now = float(np.nansum(contribs))
    score_now = clamp(score_now, -2, 2)

    # weekly-ish change proxy: compare last month vs previous month (simple, stable)
    delta_proxy = {}
    for d in drivers:
        key = d["key"]
        s = monthly.get(key)
        if s is None or s.dropna().shape[0] < 2:
            delta_proxy[key] = 0.0
        else:
            a = s.dropna().iloc[-1]
            b = s.dropna().iloc[-2]
            delta_proxy[key] = float(a - b)

    extras = {
        "sp500_latest": None if monthly["SP500"].dropna().empty else float(monthly["SP500"].dropna().iloc[-1]),
        "sp500_month": None if monthly["SP500"].dropna().empty else str(monthly["SP500"].dropna().index[-1].date()),
        "delta_proxy": delta_proxy,
    }

    return score_now, drivers, extras


def main():
    started = datetime.utcnow()

    try:
        score_now, drivers, extras = compute_macro_score_and_drivers()

        # Build curve for 2026 (12 months)
        curve = exp_decay_curve(score_now, months=12, k=0.22)

        # Write monthly table
        rows = []
        for i, score in enumerate(curve, start=1):
            rows.append({
                "anio": TARGET_YEAR,
                "mes": i,
                "score": float(score),
                "regime": regime_from_score(score),
                "drivers": drivers,  # same driver set for now; later we can compute month-specific drivers
                "updated_at": datetime.utcnow().isoformat()
            })

        # Upsert each row (anio, mes)
        for row in rows:
            supabase.table("macro_regime_monthly_us").upsert(row, on_conflict="anio,mes").execute()

        # weekly changes summary: top +/- by contribution (z_adj * weight)
        sorted_drivers = sorted(drivers, key=lambda x: x["contribution"])
        worst = sorted_drivers[0]
        best = sorted_drivers[-1]

        summary = {
            "score_now": score_now,
            "best_driver": {"key": best["key"], "name": best["name"], "contribution": best["contribution"]},
            "worst_driver": {"key": worst["key"], "name": worst["name"], "contribution": worst["contribution"]},
            "sp500_latest": extras.get("sp500_latest"),
            "sp500_month": extras.get("sp500_month"),
            "generated_at_utc": started.isoformat() + "Z",
        }

        supabase.table("macro_regime_run_log").insert({
            "status": "success",
            "summary": summary,
            "error": None,
        }).execute()

        print(json.dumps({"ok": True, "score_now": score_now, "generated_at": summary["generated_at_utc"]}))

    except Exception as e:
        supabase.table("macro_regime_run_log").insert({
            "status": "error",
            "summary": {},
            "error": str(e),
        }).execute()
        raise


if __name__ == "__main__":
    main()

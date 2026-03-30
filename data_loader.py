import os
import pandas as pd
import streamlit as st
from supabase import create_client


ECONOMIC_EVENTS_FILE = "Eventos_economicos.csv"
ECONOMIC_DATES_FILE = "Fechas_eventos_economicos.csv"
EARNINGS_FILE = "Earnings.xlsx"


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


@st.cache_data(ttl=300)
def load_economic_events():
    try:
        df = pd.read_csv(ECONOMIC_EVENTS_FILE)
    except Exception:
        return pd.DataFrame(columns=["event_name", "category", "description", "ticker", "country"])

    df = _standardize_columns(df)

    rename_map = {
        "evento_nombre": "event_name",
        "eventonombre": "event_name",
        "evento": "event_name",
        "nombre": "event_name",
        "categoria": "category",
        "descripcion": "description",
        "descripción": "description",
        "ticker": "ticker",
        "pais": "country",
        "país": "country",
        "tipo": "type",
    }
    df = df.rename(columns=rename_map)

    for col in ["event_name", "category", "description", "ticker", "country", "type"]:
        if col not in df.columns:
            df[col] = None

    df["event_name"] = df["event_name"].astype(str).str.strip()
    df["category"] = df["category"].fillna("Economic Event")
    df["type"] = df["type"].fillna("economic")
    df["source_group"] = "economic"

    df = df.dropna(subset=["event_name"])
    df = df[df["event_name"].str.strip() != ""].copy()

    return df[["event_name", "category", "description", "ticker", "country", "type", "source_group"]]


@st.cache_data(ttl=300)
def load_economic_event_dates():
    try:
        df = pd.read_csv(ECONOMIC_DATES_FILE)
    except Exception:
        return pd.DataFrame(columns=["event_name", "date", "source", "updated_at"])

    df = _standardize_columns(df)

    rename_map = {
        "evento_nombre": "event_name",
        "eventonombre": "event_name",
        "evento": "event_name",
        "fecha": "date",
        "fuente": "source",
        "updatedat": "updated_at",
    }
    df = df.rename(columns=rename_map)

    for col in ["event_name", "date", "source", "updated_at"]:
        if col not in df.columns:
            df[col] = None

    df["event_name"] = df["event_name"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df.dropna(subset=["event_name", "date"]).copy()
    df = df[df["event_name"].str.strip() != ""].copy()

    return df[["event_name", "date", "source", "updated_at"]]


def build_economic_events_with_dates():
    events_df = load_economic_events().copy()
    dates_df = load_economic_event_dates().copy()

    if events_df.empty:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description", "ticker",
            "country", "type", "source_group"
        ])

    if dates_df.empty:
        out = events_df.copy()
        out["date"] = pd.NaT
        return out[[
            "event_name", "category", "date", "description", "ticker",
            "country", "type", "source_group"
        ]]

    merged = events_df.merge(dates_df, on="event_name", how="left")

    merged["category"] = merged["category"].fillna("Economic Event")
    merged["type"] = merged["type"].fillna("economic")
    merged["source_group"] = "economic"

    return merged[[
        "event_name", "category", "date", "description", "ticker",
        "country", "type", "source_group"
    ]]


@st.cache_data(ttl=300)
def load_earnings_events():
    try:
        df = pd.read_excel(EARNINGS_FILE)
    except Exception:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description", "ticker",
            "country", "type", "source_group"
        ])

    df = _standardize_columns(df)

    rename_map = {
        "evento_nombre": "event_name",
        "empresa": "company",
        "categoria": "category",
        "fecha": "date",
        "descripcion": "description",
        "ticker": "ticker",
        "pais": "country",
        "tipo": "type",
    }
    df = df.rename(columns=rename_map)

    for col in ["event_name", "category", "date", "description", "ticker", "country", "type"]:
        if col not in df.columns:
            df[col] = None

    df["event_name"] = df["event_name"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["type"] = df["type"].fillna("earning")
    df["source_group"] = "earnings"

    df = df.dropna(subset=["event_name", "date"]).copy()
    df = df[df["event_name"].str.strip() != ""].copy()

    return df[[
        "event_name", "category", "date", "description", "ticker",
        "country", "type", "source_group"
    ]]


@st.cache_data(ttl=300)
def load_external_news():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description", "ticker",
            "country", "type", "source_group", "impact_score", "sectors"
        ])

    try:
        supabase = create_client(url, key)
        res = supabase.table("noticias_externas").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(res.data or [])
    except Exception:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description", "ticker",
            "country", "type", "source_group", "impact_score", "sectors"
        ])

    if df.empty:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description", "ticker",
            "country", "type", "source_group", "impact_score", "sectors"
        ])

    df = _standardize_columns(df)
    df = df.rename(columns={
        "titulo": "event_name",
        "fecha": "date",
        "descripcion": "description",
        "impacto": "impact_score",
        "sectores": "sectors"
    })

    for col in ["event_name", "date", "description", "impact_score", "sectors"]:
        if col not in df.columns:
            df[col] = None

    df["event_name"] = df["event_name"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["category"] = "External News"
    df["type"] = "external_news"
    df["source_group"] = "external_news"
    df["ticker"] = None
    df["country"] = None

    df = df.dropna(subset=["event_name", "date"]).copy()
    df = df[df["event_name"].str.strip() != ""].copy()

    return df[[
        "event_name", "category", "date", "description", "ticker",
        "country", "type", "source_group", "impact_score", "sectors"
    ]]


@st.cache_data(ttl=300)
def build_master_events_df():
    econ = build_economic_events_with_dates()
    earnings = load_earnings_events()
    external = load_external_news()

    frames = [df for df in [econ, earnings, external] if not df.empty]

    if not frames:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description", "ticker",
            "country", "type", "source_group"
        ])

    master = pd.concat(frames, ignore_index=True, sort=False)
    master["date"] = pd.to_datetime(master["date"], errors="coerce")
    master = master.sort_values(["date", "event_name"], ascending=[True, True]).reset_index(drop=True)

    return master
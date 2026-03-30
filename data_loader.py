import os
import pandas as pd
import streamlit as st
from supabase import create_client, Client


ECONOMIC_EVENTS_FILE = "Eventos_economicos.csv"
ECONOMIC_DATES_FILE = "Fechas_eventos_economicos.csv"
EARNINGS_FILE = "Earnings.xlsx"


def _get_supabase_client():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _ensure_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df


def _clean_text_col(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col].isin(["", "nan", "None", "NaT"]), col] = None
    return df


@st.cache_data(ttl=300)
def get_available_sectors():
    client = _get_supabase_client()
    if client is None:
        return ["General"]

    try:
        response = client.table("impactos_sectores").select("sector").execute()
        data = response.data or []
        sectors = sorted(set(item["sector"] for item in data if item.get("sector")))
        return sectors if sectors else ["General"]
    except Exception:
        return ["General"]


@st.cache_data(ttl=300)
def load_impact_data():
    client = _get_supabase_client()
    if client is None:
        return pd.DataFrame(columns=["event_name", "sector", "impact_score"])

    try:
        response = client.table("impactos_sectores").select("*").execute()
        df = pd.DataFrame(response.data or [])
    except Exception:
        return pd.DataFrame(columns=["event_name", "sector", "impact_score"])

    if df.empty:
        return pd.DataFrame(columns=["event_name", "sector", "impact_score"])

    df = _standardize_columns(df)
    df = df.rename(columns={
        "eventotipo": "event_name",
        "evento_tipo": "event_name",
        "sector": "sector",
        "impactoscore": "impact_score",
        "impact_score": "impact_score",
    })

    df = _ensure_columns(df, ["event_name", "sector", "impact_score"])
    df = _clean_text_col(df, "event_name")
    df = _clean_text_col(df, "sector")
    df["impact_score"] = pd.to_numeric(df["impact_score"], errors="coerce").fillna(0)

    df = df.dropna(subset=["event_name", "sector"]).copy()

    return df[["event_name", "sector", "impact_score"]]


def get_row_impact(event_name, sector, impact_df=None):
    if impact_df is None:
        impact_df = load_impact_data()

    if impact_df.empty or not event_name or not sector:
        return 0

    event_name = str(event_name).strip()
    sector = str(sector).strip()

    result = impact_df[
        (impact_df["event_name"] == event_name) &
        (impact_df["sector"] == sector)
    ]

    if result.empty:
        return 0

    try:
        return int(result.iloc[0]["impact_score"])
    except Exception:
        return 0


@st.cache_data(ttl=300)
def load_economic_events():
    try:
        df = pd.read_csv(ECONOMIC_EVENTS_FILE)
    except Exception:
        return pd.DataFrame(columns=[
            "event_name", "category", "description", "ticker",
            "country", "type", "source_group"
        ])

    df = _standardize_columns(df)

    df = df.rename(columns={
        "evento_nombre": "event_name",
        "eventonombre": "event_name",
        "evento": "event_name",
        "nombre": "event_name",
        "categoria": "category",
        "descripción": "description",
        "descripcion": "description",
        "ticker": "ticker",
        "pais": "country",
        "país": "country",
        "tipo": "type",
    })

    df = _ensure_columns(df, [
        "event_name", "category", "description",
        "ticker", "country", "type"
    ])

    df = _clean_text_col(df, "event_name")
    df = _clean_text_col(df, "category")
    df = _clean_text_col(df, "description")
    df = _clean_text_col(df, "ticker")
    df = _clean_text_col(df, "country")
    df = _clean_text_col(df, "type")

    df = df.dropna(subset=["event_name"]).copy()
    df["category"] = df["category"].fillna("Evento Económico")
    df["type"] = df["type"].fillna("economic")
    df["source_group"] = "economic"

    return df[[
        "event_name", "category", "description", "ticker",
        "country", "type", "source_group"
    ]]


@st.cache_data(ttl=300)
def load_economic_event_dates():
    try:
        df = pd.read_csv(ECONOMIC_DATES_FILE)
    except Exception:
        return pd.DataFrame(columns=["event_name", "date", "source", "updated_at"])

    df = _standardize_columns(df)

    df = df.rename(columns={
        "evento_nombre": "event_name",
        "eventonombre": "event_name",
        "evento": "event_name",
        "nombre": "event_name",
        "fecha": "date",
        "fuente": "source",
        "updatedat": "updated_at",
        "updated_at": "updated_at",
    })

    df = _ensure_columns(df, ["event_name", "date", "source", "updated_at"])

    df = _clean_text_col(df, "event_name")
    df = _clean_text_col(df, "source")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df.dropna(subset=["event_name", "date"]).copy()

    return df[["event_name", "date", "source", "updated_at"]]


def build_economic_events_with_dates():
    events_df = load_economic_events()
    dates_df = load_economic_event_dates()

    if events_df.empty:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description",
            "ticker", "country", "type", "source_group"
        ])

    if dates_df.empty:
        out = events_df.copy()
        out["date"] = pd.NaT
        return out[[
            "event_name", "category", "date", "description",
            "ticker", "country", "type", "source_group"
        ]]

    merged = events_df.merge(dates_df, on="event_name", how="left")

    merged["source_group"] = "economic"
    merged["type"] = merged["type"].fillna("economic")
    merged["category"] = merged["category"].fillna("Evento Económico")

    return merged[[
        "event_name", "category", "date", "description",
        "ticker", "country", "type", "source_group"
    ]]


@st.cache_data(ttl=300)
def load_earnings_events():
    try:
        df = pd.read_excel(EARNINGS_FILE)
    except Exception:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description",
            "ticker", "country", "type", "source_group"
        ])

    df = _standardize_columns(df)

    df = df.rename(columns={
        "evento_nombre": "event_name",
        "eventonombre": "event_name",
        "empresa": "company",
        "categoria": "category",
        "fecha": "date",
        "descripción": "description",
        "descripcion": "description",
        "ticker": "ticker",
        "pais": "country",
        "país": "country",
        "tipo": "type",
    })

    df = _ensure_columns(df, [
        "event_name", "category", "date",
        "description", "ticker", "country", "type"
    ])

    df = _clean_text_col(df, "event_name")
    df = _clean_text_col(df, "category")
    df = _clean_text_col(df, "description")
    df = _clean_text_col(df, "ticker")
    df = _clean_text_col(df, "country")
    df = _clean_text_col(df, "type")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df.dropna(subset=["event_name", "date"]).copy()
    df["type"] = df["type"].fillna("earning")
    df["source_group"] = "earnings"

    return df[[
        "event_name", "category", "date", "description",
        "ticker", "country", "type", "source_group"
    ]]


@st.cache_data(ttl=300)
def load_external_news():
    client = _get_supabase_client()
    if client is None:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description",
            "ticker", "country", "type", "source_group"
        ])

    try:
        response = client.table("eventos_unicos").select("*").eq("categoria", "Noticia Externa").execute()
        df = pd.DataFrame(response.data or [])
    except Exception:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description",
            "ticker", "country", "type", "source_group"
        ])

    if df.empty:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description",
            "ticker", "country", "type", "source_group"
        ])

    df = _standardize_columns(df)

    df = df.rename(columns={
        "eventonombre": "event_name",
        "evento_nombre": "event_name",
        "fecha": "date",
        "descripción": "description",
        "descripcion": "description",
        "ticker": "ticker",
        "pais": "country",
        "país": "country",
        "tipo": "type",
        "categoria": "category",
    })

    df = _ensure_columns(df, [
        "event_name", "category", "date", "description",
        "ticker", "country", "type"
    ])

    df = _clean_text_col(df, "event_name")
    df = _clean_text_col(df, "category")
    df = _clean_text_col(df, "description")
    df = _clean_text_col(df, "ticker")
    df = _clean_text_col(df, "country")
    df = _clean_text_col(df, "type")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df.dropna(subset=["event_name"]).copy()
    df["category"] = df["category"].fillna("Noticia Externa")
    df["type"] = df["type"].fillna("external_news")
    df["source_group"] = "external_news"

    return df[[
        "event_name", "category", "date", "description",
        "ticker", "country", "type", "source_group"
    ]]


@st.cache_data(ttl=300)
def build_master_events_df():
    economic_df = build_economic_events_with_dates()
    earnings_df = load_earnings_events()
    news_df = load_external_news()

    frames = [df for df in [economic_df, earnings_df, news_df] if not df.empty]

    if not frames:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description",
            "ticker", "country", "type", "source_group"
        ])

    master = pd.concat(frames, ignore_index=True, sort=False)
    master["date"] = pd.to_datetime(master["date"], errors="coerce")
    master = master.sort_values(["date", "event_name"], ascending=[True, True]).reset_index(drop=True)

    return master
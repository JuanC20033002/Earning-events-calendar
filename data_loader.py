import os
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client


ECONOMIC_EVENTS_FILE = "Eventos_economicos.csv"
ECONOMIC_DATES_FILE = "Fechas_eventos_economicos.csv"
EARNINGS_EVENTS_FILE = "Earnings_Events.csv"

BASE_EVENT_COLUMNS = [
    "event_name",
    "category",
    "date",
    "description",
    "ticker",
    "source_type",
    "source",
    "sectors",
    "impact",
]

NON_SECTOR_COLUMNS = {
    "Fecha",
    "TipoEvento",
    "Symbol",
    "event_name",
    "category",
    "date",
    "description",
    "ticker",
    "source_type",
    "source",
    "sectors",
    "impact",
}


def get_supabase_client() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY.")

    return create_client(url, key)


def _safe_read_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.read_csv(path, sep=",", engine="python")


def _clean_text(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def _parse_date_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.normalize()


@st.cache_data(ttl=300)
def load_economic_events() -> pd.DataFrame:
    df = _safe_read_csv(ECONOMIC_EVENTS_FILE).copy()

    df.columns = [str(col).strip() for col in df.columns]

    if "TipoEvento" not in df.columns:
        raise ValueError("Eventos_economicos.csv must include 'TipoEvento' column.")

    sector_columns = [col for col in df.columns if col not in {"Fecha", "TipoEvento"}]

    df = df.rename(columns={"TipoEvento": "event_name"})
    df["category"] = "Economic Event"
    df["ticker"] = None
    df["description"] = None
    df["source_type"] = "economic"
    df["source"] = "csv"
    df["date"] = pd.NaT
    df["sectors"] = None

    ordered_cols = BASE_EVENT_COLUMNS + sector_columns
    return df[ordered_cols].copy()


@st.cache_data(ttl=300)
def load_economic_event_dates() -> pd.DataFrame:
    df = _safe_read_csv(ECONOMIC_DATES_FILE).copy()

    df.columns = [str(col).strip() for col in df.columns]

    rename_map = {
        "evento_nombre": "event_name",
        "eventonombre": "event_name",
        "fecha": "date",
        "fuente": "source",
        "updated_at": "updated_at",
        "updatedat": "updated_at",
    }
    df = df.rename(columns=rename_map)

    expected = {"event_name", "date"}
    if not expected.issubset(df.columns):
        raise ValueError("Fechas_eventos_economicos.csv must include event_name/evento_nombre and date/fecha.")

    df["event_name"] = df["event_name"].apply(_clean_text)
    df["date"] = _parse_date_series(df["date"])

    if "source" not in df.columns:
        df["source"] = "manual_csv"

    if "updated_at" in df.columns:
        df["updated_at"] = pd.to_datetime(df["updated_at"], errors="coerce")

    df = df.dropna(subset=["event_name", "date"]).copy()
    df = df.sort_values(["event_name", "date"]).drop_duplicates(subset=["event_name"], keep="last")

    return df.reset_index(drop=True)


@st.cache_data(ttl=300)
def load_earnings_events() -> pd.DataFrame:
    df = _safe_read_csv(EARNINGS_EVENTS_FILE).copy()

    df.columns = [str(col).strip() for col in df.columns]

    required_cols = {"Fecha", "Symbol", "TipoEvento"}
    if not required_cols.issubset(df.columns):
        raise ValueError("Earnings_Events.csv must include 'Fecha', 'Symbol', and 'TipoEvento' columns.")

    sector_columns = [col for col in df.columns if col not in {"Fecha", "Symbol", "TipoEvento"}]

    df = df.rename(columns={
        "Fecha": "date",
        "Symbol": "ticker",
        "TipoEvento": "category",
    })

    df["date"] = _parse_date_series(df["date"])
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["event_name"] = df["ticker"] + " Earnings"
    df["description"] = None
    df["source_type"] = "earnings"
    df["source"] = "csv"
    df["sectors"] = None
    df["impact"] = None

    ordered_cols = BASE_EVENT_COLUMNS + sector_columns
    return df[ordered_cols].copy()


@st.cache_data(ttl=180)
def load_external_news() -> pd.DataFrame:
    supabase = get_supabase_client()
    response = supabase.table("noticias_externas").select("*").order("fecha").execute()

    df = pd.DataFrame(response.data or [])

    if df.empty:
        return pd.DataFrame(columns=BASE_EVENT_COLUMNS)

    df = df.rename(columns={
        "titulo": "event_name",
        "fecha": "date",
        "descripcion": "description",
        "sectores": "sectors",
        "impacto": "impact",
    })

    df["date"] = _parse_date_series(df["date"])
    df["category"] = "External News"
    df["ticker"] = None
    df["source_type"] = "external_news"
    df["source"] = "supabase"

    for col in BASE_EVENT_COLUMNS:
        if col not in df.columns:
            df[col] = None

    return df[BASE_EVENT_COLUMNS].copy()


def get_available_sectors() -> list:
    econ_df = load_economic_events()
    earnings_df = load_earnings_events()

    econ_sectors = [col for col in econ_df.columns if col not in BASE_EVENT_COLUMNS]
    earnings_sectors = [col for col in earnings_df.columns if col not in BASE_EVENT_COLUMNS]

    sectors = sorted(set(econ_sectors + earnings_sectors))
    return sectors


def get_row_impact(row: pd.Series, selected_sector: str) -> int:
    if row["source_type"] == "external_news":
        sectors = row.get("sectors") or []
        impact = row.get("impact")

        if selected_sector == "General":
            return int(impact) if pd.notna(impact) else 0

        if isinstance(sectors, list) and selected_sector in sectors:
            return int(impact) if pd.notna(impact) else 0

        return 0

    if selected_sector == "General":
        return int(row.get("General", 0) or 0)

    return int(row.get(selected_sector, 0) or 0)


@st.cache_data(ttl=300)
def build_master_events_df() -> pd.DataFrame:
    economic_df = load_economic_events()
    economic_dates_df = load_economic_event_dates()
    earnings_df = load_earnings_events()
    external_news_df = load_external_news()

    economic_df = economic_df.merge(
        economic_dates_df[["event_name", "date"]],
        on="event_name",
        how="left",
        suffixes=("", "_manual")
    )
    economic_df["date"] = economic_df["date_manual"]
    economic_df = economic_df.drop(columns=["date_manual"])

    all_columns = sorted(set(economic_df.columns) | set(earnings_df.columns) | set(external_news_df.columns))

    economic_df = economic_df.reindex(columns=all_columns)
    earnings_df = earnings_df.reindex(columns=all_columns)
    external_news_df = external_news_df.reindex(columns=all_columns)

    master_df = pd.concat(
        [economic_df, earnings_df, external_news_df],
        ignore_index=True
    )

    master_df["event_name"] = master_df["event_name"].apply(_clean_text)
    master_df["description"] = master_df["description"].apply(_clean_text)
    master_df["date"] = _parse_date_series(master_df["date"])

    return master_df.sort_values(["date", "category", "event_name"], na_position="last").reset_index(drop=True)
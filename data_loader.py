import os
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

POSSIBLE_DATE_COLS = ["Fecha", "fecha", "Date", "date"]
POSSIBLE_EVENT_COLS = [
    "TipoEvento",
    "Tipo_Evento",
    "tipoevento",
    "tipo_evento",
    "Evento",
    "event",
    "Event",
    "event_name",
]
POSSIBLE_SYMBOL_COLS = ["Symbol", "symbol", "Ticker", "ticker"]
POSSIBLE_SOURCE_COLS = ["fuente", "source", "Fuente"]
POSSIBLE_UPDATED_AT_COLS = ["updated_at", "updatedat", "UpdatedAt"]


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


def _find_first_matching_column(columns, candidates):
    return next((col for col in candidates if col in columns), None)


def _normalize_category(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    mapping = {
        "Magnificent 7": "Magnificent 7",
        "Dow Jones 30": "Dow Jones 30",
        "Top 3 Sector": "Top 3 Sector",
        "3 big companies for each sector": "Top 3 Sector",
        "Dow Jones 30 that are not mentioned": "Dow Jones 30",
        "Noticia Externa": "External News",
        "External News": "External News",
        "Evento Económico": "Economic Event",
        "Economic Event": "Economic Event",
    }

    return mapping.get(text, text)


@st.cache_data(ttl=300)
def load_economic_events() -> pd.DataFrame:
    df = _safe_read_csv(ECONOMIC_EVENTS_FILE).copy()
    df.columns = [str(col).strip() for col in df.columns]

    event_col = _find_first_matching_column(df.columns, POSSIBLE_EVENT_COLS)
    date_col = _find_first_matching_column(df.columns, POSSIBLE_DATE_COLS)

    if event_col is None:
        raise ValueError(
            f"Eventos_economicos.csv is missing the event column. Detected columns: {list(df.columns)}"
        )

    sector_columns = [col for col in df.columns if col not in {event_col, date_col}]

    df = df.rename(columns={event_col: "event_name"})

    if date_col is not None:
        df = df.rename(columns={date_col: "date"})
        df["date"] = _parse_date_series(df["date"])
    else:
        df["date"] = pd.NaT

    df["event_name"] = df["event_name"].apply(_clean_text)
    df["category"] = "Economic Event"
    df["ticker"] = None
    df["description"] = None
    df["source_type"] = "economic"
    df["source"] = "csv"
    df["sectors"] = None
    df["impact"] = None

    ordered_cols = BASE_EVENT_COLUMNS + sector_columns
    for col in ordered_cols:
        if col not in df.columns:
            df[col] = None

    return df[ordered_cols].copy()


@st.cache_data(ttl=300)
def load_economic_event_dates() -> pd.DataFrame:
    df = _safe_read_csv(ECONOMIC_DATES_FILE).copy()
    df.columns = [str(col).strip() for col in df.columns]

    rename_map = {
        "evento_nombre": "event_name",
        "eventonombre": "event_name",
        "Evento": "event_name",
        "fecha": "date",
        "Fecha": "date",
        "fuente": "source",
        "Fuente": "source",
        "updated_at": "updated_at",
        "updatedat": "updated_at",
    }
    df = df.rename(columns=rename_map)

    if "event_name" not in df.columns or "date" not in df.columns:
        raise ValueError(
            f"Fechas_eventos_economicos.csv must include event_name and date. Detected columns: {list(df.columns)}"
        )

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

    date_col = _find_first_matching_column(df.columns, POSSIBLE_DATE_COLS)
    symbol_col = _find_first_matching_column(df.columns, POSSIBLE_SYMBOL_COLS)
    category_col = _find_first_matching_column(df.columns, POSSIBLE_EVENT_COLS)

    if date_col is None or symbol_col is None or category_col is None:
        raise ValueError(
            f"Earnings_Events.csv is missing required columns. Detected columns: {list(df.columns)}"
        )

    sector_columns = [col for col in df.columns if col not in {date_col, symbol_col, category_col}]

    df = df.rename(columns={
        date_col: "date",
        symbol_col: "ticker",
        category_col: "category",
    })

    df["date"] = _parse_date_series(df["date"])
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["category"] = df["category"].apply(_normalize_category)
    df["event_name"] = df["ticker"] + " Earnings"
    df["description"] = None
    df["source_type"] = "earnings"
    df["source"] = "csv"
    df["sectors"] = None
    df["impact"] = None

    ordered_cols = BASE_EVENT_COLUMNS + sector_columns
    for col in ordered_cols:
        if col not in df.columns:
            df[col] = None

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

    df["event_name"] = df["event_name"].apply(_clean_text)
    df["description"] = df["description"].apply(_clean_text)
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
    economic_df = load_economic_events()
    earnings_df = load_earnings_events()

    economic_sectors = [col for col in economic_df.columns if col not in BASE_EVENT_COLUMNS]
    earnings_sectors = [col for col in earnings_df.columns if col not in BASE_EVENT_COLUMNS]

    sectors = sorted(set(economic_sectors + earnings_sectors))
    return sectors


def get_row_impact(row: pd.Series, selected_sector: str) -> int:
    if row["source_type"] == "external_news":
        sectors = row.get("sectors")
        impact = row.get("impact")

        if pd.isna(impact):
            return 0

        try:
            impact = int(impact)
        except Exception:
            return 0

        if selected_sector == "General":
            return impact

        if isinstance(sectors, list) and selected_sector in sectors:
            return impact

        if isinstance(sectors, str):
            parsed = [item.strip() for item in sectors.split(",") if item.strip()]
            if selected_sector in parsed:
                return impact

        return 0

    if selected_sector == "General":
        value = row.get("General", 0)
    else:
        value = row.get(selected_sector, 0)

    try:
        if pd.isna(value):
            return 0
        return int(float(value))
    except Exception:
        return 0


@st.cache_data(ttl=300)
def build_master_events_df() -> pd.DataFrame:
    economic_df = load_economic_events()
    economic_dates_df = load_economic_event_dates()
    earnings_df = load_earnings_events()
    external_news_df = load_external_news()

    economic_df = economic_df.drop(columns=["date"], errors="ignore")
    economic_df = economic_df.merge(
        economic_dates_df[["event_name", "date"]],
        on="event_name",
        how="left"
    )

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
    master_df["category"] = master_df["category"].apply(_normalize_category)
    master_df["date"] = _parse_date_series(master_df["date"])

    return master_df.sort_values(
        ["date", "category", "event_name"],
        na_position="last"
    ).reset_index(drop=True)
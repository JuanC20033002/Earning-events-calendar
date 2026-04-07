import os
import pandas as pd
import streamlit as st
from supabase import create_client


ECONOMIC_EVENTS_FILE = "Eventos_economicos.csv"
EARNINGS_FILE = "Earnings_Events.csv"
ECONOMIC_DATES_TABLE = "economic_event_dates"


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
        df.loc[df[col].isin(["", "nan", "None", "NaT", "-"]), col] = None
    return df


def _get_sector_columns(df: pd.DataFrame):
    excluded = {
        "fecha", "date", "tipo_evento", "tipoevento", "event_name", "evento_nombre",
        "eventonombre", "symbol", "ticker", "category", "description", "country",
        "type", "source_group", "source", "updated_at", "updatedat", "id"
    }
    return [c for c in df.columns if c not in excluded]


def normalize_text(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def normalize_key(value):
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    return text if text else None


def normalize_category(value):
    if pd.isna(value):
        return None

    text = str(value).strip().lower()

    mapping = {
        "economic event": "Economic Event",
        "evento económico": "Economic Event",
        "evento economico": "Economic Event",
        "evento econmico": "Economic Event",
        "magnificent 7": "Magnificent 7",
        "dow jones 30": "Dow Jones 30",
        "dow jones": "Dow Jones 30",
        "top 3 sector": "Top 3 Sector",
        "top 3 sectors": "Top 3 Sector",
        "external news": "External News",
        "noticia externa": "External News",
    }

    return mapping.get(text, str(value).strip())


@st.cache_data(ttl=300)
def get_available_sectors():
    impact_df = load_impact_data()
    if impact_df.empty:
        return ["General"]

    sectors = sorted([s for s in impact_df["sector"].dropna().unique().tolist() if s])
    return sectors if sectors else ["General"]


@st.cache_data(ttl=300)
def load_impact_data():
    frames = []

    # Economic events matrix from CSV
    try:
        econ_df = pd.read_csv(ECONOMIC_EVENTS_FILE)
        econ_df = _standardize_columns(econ_df)

        if not econ_df.empty and "tipo_evento" in econ_df.columns:
            sector_cols = _get_sector_columns(econ_df)
            econ_long = econ_df.melt(
                id_vars=["tipo_evento"],
                value_vars=sector_cols,
                var_name="sector",
                value_name="impact_score"
            )
            econ_long = econ_long.rename(columns={"tipo_evento": "event_name"})
            econ_long = _clean_text_col(econ_long, "event_name")
            econ_long["sector"] = econ_long["sector"].astype(str).str.strip()
            econ_long["impact_score"] = pd.to_numeric(econ_long["impact_score"], errors="coerce")
            econ_long = econ_long.dropna(subset=["event_name", "sector", "impact_score"])
            econ_long = econ_long[econ_long["impact_score"] > 0]
            frames.append(econ_long[["event_name", "sector", "impact_score"]])
    except Exception:
        pass

    # Earnings matrix from CSV
    try:
        earn_df = pd.read_csv(EARNINGS_FILE)
        earn_df = _standardize_columns(earn_df)

        if not earn_df.empty and "symbol" in earn_df.columns:
            sector_cols = _get_sector_columns(earn_df)
            earn_long = earn_df.melt(
                id_vars=["symbol"],
                value_vars=sector_cols,
                var_name="sector",
                value_name="impact_score"
            )
            earn_long = earn_long.rename(columns={"symbol": "event_name"})
            earn_long = _clean_text_col(earn_long, "event_name")
            earn_long["sector"] = earn_long["sector"].astype(str).str.strip()
            earn_long["impact_score"] = pd.to_numeric(earn_long["impact_score"], errors="coerce")
            earn_long = earn_long.dropna(subset=["event_name", "sector", "impact_score"])
            earn_long = earn_long[earn_long["impact_score"] > 0]
            frames.append(earn_long[["event_name", "sector", "impact_score"]])
    except Exception:
        pass

    # Optional Supabase overrides / additions for impacts
    client = _get_supabase_client()
    if client is not None:
        try:
            response = client.table("impactosectores").select("*").execute()
            db_df = pd.DataFrame(response.data or [])
            if not db_df.empty:
                db_df = _standardize_columns(db_df)
                db_df = db_df.rename(columns={
                    "eventotipo": "event_name",
                    "evento_tipo": "event_name",
                    "impactoscore": "impact_score"
                })
                db_df = _ensure_columns(db_df, ["event_name", "sector", "impact_score"])
                db_df = _clean_text_col(db_df, "event_name")
                db_df = _clean_text_col(db_df, "sector")
                db_df["impact_score"] = pd.to_numeric(db_df["impact_score"], errors="coerce")
                db_df = db_df.dropna(subset=["event_name", "sector", "impact_score"])
                db_df = db_df[db_df["impact_score"] > 0]
                frames.append(db_df[["event_name", "sector", "impact_score"]])
        except Exception:
            pass

    if not frames:
        return pd.DataFrame(columns=["event_name", "sector", "impact_score"])

    impact_df = pd.concat(frames, ignore_index=True).drop_duplicates()
    impact_df["event_name"] = impact_df["event_name"].apply(normalize_text)
    impact_df["sector"] = impact_df["sector"].apply(normalize_text)
    impact_df["impact_score"] = pd.to_numeric(impact_df["impact_score"], errors="coerce")
    impact_df = impact_df.dropna(subset=["event_name", "sector", "impact_score"]).copy()

    return impact_df


def get_row_impact(event_name, sector, impact_df=None):
    if impact_df is None:
        impact_df = load_impact_data()

    if impact_df.empty or not event_name or not sector:
        return 0

    event_name = normalize_text(event_name)
    sector = normalize_text(sector)

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

    if "tipo_evento" in df.columns:
        df = df.rename(columns={"tipo_evento": "event_name"})
    elif "tipoevento" in df.columns:
        df = df.rename(columns={"tipoevento": "event_name"})

    df = _ensure_columns(df, [
        "event_name", "description", "ticker", "country", "type"
    ])

    df = _clean_text_col(df, "event_name")
    df = _clean_text_col(df, "description")
    df = _clean_text_col(df, "ticker")
    df = _clean_text_col(df, "country")
    df = _clean_text_col(df, "type")

    df = df.dropna(subset=["event_name"]).copy()
    df["category"] = "Economic Event"
    df["type"] = df["type"].fillna("economic")
    df["source_group"] = "economic"

    return df[[
        "event_name", "category", "description", "ticker",
        "country", "type", "source_group"
    ]].drop_duplicates()


@st.cache_data(ttl=300)
def load_economic_event_dates():
    client = _get_supabase_client()
    if client is None:
        return pd.DataFrame(columns=["id", "event_name", "date", "source", "updated_at"])

    try:
        response = client.table(ECONOMIC_DATES_TABLE).select("*").order("date").execute()
        df = pd.DataFrame(response.data or [])
    except Exception:
        return pd.DataFrame(columns=["id", "event_name", "date", "source", "updated_at"])

    if df.empty:
        return pd.DataFrame(columns=["id", "event_name", "date", "source", "updated_at"])

    df = _standardize_columns(df)
    df = _ensure_columns(df, ["id", "event_name", "date", "source", "updated_at"])

    df = _clean_text_col(df, "event_name")
    df = _clean_text_col(df, "source")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df.dropna(subset=["event_name", "date"]).copy()

    return df[["id", "event_name", "date", "source", "updated_at"]]


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

    merged = events_df.merge(dates_df[["event_name", "date"]], on="event_name", how="left")

    merged["source_group"] = "economic"
    merged["type"] = merged["type"].fillna("economic")
    merged["category"] = merged["category"].fillna("Economic Event")

    return merged[[
        "event_name", "category", "date", "description",
        "ticker", "country", "type", "source_group"
    ]]


@st.cache_data(ttl=300)
def load_earnings_events():
    try:
        df = pd.read_csv(EARNINGS_FILE)
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
        "fecha": "date",
        "symbol": "ticker",
        "tipo_evento": "category",
        "tipoevento": "category",
    })

    df = _ensure_columns(df, ["date", "ticker", "category"])

    df["event_name"] = df["ticker"]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = _clean_text_col(df, "event_name")
    df = _clean_text_col(df, "ticker")
    df = _clean_text_col(df, "category")
    df["category"] = df["category"].apply(normalize_category)

    df["description"] = None
    df["country"] = None
    df["type"] = "earning"
    df["source_group"] = "earnings"

    df = df.dropna(subset=["event_name", "date"]).copy()

    return df[[
        "event_name", "category", "date", "description",
        "ticker", "country", "type", "source_group"
    ]].drop_duplicates()


@st.cache_data(ttl=300)
def load_external_news():
    client = _get_supabase_client()
    if client is None:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description",
            "ticker", "country", "type", "source_group",
            "sectors", "impact_score"
        ])

    try:
        response = client.table("noticias_externas").select("*").order("fecha", desc=False).execute()
        df = pd.DataFrame(response.data or [])
    except Exception:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description",
            "ticker", "country", "type", "source_group",
            "sectors", "impact_score"
        ])

    if df.empty:
        return pd.DataFrame(columns=[
            "event_name", "category", "date", "description",
            "ticker", "country", "type", "source_group",
            "sectors", "impact_score"
        ])

    df = _standardize_columns(df)

    df = df.rename(columns={
        "titulo": "event_name",
        "fecha": "date",
        "descripcion": "description",
        "sectores": "sectors",
        "impacto": "impact_score",
    })

    df = _ensure_columns(df, [
        "event_name", "date", "description", "sectors", "impact_score"
    ])

    df = _clean_text_col(df, "event_name")
    df = _clean_text_col(df, "description")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["impact_score"] = pd.to_numeric(df["impact_score"], errors="coerce")

    df = df.dropna(subset=["event_name"]).copy()

    df["category"] = "External News"
    df["ticker"] = None
    df["country"] = None
    df["type"] = "external_news"
    df["source_group"] = "external_news"

    df = df[[
        "event_name", "category", "date", "description",
        "ticker", "country", "type", "source_group",
        "sectors", "impact_score"
    ]].copy()

    df = df.drop_duplicates(subset=[
        "event_name", "category", "date", "description",
        "ticker", "country", "type", "source_group", "impact_score"
    ])

    return df

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
    master["event_name"] = master["event_name"].apply(normalize_text)
    master["category"] = master["category"].apply(normalize_category)
    master["date"] = pd.to_datetime(master["date"], errors="coerce")
    master = master.sort_values(["date", "event_name"], ascending=[True, True]).reset_index(drop=True)

    return master
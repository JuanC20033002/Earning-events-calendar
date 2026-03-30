
import calendar
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

from data_loader import build_master_events_df, get_available_sectors, load_impact_data


st.set_page_config(page_title="Calendario", page_icon="🗓️", layout="wide")

st.title("Calendario")
st.caption("Weekly event list by month, sector, category, and impact.")


def normalize_text(value):
    if pd.isna(value):
        return None
    return str(value).strip()


def normalize_key(value):
    if pd.isna(value):
        return None
    return str(value).strip().lower()


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


def get_event_impact(event_name: str, selected_sector: str, impact_df: pd.DataFrame) -> int:
    if impact_df.empty or not event_name or not selected_sector:
        return 0

    event_key = normalize_key(event_name)
    sector_key = normalize_key(selected_sector)

    matches = impact_df[
        (impact_df["event_key"] == event_key) &
        (impact_df["sector_key"] == sector_key)
    ].copy()

    if matches.empty:
        return 0

    try:
        return int(matches["impact_score"].max())
    except Exception:
        return 0


def get_weeks_of_month(year: int, month: int):
    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, calendar.monthrange(year, month)[1]).date()

    weeks = []
    current_date = first_day

    while current_date <= last_day:
        week_start = current_date - timedelta(days=current_date.weekday())
        week_end = week_start + timedelta(days=6)

        if week_start < first_day:
            week_start = first_day
        if week_end > last_day:
            week_end = last_day

        weeks.append((week_start, week_end))
        current_date = week_end + timedelta(days=1)

    return weeks


def impact_badge(impact: int):
    if impact >= 4:
        return "🔴 Very High"
    if impact == 3:
        return "🟠 High"
    if impact == 2:
        return "🟡 Medium"
    return "🟢 Low"


def category_badge(category: str):
    if category == "Magnificent 7":
        return "⭐ Magnificent 7"
    if category == "Dow Jones 30":
        return "🏛️ Dow Jones 30"
    if category == "Top 3 Sector":
        return "🏢 Top 3 Sector"
    if category == "External News":
        return "🌐 External News"
    return "📊 Economic Event"


master_df = build_master_events_df()
impact_df = load_impact_data()

if master_df.empty:
    st.warning("No events are available.")
    st.stop()

master_df = master_df.copy()
master_df["event_name"] = master_df["event_name"].apply(normalize_text)
master_df["category"] = master_df["category"].apply(normalize_category)
master_df["date"] = pd.to_datetime(master_df["date"], errors="coerce")

impact_df = impact_df.copy()
if not impact_df.empty:
    impact_df["event_name"] = impact_df["event_name"].apply(normalize_text)
    impact_df["sector"] = impact_df["sector"].apply(normalize_text)
    impact_df["event_key"] = impact_df["event_name"].apply(normalize_key)
    impact_df["sector_key"] = impact_df["sector"].apply(normalize_key)
    impact_df["impact_score"] = pd.to_numeric(impact_df["impact_score"], errors="coerce").fillna(0)

sectors = ["General"] + [s for s in get_available_sectors() if s != "General"]

with st.sidebar:
    st.header("Filters")

    selected_sector = st.selectbox(
        "Sector",
        sectors,
        index=sectors.index("General") if "General" in sectors else 0
    )

    st.markdown("---")
    st.subheader("Period")

    current_year = datetime.now().year
    current_month = datetime.now().month

    col_month, col_year = st.columns(2)
    with col_month:
        selected_month = st.selectbox(
            "Month",
            list(range(1, 13)),
            index=current_month - 1,
            format_func=lambda x: calendar.month_name[x]
        )
    with col_year:
        selected_year = st.selectbox(
            "Year",
            list(range(current_year, current_year + 3)),
            index=0
        )

    month_start = datetime(selected_year, selected_month, 1).date()
    month_end = datetime(selected_year, selected_month, calendar.monthrange(selected_year, selected_month)[1]).date()

    st.info(f"{month_start.strftime('%d/%m/%Y')} - {month_end.strftime('%d/%m/%Y')}")

    st.markdown("---")
    st.subheader("Event types")

    show_economic = st.checkbox("Economic Events", value=True)
    show_mag7 = st.checkbox("Magnificent 7", value=True)
    show_dow = st.checkbox("Dow Jones 30", value=True)
    show_top3 = st.checkbox("Top 3 Sector", value=True)
    show_external = st.checkbox("External News", value=True)

    st.markdown("---")
    min_impact = st.select_slider(
        "Minimum impact",
        options=[1, 2, 3, 4],
        value=1,
        format_func=lambda x: f"{x}/4"
    )

    st.markdown("---")
    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

allowed_categories = []
if show_economic:
    allowed_categories.append("Economic Event")
if show_mag7:
    allowed_categories.append("Magnificent 7")
if show_dow:
    allowed_categories.append("Dow Jones 30")
if show_top3:
    allowed_categories.append("Top 3 Sector")
if show_external:
    allowed_categories.append("External News")

filtered_df = master_df.copy()
filtered_df = filtered_df[filtered_df["date"].notna()].copy()
filtered_df = filtered_df[
    (filtered_df["date"].dt.date >= month_start) &
    (filtered_df["date"].dt.date <= month_end)
].copy()

if allowed_categories:
    filtered_df = filtered_df[filtered_df["category"].isin(allowed_categories)].copy()
else:
    filtered_df = pd.DataFrame(columns=filtered_df.columns)

if not filtered_df.empty:
    filtered_df["impact_score"] = filtered_df["event_name"].apply(
        lambda event_name: get_event_impact(event_name, selected_sector, impact_df)
    )
    filtered_df = filtered_df[filtered_df["impact_score"] >= min_impact].copy()
else:
    filtered_df["impact_score"] = pd.Series(dtype="int64")

filtered_df = filtered_df.sort_values("date").reset_index(drop=True)

st.markdown(f"### {calendar.month_name[selected_month]} {selected_year}")

if filtered_df.empty:
    st.info(f"No events in {calendar.month_name[selected_month]} {selected_year} match the selected filters.")
    st.stop()

weeks = get_weeks_of_month(selected_year, selected_month)

if "calendar_week_index" not in st.session_state:
    st.session_state.calendar_week_index = 0

if st.session_state.calendar_week_index >= len(weeks):
    st.session_state.calendar_week_index = 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Events", len(filtered_df))
with col2:
    st.metric("Economic", len(filtered_df[filtered_df["category"] == "Economic Event"]))
with col3:
    st.metric("Magnificent 7", len(filtered_df[filtered_df["category"] == "Magnificent 7"]))
with col4:
    st.metric("Impact 4", len(filtered_df[filtered_df["impact_score"] == 4]))

st.markdown("---")

nav1, nav2, nav3 = st.columns([1, 2, 1])
with nav1:
    if st.button("Previous Week", disabled=st.session_state.calendar_week_index == 0, use_container_width=True):
        st.session_state.calendar_week_index -= 1
        st.rerun()

with nav2:
    week_start, week_end = weeks[st.session_state.calendar_week_index]
    st.markdown(f"**Week {st.session_state.calendar_week_index + 1} of {len(weeks)}**")
    st.markdown(f"{week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')}")

with nav3:
    if st.button("Next Week", disabled=st.session_state.calendar_week_index >= len(weeks) - 1, use_container_width=True):
        st.session_state.calendar_week_index += 1
        st.rerun()

st.markdown("---")

week_start, week_end = weeks[st.session_state.calendar_week_index]

week_df = filtered_df[
    (filtered_df["date"].dt.date >= week_start) &
    (filtered_df["date"].dt.date <= week_end)
].copy()

if week_df.empty:
    st.info("No events in this week.")
    st.stop()

unique_dates = sorted(week_df["date"].dt.date.unique())

for event_date in unique_dates:
    day_df = week_df[week_df["date"].dt.date == event_date].copy()
    day_df = day_df.sort_values(["impact_score", "event_name"], ascending=[False, True])

    st.markdown(f"#### {pd.to_datetime(event_date).strftime('%A, %d %B %Y')}")

    for _, row in day_df.iterrows():
        impact = int(row["impact_score"])
        impact_label = impact_badge(impact)
        category_label = category_badge(row["category"])

        info_parts = []
        if pd.notna(row.get("ticker")) and row.get("ticker"):
            info_parts.append(f"Ticker: {row['ticker']}")
        if pd.notna(row.get("country")) and row.get("country"):
            info_parts.append(f"Country: {row['country']}")
        if pd.notna(row.get("description")) and row.get("description"):
            description = str(row["description"])
            if len(description) > 120:
                description = description[:117] + "..."
            info_parts.append(description)

        with st.container():
            c1, c2 = st.columns([1, 5])

            with c1:
                st.markdown(f"**{impact_label}**")
                st.markdown(f"{category_label}")

            with c2:
                st.markdown(f"**{row['event_name']}**")
                if info_parts:
                    st.caption(" • ".join(info_parts))
                st.caption(f"Impact in {selected_sector}: {impact}/4")

        st.markdown("---")
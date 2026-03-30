import calendar
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

from data_loader import build_master_events_df, get_available_sectors, get_row_impact


st.set_page_config(page_title="Calendar", page_icon="🗓️", layout="wide")


st.markdown(
    """
    <style>
    .badge {
        display:inline-block;
        padding:4px 10px;
        border-radius:999px;
        font-size:0.75rem;
        font-weight:700;
        margin-right:6px;
        margin-bottom:6px;
    }
    .event-card {
        border:1px solid rgba(255,255,255,0.08);
        border-radius:12px;
        padding:14px 16px;
        margin-bottom:12px;
        background:rgba(255,255,255,0.02);
    }
    .muted-text {
        font-size:0.9rem;
        opacity:0.8;
    }
    .small-muted {
        font-size:0.82rem;
        opacity:0.72;
    }
    </style>
    """,
    unsafe_allow_html=True
)


def get_weeks_of_month(year: int, month: int):
    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, calendar.monthrange(year, month)[1]).date()

    weeks = []
    current = first_day

    while current <= last_day:
        start_week = current - timedelta(days=current.weekday())
        end_week = start_week + timedelta(days=6)

        if start_week < first_day:
            start_week = first_day
        if end_week > last_day:
            end_week = last_day

        weeks.append((start_week, end_week))
        current = end_week + timedelta(days=1)

    unique_weeks = []
    seen = set()
    for week in weeks:
        if week not in seen:
            unique_weeks.append(week)
            seen.add(week)

    return unique_weeks


def impact_badge_html(score: int) -> str:
    if score >= 4:
        label, bg, fg = "Very High (4/4)", "#dc3545", "white"
    elif score == 3:
        label, bg, fg = "High (3/4)", "#fd7e14", "white"
    elif score == 2:
        label, bg, fg = "Medium (2/4)", "#ffc107", "black"
    else:
        label, bg, fg = "Low (1/4)", "#198754", "white"

    return f'<span class="badge" style="background:{bg}; color:{fg};">{label}</span>'


def category_badge_html(category: str) -> str:
    colors = {
        "Economic Event": ("#1f77b4", "white"),
        "Magnificent 7": ("#8e44ad", "white"),
        "Dow Jones 30": ("#16a085", "white"),
        "Top 3 Sector": ("#f39c12", "black"),
        "External News": ("#e74c3c", "white"),
    }
    bg, fg = colors.get(category, ("#6c757d", "white"))
    return f'<span class="badge" style="background:{bg}; color:{fg};">{category}</span>'


def render_event_card(row: pd.Series, sector: str):
    event_name = row.get("event_name", "Unnamed event")
    category = row.get("category", "Unknown")
    ticker = row.get("ticker")
    description = row.get("description")
    source = row.get("source")
    impact = int(row.get("impact_score", 0))

    meta_parts = []
    if pd.notna(ticker) and str(ticker).strip():
        meta_parts.append(f"Ticker: {ticker}")
    if pd.notna(source) and str(source).strip():
        meta_parts.append(f"Source: {source}")

    meta_text = " · ".join(meta_parts)

    st.markdown('<div class="event-card">', unsafe_allow_html=True)
    st.markdown(
        impact_badge_html(impact) + category_badge_html(category),
        unsafe_allow_html=True
    )
    st.write(f"**{event_name}**")

    if meta_text:
        st.markdown(f'<div class="muted-text">{meta_text}</div>', unsafe_allow_html=True)

    if pd.notna(description) and str(description).strip():
        st.write(str(description))

    st.markdown(
        f'<div class="small-muted">Impact for {sector}: {impact}/4</div>',
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)


st.title("Calendar")
st.caption("Weekly view of events filtered by sector, category, and minimum impact.")

master_df = build_master_events_df()

if master_df.empty:
    st.warning("No events are available.")
    st.stop()

sectors = ["General"] + get_available_sectors()

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

    col1, col2 = st.columns(2)
    with col1:
        selected_month = st.selectbox(
            "Month",
            list(range(1, 13)),
            index=current_month - 1,
            format_func=lambda x: calendar.month_name[x]
        )
    with col2:
        selected_year = st.selectbox(
            "Year",
            list(range(current_year, current_year + 3)),
            index=0
        )

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

month_start = datetime(selected_year, selected_month, 1).date()
month_end = datetime(selected_year, selected_month, calendar.monthrange(selected_year, selected_month)[1]).date()

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
    filtered_df["impact_score"] = filtered_df.apply(
        lambda row: get_row_impact(row, selected_sector),
        axis=1
    )
    filtered_df = filtered_df[filtered_df["impact_score"] >= min_impact].copy()
    filtered_df = filtered_df.sort_values(
        ["date", "impact_score", "event_name"],
        ascending=[True, False, True]
    ).reset_index(drop=True)
else:
    filtered_df["impact_score"] = pd.Series(dtype="int")

weeks = get_weeks_of_month(selected_year, selected_month)

if "calendar_week_index" not in st.session_state:
    st.session_state.calendar_week_index = 0

if st.session_state.calendar_week_index >= len(weeks):
    st.session_state.calendar_week_index = 0

if st.session_state.calendar_week_index < 0:
    st.session_state.calendar_week_index = 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total events", len(filtered_df))
with col2:
    st.metric("Economic", int((filtered_df["category"] == "Economic Event").sum()) if not filtered_df.empty else 0)
with col3:
    st.metric(
        "Earnings",
        int(filtered_df["category"].isin(["Magnificent 7", "Dow Jones 30", "Top 3 Sector"]).sum()) if not filtered_df.empty else 0
    )
with col4:
    st.metric("Impact 4", int((filtered_df["impact_score"] == 4).sum()) if not filtered_df.empty else 0)

st.markdown("---")

nav1, nav2, nav3 = st.columns([1, 2, 1])

with nav1:
    if st.button("Previous week", disabled=st.session_state.calendar_week_index == 0, use_container_width=True):
        st.session_state.calendar_week_index -= 1
        st.rerun()

with nav2:
    week_start, week_end = weeks[st.session_state.calendar_week_index]
    st.markdown(
        f"""
        <div style="text-align:center;">
            <div style="font-size:1.1rem; font-weight:700;">Week {st.session_state.calendar_week_index + 1} of {len(weeks)}</div>
            <div style="opacity:0.8;">{week_start.strftime('%d %b %Y')} - {week_end.strftime('%d %b %Y')}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with nav3:
    if st.button("Next week", disabled=st.session_state.calendar_week_index >= len(weeks) - 1, use_container_width=True):
        st.session_state.calendar_week_index += 1
        st.rerun()

st.markdown("---")

week_start, week_end = weeks[st.session_state.calendar_week_index]

week_df = filtered_df[
    (filtered_df["date"].dt.date >= week_start) &
    (filtered_df["date"].dt.date <= week_end)
].copy()

if week_df.empty:
    st.info(
        f"No events match the selected filters for the week {week_start.strftime('%d %b %Y')} - {week_end.strftime('%d %b %Y')}."
    )

    for offset in range((week_end - week_start).days + 1):
        current_day = week_start + timedelta(days=offset)
        st.markdown(f"### {pd.to_datetime(current_day).strftime('%A, %d %B %Y')}")
        st.markdown(
            """
            <div class="event-card" style="border-style:dashed; opacity:0.75;">
                No events.
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    unique_dates = sorted(week_df["date"].dt.date.unique())

    for current_day in unique_dates:
        day_df = week_df[week_df["date"].dt.date == current_day].copy()
        day_df = day_df.sort_values(["impact_score", "event_name"], ascending=[False, True])

        st.markdown(f"### {pd.to_datetime(current_day).strftime('%A, %d %B %Y')}")

        for _, row in day_df.iterrows():
            render_event_card(row, selected_sector)

        st.markdown("---")
import calendar
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

from data_loader import build_master_events_df, get_available_sectors, get_row_impact


st.set_page_config(page_title="Calendar", page_icon="🗓️", layout="wide")


st.markdown(
    """
    <style>
    .main {
        padding: 0rem 1rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.2rem;
    }
    .event-divider {
        margin-top: 0.6rem;
        margin-bottom: 0.8rem;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    .mini-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
        text-align: center;
        min-width: 76px;
    }
    .impact-4 { background: #ff4b4b; color: white; }
    .impact-3 { background: #ff8c00; color: white; }
    .impact-2 { background: #ffd700; color: #222; }
    .impact-1 { background: #4caf50; color: white; }

    .cat-mag7 { color: #c084fc; font-size: 0.78rem; }
    .cat-dow { color: #5eead4; font-size: 0.78rem; }
    .cat-top3 { color: #fbbf24; font-size: 0.78rem; }
    .cat-ext { color: #f87171; font-size: 0.78rem; }
    .cat-eco { color: #93c5fd; font-size: 0.78rem; }

    .empty-day-box {
        border: 1px dashed rgba(255,255,255,0.12);
        border-radius: 10px;
        padding: 0.9rem 1rem;
        opacity: 0.8;
        margin-bottom: 1rem;
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


def get_impact_badge(score: int):
    if score >= 4:
        return "Very High", "impact-4", "🔴"
    if score == 3:
        return "High", "impact-3", "🟠"
    if score == 2:
        return "Medium", "impact-2", "🟡"
    return "Low", "impact-1", "🟢"


def get_category_icon(category: str):
    if category == "Magnificent 7":
        return "💻", "cat-mag7"
    if category == "Dow Jones 30":
        return "🏛️", "cat-dow"
    if category == "Top 3 Sector":
        return "🏭", "cat-top3"
    if category == "External News":
        return "📰", "cat-ext"
    return "📊", "cat-eco"


def render_event_row(row: pd.Series, selected_sector: str):
    impact = int(row.get("impact_score", 0))
    impact_label, impact_class, impact_emoji = get_impact_badge(impact)
    category = row.get("category", "Unknown")
    cat_icon, cat_class = get_category_icon(category)

    event_name = row.get("event_name", "Unnamed event")
    ticker = row.get("ticker")
    description = row.get("description")
    source = row.get("source")

    info_parts = []
    if pd.notna(ticker) and str(ticker).strip():
        info_parts.append(f"Ticker: {ticker}")
    if pd.notna(source) and str(source).strip():
        info_parts.append(f"Source: {source}")

    if pd.notna(description) and str(description).strip():
        short_desc = str(description)
        if len(short_desc) > 100:
            short_desc = short_desc[:100] + "..."
        info_parts.append(short_desc)

    with st.container():
        col1, col2 = st.columns([1, 4])

        with col1:
            st.markdown(
                f"""
                <div class="mini-badge {impact_class}">
                    {impact_label}
                </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown(
                f"""
                <div class="{cat_class}">
                    {cat_icon} {category}
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(f"**{event_name}**")

            if info_parts:
                st.markdown(
                    f"<small>{' · '.join(info_parts)}</small>",
                    unsafe_allow_html=True
                )

            st.markdown(
                f"<small>Impact in {selected_sector}: {impact}/4</small>",
                unsafe_allow_html=True
            )

        st.markdown('<div class="event-divider"></div>', unsafe_allow_html=True)


st.title("Calendar")
st.caption("Weekly event list by month, sector, category, and impact.")

master_df = build_master_events_df()

if master_df.empty:
    st.warning("No events are available.")
    st.stop()

sectors = ["General"] + get_available_sectors()

with st.sidebar:
    st.markdown("## Filters")
    st.markdown("---")

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
    st.warning("Select at least one event category to display.")
    filtered_df = pd.DataFrame(columns=filtered_df.columns)

if not filtered_df.empty:
    filtered_df["impact_score"] = filtered_df.apply(
        lambda row: get_row_impact(row, selected_sector),
        axis=1
    )
    filtered_df = filtered_df[filtered_df["impact_score"] >= min_impact].copy()
    filtered_df = filtered_df.sort_values(["date", "impact_score"], ascending=[True, False]).reset_index(drop=True)
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
    st.metric("Total Events", len(filtered_df))
with col2:
    eco_count = int((filtered_df["category"] == "Economic Event").sum()) if not filtered_df.empty else 0
    st.metric("Economic", eco_count)
with col3:
    mag_count = int((filtered_df["category"] == "Magnificent 7").sum()) if not filtered_df.empty else 0
    st.metric("Magnificent 7", mag_count)
with col4:
    impact4_count = int((filtered_df["impact_score"] == 4).sum()) if not filtered_df.empty else 0
    st.metric("Impact 4", impact4_count)

st.markdown("---")

colnav1, colnav2, colnav3 = st.columns([1, 2, 1])

with colnav1:
    if st.button("Previous Week", disabled=st.session_state.calendar_week_index == 0, use_container_width=True):
        st.session_state.calendar_week_index -= 1
        st.rerun()

with colnav2:
    week_start, week_end = weeks[st.session_state.calendar_week_index]
    st.markdown(
        f"""
        <div style="text-align:center;">
            <div style="font-size:1rem; font-weight:700;">
                Week {st.session_state.calendar_week_index + 1} of {len(weeks)}
            </div>
            <div style="opacity:0.8;">
                {week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with colnav3:
    if st.button("Next Week", disabled=st.session_state.calendar_week_index >= len(weeks) - 1, use_container_width=True):
        st.session_state.calendar_week_index += 1
        st.rerun()

st.markdown("---")

week_start, week_end = weeks[st.session_state.calendar_week_index]

week_df = filtered_df[
    (filtered_df["date"].dt.date >= week_start) &
    (filtered_df["date"].dt.date <= week_end)
].copy()

all_days_in_week = [week_start + timedelta(days=i) for i in range((week_end - week_start).days + 1)]

if week_df.empty:
    st.info("No events match the selected filters for this week.")

for current_day in all_days_in_week:
    day_df = week_df[week_df["date"].dt.date == current_day].copy()
    day_df = day_df.sort_values(["impact_score", "event_name"], ascending=[False, True])

    day_title = pd.to_datetime(current_day).strftime("%A, %d %B %Y")
    st.markdown(f"### {day_title}")

    if day_df.empty:
        st.markdown(
            """
            <div class="empty-day-box">
                No events for this day.
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        for _, row in day_df.iterrows():
            render_event_row(row, selected_sector)

    st.markdown("---")
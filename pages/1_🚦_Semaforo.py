import calendar
from datetime import datetime
import pandas as pd
import streamlit as st

from data_loader import build_master_events_df, get_available_sectors, get_row_impact


st.set_page_config(page_title="Traffic Light", page_icon="🚦", layout="wide")

st.markdown(
    """
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .calendar-day {
        position: relative;
        cursor: pointer;
    }
    .calendar-day .tooltip-content {
        visibility: hidden;
        width: 260px;
        background-color: #333;
        color: #fff;
        text-align: left;
        border-radius: 8px;
        padding: 10px;
        position: absolute;
        z-index: 1000;
        bottom: 110%;
        left: 50%;
        transform: translateX(-50%);
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.85em;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .calendar-day .tooltip-content:after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #333 transparent transparent transparent;
    }
    .calendar-day:hover .tooltip-content {
        visibility: visible;
        opacity: 1;
    }
    .tooltip-event {
        padding: 3px 0;
        border-bottom: 1px solid #555;
    }
    .tooltip-event:last-child {
        border-bottom: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)


def get_month_options(start_year: int, end_year: int, start_month: int):
    options = []
    for year in range(start_year, end_year + 1):
        month_start = start_month if year == start_year else 1
        for month in range(month_start, 13):
            options.append((year, month))
    return options


def get_day_color(max_impact: int):
    if max_impact >= 4:
        return "#FF4444", "white", "🔴"
    if max_impact == 3:
        return "#FF8C00", "white", "🟠"
    if max_impact == 2:
        return "#FFD700", "#333", "🟡"
    return "#4CAF50", "white", "🟢"


def render_month_calendar(year: int, month: int, month_df: pd.DataFrame):
    cal = calendar.monthcalendar(year, month)
    week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    header_cols = st.columns(7)
    for i, day_name in enumerate(week_days):
        with header_cols[i]:
            st.markdown(f"**{day_name}**")

    for week in cal:
        cols = st.columns(7)

        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown(
                        """
                        <div style="
                            background-color: transparent;
                            padding: 15px;
                            border-radius: 8px;
                            text-align: center;
                            height: 100px;
                            display: flex;
                            flex-direction: column;
                            justify-content: center;
                            align-items: center;
                        "></div>
                        """,
                        unsafe_allow_html=True
                    )
                    continue

                current_date = datetime(year, month, day).date()
                day_events = month_df[month_df["date"].dt.date == current_date].copy()

                if day_events.empty:
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #f5f5f5;
                            padding: 15px;
                            border-radius: 8px;
                            text-align: center;
                            height: 100px;
                            display: flex;
                            flex-direction: column;
                            justify-content: center;
                            align-items: center;
                        ">
                            <div style="font-size: 1.2em; font-weight: bold; color: #666;">{day}</div>
                            <div style="font-size: 0.8em; color: #999; margin-top: 5px;">No events</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    continue

                max_impact = int(day_events["impact_score"].max())
                event_count = len(day_events)
                bg_color, text_color, emoji = get_day_color(max_impact)

                tooltip_html = f"<div class='tooltip-content'><strong>{day} {calendar.month_name[month]}</strong><br><br>"
                day_events = day_events.sort_values("impact_score", ascending=False)

                for _, event in day_events.iterrows():
                    impact = int(event["impact_score"])
                    impact_icon = "🔴" if impact >= 4 else "🟠" if impact == 3 else "🟡" if impact == 2 else "🟢"
                    event_name = str(event["event_name"])

                    if len(event_name) > 40:
                        event_name = event_name[:37] + "..."

                    tooltip_html += f"<div class='tooltip-event'>{impact_icon} {event_name}</div>"

                tooltip_html += "</div>"

                st.markdown(
                    f"""
                    <div class="calendar-day" style="
                        background-color: {bg_color};
                        padding: 15px;
                        border-radius: 8px;
                        text-align: center;
                        height: 100px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        position: relative;
                    ">
                        <div style="font-size: 1.3em; font-weight: bold; color: {text_color};">{day}</div>
                        <div style="font-size: 0.85em; color: {text_color}; margin-top: 5px;">
                            {emoji} {event_count} event{"s" if event_count != 1 else ""}
                        </div>
                        <div style="font-size: 0.8em; color: {text_color};">
                            Impact {max_impact}/4
                        </div>
                        {tooltip_html}
                    </div>
                    """,
                    unsafe_allow_html=True
                )


st.title("Traffic Light")
st.caption("Multi-month impact overview by sector and event type.")

master_df = build_master_events_df()

if master_df.empty:
    st.warning("No events are available.")
    st.stop()

sectors = ["General"] + [s for s in get_available_sectors() if s != "General"]

with st.sidebar:
    st.header("Filters")

    selected_sector = st.selectbox(
        "Sector",
        sectors,
        index=sectors.index("General") if "General" in sectors else 0
    )

    st.markdown("---")
    st.subheader("Base period")

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
    allowed_categories.extend(["Economic Event", "Evento Económico", "Evento Econmico"])
if show_mag7:
    allowed_categories.append("Magnificent 7")
if show_dow:
    allowed_categories.append("Dow Jones 30")
if show_top3:
    allowed_categories.extend(["Top 3 Sector", "3 big companies for each sector"])
if show_external:
    allowed_categories.extend(["External News", "Noticia Externa"])

display_df = master_df.copy()
display_df = display_df[display_df["date"].notna()].copy()

if allowed_categories:
    display_df = display_df[display_df["category"].isin(allowed_categories)].copy()
else:
    display_df = pd.DataFrame(columns=display_df.columns)

if not display_df.empty:
    display_df["impact_score"] = display_df["event_name"].apply(
        lambda event_name: get_row_impact(event_name, selected_sector)
    )
    display_df = display_df[display_df["impact_score"] >= min_impact].copy()
else:
    display_df["impact_score"] = []

st.markdown("### Select months")

month_options = get_month_options(
    start_year=selected_year,
    end_year=selected_year + 2,
    start_month=selected_month
)

selected_months = st.multiselect(
    "Choose one or more months",
    month_options,
    default=[(selected_year, selected_month)],
    format_func=lambda x: f"{calendar.month_name[x[1]]} {x[0]}"
)

if not selected_months:
    st.warning("Select at least one month.")
    st.stop()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Selected months", len(selected_months))
with col2:
    st.metric("Filtered events", len(display_df))
with col3:
    high_impact_count = len(display_df[display_df["impact_score"] == 4]) if not display_df.empty else 0
    st.metric("Impact 4 events", high_impact_count)

st.markdown("---")

for i, (year, month) in enumerate(selected_months):
    month_start = datetime(year, month, 1).date()
    month_end = datetime(year, month, calendar.monthrange(year, month)[1]).date()

    month_df = display_df[
        (display_df["date"].dt.date >= month_start) &
        (display_df["date"].dt.date <= month_end)
    ].copy()

    st.markdown(f"## {calendar.month_name[month]} {year}")

    if month_df.empty:
        st.info("No events match the selected filters for this month.")

    render_month_calendar(year, month, month_df)

    if i < len(selected_months) - 1:
        st.markdown("---")

st.markdown("---")
st.markdown("### Legend")

l1, l2, l3, l4, l5 = st.columns(5)
with l1:
    st.markdown("🟢 Low (1/4)")
with l2:
    st.markdown("🟡 Medium (2/4)")
with l3:
    st.markdown("🟠 High (3/4)")
with l4:
    st.markdown("🔴 Very High (4/4)")
with l5:
    st.markdown("⬜ No events")
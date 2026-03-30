import pandas as pd
from datetime import datetime
import streamlit as st

from data_loader import load_economic_events, load_economic_event_dates


st.set_page_config(page_title="Assign Dates", page_icon="🗓️", layout="wide")

ECONOMIC_DATES_FILE = "Fechas_eventos_economicos.csv"


def save_economic_event_date(event_name: str, new_date):
    try:
        try:
            df_dates = pd.read_csv(ECONOMIC_DATES_FILE)
        except Exception:
            df_dates = pd.DataFrame(columns=["event_name", "date", "source", "updated_at"])

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
        df_dates = df_dates.rename(columns=rename_map)

        for col in ["event_name", "date", "source", "updated_at"]:
            if col not in df_dates.columns:
                df_dates[col] = None

        new_row = {
            "event_name": str(event_name).strip(),
            "date": pd.to_datetime(new_date).strftime("%Y-%m-%d"),
            "source": "manual_app",
            "updated_at": datetime.now().isoformat()
        }

        df_dates = pd.concat([df_dates, pd.DataFrame([new_row])], ignore_index=True)
        df_dates["event_name"] = df_dates["event_name"].astype(str).str.strip()
        df_dates["date"] = pd.to_datetime(df_dates["date"], errors="coerce").dt.strftime("%Y-%m-%d")

        df_dates = df_dates.dropna(subset=["event_name", "date"])
        df_dates = df_dates.sort_values(["event_name", "date"]).reset_index(drop=True)
        df_dates.to_csv(ECONOMIC_DATES_FILE, index=False)

        return True, "Date saved successfully."
    except Exception as e:
        return False, f"Error: {e}"


st.title("Assign Dates")
st.caption("Assign one or more manual dates to economic events.")

economic_df = load_economic_events().copy()
economic_dates_df = load_economic_event_dates().copy()

if economic_df.empty:
    st.warning("No economic events available.")
    st.stop()

economic_df["event_name"] = economic_df["event_name"].astype(str).str.strip()

if not economic_dates_df.empty:
    economic_dates_df["event_name"] = economic_dates_df["event_name"].astype(str).str.strip()
    economic_dates_df["date"] = pd.to_datetime(economic_dates_df["date"], errors="coerce")

date_count_map = (
    economic_dates_df.groupby("event_name")
    .size()
    .to_dict()
    if not economic_dates_df.empty else {}
)

economic_df["assigned_dates_count"] = economic_df["event_name"].map(date_count_map).fillna(0).astype(int)

st.info("You can keep assigning dates to the same event. Events stay visible even if they already have one or more dates.")

category_options = ["All"] + sorted(economic_df["category"].dropna().unique().tolist())
selected_category = st.selectbox("Filter by category", category_options)

filtered_df = economic_df.copy()
if selected_category != "All":
    filtered_df = filtered_df[filtered_df["category"] == selected_category].copy()

if filtered_df.empty:
    st.info(f"No events found for category: {selected_category}")
    st.stop()

filtered_df = filtered_df.sort_values(["event_name"]).reset_index(drop=True)

selected_idx = st.selectbox(
    "Select an event",
    range(len(filtered_df)),
    format_func=lambda i: (
        f"{filtered_df.iloc[i]['event_name']} "
        f"({filtered_df.iloc[i]['category']}) - "
        f"{filtered_df.iloc[i]['assigned_dates_count']} saved date(s)"
    )
)

selected_event = filtered_df.iloc[selected_idx]
selected_event_name = selected_event["event_name"]

existing_dates = pd.DataFrame()
if not economic_dates_df.empty:
    existing_dates = economic_dates_df[
        economic_dates_df["event_name"] == selected_event_name
    ].copy()

    if not existing_dates.empty:
        existing_dates = existing_dates.sort_values("date").reset_index(drop=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Event Information")
    st.markdown(f"**Name:** {selected_event.get('event_name', '')}")
    st.markdown(f"**Category:** {selected_event.get('category', '')}")
    st.markdown(f"**Saved dates:** {int(selected_event.get('assigned_dates_count', 0))}")

    if pd.notna(selected_event.get("description")) and str(selected_event.get("description")).strip():
        st.markdown(f"**Description:** {selected_event.get('description')}")

with col2:
    st.markdown("### Add Date")

    with st.form("assign_date_form"):
        new_date = st.date_input("Date", value=datetime.now().date())
        st.info("A new row will be added to Fechas_eventos_economicos.csv.")
        submitted = st.form_submit_button("Save Date", use_container_width=True)

        if submitted:
            success, message = save_economic_event_date(
                event_name=selected_event_name,
                new_date=new_date
            )

            if success:
                st.success(message)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(message)

st.markdown("---")
st.subheader("Existing Dates for Selected Event")

if existing_dates.empty:
    st.info("This event has no saved dates yet.")
else:
    show_dates = existing_dates.copy()
    show_dates["date"] = pd.to_datetime(show_dates["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    visible_cols = [c for c in ["date", "source", "updated_at"] if c in show_dates.columns]
    st.dataframe(show_dates[visible_cols], use_container_width=True, hide_index=True)

st.markdown("---")
st.subheader("Events Overview")

overview_df = filtered_df[["event_name", "category", "assigned_dates_count"]].copy()
overview_df = overview_df.sort_values(["assigned_dates_count", "event_name"], ascending=[False, True])
st.dataframe(overview_df, use_container_width=True, hide_index=True)
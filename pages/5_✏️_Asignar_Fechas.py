import os
from datetime import datetime
import pandas as pd
import streamlit as st

from data_loader import (
    build_master_events_df,
    load_economic_events,
    load_economic_event_dates,
)


st.set_page_config(page_title="Assign Dates", page_icon="🗓️", layout="wide")


ECONOMIC_DATES_FILE = "Fechas_eventos_economicos.csv"


def save_economic_event_date(event_name: str, new_date):
    try:
        try:
            df_dates = pd.read_csv(ECONOMIC_DATES_FILE)
        except Exception:
            df_dates = pd.DataFrame(columns=["event_name", "date", "source", "updated_at"])

        if df_dates.empty:
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

        df_dates["event_name"] = df_dates["event_name"].astype(str).str.strip()

        new_row = {
            "event_name": str(event_name).strip(),
            "date": pd.to_datetime(new_date).strftime("%Y-%m-%d"),
            "source": "manual_app",
            "updated_at": datetime.now().isoformat()
        }

        if (df_dates["event_name"] == new_row["event_name"]).any():
            df_dates.loc[df_dates["event_name"] == new_row["event_name"], ["date", "source", "updated_at"]] = [
                new_row["date"], new_row["source"], new_row["updated_at"]
            ]
        else:
            df_dates = pd.concat([df_dates, pd.DataFrame([new_row])], ignore_index=True)

        df_dates = df_dates[["event_name", "date", "source", "updated_at"]]
        df_dates = df_dates.sort_values(["event_name"]).reset_index(drop=True)
        df_dates.to_csv(ECONOMIC_DATES_FILE, index=False)

        return True, "Date saved successfully."
    except Exception as e:
        return False, f"Error: {e}"


st.title("Assign Dates")
st.caption("Assign manual dates to events that still do not have one.")

master_df = build_master_events_df()
economic_df = load_economic_events()
economic_dates_df = load_economic_event_dates()

economic_without_dates = economic_df[~economic_df["event_name"].isin(economic_dates_df["event_name"])].copy()
economic_without_dates["source_group"] = "Economic Events CSV"

undated_df = economic_without_dates.copy()

if undated_df.empty:
    st.success("All events already have assigned dates.")
    st.stop()

st.info("Use this section to manually assign dates to events that still have no date.")

category_options = ["All"] + sorted(undated_df["category"].dropna().unique().tolist())
selected_category = st.selectbox("Filter by category", category_options)

if selected_category != "All":
    undated_df = undated_df[undated_df["category"] == selected_category].copy()

if undated_df.empty:
    st.info(f"No undated events found for category: {selected_category}")
    st.stop()

st.warning(f"{len(undated_df)} events without date found.")

undated_df = undated_df.sort_values("event_name").reset_index(drop=True)

selected_idx = st.selectbox(
    "Select an event",
    range(len(undated_df)),
    format_func=lambda i: f"{undated_df.iloc[i]['event_name']} ({undated_df.iloc[i]['category']})"
)

selected_event = undated_df.iloc[selected_idx]

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Event Information")
    st.markdown(f"**Name:** {selected_event.get('event_name', '')}")
    st.markdown(f"**Category:** {selected_event.get('category', '')}")
    st.markdown(f"**Source group:** {selected_event.get('source_group', '')}")

    if pd.notna(selected_event.get("ticker")) and str(selected_event.get("ticker")).strip():
        st.markdown(f"**Ticker:** {selected_event.get('ticker')}")

    if pd.notna(selected_event.get("description")) and str(selected_event.get("description")).strip():
        st.markdown(f"**Description:** {selected_event.get('description')}")

with col2:
    st.markdown("### Assign Date")

    with st.form("assign_date_form"):
        new_date = st.date_input(
            "Date",
            value=datetime.now().date()
        )

        st.info("The saved value will be written to Fechas_eventos_economicos.csv.")

        submitted = st.form_submit_button("Save Date", use_container_width=True)

        if submitted:
            success, message = save_economic_event_date(
                event_name=selected_event["event_name"],
                new_date=new_date
            )

            if success:
                st.success(message)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(message)

st.markdown("---")
st.subheader("Undated Events Preview")

preview_cols = [col for col in ["event_name", "category", "ticker", "source_group"] if col in undated_df.columns]
st.dataframe(undated_df[preview_cols], use_container_width=True, hide_index=True)
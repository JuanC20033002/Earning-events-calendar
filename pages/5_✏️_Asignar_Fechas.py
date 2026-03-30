import pandas as pd
from datetime import datetime
import streamlit as st

from data_loader import load_economic_events, load_economic_event_dates

st.set_page_config(page_title="Assign Dates", page_icon="🗓️", layout="wide")

ECONOMIC_DATES_FILE = "Fechas_eventos_economicos.csv"


def normalize_dates_df(df):
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

    for col in ["event_name", "date", "source", "updated_at"]:
        if col not in df.columns:
            df[col] = None

    df["event_name"] = df["event_name"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def read_dates_file():
    try:
        df = pd.read_csv(ECONOMIC_DATES_FILE)
    except Exception:
        df = pd.DataFrame(columns=["event_name", "date", "source", "updated_at"])
    return normalize_dates_df(df)


def save_economic_event_date(event_name: str, new_date):
    try:
        df_dates = read_dates_file()

        new_date_ts = pd.to_datetime(new_date)
        event_name = str(event_name).strip()

        duplicate_mask = (
            (df_dates["event_name"] == event_name) &
            (df_dates["date"] == new_date_ts)
        )

        if duplicate_mask.any():
            return False, "That exact date is already saved for this event."

        new_row = pd.DataFrame([{
            "event_name": event_name,
            "date": new_date_ts,
            "source": "manual_app",
            "updated_at": datetime.now().isoformat()
        }])

        df_dates = pd.concat([df_dates, new_row], ignore_index=True)
        df_dates = df_dates.dropna(subset=["event_name", "date"])
        df_dates = df_dates.sort_values(["event_name", "date"]).reset_index(drop=True)
        df_dates["date"] = df_dates["date"].dt.strftime("%Y-%m-%d")
        df_dates.to_csv(ECONOMIC_DATES_FILE, index=False)

        return True, "Date added successfully."
    except Exception as e:
        return False, f"Error: {e}"


def delete_manual_date(event_name: str, date_value):
    try:
        df_dates = read_dates_file()
        target_date = pd.to_datetime(date_value)
        event_name = str(event_name).strip()

        before = len(df_dates)
        df_dates = df_dates[
            ~(
                (df_dates["event_name"] == event_name) &
                (df_dates["date"] == target_date)
            )
        ].copy()

        if len(df_dates) == before:
            return False, "No matching date was found to delete."

        df_dates = df_dates.sort_values(["event_name", "date"]).reset_index(drop=True)
        df_dates["date"] = pd.to_datetime(df_dates["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df_dates.to_csv(ECONOMIC_DATES_FILE, index=False)

        return True, "Manual date deleted successfully."
    except Exception as e:
        return False, f"Error: {e}"


st.title("Assign Dates")
st.caption("Assign one or more manual dates to economic events.")

economic_df = load_economic_events().copy()
dates_df = read_dates_file()

if economic_df.empty:
    st.warning("No economic events available.")
    st.stop()

economic_df["event_name"] = economic_df["event_name"].astype(str).str.strip()

count_map = dates_df.groupby("event_name").size().to_dict() if not dates_df.empty else {}
economic_df["assigned_dates_count"] = economic_df["event_name"].map(count_map).fillna(0).astype(int)

st.info("All economic events remain visible here, even if they already have saved dates.")

category_options = ["All"] + sorted(economic_df["category"].dropna().unique().tolist())
selected_category = st.selectbox("Filter by category", category_options)

filtered_df = economic_df.copy()
if selected_category != "All":
    filtered_df = filtered_df[filtered_df["category"] == selected_category].copy()

filtered_df = filtered_df.sort_values(["event_name"]).reset_index(drop=True)

if filtered_df.empty:
    st.info(f"No events found for category: {selected_category}")
    st.stop()

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

existing_dates = dates_df[dates_df["event_name"] == selected_event_name].copy()
existing_dates = existing_dates.sort_values("date").reset_index(drop=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Event Information")
    st.markdown(f"**Name:** {selected_event_name}")
    st.markdown(f"**Category:** {selected_event.get('category', '')}")
    st.markdown(f"**Saved dates:** {int(selected_event.get('assigned_dates_count', 0))}")

    if pd.notna(selected_event.get("description")) and str(selected_event.get("description")).strip():
        st.markdown(f"**Description:** {selected_event.get('description')}")

with col2:
    st.markdown("### Add Date")
    with st.form("assign_date_form"):
        new_date = st.date_input("Date", value=datetime.now().date())
        submitted = st.form_submit_button("Add Date", use_container_width=True)

        if submitted:
            ok, msg = save_economic_event_date(selected_event_name, new_date)
            if ok:
                st.success(msg)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(msg)

st.markdown("---")
st.subheader("Saved Dates for Selected Event")

if existing_dates.empty:
    st.info("This event has no saved dates yet.")
else:
    for i, row in existing_dates.iterrows():
        c1, c2 = st.columns([4, 1])
        with c1:
            show_date = pd.to_datetime(row["date"], errors="coerce")
            show_date = show_date.strftime("%Y-%m-%d") if pd.notna(show_date) else "Invalid date"
            st.markdown(f"**{show_date}** · source: {row.get('source', 'unknown')}")
        with c2:
            if st.button("Delete", key=f"del_{selected_event_name}_{i}", use_container_width=True):
                ok, msg = delete_manual_date(selected_event_name, row["date"])
                if ok:
                    st.success(msg)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)

st.markdown("---")
st.subheader("Events Overview")
overview_df = filtered_df[["event_name", "category", "assigned_dates_count"]].copy()
overview_df = overview_df.sort_values(["assigned_dates_count", "event_name"], ascending=[False, True])
st.dataframe(overview_df, use_container_width=True, hide_index=True)
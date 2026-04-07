import pandas as pd
from datetime import datetime
import streamlit as st

from data_loader import load_economic_events, _get_supabase_client

st.set_page_config(page_title="Assign Dates", page_icon="🗓️", layout="wide")

SUPABASE_TABLE = "economic_event_dates"


def fetch_dates_from_supabase():
    client = _get_supabase_client()
    if client is None:
        return pd.DataFrame(columns=["event_name", "date", "source", "updated_at"])

    try:
        response = client.table(SUPABASE_TABLE).select("*").order("date").execute()
        df = pd.DataFrame(response.data or [])
    except Exception:
        return pd.DataFrame(columns=["event_name", "date", "source", "updated_at"])

    if df.empty:
        return pd.DataFrame(columns=["event_name", "date", "source", "updated_at"])

    df.columns = [str(c).strip().lower() for c in df.columns]

    for col in ["event_name", "date", "source", "updated_at"]:
        if col not in df.columns:
            df[col] = None

    df["event_name"] = df["event_name"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["event_name", "date"]).copy()

    return df[["event_name", "date", "source", "updated_at"]]


def cleanup_expired_dates():
    client = _get_supabase_client()
    if client is None:
        return 0

    try:
        cutoff_date = (pd.Timestamp.today().normalize() - pd.Timedelta(days=3)).strftime("%Y-%m-%d")

        response = (
            client.table(SUPABASE_TABLE)
            .delete()
            .lte("date", cutoff_date)
            .execute()
        )

        if response.data is None:
            return 0

        return len(response.data)
    except Exception:
        return 0


def save_economic_event_date(event_name: str, new_date):
    client = _get_supabase_client()
    if client is None:
        return False, "Supabase is not configured."

    try:
        event_name = str(event_name).strip()
        new_date_ts = pd.to_datetime(new_date, errors="coerce")

        if pd.isna(new_date_ts):
            return False, "Invalid date."

        existing = client.table(SUPABASE_TABLE).select("id").eq("event_name", event_name).eq(
            "date", new_date_ts.strftime("%Y-%m-%d")
        ).execute()

        if existing.data:
            return False, "That exact date is already saved for this event."

        payload = {
            "event_name": event_name,
            "date": new_date_ts.strftime("%Y-%m-%d"),
            "source": "manual_app",
            "updated_at": datetime.now().isoformat()
        }

        response = client.table(SUPABASE_TABLE).insert(payload).execute()

        if not response.data:
            return False, "Could not save the date."

        return True, "Date added successfully."
    except Exception as e:
        return False, f"Error: {e}"


def delete_manual_date(event_name, event_date):
    client = _get_supabase_client()
    if client is None:
        return False, "Supabase is not configured."

    try:
        event_name = str(event_name).strip()
        event_date_ts = pd.to_datetime(event_date, errors="coerce")

        if not event_name or pd.isna(event_date_ts):
            return False, "Invalid event name or date."

        response = (
            client.table(SUPABASE_TABLE)
            .delete()
            .eq("event_name", event_name)
            .eq("date", event_date_ts.strftime("%Y-%m-%d"))
            .execute()
        )

        if response.data is None:
            return False, "No matching date was found to delete."

        return True, "Manual date deleted successfully."
    except Exception as e:
        return False, f"Error: {e}"


st.title("Assign Dates")
st.caption("Assign one or more manual dates to economic events.")

economic_df = load_economic_events().copy()

deleted_count = cleanup_expired_dates()
dates_df = fetch_dates_from_supabase()

if deleted_count > 0:
    st.info(f"Automatic cleanup removed {deleted_count} expired date(s).")

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

        row_date = pd.to_datetime(row["date"], errors="coerce")
        row_date_text = row_date.strftime("%Y-%m-%d") if pd.notna(row_date) else "Invalid date"

        with c1:
            st.markdown(f"**{row_date_text}** · source: {row.get('source', 'unknown')}")

        with c2:
            if st.button("Delete", key=f"del_{selected_event_name}_{row_date_text}_{i}", use_container_width=True):
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
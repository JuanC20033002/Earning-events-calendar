import os
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client

from data_loader import build_master_events_df, get_available_sectors


st.set_page_config(page_title="External News", page_icon="📰", layout="wide")


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


def create_external_news(title, selected_sectors, impact, description, event_date):
    try:
        supabase = get_supabase_client()

        payload = {
            "titulo": title.strip(),
            "fecha": datetime.combine(event_date, datetime.min.time()).isoformat(),
            "descripcion": description.strip() if description else None,
            "sectores": selected_sectors,
            "impacto": int(impact),
        }

        response = supabase.table("noticias_externas").insert(payload).execute()

        if not response.data:
            return False, "Could not create the external news item."

        return True, f"External news created successfully for {len(selected_sectors)} sector(s)."
    except Exception as e:
        return False, f"Error: {e}"


def delete_external_news(record_id):
    try:
        supabase = get_supabase_client()
        supabase.table("noticias_externas").delete().eq("id", record_id).execute()
        return True, "External news deleted successfully."
    except Exception as e:
        return False, f"Error: {e}"


st.title("External News")
st.caption("Create custom news events with impact by sector and manage existing external news.")

available_sectors = ["General"] + get_available_sectors()

st.subheader("Add External News")
st.info("Create a custom event and assign one or more affected sectors.")

with st.form("external_news_form"):
    title = st.text_input(
        "News Title",
        placeholder="Example: Change in banking regulation"
    )

    st.markdown("---")
    st.markdown("#### Affected sectors")

    select_all = st.checkbox("Select all sectors")

    selectable_sectors = [sector for sector in available_sectors if sector != "General"]

    if select_all:
        selected_sectors = selectable_sectors
        st.info(f"{len(selected_sectors)} sectors selected.")
    else:
        selected_sectors = st.multiselect(
            "Select one or more sectors",
            selectable_sectors,
            default=[]
        )

    st.markdown("---")

    impact = st.select_slider(
        "Impact level",
        options=[1, 2, 3, 4],
        value=2,
        format_func=lambda x: {
            1: "1/4 - Low",
            2: "2/4 - Medium",
            3: "3/4 - High",
            4: "4/4 - Very High"
        }[x]
    )

    st.markdown("---")

    description = st.text_area(
        "Description (Optional)",
        placeholder="Add extra context about this news item...",
        height=100
    )

    st.markdown("---")

    event_date = st.date_input(
        "Event Date",
        value=datetime.now().date()
    )

    submitted = st.form_submit_button("Create External News", use_container_width=True)

    if submitted:
        if not title.strip():
            st.error("Title is required.")
        elif not selected_sectors:
            st.error("You must select at least one sector.")
        else:
            success, message = create_external_news(
                title=title,
                selected_sectors=selected_sectors,
                impact=impact,
                description=description,
                event_date=event_date
            )

            if success:
                st.success(message)
                st.cache_data.clear()
                st.balloons()
                st.rerun()
            else:
                st.error(message)

st.markdown("---")
st.subheader("Registered External News")

master_df = build_master_events_df()

external_news_df = master_df[master_df["category"] == "External News"].copy()

if external_news_df.empty:
    st.info("No external news registered.")
else:
    external_news_df = external_news_df.sort_values("date", ascending=False).reset_index(drop=True)

    try:
        supabase = get_supabase_client()
        raw_response = supabase.table("noticias_externas").select("*").order("fecha", desc=True).execute()
        raw_news_df = pd.DataFrame(raw_response.data or [])
    except Exception as e:
        st.error(f"Could not load raw external news records: {e}")
        raw_news_df = pd.DataFrame()

    if raw_news_df.empty:
        st.info("No external news records found in Supabase.")
    else:
        for _, news in raw_news_df.iterrows():
            news_title = news.get("titulo", "Untitled")
            news_date = pd.to_datetime(news.get("fecha"), errors="coerce")
            news_description = news.get("descripcion")
            news_sectors = news.get("sectores", [])
            news_impact = news.get("impacto")
            news_id = news.get("id")

            expander_title = (
                f"{news_title} - {news_date.strftime('%d/%m/%Y')}"
                if pd.notna(news_date)
                else news_title
            )

            with st.expander(expander_title):
                col1, col2 = st.columns([2, 1])

                with col1:
                    if pd.notna(news_date):
                        st.markdown(f"**Date:** {news_date.strftime('%d %B %Y')}")
                    else:
                        st.markdown("**Date:** Not available")

                    st.markdown("**Category:** External News")

                    if news_description and str(news_description).strip():
                        st.markdown(f"**Description:** {news_description}")

                    if isinstance(news_sectors, list) and news_sectors:
                        visible_sectors = ", ".join(news_sectors[:3])
                        if len(news_sectors) > 3:
                            visible_sectors += "..."
                        st.markdown(f"**Sectors:** {len(news_sectors)}")
                        st.markdown(visible_sectors)
                    else:
                        st.markdown("**Sectors:** None")

                    if pd.notna(news_impact):
                        st.markdown(f"**Impact:** {int(news_impact)}/4")

                with col2:
                    st.markdown("**Actions**")
                    st.info("External News will be deleted completely.")

                    if st.button(
                        "Delete News",
                        key=f"delete_external_news_{news_id}",
                        use_container_width=True
                    ):
                        success, message = delete_external_news(news_id)

                        if success:
                            st.success(message)
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(message)
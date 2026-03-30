import streamlit as st
from supabase import create_client, Client
import pandas as pd
import os


# ==========================================
# CONFIG
# ==========================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ==========================================
# ESTILOS
# ==========================================
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
        border-radius: 5px;
        padding: 0.5rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #FF6B6B;
        border-color: #FF4B4B;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.2rem;
    }
    h1 {
        color: #FF4B4B;
        padding-bottom: 1rem;
    }
    h2 {
        color: #262730;
        padding-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# FUNCIONES
# ==========================================
@st.cache_data(ttl=300)
def obtener_macro_2026():
    try:
        res = (
            supabase.table("macro_regime_monthly_us")
            .select("anio,mes,score,regime,drivers,updated_at")
            .eq("anio", 2026)
            .order("mes", desc=False)
            .execute()
        )

        df = pd.DataFrame(res.data or [])

        if df.empty:
            return df

        df["mes"] = df["mes"].astype(int)
        df["fecha"] = pd.to_datetime(
            df["anio"].astype(str) + "-" + df["mes"].astype(str) + "-01"
        )

        return df.sort_values("mes")

    except Exception as e:
        st.error(f"Error al cargar macro 2026: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def obtener_macro_run_logs(limit=2):
    try:
        res = (
            supabase.table("macro_regime_run_log")
            .select("run_at,status,summary,error")
            .order("run_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        st.error(f"Error al cargar macro run logs: {e}")
        return []


# ==========================================
# PAGE
# ==========================================
st.title("🌍 Macro 2026")
st.info("📌 Vista del score macro mensual de 2026 y comparación entre corridas.")

df_macro = obtener_macro_2026()
run_logs = obtener_macro_run_logs(limit=2)

# ==========================================
# CURVA 2026
# ==========================================
st.markdown("## Curva 2026")

if df_macro.empty:
    st.warning("⚠️ No hay datos en `macro_regime_monthly_us` para 2026 todavía.")
else:
    st.line_chart(df_macro.set_index("fecha")[["score"]])

    ultimo_score = float(df_macro["score"].iloc[-1]) if "score" in df_macro.columns else 0.0
    ultimo_regime = str(df_macro["regime"].iloc[-1]) if "regime" in df_macro.columns else "N/A"
    meses_cargados = int(df_macro.shape[0])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Último score", ultimo_score)

    with col2:
        st.metric("Régimen actual", ultimo_regime)

    with col3:
        st.metric("Meses cargados", meses_cargados)

    st.markdown("### Tabla mensual")
    df_view = df_macro.copy()

    columnas_visibles = [c for c in ["anio", "mes", "score", "regime", "updated_at"] if c in df_view.columns]
    st.dataframe(df_view[columnas_visibles], use_container_width=True)

    st.markdown("### Drivers (último mes)")
    drivers = df_macro["drivers"].iloc[-1] if "drivers" in df_macro.columns else []

    if isinstance(drivers, list) and drivers:
        df_drv = pd.DataFrame(drivers)
        cols_drv = [c for c in ["name", "key", "latest_value", "z_adj", "weight", "contribution"] if c in df_drv.columns]
        st.dataframe(df_drv[cols_drv], use_container_width=True)
    else:
        st.info("No hay drivers disponibles en el campo `drivers`.")

# ==========================================
# COMPARACIÓN DE CORRIDAS
# ==========================================
st.markdown("---")
st.markdown("## Qué cambió vs corrida anterior")

if not run_logs:
    st.info("No hay registros en `macro_regime_run_log` todavía.")
else:
    last = run_logs[0]
    prev = run_logs[1] if len(run_logs) > 1 else None

    st.markdown("### Última corrida")
    st.write(f"**Run UTC:** {last.get('run_at')}")
    st.write(f"**Status:** {last.get('status')}")

    if last.get("status") == "error":
        st.error(f"Última corrida falló: {last.get('error')}")
    else:
        s_last = last.get("summary", {}) or {}
        st.write(f"**Score now:** {s_last.get('score_now')}")
        st.write(f"**Regime now:** {s_last.get('regime_now', 'N/A')}")

        if not prev:
            st.info("Aún no hay una corrida anterior para comparar.")
        elif prev.get("status") != "success":
            st.info("La corrida anterior no fue exitosa, así que no se puede comparar correctamente.")
        else:
            s_prev = prev.get("summary", {}) or {}

            try:
                delta_score = float(s_last.get("score_now", 0)) - float(s_prev.get("score_now", 0))
            except Exception:
                delta_score = 0.0

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Score actual",
                    f"{float(s_last.get('score_now', 0)):.4f}" if s_last.get("score_now") is not None else "N/A"
                )

            with col2:
                st.metric(
                    "Δ score vs anterior",
                    f"{delta_score:+.4f}"
                )

            drv_last = s_last.get("drivers", []) or []
            drv_prev = s_prev.get("drivers", []) or []

            if not drv_last or not drv_prev:
                st.info("La comparación de drivers estará disponible después de 2 corridas que incluyan `summary.drivers`.")
                st.caption("Tip: guarda `summary['drivers'] = drivers` en tu pipeline para comparar contribuciones entre corridas.")
            else:
                df_last = pd.DataFrame(drv_last)
                df_prev = pd.DataFrame(drv_prev)

                if "key" in df_last.columns and "key" in df_prev.columns and "contribution" in df_last.columns and "contribution" in df_prev.columns:
                    df_cmp = df_last.merge(
                        df_prev[["key", "contribution"]],
                        on="key",
                        how="left",
                        suffixes=("_last", "_prev")
                    )

                    df_cmp["contribution_prev"] = df_cmp["contribution_prev"].fillna(0.0)
                    df_cmp["delta_contribution"] = df_cmp["contribution_last"] - df_cmp["contribution_prev"]

                    st.markdown("### Cambios en drivers")

                    cols_cmp = [c for c in ["name", "key", "contribution_last", "contribution_prev", "delta_contribution"] if c in df_cmp.columns]
                    st.dataframe(
                        df_cmp[cols_cmp].sort_values("delta_contribution", ascending=False),
                        use_container_width=True
                    )

                    top_up = df_cmp.sort_values("delta_contribution", ascending=False).head(3)
                    top_down = df_cmp.sort_values("delta_contribution", ascending=True).head(3)

                    col_up, col_down = st.columns(2)

                    with col_up:
                        st.markdown("### Top ↑")
                        for _, r in top_up.iterrows():
                            st.write(f"- {r.get('name', '')} ({r.get('key', '')}): {r['delta_contribution']:+.4f}")

                    with col_down:
                        st.markdown("### Top ↓")
                        for _, r in top_down.iterrows():
                            st.write(f"- {r.get('name', '')} ({r.get('key', '')}): {r['delta_contribution']:+.4f}")
                else:
                    st.info("Los drivers no tienen la estructura esperada para comparar contribuciones.")
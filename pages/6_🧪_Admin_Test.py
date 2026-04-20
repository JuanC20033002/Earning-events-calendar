# pages/6_🧪_Admin_Test.py

import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Config ─────────────────────────────────────────────────────────────────
CSV_FILE = "SP500_TEST.csv"
TODAY = pd.Timestamp.today().normalize()

# ── Scoring weights (same as Pandora Universe) ─────────────────────────────
SECTION_WEIGHTS = {
    "Core Fundamentals": 30.0,
    "Ratings & Factor Grades": 30.0,
    "Valuation & Size & Risk": 20.0,
    "Earnings Signals": 20.0,
}

METRIC_WEIGHTS = {
    "Core Fundamentals": {
        "Profit Margin": 4.0,
        "FCF Margin": 4.0,
        "EBITDA Margin": 3.0,
        "Return on Assets": 3.0,
        "Return on Equity": 3.0,
        "Net Income 3Y": 2.0,
        "Revenue 3Y": 2.0,
        "Profitability Grade": 2.0,
        "Div Safety": 1.5,
        "Div Growth": 1.5,
        "Div Yield": 1.5,
        "Div Consistency": 1.5,
        "Payout Ratio": 0.5,
        "Yield TTM": 0.5,
    },
    "Ratings & Factor Grades": {
        "Quant Rating": 7.0,
        "SA Analyst Ratings": 6.0,
        "Wall Street Ratings": 6.0,
        "Valuation Grade": 4.0,
        "Momentum Grade": 4.0,
        "EPS Revision Grade": 3.0,
    },
    "Valuation & Size & Risk": {
        "Market Cap": 4.0,
        "P/E FWD": 4.0,
        "Price / Sales": 3.5,
        "EV / EBITDA": 3.5,
        "Price / Book": 2.5,
        "Altman Z Score": 2.5,
    },
    "Earnings Signals": {
        "EPS YoY": 4.0,
        "EPS Growth (FWD)": 4.0,
        "Revenue YoY": 4.0,
        "Revenue FWD": 4.0,
        "EPS Surprise": 2.0,
        "Revenue Surprise": 2.0,
    },
}

LETTER_MAP = {
    "A+": 100, "A": 95, "A-": 90,
    "B+": 85, "B": 80, "B-": 75,
    "C+": 70, "C": 65, "C-": 60,
    "D+": 55, "D": 50, "D-": 45,
    "F": 35,
}

GRADE_BANDS = [
    (95, "A+"), (90, "A"), (85, "A-"), (80, "B+"), (75, "B"), (70, "B-"),
    (65, "C+"), (60, "C"), (55, "C-"), (50, "D+"), (45, "D"), (0, "D-")
]

GRADE_ORDER = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-"]

# ── Analyst rating mapping ──────────────────────────────────────────────────
# SA / Wall Street / Quant use a 1.0–5.0 scale
# 1.0–1.5 = Strong Sell, 1.5–2.5 = Sell, 2.5–3.5 = Neutral, 3.5–4.5 = Buy, 4.5–5.0 = Strong Buy
ANALYST_RATING_ORDER = ["Strong Buy", "Buy", "Neutral", "Sell", "Strong Sell", "N/A"]

def numeric_to_analyst_label(val) -> str:
    """Convert numeric analyst score (1–5) to a label."""
    try:
        v = float(str(val).strip().replace(",", ""))
    except (ValueError, TypeError):
        return "N/A"
    if v >= 4.5:
        return "Strong Buy"
    if v >= 3.5:
        return "Buy"
    if v >= 2.5:
        return "Neutral"
    if v >= 1.5:
        return "Sell"
    return "Strong Sell"

ANALYST_LABEL_COLORS = {
    "Strong Buy": "#16a34a",
    "Buy": "#4ade80",
    "Neutral": "#94a3b8",
    "Sell": "#f97316",
    "Strong Sell": "#dc2626",
    "N/A": "#cbd5e1",
}

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Admin Test – SP500", page_icon="🧪", layout="wide")

st.markdown(
    """
    <style>
    .main {padding-top: 0.5rem;}
    h1, h2, h3 {color: #0f766e;}
    .stMultiSelect [data-baseweb="tag"] {background-color: #ccfbf1 !important;}
    .stMultiSelect [data-baseweb="tag"] span {color: #000000 !important; font-weight: 600;}
    .stMultiSelect [data-baseweb="tag"] svg {fill: #000000 !important; color: #000000 !important;}
    .warning-box {
        padding: 0.85rem 1rem; border-radius: 0.75rem; margin-bottom: 0.6rem;
        border-left: 6px solid #f59e0b; background: #fffbeb; color: #92400e;
    }
    .info-box {
        padding: 0.85rem 1rem; border-radius: 0.75rem; margin-bottom: 0.6rem;
        border-left: 6px solid #0ea5e9; background: #f0f9ff; color: #075985;
    }
    .score-card {
        padding: 1rem; border-radius: 1rem;
        background: linear-gradient(135deg, #0f766e, #14b8a6);
        color: white; text-align: center; margin-bottom: 0.8rem;
    }
    .subtle {color: #64748b; font-size: 0.95rem;}
    .rating-chip {
        display: inline-block; padding: 2px 10px; border-radius: 999px;
        font-size: 0.8rem; font-weight: 700; color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Helpers (identical to Pandora Universe) ────────────────────────────────
def clamp(x, lo=0, hi=100):
    if pd.isna(x):
        return None
    return max(lo, min(hi, float(x)))

def parse_numeric(v):
    if pd.isna(v):
        return None
    s = str(v).strip().replace(",", "")
    if s in {"", "-", "NM", "N/M", "None", "nan"}:
        return None
    pct = s.endswith("%")
    if pct:
        s = s[:-1]
    try:
        return float(s)
    except Exception:
        return None

def parse_date(v):
    return pd.to_datetime(v, errors="coerce")

def score_letter(v):
    if pd.isna(v):
        return 55.0
    s = str(v).strip()
    return float(LETTER_MAP.get(s, 55.0))

def score_higher_better(v, bad, good):
    x = parse_numeric(v)
    if x is None: return 50.0
    if x <= bad: return 0.0
    if x >= good: return 100.0
    return clamp((x - bad) / (good - bad) * 100.0)

def score_middle_better(v, low_good, high_good, min_bad, max_bad):
    x = parse_numeric(v)
    if x is None: return 50.0
    if low_good <= x <= high_good: return 100.0
    if x < low_good:
        if x <= min_bad: return 0.0
        return clamp((x - min_bad) / (low_good - min_bad) * 100.0)
    if x >= max_bad: return 0.0
    return clamp((max_bad - x) / (max_bad - high_good) * 100.0)

def score_lower_better(v, best, worst):
    x = parse_numeric(v)
    if x is None or x <= 0: return 35.0
    if x <= best: return 100.0
    if x >= worst: return 0.0
    return clamp((worst - x) / (worst - best) * 100.0)

def score_lower_better_positive(v, best, worst):
    x = parse_numeric(v)
    if x is None: return 35.0
    if x < 0: return 0.0
    if x <= best: return 100.0
    if x >= worst: return 0.0
    return clamp((worst - x) / (worst - best) * 100.0)

def score_metric(col, val, df):
    if col in {"Valuation Grade", "Profitability Grade", "Momentum Grade",
               "EPS Revision Grade", "Div Consistency", "Div Growth", "Div Safety"}:
        return score_letter(val)
    if col in {"Quant Rating", "SA Analyst Ratings", "Wall Street Ratings"}:
        return score_higher_better(val, 3.0, 4.5)
    if col == "Profit Margin": return score_higher_better(val, 0.0, 20.0)
    if col == "FCF Margin": return score_higher_better(val, 0.0, 20.0)
    if col == "EBITDA Margin": return score_higher_better(val, 0.0, 30.0)
    if col == "Return on Assets": return score_higher_better(val, 0.0, 10.0)
    if col == "Return on Equity": return score_higher_better(val, 0.0, 20.0)
    if col == "Net Income 3Y": return score_higher_better(val, -10.0, 40.0)
    if col == "Revenue 3Y": return score_higher_better(val, -5.0, 20.0)
    if col in {"Div Yield", "Yield TTM"}: return score_middle_better(val, 2.0, 5.0, 0.0, 8.0)
    if col == "Payout Ratio": return score_middle_better(val, 20.0, 40.0, 0.0, 80.0)
    if col == "Market Cap": return score_higher_better(val, 2_000_000_000, 10_000_000_000)
    if col == "P/E FWD": return score_lower_better_positive(val, 10.0, 35.0)
    if col == "Price / Sales": return score_lower_better(val, 1.0, 8.0)
    if col == "EV / EBITDA": return score_lower_better_positive(val, 8.0, 25.0)
    if col == "Price / Book": return score_lower_better(val, 1.0, 5.0)
    if col == "Altman Z Score": return score_higher_better(val, 1.8, 3.0)
    if col == "EPS YoY": return score_higher_better(val, 0.0, 25.0)
    if col == "EPS Growth (FWD)": return score_higher_better(val, 0.0, 20.0)
    if col == "Revenue YoY": return score_higher_better(val, 0.0, 20.0)
    if col == "Revenue FWD": return score_higher_better(val, 0.0, 15.0)
    if col == "EPS Surprise": return score_higher_better(val, 0.0, 10.0)
    if col == "Revenue Surprise": return score_higher_better(val, 0.0, 5.0)
    return 50.0

def grade_from_score(score):
    for cutoff, grade in GRADE_BANDS:
        if score >= cutoff:
            return grade
    return "D-"

def decision_from_grade(grade):
    if grade.startswith("A"): return "Interday"
    if grade.startswith("B"): return "Gray Zone"
    return "Intraday Only"

def stock_style_from_dividends(row):
    y = parse_numeric(row.get("Yield TTM"))
    return "Value Stock" if y is not None and y > 0 else "Growth Stock"

def warning_messages(row):
    msgs = []
    upcoming = parse_date(row.get("Upcoming Announce Date"))
    previous = parse_date(row.get("Last Quarter Announce Date"))
    if pd.notna(upcoming):
        days_to = (upcoming.normalize() - TODAY).days
        if 0 <= days_to <= 10:
            msgs.append(("warning", f"Upcoming earnings in {days_to} day(s): {upcoming.strftime('%Y-%m-%d')}"))
        else:
            msgs.append(("info", f"Next earnings date: {upcoming.strftime('%Y-%m-%d')}"))
    if pd.notna(previous):
        days_since = (TODAY - previous.normalize()).days
        if 0 <= days_since <= 10:
            msgs.append(("warning", f"Previous earnings were {days_since} day(s) ago: {previous.strftime('%Y-%m-%d')}"))
        else:
            msgs.append(("info", f"Previous earnings date: {previous.strftime('%Y-%m-%d')}"))
    return msgs

# ── Data loader ────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(CSV_FILE)
    for col in ["Upcoming Announce Date", "Last Quarter Announce Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

# ── Scoring engine ─────────────────────────────────────────────────────────
def build_stock_result(row, df):
    section_scores = {}
    section_breakdowns = {}
    overall = 0.0
    for section, metrics in METRIC_WEIGHTS.items():
        weighted_points = 0.0
        breakdown = []
        for col, weight in metrics.items():
            raw = row.get(col)
            metric_score = score_metric(col, raw, df)
            weighted_points += (metric_score * weight / 100.0)
            breakdown.append({
                "metric": col,
                "raw": raw,
                "score": round(metric_score, 2),
                "weight": weight,
                "contribution": round(metric_score * weight / 100.0, 2),
            })
        section_score = round(weighted_points / SECTION_WEIGHTS[section] * 100.0, 2)
        section_scores[section] = section_score
        section_breakdowns[section] = breakdown
        overall += weighted_points
    overall = round(overall, 2)
    grade = grade_from_score(overall)
    decision = decision_from_grade(grade)
    stock_style = stock_style_from_dividends(row)
    return {
        "symbol": row["Symbol"],
        "section_scores": section_scores,
        "section_breakdowns": section_breakdowns,
        "overall_score": overall,
        "grade": grade,
        "decision": decision,
        "stock_style": stock_style,
        "warnings": warning_messages(row),
        # Raw analyst scores for display
        "sa_rating_raw": row.get("SA Analyst Ratings"),
        "ws_rating_raw": row.get("Wall Street Ratings"),
        "quant_rating_raw": row.get("Quant Rating"),
    }

# ── Charts (same as Pandora Universe) ─────────────────────────────────────
def make_section_chart(results):
    categories = list(SECTION_WEIGHTS.keys())
    fig = go.Figure()
    for item in results:
        fig.add_trace(go.Bar(
            name=item["symbol"],
            x=categories,
            y=[item["section_scores"][c] for c in categories],
            text=[f"{item['section_scores'][c]:.1f}" for c in categories],
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>Score: %{y:.2f}<extra></extra>",
        ))
    fig.update_layout(
        title="Section Comparison",
        barmode="group",
        yaxis=dict(range=[0, 100], title="Section Score"),
        xaxis_title="Sections",
        height=460,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig

def make_single_stock_section_chart(result):
    sections = list(SECTION_WEIGHTS.keys())
    fig = go.Figure(go.Bar(
        x=sections,
        y=[result["section_scores"][s] for s in sections],
        text=[f"{result['section_scores'][s]:.1f}" for s in sections],
        textposition="auto",
        marker=dict(color=["#0f766e", "#14b8a6", "#0891b2", "#f59e0b"]),
        hovertemplate="<b>%{x}</b><br>Section score: %{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Section Scores - {result['symbol']}",
        yaxis=dict(range=[0, 100]),
        height=420,
    )
    return fig

# ── Full Universe dialog (enhanced with analyst ratings + sort) ────────────
def build_full_universe_dialog_df(df):
    all_results = [build_stock_result(row, df) for _, row in df.iterrows()]
    rows = []
    for r in all_results:
        rows.append({
            "Symbol": r["symbol"],
            "Stock Style": r["stock_style"],
            "Letter Grade": r["grade"],
            "Overall Score": r["overall_score"],
            "Decision": r["decision"],
            # Analyst labels
            "SA Analyst": numeric_to_analyst_label(r["sa_rating_raw"]),
            "Wall Street": numeric_to_analyst_label(r["ws_rating_raw"]),
            "Quant": numeric_to_analyst_label(r["quant_rating_raw"]),
            # Raw numeric for sorting
            "_sa_raw": parse_numeric(r["sa_rating_raw"]) or 0,
            "_ws_raw": parse_numeric(r["ws_rating_raw"]) or 0,
            "_quant_raw": parse_numeric(r["quant_rating_raw"]) or 0,
        })
    dialog_df = pd.DataFrame(rows)
    if dialog_df.empty:
        return dialog_df
    dialog_df["Letter Grade"] = pd.Categorical(
        dialog_df["Letter Grade"], categories=GRADE_ORDER, ordered=True
    )
    return dialog_df

@st.dialog("Analyst Rating × Letter Grade Matrix", width="large")
def show_analyst_matrix_dialog(dialog_df):
    """
    Para cada analista muestra una tabla:
    Filas = Rating del analista (Strong Buy → Strong Sell)
    Columnas = Letter Grade (A+ → D-)
    Celdas = número de acciones
    """
    RATING_ROWS = ["Strong Buy", "Buy", "Neutral", "Sell", "Strong Sell", "N/A"]

    analyst_cols = {
        "SA Analyst":   "SA Analyst",
        "Wall Street":  "Wall Street",
        "Quant":        "Quant",
    }

    for analyst_name, col in analyst_cols.items():
        st.markdown(f"### {analyst_name}")

        # Construir la matriz
        matrix_data = {}
        for rating in RATING_ROWS:
            row_stocks = dialog_df[dialog_df[col] == rating]
            counts = row_stocks["Letter Grade"].value_counts()
            matrix_data[rating] = {grade: int(counts.get(grade, 0)) for grade in GRADE_ORDER}

        matrix_df = pd.DataFrame(matrix_data, index=GRADE_ORDER).T
        matrix_df.index.name = f"{analyst_name} Rating ↓  /  Letter Grade →"

        # Total por fila
        matrix_df["TOTAL"] = matrix_df.sum(axis=1)

        # Quitar filas vacías (rating sin ninguna acción)
        matrix_df = matrix_df[matrix_df["TOTAL"] > 0]

        if matrix_df.empty:
            st.info(f"No data available for {analyst_name}.")
            continue

        # Resaltar celdas con valor > 0 usando color de fondo suave
        def highlight_cells(val):
            if isinstance(val, int) and val > 0:
                return "background-color: #ccfbf1; font-weight: 600; color: #0f766e;"
            return "color: #cbd5e1;"

        styled = (
            matrix_df.style
            .applymap(highlight_cells)
            .format(lambda x: str(x) if isinstance(x, int) else x)
        )

        st.dataframe(styled, use_container_width=True)
        st.markdown("---")
        
@st.dialog("SP500 Test Universe – Grade Summary", width="large")
def show_full_universe_dialog(dialog_df):
    # ── Sort selector ──────────────────────────────────────────────────────
    sort_by = st.radio(
        "Sort by analyst rating",
        ["SA Analyst", "Wall Street", "Quant"],
        horizontal=True,
        key="dialog_sort_analyst",
    )

    raw_col_map = {
        "SA Analyst": "_sa_raw",
        "Wall Street": "_ws_raw",
        "Quant": "_quant_raw",
    }
    sort_raw_col = raw_col_map[sort_by]

    # Analyst rating display order: Strong Buy first → Strong Sell last
    ANALYST_ORDER_MAP = {
        "Strong Buy": 0,
        "Buy": 1,
        "Neutral": 2,
        "Sell": 3,
        "Strong Sell": 4,
        "N/A": 5,
    }

    display_cols = ["Symbol", "Letter Grade", "Overall Score", "Decision",
                    "SA Analyst", "Wall Street", "Quant"]

    for style_label in ["Growth Stock", "Value Stock"]:
        subset = dialog_df[dialog_df["Stock Style"] == style_label].copy()

        st.markdown(f"### {'📈' if style_label == 'Growth Stock' else '💰'} {style_label}s")

        if subset.empty:
            st.info(f"No {style_label.lower()}s found.")
            continue

        # Sort: chosen analyst rating desc (Strong Buy first), then Overall Score desc
        subset["_analyst_order"] = subset[sort_by].map(ANALYST_ORDER_MAP).fillna(5)
        subset = subset.sort_values(
            ["_analyst_order", "Overall Score"],
            ascending=[True, False],
        ).reset_index(drop=True)

        # Render with colored analyst label chips
        st.dataframe(
            subset[display_cols],
            use_container_width=True,
            hide_index=True,
            height=min(400, 35 + len(subset) * 35),
            column_config={
                "SA Analyst": st.column_config.TextColumn("SA Analyst"),
                "Wall Street": st.column_config.TextColumn("Wall St."),
                "Quant": st.column_config.TextColumn("Quant"),
                "Overall Score": st.column_config.NumberColumn("Score", format="%.1f"),
                "Letter Grade": st.column_config.TextColumn("Grade"),
            },
        )

# ── Main UI ────────────────────────────────────────────────────────────────
st.title("🧪 Admin Test – SP500 Universe")
st.markdown("Same scoring framework as Pandora Universe, applied to the SP500 test dataset.")

try:
    df = load_data()
except Exception as e:
    st.error(f"Unable to load {CSV_FILE}: {e}")
    st.stop()

if df.empty or "Symbol" not in df.columns:
    st.warning("No valid data found in SP500_TEST.csv.")
    st.stop()

# ── Full universe button ───────────────────────────────────────────────────
full_dialog_df = build_full_universe_dialog_df(df)

if st.button("📊 View Full Universe Letter Grades"):
    show_full_universe_dialog(full_dialog_df)

# ── NUEVO BOTÓN ────────────────────────────────────────────────────────────
if st.button("🔬 Analyst Rating × Grade Matrix"):
    show_analyst_matrix_dialog(full_dialog_df)
    
# ── Stock selector ─────────────────────────────────────────────────────────
options = df["Symbol"].dropna().astype(str).sort_values().unique().tolist()
selected = st.multiselect(
    "Select one or more stocks",
    options,
    placeholder="Example: AAPL, MSFT, AMZN...",
)

if not selected:
    st.info("Select one or more stocks to start the analysis.")
    st.stop()

selected_df = df[df["Symbol"].astype(str).isin(selected)].copy()
results = [build_stock_result(row, df) for _, row in selected_df.iterrows()]

# ── Multi-stock comparison ─────────────────────────────────────────────────
if len(results) > 1:
    st.plotly_chart(make_section_chart(results), use_container_width=True)
    comp_df = pd.DataFrame([
        {
            "Symbol": r["symbol"],
            "Overall Score": r["overall_score"],
            "Grade": r["grade"],
            "Decision": r["decision"],
            "Stock Style": r["stock_style"],
            "SA Analyst": numeric_to_analyst_label(r["sa_rating_raw"]),
            "Wall Street": numeric_to_analyst_label(r["ws_rating_raw"]),
            "Quant": numeric_to_analyst_label(r["quant_rating_raw"]),
            **r["section_scores"],
        }
        for r in results
    ]).sort_values("Overall Score", ascending=False)
    st.dataframe(comp_df, use_container_width=True, hide_index=True)
    st.markdown("---")

# ── Individual stock detail ────────────────────────────────────────────────
for result in results:
    row = selected_df[selected_df["Symbol"].astype(str) == result["symbol"]].iloc[0]
    with st.expander(f"{result['symbol']} Analysis", expanded=True):
        # Score cards row
        c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1.1])
        with c1:
            st.markdown(
                f"<div class='score-card'>"
                f"<div style='font-size:3rem;font-weight:700'>{result['overall_score']:.1f}</div>"
                f"<div>Overall Score</div></div>",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"<div class='score-card'>"
                f"<div style='font-size:3rem;font-weight:700'>{result['grade']}</div>"
                f"<div>Letter Grade</div></div>",
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"<div class='score-card'>"
                f"<div style='font-size:2.3rem;font-weight:700'>{result['decision']}</div>"
                f"<div>Classification</div></div>",
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"<div class='score-card'>"
                f"<div style='font-size:2.2rem;font-weight:700'>{result['stock_style']}</div>"
                f"<div>Stock Style</div></div>",
                unsafe_allow_html=True,
            )

        # Analyst ratings row
        st.markdown("#### Analyst Ratings")
        a1, a2, a3 = st.columns(3)
        for col_widget, label, raw_val in [
            (a1, "SA Analyst", result["sa_rating_raw"]),
            (a2, "Wall Street", result["ws_rating_raw"]),
            (a3, "Quant", result["quant_rating_raw"]),
        ]:
            rating_label = numeric_to_analyst_label(raw_val)
            chip_color = ANALYST_LABEL_COLORS[rating_label]
            raw_display = f"{parse_numeric(raw_val):.2f}" if parse_numeric(raw_val) is not None else "N/A"
            with col_widget:
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<div class='subtle'>{label}</div>"
                    f"<span class='rating-chip' style='background:{chip_color}'>{rating_label}</span>"
                    f"<div class='subtle' style='margin-top:4px'>({raw_display})</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("")  # spacing

        # Warnings
        for box_type, msg in result["warnings"]:
            klass = "warning-box" if box_type == "warning" else "info-box"
            st.markdown(f"<div class='{klass}'>{msg}</div>", unsafe_allow_html=True)

        # Section chart
        st.plotly_chart(make_single_stock_section_chart(result), use_container_width=True)

        # Section metrics
        sec_cols = st.columns(4)
        for idx, section in enumerate(SECTION_WEIGHTS.keys()):
            with sec_cols[idx]:
                st.metric(section, f"{result['section_scores'][section]:.1f}")

        # Detailed breakdown
        st.markdown("### Section Breakdown")
        for section in SECTION_WEIGHTS.keys():
            breakdown_df = pd.DataFrame(result["section_breakdowns"][section])
            st.markdown(f"#### {section}")
            st.dataframe(
                breakdown_df.rename(columns={
                    "metric": "Metric",
                    "raw": "Raw Value",
                    "score": "Metric Score",
                    "weight": "Weight %",
                    "contribution": "Contribution",
                }),
                use_container_width=True,
                hide_index=True,
            )
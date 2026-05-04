import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

CSV_FILE = "Pandora_Universe.csv"
TODAY = pd.Timestamp.today().normalize()

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
    "A+": 100,
    "A":  85,
    "A-": 75,
    "B+": 65,
    "B":  55,
    "C":  45,
    "D":  20,
}

GRADE_BANDS = [
    (90, "A+"),
    (80, "A"),
    (70, "A-"),
    (60, "B+"),
    (50, "B"),
    (40, "C"),
    (0,  "D"),
]

GRADE_ORDER = ["A+", "A", "A-", "B+", "B", "C", "D"]

ANALYST_RATING_ORDER = ["Strong Buy", "Buy", "Neutral", "Sell", "Strong Sell", "N/A"]

ANALYST_LABEL_COLORS = {
    "Strong Buy":  "#16a34a",
    "Buy":         "#4ade80",
    "Neutral":     "#94a3b8",
    "Sell":        "#f97316",
    "Strong Sell": "#dc2626",
    "N/A":         "#cbd5e1",
}

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Pandora Universe", page_icon="📈", layout="wide")

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

# ── Helpers ────────────────────────────────────────────────────────────────
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
    return "D"

def decision_from_grade(grade):
    if grade in {"A+", "A", "A-"}:
        return "Interday"
    if grade in {"B+", "B"}:
        return "Gray Zone"
    return "Intraday Only"

def stock_style_from_dividends(row):
    y = parse_numeric(row.get("Yield TTM"))
    return "Value Stock" if y is not None and y > 0 else "Growth Stock"

def numeric_to_analyst_label(val) -> str:
    try:
        v = float(str(val).strip().replace(",", ""))
    except (ValueError, TypeError):
        return "N/A"
    if v >= 4.5: return "Strong Buy"
    if v >= 3.5: return "Buy"
    if v >= 2.5: return "Neutral"
    if v >= 1.5: return "Sell"
    return "Strong Sell"

def analyst_consensus_score(row) -> float | None:
    sources = [
        (row.get("SA Analyst Ratings"),  0.50),
        (row.get("Wall Street Ratings"), 0.50),
    ]
    total_weight = 0.0
    weighted_sum = 0.0
    for val, weight in sources:
        x = parse_numeric(val)
        if x is not None and 1.0 <= x <= 5.0:
            weighted_sum += x * weight
            total_weight += weight
    if total_weight == 0:
        return None
    return weighted_sum / total_weight

def consensus_card_style(consensus: float | None, decision: str) -> tuple[str, str]:
    if consensus is None:
        return "linear-gradient(135deg, #64748b, #94a3b8)", "No Analyst Data"
    if consensus >= 4.5:   label = "Strong Buy"
    elif consensus >= 3.5: label = "Buy"
    elif consensus >= 2.5: label = "Neutral"
    elif consensus >= 1.5: label = "Sell"
    else:                  label = "Strong Sell"

    if decision == "Intraday Only":
        normalized = max(0.0, min(1.0, (consensus - 2.5) / 2.5))
        if normalized >= 0.80:   bg = "linear-gradient(135deg, #15803d, #22c55e)"
        elif normalized >= 0.60: bg = "linear-gradient(135deg, #16a34a, #4ade80)"
        elif normalized >= 0.40: bg = "linear-gradient(135deg, #ca8a04, #facc15)"
        elif normalized >= 0.20: bg = "linear-gradient(135deg, #ea580c, #fb923c)"
        else:                    bg = "linear-gradient(135deg, #dc2626, #f87171)"
        return bg, label

    if consensus >= 4.5:   return "linear-gradient(135deg, #15803d, #22c55e)", label
    if consensus >= 3.5:   return "linear-gradient(135deg, #16a34a, #4ade80)", label
    if consensus >= 2.5:   return "linear-gradient(135deg, #ca8a04, #facc15)", label
    if consensus >= 1.5:   return "linear-gradient(135deg, #ea580c, #fb923c)", label
    return "linear-gradient(135deg, #dc2626, #f87171)", label

def warning_messages(row):
    msgs = []
    upcoming = parse_date(row.get("Upcoming Announce Date"))
    previous = parse_date(row.get("Last Quarter Announce Date"))

    if pd.notna(upcoming):
        days_to = (upcoming.normalize() - TODAY).days
        if 0 <= days_to <= 3:
            msgs.append(("critical", f"⚠️ Earnings in {days_to} day(s) — high volatility imminent: {upcoming.strftime('%Y-%m-%d')}"))
        elif 0 <= days_to <= 7:
            msgs.append(("warning", f"📅 Earnings in {days_to} days — monitor position closely: {upcoming.strftime('%Y-%m-%d')}"))
        elif 0 <= days_to <= 10:
            msgs.append(("mild", f"📅 Earnings approaching in {days_to} days: {upcoming.strftime('%Y-%m-%d')}"))
        else:
            msgs.append(("info", f"Next earnings date: {upcoming.strftime('%Y-%m-%d')}"))

    if pd.notna(previous):
        days_since = (TODAY - previous.normalize()).days
        if 0 <= days_since <= 10:
            msgs.append(("warning", f"Previous earnings were {days_since} day(s) ago: {previous.strftime('%Y-%m-%d')}"))
        else:
            msgs.append(("info", f"Previous earnings date: {previous.strftime('%Y-%m-%d')}"))

    eps_fwd = parse_numeric(row.get("EPS Growth (FWD)"))
    if eps_fwd is not None and eps_fwd < 0:
        msgs.append(("critical", "📉 Next earnings estimate is negative — expected EPS decline ahead"))

    eps_surprise = parse_numeric(row.get("EPS Surprise"))
    if eps_surprise is not None and eps_surprise < 0:
        msgs.append(("critical", "❌ Last quarter missed expectations — earnings came in below estimates"))

    rev_fwd = parse_numeric(row.get("Revenue FWD"))
    if rev_fwd is not None and rev_fwd < 0:
        msgs.append(("critical", "📉 Forward revenue is projected to decline next quarter"))

    profit_margin = parse_numeric(row.get("Profit Margin"))
    if profit_margin is not None and profit_margin < 0:
        msgs.append(("critical", "🚨 Company is currently operating at a loss"))

    pe_fwd = parse_numeric(row.get("P/E FWD"))
    if pe_fwd is not None and pe_fwd > 0:
        if pe_fwd > 100:
            msgs.append(("warning", "🔺 Extremely overvalued — stock is trading at a speculative premium"))
        elif pe_fwd > 50:
            msgs.append(("warning", "⚠️ Stock appears overvalued — elevated valuation increases correction risk"))

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
        "consensus_score": analyst_consensus_score(row),
        "sa_rating_raw": row.get("SA Analyst Ratings"),
        "ws_rating_raw": row.get("Wall Street Ratings"),
        "quant_rating_raw": row.get("Quant Rating"),
    }

# ── Charts ─────────────────────────────────────────────────────────────────
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
        customdata=sections,
        hovertemplate="<b>%{x}</b><br>Section score: %{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Section Scores - {result['symbol']}",
        yaxis=dict(range=[0, 100]),
        height=420,
    )
    return fig

# ── Full universe dialog ───────────────────────────────────────────────────
def build_full_universe_grade_dialog_df(df):
    all_results = [build_stock_result(row, df) for _, row in df.iterrows()]
    dialog_df = pd.DataFrame([
        {
            "Symbol": r["symbol"],
            "Stock Style": r["stock_style"],
            "Letter Grade": r["grade"],
            "Overall Score": r["overall_score"],
        }
        for r in all_results
    ])
    if dialog_df.empty:
        return dialog_df
    dialog_df["Letter Grade"] = pd.Categorical(
        dialog_df["Letter Grade"], categories=GRADE_ORDER, ordered=True
    )
    dialog_df = dialog_df.sort_values(
        ["Stock Style", "Letter Grade", "Overall Score", "Symbol"],
        ascending=[True, True, False, True]
    ).reset_index(drop=True)
    return dialog_df

@st.dialog("Pandora Universe Grade Summary", width="large")
def show_full_universe_grade_dialog(dialog_df):
    growth_df = dialog_df[dialog_df["Stock Style"] == "Growth Stock"].copy()
    value_df  = dialog_df[dialog_df["Stock Style"] == "Value Stock"].copy()
    st.markdown("### Growth Stocks")
    if growth_df.empty:
        st.info("No growth stocks found.")
    else:
        st.dataframe(growth_df[["Symbol", "Letter Grade", "Overall Score"]],
                     use_container_width=True, hide_index=True, height=400)
    st.markdown("### Value Stocks")
    if value_df.empty:
        st.info("No value stocks found.")
    else:
        st.dataframe(value_df[["Symbol", "Letter Grade", "Overall Score"]],
                     use_container_width=True, hide_index=True, height=400)

# ── Analyst matrix ─────────────────────────────────────────────────────────
def build_analyst_matrix_df(df: pd.DataFrame) -> pd.DataFrame:
    all_results = [build_stock_result(row, df) for _, row in df.iterrows()]
    rows = []
    for r in all_results:
        raw_row = df[df["Symbol"].astype(str) == r["symbol"]].iloc[0]
        rows.append({
            "Symbol":        r["symbol"],
            "Letter Grade":  r["grade"],
            "Overall Score": r["overall_score"],
            "SA Analyst":    numeric_to_analyst_label(raw_row.get("SA Analyst Ratings")),
            "Wall Street":   numeric_to_analyst_label(raw_row.get("Wall Street Ratings")),
            "Quant":         numeric_to_analyst_label(raw_row.get("Quant Rating")),
        })
    result_df = pd.DataFrame(rows)
    if result_df.empty:
        return result_df
    result_df["Letter Grade"] = pd.Categorical(
        result_df["Letter Grade"], categories=GRADE_ORDER, ordered=True
    )
    return result_df

@st.dialog("Pandora Universe – Analyst Rating × Letter Grade Matrix", width="large")
def show_analyst_matrix_dialog_pandora(matrix_df: pd.DataFrame):
    RATING_ROWS = ["Strong Buy", "Buy", "Neutral", "Sell", "Strong Sell", "N/A"]
    analyst_cols = {
        "SA Analyst":  "SA Analyst",
        "Wall Street": "Wall Street",
        "Quant":       "Quant",
    }
    for analyst_name, col in analyst_cols.items():
        st.markdown(f"### {analyst_name}")
        matrix_data = {}
        for rating in RATING_ROWS:
            row_stocks = matrix_df[matrix_df[col] == rating]
            counts = row_stocks["Letter Grade"].value_counts()
            matrix_data[rating] = {grade: int(counts.get(grade, 0)) for grade in GRADE_ORDER}
        matrix_df_display = pd.DataFrame(matrix_data, index=GRADE_ORDER).T
        matrix_df_display.index.name = f"{analyst_name} Rating ↓  /  Letter Grade →"
        matrix_df_display["TOTAL"] = matrix_df_display.sum(axis=1)
        matrix_df_display = matrix_df_display[matrix_df_display["TOTAL"] > 0]
        if matrix_df_display.empty:
            st.info(f"No data available for {analyst_name}.")
            st.markdown("---")
            continue

        def highlight_cells(val):
            if isinstance(val, int) and val > 0:
                return "background-color: #ccfbf1; font-weight: 600; color: #0f766e;"
            return "color: #cbd5e1;"

        styled = (
            matrix_df_display.style
            .map(highlight_cells)
            .format(lambda x: str(x) if isinstance(x, int) else x)
        )
        st.dataframe(styled, use_container_width=True)

        with st.expander(f"🔍 See symbols for a specific cell — {analyst_name}"):
            dd_col1, dd_col2 = st.columns(2)
            with dd_col1:
                selected_rating = st.selectbox(
                    "Analyst Rating",
                    [r for r in RATING_ROWS if r in matrix_df_display.index],
                    key=f"pandora_rating_{analyst_name}",
                )
            with dd_col2:
                selected_grade = st.selectbox(
                    "Letter Grade",
                    GRADE_ORDER,
                    key=f"pandora_grade_{analyst_name}",
                )
            matches = matrix_df[
                (matrix_df[col] == selected_rating) &
                (matrix_df["Letter Grade"] == selected_grade)
            ]["Symbol"].sort_values().tolist()
            if matches:
                count = len(matches)
                st.markdown(
                    f"**{count} stock{'s' if count > 1 else ''} with "
                    f"{analyst_name} = {selected_rating} and Grade = {selected_grade}:**"
                )
                chips_html = " ".join(
                    f"<span style='display:inline-block; background:#ccfbf1; color:#0f766e; "
                    f"font-weight:700; padding:3px 10px; border-radius:999px; "
                    f"margin:3px; font-size:0.9rem;'>{sym}</span>"
                    for sym in matches
                )
                st.markdown(chips_html, unsafe_allow_html=True)
            else:
                st.info(f"No stocks found with {analyst_name} = {selected_rating} and Grade = {selected_grade}.")
        st.markdown("---")

# ── Main UI ────────────────────────────────────────────────────────────────
st.title("📈 Pandora Universe")
st.markdown("Fundamental scoring framework for classifying stocks as Interday, Gray Zone, or Intraday Only.")

with st.expander("📊 Scoring Scale Reference", expanded=False):
    scale_data = {
        "Grade": ["A+", "A", "A-", "B+", "B", "C", "D"],
        "Score Range": ["90 – 100", "80 – 89", "70 – 79", "60 – 69", "50 – 59", "40 – 49", "0 – 39"],
        "Classification": [
            "Interday", "Interday", "Interday",
            "Gray Zone", "Gray Zone",
            "Intraday Only", "Intraday Only"
        ],
    }
    scale_df = pd.DataFrame(scale_data)

    def color_classification(val):
        if val == "Interday":
            return "background-color: #d1fae5; color: #065f46; font-weight: 700;"
        if val == "Gray Zone":
            return "background-color: #dbeafe; color: #1e3a8a; font-weight: 700;"
        return "background-color: #fee2e2; color: #7f1d1d; font-weight: 700;"

    def color_grade(val):
        colors = {
            "A+": "#065f46", "A": "#047857", "A-": "#059669",
            "B+": "#1d4ed8", "B": "#2563eb",
            "C": "#b45309",
            "D": "#b91c1c",
        }
        c = colors.get(val, "#374151")
        return f"color: {c}; font-weight: 800; font-size: 1rem;"

    styled_scale = (
        scale_df.style
        .map(color_classification, subset=["Classification"])
        .map(color_grade, subset=["Grade"])
    )

    st.dataframe(styled_scale, use_container_width=True, hide_index=True)
    
try:
    df = load_data()
except Exception as e:
    st.error(f"Unable to load {CSV_FILE}: {e}")
    st.stop()

if df.empty or "Symbol" not in df.columns:
    st.warning("No valid Pandora Universe data was found.")
    st.stop()

full_universe_dialog_df = build_full_universe_grade_dialog_df(df)
analyst_matrix_df = build_analyst_matrix_df(df)

if st.button("View Full Universe Letter Grades"):
    show_full_universe_grade_dialog(full_universe_dialog_df)

if st.button("🔬 Analyst Rating × Grade Matrix"):
    show_analyst_matrix_dialog_pandora(analyst_matrix_df)

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

for result in results:
    row = selected_df[selected_df["Symbol"].astype(str) == result["symbol"]].iloc[0]
    with st.expander(f"{result['symbol']} Analysis", expanded=True):

        consensus_bg, consensus_label = consensus_card_style(result["consensus_score"], result["decision"])
        score_display = f"{result['consensus_score']:.2f}" if result["consensus_score"] is not None else "N/A"

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
                f"<div style='padding:1rem; border-radius:1rem; background:{consensus_bg}; "
                f"color:white; text-align:center; margin-bottom:0.8rem;'>"
                f"<div style='font-size:1.6rem;font-weight:700'>{consensus_label}</div>"
                f"<div style='font-size:0.85rem;opacity:0.85'>Analyst Consensus ({score_display})</div>"
                f"<div style='font-size:0.8rem;opacity:0.75;margin-top:2px'>{result['stock_style']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

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

        st.markdown("")

        for box_type, msg in result["warnings"]:
            if box_type == "critical":
                st.markdown(
                    f"<div style='padding:0.85rem 1rem; border-radius:0.75rem; margin-bottom:0.6rem; "
                    f"border-left:6px solid #dc2626; background:#fef2f2; color:#7f1d1d;'>{msg}</div>",
                    unsafe_allow_html=True,
                )
            elif box_type == "warning":
                st.markdown(
                    f"<div style='padding:0.85rem 1rem; border-radius:0.75rem; margin-bottom:0.6rem; "
                    f"border-left:6px solid #f59e0b; background:#fffbeb; color:#92400e;'>{msg}</div>",
                    unsafe_allow_html=True,
                )
            elif box_type == "mild":
                st.markdown(
                    f"<div style='padding:0.85rem 1rem; border-radius:0.75rem; margin-bottom:0.6rem; "
                    f"border-left:6px solid #facc15; background:#fefce8; color:#713f12;'>{msg}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"<div class='info-box'>{msg}</div>", unsafe_allow_html=True)

        st.plotly_chart(make_single_stock_section_chart(result), use_container_width=True)

        sec_cols = st.columns(4)
        for idx, section in enumerate(SECTION_WEIGHTS.keys()):
            with sec_cols[idx]:
                st.metric(section, f"{result['section_scores'][section]:.1f}")

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
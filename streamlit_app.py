import streamlit as st
import pandas as pd

# ===================================
# App Configuration
# ===================================
st.set_page_config(page_title="Daily Snapshot", layout="wide")
st.title("Daily Snapshot")

CSV_URLS = {
    "daily": "https://raw.githubusercontent.com/sanglocn/us_daily/main/data/us_snapshot_ohlcv_daily.csv",
    "weekly": "https://raw.githubusercontent.com/sanglocn/us_daily/main/data/us_snapshot_ohlcv_weekly.csv",
}

GROUP_ORDER = ["Market", "Sector", "Commodity", "Crypto", "Country", "Theme", "Leader"]

DISPLAY_ORDER = [
    "Ticker", "RS Trend", "RS 1M", "RS 1Y", "Volume",
    "Intraday", "1D Return", "Extension",
    "> SMA10", "> SMA20", "Stage"
]

COLUMN_RENAME = {
    "ticker": "Ticker",
    "ret_intraday": "Intraday",
    "ret_1d": "1D Return",
    "rs_rank_21d": "RS 1M",
    "rs_rank_252d": "RS 1Y",
    "pp_volume": "Volume",
    "ratio_pct_dist_to_atr_pct": "Extension",
    "above_sma10": "> SMA10",
    "above_sma20": "> SMA20",
    "stage_label_core": "Stage",
    "group": "group",
}

# ===================================
# Data Loading & Processing
# ===================================
@st.cache_data(ttl=3600)
def load_and_process_data():
    df_daily = pd.read_csv(CSV_URLS["daily"])
    df_weekly = pd.read_csv(CSV_URLS["weekly"])

    df_daily["date"] = pd.to_datetime(df_daily["date"])
    df_weekly["date"] = pd.to_datetime(df_weekly["date"])

    df_sparkline = (
        df_daily.sort_values("date")
        .groupby("ticker")["rs_to_spy"]
        .apply(list)
        .reset_index(name="RS Trend")
    )

    df_latest = df_daily.sort_values("date").groupby("ticker").last().reset_index()
    df_stage = df_weekly.sort_values("date").groupby("ticker")["stage_label_core"].last().reset_index()

    df = df_sparkline.merge(df_latest, on="ticker", how="left")
    df = df.merge(df_stage, on="ticker", how="left")

    df = df.rename(columns=COLUMN_RENAME)
    available_cols = [col for col in DISPLAY_ORDER if col in df.columns]

    return df[available_cols + (["group"] if "group" in df.columns else [])]

df = load_and_process_data()

# ===================================
# Sidebar Filters & Navigation
# ===================================
st.sidebar.header("Filters")
hide_weak_rs_1m = st.sidebar.toggle("Strong RS 1M", value=False, help="Hide all tickers with RS Rank (1M) below 85%")
hide_weak_rs_1y = st.sidebar.toggle("Strong RS 1Y", value=False, help="Hide all tickers with RS Rank (1Y) below 85%")
limit_extension = st.sidebar.toggle("Low Extension", value=False, help="Hide all tickers with Extension Multiple above 4")
stage_2_only = st.sidebar.toggle("Core Model", value=False, help="Hide all tickers different from Stage 2 in Core Model")

filtered_df = df.copy()
if hide_weak_rs_1m and "RS 1M" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["RS 1M"] >= 0.85]
if hide_weak_rs_1y and "RS 1Y" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["RS 1Y"] >= 0.85]
if limit_extension and "Extension" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Extension"] <= 4]
if stage_2_only and "Stage" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Stage"] == 2]


st.sidebar.header("Navigation")
for group_name in GROUP_ORDER:
    anchor = group_name.lower().replace(" ", "-")
    st.sidebar.markdown(f'<a href="#{anchor}" style="text-decoration:none;">{group_name}</a>', unsafe_allow_html=True)

# ===================================
# Formatting & Styling Functions
# ===================================
def pct(val, decimals=1):
    return f"{val*100:.{decimals}f}%" if pd.notna(val) else ""

def ext(val):
    return f"{val:.1f}" if pd.notna(val) else ""

def stage_emoji(s):
    return {1: "🟡", 2: "🟢", 3: "🟠", 4: "🔴"}.get(s, "⚪") if pd.notna(s) else "⚪"

def volume_icon(v):
    icons = {"Pocket": "💎", "Normal": "⚪"}
    return icons.get(str(v), "⚪") if pd.notna(v) else "⚪"

def checkmark(val):
    if pd.isna(val): return ""
    return "✅" if str(val).lower() in ("true", "1", "1.0", "yes") else "❌"

def style_returns(val):
    if pd.isna(val): return ""
    return "background-color: #d4f4dd; font-weight: bold" if val > 0 else "background-color: #f4d4d4; font-weight: bold"

def style_rs(val):
    if pd.isna(val): return ""
    v = val
    if v >= 0.85: return "background-color: #d4f4dd; font-weight: bold"
    if v >= 0.50: return "background-color: #e0e0e0; font-weight: bold"
    return "background-color: #f4d4d4; font-weight: bold"

def style_extension(val):
    if pd.isna(val): return ""
    v = float(val)
    if v < 0: return "background-color: #e0e0e0; font-weight: bold"
    if v <= 4: return "background-color: #d4f4dd; font-weight: bold"
    if v <= 10: return "background-color: #fff7cc; font-weight: bold"
    return "background-color: #f4d4d4; font-weight: bold"

# ===================================
# Display Tables by Group
# ===================================
column_config = {
    "RS Trend": st.column_config.LineChartColumn("RS", width="small", y_min=0, y_max=20)
} if "RS Trend" in df.columns else {}

for group_name in GROUP_ORDER:
    group_col = "group" in filtered_df.columns
    mask = filtered_df["group"] == group_name if group_col else True
    group_df = filtered_df[mask].copy()

    if group_df.empty:
        continue

    # Add anchor for navigation
    st.markdown(f'<a id="{group_name.lower().replace(" ", "-")}"></a>', unsafe_allow_html=True)
    st.subheader(group_name)

    display_cols = [c for c in DISPLAY_ORDER if c in group_df.columns]
    disp = group_df[display_cols].copy()

    styled = disp.style.format({
        "Intraday": lambda x: pct(x, 1),
        "1D Return": lambda x: pct(x, 1),
        "RS 1M": lambda x: pct(x, 0),
        "RS 1Y": lambda x: pct(x, 0),
        "Extension": ext,
        "Stage": stage_emoji,
        "Volume": volume_icon,
        "> SMA10": checkmark,
        "> SMA20": checkmark,
    }, na_rep="")

    styled = styled.map(style_returns, subset=pd.IndexSlice[:, ["Intraday", "1D Return"]])
    styled = styled.map(style_rs, subset=pd.IndexSlice[:, ["RS 1M", "RS 1Y"]])
    styled = styled.map(style_extension, subset="Extension")

    st.dataframe(
        styled,
        column_config=column_config,
        use_container_width=True,
        hide_index=True
    )
    st.markdown("---")

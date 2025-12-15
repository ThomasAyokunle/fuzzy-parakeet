import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import urllib.parse

# --------------------------------
# PAGE CONFIG
# --------------------------------
st.set_page_config(
    page_title="Pharmacy Performance Dashboard",
    layout="wide"
)

st.title("Pharmacy Performance Dashboard")
st.caption("Sales & Margin Performance | Google Sheets | 2022–Present")

# --------------------------------
# GOOGLE SHEET CONFIG
# --------------------------------
SHEET_ID = "1x3I_PlOBsVpftrnt_X1h0SHsn9zCu8RTILC13aXkqAs"
SHEET_NAME = "YEARLY_DATA"
encoded_sheet_name = urllib.parse.quote(SHEET_NAME)

CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    f"/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"
)

# --------------------------------
# LOAD DATA
# --------------------------------
@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv(CSV_URL)
    return df

df = load_data()

# --------------------------------
# PREPARE DATA
# --------------------------------
df.columns = df.columns.str.strip()
df["Month"] = pd.to_datetime(df["Month"], errors="coerce")

numeric_cols = [
    "Ext Price", "Qty Sold", "Ext Cost",
    "Markup %", "Margin %", "Total Margin $"
]

for col in numeric_cols:
    df[col] = (
        df[col].astype(str)
        .str.replace(",", "", regex=False)
        .astype(float)
    )

df["Revenue"] = df["Ext Price"]
df["Margin"] = df["Margin %"]
df["Year"] = df["Month"].dt.year
df["Month_Period"] = df["Month"].dt.to_period("M").astype(str)

# --------------------------------
# SIDEBAR FILTERS
# --------------------------------
st.sidebar.header("Filters")

stores = ["All Stores"] + sorted(df["Store"].dropna().unique().tolist())
departments = ["All Departments"] + sorted(df["Department"].dropna().unique().tolist())

selected_store = st.sidebar.selectbox("Store", stores)
selected_department = st.sidebar.selectbox("Department", departments)

min_date = df["Month"].min().date()
max_date = df["Month"].max().date()

date_range = st.sidebar.date_input(
    "Select period",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# --------------------------------
# APPLY FILTERS
# --------------------------------
filtered_df = df.copy()

if selected_store != "All Stores":
    filtered_df = filtered_df[filtered_df["Store"] == selected_store]

if selected_department != "All Departments":
    filtered_df = filtered_df[filtered_df["Department"] == selected_department]

if isinstance(date_range, tuple) and len(date_range) == 2:
    filtered_df = filtered_df[
        (filtered_df["Month"].dt.date >= date_range[0]) &
        (filtered_df["Month"].dt.date <= date_range[1])
    ]

# --------------------------------
# KPI CALCULATIONS
# --------------------------------
def calculate_kpis(df):
    revenue = df["Revenue"].sum()
    gross_profit = df["Total Margin $"].sum()
    margin_pct = (gross_profit / revenue) * 100 if revenue > 0 else 0
    footfall = len(df)
    avg_basket = revenue / footfall if footfall > 0 else 0
    return revenue, gross_profit, margin_pct, footfall, avg_basket

rev, gp, margin, footfall, basket = calculate_kpis(filtered_df)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Revenue", f"₦{rev:,.0f}")
col2.metric("Gross Profit", f"₦{gp:,.0f}")
col3.metric("Gross Margin %", f"{margin:.1f}%")
col4.metric("Footfall", f"{footfall:,}")
col5.metric("Avg Basket", f"₦{basket:,.0f}")

# --------------------------------
# MONTHLY AGGREGATION
# --------------------------------
monthly = (
    filtered_df
    .groupby("Month_Period", as_index=False)
    .agg(
        Revenue=("Revenue", "sum"),
        Gross_Profit=("Total Margin $", "sum"),
        Margin=("Margin", "mean")
    )
)

# --------------------------------
# SMART ANNOTATION FUNCTION
# --------------------------------
def add_spike_annotations(fig, df, x_col, y_col, label):
    if df.empty or df[y_col].count() < 4:
        return fig

    mean = df[y_col].mean()
    std = df[y_col].std()

    threshold_high = mean + std
    threshold_low = mean - std

    events = df.copy()
    events["z"] = abs((events[y_col] - mean) / std)
    events = events.sort_values("z", ascending=False).head(3)

    for _, r in events.iterrows():
        text = f"{label} spike" if r[y_col] >= threshold_high else f"{label} dip"
        color = "#22c55e" if r[y_col] >= threshold_high else "#ef4444"
        offset = -35 if r[y_col] >= threshold_high else 35

        fig.add_annotation(
            x=r[x_col],
            y=r[y_col],
            text=text,
            showarrow=True,
            ax=0,
            ay=offset,
            arrowhead=2,
            font=dict(size=11, color=color),
            arrowcolor=color,
            bgcolor="rgba(0,0,0,0.4)",
            borderpad=4
        )

    return fig

# --------------------------------
# CHARTS
# --------------------------------
colA, colB = st.columns([1.25, 1])

with colA:
    fig_rev = px.bar(
        monthly,
        x="Month_Period",
        y=["Revenue", "Gross_Profit"],
        barmode="group",
        title="Revenue & Gross Profit Trend"
    )

    fig_rev = add_spike_annotations(fig_rev, monthly, "Month_Period", "Revenue", "Revenue")

    fig_rev.update_layout(
        height=560,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"),
        plot_bgcolor="#1f2937",
        paper_bgcolor="#111827",
        font=dict(color="#e5e7eb"),
        margin=dict(t=100, b=80)
    )

    st.plotly_chart(fig_rev, use_container_width=True)

with colB:
    fig_margin = px.line(
        monthly,
        x="Month_Period",
        y="Margin",
        markers=True,
        title="Gross Margin Trend (%)"
    )

    fig_margin = add_spike_annotations(fig_margin, monthly, "Month_Period", "Margin", "Margin")

    fig_margin.update_layout(
        height=560,
        plot_bgcolor="#1f2937",
        paper_bgcolor="#111827",
        font=dict(color="#e5e7eb"),
        margin=dict(t=100, b=80)
    )

    st.plotly_chart(fig_margin, use_container_width=True)

# --------------------------------
# OPERATIONAL SUMMARY
# --------------------------------
st.subheader("Operational Summary (Auto-generated)")

insights = []

if margin >= 15:
    insights.append("Gross margin remains healthy, indicating good pricing discipline.")
else:
    insights.append("Gross margin pressure observed. Review pricing or supplier costs.")

if basket > filtered_df["Revenue"].mean():
    insights.append("Average basket value suggests effective product mix.")

if footfall > 0:
    insights.append("Transaction volume supports steady customer demand.")

for i in insights:
    st.write("•", i)

# --------------------------------
# DATA VIEW
# --------------------------------
with st.expander("View underlying data"):
    st.dataframe(filtered_df)

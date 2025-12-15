import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
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
GOOGLE_SHEET_ID = "1x3I_PlOBsVpftrnt_X1h0SHsn9zCu8RTILC13aXkqAs"
SHEET_NAME = "YEARLY_DATA"

encoded_sheet_name = urllib.parse.quote(SHEET_NAME)

CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
    f"/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"
)

# --------------------------------
# LOAD DATA
# --------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL)
    df.columns = df.columns.str.strip()

    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")

    numeric_cols = [
        "Ext Price", "Qty Sold", "Ext Cost",
        "Markup %", "Margin %", "Total Margin $"
    ]

    for col in numeric_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .astype(float)
        )

    df["Year"] = df["Month"].dt.year
    df["Revenue"] = df["Ext Price"]

    return df

df = load_data()

# --------------------------------
# SIDEBAR FILTERS
# --------------------------------
st.sidebar.header("Filters")

stores = ["All Stores"] + sorted(df["Store"].dropna().unique().tolist())
departments = ["All Departments"] + sorted(df["Department"].dropna().unique().tolist())

selected_store = st.sidebar.selectbox("Branch", stores)
selected_department = st.sidebar.selectbox("Department", departments)

# --------------------------------
# DATE RANGE + QUICK PRESETS
# --------------------------------
st.sidebar.subheader("Time Period")

min_date = df["Month"].min().date()
max_date = df["Month"].max().date()

preset = st.sidebar.selectbox(
    "Quick range",
    ["Custom", "MTD", "YTD", "Last 6 Months", "Last 12 Months"]
)

today = max_date

if preset == "MTD":
    start_date = today.replace(day=1)
    end_date = today
elif preset == "YTD":
    start_date = today.replace(month=1, day=1)
    end_date = today
elif preset == "Last 6 Months":
    start_date = today - timedelta(days=182)
    end_date = today
elif preset == "Last 12 Months":
    start_date = today - timedelta(days=365)
    end_date = today
else:
    date_selection = st.sidebar.date_input(
        "Select date range",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    if isinstance(date_selection, (list, tuple)) and len(date_selection) == 2:
        start_date, end_date = date_selection
    else:
        start_date = date_selection
        end_date = date_selection

# --------------------------------
# APPLY FILTERS
# --------------------------------
filtered_df = df.copy()

if selected_store != "All Stores":
    filtered_df = filtered_df[filtered_df["Store"] == selected_store]

if selected_department != "All Departments":
    filtered_df = filtered_df[filtered_df["Department"] == selected_department]

filtered_df = filtered_df[
    (filtered_df["Month"].dt.date >= start_date) &
    (filtered_df["Month"].dt.date <= end_date)
]

# --------------------------------
# KPI CALCULATIONS
# --------------------------------
def calculate_kpis(df):
    revenue = df["Revenue"].sum()
    gross_profit = df["Total Margin $"].sum()
    margin_pct = (gross_profit / revenue * 100) if revenue else 0
    footfall = len(df)
    avg_basket = revenue / footfall if footfall else 0

    return revenue, gross_profit, margin_pct, footfall, avg_basket

rev, gp, margin, footfall, basket = calculate_kpis(filtered_df)

# --------------------------------
# KPI DISPLAY
# --------------------------------
c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Revenue", f"₦{rev:,.0f}")
c2.metric("Gross Profit", f"₦{gp:,.0f}")
c3.metric("Gross Margin", f"{margin:.1f}%")
c4.metric("Footfall (Transactions)", f"{footfall:,}")
c5.metric("Avg Basket", f"₦{basket:,.0f}")

# --------------------------------
# CHARTS
# --------------------------------
st.subheader("Performance Trends")

monthly = (
    filtered_df
    .groupby(filtered_df["Month"].dt.to_period("M"))
    .agg(
        Revenue=("Revenue", "sum"),
        Gross_Margin=("Margin %", "mean"),
        Transactions=("Revenue", "count")
    )
    .reset_index()
)

monthly["Month"] = monthly["Month"].astype(str)

fig_rev = px.line(
    monthly,
    x="Month",
    y="Revenue",
    title="Monthly Revenue Trend"
)

fig_margin = px.line(
    monthly,
    x="Month",
    y="Gross_Margin",
    title="Gross Margin Trend (%)"
)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_rev, use_container_width=True)
col2.plotly_chart(fig_margin, use_container_width=True)

# --------------------------------
# TOP CONTRIBUTORS
# --------------------------------
st.subheader("Top Contributors")

top_products = (
    filtered_df
    .groupby("Item Name")["Revenue"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

fig_products = px.bar(
    top_products,
    title="Top 10 Products by Revenue"
)

st.plotly_chart(fig_products, use_container_width=True)

# --------------------------------
# INFLATION DATA (NIGERIA)
# --------------------------------
INFLATION = {
    2022: 22.8,
    2023: 28.2,
    2024: 34.8,
    2025: 22.2
}

# --------------------------------
# OPERATIONAL SUMMARY (RULE-BASED)
# --------------------------------
st.subheader("Operational Summary")

insights = []

current_year = filtered_df["Year"].max()
previous_year = current_year - 1

curr_rev = filtered_df[filtered_df["Year"] == current_year]["Revenue"].sum()
prev_rev = filtered_df[filtered_df["Year"] == previous_year]["Revenue"].sum()

if prev_rev > 0:
    nominal_growth = ((curr_rev - prev_rev) / prev_rev) * 100
    inflation = INFLATION.get(previous_year, 0)
    real_growth = nominal_growth - inflation

    if real_growth >= 0:
        insights.append(f"Real revenue grew {real_growth:.1f}% after inflation adjustment.")
    else:
        insights.append(f"Real revenue declined {abs(real_growth):.1f}% after inflation.")

if basket > 0:
    insights.append("Average basket value indicates pricing and mix performance.")

top_product = top_products.index[0] if len(top_products) else None
if top_product:
    insights.append(f"{top_product} is currently the leading revenue contributor.")

for i in insights[:6]:
    st.write("•", i)

# --------------------------------
# DATA TABLE
# --------------------------------
with st.expander("View underlying data"):
    st.dataframe(filtered_df)

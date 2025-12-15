import streamlit as st
import pandas as pd
import urllib.parse
import plotly.express as px

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

encoded_sheet = urllib.parse.quote(SHEET_NAME)

CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
    f"/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"
)

# --------------------------------
# LOAD DATA
# --------------------------------
@st.cache_data
def load_data():
    return pd.read_csv(CSV_URL)

# --------------------------------
# PREP DATA
# --------------------------------
def prepare_data(df):
    df.columns = df.columns.str.strip()
    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")

    num_cols = [
        "Ext Price", "Qty Sold", "Ext Cost",
        "Markup %", "Margin %", "Total Margin $"
    ]

    for col in num_cols:
        df[col] = (
            df[col].astype(str)
            .str.replace(",", "", regex=False)
            .astype(float)
        )

    df["Year"] = df["Month"].dt.year
    df["Month_Period"] = df["Month"].dt.to_period("M").astype(str)
    df["Revenue"] = df["Ext Price"]

    return df

df = prepare_data(load_data())

# --------------------------------
# SIDEBAR FILTERS
# --------------------------------
st.sidebar.header("Filters")

stores = ["All Stores"] + sorted(df["Store"].dropna().unique())
departments = ["All Departments"] + sorted(df["Department"].dropna().unique())

store = st.sidebar.selectbox("Store", stores)
department = st.sidebar.selectbox("Department", departments)

comparison_type = st.sidebar.radio(
    "Comparison Mode",
    ["Month-over-Month", "Year-over-Year"]
)

st.sidebar.subheader("Time Period")

min_date = df["Month"].min().date()
max_date = df["Month"].max().date()

start_date, end_date = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# --------------------------------
# APPLY FILTERS
# --------------------------------
def apply_filters(df):
    f = df[
        (df["Month"].dt.date >= start_date) &
        (df["Month"].dt.date <= end_date)
    ]

    if store != "All Stores":
        f = f[f["Store"] == store]

    if department != "All Departments":
        f = f[f["Department"] == department]

    return f

filtered_df = apply_filters(df)

# --------------------------------
# KPI CALCULATIONS
# --------------------------------
def calculate_kpis(df):
    revenue = df["Revenue"].sum()
    gross_profit = df["Total Margin $"].sum()
    margin_pct = (gross_profit / revenue) * 100 if revenue else 0
    footfall = len(df)
    avg_basket = revenue / footfall if footfall else 0
    return revenue, gross_profit, margin_pct, footfall, avg_basket

# --------------------------------
# PERIOD SPLIT
# --

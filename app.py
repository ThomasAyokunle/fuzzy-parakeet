import streamlit as st
import pandas as pd
from datetime import datetime
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
    try:
        return pd.read_csv(CSV_URL)
    except Exception as e:
        st.error("Failed to load Google Sheet.")
        st.code(str(e))
        st.stop()

# --------------------------------
# PREPARE DATA
# --------------------------------
def prepare_data(df):
    df.columns = df.columns.str.strip()

    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")

    numeric_cols = [
        "Ext Price",
        "Qty Sold",
        "Ext Cost",
        "Markup %",
        "Margin %",
        "Total Margin $"
    ]

    for col in numeric_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .astype(float)
        )

    df["Year"] = df["Month"].dt.year
    df["Month_Period"] = df["Month"].dt.to_period("M").astype(str)
    df["Revenue"] = df["Ext Price"]

    return df

# --------------------------------
# LOAD + PREP
# --------------------------------
df = load_data()
df = prepare_data(df)

# --------------------------------
# SIDEBAR FILTERS
# --------------------------------
st.sidebar.header("Filters")

stores = ["All Stores"] + sorted(df["Store"].dropna().unique().tolist())
departments = ["All Departments"] + sorted(df["Department"].dropna().unique().tolist())

selected_store = st.sidebar.selectbox("Store", stores)
selected_department = st.sidebar.selectbox("Department", departments)
period_type = st.sidebar.radio("Period", ["monthly", "annual"])

# --------------------------------
# APPLY FILTERS
# --------------------------------
def apply_filters(df, store, department):
    if store != "All Stores":
        df = df[df["Store"] == store]
    if department != "All Departments":
        df = df[df["Department"] == department]
    return df

filtered_df = apply_filters(df, selected_store, selected_department)

# --------------------------------
# KPI CALCULATIONS
# --------------------------------
def calculate_kpis(df):
    revenue = df["Ext Price"].sum()
    gross_profit = df["Total Margin $"].sum()
    margin_pct = (gross_profit / revenue) * 100 if revenue > 0 else 0
    footfall = len(df)
    avg_basket = revenue / footfall if footfall > 0 else 0
    return revenue, gross_profit, margin_pct, footfall, avg_basket

# --------------------------------
# PERIOD SPLIT
# --------------------------------
def split_periods(df, period):
    if period == "monthly":
        current = df["Month"].max().to_period("M")
        previous = current - 1
        return (
            df[df["Month"].dt.to_period("M") == current],
            df[df["Month"].dt.to_period("M") == previous],
            previous.year
        )
    else:
        year = df["Year"].max()
        return (
            df[df["Year"] == year],
            df[df["Year"] == year - 1],
            year - 1
        )

# --------------------------------
# KPI COMPARISON
# --------------------------------
def compare_kpis(curr, prev):
    cr, _, cm, cf, cb = calculate_kpis(curr)
    pr, _, pm, pf, pb = calculate_kpis(prev)

    def pct(a, b): return ((a - b) / b) * 100 if b > 0 else 0

    return {
        "revenue_change": pct(cr, pr),
        "margin_change_pp": cm - pm,
        "footfall_change": pct(cf, pf),
        "avg_basket_change": pct(cb, pb)
    }

# --------------------------------
# INFLATION
# --------------------------------
INFLATION_RATES = {2022: 22.8, 2023: 28.2, 2024: 34.8, 2025: 22.2}

def inflation_adjusted_growth(nominal, year):
    inflation = INFLATION_RATES.get(year, 0)
    return nominal - inflation, inflation

# --------------------------------
# TOP CONTRIBUTORS
# --------------------------------
def top_department(df):
    g = df.groupby("Department")["Revenue"].sum()
    return (g.idxmax(), g.max() / g.sum() * 100) if not g.empty else (None, 0)

def top_product(df):
    g = df.groupby("Item Name")["Revenue"].sum()
    return (g.idxmax(), g.max() / g.sum() * 100) if not g.empty else (None, 0)

# --------------------------------
# OPERATIONAL SUMMARY
# --------------------------------
def generate_operational_summary(df, store, department, period):
    curr, prev, base_year = split_periods(df, period)
    comp = compare_kpis(curr, prev)

    label = (
        f"{store} – {department}"
        if store != "All Stores" and department != "All Departments"
        else store if store != "All Stores"
        else department if department != "All Departments"
        else "All Stores"
    )

    real_rev, _ = inflation_adjusted_growth(comp["revenue_change"], base_year)

    insights = [
        f"{label}: real revenue {'grew' if real_rev >= 0 else 'declined'} {abs(real_rev):.1f}% after inflation."
    ]

    if abs(comp["footfall_change"]) >= 5:
        insights.append(f"Footfall changed by {comp['footfall_change']:.1f}%.")

    if abs(comp["avg_basket_change"]) >= 5:
        insights.append("Average basket value shifted materially.")

    if abs(comp["margin_change_pp"]) >= 1:
        insights.append(f"Gross margin moved {comp['margin_change_pp']:.1f}pp.")

    return insights

# --------------------------------
# KPI DISPLAY
# --------------------------------
rev, gp, margin, footfall, basket = calculate_kpis(filtered_df)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Revenue", f"₦{rev:,.0f}")
c2.metric("Gross Profit", f"₦{gp:,.0f}")
c3.metric("Gross Margin %", f"{margin:.1f}%")
c4.metric("Footfall", f"{footfall:,}")
c5.metric("Avg Basket", f"₦{basket:,.0f}")

# --------------------------------
# OPERATIONAL SUMMARY
# --------------------------------
st.subheader("Operational Summary (Auto-generated)")
for line in generate_operational_summary(filtered_df, selected_store, selected_department, period_type):
    st.write("•", line)

# --------------------------------
# DATA TABLE
# --------------------------------
with st.expander("View underlying data"):
    st.dataframe(filtered_df)


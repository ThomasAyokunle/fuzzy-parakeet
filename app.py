
import streamlit as st
import pandas as pd
from datetime import datetime

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
# Replace with your actual Google Sheet ID
GOOGLE_SHEET_ID = "https://docs.google.com/spreadsheets/d/1x3I_PlOBsVpftrnt_X1h0SHsn9zCu8RTILC13aXkqAs/edit?usp=sharing"

# If your data is in the first tab
SHEET_NAME = "YEARLY_DATA"

CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
    f"/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
)

# --------------------------------
# LOAD DATA
# --------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL)
    return df

df = load_data()

# --------------------------------
# DATA PREPARATION
# --------------------------------
def prepare_data(df):
    df = df.copy()

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
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

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
    filtered = df.copy()

    if store != "All Stores":
        filtered = filtered[filtered["Store"] == store]

    if department != "All Departments":
        filtered = filtered[filtered["Department"] == department]

    return filtered

filtered_df = apply_filters(df, selected_store, selected_department)

# --------------------------------
# KPI CALCULATIONS
# --------------------------------
def calculate_kpis(df):
    revenue = df["Ext Price"].sum()
    gross_profit = df["Total Margin $"].sum()
    margin_pct = (gross_profit / revenue) * 100 if revenue > 0 else 0
    footfall = len(df)  # number of transactions
    avg_basket = revenue / footfall if footfall > 0 else 0

    return revenue, gross_profit, margin_pct, footfall, avg_basket

# --------------------------------
# PERIOD SPLIT
# --------------------------------
def split_periods(df, period):
    if period == "monthly":
        current_period = df["Month"].max().to_period("M")
        previous_period = current_period - 1

        current_df = df[df["Month"].dt.to_period("M") == current_period]
        previous_df = df[df["Month"].dt.to_period("M") == previous_period]

        base_year = previous_period.year
    else:
        current_year = df["Month"].dt.year.max()
        previous_year = current_year - 1

        current_df = df[df["Month"].dt.year == current_year]
        previous_df = df[df["Month"].dt.year == previous_year]

        base_year = previous_year

    return current_df, previous_df, base_year

# --------------------------------
# KPI COMPARISON
# --------------------------------
def compare_kpis(current_df, previous_df):
    curr_rev, _, curr_margin, curr_footfall, curr_basket = calculate_kpis(current_df)
    prev_rev, _, prev_margin, prev_footfall, prev_basket = calculate_kpis(previous_df)

    def pct_change(curr, prev):
        return ((curr - prev) / prev) * 100 if prev > 0 else 0

    return {
        "revenue_change": pct_change(curr_rev, prev_rev),
        "margin_change_pp": curr_margin - prev_margin,
        "footfall_change": pct_change(curr_footfall, prev_footfall),
        "avg_basket_change": pct_change(curr_basket, prev_basket)
    }

# --------------------------------
# NIGERIA INFLATION DATA
# --------------------------------
INFLATION_RATES = {
    2022: 22.8,
    2023: 28.2,
    2024: 34.8,
    2025: 22.2
}

def inflation_adjusted_growth(nominal, year):
    inflation = INFLATION_RATES.get(year, 0)
    real = nominal - inflation
    return real, inflation

# --------------------------------
# TOP CONTRIBUTORS
# --------------------------------
def top_department(df):
    g = df.groupby("Department")["Ext Price"].sum().sort_values(ascending=False)
    if g.empty:
        return None, 0
    return g.index[0], (g.iloc[0] / g.sum()) * 100

def top_product(df):
    g = df.groupby("Item Name")["Ext Price"].sum().sort_values(ascending=False)
    if g.empty:
        return None, 0
    return g.index[0], (g.iloc[0] / g.sum()) * 100

# --------------------------------
# OPERATIONAL SUMMARY
# --------------------------------
def generate_operational_summary(df, store, department, period):
    current_df, previous_df, base_year = split_periods(df, period)
    comparison = compare_kpis(current_df, previous_df)

    insights = []

    label = (
        f"{store} – {department}"
        if store != "All Stores" and department != "All Departments"
        else store if store != "All Stores"
        else department if department != "All Departments"
        else "All Stores"
    )

    real_rev, inflation = inflation_adjusted_growth(
        comparison["revenue_change"], base_year
    )

    if real_rev >= 0:
        insights.append(
            f"{label}: real revenue grew {real_rev:.1f}% after adjusting for inflation."
        )
    else:
        insights.append(
            f"{label}: real revenue declined {abs(real_rev):.1f}% after inflation."
        )

    if abs(comparison["footfall_change"]) >= 5:
        direction = "increased" if comparison["footfall_change"] > 0 else "declined"
        insights.append(
            f"Customer footfall {direction} by {abs(comparison['footfall_change']):.1f}%."
        )

    if abs(comparison["avg_basket_change"]) >= 5:
        insights.append(
            "Average basket value increased, indicating improved mix or pricing."
            if comparison["avg_basket_change"] > 0
            else "Average basket value declined, indicating smaller spend per visit."
        )

    if abs(comparison["margin_change_pp"]) >= 1:
        direction = "improved" if comparison["margin_change_pp"] > 0 else "declined"
        insights.append(
            f"Gross margin {direction} by {abs(comparison['margin_change_pp']):.1f}pp."
        )

    if department == "All Departments":
        dept, share = top_department(current_df)
        if dept and share >= 20:
            insights.append(
                f"{dept} was the leading department, contributing {share:.1f}% of revenue."
            )

    product, pshare = top_product(current_df)
    if product and pshare >= 10:
        insights.append(
            f"Top-selling product contributed {pshare:.1f}% of total revenue."
        )

    return insights[:7]

# --------------------------------
# KPI DISPLAY
# --------------------------------
rev, gp, margin, footfall, basket = calculate_kpis(filtered_df)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Revenue", f"₦{rev:,.0f}")
col2.metric("Gross Profit", f"₦{gp:,.0f}")
col3.metric("Gross Margin %", f"{margin:.1f}%")
col4.metric("Footfall", f"{footfall:,}")
col5.metric("Avg Basket", f"₦{basket:,.0f}")

# --------------------------------
# OPERATIONAL SUMMARY DISPLAY
# --------------------------------
st.subheader("Operational Summary (Auto-generated)")

summary = generate_operational_summary(
    filtered_df,
    selected_store,
    selected_department,
    period_type
)

for line in summary:
    st.write("•", line)

# --------------------------------
# DATA TABLE (OPTIONAL)
# --------------------------------
with st.expander("View underlying data"):
    st.dataframe(filtered_df)

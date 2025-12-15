import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import urllib.parse

# --------------------------------
# PAGE CONFIG
# --------------------------------
st.set_page_config(
    page_title="Pharmacy Performance Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 1px solid #e1e4e8;
    }
    .stMetric label {
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: #374151 !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #1e3a8a !important;
    }
    .stMetric [data-testid="stMetricDelta"] {
        font-size: 1rem !important;
        font-weight: 600 !important;
    }
    .insight-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .warning-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 15px;
        border-radius: 8px;
        color: white;
        margin: 10px 0;
    }
    .success-box {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 15px;
        border-radius: 8px;
        color: white;
        margin: 10px 0;
    }
    h1 {
        color: #1e3a8a;
        font-weight: 700;
    }
    h2, h3 {
        color: #374151;
        font-weight: 600;
        margin-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Pharmacy Performance Dashboard")
st.markdown("**Executive Analytics | Real-time Performance Monitoring**")

# --------------------------------
# GOOGLE SHEET CONFIG
# --------------------------------
GOOGLE_SHEET_ID = "1x3I_PlOBsVpftrnt_X1h0SHsn9zCu8RTILC13aXkqAs"
SHEET_NAME = "YEARLY_DATA"
encoded_sheet_name = urllib.parse.quote(SHEET_NAME)
CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"

# --------------------------------
# LOAD DATA
# --------------------------------
@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(CSV_URL)
    df.columns = df.columns.str.strip()
    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    
    numeric_cols = ["Ext Price", "Qty Sold", "Ext Cost", "Markup %", "Margin %", "Total Margin $"]
    for col in numeric_cols:
        df[col] = df[col].astype(str).str.replace(",", "", regex=False).astype(float)
    
    df["Year"] = df["Month"].dt.year
    df["Revenue"] = df["Ext Price"]
    return df

df = load_data()

# --------------------------------
# SIDEBAR FILTERS
# --------------------------------
st.sidebar.markdown("### Filters")

# Add theme toggle
theme = st.sidebar.radio("Theme", ["Light", "Dark"], index=1, horizontal=True)

# Set color scheme based on theme
if theme == "Dark":
    bg_color = '#111827'
    plot_bg = '#1f2937'
    text_color = '#e5e7eb'
    grid_color = '#374151'
    title_color = '#f3f4f6'
else:
    bg_color = '#ffffff'
    plot_bg = '#f9fafb'
    text_color = '#1f2937'
    grid_color = '#e5e7eb'
    title_color = '#111827'

st.sidebar.markdown("---")

stores = ["All Stores"] + sorted(df["Store"].dropna().unique().tolist())
departments = ["All Departments"] + sorted(df["Department"].dropna().unique().tolist())

selected_store = st.sidebar.selectbox("Branch", stores)
selected_department = st.sidebar.selectbox("Department", departments)

st.sidebar.markdown("---")
st.sidebar.markdown("### Time Period")

min_date = df["Month"].min().date()
max_date = df["Month"].max().date()

# Get the last complete month (end of previous month)
today_actual = datetime.now().date()
if today_actual.day == 1:
    last_complete_month = (today_actual - timedelta(days=1))
else:
    # If we're mid-month, use last month's end as the last complete data
    last_complete_month = today_actual.replace(day=1) - timedelta(days=1)

# Use the actual max date from data (which should be month-end)
# But don't go beyond last complete month
effective_max_date = min(max_date, last_complete_month)

preset = st.sidebar.selectbox(
    "Quick Select",
    ["Custom", "MTD", "QTD", "YTD"]
)

# Comparison type
comparison_type = st.sidebar.radio(
    "Compare with:",
    ["Previous Period", "Same Period Last Year"],
    help="Previous Period: Compare with the immediately preceding period of same length\nSame Period Last Year: Compare with the same months from last year"
)

if preset == "MTD":
    # Current month data (if available)
    start_date = effective_max_date.replace(day=1)
    end_date = effective_max_date
elif preset == "QTD":
    quarter_month = ((effective_max_date.month - 1) // 3) * 3 + 1
    start_date = effective_max_date.replace(month=quarter_month, day=1)
    end_date = effective_max_date
elif preset == "YTD":
    start_date = effective_max_date.replace(month=1, day=1)
    end_date = effective_max_date
elif preset == "Last 6 Months":
    # Go back 6 complete months
    end_date = effective_max_date
    months_back = 6
    if end_date.month > months_back:
        start_date = end_date.replace(month=end_date.month - months_back, day=1)
    else:
        start_date = end_date.replace(year=end_date.year - 1, month=12 + end_date.month - months_back, day=1)
elif preset == "Last 12 Months":
    # Go back 12 complete months
    end_date = effective_max_date
    start_date = end_date.replace(year=end_date.year - 1, day=1)
    # Adjust to first day of the month 12 months ago
    if end_date.month == 12:
        start_date = start_date.replace(month=1)
    else:
        start_date = start_date.replace(month=end_date.month + 1)
else:
    date_selection = st.sidebar.date_input(
        "Select date range",
        value=[min_date, effective_max_date],
        min_value=min_date,
        max_value=effective_max_date
    )
    if isinstance(date_selection, (list, tuple)) and len(date_selection) == 2:
        start_date, end_date = date_selection
    else:
        start_date = date_selection
        end_date = date_selection

st.sidebar.info(f"📊 Latest data: {effective_max_date.strftime('%b %Y')}")

# --------------------------------
# APPLY FILTERS
# --------------------------------
filtered_df = df.copy()

if selected_store != "All Stores":
    filtered_df = filtered_df[filtered_df["Store"] == selected_store]

if selected_department != "All Departments":
    filtered_df = filtered_df[filtered_df["Department"] == selected_department]

# Convert dates to datetime for comparison - ensure we're comparing full months
filtered_df = filtered_df[
    (filtered_df["Month"] >= pd.to_datetime(start_date)) &
    (filtered_df["Month"] <= pd.to_datetime(end_date))
]

# --------------------------------
# NUMBER FORMATTING HELPER
# --------------------------------
def format_number(num):
    """Format large numbers to K (thousands) or M (millions)"""
    if abs(num) >= 1_000_000:
        return f"₦{num/1_000_000:.1f}M"
    elif abs(num) >= 1_000:
        return f"₦{num/1_000:.0f}K"
    else:
        return f"₦{num:.0f}"

def format_number_plain(num):
    """Format without currency symbol"""
    if abs(num) >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif abs(num) >= 1_000:
        return f"{num/1_000:.0f}K"
    else:
        return f"{num:.0f}"

# --------------------------------
# COMPARISON PERIOD
# --------------------------------
days_diff = (end_date - start_date).days

if comparison_type == "Same Period Last Year":
    # Compare with same months from last year
    try:
        comparison_start = start_date.replace(year=start_date.year - 1)
        comparison_end = end_date.replace(year=end_date.year - 1)
    except ValueError:
        # Handle leap year edge case (Feb 29)
        comparison_start = start_date.replace(year=start_date.year - 1, day=28)
        comparison_end = end_date.replace(year=end_date.year - 1, day=28)
else:
    # Previous Period - same length immediately before current period
    comparison_end = start_date - timedelta(days=1)
    comparison_start = comparison_end - timedelta(days=days_diff)

comparison_df = df.copy()
if selected_store != "All Stores":
    comparison_df = comparison_df[comparison_df["Store"] == selected_store]
if selected_department != "All Departments":
    comparison_df = comparison_df[comparison_df["Department"] == selected_department]

# Convert to datetime for comparison - use same logic as filtered_df
comparison_df = comparison_df[
    (comparison_df["Month"] >= pd.to_datetime(comparison_start)) &
    (comparison_df["Month"] <= pd.to_datetime(comparison_end))
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
    qty_sold = df["Qty Sold"].sum()
    return revenue, gross_profit, margin_pct, footfall, avg_basket, qty_sold

curr_rev, curr_gp, curr_margin, curr_footfall, curr_basket, curr_qty = calculate_kpis(filtered_df)
comp_rev, comp_gp, comp_margin, comp_footfall, comp_basket, comp_qty = calculate_kpis(comparison_df)

# Calculate deltas
rev_change = ((curr_rev - comp_rev) / comp_rev * 100) if comp_rev else 0
gp_change = ((curr_gp - comp_gp) / comp_gp * 100) if comp_gp else 0
margin_change = curr_margin - comp_margin
footfall_change = ((curr_footfall - comp_footfall) / comp_footfall * 100) if comp_footfall else 0
basket_change = ((curr_basket - comp_basket) / comp_basket * 100) if comp_basket else 0

# --------------------------------
# EXECUTIVE SUMMARY
# --------------------------------
st.markdown("## Executive Summary")

col1, col2, col3 = st.columns(3)

with col1:
    if rev_change > 0:
        st.markdown(f"""
        <div class="success-box">
        <h4>Revenue Growth</h4>
        <p style="font-size: 1.5rem; font-weight: bold;">+{rev_change:.1f}%</p>
        <p>vs. previous period</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="warning-box">
        <h4>Revenue Decline</h4>
        <p style="font-size: 1.5rem; font-weight: bold;">{rev_change:.1f}%</p>
        <p>vs. previous period</p>
        </div>
        """, unsafe_allow_html=True)

with col2:
    if curr_margin > 20:
        st.markdown(f"""
        <div class="success-box">
        <h4>Healthy Margins</h4>
        <p style="font-size: 1.5rem; font-weight: bold;">{curr_margin:.1f}%</p>
        <p>Gross margin maintained</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="warning-box">
        <h4>Margin Pressure</h4>
        <p style="font-size: 1.5rem; font-weight: bold;">{curr_margin:.1f}%</p>
        <p>Below 20% target</p>
        </div>
        """, unsafe_allow_html=True)

with col3:
    if basket_change > 0:
        st.markdown(f"""
        <div class="success-box">
        <h4>Basket Value Up</h4>
        <p style="font-size: 1.5rem; font-weight: bold;">+{basket_change:.1f}%</p>
        <p>Average transaction size</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="insight-box">
        <h4>Basket Value</h4>
        <p style="font-size: 1.5rem; font-weight: bold;">{basket_change:.1f}%</p>
        <p>Average transaction size</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# --------------------------------
# KPI METRICS
# --------------------------------
st.markdown("## Key Performance Indicators")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("Revenue", format_number(curr_rev), f"{rev_change:+.1f}%")

with c2:
    st.metric("Gross Profit", format_number(curr_gp), f"{gp_change:+.1f}%")

with c3:
    st.metric("Margin %", f"{curr_margin:.1f}%", f"{margin_change:+.1f}pp")

with c4:
    st.metric("Transactions", f"{curr_footfall:,}", f"{footfall_change:+.1f}%")

with c5:
    st.metric("Avg Basket", format_number(curr_basket), f"{basket_change:+.1f}%")

st.markdown("---")

# --------------------------------
# TREND ANALYSIS
# --------------------------------
st.markdown("## Performance Trends")

# Prepare monthly data for current period
monthly_current = (
    filtered_df
    .groupby(filtered_df["Month"].dt.to_period("M"))
    .agg(
        Revenue=("Revenue", "sum"),
        Gross_Profit=("Total Margin $", "sum"),
        Margin=("Margin %", "mean"),
        Transactions=("Revenue", "count")
    )
    .reset_index()
)
monthly_current["Month"] = monthly_current["Month"].dt.to_timestamp()
monthly_current["Month_Label"] = monthly_current["Month"].dt.strftime('%b %Y')
monthly_current["Period"] = "Current"

# Prepare monthly data for comparison period
monthly_comparison = (
    comparison_df
    .groupby(comparison_df["Month"].dt.to_period("M"))
    .agg(
        Revenue=("Revenue", "sum"),
        Gross_Profit=("Total Margin $", "sum"),
        Margin=("Margin %", "mean"),
        Transactions=("Revenue", "count")
    )
    .reset_index()
)
monthly_comparison["Month"] = monthly_comparison["Month"].dt.to_timestamp()
monthly_comparison["Month_Label"] = monthly_comparison["Month"].dt.strftime('%b %Y')
monthly_comparison["Period"] = "Previous"

# Revenue and Profit Trend with Comparison
fig_rev_profit = go.Figure()

# Current period - Revenue (bars)
fig_rev_profit.add_trace(go.Bar(
    x=monthly_current["Month_Label"],
    y=monthly_current["Revenue"],
    name="Revenue (Current)",
    marker_color='#6366f1',
    text=monthly_current["Revenue"].apply(lambda x: format_number_plain(x)),
    textposition='outside',
    textfont=dict(size=11, color='#e5e7eb'),
    hovertemplate='<b>%{x}</b><br>Revenue: ₦%{y:,.0f}<extra></extra>'
))

# Current period - Gross Profit (line)
fig_rev_profit.add_trace(go.Scatter(
    x=monthly_current["Month_Label"],
    y=monthly_current["Gross_Profit"],
    name="Gross Profit (Current)",
    mode='lines+markers',
    marker=dict(size=10, color='#ef4444', line=dict(width=2, color='white')),
    line=dict(width=4, color='#ef4444'),
    hovertemplate='<b>%{x}</b><br>Gross Profit: ₦%{y:,.0f}<extra></extra>'
))

# Previous period - Revenue (dashed line for comparison)
if len(monthly_comparison) > 0:
    fig_rev_profit.add_trace(go.Scatter(
        x=monthly_comparison["Month_Label"],
        y=monthly_comparison["Revenue"],
        name="Revenue (Previous)",
        mode='lines',
        line=dict(width=3, color='#6366f1', dash='dash'),
        opacity=0.6,
        hovertemplate='<b>%{x}</b><br>Revenue (Prev): ₦%{y:,.0f}<extra></extra>'
    ))

fig_rev_profit.update_layout(
    title={
        'text': "Revenue & Gross Profit Trend",
        'font': {'size': 18, 'color': '#f3f4f6', 'family': 'Arial Black'}
    },
    xaxis_title="",
    yaxis_title="Amount (₦)",
    hovermode='x unified',
    height=480,
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="top",
        y=1.15,
        xanchor="center",
        x=0.5,
        bgcolor='rgba(0,0,0,0)',
        font=dict(size=12, color='#e5e7eb')
    ),
    plot_bgcolor='#1f2937',
    paper_bgcolor='#111827',
    font=dict(color='#e5e7eb'),
    xaxis=dict(
        tickangle=-45,
        gridcolor='#374151',
        tickfont=dict(size=11, color='#9ca3af')
    ),
    yaxis=dict(
        gridcolor='#374151',
        tickfont=dict(size=11, color='#9ca3af'),
        tickformat=','
    ),
    margin=dict(t=100, b=80, l=80, r=40)
)

# Margin Trend with Comparison
fig_margin = go.Figure()

# Current period margin with fill
fig_margin.add_trace(go.Scatter(
    x=monthly_current["Month_Label"],
    y=monthly_current["Margin"],
    name="Current Period",
    mode='lines+markers',
    fill='tozeroy',
    marker=dict(size=12, color='#06b6d4', line=dict(width=2, color='white')),
    line=dict(width=4, color='#06b6d4'),
    fillcolor='rgba(6, 182, 212, 0.3)',
    text=monthly_current["Margin"].apply(lambda x: f"{x:.1f}%"),
    textposition='top center',
    textfont=dict(size=10, color='#e5e7eb'),
    hovertemplate='<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>'
))

# Previous period margin
if len(monthly_comparison) > 0:
    fig_margin.add_trace(go.Scatter(
        x=monthly_comparison["Month_Label"],
        y=monthly_comparison["Margin"],
        name="Previous Period",
        mode='lines+markers',
        marker=dict(size=10, color='#a78bfa', line=dict(width=2, color='white')),
        line=dict(width=3, color='#a78bfa', dash='dot'),
        opacity=0.8,
        hovertemplate='<b>%{x}</b><br>Margin (Prev): %{y:.1f}%<extra></extra>'
    ))

fig_margin.add_hline(
    y=20,
    line_dash="dash",
    line_color="#ef4444",
    line_width=2,
    annotation_text="Target: 20%",
    annotation_position="right",
    annotation_font=dict(size=12, color='#ef4444')
)

fig_margin.update_layout(
    title={
        'text': "Gross Margin Trend (%) - Current vs Previous",
        'font': {'size': 18, 'color': '#f3f4f6', 'family': 'Arial Black'}
    },
    xaxis_title="",
    yaxis_title="Margin %",
    height=480,
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="top",
        y=1.15,
        xanchor="center",
        x=0.5,
        bgcolor='rgba(0,0,0,0)',
        font=dict(size=12, color='#e5e7eb')
    ),
    plot_bgcolor='#1f2937',
    paper_bgcolor='#111827',
    font=dict(color='#e5e7eb'),
    xaxis=dict(
        tickangle=-45,
        gridcolor='#374151',
        tickfont=dict(size=11, color='#9ca3af')
    ),
    yaxis=dict(
        gridcolor='#374151',
        tickfont=dict(size=11, color='#9ca3af'),
        range=[0, max(monthly_current["Margin"].max() * 1.15, 25)]
    ),
    margin=dict(t=100, b=80, l=80, r=40)
)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_rev_profit, use_container_width=True)
col2.plotly_chart(fig_margin, use_container_width=True)

# Add a monthly comparison table
st.markdown("### Monthly Breakdown")

if len(monthly_current) > 0:
    # Filter out months with no data for the table
    comparison_table = monthly_current[monthly_current["Revenue"] > 0][["Month_Label", "Revenue", "Gross_Profit", "Margin", "Transactions"]].copy()
    
    if len(comparison_table) > 0:
        comparison_table.columns = ["Month", "Revenue", "Gross Profit", "Margin %", "Transactions"]

        # Format the table
        st.dataframe(
            comparison_table.style.format({
                "Revenue": lambda x: format_number(x),
                "Gross Profit": lambda x: format_number(x),
                "Margin %": "{:.1f}%",
                "Transactions": "{:,.0f}"
            }).set_properties(**{
                'background-color': plot_bg,
                'color': text_color,
                'border-color': grid_color
            }),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No transaction data available for the selected period")
else:
    st.info("No data available for the selected period")

st.markdown("---")

# --------------------------------
# PERIOD COMPARISON
# --------------------------------
st.markdown("## Period Comparison Analysis")

comp_col1, comp_col2, comp_col3 = st.columns(3)

with comp_col1:
    st.markdown("### Current Period")
    st.metric("Date Range", f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}")
    st.metric("Revenue", format_number(curr_rev))
    st.metric("Gross Profit", format_number(curr_gp))
    st.metric("Margin", f"{curr_margin:.1f}%")
    st.metric("Transactions", f"{curr_footfall:,}")

with comp_col2:
    st.markdown("### Previous Period")
    st.metric("Date Range", f"{comparison_start.strftime('%b %d, %Y')} - {comparison_end.strftime('%b %d, %Y')}")
    st.metric("Revenue", format_number(comp_rev))
    st.metric("Gross Profit", format_number(comp_gp))
    st.metric("Margin", f"{comp_margin:.1f}%")
    st.metric("Transactions", f"{comp_footfall:,}")

with comp_col3:
    st.markdown("### Change")
    st.metric("Period", f"{days_diff + 1} days")
    
    if comp_rev > 0:
        rev_diff = curr_rev - comp_rev
        st.metric("Revenue Change", format_number(rev_diff), f"{rev_change:+.1f}%")
    else:
        st.metric("Revenue Change", "N/A", "No comparison data")
    
    if comp_gp > 0:
        gp_diff = curr_gp - comp_gp
        st.metric("Profit Change", format_number(gp_diff), f"{gp_change:+.1f}%")
    else:
        st.metric("Profit Change", "N/A", "No comparison data")
    
    st.metric("Margin Change", f"{margin_change:+.1f}pp")
    
    if comp_footfall > 0:
        footfall_diff = curr_footfall - comp_footfall
        st.metric("Transaction Change", f"{footfall_diff:+,}", f"{footfall_change:+.1f}%")
    else:
        st.metric("Transaction Change", "N/A", "No comparison data")

# Comparison insights
st.markdown("#### Key Takeaways")
comparison_insights = []

if comp_rev > 0:
    if rev_change > 10:
        comparison_insights.append(("success", f"Strong revenue growth of {rev_change:.1f}% vs previous period"))
    elif rev_change > 0:
        comparison_insights.append(("info", f"Positive revenue growth of {rev_change:.1f}%"))
    else:
        comparison_insights.append(("warning", f"Revenue declined {abs(rev_change):.1f}% - requires attention"))
    
    if margin_change > 1:
        comparison_insights.append(("success", f"Margin improved by {margin_change:.1f} percentage points"))
    elif margin_change < -1:
        comparison_insights.append(("warning", f"Margin compressed by {abs(margin_change):.1f} percentage points"))
    
    if footfall_change < -5 and rev_change > 0:
        comparison_insights.append(("info", "Revenue up despite fewer transactions - higher basket value driving growth"))
    elif footfall_change > 5 and basket_change < 0:
        comparison_insights.append(("info", "More transactions but lower basket - opportunity to increase upselling"))

cols = st.columns(len(comparison_insights) if comparison_insights else 1)
for idx, (box_type, message) in enumerate(comparison_insights):
    with cols[idx]:
        if box_type == "success":
            st.success(message)
        elif box_type == "warning":
            st.warning(message)
        else:
            st.info(message)

st.markdown("---")

# --------------------------------
# COMPARATIVE ANALYSIS
# --------------------------------
st.markdown("## Comparative Analysis")

tab1, tab2, tab3 = st.tabs(["Top Products", "Store Performance", "Department Mix"])

with tab1:
    top_products = (
        filtered_df
        .groupby("Item Name")
        .agg(
            Revenue=("Revenue", "sum"),
            Quantity=("Qty Sold", "sum"),
            Margin=("Margin %", "mean")
        )
        .sort_values("Revenue", ascending=False)
        .head(10)
        .reset_index()
    )
    
    fig_products = go.Figure()
    fig_products.add_trace(go.Bar(
        y=top_products["Item Name"],
        x=top_products["Revenue"],
        orientation='h',
        marker=dict(
            color=top_products["Revenue"],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Revenue", tickfont=dict(color=text_color))
        ),
        text=top_products["Revenue"].apply(lambda x: format_number(x)),
        textposition='outside',
        textfont=dict(color=text_color),
        hovertemplate='<b>%{y}</b><br>Revenue: ₦%{x:,.0f}<extra></extra>'
    ))
    fig_products.update_layout(
        title={
            'text': "Top 10 Products by Revenue",
            'font': {'size': 18, 'color': title_color, 'family': 'Arial Black'}
        },
        xaxis_title="Revenue (₦)",
        yaxis_title="",
        height=500,
        yaxis=dict(autorange="reversed", tickfont=dict(color=text_color)),
        plot_bgcolor=plot_bg,
        paper_bgcolor=bg_color,
        font=dict(color=text_color),
        xaxis=dict(gridcolor=grid_color, tickfont=dict(color=text_color))
    )
    st.plotly_chart(fig_products, use_container_width=True)
    
    col1, col2 = st.columns(2)
    col1.dataframe(
        top_products[["Item Name", "Revenue", "Quantity"]].style.format({
            "Revenue": lambda x: format_number(x),
            "Quantity": "{:,.0f}"
        }),
        hide_index=True,
        use_container_width=True
    )

with tab2:
    if selected_store == "All Stores":
        store_perf = (
            filtered_df
            .groupby("Store")
            .agg(
                Revenue=("Revenue", "sum"),
                Margin=("Margin %", "mean"),
                Transactions=("Revenue", "count")
            )
            .sort_values("Revenue", ascending=False)
            .reset_index()
        )
        
        fig_store = go.Figure()
        fig_store.add_trace(go.Bar(
            x=store_perf["Store"],
            y=store_perf["Revenue"],
            name="Revenue",
            marker_color='#6366f1',
            text=store_perf["Revenue"].apply(lambda x: format_number_plain(x)),
            textposition='outside',
            textfont=dict(color=text_color),
            hovertemplate='<b>%{x}</b><br>Revenue: ₦%{y:,.0f}<extra></extra>'
        ))
        fig_store.update_layout(
            title={
                'text': "Store Performance Comparison",
                'font': {'size': 18, 'color': title_color, 'family': 'Arial Black'}
            },
            xaxis_title="Store",
            yaxis_title="Revenue (₦)",
            height=400,
            plot_bgcolor=plot_bg,
            paper_bgcolor=bg_color,
            font=dict(color=text_color),
            xaxis=dict(gridcolor=grid_color, tickfont=dict(color=text_color)),
            yaxis=dict(gridcolor=grid_color, tickfont=dict(color=text_color))
        )
        st.plotly_chart(fig_store, use_container_width=True)
        
        st.dataframe(
            store_perf.style.format({
                "Revenue": lambda x: format_number(x),
                "Margin": "{:.1f}%",
                "Transactions": "{:,.0f}"
            }),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info(f"Currently viewing: {selected_store}. Select 'All Stores' to see comparison.")

with tab3:
    if selected_department == "All Departments":
        dept_perf = (
            filtered_df
            .groupby("Department")
            .agg(
                Revenue=("Revenue", "sum"),
                Margin=("Margin %", "mean")
            )
            .sort_values("Revenue", ascending=False)
            .reset_index()
        )
        
        # Get top 10 departments
        top_10_dept = dept_perf.head(10).copy()
        
        # Calculate "Others" if there are more than 10 departments
        if len(dept_perf) > 10:
            others_revenue = dept_perf.iloc[10:]["Revenue"].sum()
            others_margin = dept_perf.iloc[10:]["Margin"].mean()
            others_row = pd.DataFrame({
                "Department": ["Others"],
                "Revenue": [others_revenue],
                "Margin": [others_margin]
            })
            top_10_dept = pd.concat([top_10_dept, others_row], ignore_index=True)
        
        fig_dept = px.pie(
            top_10_dept,
            values="Revenue",
            names="Department",
            title="Revenue Distribution by Department (Top 10)",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_dept.update_traces(
            textposition='inside',
            textinfo='percent+label',
            textfont=dict(size=12, color='white')
        )
        fig_dept.update_layout(
            height=500,
            title={
                'text': "Revenue Distribution by Department (Top 10)",
                'font': {'size': 18, 'color': title_color, 'family': 'Arial Black'}
            },
            paper_bgcolor=bg_color,
            font=dict(color=text_color),
            legend=dict(font=dict(color=text_color))
        )
        st.plotly_chart(fig_dept, use_container_width=True)
        
        st.dataframe(
            top_10_dept.style.format({
                "Revenue": lambda x: format_number(x),
                "Margin": "{:.1f}%"
            }),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info(f"Currently viewing: {selected_department}. Select 'All Departments' to see mix.")

st.markdown("---")

# --------------------------------
# INSIGHTS & RECOMMENDATIONS
# --------------------------------
st.markdown("## Key Insights & Recommendations")

insights = []

# Revenue analysis
if rev_change > 10:
    insights.append(("success", "Strong Growth", f"Revenue increased by {rev_change:.1f}% - maintain momentum through inventory optimization"))
elif rev_change > 0:
    insights.append(("info", "Moderate Growth", f"Revenue up {rev_change:.1f}% - explore opportunities to accelerate"))
else:
    insights.append(("warning", "Revenue Decline", f"Revenue down {abs(rev_change):.1f}% - immediate action required"))

# Margin analysis
if margin_change < -2:
    insights.append(("warning", "Margin Pressure", f"Margins declined {abs(margin_change):.1f}pp - review pricing and supplier costs"))
elif curr_margin < 18:
    insights.append(("warning", "Low Margins", "Current margins below industry standard - pricing review recommended"))

# Basket size
if basket_change < -5:
    insights.append(("warning", "Declining Basket", f"Average basket down {abs(basket_change):.1f}% - consider upselling strategies"))
elif basket_change > 5:
    insights.append(("success", "Growing Basket", f"Average basket up {basket_change:.1f}% - successful cross-selling"))

# Top performer
if len(filtered_df) > 0:
    top_product = filtered_df.groupby("Item Name")["Revenue"].sum().idxmax()
    insights.append(("info", "Top Performer", f"{top_product} drives significant revenue - ensure adequate stock"))

# Display insights
for i, (box_type, title, message) in enumerate(insights[:5]):
    if box_type == "success":
        st.markdown(f"""
        <div class="success-box">
        <h4>{title}</h4>
        <p>{message}</p>
        </div>
        """, unsafe_allow_html=True)
    elif box_type == "warning":
        st.markdown(f"""
        <div class="warning-box">
        <h4>{title}</h4>
        <p>{message}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="insight-box">
        <h4>{title}</h4>
        <p>{message}</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# --------------------------------
# DATA EXPORT
# --------------------------------
with st.expander("Export Data & Details"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Period Coverage**")
        st.write(f"From: {start_date}")
        st.write(f"To: {end_date}")
        st.write(f"Total Records: {len(filtered_df):,}")
    
    with col2:
        st.markdown("**Filters Applied**")
        st.write(f"Store: {selected_store}")
        st.write(f"Department: {selected_department}")
    
    st.markdown("**Raw Data**")
    st.dataframe(filtered_df, use_container_width=True)
    
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"pharmacy_data_{start_date}_{end_date}.csv",
        mime="text/csv"
    )

st.markdown("---")
st.caption("Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M"))

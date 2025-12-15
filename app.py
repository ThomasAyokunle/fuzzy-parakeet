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
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric label {
        font-size: 0.9rem !important;
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

stores = ["All Stores"] + sorted(df["Store"].dropna().unique().tolist())
departments = ["All Departments"] + sorted(df["Department"].dropna().unique().tolist())

selected_store = st.sidebar.selectbox("Branch", stores)
selected_department = st.sidebar.selectbox("🏥 Department", departments)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Time Period")

min_date = df["Month"].min().date()
max_date = df["Month"].max().date()

preset = st.sidebar.selectbox(
    "Quick Select",
    ["Custom", "MTD", "QTD", "YTD", "Last 6 Months", "Last 12 Months"]
)

today = max_date

if preset == "MTD":
    start_date = today.replace(day=1)
    end_date = today
elif preset == "QTD":
    quarter_month = ((today.month - 1) // 3) * 3 + 1
    start_date = today.replace(month=quarter_month, day=1)
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
# COMPARISON PERIOD
# --------------------------------
days_diff = (end_date - start_date).days
comparison_start = start_date - timedelta(days=days_diff)
comparison_end = start_date - timedelta(days=1)

comparison_df = df.copy()
if selected_store != "All Stores":
    comparison_df = comparison_df[comparison_df["Store"] == selected_store]
if selected_department != "All Departments":
    comparison_df = comparison_df[comparison_df["Department"] == selected_department]

comparison_df = comparison_df[
    (comparison_df["Month"].dt.date >= comparison_start) &
    (comparison_df["Month"].dt.date <= comparison_end)
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
        <h4> Revenue Growth</h4>
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
        <h4> Margin Pressure</h4>
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

c1.metric("Revenue", f"₦{curr_rev:,.0f}", f"{rev_change:+.1f}%")
c2.metric("Gross Profit", f"₦{curr_gp:,.0f}", f"{gp_change:+.1f}%")
c3.metric("Margin %", f"{curr_margin:.1f}%", f"{margin_change:+.1f}pp")
c4.metric("Transactions", f"{curr_footfall:,}", f"{footfall_change:+.1f}%")
c5.metric("Avg Basket", f"₦{curr_basket:,.0f}", f"{basket_change:+.1f}%")

st.markdown("---")

# --------------------------------
# TREND ANALYSIS
# --------------------------------
st.markdown("##Performance Trends")

monthly = (
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
monthly["Month"] = monthly["Month"].astype(str)

# Revenue and Profit Trend
fig_rev_profit = go.Figure()
fig_rev_profit.add_trace(go.Bar(
    x=monthly["Month"],
    y=monthly["Revenue"],
    name="Revenue",
    marker_color='#667eea',
    yaxis='y'
))
fig_rev_profit.add_trace(go.Scatter(
    x=monthly["Month"],
    y=monthly["Gross_Profit"],
    name="Gross Profit",
    mode='lines+markers',
    marker=dict(size=8, color='#f5576c'),
    line=dict(width=3),
    yaxis='y'
))
fig_rev_profit.update_layout(
    title="Revenue & Gross Profit Trend",
    xaxis_title="Month",
    yaxis_title="Amount (₦)",
    hovermode='x unified',
    height=400,
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

# Margin Trend
fig_margin = go.Figure()
fig_margin.add_trace(go.Scatter(
    x=monthly["Month"],
    y=monthly["Margin"],
    mode='lines+markers',
    fill='tozeroy',
    marker=dict(size=10, color='#00f2fe'),
    line=dict(width=3, color='#4facfe')
))
fig_margin.add_hline(y=20, line_dash="dash", line_color="red", 
                     annotation_text="Target: 20%")
fig_margin.update_layout(
    title="Gross Margin Trend (%)",
    xaxis_title="Month",
    yaxis_title="Margin %",
    height=400
)

col1, col2 = st.columns(2)
col1.plotly_chart(fig_rev_profit, use_container_width=True)
col2.plotly_chart(fig_margin, use_container_width=True)

st.markdown("---")

# --------------------------------
# COMPARATIVE ANALYSIS
# --------------------------------
st.markdown("## 🔍 Comparative Analysis")

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
            showscale=True
        ),
        text=top_products["Revenue"].apply(lambda x: f"₦{x:,.0f}"),
        textposition='outside'
    ))
    fig_products.update_layout(
        title="Top 10 Products by Revenue",
        xaxis_title="Revenue (₦)",
        yaxis_title="",
        height=500,
        yaxis=dict(autorange="reversed")
    )
    st.plotly_chart(fig_products, use_container_width=True)
    
    col1, col2 = st.columns(2)
    col1.dataframe(
        top_products[["Item Name", "Revenue", "Quantity"]].style.format({
            "Revenue": "₦{:,.0f}",
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
            marker_color='#667eea'
        ))
        fig_store.update_layout(
            title="Store Performance Comparison",
            xaxis_title="Store",
            yaxis_title="Revenue (₦)",
            height=400
        )
        st.plotly_chart(fig_store, use_container_width=True)
        
        st.dataframe(
            store_perf.style.format({
                "Revenue": "₦{:,.0f}",
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
        
        fig_dept = px.pie(
            dept_perf,
            values="Revenue",
            names="Department",
            title="Revenue Distribution by Department",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_dept.update_traces(textposition='inside', textinfo='percent+label')
        fig_dept.update_layout(height=500)
        st.plotly_chart(fig_dept, use_container_width=True)
        
        st.dataframe(
            dept_perf.style.format({
                "Revenue": "₦{:,.0f}",
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

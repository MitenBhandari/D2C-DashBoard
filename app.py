import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Order Operations Dashboard",
    layout="wide"
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    df = pd.read_csv("Output_Report.csv")

    date_columns = [
        "Devx Order Date (Date)",
        "UC Order Date (Date)",
        "Dispatch Date (Date)",
        "Pickup Date (Date)",
        "Delivery Date (Date)",
        "Assigned Date_D"
    ]

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    return df

df = load_data()

# Create Reshipped flag
if "Reshipped" in df.columns:
    df["Reshipped_Flag"] = (
        df["Reshipped"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["yes","y","true","1","reshipped"])
    )
else:
    df["Reshipped_Flag"] = False


@st.cache_data
def load_consolidated():
    df = pd.read_excel("Consolidated_Report.xlsx")
    return df
consolidated_df = load_consolidated()

merged_df = df.merge(
    consolidated_df[[
        "Devx Order ID",
        "New AWB Status",
        "Delivery Delay By"
    ]],
    on="Devx Order ID",
    how="left"
)

merged_df["Reshipped_Flag"] = merged_df["Reshipped_Flag"].fillna(False)


# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.header("Filters")

date_range = st.sidebar.date_input(
    "UC Order Date Range",
    [
        df["UC Order Date (Date)"].min(),
        df["UC Order Date (Date)"].max()
    ]
)


facility_filter = st.sidebar.multiselect(
    "Facility",
    sorted(df["Facility"].dropna().unique())
)

courier_filter = st.sidebar.multiselect(
    "Shipping Courier",
    sorted(df["Shipping Courier"].dropna().unique())
)

zone_filter = st.sidebar.multiselect(
    "Zone",
    sorted(df["Zone"].dropna().unique())
)

status_filter = st.sidebar.multiselect(
    "Final Status",
    sorted(df["Final Status"].dropna().unique())
)


# ---------------- APPLY FILTERS ----------------
filtered_df = df.copy()

if date_range:
    filtered_df = filtered_df[
        (filtered_df["UC Order Date (Date)"] >= pd.to_datetime(date_range[0])) &
        (filtered_df["UC Order Date (Date)"] <= pd.to_datetime(date_range[1]))
    ]

if facility_filter:
    filtered_df = filtered_df[filtered_df["Facility"].isin(facility_filter)]

if courier_filter:
    filtered_df = filtered_df[filtered_df["Shipping Courier"].isin(courier_filter)]

if zone_filter:
    filtered_df = filtered_df[filtered_df["Zone"].isin(zone_filter)]
    
if status_filter:
    filtered_df = filtered_df[filtered_df["Final Status"].isin(status_filter)]


# ---------------- KPI CALCULATIONS ----------------
reshipped_orders = filtered_df["Reshipped_Flag"].sum()

final_status = (
    filtered_df["Final Status"]
    .astype(str)
    .str.strip()
    .str.lower()
)

is_delivered = final_status.eq("delivered")
is_rto = final_status.eq("rto")
is_intransit = final_status.str.startswith("in-transit")

total_orders = len(filtered_df)
delivered_orders = is_delivered.sum()
rto_orders = is_rto.sum()
intransit_orders = is_intransit.sum()

def pct(part, whole):
    return round((part / whole) * 100, 1) if whole > 0 else 0

# Delivered SLA
delivered_in_tat = (
    filtered_df.loc[is_delivered, "Placed to Delivery TAT Status"]
    .astype(str)
    .str.lower()
    .eq("intat")
    .sum()
)

delivered_out_tat = (
    filtered_df.loc[is_delivered, "Placed to Delivery TAT Status"]
    .astype(str)
    .str.lower()
    .eq("outtat")
    .sum()
)

# In-Transit SLA (Pickup → Delivery)
intransit_in_tat = (
    filtered_df.loc[is_intransit, "Pickup to Delivery TAT Status"]
    .astype(str)
    .str.lower()
    .eq("intat")
    .sum()
)

intransit_out_tat = (
    filtered_df.loc[is_intransit, "Pickup to Delivery TAT Status"]
    .astype(str)
    .str.lower()
    .eq("outtat")
    .sum()
)

def green(text):
    return f"<span style='color:#2ecc71; font-weight:600'>{text}</span>"

# ---------------- EXECUTIVE SUMMARY CALCULATIONS ----------------

# Overall Delivered SLA %
overall_intat_pct = pct(delivered_in_tat, delivered_orders)

# Zone risk (Delivered orders)
zone_risk = (
    filtered_df[filtered_df["Final Status"].str.lower() == "delivered"]
    .groupby("Zone")
    .agg(
        total=("Placed to Delivery TAT Status", "count"),
        outtat=("Placed to Delivery TAT Status",
                lambda x: (x.str.lower() == "outtat").sum())
    )
    .reset_index()
)

if not zone_risk.empty:
    zone_risk["outtat_pct"] = (zone_risk["outtat"] / zone_risk["total"] * 100).round(1)
    worst_zone_row = zone_risk.sort_values("outtat_pct", ascending=False).iloc[0]
    worst_zone = worst_zone_row["Zone"]
    worst_zone_pct = worst_zone_row["outtat_pct"]
else:
    worst_zone = "N/A"
    worst_zone_pct = 0

# Courier risk
courier_risk = (
    filtered_df[filtered_df["Final Status"].str.lower() == "delivered"]
    .groupby("Shipping Courier")
    .agg(
        total=("Placed to Delivery TAT Status", "count"),
        outtat=("Placed to Delivery TAT Status",
                lambda x: (x.str.lower() == "outtat").sum())
    )
    .reset_index()
)

if not courier_risk.empty:
    courier_risk["outtat_pct"] = (courier_risk["outtat"] / courier_risk["total"] * 100).round(1)
    worst_courier = courier_risk.sort_values("outtat_pct", ascending=False).iloc[0]["Shipping Courier"]
else:
    worst_courier = "N/A"

# ---------------- DASHBOARD HEADER ----------------
st.title("Order Operations Dashboard")

tab_overview, tab_intransit, tab_delivered, tab_reshipped, tab_rto, tab_pickup = st.tabs([
    "Overview",
    "In Transit",
    "Delivered",
    "Reshipped",
    "RTO",
    "Pickup Pending"
])



with tab_overview:

    # ---------------- KPI ROW ----------------
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Orders", total_orders)

    c2.metric(
        "Delivered",
        delivered_orders,
        f"{pct(delivered_orders, total_orders)}%"
    )

    c3.metric(
        "In Transit",
        intransit_orders,
        f"{pct(intransit_orders, total_orders)}%"
    )

    c4.metric(
        "RTO",
        rto_orders,
        f"{pct(rto_orders, total_orders)}%"
    )

    # ---------------- SLA ROW ----------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("In Transit SLA")

        intransit_df = filtered_df[
            filtered_df["Final Status"].str.lower().str.startswith("in-transit")
        ]

        intransit_sla = (
            intransit_df
            .groupby("Pickup to Delivery TAT Status")
            .size()
            .reset_index(name="Orders")
        )

        fig = px.pie(
            intransit_sla,
            names="Pickup to Delivery TAT Status",
            values="Orders",
            height=320
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Delivered SLA")

        delivered_sla = (
            filtered_df[filtered_df["Final Status"].str.lower() == "delivered"]
            .groupby("Placed to Delivery TAT Status")
            .size()
            .reset_index(name="Orders")
        )

        fig = px.pie(
            delivered_sla,
            names="Placed to Delivery TAT Status",
            values="Orders",
            height=320
        )

        st.plotly_chart(fig, use_container_width=True)

    # ---------------- OPERATIONS ROW ----------------
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Reshipped Outcomes")

        reship_df = merged_df[merged_df["Reshipped_Flag"]]

        reship_summary = (
            reship_df
            .dropna(subset=["New AWB Status"])
            .groupby("New AWB Status")
            .size()
            .reset_index(name="Orders")
        )

        fig = px.bar(
            reship_summary,
            x="New AWB Status",
            y="Orders",
            height=320
        )

        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.subheader("RTO by Zone")

        rto_df = filtered_df[
            filtered_df["Final Status"].str.lower() == "rto"
        ]

        rto_summary = rto_df.groupby("Zone").size().reset_index(name="Orders")

        fig = px.bar(
            rto_summary,
            x="Zone",
            y="Orders",
            height=320
        )

        st.plotly_chart(fig, use_container_width=True)

    # ---------------- EXEC SUMMARY ----------------
    st.markdown(
        f"""
        **📌 Overall Delivery SLA:** {overall_intat_pct}% In-TAT  
        | **Biggest Risk:** {worst_zone} Zone ({worst_zone_pct}% Out-TAT)  
        | **Worst Courier:** {worst_courier}
        """
    )

# ---------------- DELIVERED IN-TAT TREND ----------------

with tab_delivered:
    trend_df = filtered_df[
    filtered_df["Final Status"].str.lower() == "delivered"
].copy()

    trend_df["order_date"] = trend_df["UC Order Date (Date)"].dt.date

    trend_agg = (
    trend_df
    .groupby("order_date")
    .agg(
        delivered_orders=("Placed to Delivery TAT Status", "count"),
        delivered_intat=("Placed to Delivery TAT Status",
                          lambda x: (x.str.lower() == "intat").sum())
    )
    .reset_index())

    trend_agg["Delivered In-TAT %"] = (
    trend_agg["delivered_intat"] / trend_agg["delivered_orders"] * 100).round(1)
    
    st.subheader("Delivered In-TAT Trend")

    trend_fig = px.line(
    trend_agg,
    x="order_date",
    y="Delivered In-TAT %",
    markers=True,
    title="Delivered In-TAT % Over Time")

    trend_fig.update_traces(
    line=dict(width=3),
    hovertemplate="Date: %{x}<br>In-TAT: %{y}%<extra></extra>")

    trend_fig.update_layout(
    yaxis=dict(range=[80, 100]),
    margin={"r":0,"t":40,"l":0,"b":0})

# Optional SLA target line (recommended)
    trend_fig.add_hline(
    y=95,
    line_dash="dash",
    annotation_text="Target: 95%",
    annotation_position="top left")

    st.plotly_chart(trend_fig, use_container_width=True, key="delivered_trend")


# ---------------- Dispatch Performance ----------------
with tab_pickup:
    st.subheader("Dispatch Performance")

    dispatch_agg = (
    filtered_df
    .groupby(["Facility", "Dispatch TAT Status"])
    .size()
    .reset_index(name="Count"))

    dispatch_agg["Percentage"] = (
    dispatch_agg["Count"] /
    dispatch_agg.groupby("Facility")["Count"].transform("sum") * 100).round(1)

    dispatch_fig = px.bar(
    dispatch_agg,
    x="Facility",
    y="Count",
    color="Dispatch TAT Status",
    text=dispatch_agg["Percentage"].astype(str) + "%",
    title="Dispatch TAT by Facility")

    dispatch_fig.update_traces(
    hovertemplate="Count: %{y}<extra></extra>"
)

    st.plotly_chart(dispatch_fig, use_container_width=True, key="dispatch_performance")


# ---------------- DELIVERY PERFORMANCE ----------------

with tab_delivered:
    st.subheader("Delivery Performance")

    delivery_agg = (
    filtered_df[filtered_df["Final Status"].str.lower() == "delivered"]
    .groupby(["Zone", "Placed to Delivery TAT Status"])
    .size()
    .reset_index(name="Count"))

    delivery_agg["Percentage"] = (
    delivery_agg["Count"] /
    delivery_agg.groupby("Zone")["Count"].transform("sum") * 100).round(1)

    delivery_fig = px.bar(
    delivery_agg,
    x="Zone",
    y="Count",
    color="Placed to Delivery TAT Status",
    text=delivery_agg["Percentage"].astype(str) + "%",
    title="Placed to Delivery TAT by Zone")

    delivery_fig.update_traces(
    hovertemplate="Count: %{y}<extra></extra>")

    st.plotly_chart(delivery_fig, use_container_width=True, key="zone_delivery_sla")

# ---------------- SHIPPING PROVIDER PERFORMANCE ----------------
with tab_delivered:
    st.subheader("Shipping Provider Load Distribution")

    provider_perf = (
    filtered_df
    .groupby("Shipping provider")
    .size()
    .reset_index(name="Count")
)

    provider_fig = px.pie(
    provider_perf,
    names="Shipping provider",
    values="Count",
    title="Orders by Shipping Provider",
    hole=0.4
)

    provider_fig.update_traces(
    hovertemplate="Provider: %{label}<br>Orders: %{value}<extra></extra>"
)

    selected_provider = st.plotly_chart(provider_fig, use_container_width=True, key="provider_load")


    st.subheader("Shipping Provider SLA Performance")

    provider_sla = (
    filtered_df
    .groupby(["Shipping provider", "Placed to Delivery TAT Status"])
    .size()
    .reset_index(name="Count")
)

    provider_sla_fig = px.bar(
    provider_sla,
    x="Shipping provider",
    y="Count",
    color="Placed to Delivery TAT Status",
    title="Provider-wise In-TAT vs Out-TAT",
    text="Count"
)

    provider_sla_fig.update_traces(
    hovertemplate="Count: %{y}<extra></extra>"
)

    st.plotly_chart(provider_sla_fig, use_container_width=True, key="provider_sla")   
    
    
with tab_intransit:
    st.subheader("In Transit SLA")

    intransit_df = merged_df[
    merged_df["Final Status"].str.lower().str.startswith("in-transit")
].copy()
    
    intransit_df["Delivery Delay By"] = pd.to_numeric(
    intransit_df["Delivery Delay By"], errors="coerce")

# Convert delay column to numeric
    intransit_df["Delivery Delay By"] = pd.to_numeric(
    intransit_df["Delivery Delay By"], errors="coerce"
)

# Create delay buckets
    def delay_bucket(row):

        if str(row["Pickup to Delivery TAT Status"]).lower() == "intat":
            return "In-TAT"

        d = row["Delivery Delay By"]

        if pd.isna(d):
            return "Out-TAT"

        elif d <= 2:
            return "Out-TAT (0–2 days)"

        elif d <= 5:
            return "Out-TAT (2–5 days)"

        else:
            return "Out-TAT (5+ days)"

    intransit_df["Delay Bucket"] = intransit_df.apply(delay_bucket, axis=1)

# Aggregate data
    intransit_sla = (
    intransit_df
    .groupby("Delay Bucket")
    .size()
    .reset_index(name="Orders"))

# Pie chart
    fig = px.pie(
    intransit_sla,
    names="Delay Bucket",
    values="Orders",
    title="In Transit SLA Breakdown",
    color="Delay Bucket",
    color_discrete_map={
        "In-TAT": "#2ecc71",
        "Out-TAT (0–2 days)": "#f1c40f",
        "Out-TAT (2–5 days)": "#e67e22",
        "Out-TAT (5+ days)": "#e74c3c",
        "Out-TAT": "#95a5a6"
    })

st.plotly_chart(fig, use_container_width=True, key="intransit_tab_sla")
    
    
with tab_reshipped:

    st.subheader("Reshipped Orders")

    reship_df = merged_df[merged_df["Reshipped_Flag"]]

    st.metric("Total Reshipped Orders", len(reship_df))

    reship_summary = (
        reship_df.groupby("New AWB Status")
        .size()
        .reset_index(name="Orders")
    )

    fig = px.bar(
        reship_summary,
        x="New AWB Status",
        y="Orders",
        color="New AWB Status",
        title="Reshipped Outcome"
    )

    st.plotly_chart(fig, use_container_width=True, key="reshipped_tab_chart")
    
    
with tab_rto:

    st.subheader("RTO Orders")

    rto_df = filtered_df[
        filtered_df["Final Status"].str.lower() == "rto"
    ]

    st.metric("Total RTO Orders", len(rto_df))

    rto_zone = (
        rto_df.groupby("Zone")
        .size()
        .reset_index(name="Orders")
    )

    fig = px.bar(
        rto_zone,
        x="Zone",
        y="Orders",
        color="Zone",
        title="RTO by Zone"
    )

    st.plotly_chart(fig, use_container_width=True, key="rto_tab_chart")

with tab_pickup:
    from datetime import datetime, timedelta

    consolidated = consolidated_df

    yesterday = datetime.today() - timedelta(days=1)

    pending_df = consolidated[
    (pd.to_datetime(consolidated["Ideal Dispatch Date"], errors="coerce") <= yesterday) &
    (consolidated["CP Order Status"].str.lower().isin([
        "awb registered",
        "orderplaced",
        "pickuppending"
    ]))
]

    st.subheader("Pickup Pending Orders")

    st.metric("Pending Pickup Orders", len(pending_df))

    st.dataframe(pending_df)

# ---------------- DATA PREVIEW ----------------
st.subheader("Filtered Data Preview")
st.dataframe(filtered_df, use_container_width=True)
#python -m streamlit run app.py
#python -m venv venv
#.\venv\Scripts\Activate.ps1

#git add Consolidated_Report.xlsx Output_Report.csv app.py input.py
#git commit -m "Add All"
#git push

#git add app.py 
#git commit -m "Add All" 
#git push



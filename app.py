import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Order Operations Dashboard",
    layout="wide"
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

# ---------------- DERIVED COLUMNS ----------------
if "Reshipped" in df.columns:
    df["Reshipped_Flag"] = (
        df["Reshipped"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["yes", "y", "true", "1", "reshipped"])
    )
else:
    df["Reshipped_Flag"] = False


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



# ---------------- DASHBOARD HEADER ----------------
st.title("Order Operations Dashboard")

c1, c2, c3 = st.columns(3)

# ---------------- Column 1: Overall ----------------
c1.metric(
    "Total Orders",
    total_orders
)
c1.metric(
    "RTO",
    rto_orders,
    f"{pct(rto_orders, total_orders)}%"
)
c1.metric(
    "Reshipped",
    reshipped_orders,
    f"{pct(reshipped_orders, total_orders)}%"
)

# ---------------- Column 2: Delivered ----------------
c2.metric(
    "Delivered",
    delivered_orders,
    f"{pct(delivered_orders, total_orders)}%"
)
c2.metric(
    "Delivered In-TAT",
    delivered_in_tat,
    f"{pct(delivered_in_tat, delivered_orders)}%"
)
c2.metric(
    "Delivered Out-TAT",
    delivered_out_tat,
    f"{pct(delivered_out_tat, delivered_orders)}%"
)

# ---------------- Column 3: In-Transit ----------------
c3.metric(
    "In Transit",
    intransit_orders,
    f"{pct(intransit_orders, total_orders)}%"
)
c3.metric(
    "In-Transit In-TAT",
    intransit_in_tat,
    f"{pct(intransit_in_tat, intransit_orders)}%"
)
c3.metric(
    "In-Transit Out-TAT",
    intransit_out_tat,
    f"{pct(intransit_out_tat, intransit_orders)}%"
)

st.divider()

st.subheader("SLA Split (Delivered vs In-Transit)")

status_choice = st.radio(
    "Select Order Type",
    ["Delivered", "In-Transit"],
    horizontal=True
)

if status_choice == "Delivered":
    sla_df = filtered_df[filtered_df["Final Status"].str.lower() == "delivered"]
else:
    sla_df = filtered_df[
        filtered_df["Final Status"].str.lower().str.startswith("in-transit")
    ]

status_col = (
    "Placed to Delivery TAT Status"
    if status_choice == "Delivered"
    else "Placed to Delivery TAT Status"
)

sla_split = (
    sla_df
    .groupby(status_col)
    .size()
    .reset_index(name="Count")
)


sla_pie = px.pie(
    sla_split,
    names="Placed to Delivery TAT Status",
    values="Count",
    title=f"{status_choice} SLA Split"
)

st.plotly_chart(sla_pie, use_container_width=True)


# ---------------- STATUS DISTRIBUTION ----------------
st.subheader("Final Order Status Distribution")

status_fig = px.pie(
    filtered_df,
    names="Final Status",
    title="Order Final Status Split"
)

st.plotly_chart(status_fig, use_container_width=True)

# ---------------- Dispatch Performance ----------------
st.subheader("Dispatch Performance")

dispatch_agg = (
    filtered_df
    .groupby(["Facility", "Dispatch TAT Status"])
    .size()
    .reset_index(name="Count")
)

dispatch_agg["Percentage"] = (
    dispatch_agg["Count"] /
    dispatch_agg.groupby("Facility")["Count"].transform("sum") * 100
).round(1)

dispatch_fig = px.bar(
    dispatch_agg,
    x="Facility",
    y="Count",
    color="Dispatch TAT Status",
    text=dispatch_agg["Percentage"].astype(str) + "%",
    title="Dispatch TAT by Facility"
)

dispatch_fig.update_traces(
    hovertemplate="Count: %{y}<extra></extra>"
)

st.plotly_chart(dispatch_fig, use_container_width=True)

# ---------------- DELIVERY PERFORMANCE ----------------
st.subheader("Delivery Performance")

delivery_agg = (
    filtered_df[filtered_df["Final Status"].str.lower() == "delivered"]
    .groupby(["Zone", "Placed to Delivery TAT Status"])
    .size()
    .reset_index(name="Count")
)

delivery_agg["Percentage"] = (
    delivery_agg["Count"] /
    delivery_agg.groupby("Zone")["Count"].transform("sum") * 100
).round(1)

delivery_fig = px.bar(
    delivery_agg,
    x="Zone",
    y="Count",
    color="Placed to Delivery TAT Status",
    text=delivery_agg["Percentage"].astype(str) + "%",
    title="Placed to Delivery TAT by Zone"
)

delivery_fig.update_traces(
    hovertemplate="Count: %{y}<extra></extra>"
)

st.plotly_chart(delivery_fig, use_container_width=True)



# ---------------- CONSUMER FACING DELIVERY PERFORMANCE ----------------
st.subheader("Consumer Facing Delivery Performance (Delivered Orders Only)")

consumer_delivery_df = filtered_df[
    filtered_df["Final Status"].astype(str).str.lower() == "delivered"
]

consumer_delivery_agg = (
    consumer_delivery_df
    .groupby(["Zone", "Consumer to Delivery TAT Status"])
    .size()
    .reset_index(name="Count")
)

consumer_delivery_agg["Percentage"] = (
    consumer_delivery_agg["Count"] /
    consumer_delivery_agg.groupby("Zone")["Count"].transform("sum") * 100
).round(1)

consumer_delivery_fig = px.bar(
    consumer_delivery_agg,
    x="Zone",
    y="Count",
    color="Consumer to Delivery TAT Status",
    text=consumer_delivery_agg["Percentage"].astype(str) + "%",
    title="Consumer Facing Placed to Delivery TAT (Delivered Orders)"
)

consumer_delivery_fig.update_traces(
    hovertemplate="Count: %{y}<extra></extra>"
)

st.plotly_chart(consumer_delivery_fig, use_container_width=True)

# ---------------- IN-TRANSIT SLA PERFORMANCE ----------------
st.subheader("In-Transit SLA Performance")

intransit_df = filtered_df[
    filtered_df["Final Status"].str.lower().str.startswith("in-transit")
]

intransit_agg = (
    intransit_df
    .groupby("Pickup to Delivery TAT Status")
    .size()
    .reset_index(name="Count")
)

intransit_agg["Percentage"] = (
    intransit_agg["Count"] / intransit_agg["Count"].sum() * 100
).round(1)

intransit_fig = px.bar(
    intransit_agg,
    x="Pickup to Delivery TAT Status",
    y="Count",
    text=intransit_agg["Percentage"].astype(str) + "%",
    title="In-Transit Orders SLA Status (Pickup to Delivery)"
)

intransit_fig.update_traces(
    hovertemplate="Count: %{y}<extra></extra>"
)

st.plotly_chart(intransit_fig, use_container_width=True)



# ---------------- SHIPPING PROVIDER PERFORMANCE ----------------
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

selected_provider = st.plotly_chart(
    provider_fig,
    use_container_width=True
)


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

st.plotly_chart(provider_sla_fig, use_container_width=True)


# Courier breakup
st.subheader("Courier Split for Selected Provider")

provider = st.selectbox(
    "Select Shipping Provider",
    provider_perf["Shipping provider"]
)

courier_split = (
    filtered_df[filtered_df["Shipping provider"] == provider]
    .groupby("Shipping Courier")
    .size()
    .reset_index(name="Count")
)

courier_pie = px.pie(
    courier_split,
    names="Shipping Courier",
    values="Count",
    title=f"Courier Split – {provider}"
)

st.plotly_chart(courier_pie, use_container_width=True)

st.subheader("Courier SLA Performance")

courier_sla = (
    filtered_df
    .groupby(["Shipping Courier", "Placed to Delivery TAT Status"])
    .size()
    .reset_index(name="Count")
)

courier_sla_fig = px.bar(
    courier_sla,
    x="Shipping Courier",
    y="Count",
    color="Placed to Delivery TAT Status",
    title="Courier-wise In-TAT vs Out-TAT",
    text="Count"
)

courier_sla_fig.update_traces(
    hovertemplate="Count: %{y}<extra></extra>"
)

st.plotly_chart(courier_sla_fig, use_container_width=True)

st.subheader("Zone SLA Distribution (Delivered Orders)")

zone_sla = (
    filtered_df[filtered_df["Final Status"].str.lower() == "delivered"]
    .groupby(["Zone", "Placed to Delivery TAT Status"])
    .size()
    .reset_index(name="Count")
)

zone = st.selectbox("Select Zone", zone_sla["Zone"].unique())

zone_pie_df = zone_sla[zone_sla["Zone"] == zone]

zone_pie = px.pie(
    zone_pie_df,
    names="Placed to Delivery TAT Status",
    values="Count",
    title=f"SLA Split – {zone}"
)

zone_pie.update_traces(
    hovertemplate="Status: %{label}<br>Count: %{value}<extra></extra>"
)

st.plotly_chart(zone_pie, use_container_width=True)



# ---------------- DATA PREVIEW ----------------
st.subheader("Filtered Data Preview")
st.dataframe(filtered_df, use_container_width=True)
#python -m streamlit run app.py
#python -m venv venv
#.\venv\Scripts\Activate.ps1

#git add requirements.txt
#git commit -m "Add requirements"
#git push



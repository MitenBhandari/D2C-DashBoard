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

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.header("Filters")

date_range = st.sidebar.date_input(
    "Devx Order Date Range",
    [
        df["Devx Order Date (Date)"].min(),
        df["Devx Order Date (Date)"].max()
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

# ---------------- APPLY FILTERS ----------------
filtered_df = df.copy()

if date_range:
    filtered_df = filtered_df[
        (filtered_df["Devx Order Date (Date)"] >= pd.to_datetime(date_range[0])) &
        (filtered_df["Devx Order Date (Date)"] <= pd.to_datetime(date_range[1]))
    ]

if facility_filter:
    filtered_df = filtered_df[filtered_df["Facility"].isin(facility_filter)]

if courier_filter:
    filtered_df = filtered_df[filtered_df["Shipping Courier"].isin(courier_filter)]

if zone_filter:
    filtered_df = filtered_df[filtered_df["Zone"].isin(zone_filter)]

# ---------------- KPI CALCULATIONS ----------------
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

# In-Transit SLA
intransit_in_tat = (
    filtered_df.loc[is_intransit, "Placed to Delivery TAT Status"]
    .astype(str)
    .str.lower()
    .eq("intat")
    .sum()
)

intransit_out_tat = (
    filtered_df.loc[is_intransit, "Placed to Delivery TAT Status"]
    .astype(str)
    .str.lower()
    .eq("outtat")
    .sum()
)


# ---------------- DASHBOARD HEADER ----------------
st.title("Order Operations Dashboard")

row1 = st.columns(5)
row1[0].metric("Total Orders", total_orders)
row1[1].metric("Delivered", delivered_orders)
row1[2].metric("In Transit", intransit_orders)
row1[3].metric("RTO", rto_orders)

row2 = st.columns(4)
row2[0].metric("Delivered In-TAT", delivered_in_tat)
row2[1].metric("Delivered Out-TAT", delivered_out_tat)
row2[2].metric("In-Transit In-TAT", intransit_in_tat)
row2[3].metric("In-Transit Out-TAT", intransit_out_tat)

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
    .groupby("Placed to Delivery TAT Status")
    .size()
    .reset_index(name="Count")
)

intransit_agg["Percentage"] = (
    intransit_agg["Count"] / intransit_agg["Count"].sum() * 100
).round(1)

intransit_fig = px.bar(
    intransit_agg,
    x="Placed to Delivery TAT Status",
    y="Count",
    text=intransit_agg["Percentage"].astype(str) + "%",
    title="In-Transit Orders SLA Status"
)

intransit_fig.update_traces(
    hovertemplate="Count: %{y}<extra></extra>"
)

st.plotly_chart(intransit_fig, use_container_width=True)



# ---------------- SHIPPING PROVIDER PERFORMANCE ----------------
st.subheader("Shipping Provider Performance")

provider_perf = (
    filtered_df
    .groupby("Shipping provider")
    .size()
    .reset_index(name="Count")
)

provider_fig = px.bar(
    provider_perf,
    x="Shipping provider",
    y="Count",
    title="Orders by Shipping Provider"
)

selected_provider = st.plotly_chart(
    provider_fig,
    use_container_width=True
)

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


# ---------------- DATA PREVIEW ----------------
st.subheader("Filtered Data Preview")
st.dataframe(filtered_df, use_container_width=True)
#streamlit run app.py


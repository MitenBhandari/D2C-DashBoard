import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Logistics TAT Analyzer", layout="wide")
st.title("📦 Logistics TAT Pivot Dashboard")

# ===============================
# Load File
# ===============================
file_path = "Output_Report.csv"

if not os.path.exists(file_path):
    st.error("❌ Output_Report.csv not found in project folder")
    st.stop()

df = pd.read_csv(file_path)

# ===============================
# Clean Data
# ===============================
df.columns = df.columns.str.strip()

df["Final Status"] = df["Final Status"].astype(str).str.strip().str.upper()
df["Reshipped"] = df["Reshipped"].astype(str).str.strip().str.upper()

tat_status_cols = [
    "Dispatch TAT Status",
    "Placed to Delivery TAT Status",
    "Consumer to Delivery TAT Status",
    "Pickup to Delivery TAT Status"
]

for col in tat_status_cols:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.upper()

# ===============================
# Date Filter (UNICOM Date)
# ===============================
df["UC Order Date (Date)"] = pd.to_datetime(df["UC Order Date (Date)"], errors="coerce")

min_date = df["UC Order Date (Date)"].min()
max_date = df["UC Order Date (Date)"].max()

start_date, end_date = st.date_input(
    "Select UNICOM Date Range",
    [min_date, max_date]
)

df = df[
    (df["UC Order Date (Date)"] >= pd.to_datetime(start_date)) &
    (df["UC Order Date (Date)"] <= pd.to_datetime(end_date))
]

# ===============================
# Constants
# ===============================
DELIVERED = ["DELIVERED"]
TRANSIT = [
    "IN-TRANSIT",
    "IN-TRANSIT, DAMAGED/LOST",
    "IN-TRANSIT, DELAYED",
    "OUTFORPICKUP"
]

INTAT = ["INTAT"]
OUTTAT = ["OUTTAT"]

# ===============================
# Helper Functions
# ===============================
def tat_pivot(df, group_col, tat_col):
    base = df.groupby(group_col).agg(
        Total_Orders=("UNICOM Order ID", "count")
    )

    base["% Volume"] = (base["Total_Orders"] / base["Total_Orders"].sum()) * 100

    for label, statuses in {
        "Delivered": DELIVERED,
        "Transit": TRANSIT
    }.items():
        base[label] = df[df["Final Status"].isin(statuses)] \
            .groupby(group_col)["UNICOM Order ID"].count()

        base[f"{label} InTAT"] = df[
            (df["Final Status"].isin(statuses)) &
            (df[tat_col].isin(INTAT))
        ].groupby(group_col)["UNICOM Order ID"].count()

        base[f"{label} OutTAT"] = df[
            (df["Final Status"].isin(statuses)) &
            (df[tat_col].isin(OUTTAT))
        ].groupby(group_col)["UNICOM Order ID"].count()

    base = base.fillna(0).reset_index()

    # Percentages
    for col in base.columns:
        if col.endswith("InTAT") or col.endswith("OutTAT"):
            base[f"{col} %"] = (base[col] / base["Total_Orders"] * 100).round(2)

    base["% Volume"] = base["% Volume"].round(2)

    return base.sort_values("Total_Orders", ascending=False)

# ===============================
# Pivot 1: Placed / Consumer / Pickup
# ===============================
tat_type = st.selectbox(
    "Select TAT Type",
    [
        "Placed to Delivery TAT",
        "Consumer to Delivery TAT",
        "Pickup to Delivery TAT"
    ]
)

pivot_column = st.selectbox(
    "Select Pivot Variable",
    df.columns.tolist()
)

tat_map = {
    "Placed to Delivery TAT": "Placed to Delivery TAT Status",
    "Consumer to Delivery TAT": "Consumer to Delivery TAT Status",
    "Pickup to Delivery TAT": "Pickup to Delivery TAT Status"
}

pivot_df = tat_pivot(df, pivot_column, tat_map[tat_type])

st.subheader(f"📊 {tat_type} Pivot | {pivot_column}")
st.dataframe(pivot_df, use_container_width=True)

# ===============================
# Pivot 2: Dispatch TAT (Facility)
# ===============================
st.subheader("🚚 Dispatch TAT – Facility Level")

dispatch = df.groupby("Facility").agg(
    Total_Orders=("UNICOM Order ID", "count")
)

dispatch["% Volume"] = dispatch["Total_Orders"] / dispatch["Total_Orders"].sum() * 100

dispatch["InTAT"] = df[df["Dispatch TAT Status"].isin(INTAT)] \
    .groupby("Facility")["UNICOM Order ID"].count()

dispatch["OutTAT"] = df[df["Dispatch TAT Status"].isin(OUTTAT)] \
    .groupby("Facility")["UNICOM Order ID"].count()

dispatch = dispatch.fillna(0).reset_index()

dispatch["InTAT %"] = (dispatch["InTAT"] / dispatch["Total_Orders"] * 100).round(2)
dispatch["OutTAT %"] = (dispatch["OutTAT"] / dispatch["Total_Orders"] * 100).round(2)
dispatch["% Volume"] = dispatch["% Volume"].round(2)

st.dataframe(dispatch, use_container_width=True)

# ===============================
# Pivot 3: Shipping Provider × Courier × Zone
# ===============================
st.subheader("📦 Pickup to Delivery TAT by Shipping Provider & Courier (Zone Wise)")

zone_pivot = (
    df.groupby(
        ["Shipping provider", "Shipping Courier", "Zone"]
    )
    .agg(
        Total_Orders=("UNICOM Order ID", "count"),
        InTAT=("Pickup to Delivery TAT Status", lambda x: (x == "INTAT").sum()),
        OutTAT=("Pickup to Delivery TAT Status", lambda x: (x == "OUTTAT").sum())
    )
    .reset_index()
)

zone_pivot["InTAT %"] = (zone_pivot["InTAT"] / zone_pivot["Total_Orders"] * 100).round(2)
zone_pivot["OutTAT %"] = (zone_pivot["OutTAT"] / zone_pivot["Total_Orders"] * 100).round(2)

st.dataframe(zone_pivot, use_container_width=True)

# ===============================
# Pivot 4: Pickup to Delivery TAT – Pincode × Provider × Courier
# ===============================
st.subheader("📍 Pickup to Delivery TAT – Pincode Level (Provider × Courier | Delivered Only)")

# Filter Delivered Orders Only
delivered_df = df[df["Final Status"] == "DELIVERED"]

# Total delivered orders (for % volume calculation)
total_delivered_orders = delivered_df["UNICOM Order ID"].count()

# Grouping
pincode_provider_courier = (
    delivered_df.groupby(
        ["Pincode", "Shipping provider", "Shipping Courier"]
    )
    .agg(
        Total_Orders=("UNICOM Order ID", "count"),
        InTAT_Delivered=("Pickup to Delivery TAT Status", lambda x: (x == "INTAT").sum()),
        OutTAT_Delivered=("Pickup to Delivery TAT Status", lambda x: (x == "OUTTAT").sum())
    )
    .reset_index()
)

# Percent Calculations
pincode_provider_courier["% Vol"] = (
    pincode_provider_courier["Total_Orders"] / total_delivered_orders * 100
).round(2)

pincode_provider_courier["InTAT %"] = (
    pincode_provider_courier["InTAT_Delivered"] /
    pincode_provider_courier["Total_Orders"] * 100
).round(2)

pincode_provider_courier["OutTAT %"] = (
    pincode_provider_courier["OutTAT_Delivered"] /
    pincode_provider_courier["Total_Orders"] * 100
).round(2)

# Sort for readability
pincode_provider_courier = pincode_provider_courier.sort_values(
    ["Pincode", "Shipping provider", "Total_Orders"],
    ascending=[True, True, False]
)

st.dataframe(pincode_provider_courier, use_container_width=True)



#python -m streamlit run int.py
#python -m venv venv
#.\venv\Scripts\Activate.ps1

#git add Consolidated_Report.xlsx Output_Report.csv app.py input.py
#git commit -m "Add All"
#git push

#git add app.py 
#git commit -m "Add All"
#git push
import pandas as pd
import numpy as np
from datetime import datetime

# ---------------- CONFIG ----------------
INPUT_FILE = "Consolidated_Report.xlsx"
OUTPUT_FILE = "Output_Report.csv"

TODAY = pd.to_datetime(datetime.today().date())

# ---------------- LOAD ----------------
df = pd.read_excel(INPUT_FILE)

# ---------------- FILTER PICKED UP ORDERS ----------------
df = df[df["Order Dispatched"].astype(str).str.lower() == "yes"].copy()
# ---------------- REMOVE BLANK FINAL STATUS ----------------
df = df[
    df["Final Status"]
    .notna() &
    df["Final Status"]
    .astype(str)
    .str.strip()
    .ne("")
].copy()


# ---------------- KEEP ONLY REQUIRED COLUMNS ----------------
required_columns = [
    "Devx Order ID",
    "Devx Order Date (Date)",
    "Devx Order Status",
    "Payment method",
    "UC Order Date (Date)",
    "Ideal Dispatch Date",
    "Ideal Dispatch Date(R)",
    "Facility",
    "Series",
    "Facility Type",
    "Shipping Address City",
    "Order Pincode",
    "UC Order Status",
    "UC Shipping Package Status",
    "Dispatch Date (Date)",
    "UNICOM Order ID",
    "Shipping provider",
    "Shipping Courier",
    "Tracking No.",
    "Assigned Date_D",        
    "CP Order Status",
    "Pickup Date (Date)",
    "Delivery Date (Date)",
    "Final Status",
    "Zone"
]

df = df[required_columns]

# ---------------- DATE PARSING ----------------
date_cols = [
    "Devx Order Date (Date)",
    "UC Order Date (Date)",
    "Ideal Dispatch Date",
    "Pickup Date (Date)",
    "Delivery Date (Date)"
]

for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors="coerce")

# ---------------- WEEK CALCULATION (UC ORDER DATE) ----------------
df["Week"] = np.where(
    df["UC Order Date (Date)"].notna(),
    ((df["UC Order Date (Date)"].dt.day - 1) // 7) + 1,
    np.nan
)

# ---------------- PICKUP DATE FALLBACK (FACILITY BASED) ----------------

# Normalize Facility for comparison
df["Facility_Normalized"] = (
    df["Facility"]
    .astype(str)
    .str.lower()
    .str.replace(r"\s+", " ", regex=True)  # removes newlines & extra spaces
    .str.strip()
)


df["Effective Pickup Date"] = df["Pickup Date (Date)"]

# If Pickup Date is blank & Facility = warehouse → Assigned Date_D
df.loc[
    (df["Effective Pickup Date"].isna()) &
    (df["Facility_Normalized"] == "warehouse"),
    "Effective Pickup Date"
] = df["Assigned Date_D"]

# If Pickup Date is blank & Facility = dark store → Ideal Dispatch Date
df.loc[
    (df["Effective Pickup Date"].isna()) &
    (df["Facility_Normalized"] == "dark store"),
    "Effective Pickup Date"
] = df["Ideal Dispatch Date"]

# ---------------- FINAL PICKUP DATE SAFETY FALLBACK ----------------
df.loc[
    df["Effective Pickup Date"].isna(),
    "Effective Pickup Date"
] = df["Ideal Dispatch Date"]



# ---------------- DELIVERY DATE FALLBACK ----------------
df["Effective Delivery Date"] = df["Delivery Date (Date)"]
df.loc[df["Effective Delivery Date"].isna(), "Effective Delivery Date"] = TODAY

# ---------------- ZONE NORMALIZATION ----------------
df["Zone"] = df["Zone"].astype(str).str.strip().str.lower()

zone_map = {
    "a": 2,
    "b": 3,
    "c": 3,
    "d": 5,
    "e": 7,
    "sdd": 0,
    "ndd": 1
}

df["Calculated Ideal Delivery TAT"] = df["Zone"].map(zone_map)

# ---------------- IDEAL PLACED TO DELIVERY ----------------
df["Ideal Placed to Delivery TAT"] = df["Calculated Ideal Delivery TAT"]
df.loc[df["Zone"] != "sdd", "Ideal Placed to Delivery TAT"] += 1

# ---------------- CONSUMER PLACED TO DELIVERY ----------------
df["Consumer Placed to Delivery TAT"] = df["Ideal Placed to Delivery TAT"]
df.loc[df["Zone"].isin(["sdd", "ndd"]), "Consumer Placed to Delivery TAT"] += 1

# ---------------- DISPATCH TAT ----------------
df["Dispatch TAT"] = (
    df["Effective Pickup Date"] - df["Ideal Dispatch Date"]
).dt.days.clip(lower=0)


df["Dispatch TAT Status"] = np.where(
    df["Dispatch TAT"] > 1,
    "OutTAT",
    "InTAT"
)

# ---------------- PLACED TO DELIVERY ----------------
df["Placed to Delivery TAT"] = (
    df["Effective Delivery Date"] - df["Ideal Dispatch Date"]
).dt.days.clip(lower=0)


df["Placed to Delivery TAT Status"] = np.where(
    df["Placed to Delivery TAT"] > df["Ideal Placed to Delivery TAT"],
    "OutTAT",
    "InTAT"
)

# ---------------- CONSUMER TO DELIVERY STATUS ----------------
df["Consumer to Delivery TAT Status"] = np.where(
    df["Placed to Delivery TAT"] > df["Consumer Placed to Delivery TAT"],
    "OutTAT",
    "InTAT"
)

# ---------------- PICKUP TO DELIVERY ----------------
df["Pickup to Delivery TAT"] = (
    df["Effective Delivery Date"] - df["Effective Pickup Date"]
).dt.days.clip(lower=0)


df["Pickup to Delivery TAT Status"] = np.where(
    df["Pickup to Delivery TAT"] > df["Calculated Ideal Delivery TAT"],
    "OutTAT",
    "InTAT"
)

# ---------------- WRITE BACK RESOLVED PICKUP DATE ----------------
df["Pickup Date (Date)"] = df["Effective Pickup Date"]


# ---------------- CLEANUP ----------------
df.drop(
    columns=["Effective Pickup Date", "Effective Delivery Date", "Facility_Normalized"],
    inplace=True)

# ---------------- FORMAT DATE COLUMNS (DD-MM-YYYY) ----------------
date_format_cols = [
    "Devx Order Date (Date)",
    "UC Order Date (Date)",
    "Ideal Dispatch Date",
    "Ideal Dispatch Date(R)",
    "Dispatch Date (Date)",
    "Assigned Date_D",
    "Pickup Date (Date)",
    "Delivery Date (Date)"
]

for col in date_format_cols:
    if col in df.columns:
        df[col] = df[col].dt.strftime("%d-%m-%Y")



# ---------------- OUTPUT ----------------
df.to_csv(OUTPUT_FILE, index=False)

print("Final report generated successfully:", OUTPUT_FILE)

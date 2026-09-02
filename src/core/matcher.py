import pandas as pd
import numpy as np


def run_reconciliation(orders: pd.DataFrame, settlements: pd.DataFrame, bank: pd.DataFrame) -> tuple[pd.DataFrame, 
    pd.DataFrame, pd.DataFrame, pd.DataFrame, float]:

    #1. Multi Source Merged

    merged = pd.merge(orders, settlements, on = "order_id", how = "outer")
    merged = pd.merge(merged, bank, on = "utr", how = "outer")

   #2. Secure string to float Conversion & Schema Guarantee
    numeric_cols = ["merchant_amount", "gross_amount", "fee", "gst", "net_settled", "bank_credit"]

      # Ensure all expected financial columns exist in the DataFrame
    for col in numeric_cols:
        if col not in merged.columns:
            merged[col] = 0.0

      # Track rows with non-numeric strings (Dead Letter Queue)
    invalid_numeric_rows = pd.Series(False, index=merged.index)

    for col in numeric_cols:
        original = merged[col]
        converted = pd.to_numeric(original, errors="coerce")
        
        # Flag values that existed as strings but failed conversion
        invalid_values = converted.isna() & original.notna()
        invalid_numeric_rows |= invalid_values
        
        # Fill remaining valid NaNs (from outer join) with 0.0
        merged[col] = converted.fillna(0.0)

    # 3. Separate quarantined data from valid data
    data_errors = merged[invalid_numeric_rows].copy()
    merged = merged[~invalid_numeric_rows].copy()

    # Cash Forecaster(Unsettled)

    unsettled_mask = (merged["merchant_amount"] > 0) & (merged["net_settled"] == 0.0)
    unsettled = merged[unsettled_mask].copy()


    unsettled["expected_fee"] = unsettled["merchant_amount"] * 0.02
    unsettled["expected_gst"] = unsettled["expected_fee"] * 0.18
    unsettled["expected_payout"] = unsettled["merchant_amount"] - unsettled["expected_fee"] - unsettled["expected_gst"]

    total_expected_cash = round(unsettled["expected_payout"].sum(), 2)


    # Tax Matcher & Reconciliation Rules

    fully_settled = merged[~unsettled_mask].copy()

    is_clean = (
        np.isclose(fully_settled["merchant_amount"], fully_settled["gross_amount"])  &
        np.isclose(fully_settled["gst"], (fully_settled["fee"] * 0.18), atol = 0.05) &
        np.isclose(fully_settled["net_settled"], (fully_settled["gross_amount"] - fully_settled["fee"] - fully_settled["gst"])) &
        np.isclose(fully_settled["bank_credit"], fully_settled["net_settled"])
    )


    clean_matches = fully_settled[is_clean].copy()
    exceptions = fully_settled[~is_clean].copy()


    return clean_matches, exceptions, unsettled,data_errors, total_expected_cash 
    
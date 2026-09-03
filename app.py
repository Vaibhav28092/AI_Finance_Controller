import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Page Configuration
st.set_page_config(
    page_title="AI Finance Controller",
    layout="wide",
    initial_sidebar_state="collapsed" # Collapse sidebar by default for more space
)

# 2. Razorpay-Inspired CSS
st.markdown("""
    <style>
    /* Razorpay Blue Accents */
    .stButton>button { border-radius: 6px; }
    .stButton>button[kind="primary"] { background-color: #0253cc; color: white; }
    
    /* Clean up the Chat UI */
    .stChatMessage { border-radius: 8px; padding: 10px; margin-bottom: 10px; }
    
    /* Subtle Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
    }
    
    /* Dark Mode Fallbacks for Metrics */
    @media (prefers-color-scheme: dark) {
        div[data-testid="metric-container"] { background-color: #1e1e2e; border-color: #2a2a3c; }
    }
    </style>
""", unsafe_allow_html=True)

# 3. Environment & State
API_KEY = os.getenv("API_KEY", "Key_2026")
HEADERS = {"API-Key": API_KEY}
API_URL = "http://127.0.0.1:8000"

if "recon_data" not in st.session_state:
    st.session_state.recon_data = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "Hi! I am your AI Finance Controller. Upload a batch to begin."}]

# Helper: Convert DataFrame to CSV for downloading
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# 4. Top Header & Upload Bar
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/commons/8/89/Razorpay_logo.svg", width=120)
with col_title:
    st.header("Ledger Intelligence & Reconciliation Dashboard")

with st.expander("Upload Files", expanded=(st.session_state.recon_data is None)):

    up_c1, up_c2, up_c3, up_c4 = st.columns([2, 2, 2, 1])
    SUPPORTED = ["csv", "xlsx", "xls", "json", "parquet", "pdf"]
    file_orders = up_c1.file_uploader("Merchant Orders", type= SUPPORTED)
    file_sett = up_c2.file_uploader("Gateway Settlements", type= SUPPORTED)
    file_bank = up_c3.file_uploader("Bank Statement", type= SUPPORTED)
    
    if up_c4.button("Run AI Audit", use_container_width=True, type="primary"):
        if file_orders and file_sett and file_bank:

            # Added UI Spinner to mask Render's cold start delay
            with st.spinner("Waking up API backend... (This may take up to 50s on initial load)"):
                files = {
                    "orders": (file_orders.name, file_orders.getvalue(), "text/csv"),
                    "settlements": (file_sett.name, file_sett.getvalue(), "application/json"),
                    "bank": (file_bank.name, file_bank.getvalue(), "text/csv"),
                }
                res = requests.post(f"{API_URL}/api/reconcile", files=files, headers=HEADERS)
                if res.status_code == 200:
                    st.session_state.recon_data = res.json()
                    
                    # Help to Reset the chat on new upload
                    st.session_state.chat_history = [{"role": "assistant", "content": f"Batch {res.json()['batch_id'][:8]} processed! What would you like to investigate?"}]
                    st.rerun()
                else:
                    st.error(f"API Error: {res.text}")
        else:
            st.warning("Please upload all 3 files.")

# 5. Main Dashboard Split (Data Left, Chat Right)
if st.session_state.recon_data:
    data = st.session_state.recon_data
    stats = data["summary"]
    
    # Create the Side-by-Side Layout
    main_view, chat_view = st.columns([2.2, 1.2], gap="large")
    
    with main_view:
        # --- KPI Row ---
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Records", stats["total_records"])
        kpi2.metric("Clean Matches", stats["matched_by_code"])
        kpi3.metric("Exceptions", stats["exceptions_found"])
        kpi4.metric("Pending Cash", f"₹{stats['future_cash']:,.2f}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- Data Tabs ---
        tab_ai, tab_forecast, tab_dlq = st.tabs(["AI Exceptions", "Expected Settlements", "Corrupted Data"])
        
        with tab_ai:
            if data["ai_investigation_results"]:
                df_ex = pd.DataFrame(data["ai_investigation_results"])
                
                # Action Bar: Download Button
                st.download_button(
                    label="Download Exception Report",
                    data=convert_df_to_csv(df_ex),
                    file_name="ai_exceptions.csv",
                    mime="text/csv"
                )
                
                st.dataframe(df_ex, use_container_width=True, hide_index=True)
            else:
                st.success("Ledger is perfectly balanced. No exceptions.")

        with tab_forecast:
            if data["unsettled_data"]:
                df_un = pd.DataFrame(data["unsettled_data"])
                st.download_button("Download Pending Cash", convert_df_to_csv(df_un), "pending.csv", "text/csv")
                st.dataframe(df_un[["order_id", "merchant_amount", "gross_amount", "net_settled"]], use_container_width=True, hide_index=True)
            else:
                st.info("No pending cash flow.")

        with tab_dlq:
            if data["data_errors"]:
                df_err = pd.DataFrame(data["data_errors"])
                st.download_button("Download DLQ", convert_df_to_csv(df_err), "dlq_errors.csv", "text/csv")
                st.error("The following rows contained string corruptions and bypassed math processing.")
                st.dataframe(df_err, use_container_width=True)
            else:
                st.success("No corrupted strings detected.")

    with chat_view:
        st.markdown("### 🤖 FinOps Copilot")
        st.caption("Chat directly with this batch's data.")
        
        # Chat Window Container
        chat_container = st.container(height=500, border=True)
        
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        # Chat Input at the bottom of the column
        if prompt := st.chat_input("Ask about an order or UTR..."):

            # Update UI instantly
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            st.rerun() # Rerun to render user message in container

        # Handle API Call outside the prompt block to allow spinner rendering
        if st.session_state.chat_history[-1]["role"] == "user":
            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing..."):
                        payload = {"question": st.session_state.chat_history[-1]["content"], "batch_id": data["batch_id"]}
                        try:
                            res = requests.post(f"{API_URL}/api/chat", json=payload, headers=HEADERS)
                            if res.status_code == 200:
                                answer = res.json().get("answer", "Error retrieving answer.")
                                st.markdown(answer)
                                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                            else:
                                st.error("Failed to connect to AI.")
                        except Exception as e:
                            st.error("Backend offline.")
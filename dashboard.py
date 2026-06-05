import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Experimental Tests Dashboard", layout="wide")

st.title("🧪 Experimental Tests Summary")
st.markdown("Enter your reactor run data directly into the tables below. Your data is automatically synced to the cloud via Google Sheets.")

# --- 2. INITIALIZE GLOBAL VARIABLES & CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Updated Columns List
columns = [
    "Test No.", "Aim", "Mode","Start", "Duration(h)", "T_in (°C)", "RH_in %", 
    "Flow Rate_in(L/min)", "Sample ID", "Particle Size (mm)",
    "m_pre (g)", "m_post (g)", "Δm", 
    "t_re (h)", "T_re (°C)", "Regeneration Method", "Operator", "Raw Data"
]

reactor_names = ["Reactor 1", "Reactor 2", "Reactor 3", "Reactor 4", "Reactor 5"]
all_cloud_data = {}

# Initialize the dropdown options in session state
if "sample_options" not in st.session_state:
    st.session_state.sample_options = ["Zeolite13X beads (JL)"]
if "operator_options" not in st.session_state:
    st.session_state.operator_options = ["Operator 1"]

# --- 3. TABBED INTERFACE (Cloud Synced) ---
tabs = st.tabs(reactor_names)

for i, reactor in enumerate(reactor_names):
    with tabs[i]:
        st.subheader(f"📋 {reactor} Database")
        
        # 1. READ
        try:
            cloud_data = conn.read(worksheet=reactor, usecols=list(range(len(columns))))
            cloud_data = cloud_data.dropna(how="all")
            if cloud_data.empty:
                cloud_data = pd.DataFrame(columns=columns)
            else:
                cloud_data.columns = columns 
        except Exception:
            cloud_data = pd.DataFrame(columns=columns)

        # 2. EDIT
        edited_df = st.data_editor(
            cloud_data,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"editor_{reactor}",
            column_config={
                "Mode": st.column_config.SelectboxColumn("Mode", options=["🔴 Charging", "🟢 Discharging"], required=True),
                "Sample ID": st.column_config.SelectboxColumn("Sample ID", options=st.session_state.sample_options),
                "Operator": st.column_config.SelectboxColumn("Operator", options=st.session_state.operator_options),
                "Δm": st.column_config.NumberColumn("Δm", disabled=True) # Disable manual input
            }
        )
        
        # --- AUTOMATIC CALCULATION ---
        # Convert to numeric, calculate Δm immediately
        edited_df["m_pre (g)"] = pd.to_numeric(edited_df["m_pre (g)"], errors="coerce")
        edited_df["m_post (g)"] = pd.to_numeric(edited_df["m_post (g)"], errors="coerce")
        edited_df["Δm"] = edited_df["m_post (g)"] - edited_df["m_pre (g)"]

        # 3. WRITE (AUTO-SAVE)
        # We check if the data changed (excluding the Δm column, which we just calculated)
        if not edited_df.equals(cloud_data):
            conn.update(worksheet=reactor, data=edited_df)
            st.cache_data.clear() 
            st.success(f"✅ Data for {reactor} synced!")
            st.rerun() # Force rerun to show calculated Δm values
            
        all_cloud_data[reactor] = edited_df

st.divider()

# --- 4. MASS COMPARISON SUMMARY ---
st.subheader("📊 Mass Comparison Summary")

all_data = pd.concat(all_cloud_data.values(), ignore_index=True)

# FILTER LOGIC: Include only if Test No. exists AND both masses exist
summary_data = all_data.dropna(subset=["Test No.", "m_pre (g)", "m_post (g)"])

if not summary_data.empty:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(summary_data[["Test No.", "m_pre (g)", "m_post (g)", "Δm"]], use_container_width=True, hide_index=True)
    # ... [Rest of your Plotly code]
else:
    st.info("No complete test runs logged yet (Missing Mass data).")

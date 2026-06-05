import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Experimental Tests Dashboard", layout="wide")

st.title("🧪 Experimental Tests Summary")
st.markdown("Enter your reactor run data directly into the tables below. Your data is automatically synced to the cloud via Google Sheets.")

# --- 2. INITIALIZE GOOGLE SHEETS CONNECTION ---
# Establish connection to the Google Sheet defined in .streamlit/secrets.toml
conn = st.connection("gsheets", type=GSheetsConnection)

columns = [
    "Test No.", "Start", "Duration(h)", "T_in (°C)", "RH_in %", 
    "Flow Rate_in(L/min)", "Sample ID", "Particle Size (mm)",
    "Pre-Run Mass (g)", "Post-Run Mass (g)", "Δm", "Operator", 
    "Regeneration Method", "Raw Data"
]

reactor_names = ["Reactor 1", "Reactor 2", "Reactor 3", "Reactor 4", "Reactor 5"]

# Dictionary to hold the latest data for the overall summary section
all_cloud_data = {}

# --- 3. TABBED INTERFACE (Cloud Synced) ---
tabs = st.tabs(reactor_names)

for i, reactor in enumerate(reactor_names):
    with tabs[i]:
        st.subheader(f"📋 {reactor} Database")
        
        # 1. READ: Pull existing data from the Google Sheet tab
        try:
            cloud_data = conn.read(worksheet=reactor, usecols=list(range(len(columns))))
            # Drop any empty rows that Google Sheets occasionally sends over
            cloud_data = cloud_data.dropna(how="all")
        except Exception:
            # If the worksheet is completely blank, initialize with empty columns
            cloud_data = pd.DataFrame(columns=columns)
            
        all_cloud_data[reactor] = cloud_data

        # 2. EDIT: Display the interactive table
        edited_df = st.data_editor(
            cloud_data,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"editor_{reactor}",
            column_config={
                "Test No.": st.column_config.TextColumn(
                    "Test No.",
                    help="Enter test number with status, e.g., '🔴 - 1' or '🟢 - 2'"
                )
            }
        )
        
        st.markdown("**Legend:** 🔴 Charging | 🟢 Discharging *(Copy and paste the dots directly into the Test No. column)*")

        # 3. WRITE (AUTO-SAVE): If the user makes a change, silently update the Google Sheet
        if not edited_df.equals(cloud_data):
            conn.update(worksheet=reactor, data=edited_df)
            st.success(f"✅ Data for {reactor} successfully synced to the cloud!")
            all_cloud_data[reactor] = edited_df # Update local dictionary for summary

st.divider()

# --- 4. MASS COMPARISON SUMMARY ---
st.subheader("📊 Mass Comparison Summary")
st.markdown("Comparison of Pre-Run Mass, Post-Run Mass, and Δm across all recorded test runs.")

# Combine all synced dataframes for the summary
all_data = pd.concat(all_cloud_data.values(), ignore_index=True)

# Filter out empty rows (where Test No. hasn't been entered yet)
summary_data = all_data.dropna(subset=["Test No."])

if not summary_data.empty:
    # Safely convert mass columns to numeric for visualization
    for col in ["Pre-Run Mass (g)", "Post-Run Mass (g)", "Δm"]:
        summary_data[col] = pd.to_numeric(summary_data[col], errors="coerce")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display isolated dataframe for mass comparison
        mass_df = summary_data[["Test No.", "Pre-Run Mass (g)", "Post-Run Mass (g)", "Δm"]]
        st.dataframe(mass_df, use_container_width=True, hide_index=True)
        
    with col2:
        # Visual Bar Chart Comparison
        melted_df = summary_data.melt(
            id_vars=["Test No."], 
            value_vars=["Pre-Run Mass (g)", "Post-Run Mass (g)"],
            var_name="Measurement Phase", 
            value_name="Mass (g)"
        )
        fig = px.bar(
            melted_df, 
            x="Test No.", 
            y="Mass (g)", 
            color="Measurement Phase", 
            barmode="group",
            title="Pre vs Post Run Mass by Test"
        )
        # Force the x-axis to be categorical so it displays the emojis properly
        fig.update_xaxes(type='category')
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No test runs logged yet. Add data above with a valid 'Test No.' to view the mass comparison.")
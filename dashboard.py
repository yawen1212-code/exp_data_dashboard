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

columns = [
    "Test No.", "Aim" "Mode","Start", "Duration(h)", "T_in (°C)", "RH_in %", 
    "Flow Rate_in(L/min)", "Sample ID", "Particle Size (mm)",
    "m_pre (g)", "m_post (g)", "Δm", 
    "t_re (h)", "T_re (°C)", "Regeneration Method" "Operator", "Raw Data"
]

reactor_names = ["Reactor 1", "Reactor 2", "Reactor 3", "Reactor 4", "Reactor 5"]
all_cloud_data = {}

# Initialize the Sample ID dropdown options in session state
if "sample_options" not in st.session_state:
    st.session_state.sample_options = ["Zeolite13X beads (JL)"]

# --- 3. TABBED INTERFACE (Cloud Synced) ---
tabs = st.tabs(reactor_names)

for i, reactor in enumerate(reactor_names):
    with tabs[i]:
        st.subheader(f"📋 {reactor} Database")
        
        # 1. READ: Pull existing data from the Google Sheet tab
        try:
            cloud_data = conn.read(worksheet=reactor, usecols=list(range(len(columns))))
            cloud_data = cloud_data.dropna(how="all")
            
            if cloud_data.empty:
                cloud_data = pd.DataFrame(columns=columns)
            else:
                cloud_data.columns = columns 
                
            # AUTO-LEARNING: Add any existing Sample IDs from the database to our dropdown list
            if "Sample ID" in cloud_data.columns:
                existing_samples = cloud_data["Sample ID"].dropna().unique()
                for sample in existing_samples:
                    if sample not in st.session_state.sample_options and sample != "":
                        st.session_state.sample_options.append(sample)
                        
        except Exception:
            cloud_data = pd.DataFrame(columns=columns)

        # 2. QUICK-ADD TOOL: UI to manually add new Sample IDs
        with st.expander("➕ Need to add a new Sample ID?"):
            new_sample = st.text_input("Type the new Sample ID label here:", key=f"new_sample_{reactor}")
            if st.button("Add to Dropdown Options", key=f"add_btn_{reactor}"):
                if new_sample and new_sample not in st.session_state.sample_options:
                    st.session_state.sample_options.append(new_sample)
                    st.success(f"'{new_sample}' added to the dropdown!")
                    st.rerun() # Refresh the app to update the table immediately

        # 3. EDIT: Display the interactive table
        edited_df = st.data_editor(
            cloud_data,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"editor_{reactor}",
            column_config={
                "Mode": st.column_config.SelectboxColumn(
                    "Mode",
                    help="Select the operational mode",
                    options=["🔴 Charging", "🟢 Discharging"],
                    required=True
                ),
                "Sample ID": st.column_config.SelectboxColumn(
                    "Sample ID",
                    help="Select the material sample from the list",
                    options=st.session_state.sample_options,
                    required=True
                )
            }
        )

        # 4. WRITE (AUTO-SAVE): If the user makes a change, silently update the Google Sheet
        if not edited_df.equals(cloud_data):
            conn.update(worksheet=reactor, data=edited_df)
            
            # Clear cache so the fresh data appears on refresh
            st.cache_data.clear() 
            
            st.success(f"✅ Data for {reactor} successfully synced to the cloud!")
            all_cloud_data[reactor] = edited_df

st.divider()

# --- 4. MASS COMPARISON SUMMARY ---
st.subheader("📊 Mass Comparison Summary")
st.markdown("Comparison of Pre-Run Mass, Post-Run Mass, and Δm across all recorded test runs.")

# Combine all synced dataframes for the summary
all_data = pd.concat(all_cloud_data.values(), ignore_index=True)

# Filter out empty rows (where Test No. hasn't been entered yet)
summary_data = all_data.dropna(subset=["Test No."])

if not summary_data.empty:
    for col in ["Pre-Run Mass (g)", "Post-Run Mass (g)", "Δm"]:
        summary_data[col] = pd.to_numeric(summary_data[col], errors="coerce")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display isolated dataframe for mass comparison
        mass_df = summary_data[["Test No.", "Mode", "Sample ID", "Pre-Run Mass (g)", "Post-Run Mass (g)", "Δm"]]
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
        fig.update_xaxes(type='category')
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No test runs logged yet. Add data above with a valid 'Test No.' to view the mass comparison.")

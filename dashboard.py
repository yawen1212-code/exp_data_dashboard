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
        
        # 1. READ: Pull existing data from the Google Sheet tab
        try:
            cloud_data = conn.read(worksheet=reactor, usecols=list(range(len(columns))))
            cloud_data = cloud_data.dropna(how="all")
            
            if cloud_data.empty:
                cloud_data = pd.DataFrame(columns=columns)
            else:
                cloud_data.columns = columns 
                
            # AUTO-LEARNING: Add any existing Sample IDs or Operators from the database to our dropdown lists
            if "Sample ID" in cloud_data.columns:
                for sample in cloud_data["Sample ID"].dropna().unique():
                    if sample not in st.session_state.sample_options and sample != "":
                        st.session_state.sample_options.append(sample)
            
            if "Operator" in cloud_data.columns:
                for operator in cloud_data["Operator"].dropna().unique():
                    if operator not in st.session_state.operator_options and operator != "":
                        st.session_state.operator_options.append(operator)
                        
        except Exception:
            cloud_data = pd.DataFrame(columns=columns)

        # 2. LABEL MANAGER: UI to manually add or delete Dropdown Labels
        with st.expander("⚙️ Manage Dropdown Labels"):
            col_sample, col_operator = st.columns(2)
            
            # --- Sample ID Manager ---
            with col_sample:
                st.markdown("**🧪 Manage Sample IDs**")
                # Add
                new_sample = st.text_input("Add new Sample ID:", key=f"new_sample_{reactor}")
                if st.button("Add Sample", key=f"add_samp_btn_{reactor}"):
                    if new_sample and new_sample not in st.session_state.sample_options:
                        st.session_state.sample_options.append(new_sample)
                        st.rerun()
                # Delete
                del_sample = st.selectbox("Select Sample ID to remove:", st.session_state.sample_options, key=f"del_sample_{reactor}")
                if st.button("Delete Sample", key=f"del_samp_btn_{reactor}"):
                    if del_sample in st.session_state.sample_options:
                        st.session_state.sample_options.remove(del_sample)
                        st.rerun()

            # --- Operator Manager ---
            with col_operator:
                st.markdown("**🧑‍🔬 Manage Operators**")
                # Add
                new_operator = st.text_input("Add new Operator:", key=f"new_operator_{reactor}")
                if st.button("Add Operator", key=f"add_op_btn_{reactor}"):
                    if new_operator and new_operator not in st.session_state.operator_options:
                        st.session_state.operator_options.append(new_operator)
                        st.rerun()
                # Delete
                del_operator = st.selectbox("Select Operator to remove:", st.session_state.operator_options, key=f"del_operator_{reactor}")
                if st.button("Delete Operator", key=f"del_op_btn_{reactor}"):
                    if del_operator in st.session_state.operator_options:
                        st.session_state.operator_options.remove(del_operator)
                        st.rerun()

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
                ),
                "Operator": st.column_config.SelectboxColumn(
                    "Operator",
                    help="Select the operator from the list",
                    options=st.session_state.operator_options,
                    required=True
                )
            }
        )

        # 4. WRITE (AUTO-SAVE): If the user makes a change, calculate Δm and update Google Sheet
        if not edited_df.equals(cloud_data):
            # --- AUTOMATIC CALCULATION ---
            # Ensure mass columns are numeric for calculation
            edited_df["m_pre (g)"] = pd.to_numeric(edited_df["m_pre (g)"], errors="coerce")
            edited_df["m_post (g)"] = pd.to_numeric(edited_df["m_post (g)"], errors="coerce")
            
            # Apply the formula: Δm = m_post - m_pre
            edited_df["Δm"] = edited_df["m_post (g)"] - edited_df["m_pre (g)"]
            
            # Sync to Google Sheets
            conn.update(worksheet=reactor, data=edited_df)
            
            # Clear cache and trigger UI refresh
            st.cache_data.clear() 
            st.success(f"✅ Data for {reactor} synced & Δm calculated!")
            all_cloud_data[reactor] = edited_df

st.divider()

# --- 4. MASS COMPARISON SUMMARY ---
st.subheader("📊 Mass Comparison Summary")
st.markdown("Comparison of pre-run mass, post-run mass, and Δm across all recorded test runs.")

# Combine all synced dataframes for the summary
if all_cloud_data:
    all_data = pd.concat(all_cloud_data.values(), ignore_index=True)
else:
    all_data = pd.DataFrame(columns=columns)

# Filter out empty rows (where Test No. hasn't been entered yet)
summary_data = all_data.dropna(subset=["Test No."])

if not summary_data.empty:
    for col in ["m_pre (g)", "m_post (g)", "Δm"]:
        if col in summary_data.columns:
            summary_data[col] = pd.to_numeric(summary_data[col], errors="coerce")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display isolated dataframe for mass comparison
        mass_df = summary_data[["Test No.", "Mode", "Sample ID", "m_pre (g)", "m_post (g)", "Δm"]]
        st.dataframe(mass_df, use_container_width=True, hide_index=True)
        
    with col2:
        # Visual Bar Chart Comparison
        melted_df = summary_data.melt(
            id_vars=["Test No."], 
            value_vars=["m_pre (g)", "m_post (g)"],
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

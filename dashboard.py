import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIG & INIT ---
st.set_page_config(page_title="Experimental Tests Dashboard", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

columns = [
    "Test No.", "Aim", "Mode", "Start", "Duration(h)", "T_in (°C)", "RH_in %", 
    "Flow Rate_in(L/min)", "Sample ID", "Particle Size (mm)",
    "m_pre (g)", "m_post (g)", "Δm", 
    "t_re (h)", "T_re (°C)", "Regeneration Method", "Operator", "Raw Data"
]

reactor_names = ["Reactor 1", "Reactor 2", "Reactor 3", "Reactor 4", "Reactor 5"]

if "sample_options" not in st.session_state:
    st.session_state.sample_options = ["Zeolite13X beads (JL)"]
if "operator_options" not in st.session_state:
    st.session_state.operator_options = ["Operator 1"]

# --- 2. TABBED INTERFACE ---
tabs = st.tabs(reactor_names)
all_cloud_data = {}

for i, reactor in enumerate(reactor_names):
    with tabs[i]:
        st.subheader(f"📋 {reactor} Database")
        
        # 1. READ
        try:
            cloud_data = conn.read(worksheet=reactor)
            if cloud_data.empty:
                cloud_data = pd.DataFrame(columns=columns)
            else:
                cloud_data = cloud_data.reindex(columns=columns)
        except Exception:
            cloud_data = pd.DataFrame(columns=columns)

        # 2. LABEL MANAGER (RESTORED)
        with st.expander("⚙️ Manage Dropdown Labels"):
            c1, c2 = st.columns(2)
            with c1:
                new_s = st.text_input("Add Sample", key=f"s_{reactor}")
                if st.button("Add", key=f"add_s_{reactor}") and new_s:
                    st.session_state.sample_options.append(new_s)
                    st.rerun()
                if st.button("Delete Selected", key=f"del_s_{reactor}"):
                    st.session_state.sample_options.remove(st.selectbox("Select", st.session_state.sample_options, key="sel_s"))
                    st.rerun()
            with c2:
                new_o = st.text_input("Add Operator", key=f"o_{reactor}")
                if st.button("Add", key=f"add_o_{reactor}") and new_o:
                    st.session_state.operator_options.append(new_o)
                    st.rerun()

        # 3. EDIT
        edited_df = st.data_editor(
            cloud_data,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Mode": st.column_config.SelectboxColumn(options=["🔴 Charging", "🟢 Discharging"]),
                "Sample ID": st.column_config.SelectboxColumn(options=st.session_state.sample_options),
                "Operator": st.column_config.SelectboxColumn(options=st.session_state.operator_options),
                "Δm": st.column_config.NumberColumn(disabled=True)
            }
        )
        
        # 4. CALC & WRITE
        edited_df["m_pre (g)"] = pd.to_numeric(edited_df["m_pre (g)"], errors="coerce")
        edited_df["m_post (g)"] = pd.to_numeric(edited_df["m_post (g)"], errors="coerce")
        edited_df["Δm"] = edited_df["m_post (g)"] - edited_df["m_pre (g)"]
        
        if not edited_df.equals(cloud_data):
            conn.update(worksheet=reactor, data=edited_df)
            st.success("Synced!")
            st.rerun()
            
        all_cloud_data[reactor] = edited_df

# --- 3. MASS SUMMARY (RESTORED) ---
st.divider()
st.subheader("📊 Mass Comparison Summary")
all_data = pd.concat(all_cloud_data.values(), ignore_index=True).dropna(subset=["Test No.", "m_pre (g)", "m_post (g)"])

if not all_data.empty:
    st.dataframe(all_data[["Test No.", "m_pre (g)", "m_post (g)", "Δm"]], use_container_width=True)
    fig = px.bar(all_data, x="Test No.", y=["m_pre (g)", "m_post (g)"], barmode="group")
    st.plotly_chart(fig)

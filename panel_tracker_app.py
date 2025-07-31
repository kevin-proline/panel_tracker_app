
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

st.image("logo.png", width=200)


st.set_page_config(page_title="Panel Tracker", layout="wide")

st.title("📦 Panel Demand vs. Delivery Tracker")

# --- Upload Section ---
bom_file = st.file_uploader("Upload BOM Excel File", type=["xlsx"])
deliv_file = st.file_uploader("Upload Deliveries Excel File", type=["xlsx"])
build_file = st.file_uploader("Upload Build Plan Excel File", type=["xlsx"])

if bom_file and deliv_file and build_file:
    df_bom = pd.read_excel(bom_file)
    df_deliv = pd.read_excel(deliv_file)
    df_build = pd.read_excel(build_file)

    # --- Clean Part Numbers ---
    df_bom['Part Number'] = df_bom['Part Number'].astype(str).str.strip().str.upper()
    df_deliv['Part Number'] = df_deliv['Part Number'].astype(str).str.strip().str.upper()
    df_build['Panel Need-By Date'] = pd.to_datetime(df_build['Panel Need-By Date'])

    # --- Demand Calculation ---
    demand = df_build.assign(key=1).merge(df_bom.assign(key=1), on='key').drop('key', axis=1)
    demand['Total Required'] = demand['Qty to Build'] * demand['Qty per Building']
    demand_total = demand.groupby(['Part Number', 'Description'], as_index=False)['Total Required'].sum()

    # --- Delivery Calculation ---
    earliest_due = df_build['Panel Need-By Date'].min()
    on_time_deliv = df_deliv[df_deliv['Delivery Date'] <= earliest_due]
    deliv_total = on_time_deliv.groupby('Part Number', as_index=False)['Qty'].sum().rename(columns={'Qty': 'Qty Arriving'})

    latest_dates = df_deliv.groupby('Part Number')['Delivery Date'].max().reset_index().rename(columns={'Delivery Date': 'Last Delivery'})

    # --- Final Dashboard ---
    dashboard = pd.merge(demand_total, deliv_total, on='Part Number', how='left')
    dashboard = pd.merge(dashboard, latest_dates, on='Part Number', how='left')
    dashboard['Qty Arriving'] = dashboard['Qty Arriving'].fillna(0).astype(int)
    dashboard['Shortfall'] = dashboard['Total Required'] - dashboard['Qty Arriving']
    dashboard['Status'] = dashboard['Shortfall'].apply(lambda x: '✅ OK' if x <= 0 else '⚠️ Short')

    st.subheader("📊 Demand vs. Supply Dashboard")
    st.dataframe(dashboard)

    # --- Download ---
    def convert_df(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()

    st.download_button("📥 Download Dashboard as Excel", data=convert_df(dashboard),
                       file_name="panel_dashboard.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

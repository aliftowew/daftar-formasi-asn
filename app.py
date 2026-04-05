import streamlit as st
import pandas as pd

st.set_page_config(page_title="Tes Darurat")
st.title("🛠️ Mode Tes Darurat")

try:
    st.info("Mencoba membaca SATU partikel file data saja...")
    # Kita tes baca 1 file saja, dan hanya ambil 2 kolom biar sangat ringan
    df_test = pd.read_parquet("cpns_part_1.parquet", columns=['agency_name', 'position_name'])
    
    st.success("✅ BERHASIL! File parquet bisa dibaca oleh server Streamlit.")
    st.metric("Total Baris di File 1", f"{len(df_test):,}")
    st.dataframe(df_test.head(10))

except Exception as e:
    st.error(f"❌ GAGAL! Server menemukan error saat membaca file: {e}")

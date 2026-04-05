import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Formasi CPNS", layout="wide")
st.title("📊 Dashboard Analisis Formasi CPNS")
st.markdown("Eksplorasi peta persaingan, formasi instansi, dan kualifikasi pendidikan.")

# 2. Load Data (Menggabungkan partikel file parquet)
@st.cache_data
def load_data():
    file_parts = [
        "cpns_part_1.parquet", "cpns_part_2.parquet", 
        "cpns_part_3.parquet", "cpns_part_4.parquet", 
        "cpns_part_5.parquet"
    ]
    
    df_list = []
    for file in file_parts:
        try:
            df_list.append(pd.read_parquet(file))
        except FileNotFoundError:
            pass
            
    if not df_list:
        st.error("File data tidak ditemukan. Pastikan file cpns_part sudah ada.")
        st.stop()
        
    df = pd.concat(df_list, ignore_index=True)
    df['total_formation'] = pd.to_numeric(df['total_formation'], errors='coerce').fillna(0)
    df['total_applicants'] = pd.to_numeric(df['total_applicants'], errors='coerce').fillna(0)
    return df

with st.spinner('Memuat jutaan sel data...'):
    df = load_data()

# ==========================================
# 3. FILTER PENCARIAN (Pindah ke Halaman Utama)
# ==========================================
st.markdown("### 🔍 Filter Pencarian")

# Membuat 3 kolom agar letak filter sejajar ke samping
col_filter1, col_filter2, col_filter3 = st.columns(3)

instansi_unik = sorted(df['agency_name'].dropna().unique())
pendidikan_unik = sorted(df['education_name'].dropna().unique())

with col_filter1:
    pilihan_instansi = st.multiselect("Pilih Instansi:", options=instansi_unik)

with col_filter2:
    pilihan_pendidikan = st.multiselect("Kualifikasi Pendidikan:", options=pendidikan_unik)

with col_filter3:
    cari_jabatan = st.text_input("Cari Nama Jabatan (misal: PENATA LAYANAN):")

st.divider() # Garis pembatas agar rapi

# 4. Terapkan Filter ke Data
df_filtered = df.copy()

if pilihan_instansi:
    df_filtered = df_filtered[df_filtered['agency_name'].isin(pilihan_instansi)]
if pilihan_pendidikan:
    df_filtered = df_filtered[df_filtered['education_name'].isin(pilihan_pendidikan)]
if cari_jabatan:
    df_filtered = df_filtered[df_filtered['position_name'].str.contains(cari_jabatan, case=False, na=False)]

# ==========================================
# 5. METRIK & VISUALISASI
# ==========================================
st.markdown("### 📌 Ringkasan Data")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Jabatan/Posisi", value=f"{len(df_filtered):,}")
with col2:
    st.metric(label="Total Formasi Dibuka", value=f"{int(df_filtered['total_formation'].sum()):,}")
with col3:
    st.metric(label="Total Pelamar Sementara", value=f"{int(df_filtered['total_applicants'].sum()):,}")

st.markdown("### 📈 Peta Persaingan & Formasi")
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    top_instansi = df_filtered.groupby('agency_name')['total_formation'].sum().reset_index()
    top_instansi = top_instansi.sort_values(by='total_formation', ascending=False).head(10)
    
    fig_instansi = px.bar(
        top_instansi, 
        x='total_formation', 
        y='agency_name', 
        orientation='h',
        title="Top 10 Instansi dengan Formasi Terbanyak",
        labels={'total_formation': 'Jumlah Formasi', 'agency_name': 'Instansi'},
        template="plotly_white"
    )
    fig_instansi.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_instansi, use_container_width=True)

with col_chart2:
    fig_scatter = px.scatter(
        df_filtered, 
        x='total_formation', 
        y='total_applicants', 
        color='formation_type_id',
        hover_data=['agency_name', 'position_name'],
        title="Distribusi Formasi vs Jumlah Pelamar",
        labels={'total_formation': 'Formasi Dibuka', 'total_applicants': 'Total Pelamar'},
        template="plotly_white",
        opacity=0.7
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# 6. Tabel Eksplorasi
st.markdown("### 📋 Detail Formasi")
kolom_tampil = [
    'agency_name', 'position_name', 'formation_name', 
    'education_name', 'total_formation', 'total_applicants'
]
st.dataframe(df_filtered[kolom_tampil].head(1000), use_container_width=True)

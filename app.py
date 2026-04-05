import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Formasi CPNS", layout="wide")
st.title("📊 Dashboard Analisis Formasi CPNS")
st.markdown("Eksplorasi peta persaingan, formasi instansi, dan kualifikasi pendidikan.")

# 2. Load Data dengan Cache & Optimasi Memori
@st.cache_data
def load_data():
    # Saran: Gunakan file .parquet saat deploy ke GitHub agar jauh lebih ringan
    # df = pd.read_parquet("tbl_cpns_formations.parquet") 
    df = pd.read_csv("tbl_cpns_formations.csv")
    
    # Memastikan kolom numerik terbaca dengan benar untuk kalkulasi
    df['total_formation'] = pd.to_numeric(df['total_formation'], errors='coerce').fillna(0)
    df['total_applicants'] = pd.to_numeric(df['total_applicants'], errors='coerce').fillna(0)
    return df

with st.spinner('Memuat jutaan sel data...'):
    try:
        df = load_data()
    except FileNotFoundError:
        st.error("File data tidak ditemukan. Pastikan file berada di direktori yang sama.")
        st.stop()

# 3. Sidebar: Filter Data
st.sidebar.header("🔍 Filter Pencarian")

# Filter Instansi
instansi_unik = sorted(df['agency_name'].dropna().unique())
pilihan_instansi = st.sidebar.multiselect("Pilih Instansi:", options=instansi_unik)

# Filter Pendidikan
pendidikan_unik = sorted(df['education_name'].dropna().unique())
pilihan_pendidikan = st.sidebar.multiselect("Kualifikasi Pendidikan:", options=pendidikan_unik)

# Filter Nama Jabatan (Pencarian Teks)
cari_jabatan = st.sidebar.text_input("Cari Nama Jabatan (misal: PENATA LAYANAN):")

# 4. Terapkan Filter ke Data
df_filtered = df.copy()

if pilihan_instansi:
    df_filtered = df_filtered[df_filtered['agency_name'].isin(pilihan_instansi)]
if pilihan_pendidikan:
    df_filtered = df_filtered[df_filtered['education_name'].isin(pilihan_pendidikan)]
if cari_jabatan:
    df_filtered = df_filtered[df_filtered['position_name'].str.contains(cari_jabatan, case=False, na=False)]

# 5. Metrik Utama (KPI)
st.markdown("### 📌 Ringkasan Data (Berdasarkan Filter)")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Jabatan/Posisi", value=f"{len(df_filtered):,}")
with col2:
    st.metric(label="Total Formasi Dibuka", value=f"{int(df_filtered['total_formation'].sum()):,}")
with col3:
    st.metric(label="Total Pelamar Sementara", value=f"{int(df_filtered['total_applicants'].sum()):,}")

st.divider()

# 6. Visualisasi Interaktif
st.markdown("### 📈 Peta Persaingan & Formasi")
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    # Top 10 Instansi dengan Formasi Terbanyak
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
    # Scatter Plot: Formasi vs Pelamar (Tingkat Keketatan)
    fig_scatter = px.scatter(
        df_filtered, 
        x='total_formation', 
        y='total_applicants', 
        color='formation_type_id', # Membedakan warna berdasarkan tipe formasi (Khusus/Umum)
        hover_data=['agency_name', 'position_name'],
        title="Distribusi Formasi vs Jumlah Pelamar",
        labels={'total_formation': 'Formasi Dibuka', 'total_applicants': 'Total Pelamar'},
        template="plotly_white",
        opacity=0.7
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# 7. Tabel Eksplorasi (Raw Data)
st.markdown("### 📋 Detail Formasi")
# Memilih kolom yang paling relevan untuk ditampilkan agar tabel rapi
kolom_tampil = [
    'agency_name', 'position_name', 'formation_name', 
    'education_name', 'total_formation', 'total_applicants'
]

# Batasi tampilan tabel maksimum 1000 baris agar browser tidak berat
st.dataframe(df_filtered[kolom_tampil].head(1000), use_container_width=True)

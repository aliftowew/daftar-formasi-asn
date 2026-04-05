import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Strategis CPNS", layout="wide")
st.title("📊 Dashboard Analisis Strategis Formasi CPNS")
st.markdown("Maksimalkan peluang lulus dengan analisis gaji dan rasio keketatan persaingan.")

# 2. Load Data & Data Engineering
@st.cache_data
def load_data():
    file_parts = ["cpns_part_1.parquet", "cpns_part_2.parquet", "cpns_part_3.parquet", "cpns_part_4.parquet", "cpns_part_5.parquet"]
    df_list = [pd.read_parquet(f) for f in file_parts if pd.io.common.file_exists(f)]
    
    if not df_list:
        st.error("Data tidak ditemukan.")
        st.stop()
        
    df = pd.concat(df_list, ignore_index=True)
    
    # Cleaning & Konversi Numerik
    df['total_formation'] = pd.to_numeric(df['total_formation'], errors='coerce').fillna(0)
    df['total_applicants'] = pd.to_numeric(df['total_applicants'], errors='coerce').fillna(0)
    df['salary_min'] = pd.to_numeric(df['salary_min'], errors='coerce').fillna(0)
    df['salary_max'] = pd.to_numeric(df['salary_max'], errors='coerce').fillna(0)
    
    # Hitung Rasio Keketatan (Pelamar per 1 Formasi)
    # Jika formasi 0, kita asumsikan 1 untuk menghindari pembagian dengan nol
    df['ratio_keketatan'] = (df['total_applicants'] / df['total_formation'].replace(0, 1)).round(2)
    
    return df

df = load_data()

# 3. Filter Utama di Halaman Depan
st.markdown("### 🔍 Filter Pencarian Strategis")
c1, c2, c3 = st.columns(3)

with c1:
    instansi = st.multiselect("Pilih Instansi:", options=sorted(df['agency_name'].unique()))
with c2:
    pendidikan = st.multiselect("Kualifikasi Pendidikan:", options=sorted(df['education_name'].unique()))
with c3:
    # Filter Gaji menggunakan Slider
    max_salary_limit = int(df['salary_max'].max()) if df['salary_max'].max() > 0 else 20000000
    filter_gaji = st.slider("Minimal Gaji Maksimum (Rp):", 0, max_salary_limit, 0, step=500000)

# Filter Logic
df_filtered = df.copy()
if instansi:
    df_filtered = df_filtered[df_filtered['agency_name'].isin(instansi)]
if pendidikan:
    df_filtered = df_filtered[df_filtered['education_name'].isin(pendidikan)]
df_filtered = df_filtered[df_filtered['salary_max'] >= filter_gaji]

st.divider()

# 4. Highlight Metrik Strategis
st.markdown("### 📌 Insight Penting")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Formasi", f"{int(df_filtered['total_formation'].sum()):,}")
m2.metric("Rata-rata Gaji Max", f"Rp {df_filtered['salary_max'].mean():,.0f}")
m3.metric("Keketatan Tertinggi", f"{df_filtered['ratio_keketatan'].max()}x")
m4.metric("Instansi Terpilih", f"{df_filtered['agency_name'].nunique()}")

# 5. Visualisasi Lanjutan
st.markdown("### 📈 Analisis Kesejahteraan vs Persaingan")
col_a, col_b = st.columns(2)

with col_a:
    # Box Plot Gaji per Instansi (Melihat sebaran gaji)
    top_10_instansi = df_filtered.groupby('agency_name')['salary_max'].mean().nlargest(10).index
    df_box = df_filtered[df_filtered['agency_name'].isin(top_10_instansi)]
    fig_box = px.box(df_box, x="agency_name", y="salary_max", 
                     title="Sebaran Gaji Maksimum di 10 Instansi Terpilih",
                     labels={'salary_max': 'Gaji Maksimum (Rp)', 'agency_name': 'Instansi'})
    st.plotly_chart(fig_box, use_container_width=True)

with col_b:
    # Scatter Plot: Gaji vs Keketatan
    fig_scatter = px.scatter(df_filtered, x="ratio_keketatan", y="salary_max",
                             size="total_formation", color="agency_name",
                             hover_data=['position_name'],
                             title="Hubungan Keketatan vs Gaji (Mencari Peluang 'Low Risk High Reward')",
                             labels={'ratio_keketatan': 'Rasio Keketatan (Pelamar/Formasi)', 'salary_max': 'Gaji Max'})
    st.plotly_chart(fig_scatter, use_container_width=True)

# 6. Tabel Detail yang Lebih Kaya
st.markdown("### 📋 Tabel Detail Formasi (Sortable)")
st.info("💡 Klik pada judul kolom untuk mengurutkan (misal: urutkan Gaji atau Keketatan).")

# Menampilkan kolom yang lebih fungsional
kolom_view = [
    'agency_name', 'position_name', 'education_name', 
    'salary_min', 'salary_max', 'total_formation', 
    'total_applicants', 'ratio_keketatan'
]

st.dataframe(
    df_filtered[kolom_view].sort_values('salary_max', ascending=False), 
    use_container_width=True,
    column_config={
        "salary_min": st.column_config.NumberColumn("Gaji Min", format="Rp %d"),
        "salary_max": st.column_config.NumberColumn("Gaji Max", format="Rp %d"),
        "ratio_keketatan": st.column_config.NumberColumn("Keketatan", format="%.2f x"),
    }
)

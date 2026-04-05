import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Strategis CPNS", layout="wide")
st.title("📊 Dashboard Analisis Strategis Formasi CPNS")
st.markdown("Maksimalkan peluang lulus dengan analisis gaji, rasio keketatan, dan detail pekerjaan.")

# 2. Load Data & Data Engineering
@st.cache_data
def load_data():
    file_parts = [
        "cpns_part_1.parquet", "cpns_part_2.parquet", 
        "cpns_part_3.parquet", "cpns_part_4.parquet", 
        "cpns_part_5.parquet"
    ]
    
    df_list = []
    for f in file_parts:
        try:
            df_list.append(pd.read_parquet(f))
        except FileNotFoundError:
            pass
    
    if not df_list:
        st.error("Data tidak ditemukan. Pastikan file cpns_part sudah terunggah.")
        st.stop()
        
    df = pd.concat(df_list, ignore_index=True)
    
    # Cleaning Numerik
    df['total_formation'] = pd.to_numeric(df['total_formation'], errors='coerce').fillna(0)
    df['total_applicants'] = pd.to_numeric(df['total_applicants'], errors='coerce').fillna(0)
    df['salary_min'] = pd.to_numeric(df['salary_min'], errors='coerce').fillna(0)
    df['salary_max'] = pd.to_numeric(df['salary_max'], errors='coerce').fillna(0)
    
    # 🛠️ PERBAIKAN BUG: Mengubah data kosong (NaN) menjadi teks agar tidak error saat di-sort
    df['education_name'] = df['education_name'].fillna("Tidak Ada Data").astype(str)
    df['agency_name'] = df['agency_name'].fillna("Tidak Ada Data").astype(str)
    df['job_description'] = df['job_description'].fillna("-").astype(str)
    
    # Hitung Rasio Keketatan
    df['ratio_keketatan'] = (df['total_applicants'] / df['total_formation'].replace(0, 1)).round(2)
    
    return df

df = load_data()

# 3. Filter Utama (URUTAN DIUBAH)
st.markdown("### 🔍 Filter Pencarian Strategis")
c1, c2, c3 = st.columns(3)

with c1:
    # Filter Pendidikan menjadi yang pertama
    pendidikan_unik = sorted(df['education_name'].unique())
    pendidikan = st.multiselect("Kualifikasi Pendidikan (Jurusan):", options=pendidikan_unik)
    
with c2:
    # Filter Instansi menjadi yang kedua
    instansi_unik = sorted(df['agency_name'].unique())
    instansi = st.multiselect("Pilih Instansi:", options=instansi_unik)
    
with c3:
    max_salary_limit = int(df['salary_max'].max()) if df['salary_max'].max() > 0 else 20000000
    filter_gaji = st.slider("Minimal Gaji Max (Rp):", 0, max_salary_limit, 0, step=500000)

# Terapkan logika filter
df_filtered = df.copy()
if pendidikan:
    df_filtered = df_filtered[df_filtered['education_name'].isin(pendidikan)]
if instansi:
    df_filtered = df_filtered[df_filtered['agency_name'].isin(instansi)]
df_filtered = df_filtered[df_filtered['salary_max'] >= filter_gaji]

st.divider()

# 4. Insight Penting
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
    top_10_instansi = df_filtered.groupby('agency_name')['salary_max'].mean().nlargest(10).index
    df_box = df_filtered[df_filtered['agency_name'].isin(top_10_instansi)]
    if not df_box.empty:
        fig_box = px.box(df_box, x="agency_name", y="salary_max", 
                         title="Sebaran Gaji Maksimum (Top 10 Instansi Terfilter)",
                         labels={'salary_max': 'Gaji Maksimum (Rp)', 'agency_name': 'Instansi'})
        st.plotly_chart(fig_box, use_container_width=True)
    else:
        st.info("Grafik gaji akan muncul setelah data dipilih.")

with col_b:
    if not df_filtered.empty:
        fig_scatter = px.scatter(df_filtered, x="ratio_keketatan", y="salary_max",
                                 size="total_formation", color="agency_name",
                                 hover_data=['position_name'],
                                 title="Hubungan Keketatan vs Gaji",
                                 labels={'ratio_keketatan': 'Rasio Keketatan', 'salary_max': 'Gaji Max'})
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Grafik persaingan akan muncul setelah data dipilih.")

# 6. Tabel Detail yang Lebih Kaya
st.markdown("### 📋 Detail Formasi & Deskripsi Pekerjaan")
st.info("💡 Scroll tabel ke kanan untuk melihat Deskripsi Pekerjaan secara lengkap.")

# Menambahkan job_description ke dalam daftar yang ditampilkan
kolom_view = [
    'agency_name', 'position_name', 'education_name', 
    'salary_min', 'salary_max', 'total_formation', 
    'total_applicants', 'ratio_keketatan', 
    'job_description' # <--- Deskripsi ditambahkan di sini
]

st.dataframe(
    df_filtered[kolom_view].sort_values('salary_max', ascending=False), 
    use_container_width=True,
    column_config={
        "salary_min": st.column_config.NumberColumn("Gaji Min", format="Rp %d"),
        "salary_max": st.column_config.NumberColumn("Gaji Max", format="Rp %d"),
        "ratio_keketatan": st.column_config.NumberColumn("Keketatan", format="%.2f x"),
        "job_description": st.column_config.TextColumn("Deskripsi Pekerjaan", width="large"), # Memberikan ruang lebar untuk teks panjang
    }
)

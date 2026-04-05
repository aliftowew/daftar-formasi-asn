import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Strategis CPNS", layout="wide")
st.title("📊 Dashboard Analisis Strategis Formasi CPNS")
st.markdown("Temukan formasi yang tepat untuk jurusanmu beserta detail pekerjaannya.")

# 2. Load Data (Optimasi RAM Maksimal)
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
    
    # 1. Buang kolom yang tidak dipakai di dashboard agar RAM lega
    kolom_penting = [
        'agency_name', 'position_name', 'education_name', 
        'salary_min', 'salary_max', 'total_formation', 
        'total_applicants', 'job_description'
    ]
    kolom_tersedia = [k for k in kolom_penting if k in df.columns]
    df = df[kolom_tersedia]
    
    # Cleaning Numerik
    df['total_formation'] = pd.to_numeric(df['total_formation'], errors='coerce').fillna(0)
    df['total_applicants'] = pd.to_numeric(df['total_applicants'], errors='coerce').fillna(0)
    df['salary_min'] = pd.to_numeric(df['salary_min'], errors='coerce').fillna(0)
    df['salary_max'] = pd.to_numeric(df['salary_max'], errors='coerce').fillna(0)
    
    df['education_name'] = df['education_name'].fillna("Tidak Ada Data").astype(str)
    
    if 'job_description' in df.columns:
        df['job_description'] = df['job_description'].fillna("-").astype(str)

    # 2. Ubah tipe data string ke tipe 'category' (Sangat hemat memori)
    for col in ['agency_name', 'position_name']:
        if col in df.columns:
            df[col] = df[col].astype('category')
            
    if 'agency_name' in df.columns:
        # Perbaikan Bug Kategori: Cek dulu apakah kategori sudah ada sebelum ditambahkan
        if "Tidak Ada Data" not in df['agency_name'].cat.categories:
            df['agency_name'] = df['agency_name'].cat.add_categories(["Tidak Ada Data"])
        df['agency_name'] = df['agency_name'].fillna("Tidak Ada Data")
    
    df = df[(df['total_formation'] > 0) & (df['total_applicants'] >= 0)]
    df['ratio_keketatan'] = (df['total_applicants'] / df['total_formation']).round(2)
    
    return df

df = load_data()

# =======================================================
# 3. FITUR BARU: EKSTRAKSI JURUSAN TUNGGAL (RAM DIET)
# =======================================================
@st.cache_data
def get_unique_majors(dataframe):
    # TRIK ANTI-OOM: Ekstrak nilai mentah uniknya DULU agar array menyusut drastis, 
    # baru dipecah (split) dan di-explode. Memangkas proses dari 1 juta baris menjadi beberapa ribu baris saja.
    unik_mentah = pd.Series(dataframe['education_name'].unique())
    semua_jurusan = unik_mentah.str.split(r'\s*/\s*').explode()
    jurusan_bersih = sorted(semua_jurusan[semua_jurusan != "Tidak Ada Data"].dropna().unique())
    return jurusan_bersih

jurusan_unik = get_unique_majors(df)

# 4. Filter Utama
st.markdown("### 🔍 Cari Berdasarkan Kualifikasimu")
c1, c2, c3 = st.columns(3)

with c1:
    pendidikan = st.multiselect("Kualifikasi Pendidikan (Bisa pilih >1):", options=jurusan_unik)
    
with c2:
    instansi = st.multiselect("Pilih Instansi (Opsional):", options=sorted(df['agency_name'].unique()))
    
with c3:
    max_salary_limit = int(df['salary_max'].max()) if df['salary_max'].max() > 0 else 20000000
    filter_gaji = st.slider("Minimal Gaji Max (Rp):", 0, max_salary_limit, 0, step=500000)

# =======================================================
# 5. LOGIKA FILTER CERDAS (Tanpa df.copy yang makan memori)
# =======================================================
df_filtered = df # <-- Gunakan referensi langsung, BUKAN .copy()

if pendidikan:
    pattern = '|'.join([f'(^|/)\\s*{re.escape(p)}\\s*(/|$)' for p in pendidikan])
    df_filtered = df_filtered[df_filtered['education_name'].str.contains(pattern, regex=True, na=False)]

if instansi:
    df_filtered = df_filtered[df_filtered['agency_name'].isin(instansi)]

df_filtered = df_filtered[df_filtered['salary_max'] >= filter_gaji]

st.divider()

# 6. Insight Penting
st.markdown("### 📌 Ringkasan Peluang")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Posisi Tersedia", f"{len(df_filtered):,}")
m2.metric("Total Kuota (Formasi)", f"{int(df_filtered['total_formation'].sum()):,}")
m3.metric("Rata-rata Gaji Max", f"Rp {df_filtered['salary_max'].mean():,.0f}" if not df_filtered.empty else "Rp 0")
m4.metric("Keketatan Tertinggi", f"{df_filtered['ratio_keketatan'].max()}x" if not df_filtered.empty else "0x")

# 7. Visualisasi (Anti Rusak)
st.markdown("### 📈 Analisis Kesejahteraan vs Persaingan")
col_a, col_b = st.columns(2)

with col_a:
    # Memastikan observed=True agar aman pada tipe data category
    top_10_instansi = df_filtered.groupby('agency_name', observed=True)['salary_max'].mean().nlargest(10).index
    df_box = df_filtered[df_filtered['agency_name'].isin(top_10_instansi)].copy()
    
    if not df_box.empty:
        df_box['agency_short'] = df_box['agency_name'].astype(str).apply(lambda x: x[:25] + '...' if len(x) > 25 else x)
        fig_box = px.box(df_box, x="agency_short", y="salary_max", 
                         title="Sebaran Gaji Max (Top 10 Instansi)",
                         labels={'salary_max': 'Gaji Max (Rp)', 'agency_short': 'Instansi'})
        st.plotly_chart(fig_box, use_container_width=True)
    else:
        st.info("Pilih filter terlebih dahulu untuk melihat sebaran gaji.")

with col_b:
    if not df_filtered.empty:
        fig_scatter = px.scatter(df_filtered, x="ratio_keketatan", y="salary_max",
                                 size="total_formation", color="agency_name",
                                 hover_data=['position_name', 'agency_name'],
                                 title="Keketatan vs Gaji",
                                 labels={'ratio_keketatan': 'Keketatan (Pelamar/Formasi)', 'salary_max': 'Gaji Max'})
        fig_scatter.update_layout(showlegend=False)
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Pilih filter terlebih dahulu untuk memetakan persaingan.")

# 8. Tabel Detail Interaktif (Super Lengkap)
st.markdown("### 📋 Detail Formasi, Gaji & Deskripsi Pekerjaan")
st.info("💡 Klik baris tabel untuk menyeleksi, atau geser kolom ke kanan untuk melihat Job Description.")

kolom_view = [
    'agency_name', 'position_name', 'education_name', 
    'salary_min', 'salary_max', 'total_formation', 
    'total_applicants', 'ratio_keketatan', 
    'job_description'
]

st.dataframe(
    df_filtered[kolom_view].sort_values('salary_max', ascending=False), 
    use_container_width=True,
    hide_index=True,
    column_config={
        "agency_name": "Instansi",
        "position_name": "Nama Jabatan",
        "education_name": "Kualifikasi (Semua Jurusan Diterima)",
        "salary_min": st.column_config.NumberColumn("Gaji Min", format="Rp %d"),
        "salary_max": st.column_config.NumberColumn("Gaji Max", format="Rp %d"),
        "total_formation": "Kuota",
        "total_applicants": "Pelamar",
        "ratio_keketatan": st.column_config.NumberColumn("Keketatan", format="%.2f x"),
        "job_description": st.column_config.TextColumn("Detail Pekerjaan", width="large"),
    }
)

import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Strategis ASN", layout="wide")
st.title("📊 Dashboard Analisis Strategis Formasi CPNS & PPPK")
st.markdown("Analisis tren kuota, petakan persaingan, dan temukan formasi yang tepat untuk jurusanmu.")

# 2. Load Data (Ultra Diet RAM + Penambahan Tahun & Jenis Pengadaan)
@st.cache_data
def load_data():
    file_parts = [
        "cpns_part_1.parquet", "cpns_part_2.parquet", 
        "cpns_part_3.parquet", "cpns_part_4.parquet", 
        "cpns_part_5.parquet"
    ]
    
    # Menambahkan 'year' dan 'procurement_name' (CPNS/PPPK) ke dalam memori
    kolom_penting = [
        'year', 'procurement_name', 'agency_name', 'position_name', 
        'education_name', 'salary_min', 'salary_max', 
        'total_formation', 'total_applicants', 'job_description'
    ]
    
    df_list = []
    for f in file_parts:
        try:
            temp_df = pd.read_parquet(f, columns=kolom_penting)
            df_list.append(temp_df)
        except FileNotFoundError:
            pass
            
    if not df_list:
        st.error("Data tidak ditemukan. Pastikan file cpns_part sudah terunggah.")
        st.stop()
        
    df = pd.concat(df_list, ignore_index=True)
    
    # Cleaning Data
    df['year'] = pd.to_numeric(df['year'], errors='coerce').fillna(2024).astype(int)
    df['total_formation'] = pd.to_numeric(df['total_formation'], errors='coerce').fillna(0)
    df['total_applicants'] = pd.to_numeric(df['total_applicants'], errors='coerce').fillna(0)
    df['salary_min'] = pd.to_numeric(df['salary_min'], errors='coerce').fillna(0)
    df['salary_max'] = pd.to_numeric(df['salary_max'], errors='coerce').fillna(0)
    
    df = df[df['total_formation'] > 0]
    df['ratio_keketatan'] = (df['total_applicants'] / df['total_formation']).round(2)
    
    # Merapikan Teks
    df['education_name'] = df['education_name'].fillna("Tidak Ada Data").astype(str)
    df['procurement_name'] = df['procurement_name'].fillna("Tidak Diketahui").astype(str)
    if 'job_description' in df.columns:
        df['job_description'] = df['job_description'].fillna("Deskripsi tidak tersedia.").astype(str)

    # Optimasi Memori
    for col in ['agency_name', 'position_name', 'procurement_name']:
        df[col] = df[col].astype('category')
            
    if "Tidak Ada Data" not in df['agency_name'].cat.categories:
        df['agency_name'] = df['agency_name'].cat.add_categories(["Tidak Ada Data"])
    df['agency_name'] = df['agency_name'].fillna("Tidak Ada Data")
    
    return df

df = load_data()

# =======================================================
# 3. FILTER CERDAS (Mendukung Pilihan Ganda Mudah)
# =======================================================
st.markdown("### 🔍 Filter Pencarian")
c1, c2, c3 = st.columns(3)

with c1:
    st.info("💡 Ketik nama jurusan lalu klik. Ulangi untuk memilih banyak jurusan sekaligus.")
    # Kita menggunakan multiselect karena ini adalah UI terbaik untuk "Search + Multiple Checkbox"
    # User tidak perlu mengetik Regex manual.
    cari_jurusan = st.text_input("Ketik Kata Kunci Jurusan (misal: Matematika):")
    kecualikan_pendidikan = st.checkbox("🚫 Jangan tampilkan S-1 Pendidikan", value=True)
    
with c2:
    instansi = st.multiselect("Pilih Instansi (Opsional):", options=sorted(df['agency_name'].dropna().unique()))
    
with c3:
    max_salary_limit = int(df['salary_max'].max()) if df['salary_max'].max() > 0 else 20000000
    filter_gaji = st.slider("Minimal Gaji Max (Rp):", 0, max_salary_limit, 0, step=500000)

# Terapkan Filter
df_filtered = df.copy()

if cari_jurusan:
    df_filtered = df_filtered[df_filtered['education_name'].str.contains(cari_jurusan, case=False, na=False)]
    if kecualikan_pendidikan and "pendidikan" not in cari_jurusan.lower():
        df_filtered = df_filtered[~df_filtered['education_name'].str.contains("pendidikan|keguruan", case=False, na=False)]

if instansi:
    df_filtered = df_filtered[df_filtered['agency_name'].isin(instansi)]

df_filtered = df_filtered[df_filtered['salary_max'] >= filter_gaji]

st.divider()

# =======================================================
# 4. GRAFIK HISTORIS (Tren dari Tahun ke Tahun)
# =======================================================
st.markdown("### 📈 Tren Formasi Historis")

# Mengelompokkan data berdasarkan Tahun dan Jenis Pengadaan
df_trend = df_filtered.groupby(['year', 'procurement_name'], observed=True)['total_formation'].sum().reset_index()

if not df_trend.empty:
    fig_trend = px.line(
        df_trend, 
        x='year', 
        y='total_formation', 
        color='procurement_name',
        markers=True,
        title="Pergerakan Jumlah Kuota Formasi (Berdasarkan Filter)",
        labels={'year': 'Tahun Anggaran', 'total_formation': 'Total Kuota Formasi', 'procurement_name': 'Jenis Pengadaan'},
        template="plotly_white"
    )
    # Memastikan sumbu X menampilkan tahun sebagai angka utuh, bukan desimal (misal 2024.5)
    fig_trend.update_xaxes(dtick=1) 
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("Pilih jurusan atau filter di atas untuk melihat tren data historis.")

st.divider()

# =======================================================
# 5. TAB TERPISAH (CPNS & PPPK) & TABEL KLIK INTERAKTIF
# =======================================================
st.markdown("### 📋 Daftar Detail Formasi")
st.success("✨ **FITUR BARU:** Klik salah satu baris pada tabel di bawah ini untuk melihat Detail Pekerjaan secara otomatis!")

# Memisahkan Data CPNS dan PPPK berdasarkan kata kunci pada kolom procurement_name
df_cpns = df_filtered[df_filtered['procurement_name'].str.contains("CPNS", case=False, na=False)]
df_pppk = df_filtered[~df_filtered['procurement_name'].str.contains("CPNS", case=False, na=False)] # Asumsi sisanya adalah PPPK

# Kolom yang ditampilkan di tabel (Sangat Ramping, tanpa deskripsi)
kolom_tabel = [
    'agency_name', 'position_name', 'salary_min', 'salary_max', 
    'total_formation', 'total_applicants', 'ratio_keketatan', 'year'
]

# Konfigurasi format kolom agar rapi
kolom_config = {
    "agency_name": "Instansi",
    "position_name": "Nama Jabatan",
    "salary_min": st.column_config.NumberColumn("Gaji Min", format="Rp %d"),
    "salary_max": st.column_config.NumberColumn("Gaji Max", format="Rp %d"),
    "total_formation": "Kuota",
    "total_applicants": "Pelamar",
    "ratio_keketatan": st.column_config.NumberColumn("Keketatan", format="%.2f x"),
    "year": st.column_config.NumberColumn("Tahun", format="%d")
}

# Membuat Tab
tab1, tab2 = st.tabs(["🏛️ Formasi CPNS", "💼 Formasi PPPK"])

with tab1:
    st.markdown(f"**Total Formasi CPNS Ditemukan: {len(df_cpns):,} posisi**")
    if not df_cpns.empty:
        # Menampilkan tabel dengan fitur seleksi baris (on_select)
        event_cpns = st.dataframe(
            df_cpns[kolom_tabel].sort_values('salary_max', ascending=False), 
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun", # Aplikasi akan me-refresh ringan saat baris diklik
            column_config=kolom_config
        )
        
        # Logika: Jika user mengeklik baris, tampilkan detailnya di bawah tabel
        if len(event_cpns.selection.rows) > 0:
            baris_terpilih = event_cpns.selection.rows[0]
            # Mengambil data asli berdasarkan baris yang diklik
            data_detail = df_cpns.sort_values('salary_max', ascending=False).iloc[baris_terpilih]
            
            with st.expander(f"📖 Lihat Detail: {data_detail['position_name']} di {data_detail['agency_name']}", expanded=True):
                st.write("**🎓 Syarat Jurusan:**")
                st.info(data_detail['education_name'])
                st.write("**📝 Deskripsi Pekerjaan:**")
                st.success(data_detail['job_description'])

with tab2:
    st.markdown(f"**Total Formasi PPPK Ditemukan: {len(df_pppk):,} posisi**")
    if not df_pppk.empty:
        event_pppk = st.dataframe(
            df_pppk[kolom_tabel].sort_values('salary_max', ascending=False), 
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            column_config=kolom_config
        )
        
        if len(event_pppk.selection.rows) > 0:
            baris_terpilih = event_pppk.selection.rows[0]
            data_detail = df_pppk.sort_values('salary_max', ascending=False).iloc[baris_terpilih]
            
            with st.expander(f"📖 Lihat Detail: {data_detail['position_name']} di {data_detail['agency_name']}", expanded=True):
                st.write("**🎓 Syarat Jurusan:**")
                st.info(data_detail['education_name'])
                st.write("**📝 Deskripsi Pekerjaan:**")
                st.success(data_detail['job_description'])

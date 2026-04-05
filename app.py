import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Strategis CPNS", layout="wide")
st.title("📊 Dashboard Analisis Strategis Formasi CPNS")
st.markdown("Temukan formasi yang tepat untuk jurusanmu beserta detail pekerjaannya.")

# 2. Load Data (Ultra Diet RAM)
@st.cache_data
def load_data():
    file_parts = [
        "cpns_part_1.parquet", "cpns_part_2.parquet", 
        "cpns_part_3.parquet", "cpns_part_4.parquet", 
        "cpns_part_5.parquet"
    ]
    
    kolom_penting = [
        'agency_name', 'position_name', 'education_name', 
        'salary_min', 'salary_max', 'total_formation', 
        'total_applicants', 'job_description'
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
    
    df['total_formation'] = pd.to_numeric(df['total_formation'], errors='coerce').fillna(0)
    df['total_applicants'] = pd.to_numeric(df['total_applicants'], errors='coerce').fillna(0)
    df['salary_min'] = pd.to_numeric(df['salary_min'], errors='coerce').fillna(0)
    df['salary_max'] = pd.to_numeric(df['salary_max'], errors='coerce').fillna(0)
    
    df = df[df['total_formation'] > 0]
    df['ratio_keketatan'] = (df['total_applicants'] / df['total_formation']).round(2)
    
    df['education_name'] = df['education_name'].fillna("Tidak Ada Data").astype(str)
    if 'job_description' in df.columns:
        df['job_description'] = df['job_description'].fillna("-").astype(str)

    for col in ['agency_name', 'position_name']:
        df[col] = df[col].astype('category')
            
    if "Tidak Ada Data" not in df['agency_name'].cat.categories:
        df['agency_name'] = df['agency_name'].cat.add_categories(["Tidak Ada Data"])
    df['agency_name'] = df['agency_name'].fillna("Tidak Ada Data")
    
    return df

df = load_data()

# =======================================================
# 3. FILTER CERDAS (Perbaikan Logika Jurusan)
# =======================================================
st.markdown("### 🔍 Cari Berdasarkan Kualifikasimu")

col_f1, col_f2 = st.columns(2)

with col_f1:
    # Menggunakan text input agar semua variasi nama jurusan bisa tertangkap
    cari_jurusan = st.text_input("🎓 Ketik Kata Kunci Jurusan (misal: Matematika, Akuntansi):")
    # Fitur canggih untuk memisahkan S-1 Murni dan S-1 Pendidikan
    kecualikan_pendidikan = st.checkbox("🚫 Singkirkan jurusan 'Pendidikan/Keguruan' (Centang jika kamu S-1 Murni)", value=True)

with col_f2:
    instansi = st.multiselect("🏢 Pilih Instansi (Opsional):", options=sorted(df['agency_name'].dropna().unique()))
    max_salary_limit = int(df['salary_max'].max()) if df['salary_max'].max() > 0 else 20000000
    filter_gaji = st.slider("💰 Minimal Gaji Max (Rp):", 0, max_salary_limit, 0, step=500000)

# Terapkan Filter
df_filtered = df.copy()

if cari_jurusan:
    # Filter pertama: cari semua yang mengandung kata kunci (MIPA Matematika, Ilmu Matematika, dll masuk)
    df_filtered = df_filtered[df_filtered['education_name'].str.contains(cari_jurusan, case=False, na=False)]
    
    # Filter kedua: Jika user tidak mengetik kata "pendidikan" tapi checkbox dicentang, buang semua S-1 Pendidikan
    if kecualikan_pendidikan and "pendidikan" not in cari_jurusan.lower():
        df_filtered = df_filtered[~df_filtered['education_name'].str.contains("pendidikan|keguruan", case=False, na=False)]

if instansi:
    df_filtered = df_filtered[df_filtered['agency_name'].isin(instansi)]

df_filtered = df_filtered[df_filtered['salary_max'] >= filter_gaji]

st.divider()

# =======================================================
# 4. INSIGHT & VISUALISASI
# =======================================================
st.markdown("### 📌 Ringkasan Peluang")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Posisi Tersedia", f"{len(df_filtered):,}")
m2.metric("Total Kuota (Formasi)", f"{int(df_filtered['total_formation'].sum()):,}")
m3.metric("Rata-rata Gaji Max", f"Rp {df_filtered['salary_max'].mean():,.0f}" if not df_filtered.empty else "Rp 0")
m4.metric("Keketatan Tertinggi", f"{df_filtered['ratio_keketatan'].max()}x" if not df_filtered.empty else "0x")

st.markdown("### 📈 Analisis Kesejahteraan vs Persaingan")
col_a, col_b = st.columns(2)

with col_a:
    top_10_instansi = df_filtered.groupby('agency_name', observed=True)['salary_max'].mean().nlargest(10).index
    df_box = df_filtered[df_filtered['agency_name'].isin(top_10_instansi)].copy()
    
    if not df_box.empty:
        df_box['agency_short'] = df_box['agency_name'].astype(str).apply(lambda x: x[:25] + '...' if len(x) > 25 else x)
        fig_box = px.box(df_box, x="agency_short", y="salary_max", 
                         title="Sebaran Gaji Max (Top 10 Instansi)",
                         labels={'salary_max': 'Gaji Max (Rp)', 'agency_short': 'Instansi'})
        st.plotly_chart(fig_box, use_container_width=True)
    else:
        st.info("Pilih jurusan terlebih dahulu untuk melihat grafik.")

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
        st.info("Pilih jurusan terlebih dahulu untuk melihat grafik.")

# =======================================================
# 5. TABEL UTAMA (Tanpa Deskripsi Panjang)
# =======================================================
st.markdown("### 📋 Daftar Formasi")

# Kolom deskripsi dibuang dari tabel agar rapi dan tidak perlu scroll ke kanan
kolom_tabel = [
    'agency_name', 'position_name', 'salary_min', 'salary_max', 
    'total_formation', 'total_applicants', 'ratio_keketatan'
]

st.dataframe(
    df_filtered[kolom_tabel].sort_values('salary_max', ascending=False), 
    use_container_width=True,
    hide_index=True,
    column_config={
        "agency_name": "Instansi",
        "position_name": "Nama Jabatan",
        "salary_min": st.column_config.NumberColumn("Gaji Min", format="Rp %d"),
        "salary_max": st.column_config.NumberColumn("Gaji Max", format="Rp %d"),
        "total_formation": "Kuota",
        "total_applicants": "Pelamar",
        "ratio_keketatan": st.column_config.NumberColumn("Keketatan", format="%.2f x"),
    }
)

st.divider()

# =======================================================
# 6. FITUR BARU: KARTU DESKRIPSI DETAIL
# =======================================================
st.markdown("### 📖 Detail & Deskripsi Pekerjaan Lengkap")
st.markdown("Pilih formasi spesifik untuk membaca tugas dan syarat jurusan selengkapnya tanpa harus geser tabel.")

if not df_filtered.empty:
    # Membuat label gabungan yang unik untuk dropdown
    df_filtered['opsi_pilihan'] = df_filtered['agency_name'].astype(str) + " - " + df_filtered['position_name'].astype(str) + " (Gaji Max: Rp " + df_filtered['salary_max'].apply(lambda x: f"{x:,.0f}") + ")"
    
    pilihan_jabatan = st.selectbox("🔎 Pilih formasi untuk melihat detail:", options=df_filtered['opsi_pilihan'].unique())
    
    if pilihan_jabatan:
        # Ambil data spesifik yang dipilih
        detail = df_filtered[df_filtered['opsi_pilihan'] == pilihan_jabatan].iloc[0]
        
        # Desain Kartu (Card) menggunakan container dengan border
        with st.container(border=True):
            st.subheader(f"💼 {detail['position_name']}")
            st.write(f"🏢 **Instansi:** {detail['agency_name']}")
            st.write(f"🎓 **Syarat Jurusan yang Diterima:**")
            st.info(detail['education_name'])
            
            c_gaji, c_kuota, c_ketat = st.columns(3)
            c_gaji.metric("Rentang Gaji", f"Rp {detail['salary_min']:,.0f} - Rp {detail['salary_max']:,.0f}")
            c_kuota.metric("Kuota Formasi", f"{detail['total_formation']} kursi")
            c_ketat.metric("Tingkat Keketatan", f"{detail['ratio_keketatan']}x")
            
            st.markdown("---")
            st.markdown("**Deskripsi & Tugas Pekerjaan:**")
            # Teks panjang akan ditampilkan dengan rapi membentang ke bawah
            st.success(detail['job_description'])

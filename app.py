import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Strategis ASN", layout="wide")
st.title("📊 Dashboard Analisis Strategis Formasi CPNS & PPPK")
st.markdown("Temukan formasi yang tepat, lihat detail gaji, dan analisis tren kuota dari tahun ke tahun.")

# 2. Load Data (Ultra Diet RAM)
@st.cache_data
def load_data():
    file_parts = [
        "cpns_part_1.parquet", "cpns_part_2.parquet", 
        "cpns_part_3.parquet", "cpns_part_4.parquet", 
        "cpns_part_5.parquet"
    ]
    
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
            # Mengabaikan jika file memang belum di-upload
            pass
        except Exception as e:
            # JIKA FILE KORUP, TAMPILKAN PERINGATAN TAPI APLIKASI TETAP JALAN
            st.warning(f"⚠️ Peringatan: File {f} korup atau gagal terbaca dan akan dilewati.")
            
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
# 3. EKSTRAKSI JURUSAN
# =======================================================
@st.cache_data
def get_unique_majors(dataframe):
    unik_teks = dataframe['education_name'].unique()
    semua_teks = " / ".join(unik_teks)
    jurusan_list = re.split(r'\s*/\s*', semua_teks)
    
    jurusan_bersih = sorted(list(set(jurusan_list)))
    if "Tidak Ada Data" in jurusan_bersih:
        jurusan_bersih.remove("Tidak Ada Data")
    return jurusan_bersih

jurusan_unik = get_unique_majors(df)

# =======================================================
# 4. FILTER CERDAS (UI Diperbarui)
# =======================================================
st.markdown("### 🔍 Cari Formasi Anda")
c1, c2, c3 = st.columns(3)

with c1:
    # Menggunakan multiselect: Bertindak sebagai search box + multiple checkbox
    pendidikan = st.multiselect("🎓 Cari & Pilih Jurusan (Bisa >1):", options=jurusan_unik)
    
with c2:
    instansi = st.multiselect("🏢 Pilih Instansi (Opsional):", options=sorted(df['agency_name'].unique()))
    
with c3:
    max_salary_limit = int(df['salary_max'].max()) if df['salary_max'].max() > 0 else 20000000
    filter_gaji = st.slider("💰 Minimal Gaji Max (Rp):", 0, max_salary_limit, 0, step=500000)

# Terapkan Filter
df_filtered = df.copy()

if pendidikan:
    pattern = '|'.join([f'(^|/)\\s*{re.escape(p)}\\s*(/|$)' for p in pendidikan])
    df_filtered = df_filtered[df_filtered['education_name'].str.contains(pattern, regex=True, na=False)]

if instansi:
    df_filtered = df_filtered[df_filtered['agency_name'].isin(instansi)]

df_filtered = df_filtered[df_filtered['salary_max'] >= filter_gaji]

st.divider()

# =======================================================
# 5. TAB TERPISAH & TABEL RAMPING INTERAKTIF
# =======================================================
st.markdown("### 📋 Daftar Formasi")
st.info("👆 **TIPS:** Klik baris mana saja pada tabel di bawah ini untuk melihat Detail Gaji, Kuota, dan Grafik Historis.")

# Memisahkan Data
df_cpns = df_filtered[df_filtered['procurement_name'].str.contains("CPNS", case=False, na=False)]
df_pppk = df_filtered[~df_filtered['procurement_name'].str.contains("CPNS", case=False, na=False)]

# Fungsi untuk menampilkan detail dan grafik historis
def tampilkan_detail(data_detail, df_full):
    with st.container(border=True):
        st.subheader(f"💼 {data_detail['position_name']}")
        st.markdown(f"**🏢 Instansi:** {data_detail['agency_name']} | **Tahun:** {data_detail['year']}")
        
        # Metrik Utama
        m1, m2, m3 = st.columns(3)
        m1.metric("Rentang Gaji", f"Rp {data_detail['salary_min']:,.0f} - Rp {data_detail['salary_max']:,.0f}")
        m2.metric("Kuota Formasi", f"{data_detail['total_formation']} Kursi")
        m3.metric("Tingkat Keketatan", f"{data_detail['ratio_keketatan']}x")
        
        st.markdown("**🎓 Syarat Jurusan Diterima:**")
        st.info(data_detail['education_name'])
        
        st.markdown("**📝 Deskripsi Pekerjaan:**")
        st.success(data_detail['job_description'])
        
        # Grafik Historis untuk Posisi dan Instansi yang sama
        df_historis = df_full[
            (df_full['agency_name'] == data_detail['agency_name']) & 
            (df_full['position_name'] == data_detail['position_name']) &
            (df_full['procurement_name'] == data_detail['procurement_name'])
        ].groupby('year')['total_formation'].sum().reset_index()

        if len(df_historis) > 1:
            st.markdown("---")
            st.markdown("#### 📈 Tren Kuota Formasi Historis")
            fig = px.bar(
                df_historis, x='year', y='total_formation',
                text='total_formation',
                labels={'year': 'Tahun', 'total_formation': 'Jumlah Kuota'},
                template="plotly_white"
            )
            fig.update_traces(textposition='outside')
            fig.update_xaxes(dtick=1) # Memastikan tahun tidak desimal
            st.plotly_chart(fig, use_container_width=True)

# Membuat Tab
tab1, tab2 = st.tabs(["🏛️ Formasi CPNS", "💼 Formasi PPPK"])

# --- TAB CPNS ---
with tab1:
    st.markdown(f"**Total Ditemukan: {len(df_cpns):,} Formasi CPNS**")
    if not df_cpns.empty:
        # Sortir alfabetis agar mudah dicari
        df_cpns_view = df_cpns.sort_values(['agency_name', 'position_name']).reset_index(drop=True)
        
        event_cpns = st.dataframe(
            df_cpns_view[['agency_name', 'position_name']], 
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            column_config={
                "agency_name": "Instansi Pemerintahan",
                "position_name": "Nama Jabatan / Posisi"
            }
        )
        
        # Pemicu Detail
        if len(event_cpns.selection.rows) > 0:
            baris_terpilih = event_cpns.selection.rows[0]
            data_detail = df_cpns_view.iloc[baris_terpilih]
            tampilkan_detail(data_detail, df)

# --- TAB PPPK ---
with tab2:
    st.markdown(f"**Total Ditemukan: {len(df_pppk):,} Formasi PPPK**")
    if not df_pppk.empty:
        df_pppk_view = df_pppk.sort_values(['agency_name', 'position_name']).reset_index(drop=True)
        
        event_pppk = st.dataframe(
            df_pppk_view[['agency_name', 'position_name']], 
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            column_config={
                "agency_name": "Instansi Pemerintahan",
                "position_name": "Nama Jabatan / Posisi"
            }
        )
        
        if len(event_pppk.selection.rows) > 0:
            baris_terpilih = event_pppk.selection.rows[0]
            data_detail = df_pppk_view.iloc[baris_terpilih]
            tampilkan_detail(data_detail, df)

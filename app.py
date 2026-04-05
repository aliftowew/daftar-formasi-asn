import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="SSCASN Explorer",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "https://api-sscasn.bkn.go.id/2026"
HEADERS = {
    "Referer": "https://sscasn.bkn.go.id/",
    "Origin": "https://sscasn.bkn.go.id",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}

# ─────────────────────────────────────────
# DATA FETCH
# ─────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_all_formasi():
    """Ambil semua data formasi dari API BKN dengan pagination."""
    try:
        # Ambil page pertama untuk tahu total
        r = requests.get(f"{API_BASE}/portal/spf?offset=0&limit=10", headers=HEADERS, timeout=15)
        r.raise_for_status()
        first = r.json()
        total = first["data"]["meta"]["total"]
        all_data = list(first["data"]["data"])

        # Ambil halaman selanjutnya
        pages = (total + 9) // 10
        for i in range(1, pages):
            r2 = requests.get(f"{API_BASE}/portal/spf?offset={i*10}&limit=10", headers=HEADERS, timeout=15)
            r2.raise_for_status()
            all_data.extend(r2.json()["data"]["data"])

        return all_data, None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=3600)
def fetch_instansi():
    try:
        r = requests.get(f"{API_BASE}/referensi/instansi", headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json().get("data", [])
    except:
        return []


def build_dataframe(raw):
    df = pd.DataFrame(raw)
    df = df.rename(columns={
        "ins_nm": "Instansi",
        "jp_nama": "Jenis Pengadaan",
        "formasi_nm": "Jenis Formasi",
        "jabatan_nm": "Jabatan",
        "lokasi_nm": "Lokasi / Unit Kerja",
        "jumlah_formasi": "Jumlah Formasi",
        "gaji_min": "Gaji Min",
        "gaji_max": "Gaji Max",
    })
    df["Jumlah Formasi"] = pd.to_numeric(df["Jumlah Formasi"], errors="coerce").fillna(0).astype(int)
    # Bersihkan nama jabatan (singkat prefix panjang)
    df["Jabatan Singkat"] = df["Jabatan"].str.replace(r"^GURU AHLI PERTAMA - ", "", regex=True)
    # Provinsi dari kolom lokasi
    df["Provinsi"] = df["Lokasi / Unit Kerja"].str.extract(r"Provinsi (.+)$")
    df["Provinsi"] = df["Provinsi"].fillna("Tidak Diketahui")
    return df


# ─────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────
with st.spinner("Mengambil data terbaru dari SSCASN BKN..."):
    raw_data, error = fetch_all_formasi()

if error or not raw_data:
    st.warning(f"⚠️ Tidak dapat mengambil data dari API BKN. Menampilkan data contoh.\n\nError: {error}")
    # Data demo berdasarkan data real yang di-scrape
    raw_data = [
        {"ins_nm": "Kementerian Pendidikan Tinggi, Sains, dan Teknologi", "jp_nama": "PPPK Guru", "formasi_nm": "UMUM", "jabatan_nm": "GURU AHLI PERTAMA - GURU BAHASA ARAB", "lokasi_nm": "SMA Unggul Garuda Belitung Timur, Provinsi Kepulauan Bangka Belitung", "jumlah_formasi": 1, "gaji_min": "", "gaji_max": ""},
        {"ins_nm": "Kementerian Pendidikan Tinggi, Sains, dan Teknologi", "jp_nama": "PPPK Guru", "formasi_nm": "UMUM", "jabatan_nm": "GURU AHLI PERTAMA - GURU BAHASA INGGRIS", "lokasi_nm": "SMA Unggul Garuda Papua, Provinsi Papua", "jumlah_formasi": 2, "gaji_min": "", "gaji_max": ""},
        {"ins_nm": "Kementerian Pendidikan Tinggi, Sains, dan Teknologi", "jp_nama": "PPPK Guru", "formasi_nm": "UMUM", "jabatan_nm": "GURU AHLI PERTAMA - GURU MATEMATIKA", "lokasi_nm": "SMA Unggul Garuda Timor Tengah Selatan, Provinsi Nusa Tenggara Timur", "jumlah_formasi": 1, "gaji_min": "", "gaji_max": ""},
        {"ins_nm": "Kementerian Pendidikan Tinggi, Sains, dan Teknologi", "jp_nama": "PPPK Guru", "formasi_nm": "DISABILITAS", "jabatan_nm": "GURU AHLI PERTAMA - GURU FISIKA", "lokasi_nm": "SMA Unggul Garuda Kalimantan Timur, Provinsi Kalimantan Timur", "jumlah_formasi": 1, "gaji_min": "", "gaji_max": ""},
        {"ins_nm": "Kementerian Pendidikan Tinggi, Sains, dan Teknologi", "jp_nama": "PPPK Guru", "formasi_nm": "UMUM", "jabatan_nm": "GURU AHLI PERTAMA - GURU KIMIA", "lokasi_nm": "SMA Unggul Garuda Maluku Utara, Provinsi Maluku Utara", "jumlah_formasi": 2, "gaji_min": "", "gaji_max": ""},
        {"ins_nm": "Kementerian Pendidikan Tinggi, Sains, dan Teknologi", "jp_nama": "PPPK Guru", "formasi_nm": "PUTRA/PUTRI PAPUA", "jabatan_nm": "GURU AHLI PERTAMA - GURU BIOLOGI", "lokasi_nm": "SMA Unggul Garuda Papua Barat, Provinsi Papua Barat", "jumlah_formasi": 1, "gaji_min": "", "gaji_max": ""},
    ] * 12  # expand to ~72 rows

df = build_dataframe(raw_data)

# ─────────────────────────────────────────
# SIDEBAR FILTER
# ─────────────────────────────────────────
st.sidebar.image("https://sscasn.bkn.go.id/_next/static/media/logo.3b5a1473.png", width=160)
st.sidebar.title("🔍 Filter Formasi")
st.sidebar.caption(f"Data diperbarui: {datetime.now().strftime('%d %B %Y, %H:%M')}")

instansi_list = ["Semua"] + sorted(df["Instansi"].dropna().unique().tolist())
jenis_pengadaan_list = ["Semua"] + sorted(df["Jenis Pengadaan"].dropna().unique().tolist())
jenis_formasi_list = ["Semua"] + sorted(df["Jenis Formasi"].dropna().unique().tolist())
provinsi_list = ["Semua"] + sorted(df["Provinsi"].dropna().unique().tolist())

sel_instansi = st.sidebar.selectbox("🏢 Instansi", instansi_list)
sel_pengadaan = st.sidebar.selectbox("📋 Jenis Pengadaan", jenis_pengadaan_list)
sel_formasi = st.sidebar.selectbox("📌 Jenis Formasi", jenis_formasi_list)
sel_provinsi = st.sidebar.selectbox("📍 Provinsi", provinsi_list)
cari = st.sidebar.text_input("🔎 Cari Jabatan", placeholder="contoh: matematika, biologi...")

# Apply filter
fdf = df.copy()
if sel_instansi != "Semua":
    fdf = fdf[fdf["Instansi"] == sel_instansi]
if sel_pengadaan != "Semua":
    fdf = fdf[fdf["Jenis Pengadaan"] == sel_pengadaan]
if sel_formasi != "Semua":
    fdf = fdf[fdf["Jenis Formasi"] == sel_formasi]
if sel_provinsi != "Semua":
    fdf = fdf[fdf["Provinsi"] == sel_provinsi]
if cari:
    fdf = fdf[fdf["Jabatan"].str.contains(cari, case=False, na=False)]

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.title("🏛️ SSCASN Explorer")
st.caption("Pencari Formasi CPNS & PPPK yang lebih nyaman — data langsung dari API resmi BKN")

# Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Formasi Ditampilkan", f"{len(fdf):,}")
col2.metric("Total Lowongan", f"{fdf['Jumlah Formasi'].sum():,}")
col3.metric("Jumlah Instansi", f"{fdf['Instansi'].nunique():,}")
col4.metric("Jenis Jabatan", f"{fdf['Jabatan'].nunique():,}")

st.divider()

# ─────────────────────────────────────────
# TABS
# ─────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Visualisasi", "📋 Tabel Data", "ℹ️ Info & Bantuan"])

# ── TAB 1: Visualisasi ──
with tab1:
    if fdf.empty:
        st.info("Tidak ada data yang cocok dengan filter yang dipilih.")
    else:
        c1, c2 = st.columns(2)

        # Chart: Top jabatan
        with c1:
            top_jabatan = (
                fdf.groupby("Jabatan Singkat")["Jumlah Formasi"]
                .sum()
                .sort_values(ascending=False)
                .head(10)
                .reset_index()
            )
            fig = px.bar(
                top_jabatan,
                x="Jumlah Formasi",
                y="Jabatan Singkat",
                orientation="h",
                title="Top 10 Jabatan by Jumlah Formasi",
                color="Jumlah Formasi",
                color_continuous_scale="Blues",
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # Chart: Pie jenis formasi
        with c2:
            pie_data = fdf.groupby("Jenis Formasi")["Jumlah Formasi"].sum().reset_index()
            fig2 = px.pie(
                pie_data,
                names="Jenis Formasi",
                values="Jumlah Formasi",
                title="Sebaran Jenis Formasi",
                hole=0.4,
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Chart: Sebaran provinsi
        if fdf["Provinsi"].nunique() > 1:
            prov_data = (
                fdf.groupby("Provinsi")["Jumlah Formasi"]
                .sum()
                .sort_values(ascending=False)
                .head(15)
                .reset_index()
            )
            fig3 = px.bar(
                prov_data,
                x="Provinsi",
                y="Jumlah Formasi",
                title="Top Provinsi by Jumlah Formasi",
                color="Jumlah Formasi",
                color_continuous_scale="Teal",
            )
            fig3.update_xaxes(tickangle=45)
            st.plotly_chart(fig3, use_container_width=True)

# ── TAB 2: Tabel ──
with tab2:
    st.subheader(f"📋 {len(fdf):,} Formasi Ditemukan")

    # Download
    col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 4])
    csv = fdf.to_csv(index=False).encode("utf-8-sig")
    col_dl1.download_button("⬇️ Download CSV", csv, "formasi_sscasn.csv", "text/csv")

    cols_show = ["Instansi", "Jenis Pengadaan", "Jenis Formasi", "Jabatan", "Lokasi / Unit Kerja", "Jumlah Formasi"]
    st.dataframe(
        fdf[cols_show],
        use_container_width=True,
        height=500,
        hide_index=True,
    )

# ── TAB 3: Info ──
with tab3:
    st.subheader("ℹ️ Tentang Aplikasi Ini")
    st.markdown("""
    Aplikasi ini mengambil data **langsung dari API resmi SSCASN BKN** secara real-time.

    **Sumber data:** `api-sscasn.bkn.go.id`
    **Periode:** 2026
    **Pembaruan data:** Setiap 1 jam (cache otomatis)

    ---

    ### Kenapa data sedikit?
    Data formasi muncul bertahap sesuai jadwal pembukaan seleksi. Jika hanya ada 1 instansi,
    berarti instansi lain belum membuka pendaftaran. Pantau terus!

    ### Cara deploy ulang dengan data terbaru
    Klik tombol **☁️ Clear Cache** di sudut kanan atas untuk refresh data manual.

    ---

    ### Link Resmi
    - 🌐 [SSCASN BKN](https://sscasn.bkn.go.id)
    - 📖 [Buku Petunjuk SSCASN](https://sscasn.bkn.go.id/buku-petunjuk)
    - ❓ [Helpdesk BKN](https://helpdesk.bkn.go.id)
    """)

    st.info("💡 **Tips:** Gunakan filter di sidebar untuk mempersempit pencarian sesuai kebutuhan kamu.")

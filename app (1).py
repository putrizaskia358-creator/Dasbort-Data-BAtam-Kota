import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO

# Dashboard khusus Kota Batam berdasarkan dataset fiskal yang diberikan
CSV_URL = "https://raw.githubusercontent.com/Alam-A99/DATAAKSI/main/dataset_fiskal_97_hipoFull.csv"

st.set_page_config(
    page_title="Dashboard Fiskal Kota Batam",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dashboard Fiskal dan IPM Kota Batam")
st.caption("Analisis data Kota Batam periode 2014–2024 | Sumber: dataset_fiskal_97_hipoFull.csv")

@st.cache_data
def load_data():
    # Membaca dataset dari GitHub
    response = requests.get(CSV_URL, timeout=30)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text))
    df.columns = df.columns.str.strip()
    df["Kota"] = df["Kota"].astype(str).str.strip()
    df["Tahun"] = pd.to_numeric(df["Tahun"], errors="coerce")
    return df

try:
    data = load_data()
except Exception as e:
    st.error("Data belum berhasil dimuat dari GitHub. Periksa koneksi internet, lalu muat ulang aplikasi.")
    st.code(str(e))
    st.stop()

# Filter hanya baris Kota Batam (menggunakan nama persis yang ada di dataset)
batam = data[data["Kota"].str.casefold().eq("kota batam")].copy()

if batam.empty:
    st.error("Kota Batam tidak ditemukan pada dataset. Nama kota yang tersedia dengan kata 'Batam':")
    st.write(data.loc[data["Kota"].str.contains("Batam", case=False, na=False), "Kota"].drop_duplicates().tolist())
    st.stop()

batam = batam.sort_values("Tahun")
numeric_cols = batam.select_dtypes(include="number").columns.tolist()

# Kolom analisis utama yang memang ada pada dataset
indikator_fiskal = [
    "DBH_PAJAK", "DBH_SDA", "DBH_Lainnya", "DAU_Grant", "DAU_Earmark",
    "DAK_Fisik", "DAK_Nonfisik", "PAD", "ICT"
]
belanja_cols = [
    "bm_pendidikan", "bm_kesehatan", "bm_perumahan", "bm_lingkungan",
    "bm_ekonomi", "bm_infrastruktur", "bm_pariwisata",
    "bm_perlindungan_sosial"
]
indikator_sosial = ["IPM", "KEMISKINAN", "PENGANGGURAN", "KETIMPANGAN", "PE"]
indikator_fiskal = [c for c in indikator_fiskal if c in batam.columns]
belanja_cols = [c for c in belanja_cols if c in batam.columns]
indikator_sosial = [c for c in indikator_sosial if c in batam.columns]

# Sidebar
st.sidebar.header("Pengaturan Dashboard")
tahun_tersedia = sorted(batam["Tahun"].dropna().astype(int).unique().tolist())
tahun_pilihan = st.sidebar.select_slider(
    "Pilih rentang tahun",
    options=tahun_tersedia,
    value=(tahun_tersedia[0], tahun_tersedia[-1])
)
df = batam[batam["Tahun"].between(tahun_pilihan[0], tahun_pilihan[1])].copy()

st.subheader("Ringkasan Kota Batam")
terbaru = df.sort_values("Tahun").iloc[-1]
awal = df.sort_values("Tahun").iloc[0]

def fmt_num(value, decimals=2):
    if pd.isna(value):
        return "—"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Tahun terbaru pada filter", str(int(terbaru["Tahun"])))
if "IPM" in df.columns:
    perubahan_ipm = terbaru["IPM"] - awal["IPM"] if len(df) > 1 else 0
    c2.metric("IPM tahun terbaru", fmt_num(terbaru["IPM"]), f"{perubahan_ipm:+.2f} dari awal rentang" if len(df) > 1 else None)
if "PAD" in df.columns:
    c3.metric("PAD tahun terbaru", fmt_num(terbaru["PAD"]))
if "bm_pendidikan" in df.columns:
    c4.metric("Belanja pendidikan terbaru", fmt_num(terbaru["bm_pendidikan"]))

st.info("Angka ditampilkan mengikuti satuan pada dataset sumber. Dashboard tidak mengubah angka menjadi rupiah karena keterangan satuan tidak dicantumkan pada file CSV.")

# Tren IPM dan indikator sosial
st.subheader("1. Perkembangan IPM Kota Batam")
if "IPM" in df.columns:
    fig_ipm = px.line(
        df, x="Tahun", y="IPM", markers=True,
        title="Tren Indeks Pembangunan Manusia (IPM)",
        labels={"Tahun": "Tahun", "IPM": "IPM"}
    )
    fig_ipm.update_layout(hovermode="x unified")
    st.plotly_chart(fig_ipm, use_container_width=True)

cols_sosial_chart = [c for c in ["KEMISKINAN", "PENGANGGURAN", "KETIMPANGAN"] if c in df.columns]
if cols_sosial_chart:
    sosial_long = df[["Tahun"] + cols_sosial_chart].melt(
        id_vars="Tahun", var_name="Indikator", value_name="Nilai"
    )
    fig_sosial = px.line(
        sosial_long, x="Tahun", y="Nilai", color="Indikator", markers=True,
        title="Tren Indikator Sosial",
        labels={"Tahun": "Tahun", "Nilai": "Nilai indikator"}
    )
    st.plotly_chart(fig_sosial, use_container_width=True)

# Pendapatan/transfer fiskal
st.subheader("2. Komponen Pendapatan dan Transfer Fiskal")
if indikator_fiskal:
    fiskal_long = df[["Tahun"] + indikator_fiskal].melt(
        id_vars="Tahun", var_name="Komponen", value_name="Nilai"
    )
    fig_fiskal = px.bar(
        fiskal_long, x="Tahun", y="Nilai", color="Komponen", barmode="group",
        title="Perbandingan Komponen Fiskal per Tahun",
        labels={"Tahun": "Tahun", "Nilai": "Nilai pada dataset"}
    )
    st.plotly_chart(fig_fiskal, use_container_width=True)

# Belanja menurut bidang
st.subheader("3. Belanja Menurut Bidang")
if belanja_cols:
    pilihan_belanja = st.multiselect(
        "Pilih bidang belanja untuk ditampilkan",
        options=belanja_cols,
        default=[c for c in ["bm_pendidikan", "bm_kesehatan", "bm_infrastruktur"] if c in belanja_cols]
    )
    if pilihan_belanja:
        belanja_long = df[["Tahun"] + pilihan_belanja].melt(
            id_vars="Tahun", var_name="Bidang", value_name="Nilai"
        )
        fig_belanja = px.bar(
            belanja_long, x="Tahun", y="Nilai", color="Bidang", barmode="group",
            title="Perbandingan Belanja per Bidang",
            labels={"Tahun": "Tahun", "Nilai": "Nilai pada dataset"}
        )
        st.plotly_chart(fig_belanja, use_container_width=True)
    else:
        st.warning("Pilih minimal satu bidang belanja.")
    rata_belanja = df[belanja_cols].mean().sort_values(ascending=False).rename("Rata-rata").reset_index()
    rata_belanja.columns = ["Bidang belanja", "Rata-rata"]
    fig_rank = px.bar(
        rata_belanja, x="Rata-rata", y="Bidang belanja", orientation="h",
        title="Rata-rata Belanja per Bidang (rentang tahun terpilih)"
    )
    st.plotly_chart(fig_rank, use_container_width=True)

# Hubungan belanja pendidikan/kesehatan dengan IPM
st.subheader("4. Hubungan Belanja Pendidikan dan Kesehatan dengan IPM")
relasi = [c for c in ["bm_pendidikan", "bm_kesehatan", "IPM"] if c in df.columns]
if len(relasi) == 3:
    col1, col2 = st.columns(2)
    with col1:
        fig_pend = px.scatter(
            df, x="bm_pendidikan", y="IPM", trendline="ols", text="Tahun",
            title="Belanja Pendidikan dan IPM",
            labels={"bm_pendidikan": "Belanja pendidikan", "IPM": "IPM"}
        )
        fig_pend.update_traces(textposition="top center")
        st.plotly_chart(fig_pend, use_container_width=True)
    with col2:
        fig_kes = px.scatter(
            df, x="bm_kesehatan", y="IPM", trendline="ols", text="Tahun",
            title="Belanja Kesehatan dan IPM",
            labels={"bm_kesehatan": "Belanja kesehatan", "IPM": "IPM"}
        )
        fig_kes.update_traces(textposition="top center")
        st.plotly_chart(fig_kes, use_container_width=True)

    korelasi = df[["bm_pendidikan", "bm_kesehatan", "IPM"]].corr()
    st.write("Korelasi antarindikator (korelasi menunjukkan hubungan, bukan bukti sebab-akibat).")
    st.dataframe(korelasi.style.format("{:.2f}"), use_container_width=True)

# Tabel data
st.subheader("5. Data Kota Batam yang Digunakan")
st.dataframe(df, use_container_width=True, hide_index=True)

csv = df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="⬇️ Unduh data Kota Batam (CSV)",
    data=csv,
    file_name="data_kota_batam.csv",
    mime="text/csv"
)

with st.expander("Keterangan indikator"):
    st.markdown("""
    - **PAD**: Pendapatan Asli Daerah.
    - **DBH**: Dana Bagi Hasil.
    - **DAU**: Dana Alokasi Umum.
    - **DAK**: Dana Alokasi Khusus.
    - **IPM**: Indeks Pembangunan Manusia.
    - **bm_***: kelompok belanja menurut bidang sesuai nama kolom pada dataset.
    - **Catatan analisis**: hubungan statistik tidak otomatis berarti satu indikator menyebabkan perubahan indikator lain.
    """)

st.caption("Dashboard dibuat untuk mengeksplorasi data Kota Batam dari dataset yang diberikan; periksa definisi dan satuan indikator pada sumber asli sebelum menarik kesimpulan kebijakan.")

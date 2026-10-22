# ============================================================
# DASHBOARD ANALISIS PENJUALAN E-COMMERCE
# Jalankan: python -m streamlit run dashboard.py
# ============================================================

from pathlib import Path
import re
import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------
# 1. KONFIGURASI HALAMAN
# ------------------------------------------------------------
st.set_page_config(
    page_title="E-Commerce Sales Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# 2. TAMPILAN / CSS
# ------------------------------------------------------------
st.markdown("""
<style>
    .stApp { background: #f5f7fb; }
    [data-testid="stSidebar"] { background: #eef2ff; }
    .main-title { font-size: 2.15rem; font-weight: 800; color: #172554; }
    .subtitle { color: #64748b; margin-bottom: 1.2rem; }
    div[data-testid="stMetric"] {
        background: white; padding: 18px 20px; border-radius: 16px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 16px #0f172a0b;
    }
    div[data-testid="stMetricLabel"] { color: #64748b; }
    .insight {
        background: white; padding: 16px 18px; border-radius: 12px;
        border-left: 5px solid #6366f1; margin: 8px 0 18px 0;
        box-shadow: 0 4px 16px #0f172a0a;
    }
    .section-note { color: #64748b; font-size: 0.95rem; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 3. FUNGSI BANTU
# ------------------------------------------------------------
def normalisasi_nama_kolom(nama):
    """Samakan variasi penamaan kolom agar lebih mudah dicocokkan."""
    nama = str(nama).strip().lower()
    nama = re.sub(r"[^\w]+", "_", nama, flags=re.UNICODE)
    return nama.strip("_")

def cari_kolom(df, kandidat):
    """Cari kolom berdasarkan beberapa kemungkinan nama."""
    kolom = set(df.columns)
    for nama in kandidat:
        normal = normalisasi_nama_kolom(nama)
        if normal in kolom:
            return normal
    return None

def rupiah(nilai):
    try:
        return "Rp " + f"{float(nilai):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "Rp 0"

def bersihkan_teks(series):
    return series.astype("string").str.strip()

# ------------------------------------------------------------
# 4. CARI FILE DATA OTOMATIS
# Mencari CSV di folder dashboard.py dan subfolder data.
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
lokasi_dicari = [BASE_DIR, BASE_DIR / "data"]
csv_files = []
for folder in lokasi_dicari:
    if folder.exists():
        csv_files.extend(
            p for p in folder.glob("*.csv")
            if p.is_file() and not p.name.startswith("~$")
        )

# Hindari duplikat path
csv_files = list(dict.fromkeys(csv_files))

if not csv_files:
    st.error("File CSV belum ditemukan.")
    st.markdown(
        f"""
        **Folder yang diperiksa:** `{BASE_DIR}` dan `{BASE_DIR / 'data'}`

        **Cara memperbaiki:**
        1. Simpan file dataset `.csv` satu folder dengan `dashboard.py`, atau buat folder `data` lalu taruh CSV di dalamnya.
        2. Pastikan file bukan hanya `data.zip`; ekstrak ZIP terlebih dahulu.
        3. Jalankan ulang dashboard.
        """
    )
    st.stop()

# Prioritaskan nama file yang terlihat seperti dataset utama/clean
def skor_file(path):
    n = path.name.lower()
    skor = 0
    if "clean" in n: skor += 5
    if "ecommerce" in n or "e_commerce" in n: skor += 4
    if "sales" in n or "penjualan" in n: skor += 2
    if "indonesia" in n: skor += 1
    return skor

csv_files = sorted(csv_files, key=lambda p: (-skor_file(p), p.name.lower()))

# Jika ada beberapa CSV, biarkan pengguna memilih file yang benar.
nama_file = st.sidebar.selectbox(
    "📂 Pilih file dataset",
    options=csv_files,
    format_func=lambda p: str(p.relative_to(BASE_DIR)),
    help="Pilih dataset transaksi utama yang berisi tanggal, kategori, wilayah, dan pembayaran."
)

try:
    df = pd.read_csv(nama_file, low_memory=False)
except Exception as e:
    st.error(f"File CSV tidak bisa dibaca: {nama_file.name}")
    st.exception(e)
    st.stop()

if df.empty:
    st.error("Dataset berhasil dibaca, tetapi isinya kosong.")
    st.stop()

# Normalisasi nama kolom
df.columns = [normalisasi_nama_kolom(c) for c in df.columns]

# ------------------------------------------------------------
# 5. COCOKKAN NAMA KOLOM
# ------------------------------------------------------------
kolom_tanggal = cari_kolom(df, [
    "order_date", "tanggal_pesanan", "tanggal_transaksi", "tanggal",
    "transaction_date", "date", "waktu_pesanan"
])
kolom_status = cari_kolom(df, [
    "status_pesanan", "order_status", "status", "status_transaksi"
])
kolom_id = cari_kolom(df, [
    "order_id", "id_pesanan", "transaction_id", "id_transaksi", "invoice_id"
])
kolom_bayar = cari_kolom(df, [
    "total_pembayaran", "total_payment", "payment_total", "total_harga",
    "total_amount", "revenue", "sales", "amount", "nilai_transaksi"
])
kolom_qty = cari_kolom(df, [
    "total_qty", "jumlah_barang", "quantity", "qty", "jumlah_produk",
    "total_quantity", "kuantitas"
])
kolom_kategori = cari_kolom(df, [
    "product_categories", "kategori_produk", "kategori", "product_category",
    "category", "nama_kategori"
])
kolom_wilayah = cari_kolom(df, [
    "kota_kabupaten", "kabupaten_kota", "kabupaten", "kota",
    "city", "region", "wilayah", "shipping_city"
])

# Tampilkan diagnosa yang berguna jika dataset berbeda dari perkiraan.
kolom_wajib = {
    "Tanggal pesanan": kolom_tanggal,
    "Total pembayaran/pendapatan": kolom_bayar,
    "Jumlah barang": kolom_qty,
    "Kategori produk": kolom_kategori,
    "Kabupaten/kota": kolom_wilayah,
}
kolom_hilang = [nama for nama, kolom in kolom_wajib.items() if kolom is None]

if kolom_hilang:
    st.error("Beberapa kolom yang dibutuhkan belum ditemukan.")
    st.write("Kolom yang belum terdeteksi:", ", ".join(kolom_hilang))
    st.write("**Kolom yang tersedia di dataset ini:**")
    st.code(", ".join(df.columns), language="text")
    st.info(
        "Nama kolom dataset kamu mungkin berbeda. Kirim daftar kolom yang tampil di atas "
        "agar pemetaan bisa disesuaikan."
    )
    st.stop()

# Pastikan kolom numerik dan tanggal memiliki tipe yang sesuai.
df[kolom_tanggal] = pd.to_datetime(df[kolom_tanggal], errors="coerce", dayfirst=True)
df[kolom_bayar] = pd.to_numeric(df[kolom_bayar], errors="coerce").fillna(0)
df[kolom_qty] = pd.to_numeric(df[kolom_qty], errors="coerce").fillna(0)
df[kolom_kategori] = bersihkan_teks(df[kolom_kategori]).fillna("Tidak diketahui")
df[kolom_wilayah] = bersihkan_teks(df[kolom_wilayah]).fillna("Tidak diketahui")

# Status transaksi: jika ada kolom status, prioritaskan transaksi selesai.
if kolom_status:
    status = bersihkan_teks(df[kolom_status]).str.lower()
    selesai = status.isin(["selesai", "completed", "complete", "delivered", "success", "berhasil"])
    if selesai.any():
        data = df.loc[selesai].copy()
        catatan_status = "Hanya transaksi berstatus selesai yang digunakan."
    else:
        data = df.copy()
        catatan_status = (
            "Tidak ditemukan label status 'selesai/completed/delivered'; "
            "semua baris digunakan. Periksa status dataset."
        )
else:
    data = df.copy()
    catatan_status = "Dataset tidak memiliki kolom status; semua baris digunakan."

data["tahun_dashboard"] = data[kolom_tanggal].dt.year
data = data.dropna(subset=["tahun_dashboard"]).copy()
data["tahun_dashboard"] = data["tahun_dashboard"].astype(int)

if data.empty:
    st.error("Tidak ada tanggal transaksi yang berhasil dibaca. Periksa format kolom tanggal.")
    st.stop()

# ------------------------------------------------------------
# 6. SIDEBAR FILTER
# ------------------------------------------------------------
st.sidebar.title("🎛️ Filter Dashboard")
st.sidebar.caption("Pilih tahun dan wilayah untuk mengubah grafik.")

tahun_tersedia = sorted(data["tahun_dashboard"].unique().tolist())
wilayah_tersedia = sorted(data[kolom_wilayah].dropna().unique().tolist())

tahun_dipilih = st.sidebar.multiselect(
    "Tahun transaksi", options=tahun_tersedia, default=tahun_tersedia
)
wilayah_dipilih = st.sidebar.multiselect(
    "Wilayah", options=wilayah_tersedia, default=wilayah_tersedia
)

filtered = data.copy()
if tahun_dipilih:
    filtered = filtered[filtered["tahun_dashboard"].isin(tahun_dipilih)]
else:
    filtered = filtered.iloc[0:0]
if wilayah_dipilih:
    filtered = filtered[filtered[kolom_wilayah].isin(wilayah_dipilih)]
else:
    filtered = filtered.iloc[0:0]

# ------------------------------------------------------------
# 7. HEADER
# ------------------------------------------------------------
st.markdown('<div class="main-title">🛍️ E-Commerce Sales Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Ringkasan pendapatan, tren tahunan, dan perilaku pembelian berdasarkan wilayah.</div>',
    unsafe_allow_html=True,
)
st.caption(f"Dataset: {nama_file.name} · {catatan_status}")

if filtered.empty:
    st.warning("Tidak ada data pada filter yang dipilih. Pilih minimal satu tahun dan satu wilayah di sidebar.")
    st.stop()

# ------------------------------------------------------------
# 8. KPI
# ------------------------------------------------------------
total_pendapatan = filtered[kolom_bayar].sum()
total_transaksi = (
    filtered[kolom_id].nunique()
    if kolom_id and kolom_id in filtered.columns
    else len(filtered)
)
total_barang = filtered[kolom_qty].sum()
rata_transaksi = total_pendapatan / total_transaksi if total_transaksi else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 Total Pendapatan", rupiah(total_pendapatan))
k2.metric("🧾 Total Transaksi", f"{total_transaksi:,.0f}".replace(",", "."))
k3.metric("📦 Jumlah Barang", f"{total_barang:,.0f}".replace(",", "."))
k4.metric("🛒 Rata-rata per Transaksi", rupiah(rata_transaksi))

st.divider()

# ------------------------------------------------------------
# 9. PERTANYAAN 1: PRODUK/KATEGORI DENGAN PENDAPATAN TERTINGGI
# ------------------------------------------------------------
st.header("1. 💰 Produk atau kategori dengan pendapatan tertinggi")
st.markdown('<div class="section-note">Kategori diurutkan berdasarkan jumlah total pembayaran.</div>', unsafe_allow_html=True)

pendapatan_kategori = (
    filtered.groupby(kolom_kategori, dropna=False)[kolom_bayar]
    .sum().sort_values(ascending=False).reset_index()
)
pendapatan_kategori.columns = ["Kategori", "Pendapatan"]
top_pendapatan = pendapatan_kategori.head(10).sort_values("Pendapatan", ascending=True)

if not top_pendapatan.empty:
    fig = px.bar(
        top_pendapatan, x="Pendapatan", y="Kategori", orientation="h",
        text="Pendapatan", color="Pendapatan",
        color_continuous_scale=["#c7d2fe", "#4f46e5"],
        title="Top 10 Kategori berdasarkan Pendapatan",
    )
    fig.update_traces(texttemplate="%{x:,.0f}", textposition="outside", cliponaxis=False)
    fig.update_layout(height=460, showlegend=False, coloraxis_showscale=False,
                      margin=dict(l=10, r=40, t=60, b=10), yaxis_title="", xaxis_title="Pendapatan (Rp)")
    st.plotly_chart(fig, use_container_width=True)
    pemenang = pendapatan_kategori.iloc[0]
    st.markdown(
        f'<div class="insight">💡 <b>Insight:</b> Kategori dengan pendapatan tertinggi adalah '
        f'<b>{pemenang["Kategori"]}</b>, sebesar <b>{rupiah(pemenang["Pendapatan"])}</b>.</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("Belum ada data kategori untuk ditampilkan.")

# ------------------------------------------------------------
# 10. PERTANYAAN 2: TREN PENJUALAN SETIAP TAHUN
# ------------------------------------------------------------
st.header("2. 📈 Bagaimana tren penjualan setiap tahun?")
tren = (
    filtered.groupby("tahun_dashboard", as_index=False)[kolom_bayar]
    .sum().sort_values("tahun_dashboard")
)
tren.columns = ["Tahun", "Pendapatan"]

if not tren.empty:
    fig_tren = px.line(
        tren, x="Tahun", y="Pendapatan", markers=True,
        title="Tren Pendapatan Tahunan",
        labels={"Pendapatan": "Pendapatan (Rp)", "Tahun": "Tahun"},
    )
    fig_tren.update_traces(line=dict(width=3, color="#4f46e5"), marker=dict(size=9))
    fig_tren.update_layout(height=400, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_tren, use_container_width=True)

    if len(tren) >= 2:
        sebelumnya = tren.iloc[-2]["Pendapatan"]
        terbaru = tren.iloc[-1]["Pendapatan"]
        perubahan = ((terbaru - sebelumnya) / abs(sebelumnya) * 100) if sebelumnya else None
        if perubahan is not None:
            arah = "meningkat 📈" if perubahan > 0 else ("menurun 📉" if perubahan < 0 else "stabil ➡️")
            st.markdown(
                f'<div class="insight">💡 <b>Insight:</b> Pendapatan tahun {int(tren.iloc[-1]["Tahun"])} '
                f'{arah} sebesar <b>{abs(perubahan):.2f}%</b> dibandingkan tahun {int(tren.iloc[-2]["Tahun"])}.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("Pendapatan tahun sebelumnya bernilai nol, sehingga persentase perubahan tidak dihitung.")
    else:
        st.info("Pilih rentang yang mencakup minimal dua tahun untuk melihat perubahan tahunan.")

# ------------------------------------------------------------
# 11. PERTANYAAN 3: KATEGORI TERLARIS DI KABUPATEN BOGOR
# ------------------------------------------------------------
st.header("3. 📍 Kategori apa yang paling banyak dibeli di Kabupaten Bogor?")
wilayah_norm = filtered[kolom_wilayah].astype(str).str.upper().str.strip()
bogor = filtered[
    wilayah_norm.str.contains(r"KAB(\.|UPATEN)?\s*BOGOR|KAB\s*BOGOR", regex=True, na=False)
].copy()

# Jika label wilayah dataset memakai nama lain, jangan mengarang hasil.
if bogor.empty:
    st.warning(
        "Belum ditemukan label wilayah yang cocok dengan 'Kabupaten Bogor' pada filter saat ini. "
        "Pilih semua wilayah di sidebar, lalu cek ejaan nama wilayah pada dataset."
    )
    with st.expander("Lihat nama wilayah yang tersedia"):
        st.write(wilayah_tersedia)
else:
    kategori_bogor = (
        bogor.groupby(kolom_kategori, as_index=False)[kolom_qty]
        .sum().sort_values(kolom_qty, ascending=False)
    )
    kategori_bogor.columns = ["Kategori", "Jumlah Barang"]
    top_bogor = kategori_bogor.head(10).sort_values("Jumlah Barang", ascending=True)

    fig_bogor = px.bar(
        top_bogor, x="Jumlah Barang", y="Kategori", orientation="h",
        text="Jumlah Barang", color="Jumlah Barang",
        color_continuous_scale=["#bbf7d0", "#059669"],
        title="Top 10 Kategori Paling Banyak Dibeli — Kabupaten Bogor",
    )
    fig_bogor.update_traces(textposition="outside", cliponaxis=False)
    fig_bogor.update_layout(height=460, showlegend=False, coloraxis_showscale=False,
                            margin=dict(l=10, r=35, t=60, b=10), yaxis_title="", xaxis_title="Jumlah barang")
    st.plotly_chart(fig_bogor, use_container_width=True)

    if not kategori_bogor.empty:
        pemenang_bogor = kategori_bogor.iloc[0]
        st.markdown(
            f'<div class="insight">💡 <b>Insight Kabupaten Bogor:</b> Kategori paling banyak dibeli adalah '
            f'<b>{pemenang_bogor["Kategori"]}</b>, dengan total <b>{pemenang_bogor["Jumlah Barang"]:,.0f} barang</b>.</div>',
            unsafe_allow_html=True,
        )
        st.subheader("🏆 Ranking kategori di Kabupaten Bogor")
        tabel = kategori_bogor.copy()
        tabel.insert(0, "Peringkat", range(1, len(tabel) + 1))
        st.dataframe(tabel.head(10), use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# 12. DATA PREVIEW & DOWNLOAD
# ------------------------------------------------------------
with st.expander("🔎 Lihat contoh data yang sedang dianalisis"):
    st.write(f"Jumlah baris setelah filter: {len(filtered):,}")
    st.dataframe(filtered.head(100), use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download data hasil filter (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name="data_dashboard_hasil_filter.csv",
        mime="text/csv",
    )

st.divider()
st.markdown(
    "<div style='text-align:center;color:#64748b;padding:8px 0;'>"
    "🛍️ E-Commerce Sales Dashboard · Data Analysis & Visualization Project"
    "</div>",
    unsafe_allow_html=True,
)
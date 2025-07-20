import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import os

# --- Direktori output ---
if not os.path.exists("laporan_gizi"):
    os.makedirs("laporan_gizi")

# --- Fungsi umur detail dan tahun desimal ---
def hitung_umur_detail(tgl_lahir):
    today = datetime.today().date()
    rd = relativedelta(today, tgl_lahir)
    umur_teks = f"{rd.years} tahun {rd.months} bulan {rd.days} hari"
    umur_tahun_desimal = rd.years + rd.months / 12 + rd.days / 365.25
    return umur_teks, round(umur_tahun_desimal, 2)

# --- Fungsi kalkulasi Z-score HAZ berdasarkan WHO (kasar, untuk demo) ---
def calculate_haz(height, usia, sex):
    median_height = {
        'L': [109.2, 114.6, 120.0, 125.1, 130.1, 134.9],
        'P': [108.4, 113.7, 119.0, 124.2, 129.2, 134.0]
    }
    sd_height = {
        'L': [4.6, 4.9, 5.2, 5.5, 5.8, 6.0],
        'P': [4.5, 4.8, 5.1, 5.4, 5.7, 6.0]
    }
    index = usia - 5
    if index < 0 or index >= len(median_height[sex]):
        return None
    z = (height - median_height[sex][index]) / sd_height[sex][index]
    return round(z, 2)

# --- Fungsi saran dan PDF ---
def generate_tip(status):
    if status == "Stunting":
        return "Perlu peningkatan gizi, tidur cukup, dan cek rutin ke puskesmas."
    elif status == "Normal":
        return "Pertumbuhan baik! Terus pertahankan pola makan sehat."
    else:
        return "Data belum mencukupi atau perlu validasi ulang."

def generate_pdf(name, umur_teks, gender, height, weight, haz, status):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Laporan Status Gizi - StunTrack SD", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Nama: {name}", ln=True)
    pdf.cell(200, 10, txt=f"Umur: {umur_teks}", ln=True)
    pdf.cell(200, 10, txt=f"Jenis Kelamin: {'Laki-laki' if gender == 'L' else 'Perempuan'}", ln=True)
    pdf.cell(200, 10, txt=f"Tinggi Badan: {height} cm", ln=True)
    pdf.cell(200, 10, txt=f"Berat Badan: {weight} kg", ln=True)
    pdf.cell(200, 10, txt=f"Z-score HAZ: {haz}", ln=True)
    pdf.cell(200, 10, txt=f"Status: {status}", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt="Saran: " + generate_tip(status))

    filename = f"laporan_gizi/{name.replace(' ', '_')}_gizi.pdf"
    pdf.output(filename)
    return filename

# --- Streamlit UI ---
st.set_page_config(page_title="StunTrack SD", layout="centered")
st.title("📏 Deteksi Dini Stunting Anak SD")
st.markdown("_Pantau pertumbuhan anak-anak sekolah dasar dengan input tanggal lahir_")

with st.form("form_input"):
    name = st.text_input("Nama Anak")
    tgl_lahir = st.date_input("Tanggal Lahir", min_value=date(2010,1,1), max_value=date.today())
    gender = st.radio("Jenis Kelamin", ["Laki-laki", "Perempuan"])
    height = st.number_input("Tinggi Badan (cm)", min_value=50.0, max_value=180.0)
    weight = st.number_input("Berat Badan (kg)", min_value=10.0, max_value=80.0)
    kelas = st.selectbox("Kelas", ["1", "2", "3", "4", "5", "6"])
    submitted = st.form_submit_button("🔍 Cek Status Gizi")

if submitted:
    umur_teks, umur_tahun = hitung_umur_detail(tgl_lahir)
    usia_bulat = int(umur_tahun)

    st.info(f"Umur saat ini: **{umur_teks}** ({umur_tahun} tahun)")

    sex_code = 'L' if gender == "Laki-laki" else 'P'
    haz = calculate_haz(height, usia_bulat, sex_code)

    if haz is None:
        st.warning("Usia belum dalam rentang WHO (5–10 tahun).")
    else:
        status = "Stunting" if haz < -2 else "Normal"

        st.success(f"Status: **{status}** (Z-score: {haz})")
        st.progress(min(max((haz + 3) / 6, 0.0), 1.0))
        st.caption(generate_tip(status))

        # Simpan ke CSV
        new_data = pd.DataFrame([[name, umur_teks, gender, kelas, height, weight, haz, status]],
            columns=["Nama", "Umur", "Gender", "Kelas", "Tinggi", "Berat", "HAZ", "Status"])
        if not os.path.isfile("data_stunting.csv"):
            new_data.to_csv("data_stunting.csv", index=False)
        else:
            new_data.to_csv("data_stunting.csv", mode='a', header=False, index=False)

        # PDF
        pdf_path = generate_pdf(name, umur_teks, sex_code, height, weight, haz, status)
        with open(pdf_path, "rb") as f:
            st.download_button("📄 Unduh PDF Laporan", f, file_name=pdf_path.split("/")[-1])

# --- Sidebar laporan kolektif ---
st.sidebar.header("📊 Rekap Sekolah")
if st.sidebar.button("Tampilkan Semua Data"):
    if os.path.exists("data_stunting.csv"):
        df = pd.read_csv("data_stunting.csv")
        st.sidebar.success("Data ditemukan")
        st.dataframe(df)

        # Grafik sederhana
        st.subheader("📈 Distribusi Anak Stunting per Kelas")
        st.caption("_Grafik anak yang termasuk kategori stunting_")
        chart_data = df[df['Status'] == 'Stunting'].groupby('Kelas').size()
        fig, ax = plt.subplots()
        chart_data.plot(kind='bar', ax=ax, color='salmon')
        ax.set_xlabel("Kelas")
        ax.set_ylabel("Jumlah Anak")
        ax.set_title("Jumlah Anak Stunting per Kelas")
        st.pyplot(fig)
    else:
        st.sidebar.warning("Belum ada data.")

# Laporan Pembaruan DUKPNSFULL Agustus

Dibuat: 03-08-2026 15:31 WIB

## Hasil

- Total objek Agustus: **845**.
- Disalin dari April lalu diperbarui dari daftar Agustus: **838**.
- Dibuat dari `datamentahdetail.txt`: **7**.
- Komposisi status: PNS 249, CPNS 9, PPPK 587.
- Semua objek memiliki 52 key dengan nama dan urutan yang sama seperti `DUKPNSFULLapril.json`.
- Urutan output mengikuti nomor urut 1–845 pada daftar Agustus.

## Pegawai baru yang berhasil dibuat dari detail Agustus

- 199107072015071002 — ACHMAD HUSEIN HARAHAP, S.STP (pendidikan 3, pangkat 3, jabatan 7).
- 198009292000122001 — AISYAH RAMBE, S.STP, M.A.P (pendidikan 5, pangkat 6, jabatan 10).
- 198609112010012040 — HARISMAH, SEI (pendidikan 4, pangkat 3, jabatan 10).
- 198204202010012027 — IRMA SARAH MANURUNG, S.E. (pendidikan 4, pangkat 4, jabatan 8).
- 198101212011011007 — JULHERMAN LUBIS, S.H. (pendidikan 4, pangkat 4, jabatan 7).
- 198203102010012029 — MARTINI AKBAR, S.T. (pendidikan 4, pangkat 4, jabatan 9).
- 198703042015031002 — RIO FERNANDO MANIK, S.H. (pendidikan 1, pangkat 3, jabatan 7).

## Pembaruan yang diterapkan pada pegawai lama

- Nama/gelar, status/kedudukan, tempat-tanggal lahir, golongan, jabatan, dan SKPD diambil dari daftar Agustus.
- `gelarDepan`/`gelarBelakang` berhasil diselaraskan untuk **377** pegawai yang nama/gelarnya berubah.
- Detail pendidikan terakhir berhasil diselaraskan untuk **172** pegawai.

## Data yang tidak dapat diperbarui atau perlu diperhatikan

1. `datamentahdetail.txt` hanya berisi detail 7 pegawai baru. Karena itu data pribadi, kontak, dokumen, dan seluruh riwayat 838 pegawai lama tetap berasal dari snapshot April, kecuali field ringkasan serta gelar/pendidikan terakhir yang disebutkan di atas.
2. Halaman riwayat diklat tidak tersedia pada `datamentahdetail.txt`. `riwayatDiklatStruktural` dan `riwayatDiklatLainnya` untuk ketujuh pegawai baru diisi string kosong agar tipenya mengikuti pola file April.
3. Ada **3** pegawai dengan golongan Agustus yang tidak cocok dengan entri terakhir riwayat pangkat yang tersedia. Golongan ringkasan sudah diperbarui, tetapi detail SK/TMT pangkat tidak diubah karena sumbernya tidak tersedia:
   - 198107252010011008 — ALVHANT SYAFRI: III/D → IV/A.
   - 198305202010011029 — KOKO MAGRISA FAISAL SIREGAR, S.E.: III/C → III/D.
   - 198006112008012019 — MIRANDA: II/D → III/A.

4. Ada **35** pegawai dengan jabatan dan/atau SKPD Agustus yang berbeda dari entri terakhir `riwayatJabatan`. Field ringkasan sudah diperbarui, tetapi detail SK/TMT riwayat tidak diubah tanpa sumber riwayat terbaru:
   - 196811241990071001 — AHMAD SAI SAMOSIR, S.SOS, M.SI (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Pengadministrasi Pajak → ringkasan Agustus: PENGOLAH DATA DAN INFORMASI.
     - SKPD riwayat: Badan Pengelola Pajak dan Retribusi Daerah Kota Medan → ringkasan Agustus: SUB BIDANG PEMBUKUAN DAN PELAPORAN BIDANG HOTEL, RESTORAN, DAN HIBURAN BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 198009292000122001 — AISYAH RAMBE, S.STP, M.A.P (berbeda: SKPD)
     - SKPD riwayat: Dinas Pemuda dan Olahraga Kota Medan → ringkasan Agustus: BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 200002032025051001 — ALIF RIZKY PURWANTO, S.KOM (berbeda: jabatan)
     - Jabatan riwayat: CALON PENATA KELOLA SISTEM DAN TEKNOLOGI INFORMASI → ringkasan Agustus: KOSONG.
   - 197809172010011008 — ANDRY HASAN NASUTION, S.E. (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Plt. Kasubbag Keuangan → ringkasan Agustus: PENGOLAH DATA DAN INFORMASI.
     - SKPD riwayat: Dinas Pemberdayaan Perempuan, Perlindungan Anak dan Pemberdayaan Masyarakat Kota Medan → ringkasan Agustus: SUB BIDANG TEKNIS BEA PEROLEHAN HAK ATAS TANAH DAN BANGUNAN DAN PAJAK BUMI DAN BANGUNAN BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 198601222010012034 — ANGGI ANGGRIANI , S.E, M.SC, M.A (berbeda: jabatan)
     - Jabatan riwayat: Penyusun Program Anggaran dan Pelaporan → ringkasan Agustus: PENELAAH TEKNIS KEBIJAKAN.
   - 196901052007011006 — ARSAD HUSIN (berbeda: jabatan, SKPD)
     - Jabatan riwayat: PENSIUN → ringkasan Agustus: PENGADMINISTRASI PERKANTORAN.
     - SKPD riwayat: PENSIUN → ringkasan Agustus: SUB BIDANG TEKNIS HOTEL, RESTORAN, DAN HIBURAN BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 196808031989031007 — BAMBANG HENDRATMO, SE, M.M (berbeda: jabatan, SKPD)
     - Jabatan riwayat: PENSIUN → ringkasan Agustus: PENGOLAH DATA DAN INFORMASI.
     - SKPD riwayat: PENSIUN → ringkasan Agustus: SUB BIDANG PEMBUKUAN DAN PELAPORAN BIDANG HOTEL, RESTORAN, DAN HIBURAN BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 197112082007011022 — DEDY SUHENDRA (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Pengadministrasi Keuangan → ringkasan Agustus: PENELAAH TEKNIS KEBIJAKAN.
     - SKPD riwayat: Badan Pengelola Pajak dan Retribusi Daerah Kota Medan → ringkasan Agustus: SEKRETARIAT BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 196901021996032003 — DRA FITRIATI HASIBUAN, M.M (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Sub Koordinator Lingkup Keuangan Badan Pengelola Pajak dan Retribusi Daerah Kota Medan → ringkasan Agustus: ANALIS KEUANGAN PUSAT DAN DAERAH MUDA.
     - SKPD riwayat: Badan Pengelola Pajak dan Retribusi Daerah Kota Medan → ringkasan Agustus: BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 199809222025051002 — FOLKEN BERG SETIAWAN ARUAN, S.AK. (berbeda: jabatan)
     - Jabatan riwayat: CALON PRANATA KEWILAYAHAN → ringkasan Agustus: KOSONG.
   - 199503292025052003 — GOMGOM TRIMINAR SIRINGORINGO, S.PN. (berbeda: jabatan)
     - Jabatan riwayat: CALON PRANATA KEWILAYAHAN → ringkasan Agustus: KOSONG.
   - 197901222010012008 — HAIRANI, A.MD. (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Pengolah Data Berkas Sengketa → ringkasan Agustus: PENGOLAH DATA DAN INFORMASI.
     - SKPD riwayat: Badan Pendapatan Daerah Kota Medan → ringkasan Agustus: SUB BAGIAN UMUM BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 198609112010012040 — HARISMAH, SEI (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Pengola Data dan Informasi → ringkasan Agustus: PENGOLAH DATA DAN INFORMASI.
     - SKPD riwayat: Bagian Perencanaan Dan Keuangan Sekretariat Daerah Kota Medan → ringkasan Agustus: BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 196906171990091001 — HENDRA ASMILAN, S.IP., M.A.P. (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Pengelola PBB P2 dan BPHTB → ringkasan Agustus: KEPALA SUB BIDANG KEBERATAN DAN SENGKETA BADAN PENDAPATAN DAERAH KOTA MEDAN.
     - SKPD riwayat: Badan Pendapatan Daerah Kota Medan → ringkasan Agustus: SUB BIDANG KEBERATAN DAN SENGKETA BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 199403192025052001 — LILIS ATIKA MANURUNG, S.E. (berbeda: jabatan)
     - Jabatan riwayat: CALON PRANATA KEWILAYAHAN → ringkasan Agustus: KOSONG.
   - 196812122008012006 — LILY TRISNA, S.T.P, MM (berbeda: jabatan, SKPD)
     - Jabatan riwayat: PENSIUN → ringkasan Agustus: PENATA LAYANAN OPERASIONAL.
     - SKPD riwayat: PENSIUN → ringkasan Agustus: BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 200011082025052001 — LIZA NOVIANTI, S.AK. (berbeda: jabatan)
     - Jabatan riwayat: CALON PRANATA KEWILAYAHAN → ringkasan Agustus: KOSONG.
   - 198411302002121003 — DR. M. AGHA NOVRIAN, S.STP, M.SI (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Sekretaris Dinas Pemuda dan Olahraga Kota Medan → ringkasan Agustus: KEPALA BADAN PENDAPATAN DAERAH KOTA MEDAN.
     - SKPD riwayat: Sekretariat Dinas Pemuda dan Olahraga Kota Medan → ringkasan Agustus: BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 198203262011011006 — MARADONA HERDIN SIREGAR, S.M (berbeda: jabatan)
     - Jabatan riwayat: Ketua Tim Kerja Lingkup Hukum dan Publikasi Pajak dan Retribusi Daerah Badan Pendapatan Daerah Kota Medan → ringkasan Agustus: PENELAAH TEKNIS KEBIJAKAN.
   - 200008182025051001 — MHD WAWIN ALBANI, S.AK. (berbeda: jabatan)
     - Jabatan riwayat: CALON PRANATA KEWILAYAHAN → ringkasan Agustus: KOSONG.
   - 199906252025052002 — NUR ANNISA NASUTION, S.KOM (berbeda: jabatan)
     - Jabatan riwayat: CALON PENATA KELOLA SISTEM DAN TEKNOLOGI INFORMASI → ringkasan Agustus: KOSONG.
   - 197602062009031005 — PARUHUMAN SIREGAR, S.T. (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Pengelola PBB P2 dan BPHTB → ringkasan Agustus: PENGOLAH DATA DAN INFORMASI.
     - SKPD riwayat: Badan Pendapatan Daerah Kota Medan → ringkasan Agustus: SUB BIDANG TEKNIS BEA PEROLEHAN HAK ATAS TANAH DAN BANGUNAN DAN PAJAK BUMI DAN BANGUNAN BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 197606022002121006 — RICKY NELSON BUDIMAN SIHITE, SE, MSE (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Sub Koordinator Lingkup Penyusunan Program Badan Pengelola Pajak dan Retribusi Daerah Kota Medan → ringkasan Agustus: PERENCANA MUDA.
     - SKPD riwayat: Badan Pengelola Pajak dan Retribusi Daerah Kota Medan → ringkasan Agustus: BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 197808232009021002 — RISDIANTO (berbeda: jabatan)
     - Jabatan riwayat: PEMBERHENTIAN DENGAN HORMAT TIDAK ATAS PERMINTAAN SENDIRI SEBAGAI PEGAWAI NEGERI SIPIL → ringkasan Agustus: PENGADMINISTRASI PERKANTORAN.
   - 197410131997032004 — ROSANA FODESTA SIMANJUNTAK, SE, MM (berbeda: jabatan)
     - Jabatan riwayat: Ketua Tim Kerja Lingkup Keberatan dan Sengketa Bidang Parkir, Reklame, Penerangan Jalan, Air Tanah, Sarang Burung Walet, dan Retribusi Badan Pendapatan Daerah Kota Medan → ringkasan Agustus: PENELAAH TEKNIS KEBIJAKAN.
   - 198009222006042003 — ROSAWATI FORTUNA TANJUNG, ST (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Penelaah Teknis Kebijakan → ringkasan Agustus: KEPALA SUB BAGIAN TATA USAHA UPT PAJAK DAN RETRIBUSI WILAYAH III BADAN PENDAPATAN DAERAH KOTA MEDAN.
     - SKPD riwayat: Sub Bidang Teknis Hotel, Restoran, dan Hiburan Badan Pendapatan Daerah Kota Medan → ringkasan Agustus: SUB BAGIAN TATA USAHA UPT PAJAK DAN RETRIBUSI WILAYAH III BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 197909232010012016 — SURIYATI, S.SOS, M.A.P. (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Analis Peserta Didik → ringkasan Agustus: PENGOLAH DATA DAN INFORMASI.
     - SKPD riwayat: Dinas Pendidikan dan Kebudayaan Kota Medan → ringkasan Agustus: BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 198610092012122002 — T RINI SRI MEKA, S.I.P, M.H (berbeda: jabatan)
     - Jabatan riwayat: Arsiparis → ringkasan Agustus: ARSIPARIS PERTAMA.
   - 197405022006041010 — TEDDY ARMAYA, S.T. (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Verifikator Pajak → ringkasan Agustus: PENGOLAH DATA DAN INFORMASI.
     - SKPD riwayat: Badan Pendapatan Daerah Kota Medan → ringkasan Agustus: SUB BIDANG TEKNIS PARKIR, REKLAME, PENERANGAN JALAN, AIR TANAH, SARANG BURUNG WALET, DAN RETRIBUSI BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 199507052025052002 — TIUR NORITA SARI MANURUNG, S.H. (berbeda: jabatan)
     - Jabatan riwayat: CALON FASILITATOR PEMERINTAHAN → ringkasan Agustus: KOSONG.
   - 199310102017082001 — WIDYA SARASWATI PARIMORA, S.STP (berbeda: jabatan)
     - Jabatan riwayat: Analis Kepegawaian → ringkasan Agustus: ANALIS SUMBER DAYA MANUSIA APARATUR MUDA.
   - 197804272005021004 — YEMKI SATRIA, S.SOS, M.M. (berbeda: jabatan)
     - Jabatan riwayat: Pengolah Data Penagihan Pajak → ringkasan Agustus: PENELAAH TEKNIS KEBIJAKAN.
   - 199807172025052001 — YUNINGSIH, S.H (berbeda: jabatan)
     - Jabatan riwayat: CALON FASILITATOR PEMERINTAHAN → ringkasan Agustus: KOSONG.
   - 198601052005022001 — YUNITA HANIF, S.E., M.M. (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Ketua Tim Kerja Lingkup Komunikasi Pimpinan Bagian Protokol dan Komunikasi Pimpinan Sekretariat Daerah Kota Medan → ringkasan Agustus: KEPALA SUB BIDANG PERENCANAAN, PENGEMBANGAN, DAN EVALUASI PAJAK DAERAH BADAN PENDAPATAN DAERAH KOTA MEDAN.
     - SKPD riwayat: Bagian Protokol Dan Komunikasi Pimpinan Sekretariat Daerah Kota Medan → ringkasan Agustus: SUB BIDANG PERENCANAAN, PENGEMBANGAN, DAN EVALUASI PAJAK DAERAH BADAN PENDAPATAN DAERAH KOTA MEDAN.
   - 197107121996021001 — ZULFAKHRI AHMADI, S.SOS (berbeda: jabatan, SKPD)
     - Jabatan riwayat: Sekretaris Dinas Kebersihan dan Pertamanan Kota Medan → ringkasan Agustus: PENGOLAH DATA DAN INFORMASI.
     - SKPD riwayat: Dinas Kebersihan dan Pertamanan Kota Medan → ringkasan Agustus: SUB BIDANG TEKNIS BEA PEROLEHAN HAK ATAS TANAH DAN BANGUNAN DAN PAJAK BUMI DAN BANGUNAN BADAN PENDAPATAN DAERAH KOTA MEDAN.

5. Field profil yang memang kosong pada sumber detail pegawai baru:
   - 199107072015071002 — ACHMAD HUSEIN HARAHAP, S.STP: `nipLama`, `kota`, `kecamatan`, `kelurahan`, `rt`, `rw`, `kodePos`, `noTel`, `email`, `marga`, `cacat`, `ciriKhas`, `hobi`, `askes`, `gelarDepan`, `statusPernikahan`, `rambut`, `bentukMuka`, `warnaKulit`.
   - 198009292000122001 — AISYAH RAMBE, S.STP, M.A.P: `noTel`, `cacat`, `ciriKhas`, `gelarDepan`.
   - 198609112010012040 — HARISMAH, SEI: `nipLama`, `kota`, `rt`, `rw`, `kodePos`, `noTel`, `marga`, `cacat`, `ciriKhas`, `hobi`, `gelarDepan`, `rambut`, `bentukMuka`, `warnaKulit`.
   - 198204202010012027 — IRMA SARAH MANURUNG, S.E.: `nipLama`, `noTel`, `cacat`, `gelarDepan`.
   - 198101212011011007 — JULHERMAN LUBIS, S.H.: `nipLama`, `rt`, `rw`, `noTel`, `cacat`, `gelarDepan`.
   - 198203102010012029 — MARTINI AKBAR, S.T.: `rt`, `rw`, `noTel`, `marga`, `cacat`, `ciriKhas`, `gelarDepan`.
   - 198703042015031002 — RIO FERNANDO MANIK, S.H.: `nipLama`, `rt`, `rw`, `kodePos`, `noTel`, `suku`, `marga`, `cacat`, `ciriKhas`, `hobi`, `gelarDepan`, `statusPernikahan`, `rambut`, `bentukMuka`, `warnaKulit`.

6. Tidak ada kegagalan pemisahan gelar pada nama yang berubah.

7. Semua halaman pendidikan, pangkat, dan jabatan untuk 7 pegawai baru berhasil dibaca.

## Pegawai April yang tidak dimasukkan karena tidak ada di daftar Agustus

- 196805021990071001 — ILHAM NUR, S.E, MM.
- 196807161991031003 — RUSHENDRI, S.SOS, M.SI.
- 197110161997031005 — HERIDJON TUMPAL MARGANDA SIHOMBING, S.SOS, M.SI.
- 198502242025211056 — ANANDA ABDINESIA SITEPU.

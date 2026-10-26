# Catatan perubahan DUK Oktober

## Sumber dan cakupan

- Acuan data Agustus: `DUKPNSFULLagustus.json`.
- Daftar Oktober: `pegawaiBapendaOktober.xlsx`.
- Data profil tambahan untuk empat pegawai: `databaru.txt`.
- Pencocokan pegawai dilakukan berdasarkan NIP yang dinormalisasi menjadi angka saja.
- JSON Oktober memuat 847 pegawai: 843 NIP cocok dengan Agustus dan 4 pegawai hanya ada di daftar Oktober.

## Pegawai Agustus yang dikeluarkan dari roster Oktober

Nama berikut tidak tercantum di workbook Oktober, sehingga tidak dimasukkan ke `dataOktober`. Ini hanya menandai perbedaan daftar, bukan kesimpulan tentang status kerja mereka.

- BAMBANG HENDRATMO, SE, M.M
- ZULFAKHRI AHMADI, S.SOS

## Empat profil Oktober yang dilengkapi

Data profil dan riwayat yang tersedia di `databaru.txt` ditambahkan ke empat entri Oktober berikut:

- ADIANTO R HARAHAP, S.H.
- DEDE AMBIA, S.Tr.I.P.
- NAMIRA OKITA ZAHRA SIREGAR, S.Tr.IP
- RATIH SORAYA

Riwayat pangkat diisi dari sumber tersebut jika tersedia. Adianto R Harahap tidak memiliki tabel riwayat pangkat pada data sumber. Pangkat Oktober tidak dapat dibandingkan langsung karena workbook tidak menyediakan kolom pangkat/golongan.

## Sembilan CPNS tanpa jabatan

Sembilan baris dengan jabatan kosong ditandai sebagai CPNS. Unit kerja profil diselaraskan dengan workbook Oktober:

- ALIF RIZKY PURWANTO, S.KOM — Badan Pendapatan Daerah Kota Medan
- FOLKEN BERG SETIAWAN ARUAN, S.AK. — Badan Pendapatan Daerah Kota Medan
- GOMGOM TRIMINAR SIRINGORINGO, S.PN. — UPT Pajak Dan Retribusi Wilayah II Badan Pendapatan Daerah Kota Medan
- LILIS ATIKA MANURUNG, S.E. — UPT Pajak Dan Retribusi Wilayah V Badan Pendapatan Daerah Kota Medan
- LIZA NOVIANTI, S.AK. — UPT Pajak Dan Retribusi Wilayah VI Badan Pendapatan Daerah Kota Medan
- MHD WAWIN ALBANI, S.AK. — UPT Pajak Dan Retribusi Wilayah I Badan Pendapatan Daerah Kota Medan
- NUR ANNISA NASUTION, S.KOM — Badan Pendapatan Daerah Kota Medan
- TIUR NORITA SARI MANURUNG, S.H. — Badan Pendapatan Daerah Kota Medan
- YUNINGSIH, S.H — Badan Pendapatan Daerah Kota Medan

## Perubahan jabatan dan unit kerja

Jabatan dan unit kerja saat ini pada profil diselaraskan dengan nilai workbook Oktober. Jabatan cocok untuk 834 pegawai; 9 jabatan kosong dicatat sebagai CPNS. Satu unit kerja berbeda dari data Agustus:

- AISYAH RAMBE, S.STP, M.A.P: `BADAN PENDAPATAN DAERAH KOTA MEDAN` → `UPT Pajak Dan Retribusi Wilayah I Badan Pendapatan Daerah Kota Medan`

Nama seluruh 843 pegawai dengan NIP cocok sama. Pendidikan: 795 sama persis, 1 berbeda istilah tetapi setara (`S-1 / Sarjana` vs `S-1`), 36 berbeda rincian pada jenjang yang sama, dan 11 kosong di workbook Oktober. Workbook tidak memuat kolom pangkat/golongan, sehingga pangkat tidak dapat dibandingkan.

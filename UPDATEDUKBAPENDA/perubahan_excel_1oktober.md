# Log pembaruan DUK per 1 Oktober 2026

## Status

Selesai. Workbook Oktober dibuat sebagai file baru. Workbook Agustus digunakan sebagai sumber awal dan tidak ditimpa.

## Sumber

- `DUK BAPENDA KOTA MEDAN 2026 1 Agustus 2026.xlsx` — roster dan data pendidikan yang dipertahankan jika data Oktober kosong.
- `dukpnsfulloktober.json` — acuan PNS, CPNS, PPPK penuh waktu, nama, jabatan, unit kerja, status, dan profil.
- `Copy of data baru.xlsx` — acuan nama, jabatan, unit kerja, dan pendidikan PPPK paruh waktu.

Pencocokan utama memakai NIP. Untuk baris Copy dengan NIP yang tidak cocok, nama yang hanya mengarah ke satu profil JSON digunakan untuk menentukan identitas; NIP pada keluaran mengikuti JSON.

## Keputusan pengguna

- ASWAN (`197606042025211047`) sudah meninggal dan dikeluarkan dari roster Oktober.
- ANNA SARI HASIBUAN (`196904161988102001`) sudah meninggal dan tidak ditambahkan ke workbook.
- RISDIANTO (`197808232009021002`) dikeluarkan dari workbook.
- ADIANTO R HARAHAP, DEDE AMBIA, NAMIRA OKITA ZAHRA SIREGAR, dan RATIH SORAYA ditempatkan pada Bidang 4.
- Jika pendidikan kosong pada data Oktober, pertahankan pendidikan dari workbook Agustus.

## Pegawai dikeluarkan

Baris berikut ada pada workbook Agustus tetapi tidak ada pada daftar Oktober, sehingga dihapus dari roster Oktober:

- BAMBANG HENDRATMO, NIP `196808031989031007`.
- ZULFAKHRI AHMADI, NIP `197107121996021001`.
- RISDIANTO, NIP `197808232009021002`, sesuai arahan pengguna.

ASWAN dan ANNA SARI HASIBUAN juga tidak muncul pada workbook keluaran. Keduanya tidak menjadi penghapusan baris lama: ASWAN tidak ada di tiga tab roster Agustus, sedangkan ANNA tidak ada pada roster Agustus dan tidak jadi ditambahkan. Nama YUDHA PUTRA RISDIANTO tetap tercantum karena orang dan NIP-nya berbeda dari RISDIANTO yang dikeluarkan.

## Pegawai ditambahkan dan dipindahkan

Empat pegawai PNS yang belum ada pada roster Agustus ditambahkan ke lembar utama dan lembar PNS, seluruhnya pada blok Bidang 4:

- ADIANTO R HARAHAP, NIP `198602062011011011`.
- DEDE AMBIA, NIP `199904032023081002`.
- NAMIRA OKITA ZAHRA SIREGAR, NIP `199907202022082001`.
- RATIH SORAYA, NIP `198502072014122002`.

Perpindahan blok yang diterapkan:

- AISYAH RAMBE: Bidang 4 → UPT 1, mengikuti unit kerja di JSON Oktober.
- WINDA ARDILA POHAN: UPT 7 → Sekretariat, mengikuti unit kerja di file Copy.
- YUDHA HENDRAWAN: UPT 5 → Sekretariat, mengikuti unit kerja di file Copy.

Untuk menetapkan blok PPPK paruh waktu, ejaan UPT singkat dan variasi OCR pada label wilayah dinormalisasi hanya saat membaca kategorinya. Teks unit kerja di workbook tetap mengikuti sumber Copy.

## PPPK paruh waktu

- 538 dari 540 pegawai cocok dengan profil di file Copy. Jika ada beberapa baris Copy untuk orang yang sama, baris paling akhir dipakai.
- Ada 21 baris Copy dengan NIP yang tidak cocok ke identitasnya; kecocokan nama tunggal dipakai dan NIP keluaran mengikuti JSON.
- MUHAMMAD IQBAL SIREGAR (`199611172025211047`) dan ULFA HUDAYAH (`199009282025212071`) tidak ditemukan di file Copy. Data jabatan dan pendidikan Agustus dipertahankan; unit kerja diselaraskan dengan JSON.
- Unit kerja untuk 538 pegawai yang cocok mengikuti Copy. Nama, jabatan, pendidikan, dan detail profil diisi sesuai sumber yang tersedia.

## Pendidikan kosong pada data Oktober

Data Oktober memiliki 11 profil tanpa nilai pendidikan. Sesuai arahan, pendidikan pada workbook Agustus dipertahankan untuk 10 pegawai yang masuk roster Oktober:

- ABDUL AZIS AMIN SITORUS
- ATIKA AULIA SYAHFITRI
- MARNO
- MEDAHENY GM
- RATU TRIANA DEWI
- SAPARUDDIN HARAHAP
- T. IRWANSYAH
- TAUFIK
- TIARA MASHITA
- YUDHA HENDRAWAN

Profil kesebelas adalah ASWAN; ia tidak dimasukkan ke workbook. Pendidikan PNS dan PPPK penuh waktu yang tersedia di JSON diperbarui dari data Oktober. Untuk PPPK paruh waktu, Copy dipakai sebagai acuan pendidikan kecuali pada 10 nama di atas yang mengikuti keputusan untuk mempertahankan data Agustus.

## Rekapitulasi dan jumlah akhir

Rekapitulasi per unit diperbarui untuk roster Oktober. Rumus penomoran dan rekap disiapkan untuk dihitung ulang saat workbook dibuka di Excel.

- PNS/CPNS: 258.
- PPPK penuh waktu: 46.
- PPPK paruh waktu: 540.
- Jumlah lembar utama: 844.

Jumlah per blok unit pada rekapitulasi:

| Unit | PNS/CPNS | PPPK penuh waktu | PPPK paruh waktu |
|---|---:|---:|---:|
| Sekretariat | 41 | 14 | 90 |
| Bidang 1 | 45 | 4 | 30 |
| Bidang 2 | 39 | 5 | 47 |
| Bidang 3 | 49 | 6 | 65 |
| Bidang 4 | 28 | 3 | 4 |
| UPT 1 | 8 | 2 | 40 |
| UPT 2 | 9 | 2 | 45 |
| UPT 3 | 9 | 2 | 41 |
| UPT 4 | 8 | 2 | 48 |
| UPT 5 | 5 | 2 | 46 |
| UPT 6 | 11 | 2 | 49 |
| UPT 7 | 6 | 2 | 35 |

Pangkat/golongan PNS mengikuti riwayat yang tersedia pada JSON. JSON perbandingan Oktober tidak menyediakan pembaruan pangkat/golongan, sehingga perubahan pangkat untuk Oktober tidak dapat dipastikan dari sumber ini. Kolom golongan PPPK yang tidak tersedia pada JSON dibiarkan mengikuti workbook Agustus.

## Pemeriksaan keluaran

- File XLSX lolos pemeriksaan struktur arsip dan dapat dibuka kembali dengan `openpyxl`.
- Keanggotaan NIP dan jumlah baris pada lembar utama serta tiga lembar kategori sesuai: 844, 258, 46, dan 540; tidak ada NIP ganda.
- Nama yang ditetapkan untuk dikeluarkan tidak tersisa pada roster yang sesuai; empat pegawai baru, tiga perpindahan blok, dan 10 nilai pendidikan yang dipertahankan diperiksa kembali.
- Pemeriksaan visual/render Excel tidak dilakukan; validasi ini memeriksa struktur dan isi workbook.

## File keluaran

`DUK BAPENDA KOTA MEDAN 2026 1 Oktober 2026.xlsx`

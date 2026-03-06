import json
import pandas as pd
import os
from collections import defaultdict

def create_bezzeting(json_file, output_file):
    print(f"Membaca data dari {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Total data: {len(data)}")
    
    # helper for golongan & pendidikan
    def get_pendidikan(emp):
        pend = "-"
        jurusan = "-"
        riw = emp.get("riwayatPendidikan")
        if riw and isinstance(riw, list) and len(riw) > 0:
            last = riw[-1]
            if isinstance(last, dict):
                pend = last.get("tingkatPendidikan", "-")
                jurusan = last.get("jurusan", "-")
        return pend, jurusan
        
    def get_golongan(emp):
        gol = emp.get("golonganTerakhir", "-")
        if not gol:
            riw = emp.get("riwayatPangkat")
            if riw and isinstance(riw, list) and len(riw) > 0:
                last = riw[-1]
                if isinstance(last, dict):
                    gol = last.get("pangkat", "-")
        return gol if gol else "-"

    def get_diklat(emp):
        diklats = []
        riw = emp.get("riwayatDiklatStruktural")
        if riw and isinstance(riw, list):
            for i, d in enumerate(riw):
                if isinstance(d, dict) and "namaDiklat" in d:
                    diklats.append(f"{i+1}. {d.get('namaDiklat')}")
        if diklats:
            return "(" + "\n".join(diklats) + ")"
        return "()"

    sheet1_data = []
    jabatan_groups = defaultdict(list)
    
    for i, emp in enumerate(data):
        pend, jur = get_pendidikan(emp)
        gol = get_golongan(emp)
        
        row1 = {
            "No": i + 1,
            "NIP": emp.get("nip", "-"),
            "Nama Pegawai": emp.get("namaWithGelar", emp.get("nama", "-")),
            "Tempat Lahir": emp.get("tempatLahir", "-"),
            "Tanggal Lahir": emp.get("tanggalLahir", "-"),
            "Jenis Kelamin": emp.get("jenisKelamin", "-"),
            "Agama": emp.get("agama", "-"),
            "Status Kepegawaian": emp.get("statusKepegawaian", "-"),
            "Pangkat / Golongan": gol,
            "Jabatan": emp.get("jabatanTerakhir", "-"),
            "Unit Kerja (SKPD)": emp.get("skpd", "-"),
            "Pendidikan Terakhir": pend,
            "Jurusan Pendidikan": jur,
            "Kedudukan": emp.get("kedudukan", "-")
        }
        sheet1_data.append(row1)
        
        jab_name = emp.get("jabatanTerakhir", "")
        if not jab_name:
            jab_name = "-"
        jabatan_groups[jab_name].append(emp)

    df1 = pd.DataFrame(sheet1_data)
    
    sheet2_data = []
    no_jabatan = 1
    
    def jab_sort_key(item):
        jab = str(item[0]).upper()
        if jab == "-" or not jab: return (999, jab)
        if jab.startswith("KEPALA BADAN"): return (1, jab)
        if jab.startswith("SEKRETARIS"): return (2, jab)
        if jab.startswith("KEPALA BIDANG"): return (3, jab)
        if jab.startswith("KEPALA UPT"): return (4, jab)
        if jab.startswith("KEPALA SUB"): return (5, jab)
        if "KEPALA" in jab: return (10, jab)
        return (50, jab)
    
    for jab, emps in sorted(jabatan_groups.items(), key=jab_sort_key):
        if jab == "KEPALA BIDANG BEA PEROLEHAN HAK ATAS TANAH DAN BANGUNAN DAN PAJAK BUMI DAN BANGUNAN BADAN PENDAPATAN DAERAH KOTA MEDAN":
            sheet2_data.append({
                "No": no_jabatan,
                "Jabatan Terakhir": "KEPALA BIDANG TEKNIS HOTEL, RESTORAN, DAN HIBURAN BADAN PENDAPATAN DAERAH KOTA MEDAN",
                "Jumlah": "-",
                "Nama": "-",
                "Diklat": "-",
                "Pendidikan": "-",
                "Jurusan Terakhir": "-",
                "Golongan": "-",
                "Kedudukan": "-"
            })
            no_jabatan += 1
            
        jumlah = len(emps)
        for i, emp in enumerate(emps):
            pend, jur = get_pendidikan(emp)
            gol = get_golongan(emp)
            diklat = get_diklat(emp)
            nama = f"{i+1}) {emp.get('namaWithGelar', emp.get('nama', '-'))}"
            kedud = emp.get("statusKepegawaian", "-")
            
            row2 = {
                "No": no_jabatan if i == 0 else "",
                "Jabatan Terakhir": jab if i == 0 else "",
                "Jumlah": jumlah if i == 0 else "",
                "Nama": nama,
                "Diklat": diklat,
                "Pendidikan": pend,
                "Jurusan Terakhir": jur,
                "Golongan": gol,
                "Kedudukan": kedud
            }
            sheet2_data.append(row2)
        no_jabatan += 1
            
    df2 = pd.DataFrame(sheet2_data)

    print(f"Menyimpan ke Excel: {output_file}...")
    try:
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            df1.to_excel(writer, sheet_name='Data Lengkap', index=False)
            df2.to_excel(writer, sheet_name='Bezzeting', index=False)
            
            # Formatting
            workbook = writer.book
            worksheet = writer.sheets['Bezzeting']
            
            # Wrap text in Diklat column (E)
            wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
            top_format = workbook.add_format({'valign': 'top'})
            
            # Set columns width
            worksheet.set_column('A:A', 5, top_format)
            worksheet.set_column('B:B', 40, top_format)
            worksheet.set_column('C:C', 8, top_format)
            worksheet.set_column('D:D', 35, top_format)
            worksheet.set_column('E:E', 40, wrap_format)
            worksheet.set_column('F:F', 15, top_format)
            worksheet.set_column('G:G', 15, top_format)
            worksheet.set_column('H:H', 20, top_format)
            
    except Exception as e:
        print(f"ExcelWriter dengan xlsxwriter gagal, mencoba default.. Error: {e}")
        with pd.ExcelWriter(output_file) as writer:
            df1.to_excel(writer, sheet_name='Data Lengkap', index=False)
            df2.to_excel(writer, sheet_name='Bezzeting', index=False)
            
    print("Selesai!")

if __name__ == "__main__":
    base_dir = "/Users/nevv/Documents/scraping"
    json_path = os.path.join(base_dir, "DUKPNSFULL.json")
    out_path = os.path.join(base_dir, "Bezzeting_Pegawai.xlsx")
    
    create_bezzeting(json_path, out_path)

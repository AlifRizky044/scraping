import pandas as pd
import json
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

def normalize_str(s):
    if not isinstance(s, str) or str(s).lower() == 'nan':
        return ""
    # Remove dots, commas, extra spaces, and uppercase
    s = s.strip().upper()
    s = s.replace(".", "").replace(",", "")
    s = re.sub(r'\s+', ' ', s)
    return s

def get_golongan_rank(pangkat_str):
    ranks = {
        'IV/E': 17, 'IV/D': 16, 'IV/C': 15, 'IV/B': 14, 'IV/A': 13,
        'III/D': 12, 'III/C': 11, 'III/B': 10, 'III/A': 9,
        'II/D': 8, 'II/C': 7, 'II/B': 6, 'II/A': 5,
        'I/D': 4, 'I/C': 3, 'I/B': 2, 'I/A': 1
    }
    pangkat_str = str(pangkat_str).upper()
    if "(" in pangkat_str and ")" in pangkat_str:
        gol = pangkat_str.split("(")[1].split(")")[0].strip()
        return ranks.get(gol, 0)
    return 0

def get_eselon_rank(eselon_str):
    ranks = {
        'II.A': 10, 'II.B': 9,
        'III.A': 8, 'III.B': 7,
        'IV.A': 6, 'IV.B': 5,
        'V.A': 4, 'V.B': 3,
        '-': 0, 'NON ESELON': 0
    }
    return ranks.get(normalize_str(eselon_str), 0)

def main():
    template_file = 'DUK FORMAT.xlsx'
    df_template = pd.read_excel(template_file, header=None, dtype=str)
    
    # Aggressively clean 'nan' strings from the entire dataframe
    df_template = df_template.fillna('')
    for col in df_template.columns:
        df_template[col] = df_template[col].astype(str).replace(['nan', 'NaN', 'NAN', 'None'], '')
        df_template[col] = df_template[col].str.strip()

    headers_df = df_template.iloc[:5].copy()
    data_df = df_template.iloc[5:].copy()
    
    # Read JSON
    with open('DUKPNSFULL.json', 'r') as f:
        json_data = json.load(f)
        
    pns_data = [d for d in json_data if d.get('statusKepegawaian') in ['PNS', 'CPNS']]
    
    # Group employees by SKPD and sort by DUK rules
    def get_duk_sort_key(e):
        rj = e.get('riwayatJabatan', [])
        latest_rj = rj[-1] if rj else {}
        rp = e.get('riwayatPangkat', [])
        latest_rp = rp[-1] if rp else {}
        eselon = get_eselon_rank(latest_rj.get('eselon', ''))
        gol = get_golongan_rank(latest_rp.get('pangkat', ''))
        mkg = 0
        try: mkg = int(latest_rp.get('mkgTahun', 0))
        except: pass
        return (-eselon, -gol, -mkg)

    skpd_pools = {}
    for emp in pns_data:
        rj = emp.get('riwayatJabatan', [])
        latest_rj = rj[-1] if rj else {}
        skpd = normalize_str(latest_rj.get('skpd', emp.get('skpd', '')))
        if skpd not in skpd_pools: skpd_pools[skpd] = []
        skpd_pools[skpd].append(emp)
    
    # Sort each pool by DUK
    for s in skpd_pools:
        skpd_pools[s].sort(key=get_duk_sort_key)

    placed_nips = set()
    processed_rows = []
    
    # Phase 1: Match by Exact Jabatan + fill empty slots
    for idx, row in data_df.iterrows():
        excel_jabatan = normalize_str(row[14])
        excel_skpd = normalize_str(row[16])
        excel_name = str(row[1]).strip()
        
        matched_emp = None
        pool = skpd_pools.get(excel_skpd, [])
        
        # Priority 1: Exact Jabatan Match within same SKPD
        if excel_jabatan:
            for i, emp in enumerate(pool):
                rj = emp.get('riwayatJabatan', [])
                emp_jab = normalize_str(rj[-1].get('jabatan', '')) if rj else ""
                if emp_jab == excel_jabatan:
                    matched_emp = pool.pop(i)
                    break
        
        # Priority 2: Fill if slot is a "person slot" but no exact match found
        if matched_emp is None:
            is_potential_person_slot = False
            # Check if this row is likely for a person (has a name in template OR a jabatan that isn't structural/header)
            if excel_name != "":
                is_potential_person_slot = True
            elif excel_jabatan != "" and not any(k in excel_jabatan.upper() for k in ["DAFTAR", "URUT", "KEPANGKATAN", "PEGAWAI", "ASN"]):
                is_potential_person_slot = True
                
            if is_potential_person_slot and pool:
                matched_emp = pool.pop(0)

        if matched_emp:
            nip_val = str(matched_emp.get('nip', '')).strip()
            placed_nips.add(nip_val)
            new_row = build_row(matched_emp, nip_val)
            if not new_row[16]:
                new_row[16] = str(row[16]).strip()
        else:
            new_row = [str(val) for val in row.values]
            if excel_name != "" and not any(k in excel_name.upper() for k in ["KEPALA", "BIDANG", "SEKRETARIAT"]):
                # Clear personal data if no replacement found
                for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17, 18, 19, 21, 22, 23, 24, 25, 26]:
                    if i < len(new_row): new_row[i] = ""
            
        processed_rows.append(new_row)
        
    # Phase 2: Append remaining employees
    all_remaining = []
    for s in skpd_pools:
        for emp in skpd_pools[s]:
            all_remaining.append(emp)
            
    all_remaining.sort(key=lambda e: (normalize_str(e.get('skpd', '')), get_duk_sort_key(e)))
    for emp in all_remaining:
        nip = str(emp.get('nip', '')).strip()
        if nip not in placed_nips:
            new_row = build_row(emp, nip)
            processed_rows.append(new_row)
            placed_nips.add(nip)
        
    # Phase 2.5: Hotel Rule
    mover_jab_target = "KEPALA BIDANG HOTEL, RESTORAN, DAN HIBURAN"
    target_jab_target = "KEPALA SUB BIDANG TEKNIS HOTEL, RESTORAN, DAN HIBURAN"
    mover_row = None
    for i, row in enumerate(processed_rows):
        jab = str(row[14]).strip().upper()
        if mover_jab_target in jab:
            mover_row = processed_rows.pop(i)
            break
            
    if mover_row:
        target_idx = -1
        for i, row in enumerate(processed_rows):
            jab = str(row[14]).strip().upper()
            if target_jab_target in jab:
                target_idx = i
                break
        
        if target_idx != -1:
            processed_rows.insert(target_idx, mover_row)
        else:
            processed_rows.append(mover_row)

    # Phase 3: Numbering
    for i, row in enumerate(processed_rows):
        row[0] = i + 1

    # Final sanity check: Replace any None with ''
    cleaned_final_rows = []
    for row in processed_rows:
        cleaned_final_rows.append([str(v) if v is not None and str(v).lower() != 'nan' else "" for v in row])

    df_output_data = pd.DataFrame(cleaned_final_rows)
    df_final = pd.concat([headers_df, df_output_data], ignore_index=True)
    
    output_filename = 'DUK_PNS_OUTPUT.xlsx'
    with pd.ExcelWriter(output_filename) as writer:
        df_final.to_excel(writer, index=False, header=False)
        
    print(f"Generated {output_filename} successfully with {len(cleaned_final_rows)} records (Hierarchical Fill/Update).")

def build_row(emp, nip):
    def safe_get(d, key, default=""):
        val = d.get(key, default)
        if val is None: return default
        return str(val)

    row = [""] * 44
    row[1] = safe_get(emp, 'namaWithGelar', emp.get('nama', '')).upper()
    row[2] = f"'{nip}"
    
    rp = emp.get('riwayatPangkat', [])
    if isinstance(rp, list) and len(rp) > 0:
        pt = rp[-1]
        row[3] = safe_get(pt, 'mkgTahun')
        row[4] = safe_get(pt, 'mkgBulan')
        row[8] = safe_get(pt, 'pangkat')
        p_str = safe_get(pt, 'pangkat')
        gol = ""
        if "(" in p_str and ")" in p_str:
            gol = p_str.split("(")[1].split(")")[0]
        row[9] = gol.upper() if gol else ""
        row[10] = safe_get(pt, 'noSk')
        row[11] = safe_get(pt, 'pejabatPenandatangan')
        row[12] = safe_get(pt, 'tmt')
        cpns = rp[0]
        row[5] = safe_get(cpns, 'pangkat')
        c_str = safe_get(cpns, 'pangkat')
        row[6] = ""
        if "(" in c_str and ")" in c_str:
            row[6] = c_str.split("(")[1].split(")")[0].upper()
        row[7] = safe_get(cpns, 'tmt')
        
    rj = emp.get('riwayatJabatan', [])
    if isinstance(rj, list) and len(rj) > 0:
        jt = rj[-1]
        row[13] = safe_get(jt, 'tipeJabatan')
        row[14] = safe_get(jt, 'jabatan').upper()
        row[15] = safe_get(jt, 'eselon')
        row[16] = safe_get(jt, 'skpd').upper()
        row[17] = safe_get(jt, 'tmt')
        row[18] = safe_get(jt, 'tmtSk')
        row[20] = safe_get(jt, 'pejabatPenetapan')

    if not row[16]:
        row[16] = safe_get(emp, 'skpd').upper()
        
    rpend = emp.get('riwayatPendidikan', [])
    if isinstance(rpend, list) and len(rpend) > 0:
        pt = rpend[-1]
        row[21] = safe_get(pt, 'tingkatPendidikan')
        row[22] = safe_get(pt, 'jurusan')
        row[23] = safe_get(pt, 'namaSekolah')
        row[24] = safe_get(pt, 'tanggalIjazah')
        
    rdiklat = emp.get('riwayatDiklatStruktural', [])
    if isinstance(rdiklat, list) and len(rdiklat) > 0:
        dt = rdiklat[-1]
        row[25] = safe_get(dt, 'namaDiklat')
        
    tgl_lahir_str = emp.get('tanggalLahir', '')
    if tgl_lahir_str:
        try:
            b_date = datetime.strptime(tgl_lahir_str, '%Y-%m-%d')
            eselon_str = row[15]
            bup_age = 60 if isinstance(eselon_str, str) and eselon_str.startswith('II.') else 58
            bup_date = b_date + relativedelta(years=bup_age, months=1)
            bup_date = bup_date.replace(day=1)
            row[26] = bup_date.strftime('%d-%m-%Y')
        except:
            row[26] = ''
    
    row[28] = safe_get(emp, 'helper')
    row[29] = safe_get(emp, 'statusKepegawaian')
    row[30] = safe_get(emp, 'agama')
    row[31] = safe_get(emp, 'statusPernikahan')
    row[32] = safe_get(emp, 'jenisKelamin')
    row[33] = safe_get(emp, 'golDarah')
    row[34] = safe_get(emp, 'noHp')
    row[35] = safe_get(emp, 'email')
    
    ttl = emp.get('tempatTglLahir', '')
    row[36] = ttl.replace('\n', ' ') if ttl else ""
    row[37] = safe_get(emp, 'alamat')
    row[38] = safe_get(emp, 'provinsi')
    row[39] = safe_get(emp, 'kota')
    row[40] = safe_get(emp, 'kecamatan')
    row[41] = safe_get(emp, 'kelurahan')
    row[42] = safe_get(emp, 'rt')
    row[43] = safe_get(emp, 'rw')
    return row

if __name__ == '__main__':
    main()

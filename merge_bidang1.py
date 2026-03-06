import pandas as pd
import re
import difflib
from difflib import SequenceMatcher

# Configuration
MASTER_FILE = '/Users/nevv/Documents/scraping/data/master data bidang 1.xlsx'
DATA_FILE = '/Users/nevv/Documents/scraping/data/bidang1 nop.xls'
OUTPUT_FILE = '/Users/nevv/Documents/scraping/data/HASIL_GABUNGAN_BIDANG_1.xlsx'

def clean_nip(val):
    if pd.isna(val):
        return None
    s = str(val)
    if s.endswith('.0'):
        s = s[:-2]
    s = re.sub(r'[^0-9]', '', s)
    if not s:
        return None
    return s

def format_nop(val):
    if pd.isna(val):
        return None
    if isinstance(val, float):
            return f"{val:.0f}"
    s = str(val)
    if s.endswith('.0'):
        s = s[:-2]
    return s

def similarity(a, b):
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def run():
    print("Loading Master Data Bidang 1...")
    # Read Master
    df_master = pd.read_excel(MASTER_FILE, dtype={'NIP': str, 'NOP PBB': str})
    df_master.columns = df_master.columns.astype(str).str.strip()
    
    # Rename for consistency (case-insensitive)
    cols_map = {c.upper(): c for c in df_master.columns}
    rename_map = {}
    if 'NAMA' in cols_map: rename_map[cols_map['NAMA']] = 'NAMA_MASTER'
    if 'NIP' in cols_map: rename_map[cols_map['NIP']] = 'NIP_MASTER'
    if 'GOL' in cols_map: rename_map[cols_map['GOL']] = 'GOLONGAN_TERAKHIR'
    if 'JABATAN' in cols_map: rename_map[cols_map['JABATAN']] = 'JABATAN_MASTER'
    if 'NOP PBB' in cols_map: rename_map[cols_map['NOP PBB']] = 'NOP_MASTER'
    elif 'NOP' in cols_map: rename_map[cols_map['NOP']] = 'NOP_MASTER'
    
    df_master = df_master.rename(columns=rename_map)
    
    # Clean NIP and Create Key (First 15 chars)
    df_master['NIP_CLEAN'] = df_master['NIP_MASTER'].apply(clean_nip)
    df_master = df_master.dropna(subset=['NIP_CLEAN'])
    df_master['NIP_KEY'] = df_master['NIP_CLEAN'].str[:15]
    
    print(f"Master Loaded: {len(df_master)} rows.")
    
    # ---------------- LOAD PBB DATA ----------------
    print("Loading PBB Data...")
    xl = pd.ExcelFile(DATA_FILE)
    print(f"Available Sheets: {xl.sheet_names}")
    
    # Find PBB Sheet
    pbb_sheet_name = None
    for sheet in xl.sheet_names:
        if 'PBB ASN' in sheet:
            pbb_sheet_name = sheet
            break
            
    if not pbb_sheet_name:
        print("Error: Could not find PBB ASN sheet.")
        return

    print(f"Reading PBB Sheet: '{pbb_sheet_name}'")
    # Sheet name has trailing space based on inspection
    df_pbb = pd.read_excel(DATA_FILE, sheet_name=pbb_sheet_name, header=2, dtype=str)
    
    # Columns expected: NO, NAMA, NIP, GOL, JABATAN, NOP PBB
    # Clean NIP
    df_pbb['NIP_CLEAN'] = df_pbb['NIP'].apply(clean_nip)
    df_pbb = df_pbb.dropna(subset=['NIP_CLEAN'])
    df_pbb['NIP_KEY'] = df_pbb['NIP_CLEAN'].str[:15]
    df_pbb = df_pbb.rename(columns={'NOP PBB': 'NOP_DATA', 'NAMA': 'NAMA_PBB'})
    
    # ---------------- LOAD VEHICLE DATA ----------------
    print("Loading Vehicle Data (Sheet: OPSEN ASN HRH)...")
    # Sheet name might not have trailing space? Inspection showed 'OPSEN ASN HRH'
    try:
        df_opsen = pd.read_excel(DATA_FILE, sheet_name='OPSEN ASN HRH', header=2, dtype=str)
    except:
        # Try with space if failed
        df_opsen = pd.read_excel(DATA_FILE, sheet_name='OPSEN ASN HRH ', header=2, dtype=str)

    # Columns: NO, NAMA, NIP, GOL, JABATAN, JENIS KENDARAAN, NO POLISI
    df_opsen['NIP_CLEAN'] = df_opsen['NIP'].apply(clean_nip)
    df_opsen = df_opsen.dropna(subset=['NIP_CLEAN'])
    df_opsen['NIP_KEY'] = df_opsen['NIP_CLEAN'].str[:15]
    
    # Handle Column Names (Strip whitespace)
    df_opsen.columns = df_opsen.columns.astype(str).str.strip()
    df_opsen = df_opsen.rename(columns={
        'NO POLISI': 'NO_POLISI_DATA', 
        'JENIS KENDARAAN': 'TIPE_KENDARAAN_DATA',
        'NAMA': 'NAMA_OPSEN'
    })
    
    # ---------------- MERGE PBB ----------------
    print("Merging Master + PBB...")
    merged = pd.merge(df_master, df_pbb[['NIP_KEY', 'NOP_DATA', 'NAMA_PBB']], on='NIP_KEY', how='left')
    
    # Fuzzy Match for PBB (if NOP missing)
    unmatched_pbb_mask = merged['NOP_DATA'].isna()
    unmatched_indices = merged[unmatched_pbb_mask].index
    
    # Pool of PBB data not used?
    # Actually, let's just match against ALL PBB data for simplicity, or unmatched ones.
    # Logic: If Master doesn't have NOP from key match, try to find Name match in PBB df
    
    print(f"Checking {len(unmatched_indices)} rows for Fuzzy PBB Match...")
    count_fuzzy_pbb = 0
    for idx in unmatched_indices:
        master_name = merged.at[idx, 'NAMA_MASTER']
        if pd.isna(master_name): continue
        
        best_score = 0
        best_nop = None
        
        for _, row in df_pbb.iterrows():
            score = similarity(master_name, row['NAMA_PBB'])
            if score > best_score:
                best_score = score
                best_nop = row['NOP_DATA']
        
        if best_score > 0.55:
            merged.at[idx, 'NOP_DATA'] = best_nop
            # print(f"  PBB Fuzzy: {master_name} -> {best_nop} ({best_score:.2f})")
            count_fuzzy_pbb += 1
            
    print(f"Fuzzy PBB Matches: {count_fuzzy_pbb}")

    # ---------------- MERGE VEHICLE ----------------
    print("Merging Result + Vehicle...")
    merged = pd.merge(merged, df_opsen[['NIP_KEY', 'NO_POLISI_DATA', 'TIPE_KENDARAAN_DATA', 'NAMA_OPSEN']], on='NIP_KEY', how='left')
    
    # Fuzzy Match for Vehicle
    unmatched_opsen_mask = merged['NO_POLISI_DATA'].isna()
    unmatched_opsen_indices = merged[unmatched_opsen_mask].index
    
    print(f"Checking {len(unmatched_opsen_indices)} rows for Fuzzy Vehicle Match...")
    count_fuzzy_opsen = 0
    for idx in unmatched_opsen_indices:
        master_name = merged.at[idx, 'NAMA_MASTER']
        if pd.isna(master_name): continue
        
        best_score = 0
        best_nopol = None
        best_tipe = None
        
        for _, row in df_opsen.iterrows():
            score = similarity(master_name, row['NAMA_OPSEN'])
            if score > best_score:
                best_score = score
                best_nopol = row['NO_POLISI_DATA']
                best_tipe = row['TIPE_KENDARAAN_DATA']
        
        if best_score > 0.55:
            merged.at[idx, 'NO_POLISI_DATA'] = best_nopol
            merged.at[idx, 'TIPE_KENDARAAN_DATA'] = best_tipe
            # print(f"  Vehicle Fuzzy: {master_name} -> {best_nopol} ({best_score:.2f})")
            count_fuzzy_opsen += 1

    print(f"Fuzzy Vehicle Matches: {count_fuzzy_opsen}")

    # ---------------- FINALIZE ----------------
    final_df = pd.DataFrame()
    final_df['No'] = range(1, len(merged) + 1)
    final_df['Nama'] = merged['NAMA_MASTER']
    final_df['NIP'] = merged['NIP_MASTER']
    final_df['Golongan Terakhir'] = merged['GOLONGAN_TERAKHIR']
    final_df['Jabatan'] = merged['JABATAN_MASTER']
    
    # NOP Logic: PBB Sheet -> Master Fallback
    final_df['NOP'] = merged['NOP_DATA'].fillna(merged['NOP_MASTER'])
    final_df['NOP'] = final_df['NOP'].apply(format_nop)
    
    final_df['Nomor Polisi Kendaraan'] = merged['NO_POLISI_DATA']
    final_df['Tipe Kendaraan'] = merged['TIPE_KENDARAAN_DATA']
    
    print("Saving to Excel...")
    final_df.to_excel(OUTPUT_FILE, index=False)
    print(f"Done! Saved to {OUTPUT_FILE}")
    print(final_df.head())

if __name__ == "__main__":
    run()

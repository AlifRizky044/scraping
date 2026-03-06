import pandas as pd
import re
import difflib
from difflib import SequenceMatcher

# Configuration
MASTER_FILE = '/Users/nevv/Documents/scraping/data/master data bidang 3.xlsx'
DATA_FILE = '/Users/nevv/Documents/scraping/data/STTS ASN DAN NON ASN BID. III(1).xlsx'
OUTPUT_FILE = '/Users/nevv/Documents/scraping/data/HASIL_GABUNGAN_BIDANG_3.xlsx'

def clean_nip(val):
    if pd.isna(val) or val == 'nan':
        return None
    s = str(val)
    if s.endswith('.0'):
        s = s[:-2]
    # Remove all non-numeric characters
    s = re.sub(r'[^0-9]', '', s)
    if not s:
        return None
    return s

def format_nop(val):
    if pd.isna(val) or val == 'nan' or not val:
        return None
    s = str(val)
    # Remove dots and spaces commonly found in NOP formatting
    s = re.sub(r'[^0-9]', '', s)
    if s.endswith('.0'):
        s = s[:-2]
    return s

def clean_name(name):
    if pd.isna(name):
        return ""
    s = str(name).lower()
    # Remove characters that are not letters or spaces
    s = re.sub(r'[^a-z\s]', ' ', s)
    # List of titles/degrees to remove (common in Indonesia)
    titles = [
        r'\bhj\b', r'\bh\b', r'\bdrs\b', r'\bdra\b', r'\bir\b', 
        r'\bse\b', r'\bmm\b', r'\bssos\b', r'\bsh\b', r'\bsstp\b', 
        r'\bsp\b', r'\bspi\b', r'\bst\b', r'\bmap\b', r'\bmsi\b',
        r'\bak\b', r'\bptk\b', r'\bap\b'
    ]
    for t in titles:
        s = re.sub(t, ' ', s)
    # Remove multiple spaces
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def similarity(a, b):
    # Use cleaned names for comparison
    return SequenceMatcher(None, clean_name(a), clean_name(b)).ratio()

def run():
    print("Loading Master Data Bidang 3...")
    # Read Master (Sheet name is 'Bidang 1' according to inspection)
    try:
        df_master = pd.read_excel(MASTER_FILE, sheet_name='Bidang 1', dtype={'NIP': str, 'NOP PBB': str})
    except:
        # Fallback to first sheet
        df_master = pd.read_excel(MASTER_FILE, sheet_name=0, dtype={'NIP': str, 'NOP PBB': str})

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
    
    # ---------------- LOAD DATA FILE ----------------
    print("Loading Data File (Sheet: ASN)...")
    # Data has headers at Row 1 (Index 1)
    df_data = pd.read_excel(DATA_FILE, sheet_name='ASN', header=1, dtype=str)
    
    # Clean columns
    df_data.columns = df_data.columns.astype(str).str.strip()
    
    # Identify key columns based on inspection: NAMA, NIP, NOP
    # The header names in the file are bit generic or messy
    # Re-assign if necessary? Inspection showed: NO, NAMA, NIP, GOL, JABATAN, NOP, KET
    # Let's trust the header=1 read.
    
    # Check if NIP column exists, if not use index
    if 'NIP' not in df_data.columns:
        print("Warning: 'NIP' column not found in data by name. Using index-based assignment.")
        # Based on inspection: Col 1 is Nama, Col 2 is NIP, Col 5 is NOP
        df_data.columns = ['NO', 'NAMA_DATA', 'NIP_DATA', 'GOL_DATA', 'JABATAN_DATA', 'NOP_DATA', 'KET_DATA']
    else:
        df_data = df_data.rename(columns={'NIP': 'NIP_DATA', 'NAMA': 'NAMA_DATA', 'NOP': 'NOP_DATA'})

    # Clean NIP
    df_data['NIP_CLEAN'] = df_data['NIP_DATA'].apply(clean_nip)
    # Don't drop NIP NaNs here! We want to keep PHL/NON-ASN for fuzzy matching
    
    # Create NIP_KEY only for those who HAVE a clean NIP
    df_data['NIP_KEY'] = df_data['NIP_CLEAN'].apply(lambda x: str(x)[:15] if x else None)
    
    print(f"Data File Loaded: {len(df_data)} rows ({df_data['NIP_CLEAN'].notna().sum()} with NIP).")

    # ---------------- MERGE ----------------
    print("Merging Data...")
    merged = pd.merge(df_master, df_data[['NIP_KEY', 'NOP_DATA', 'NAMA_DATA']], on='NIP_KEY', how='left')
    
    # Fuzzy Match
    unmatched_mask = merged['NOP_DATA'].isna()
    unmatched_indices = merged[unmatched_mask].index
    
    # Identify Unmatched Data Rows
    # Get NIP Keys that WERE matched
    matched_nip_keys = merged.loc[~merged['NOP_DATA'].isna(), 'NIP_KEY'].unique()
    
    # Filter Data to only those NOT matched yet by NIP
    unmatched_data_df = df_data[~df_data['NIP_KEY'].isin(matched_nip_keys)].copy()
    
    print(f"Checking {len(unmatched_indices)} master rows for Fuzzy Match...")
    print(f"Available Data Rows for Fuzzy: {len(unmatched_data_df)}")
    
    count_fuzzy = 0
    threshold = 0.70 # Increased for better precision with name cleaning
    
    for idx in unmatched_indices:
        master_name = merged.at[idx, 'NAMA_MASTER']
        if pd.isna(master_name) or not unmatched_data_df.empty == False: continue
        
        best_score = 0
        best_nop = None
        best_data_idx = -1
        
        for d_idx, row in unmatched_data_df.iterrows():
            score = similarity(master_name, row['NAMA_DATA'])
            if score > best_score:
                best_score = score
                best_nop = row['NOP_DATA']
                best_data_idx = d_idx
        
        if best_score >= threshold:
            merged.at[idx, 'NOP_DATA'] = best_nop
            match_name = unmatched_data_df.loc[best_data_idx, 'NAMA_DATA']
            print(f"  Fuzzy Match: '{master_name}' <--> '{match_name}' (Score: {best_score:.2f})")
            count_fuzzy += 1
            # Remove from pool
            unmatched_data_df = unmatched_data_df.drop(best_data_idx)
            
    print(f"Fuzzy Matches Added: {count_fuzzy}")

    # ---------------- FINALIZE ----------------
    final_df = pd.DataFrame()
    final_df['No'] = range(1, len(merged) + 1)
    final_df['Nama'] = merged['NAMA_MASTER']
    final_df['NIP'] = merged['NIP_MASTER']
    final_df['Golongan Terakhir'] = merged['GOLONGAN_TERAKHIR']
    final_df['Jabatan'] = merged['JABATAN_MASTER']
    
    # NOP Logic: Data Sheet -> Master Fallback
    final_df['NOP'] = merged['NOP_DATA'].fillna(merged['NOP_MASTER'])
    final_df['NOP'] = final_df['NOP'].apply(format_nop)
    
    # Bidang 3 doesn't seem to have vehicle info in this file
    final_df['Nomor Polisi Kendaraan'] = None
    final_df['Tipe Kendaraan'] = None
    
    print("Saving to Excel...")
    final_df.to_excel(OUTPUT_FILE, index=False)
    print(f"Done! Saved to {OUTPUT_FILE}")
    print(final_df.head())

if __name__ == "__main__":
    run()

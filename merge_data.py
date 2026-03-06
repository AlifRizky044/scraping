import pandas as pd
import numpy as np
import re

# File Paths
MASTER_FILE = '/Users/nevv/Documents/scraping/data/master bidang 2.xlsx'
STNK_FILE = '/Users/nevv/Documents/scraping/data/STNK DAN PBB - Copy(1).xlsx'
OUTPUT_FILE = '/Users/nevv/Documents/scraping/data/HASIL_GABUNGAN_MASTER_BIDANG_2.xlsx'

def clean_nip(val):
    if pd.isna(val):
        return None
    # Convert to string, remove spaces, non-numeric chars
    s = str(val)
    # Remove .0 if it exists
    if s.endswith('.0'):
        s = s[:-2]
    s = re.sub(r'[^0-9]', '', s)
    if not s:
        return None
    return s

def run():
    # Master file `master bidang 2.xlsx` has headers at row 0 (NO, NAMA, NIP, GOL, JABATAN, NOP PBB)
    # Force NIP and NOP PBB to be strings to avoid scientific notation
    df_master = pd.read_excel(MASTER_FILE, dtype={'NIP': str, 'NOP PBB': str})
    
    # Strip whitespace from column names
    df_master.columns = df_master.columns.astype(str).str.strip()
    print("Master columns (raw):", df_master.columns.tolist())
    
    # Simple mapping based on inspection (case-insensitive)
    cols_map = {c.upper(): c for c in df_master.columns}
    rename_map = {}
    if 'NAMA' in cols_map: rename_map[cols_map['NAMA']] = 'NAMA_MASTER'
    if 'NIP' in cols_map: rename_map[cols_map['NIP']] = 'NIP_MASTER'
    if 'GOL' in cols_map: rename_map[cols_map['GOL']] = 'GOLONGAN_TERAKHIR'
    if 'JABATAN' in cols_map: rename_map[cols_map['JABATAN']] = 'JABATAN_MASTER'
    if 'NOP PBB' in cols_map: rename_map[cols_map['NOP PBB']] = 'NOP_MASTER'
    elif 'NOP' in cols_map: rename_map[cols_map['NOP']] = 'NOP_MASTER'
    
    df_master = df_master.rename(columns=rename_map)
    
    # Basic Check
    if 'NIP_MASTER' not in df_master.columns:
        print("Error: NIP column not found in Master.")
        return

    df_master['NIP_CLEAN'] = df_master['NIP_MASTER'].apply(clean_nip)
    
    # Drop rows without NIP
    df_master = df_master.dropna(subset=['NIP_CLEAN'])
    
    # Keep columns
    cols_to_keep_master = ['NIP_CLEAN', 'NIP_MASTER', 'NAMA_MASTER', 'GOLONGAN_TERAKHIR', 'JABATAN_MASTER', 'NOP_MASTER']
    # Filter only existing columns just in case
    cols_to_keep_master = [c for c in cols_to_keep_master if c in df_master.columns]
    
    df_master_clean = df_master[cols_to_keep_master].drop_duplicates(subset=['NIP_CLEAN'])

    
    print(f"Master Data Loaded: {len(df_master_clean)} rows.")

    print("Reading STNK Data...")
    # STNK file has messy headers. Data starts around row 7 (index 7, row 8 in Excel).
    # Using header=None and manual assignment is safest based on inspection.
    # Col 3 is NIP, Col 7 is NOP. Force them to be strings.
    df_stnk = pd.read_excel(STNK_FILE, sheet_name='STNK&PBB ASN FIX', header=None, skiprows=7, converters={3: str, 7: str})
    
    # Manually assign columns based on verified inspection (Row 7 data)
    # Col 0: NO
    # Col 1: NAMA
    # Col 2: GOLONGAN (rank) -> Not needed but occupies index
    # Col 3: NIP
    # Col 4: JABATAN
    # Col 5: TIPE KENDARAAN
    # Col 6: NO POLISI
    # Col 7: NOP PBB
    
    # Ensure sufficient columns
    if df_stnk.shape[1] < 8:
        print("Warning: STNK file has fewer columns than expected.")
    
    new_columns = [
        'NO', 'NAMA', 'GOLONGAN', 'NIP', 'JABATAN', 
        'TIPE KENDARAAN', 'NO POLISI', 'NOP PBB'
    ]
    
    # Rename matching count
    current_cols = df_stnk.columns.tolist()
    if len(current_cols) >= len(new_columns):
        df_stnk.columns = new_columns + current_cols[len(new_columns):]
    else:
        df_stnk.columns = new_columns[:len(current_cols)]
    
    print("STNK columns assigned manually (corrected).")
    print("STNK Head (Check Columns):")
    print(df_stnk.head())
    
    # Clean NIP in STNK
    if 'NIP' in df_stnk.columns:
        df_stnk['NIP_CLEAN'] = df_stnk['NIP'].apply(clean_nip)
    else:
        print("Error: NIP column missing in STNK after manual assignment.")
        return
    
    # Create a robust key: First 15 chars (DOB + CPNS + Gender)
    # This ignores the Sequence number which seems to be the source of length errors
    df_master['NIP_KEY'] = df_master['NIP_CLEAN'].str[:15]
    df_stnk['NIP_KEY'] = df_stnk['NIP_CLEAN'].str[:15]
    
    # Check for duplicates in Master on Key
    if df_master['NIP_KEY'].duplicated().any():
        print("Warning: Duplicate NIP Keys (first 15 chars) in Master. Merge might duplicate rows.")
        # We can drop duplicates or just proceed. Master should be unique usually.
        # df_master = df_master.drop_duplicates(subset=['NIP_KEY'])
    
    print("Master Keys (sample):", df_master['NIP_KEY'].head().tolist())
    if not df_stnk.empty:
        print("STNK Keys (sample):", df_stnk['NIP_KEY'].head().tolist())
    
    # Merge: Left join on MASTER
    print("Merging Data (Master LEFT Join STNK on NIP Key)...")
    
    # Add index to tracking for STNK
    df_stnk['STNK_INDEX'] = df_stnk.index
    
    merged = pd.merge(df_master_clean.assign(NIP_KEY=df_master['NIP_KEY']), 
                      df_stnk, 
                      on='NIP_KEY', 
                      how='left',
                      suffixes=('', '_STNK'))
    
    print(f"Merged (NIP Match): {len(merged)} rows.")
    
    # ---------------- FUZZY MATCHING ----------------
    from difflib import SequenceMatcher
    
    def similarity(a, b):
        return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

    # Identify Unmatched Master Rows (No STNK info)
    # Check if 'NO POLISI' is NaN
    unmatched_mask = merged['NO POLISI'].isna()
    unmatched_master_indices = merged[unmatched_mask].index
    
    # Identify Unmatched STNK Rows (Not used in NIP merge)
    # Get STNK indices that WERE matched
    matched_stnk_indices = merged.loc[~merged['STNK_INDEX'].isna(), 'STNK_INDEX'].unique()
    
    # Filter STNK to only those NOT matched yet
    unnmatched_stnk_df = df_stnk[~df_stnk.index.isin(matched_stnk_indices)].copy()
    
    print(f"Unmatched Master Rows: {len(unmatched_master_indices)}")
    print(f"Unmatched STNK Rows Available: {len(unnmatched_stnk_df)}")
    
    fuzzy_matches_found = 0
    threshold = 0.55 # Tuned to avoid false positives (e.g., mismatching names with score 0.41)
    
    if not unnmatched_stnk_df.empty:
        print("Running Fuzzy Matching on Names...")
        for idx in unmatched_master_indices:
            master_name = merged.at[idx, 'NAMA_MASTER']
            if pd.isna(master_name):
                continue
                
            best_score = 0
            best_stnk_idx = -1
            
            # Iterate through available STNK rows
            for stnk_idx, row in unnmatched_stnk_df.iterrows():
                 stnk_name = row['NAMA']
                 if pd.isna(stnk_name):
                     continue
                 
                 score = similarity(master_name, stnk_name)
                 if score > best_score:
                     best_score = score
                     best_stnk_idx = stnk_idx
            
            if best_score >= threshold:
                # We found a match!
                # Assign values to merged dataframe
                stnk_row = df_stnk.loc[best_stnk_idx]
                
                # Update columns
                merged.at[idx, 'NO POLISI'] = stnk_row['NO POLISI']
                merged.at[idx, 'TIPE KENDARAAN'] = stnk_row['TIPE KENDARAAN']
                merged.at[idx, 'NOP PBB'] = stnk_row['NOP PBB']
                merged.at[idx, 'NIP_STNK'] = stnk_row['NIP'] # Keep STNK NIP for ref
                
                # Remove from pool to avoid double matching
                unnmatched_stnk_df = unnmatched_stnk_df.drop(best_stnk_idx)
                fuzzy_matches_found += 1
                print(f"  -> Fuzzy Match: '{master_name}' <--> '{stnk_row['NAMA']}' (Score: {best_score:.2f})")
    
    print(f"Fuzzy Matches Added: {fuzzy_matches_found}")
    
    # ------------------------------------------------

    # Matches count: where STNK data is present
    matched_count = merged['NO POLISI'].notna().sum() if 'NO POLISI' in merged.columns else 0
    print(f"Total Matches found (People with Vehicles/PBB in Bidang 2): {matched_count} out of {len(merged)}")
    
    # Construct Final DataFrame
    final_df = pd.DataFrame()
    final_df['No'] = range(1, len(merged) + 1)
    
    # Use Master Name/NIP/Jabatan/Golongan as primary
    final_df['Nama'] = merged['NAMA_MASTER']
    final_df['NIP'] = merged['NIP_MASTER'] # Keep original Master NIP
    final_df['Golongan Terakhir'] = merged['GOLONGAN_TERAKHIR']
    final_df['Jabatan'] = merged['JABATAN_MASTER']
    
    # STNK/PBB info
    # NOP: Prefer STNK 'NOP PBB', if missing try Master 'NOP_MASTER'
    if 'NOP_MASTER' in merged.columns and 'NOP PBB' in merged.columns:
         final_df['NOP'] = merged['NOP PBB'].fillna(merged['NOP_MASTER'])
    elif 'NOP PBB' in merged.columns:
         final_df['NOP'] = merged['NOP PBB']
    elif 'NOP_MASTER' in merged.columns:
         final_df['NOP'] = merged['NOP_MASTER']
    else:
         final_df['NOP'] = None

    # Format NOP as string to avoid scientific notation
    def format_nop(val):
        if pd.isna(val):
            return None
        # Check if float and large
        if isinstance(val, float):
             return f"{val:.0f}"
        
        s = str(val)
        if s.endswith('.0'):
            s = s[:-2]
        return s
    
    final_df['NOP'] = final_df['NOP'].apply(format_nop)

    # Nopol and Tipe from STNK
    final_df['Nomor Polisi Kendaraan'] = merged['NO POLISI'] if 'NO POLISI' in merged.columns else None
    final_df['Tipe Kendaraan'] = merged['TIPE KENDARAAN'] if 'TIPE KENDARAAN' in merged.columns else None

    print("Saving to Excel...")
    final_df.to_excel(OUTPUT_FILE, index=False)
    print(f"Done! Saved to {OUTPUT_FILE}")
    print(final_df.head())

if __name__ == "__main__":
    run()

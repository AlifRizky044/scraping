import pandas as pd
import re
from difflib import SequenceMatcher

# Configuration
MASTER_FILE = '/Users/nevv/Documents/scraping/data/master data upt.xlsx'
DATA_FILE = '/Users/nevv/Documents/scraping/data/REKAPITULASI PBB 2025 (3).xlsx'
OUTPUT_FILE = '/Users/nevv/Documents/scraping/data/HASIL_GABUNGAN_UPT.xlsx'
LOG_FILE = '/Users/nevv/Documents/scraping/accuracy_log_upt.txt'

def clean_nip(val):
    if pd.isna(val) or val == 'nan':
        return None
    s = str(val)
    if s.endswith('.0'): s = s[:-2]
    s = re.sub(r'[^0-9]', '', s)
    return s if s else None

def clean_name(name):
    if pd.isna(name):
        return ""
    s = str(name).lower()
    
    # 1. Strip identifiable degree patterns before character cleaning
    # This prevents Magister (M.) from becoming Muhammad
    degree_patterns = [
        r'[,.\s]s\.?e\.?\b', r'[,.\s]s\.?h\.?\b', r'[,.\s]s\.?t\.?\b', r'[,.\s]s\.?p\.?\b',
        r'[,.\s]m\.?m\.?\b', r'[,.\s]m\.?si\.?\b', r'[,.\s]s\.?kom\.?\b', r'[,.\s]s\.?pd\.?\b',
        r'[,.\s]s\.?os\.?\b', r'[,.\s]a\.?md\.?\b', r'[,.\s]s\.?tp\.?\b', r'[,.\s]m\.?ap\.?\b',
        r'[,.\s]s\.?k\.?m\.?\b', r'[,.\s]m\.?k\.?m\.?\b', r'[,.\s]s\.?p\.?s\.?i\.?\b',
        r'[,.\s]a\.?k\.?\b', r'[,.\s]c\.?a\.?\b', r'[,.\s]b\.?k\.?p\.?\b', r'[,.\s]c\.?t\.?a\.?\b',
        r'[,.\s]c\.?p\.?a\.?\b', r'[,.\s]s\.?si\.?\b', r'[,.\s]s\.?ap\.?\b'
    ]
    for p in degree_patterns:
        s = re.sub(p, ' ', s)
    
    # 2. Replace non-alphabetic with spaces
    s = re.sub(r'[^a-z\s]', ' ', s)
    
    # 3. Exhaustive list of Indonesian titles/degrees (word-based)
    titles = [
        r'\bhj\b', r'\bh\b', r'\bdrs\b', r'\bdra\b', r'\bir\b', 
        r'\bse\b', r'\bmm\b', r'\bssos\b', r'\bsh\b', r'\bskom\b',
        r'\bsstp\b', r'\bsp\b', r'\bspi\b', r'\bst\b', r'\bmap\b', r'\bmsi\b',
        r'\bak\b', r'\bptk\b', r'\bap\b', r'\bskom\b', r'\bsap\b', r'\bmd\b', r'\bamd\b',
        r'\bakun\b', r'\bpsi\b', r'\bspd\b', r'\bsi\b', r'\bmsi\b', r'\bpd\b', r'\bkom\b',
        r'\bs\b', r'\bag\b', r'\bh\b', r'\bptk\b', r'\bip\b', r'\bis\b', r'\bsk\b', r'\bsag\b',
        r'\bsos\b', r'\bsh\b', r'\bca\b', r'\bbkp\b', r'\bcta\b', r'\bcpa\b'
    ]
    for t in titles:
        s = re.sub(t, ' ', s)

    # 4. Standardize common abbreviations
    s = re.sub(r'\bmhd\b', 'muhammad', s)
    s = re.sub(r'\bmohd\b', 'muhammad', s)
    s = re.sub(r'\bmuh\b', 'muhammad', s)
    # Normalize 'm' at start or after space
    s = re.sub(r'^m\s', 'muhammad ', s)
    s = re.sub(r'\sm\s', ' muhammad ', s)
    
    # 5. Filter out noise words and single chars
    words = s.split()
    if len(words) > 1:
        # If we have multiple words, we can afford to strip single characters (initials/remnants)
        words = [w for w in words if len(w) > 1]
    s = " ".join(words)
    
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def format_nop(val):
    if pd.isna(val) or not val or str(val).lower() == 'nan': return None
    s = str(val)
    # Remove dots and spaces
    s = re.sub(r'[^0-9]', '', s)
    if not s: return None
    if s.endswith('.0'): s = s[:-2]
    return s

COMMON_NAMES = {'muhammad', 'mohammad', 'mohd', 'mhd', 'muh', 'siti', 'sri', 'ayu', 'putri', 'nur', 'h'}

def similarity(a, b):
    # Use cleaned names for comparison
    ca = clean_name(a)
    cb = clean_name(b)
    if not ca or not cb: return 0
    
    # Standard fuzzy score
    base_score = SequenceMatcher(None, ca, cb).ratio()
    
    # Word comparison for subsets and typos
    wa = ca.split()
    wb = cb.split()
    if not wa or not wb: return base_score

    # Identify "specific" words (not common titles or names)
    specific_wa = [w for w in wa if w not in COMMON_NAMES]
    specific_wb = [w for w in wb if w not in COMMON_NAMES]
    
    # Specific match validation:
    # If both have specific parts, at least one pair must match reasonably well
    if specific_wa and specific_wb:
        found_specific = False
        for sw in specific_wa:
            for dw in specific_wb:
                if SequenceMatcher(None, sw, dw).ratio() >= 0.85:
                    found_specific = True
                    break
        if not found_specific:
            # If the only matching part is "Muhammad" or similar common names, 
            # and the specific parts don't match, penalize the score heavily.
            return base_score * 0.5

    # Standard subset boost logic (only if specific parts passed or weren't present)
    if base_score >= 0.88: return base_score
    
    # Iterate over shorter name words to find matches in longer name
    short, long = (wa, wb) if len(wa) < len(wb) else (wb, wa)
    matches = 0
    matched_short_indices = set()
    matched_long_indices = set()
    
    for s_idx, s_word in enumerate(short):
        best_word_score = 0
        best_l_idx = -1
        for i, l_word in enumerate(long):
            if i in matched_long_indices: continue
            score = SequenceMatcher(None, s_word, l_word).ratio()
            if score > best_word_score:
                best_word_score = score
                best_l_idx = i
        
        if best_word_score >= 0.8: # Word-level typo tolerance
            matches += 1
            matched_long_indices.add(best_l_idx)
            matched_short_indices.add(s_idx)
    
    # NEW: Initial/Abbreviation check for unmatched words
    # Example: 'hm' vs ['hadi', 'mirsa']
    unmatched_short_words_with_indices = [(i, w) for i, w in enumerate(short) if i not in matched_short_indices]
    unmatched_long_words_with_indices = [(i, w) for i, w in enumerate(long) if i not in matched_long_indices]

    # Check if a single unmatched short word can be formed by initials of unmatched long words
    if len(unmatched_short_words_with_indices) == 1 and len(unmatched_long_words_with_indices) > 1:
        s_idx, s_word = unmatched_short_words_with_indices[0]
        
        # Create a string of initials from the unmatched long words
        long_initials = "".join([lw[0] for _, lw in unmatched_long_words_with_indices if lw])
        
        # If the short word matches the initials, consider it a match
        if s_word == long_initials:
            matches += 1
            matched_short_indices.add(s_idx)
            # Mark all long words as matched for this initial match
            for l_idx, _ in unmatched_long_words_with_indices:
                matched_long_indices.add(l_idx)
    
    # Check if multiple single-character short words match initials of long words
    elif len(unmatched_short_words_with_indices) > 1 and len(unmatched_short_words_with_indices) <= len(unmatched_long_words_with_indices):
        temp_matched_long_indices = set()
        for s_idx, s_word in unmatched_short_words_with_indices:
            if len(s_word) == 1: # Only consider single character words as initials
                for l_idx, l_word in unmatched_long_words_with_indices:
                    if l_idx not in temp_matched_long_indices and l_word and s_word == l_word[0]:
                        matches += 1
                        matched_short_indices.add(s_idx)
                        temp_matched_long_indices.add(l_idx)
                        break
        matched_long_indices.update(temp_matched_long_indices)


    overlap_score = matches / len(short)
    if overlap_score == 1.0:
        if len(short) >= 2:
            return max(base_score, 0.95)
        elif len(short) == 1:
            if base_score >= 0.85:
                return max(base_score, 0.9)
            
    return base_score

def run():
    print("Loading Master Data UPT...")
    df_master = pd.read_excel(MASTER_FILE, sheet_name=0, dtype={'NIP': str, 'NOP': str})
    df_master.columns = df_master.columns.astype(str).str.strip()
    
    # Case-insensitive map for Master columns
    cols_map = {c.upper(): c for c in df_master.columns}
    rename_map = {}
    if 'NAMA' in cols_map: rename_map[cols_map['NAMA']] = 'NAMA_MASTER'
    if 'NIP' in cols_map: rename_map[cols_map['NIP']] = 'NIP_MASTER'
    if 'GOL' in cols_map: rename_map[cols_map['GOL']] = 'GOLONGAN_TERAKHIR'
    if 'JABATAN' in cols_map: rename_map[cols_map['JABATAN']] = 'JABATAN_MASTER'
    if 'NOP' in cols_map: rename_map[cols_map['NOP']] = 'NOP_MASTER'
    
    df_master = df_master.rename(columns=rename_map)
    df_master['NIP_CLEAN'] = df_master['NIP_MASTER'].apply(clean_nip)
    df_master['NIP_KEY'] = df_master['NIP_CLEAN'].str[:15]
    
    print(f"Master Loaded: {len(df_master)} rows.")
    
    # ---------------- LOAD REKAP DATA ----------------
    print("Loading Rekap PNS Data...")
    df_pns = pd.read_excel(DATA_FILE, sheet_name='PNS', header=None, dtype=str)
    
    pns_rows = []
    data_start = -1
    for idx, row in df_pns.iterrows():
        if any('NAMA/NIP' in str(v).upper() for v in row if not pd.isna(v)):
            data_start = idx + 1
            break
            
    if data_start != -1:
        for idx in range(data_start, len(df_pns)):
            row = df_pns.iloc[idx]
            raw_cell = str(row[1]) # Col 1: NAME/NIP
            nop_val = row[4] # Col 4: NOP
            
            if pd.isna(raw_cell) or raw_cell.lower() == 'nan': continue
            
            parts = raw_cell.split('\n')
            name = parts[0].strip()
            nip = parts[1].strip() if len(parts) > 1 else None
            
            f_nop = format_nop(nop_val)
            pns_rows.append({
                'NAMA_DATA': name,
                'NIP_DATA': nip,
                'NOP_DATA': f_nop,
                'SOURCE': 'PNS'
            })

    print("Loading Rekap PHL Data...")
    df_phl = pd.read_excel(DATA_FILE, sheet_name='PHL', header=None, dtype=str)
    phl_rows = []
    data_start_phl = -1
    for idx, row in df_phl.iterrows():
        if any('NAMA/NIP' in str(v).upper() for v in row if not pd.isna(v)):
            data_start_phl = idx + 1
            break
            
    if data_start_phl != -1:
        for idx in range(data_start_phl, len(df_phl)):
            row = df_phl.iloc[idx]
            name = str(row[1]).strip() # Col 1
            nop_val = row[4] # Col 4
            if pd.isna(name) or name.lower() == 'nan' or not name: continue
            phl_rows.append({
                'NAMA_DATA': name,
                'NIP_DATA': None,
                'NOP_DATA': format_nop(nop_val),
                'SOURCE': 'PHL'
            })
            
    df_data = pd.DataFrame(pns_rows + phl_rows)
    df_data['NIP_CLEAN'] = df_data['NIP_DATA'].apply(clean_nip)
    df_data['NIP_KEY'] = df_data['NIP_CLEAN'].apply(lambda x: str(x)[:15] if x else None)
    print(f"Data Loaded: {len(df_data)} rows ({len(pns_rows)} PNS, {len(phl_rows)} PHL).")

    # ---------------- MERGING ----------------
    with open(LOG_FILE, 'w') as log:
        log.write("UPT MERGE ACCURACY LOG\n")
        log.write("========================\n\n")
        
        print("Merging by NIP...")
        merged = pd.merge(df_master, df_data[['NIP_KEY', 'NOP_DATA', 'NAMA_DATA', 'NIP_DATA', 'SOURCE']], on='NIP_KEY', how='left')
        
        # Track matches for log
        nip_matches = merged[merged['SOURCE'].notna()]
        log.write(f"--- NIP PREFIX MATCHES (15 chars) - Total: {len(nip_matches)} ---\n")
        for _, row in nip_matches.iterrows():
            log.write(f"MATCH [NIP]: Master '{row['NAMA_MASTER']}' ({row['NIP_MASTER']}) <--> Data '{row['NAMA_DATA']}' ({row['NIP_DATA']})\n")
        log.write("\n")

        # Fuzzy Match pool
        unmatched_master_mask = merged['SOURCE'].isna()
        unmatched_indices = merged[unmatched_master_mask].index
        
        matched_indices_data = df_data[df_data['NIP_KEY'].isin(merged['NIP_KEY'].dropna().unique())].index.tolist()
        unmatched_data_df = df_data[~df_data.index.isin(matched_indices_data)].copy()
        
        print(f"Checking {len(unmatched_indices)} rows for Fuzzy Name Match...")
        log.write(f"--- FUZZY NAME MATCHES - Checking {len(unmatched_indices)} master rows ---\n")
        
        count_fuzzy = 0
        threshold = 0.85 # Increased for high accuracy as requested
        
        for idx in unmatched_indices:
            master_name = merged.at[idx, 'NAMA_MASTER']
            if pd.isna(master_name) or unmatched_data_df.empty: continue
            
            best_score = 0
            best_data_idx = -1
            
            for d_idx, row in unmatched_data_df.iterrows():
                score = similarity(master_name, row['NAMA_DATA'])
                if score > best_score:
                    best_score = score
                    best_data_idx = d_idx
            
            if best_score >= threshold:
                tgt_row = unmatched_data_df.loc[best_data_idx]
                merged.at[idx, 'NOP_DATA'] = tgt_row['NOP_DATA']
                merged.at[idx, 'NAMA_DATA'] = tgt_row['NAMA_DATA']
                merged.at[idx, 'SOURCE'] = tgt_row['SOURCE']
                
                log.write(f"MATCH [FUZZY]: Master '{master_name}' <--> Data '{tgt_row['NAMA_DATA']}' (Score: {best_score:.2f}, Source: {tgt_row['SOURCE']})\n")
                count_fuzzy += 1
                unmatched_data_df = unmatched_data_df.drop(best_data_idx)
            elif best_score > 0.4:
                tgt_row = unmatched_data_df.loc[best_data_idx]
                log.write(f"REJECT [LOW SCORE]: Master '{master_name}' vs Data '{tgt_row['NAMA_DATA']}' (Score: {best_score:.2f})\n")

    print(f"Fuzzy Matches Found: {count_fuzzy}")
    
    # Finalize DataFrame
    final_df = pd.DataFrame()
    final_df['No'] = range(1, len(merged) + 1)
    final_df['Nama'] = merged['NAMA_MASTER']
    final_df['NIP'] = merged['NIP_MASTER']
    final_df['Golongan Terakhir'] = merged['GOLONGAN_TERAKHIR']
    final_df['Jabatan'] = merged['JABATAN_MASTER']
    
    # Combine NOP
    final_df['NOP'] = merged['NOP_DATA'].fillna(merged['NOP_MASTER'])
    final_df['NOP'] = final_df['NOP'].apply(format_nop)
    
    # No vehicle data mentioned for UPT merge
    final_df['Nomor Polisi Kendaraan'] = None
    final_df['Tipe Kendaraan'] = None
    
    print(f"Saving to {OUTPUT_FILE}...")
    final_df.to_excel(OUTPUT_FILE, index=False)
    print("Done!")

if __name__ == "__main__":
    run()

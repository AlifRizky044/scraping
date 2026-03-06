import pandas as pd

f = '/Users/nevv/Documents/scraping/data/STNK DAN PBB - Copy(1).xlsx'
print(f"--- File: {f} ---")
try:
    # Read without header to find where the header actually is
    df = pd.read_excel(f, sheet_name='STNK&PBB ASN FIX', header=None, nrows=10)
    print("First 10 rows of STNK&PBB ASN FIX:")
    print(df)
    
    print("\n")
    df_phl = pd.read_excel(f, sheet_name='STNK&PBB PHL FIX', header=None, nrows=10)
    print("First 10 rows of STNK&PBB PHL FIX:")
    print(df_phl)

except Exception as e:
    print(f"Error reading {f}: {e}")

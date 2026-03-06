import pandas as pd
import os

import sys

files = sys.argv[1:] if len(sys.argv) > 1 else [
    '/Users/nevv/Documents/scraping/data/DUK BAPENDA KOTA MEDAN 2026 1 Februari(1).xlsx',
    '/Users/nevv/Documents/scraping/data/STNK DAN PBB - Copy(1).xlsx'
]

for f in files:
    print(f"--- File: {os.path.basename(f)} ---")
    try:
        xl = pd.ExcelFile(f)
        print(f"Sheet names: {xl.sheet_names}")
        for sheet in xl.sheet_names:
            df = pd.read_excel(f, sheet_name=sheet, nrows=5)
            print(f"Sheet: {sheet}")
            print("Columns:", df.columns.tolist())
            print(df.head(2))
            print("\n")
    except Exception as e:
        print(f"Error reading {f}: {e}")

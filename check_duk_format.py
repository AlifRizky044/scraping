import pandas as pd
df = pd.read_excel('DUK_PNS_OUTPUT.xlsx', header=None, skiprows=5)

print("--- Checking for literal 'nan' strings ---")
# If we read without dtype=str, empty cells will be NaN (the object). 
# If they are literal 'nan' strings, they will be strings.
count_nan_str = 0
for col in df.columns:
    count_nan_str += df[col].astype(str).str.fullmatch('nan').sum()
print(f"Total literal 'nan' strings found: {count_nan_str}")

print("\n--- Sample of first 15 records in output ---")
for i, row in df.head(15).iterrows():
    print(f"Index {i+6}: {row[1]} | {row[14]}")

print("\n--- Checking specific hierarchy for Irvan ---")
target_jab = "KEPALA BIDANG HOTEL, RESTORAN, DAN HIBURAN"
anchor_jab = "KEPALA SUB BIDANG TEKNIS HOTEL, RESTORAN, DAN HIBURAN"
idx_mover = -1
idx_anchor = -1
for i, row in df.iterrows():
    jab = str(row[14]).strip().upper()
    if target_jab in jab: idx_mover = i
    if anchor_jab in jab: idx_anchor = i

if idx_mover != -1 and idx_anchor != -1:
    print(f"Mover index: {idx_mover}, Anchor index: {idx_anchor}")
    if idx_mover < idx_anchor:
        print("✅ Correct: Kabid is above Kasubbid.")
    else:
        print("❌ Incorrect: Kabid is below Kasubbid.")
else:
    print("❌ Could not find one or both roles.")

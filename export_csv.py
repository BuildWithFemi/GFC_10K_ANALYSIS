import pandas as pd
from pathlib import Path

root = Path(__file__).parent

raw = pd.read_excel(root / "GFC_10K_Financial_Analysis.xlsx", sheet_name="Raw Data")
ratios = pd.read_excel(root / "GFC_10K_Financial_Analysis.xlsx", sheet_name="Ratios")

ratios = ratios.dropna(subset=["Company", "FiscalYear"])
ratios = ratios.reset_index(drop=True)

raw.to_csv(root / "raw_data.csv", index=False)
ratios.to_csv(root / "ratios.csv", index=False)

print(f"raw_data.csv: {len(raw)} rows, {len(raw.columns)} columns")
print(f"ratios.csv:   {len(ratios)} rows, {len(ratios.columns)} columns")
print("Done.")

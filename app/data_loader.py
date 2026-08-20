import pandas as pd
from pathlib import Path

# Resolve relative to project root (one level up from this file)
ROOT = Path(__file__).parent.parent


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load raw financials and ratios from CSV files in the project root."""
    raw = pd.read_csv(ROOT / "raw_data.csv")
    ratios = pd.read_csv(ROOT / "ratios.csv")

    raw = raw.dropna(subset=["Company"]).reset_index(drop=True)
    ratios = ratios.dropna(subset=["Company", "FiscalYear"]).reset_index(drop=True)

    return raw, ratios

"""
UPI Transaction Reconciliation Tool.

Merges, deduplicates, and categorizes UPI transactions across PhonePe,
Google Pay, and Paytm CSV exports into a single reconciled Excel file.

Usage:
    Drop your CSVs in ./statements/ named like phonepe_april.csv,
        gpay_april.csv, paytm_april.csv. Run the script. Get one Excel file
            with a transactions sheet and a monthly category pivot in INR.

            See blog post: https://dev.to/automate-archit
            """
import pandas as pd
from pathlib import Path
from datetime import datetime

SCHEMA = {
      "phonepe": {"date": "Transaction Date", "amount": "Amount (INR)", "party": "Merchant", "ref": "UTR"},
      "gpay":    {"date": "Date",             "amount": "Amount",       "party": "To",       "ref": "Transaction ID"},
      "paytm":   {"date": "Txn Date",         "amount": "Amount",       "party": "Payee",    "ref": "Order ID"},
}

CATEGORIES = {
      "food":  ["zomato", "swiggy", "dominos", "kfc", "mcdonald"],
      "fuel":  ["hpcl", "iocl", "bpcl", "petrol", "indian oil"],
      "rent":  ["rent", "landlord", "housing"],
      "bills": ["airtel", "jio", "vi ", "tata power", "electricity"],
      "shop":  ["amazon", "flipkart", "myntra", "blinkit", "zepto"],
}

def categorize(party: str) -> str:
      p = (party or "").lower()
      for cat, keywords in CATEGORIES.items():
                if any(k in p for k in keywords):
                              return cat
                      return "other"


def load(path: Path, app: str) -> pd.DataFrame:
      df = pd.read_csv(path)
      cols = SCHEMA[app]
      out = pd.DataFrame({
          "date":   pd.to_datetime(df[cols["date"]], errors="coerce"),
          "amount": pd.to_numeric(df[cols["amount"]].astype(str).str.replace("[Rs,]", "", regex=True), errors="coerce"),
          "party":  df[cols["party"]].astype(str),
          "ref":    df[cols["ref"]].astype(str),
          "app":    app,
      })
      out["category"] = out["party"].apply(categorize)
      return out.dropna(subset=["date", "amount"])


def reconcile(folder: Path) -> pd.DataFrame:
      frames = [load(p, app) for app in SCHEMA for p in folder.glob(f"{app}*.csv")]
      if not frames:
                raise SystemExit("No UPI CSVs found.")
            combined = pd.concat(frames, ignore_index=True).sort_values("date")
    combined["minute"] = combined["date"].dt.floor("min")
    combined = combined.drop_duplicates(subset=["minute", "amount", "party"], keep="first").drop(columns="minute")
    combined["month"] = combined["date"].dt.to_period("M").astype(str)
    return combined


def export(df: pd.DataFrame, out_path: Path) -> None:
      monthly = df.pivot_table(index="month", columns="category", values="amount", aggfunc="sum", fill_value=0)
    with pd.ExcelWriter(out_path, engine="openpyxl") as xl:
              df.to_excel(xl, sheet_name="transactions", index=False)
              monthly.to_excel(xl, sheet_name="monthly_by_category")
          print(f"Saved {len(df)} transactions to {out_path}")


if __name__ == "__main__":
      df = reconcile(Path("./statements"))
    export(df, Path(f"upi_reconciled_{datetime.now():%Y_%m_%d}.xlsx"))

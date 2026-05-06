"""
examples/categorize_upi_statement.py

Minimal example: categorize a UPI bank statement CSV into spending buckets.
Mirrors the pattern from the writeup at:
    https://dev.to/automate-archit/build-a-upi-transaction-categorizer-in-95-lines-of-python-2g8f

Run it like:
    python examples/categorize_upi_statement.py sample_statement.csv
"""
import re
import sys
from pathlib import Path

import pandas as pd

CATEGORIES = {
    "Food": ["zomato", "swiggy", "dunzo", "dominos", "kfc", "starbucks"],
    "Groceries": ["bigbasket", "blinkit", "zepto", "dmart", "instamart"],
    "Transport": ["uber", "olacabs", "rapido", "irctc", "redbus", "blusmart"],
    "Bills": ["airtel", "jio", "vi-mobile", "tatapower", "bescom"],
    "Shopping": ["amazon", "flipkart", "myntra", "ajio", "nykaa"],
    "Investments": ["zerodha", "groww", "upstox", "kuvera"],
}

UPI = re.compile(r"upi[/-]([a-z0-9.\-_@]+)", re.IGNORECASE)


def categorize(narration: str) -> str:
    if not isinstance(narration, str):
        return "Other"
    match = UPI.search(narration.lower())
    haystack = match.group(1) if match else narration.lower()
    for category, keywords in CATEGORIES.items():
        if any(k in haystack for k in keywords):
            return category
    return "Other"


def main(path: Path) -> None:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    narration_col = next(
        (c for c in ("narration", "description", "details") if c in df.columns),
        None,
    )
    if not narration_col:
        sys.exit("No narration column found in " + str(path))
    df["category"] = df[narration_col].apply(categorize)
    summary = df.groupby("category").size().sort_values(ascending=False)
    print(summary.to_string())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python categorize_upi_statement.py <statement.csv>")
    main(Path(sys.argv[1]))

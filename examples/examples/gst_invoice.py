"""GST Invoice Generator — companion to the Dev.to article.

Generates a GST-compliant PDF invoice. Auto-detects intra-state (CGST+SGST)
vs inter-state (IGST) based on the GSTIN state code.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import date


def generate_gst_invoice(seller, buyer, items, invoice_no, inv_date=None):
    inv_date = inv_date or date.today().isoformat()
    same_state = seller["state_code"] == buyer["state_code"]
    rows = [["#", "Description", "HSN", "Qty", "Rate", "Taxable", "Tax%", "Tax", "Total"]]
    total_tax = grand_total = 0
    for i, it in enumerate(items, 1):
        taxable = round(it["qty"] * it["rate"], 2)
        tax = round(taxable * it["gst"] / 100, 2)
        total_tax += tax
        grand_total += taxable + tax
        rows.append([i, it["desc"], it["hsn"], it["qty"],
                     f"{it['rate']:.2f}", f"{taxable:.2f}",
                     f"{it['gst']}%", f"{tax:.2f}", f"{taxable + tax:.2f}"])
    if same_state:
        tax_rows = [["CGST", f"{total_tax/2:.2f}"], ["SGST", f"{total_tax/2:.2f}"]]
    else:
        tax_rows = [["IGST", f"{total_tax:.2f}"]]
    tax_rows.append(["Grand Total (INR)", f"{grand_total:.2f}"])

    doc = SimpleDocTemplate(f"Invoice_{invoice_no}.pdf", pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"<b>{seller['name']}</b>", styles["Title"]),
        Paragraph(f"{seller['address']}<br/>GSTIN: {seller['gstin']}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(f"<b>Tax Invoice #{invoice_no}</b>   Date: {inv_date}", styles["Heading3"]),
        Paragraph(f"<b>Bill To:</b> {buyer['name']}<br/>{buyer['address']}<br/>GSTIN: {buyer['gstin']}", styles["Normal"]),
        Spacer(1, 12),
        Table(rows, repeatRows=1, hAlign="LEFT"),
        Spacer(1, 12),
        Table(tax_rows, hAlign="RIGHT", colWidths=[140, 90]),
    ]
    doc.build(story)
    return f"Invoice_{invoice_no}.pdf"


if __name__ == "__main__":
    seller = {"name": "Mittal Automation Studio", "address": "Sector 62, Noida, UP",
              "gstin": "09ABCDE1234F1Z5", "state_code": "09"}
    buyer  = {"name": "Acme Retail Pvt Ltd", "address": "Bandra West, Mumbai, MH",
              "gstin": "27FGHIJ5678K2Z9", "state_code": "27"}
    items = [
        {"desc": "Workflow automation setup", "hsn": "998313", "qty": 1, "rate": 45000, "gst": 18},
        {"desc": "Monthly support retainer",   "hsn": "998313", "qty": 3, "rate": 12000, "gst": 18},
    ]
    print(f"Generated: {generate_gst_invoice(seller, buyer, items, 'INV-2026-014')}")

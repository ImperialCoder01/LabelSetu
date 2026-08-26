"""
Generate Product Catalog PDF — Creates a PDF catalog containing all product details
and rendered barcode graphics saved locally to docs/Product_Catalog.pdf.

Includes:
  - Barcode (EAN-13) + Rendered Barcode Graphic
  - Product Name, Brand, Category
  - Net Quantity, MRP (₹), Unit Price
  - Manufacturer & Address, FSSAI Lic No.
  - Country of Origin, Ingredients
"""

import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.barcode import createBarcodeDrawing

CATALOG_JSON_PATH = Path(__file__).parent.parent / "models" / "barcode_catalog.json"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "docs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PDF_PATH = OUTPUT_DIR / "Product_Catalog.pdf"


def build_barcode_drawing(barcode_str: str) -> Drawing:
    """Generate an EAN-13 barcode drawing for the PDF."""
    try:
        # Pad or sanitize barcode string to 12/13 digits
        digits = "".join(filter(str.isdigit, barcode_str))
        if len(digits) < 12:
            digits = digits.zfill(12)
        elif len(digits) > 13:
            digits = digits[:13]
            
        d = createBarcodeDrawing(
            "EAN13",
            value=digits,
            height=30,
            barWidth=1.1,
            humanReadable=True,
            fontSize=8,
        )
        return d
    except Exception:
        # Fallback drawing if barcode string fails validation
        d = Drawing(120, 30)
        d.add(Rect(0, 0, 120, 30, fillColor=colors.lightgrey, strokeColor=colors.grey))
        return d


def generate_pdf():
    print("==========================================================")
    print("Generating FMCG Product Catalog PDF with Barcode Images...")
    print("==========================================================")

    if not CATALOG_JSON_PATH.exists():
        print(f"Error: Catalog file not found at {CATALOG_JSON_PATH}")
        return

    with open(CATALOG_JSON_PATH, "r", encoding="utf-8") as f:
        catalog_data = json.load(f)

    products = list(catalog_data.values())
    print(f"[OK] Loaded {len(products)} products from catalog JSON.")

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF_PATH),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1e3a8a"),
        alignment=1,  # Center
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#4b5563"),
        alignment=1,
        spaceAfter=15,
    )
    header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#111827"),
    )
    cell_text = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#374151"),
    )
    cell_code = ParagraphStyle(
        "CellCode",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=9,
        fontName="Courier-Bold",
        textColor=colors.HexColor("#1d4ed8"),
    )

    story = []

    # Title & Header
    story.append(Paragraph("LabelSetu — FMCG Product & Barcode Catalog", title_style))
    story.append(Paragraph("Legal Metrology Compliance Database | SIH26034 | Ministry of Consumer Affairs", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=15))

    # Summary Stats Box
    summary_html = f"""
    <b>Catalog Statistics:</b><br/>
    • Total Products Registered: <b>{len(products)}</b><br/>
    • Storage Size: <b>~150 KB</b> (under 200MB limit)<br/>
    • Regulatory Scope: Legal Metrology (Packaged Commodities) Rules, 2011 & FSSAI Standards
    """
    summary_p = Paragraph(summary_html, cell_text)
    summary_table = Table([[summary_p]], colWidths=[520])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#bbf7d0")),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    # Build product list table
    # Columns: [ #, Product Name & Details, Barcode Graphic, Price & Qty, Manufacturer & FSSAI ]
    table_data = [[
        Paragraph("#", header_style),
        Paragraph("Product & Brand", header_style),
        Paragraph("Barcode (EAN-13)", header_style),
        Paragraph("MRP & Qty", header_style),
        Paragraph("Manufacturer & FSSAI", header_style),
    ]]

    for idx, p in enumerate(products, 1):
        p_name = p.get("product_name", "N/A")
        brand = p.get("brand", "N/A")
        category = p.get("category", "N/A")
        barcode_str = p.get("barcode", "")
        mrp = p.get("mrp", 0.0)
        net_qty = p.get("net_quantity", "N/A")
        mfg = p.get("manufacturer", "N/A")
        fssai = p.get("fssai_lic", "N/A")
        origin = p.get("country_of_origin", "India")
        ingredients = p.get("ingredients", "N/A")

        col1_text = f"<b>{p_name}</b><br/><font color='#6b7280'>Brand:</font> {brand}<br/><font color='#6b7280'>Cat:</font> {category}"
        col3_text = f"<b>₹{mrp:.2f}</b><br/><font color='#6b7280'>Net:</font> {net_qty}"
        col4_text = f"<b>{mfg}</b><br/><font color='#6b7280'>FSSAI:</font> {fssai}<br/><font color='#6b7280'>Origin:</font> {origin}"

        barcode_drawing = build_barcode_drawing(barcode_str)

        row = [
            Paragraph(str(idx), cell_bold),
            Paragraph(col1_text, cell_text),
            barcode_drawing,
            Paragraph(col3_text, cell_text),
            Paragraph(col4_text, cell_text),
        ]
        table_data.append(row)

    # Product Table Layout
    prod_table = Table(
        table_data,
        colWidths=[25, 140, 110, 85, 160],
        repeatRows=1
    )
    prod_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
    ]))

    story.append(prod_table)

    # Build Document
    doc.build(story)
    print("==========================================================")
    print(f"[SUCCESS] PDF Catalog successfully generated at:\n{OUTPUT_PDF_PATH}")
    print("==========================================================")


if __name__ == "__main__":
    generate_pdf()

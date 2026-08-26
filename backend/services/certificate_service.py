"""
Certificate Service — generates PDF compliance certificates with QR codes.

Each certificate includes:
  - Brand name, product name (from extracted text)
  - Compliance score and status
  - Per-field checklist
  - QR code linking to public verification page
  - Issue date and certificate ID
"""

import io
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def _qr_image(data: str, size: int = 40 * mm) -> io.BytesIO:
    """Generate a QR code as an in-memory PNG."""
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generate_certificate(
    scan: dict,
    compliance_report: dict,
    user_profile: dict,
    verify_url: str,
) -> bytes:
    """
    Generate a PDF compliance certificate.

    Args:
        scan: scan row from Supabase
        compliance_report: the compliance report dict
        user_profile: the brand user's profile (full_name)
        verify_url: public URL for QR code

    Returns:
        PDF file as bytes
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # --- Custom styles ---
    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Heading1"],
        fontSize=22,
        textColor=colors.HexColor("#1e3a8a"),
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )
    subtitle_style = ParagraphStyle(
        "CertSub",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#6b7280"),
        alignment=TA_CENTER,
        spaceAfter=8 * mm,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
    )

    score = compliance_report.get("overall_score", 0)
    if score >= 80:
        status_text = "COMPLIANT"
        status_color = colors.HexColor("#16a34a")
    elif score >= 50:
        status_text = "PARTIALLY COMPLIANT"
        status_color = colors.HexColor("#d97706")
    else:
        status_text = "NON-COMPLIANT"
        status_color = colors.HexColor("#dc2626")

    brand_name = user_profile.get("full_name", "Brand")
    extracted_text = scan.get("extracted_text", "")
    # Try to extract a product name from the first line
    product_name = extracted_text.split("\n")[0][:60] if extracted_text else "Product"
    scan_id = scan.get("id", "N/A")
    created_at = scan.get("created_at", "")

    # ---- Header ----
    elements.append(Paragraph("LABELSETU", title_style))
    elements.append(Paragraph("Product Label Compliance Certificate", subtitle_style))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#d1d5db"), thickness=1))
    elements.append(Spacer(1, 4 * mm))

    # ---- Score badge ----
    score_data = [
        [
            Paragraph(f'<font size="36" color="{status_color.hexval()}">{score}</font>', styles["Normal"]),
            Paragraph(
                f'<font size="10" color="#6b7280">/ 100</font><br/>'
                f'<font size="14" color="{status_color.hexval()}"><b>{status_text}</b></font>',
                styles["Normal"],
            ),
        ]
    ]
    score_table = Table(score_data, colWidths=[40 * mm, 60 * mm])
    score_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "RIGHT"),
        ("ALIGN", (1, 0), (1, 0), "LEFT"),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 6 * mm))

    # ---- Product info ----
    elements.append(Paragraph("Product Details", section_style))
    info_data = [
        ["Brand", brand_name],
        ["Product", product_name],
        ["Scan ID", scan_id[:16] + "..."],
        ["Date", created_at[:10] if created_at else "—"],
        ["OCR Confidence", f'{compliance_report.get("ocr_confidence", "—")}'],
    ]
    info_table = Table(info_data, colWidths=[45 * mm, 120 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6b7280")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4 * mm))

    # ---- Compliance checklist ----
    elements.append(Paragraph("Compliance Checklist", section_style))

    header = ["Field", "Severity", "Status"]
    rows = [header]
    for field in compliance_report.get("fields", []):
        field_name = field.get("field_name", field.get("field_id", ""))
        severity = field.get("severity", "")
        status = "✓ Pass" if field.get("status") == "pass" else "✗ Fail"
        rows.append([field_name, severity, status])

    checklist_table = Table(rows, colWidths=[80 * mm, 30 * mm, 40 * mm])

    table_style_cmds = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]

    # Color-code status column
    for i, row in enumerate(rows[1:], start=1):
        if "Pass" in row[2]:
            table_style_cmds.append(("TEXTCOLOR", (2, i), (2, i), colors.HexColor("#16a34a")))
        else:
            table_style_cmds.append(("TEXTCOLOR", (2, i), (2, i), colors.HexColor("#dc2626")))

    checklist_table.setStyle(TableStyle(table_style_cmds))
    elements.append(checklist_table)
    elements.append(Spacer(1, 6 * mm))

    # ---- QR code + verification ----
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#d1d5db"), thickness=1))
    elements.append(Spacer(1, 4 * mm))

    qr_buf = _qr_image(verify_url)
    qr_img = RLImage(qr_buf, width=35 * mm, height=35 * mm)

    verify_text = Paragraph(
        f'<font size="8" color="#6b7280">Scan to verify this certificate</font><br/>'
        f'<font size="7" color="#9ca3af">{verify_url}</font>',
        styles["Normal"],
    )
    qr_row = Table([[qr_img, verify_text]], colWidths=[40 * mm, 120 * mm])
    qr_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(qr_row)

    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(
        f'<font size="7" color="#9ca3af">This certificate was generated by LabelSetu. '
        f'Certificate ID: {scan_id}</font>',
        ParagraphStyle("Footer", parent=styles["Normal"], alignment=TA_CENTER),
    ))

    # ---- Build PDF ----
    doc.build(elements)
    return buf.getvalue()

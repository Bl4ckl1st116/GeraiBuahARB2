from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable, Frame, PageTemplate, BaseDocTemplate
)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, Line
from io import BytesIO
from datetime import datetime

# ======================================================
# BRAND COLORS (matching the web theme)
# ======================================================
COLOR_PRIMARY = colors.HexColor('#81C408')       # Green
COLOR_PRIMARY_DARK = colors.HexColor('#5A8A00')   # Darker green for accents
COLOR_SECONDARY = colors.HexColor('#FFB524')       # Amber/Orange
COLOR_DARK = colors.HexColor('#45595B')            # Dark text
COLOR_LIGHT = colors.HexColor('#F4F6F8')           # Light background
COLOR_WHITE = colors.HexColor('#FFFFFF')
COLOR_ROW_ALT = colors.HexColor('#F0F7E2')        # Light green tint for alt rows
COLOR_HEADER_BG = colors.HexColor('#45595B')       # Dark header
COLOR_BORDER = colors.HexColor('#D1D5DB')          # Subtle border
COLOR_ACCENT_LINE = colors.HexColor('#81C408')     # Green accent


def _build_styles():
    """Build custom paragraph styles for the PDF report."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='BrandTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=COLOR_DARK,
        alignment=TA_CENTER,
        spaceAfter=2 * mm,
        leading=22,
    ))

    styles.add(ParagraphStyle(
        name='ReportSubtitle',
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    ))

    styles.add(ParagraphStyle(
        name='BusinessName',
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=COLOR_PRIMARY_DARK,
        alignment=TA_CENTER,
        spaceAfter=1 * mm,
    ))

    styles.add(ParagraphStyle(
        name='FooterText',
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='FooterTextRight',
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_RIGHT,
    ))

    styles.add(ParagraphStyle(
        name='TableCellStyle',
        fontName='Helvetica',
        fontSize=9,
        textColor=COLOR_DARK,
        leading=12,
    ))

    styles.add(ParagraphStyle(
        name='TableHeaderStyle',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=COLOR_WHITE,
        leading=12,
    ))

    return styles


def _header_block(styles, title):
    """Build the header section of the report."""
    elements = []

    # Business name
    elements.append(Paragraph("GERAI BUAH ARB", styles['BusinessName']))

    # Decorative accent line (green-amber gradient effect via two lines)
    accent = Drawing(480, 6)
    accent.add(Rect(0, 2, 240, 2, fillColor=COLOR_PRIMARY, strokeColor=None))
    accent.add(Rect(240, 2, 240, 2, fillColor=COLOR_SECONDARY, strokeColor=None))
    elements.append(accent)
    elements.append(Spacer(1, 4 * mm))

    # Report title
    elements.append(Paragraph(title.upper(), styles['BrandTitle']))

    # Generation timestamp
    now = datetime.now().strftime('%d %B %Y, %H:%M WIB')
    elements.append(Paragraph(f"Tanggal Cetak: {now}", styles['ReportSubtitle']))

    # Thin separator
    elements.append(HRFlowable(
        width="100%", thickness=0.5,
        color=COLOR_BORDER, spaceAfter=6 * mm, spaceBefore=2 * mm
    ))

    return elements


def _footer_block(styles, generated_by):
    """Build the footer section with report metadata."""
    elements = []

    # Separator before footer
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(
        width="100%", thickness=0.5,
        color=COLOR_BORDER, spaceAfter=3 * mm, spaceBefore=0
    ))

    now = datetime.now()
    date_str = now.strftime('%d %B %Y')
    time_str = now.strftime('%H:%M:%S WIB')

    # Footer table with left and right aligned info
    footer_data = [[
        Paragraph(
            f"<b>Dicetak pada:</b> {date_str}, {time_str}<br/>"
            f"<b>Dicetak oleh:</b> {generated_by}",
            styles['FooterText']
        ),
        Paragraph(
            "<b>GERAI BUAH ARB</b><br/>"
            "Sistem Informasi Manajemen",
            styles['FooterTextRight']
        ),
    ]]

    footer_table = Table(footer_data, colWidths=[260, 220])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    elements.append(footer_table)

    # Bottom accent line
    elements.append(Spacer(1, 3 * mm))
    accent = Drawing(480, 4)
    accent.add(Rect(0, 1, 240, 2, fillColor=COLOR_PRIMARY, strokeColor=None))
    accent.add(Rect(240, 1, 240, 2, fillColor=COLOR_SECONDARY, strokeColor=None))
    elements.append(accent)

    return elements


def _build_table(table_data):
    """Build a professionally styled data table with row numbering."""
    if not table_data or len(table_data) < 1:
        return []

    styles = _build_styles()

    # Add "No." column and wrap cells in Paragraphs for text wrapping
    header_row = table_data[0]
    styled_header = [Paragraph("No.", styles['TableHeaderStyle'])]
    for cell in header_row:
        styled_header.append(Paragraph(str(cell), styles['TableHeaderStyle']))

    styled_data = [styled_header]
    for idx, row in enumerate(table_data[1:], start=1):
        styled_row = [Paragraph(str(idx), styles['TableCellStyle'])]
        for cell in row:
            styled_row.append(Paragraph(str(cell), styles['TableCellStyle']))
        styled_data.append(styled_row)

    num_cols = len(styled_header)

    # Calculate column widths: small "No." column, rest distributed evenly
    available_width = 480
    no_col_width = 28
    remaining = available_width - no_col_width
    other_col_width = remaining / (num_cols - 1) if num_cols > 1 else remaining
    col_widths = [no_col_width] + [other_col_width] * (num_cols - 1)

    table = Table(styled_data, colWidths=col_widths, repeatRows=1)

    # Table styling
    style_commands = [
        # Header row styling
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),

        # Data rows base styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),

        # Alignment
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),   # No. column centered
        ('ALIGN', (1, 0), (-1, 0), 'LEFT'),      # Header left-aligned
        ('ALIGN', (1, 1), (-1, -1), 'LEFT'),      # Data left-aligned
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Grid & borders
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, COLOR_PRIMARY),  # Green line under header

        # Left and right padding
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]

    # Alternating row colors
    for i in range(1, len(styled_data)):
        if i % 2 == 0:
            style_commands.append(
                ('BACKGROUND', (0, i), (-1, i), COLOR_ROW_ALT)
            )
        else:
            style_commands.append(
                ('BACKGROUND', (0, i), (-1, i), COLOR_WHITE)
            )

    table.setStyle(TableStyle(style_commands))
    return [table]


def generate_pdf(title, table_data, generated_by="Administrator"):
    """
    Generate a professional, branded PDF report.

    Args:
        title: The report title string
        table_data: List of lists — first row is headers, rest is data
        generated_by: Name of the user who generated the report

    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=title,
        author="Gerai Buah ARB",
    )

    styles = _build_styles()

    # Build the story
    story = []

    # Header
    story.extend(_header_block(styles, title))

    # Data summary line
    row_count = len(table_data) - 1 if len(table_data) > 1 else 0
    story.append(Paragraph(
        f"Total Data: <b>{row_count}</b> record(s)",
        styles['ReportSubtitle']
    ))
    story.append(Spacer(1, 3 * mm))

    # Table
    story.extend(_build_table(table_data))

    # Footer
    story.extend(_footer_block(styles, generated_by))

    doc.build(story)
    buffer.seek(0)
    return buffer

import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

CONFIG_TANQUES_PDF = [
    "STK-MOVIL",
    "MUECAS",
    "STK- 03 Chook",
    "stk-04 pelayo",
    "STK- 05 GBA (S/A)",
    "STK- 06",
    "STK-07 PASCUA",
    "STK- 08 GBA (Leche)",
    "STK- 09 Sollish",
    "STK- 10 Grageado",
    "blanco",
    "Tanque de licor",
    "Tanque de illexao",
    "laurico",
]


def generar_pdf_planilla_blanca() -> io.BytesIO:
    """Genera la planilla A4 horizontal en blanco para registro manual en planta."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloPlanilla",
        parent=styles["Heading1"],
        fontSize=15,
        textColor=colors.HexColor("#1e3a5f"),
        spaceAfter=6,
    )
    estilo_cabecera = ParagraphStyle(
        "CabeceraManual",
        parent=styles["Normal"],
        fontSize=10.5,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=12,
    )

    elementos = []
    elementos.append(Paragraph("PLANILLA DE NIVELES DE TANQUES — PLANTA CHOCOLATES", estilo_titulo))
    elementos.append(
        Paragraph(
            "<b>Fecha y Hora:</b> _____ / _____ / 202___ &nbsp;&nbsp; _____ : _____ hs "
            "&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp; "
            "<b>Supervisor:</b> __________________________ "
            "&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp; "
            "<b>Operario:</b> __________________________",
            estilo_cabecera,
        )
    )

    encabezados = [
        "TK",
        "Código",
        "Descripción",
        "Valor Medido",
        "N / CM",
        "N / %",
        "Cantidad (Kg)",
        "N° Conca",
        "Kg Conca / Manual",
        "TOTAL (Kg)",
    ]
    filas_tabla = [encabezados]

    for tanque in CONFIG_TANQUES_PDF:
        filas_tabla.append([tanque, "", "", "", "", "", "", "", "", ""])

    filas_tabla.append(["TOTAL GENERAL EN PLANTA:", "", "", "", "", "", "", "", "", ""])

    anchos_col = [
        36 * mm,  # TK
        24 * mm,  # Código
        64 * mm,  # Descripción
        22 * mm,  # Valor Medido
        16 * mm,  # N / CM
        16 * mm,  # N / %
        25 * mm,  # Cantidad (Kg)
        18 * mm,  # N° Conca
        28 * mm,  # Kg Conca / Manual
        24 * mm,  # TOTAL (Kg)
    ]

    # Alto de filas cómodo para escribir a lapicera (9.5mm cada fila de tanque)
    altos_fila = [9 * mm] + [9.5 * mm] * len(CONFIG_TANQUES_PDF) + [10 * mm]

    tabla = Table(filas_tabla, colWidths=anchos_col, rowHeights=altos_fila, repeatRows=1)

    estilo_tabla = TableStyle([
        # Encabezado
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # Columna nombres de tanques
        ("FONTNAME", (0, 1), (0, -2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (0, -2), 9),
        ("ALIGN", (0, 1), (0, -2), "LEFT"),
        ("LEFTPADDING", (0, 1), (0, -2), 6),
        ("BACKGROUND", (0, 1), (0, -2), colors.HexColor("#f8fafc")),

        # Sombras sutiles para guiar el llenado manual
        ("BACKGROUND", (3, 1), (3, -2), colors.HexColor("#fffbeb")),
        ("BACKGROUND", (7, 1), (8, -2), colors.HexColor("#fffbeb")),
        ("BACKGROUND", (9, 1), (9, -2), colors.HexColor("#f0fdf4")),

        # Fila final de totales
        ("SPAN", (0, -1), (5, -1)),
        ("ALIGN", (0, -1), (5, -1), "RIGHT"),
        ("RIGHTPADDING", (0, -1), (5, -1), 8),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 9.5),
        ("BACKGROUND", (0, -1), (8, -1), colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (9, -1), (9, -1), colors.HexColor("#dcfce7")),

        # Grilla bien marcada para impresión
        ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#475569")),
        ("LINEABOVE", (0, -1), (-1, -1), 1.3, colors.HexColor("#1e293b")),
    ])

    tabla.setStyle(estilo_tabla)
    elementos.append(tabla)

    doc.build(elementos)
    buffer.seek(0)
    return buffer
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

CONFIG_TANQUES_PDF = [
    {"tanque": "STK-MOVIL",           "altura": 50,  "capacidad": 650},
    {"tanque": "MUECAS",              "altura": 201, "capacidad": 5000},
    {"tanque": "STK- 03 Chook",       "altura": 178, "capacidad": 4564},
    {"tanque": "stk-04 pelayo",       "altura": 150, "capacidad": 2300},
    {"tanque": "STK- 05 GBA (S/A)",   "altura": 191, "capacidad": 1700},
    {"tanque": "STK- 06",             "altura": 191, "capacidad": 5000},
    {"tanque": "STK-07 PASCUA",       "altura": 196, "capacidad": 5500},
    {"tanque": "STK- 08 GBA (Leche)", "altura": 109, "capacidad": 1700},
    {"tanque": "STK- 09 Sollish",     "altura": 109, "capacidad": 1700},
    {"tanque": "STK- 10 Grageado",    "altura": 90,  "capacidad": 1000},
    {"tanque": "blanco",              "altura": 0,   "capacidad": 1000},
    {"tanque": "Tanque de licor",     "altura": 115, "capacidad": 2000},
    {"tanque": "Tanque de illexao",   "altura": 0,   "capacidad": 0},
    {"tanque": "laurico",             "altura": 94,  "capacidad": 3000},
]


def _fmt_num(val):
    if val is None or val == 0:
        return "-"
    return f"{round(val):,}".replace(",", ".")


def _calcular_fila(cfg, valor_medido, kg_manual):
    val = float(valor_medido) if valor_medido is not None else None
    kg_man = float(kg_manual) if kg_manual is not None else 0.0

    n_cm = None
    n_pct = 0.0
    cantidad = 0.0

    if val is not None and cfg["altura"] > 0:
        n_cm = max(0.0, cfg["altura"] - val)
        n_pct = min(100.0, max(0.0, (n_cm / cfg["altura"]) * 100.0))
        cantidad = (cfg["capacidad"] / cfg["altura"]) * n_cm
    elif kg_man > 0 and cfg["capacidad"] > 0:
        n_pct = min(100.0, max(0.0, (kg_man / cfg["capacidad"]) * 100.0))

    total = cantidad + kg_man
    return {
        "n_cm": round(n_cm) if n_cm is not None else None,
        "n_pct": round(n_pct) if n_cm is not None else None,
        "cantidad": round(cantidad),
        "kg_manual": round(kg_man),
        "total": round(total),
    }


def generar_pdf_relevamiento(relevamiento: dict) -> io.BytesIO:
    """Genera el PDF A4 horizontal de la planilla de niveles de tanques en memoria."""
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
        spaceAfter=4,
    )
    estilo_sub = ParagraphStyle(
        "SubtituloPlanilla",
        parent=styles["Normal"],
        fontSize=9.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=10,
    )
    estilo_desc = ParagraphStyle(
        "DescCelda",
        parent=styles["Normal"],
        fontSize=8,
        leading=9.5,
        alignment=TA_LEFT,
    )

    # Formatear fecha
    fh_raw = relevamiento.get("fecha_hora")
    if isinstance(fh_raw, datetime):
        fecha_str = fh_raw.strftime("%d/%m/%Y %H:%M")
    elif fh_raw:
        try:
            fecha_str = datetime.fromisoformat(str(fh_raw)).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            fecha_str = str(fh_raw)
    else:
        fecha_str = "-"

    elementos = []
    elementos.append(Paragraph(f"PLANILLA DE NIVELES DE TANQUES — PLANTA CHOCOLATES (Relevamiento #{relevamiento.get('id', '')})", estilo_titulo))
    elementos.append(
        Paragraph(
            f"<b>Fecha y Hora:</b> {fecha_str} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Supervisor:</b> {relevamiento.get('supervisor') or '-'} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Operario:</b> {relevamiento.get('operario') or '-'}",
            estilo_sub,
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

    detalles = relevamiento.get("detalles") or []
    suma_cantidad = 0
    suma_kg_manual = 0
    suma_total = 0

    for cfg in CONFIG_TANQUES_PDF:
        det = next(
            (d for d in detalles if str(d.get("tanque", "")).strip().lower() == cfg["tanque"].strip().lower()),
            {},
        )
        calc = _calcular_fila(cfg, det.get("valor_medido"), det.get("kg_manual"))

        suma_cantidad += calc["cantidad"]
        suma_kg_manual += calc["kg_manual"]
        suma_total += calc["total"]

        val_med_txt = (
            f"{float(det['valor_medido']):g}"
            if det.get("valor_medido") is not None
            else "-"
        )
        conca_txt = str(det["nro_conca"]) if det.get("nro_conca") is not None else "-"
        desc_txt = str(det.get("descripcion") or "-").strip()

        filas_tabla.append([
            cfg["tanque"],
            str(det.get("codigo") or "-").strip() or "-",
            Paragraph(desc_txt, estilo_desc),
            val_med_txt,
            str(calc["n_cm"]) if calc["n_cm"] is not None else "-",
            f"{calc['n_pct']}%" if calc["n_pct"] is not None else "-",
            _fmt_num(calc["cantidad"]),
            conca_txt,
            _fmt_num(calc["kg_manual"]),
            _fmt_num(calc["total"]),
        ])

    # Fila final de totales
    filas_tabla.append([
        "TOTAL GENERAL EN PLANTA",
        "",
        "",
        "",
        "",
        "",
        _fmt_num(suma_cantidad),
        "",
        f"{_fmt_num(suma_kg_manual)} kg",
        f"{_fmt_num(suma_total)} kg",
    ])

    anchos_col = [
        34 * mm,  # TK
        22 * mm,  # Código
        66 * mm,  # Descripción
        22 * mm,  # Valor Medido
        16 * mm,  # N / CM
        16 * mm,  # N / %
        25 * mm,  # Cantidad (Kg)
        18 * mm,  # N° Conca
        28 * mm,  # Kg Conca / Manual
        26 * mm,  # TOTAL (Kg)
    ]

    tabla = Table(filas_tabla, colWidths=anchos_col, repeatRows=1)

    estilo_tabla = TableStyle([
        # Encabezado oscuro igual a la pantalla
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),

        # Cuerpo general
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -2), 8.2),
        ("ALIGN", (0, 1), (0, -2), "LEFT"),
        ("FONTNAME", (0, 1), (0, -2), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (1, -2), "CENTER"),
        ("ALIGN", (3, 1), (-1, -2), "CENTER"),

        # Columna Valor Medido, Conca y Kg Manual (amarillo suave)
        ("BACKGROUND", (3, 1), (3, -2), colors.HexColor("#fffbeb")),
        ("BACKGROUND", (7, 1), (8, -2), colors.HexColor("#fffbeb")),

        # Columnas calculadas N/CM, N/%, Cantidad (verde muy suave)
        ("BACKGROUND", (4, 1), (6, -2), colors.HexColor("#f0fdf4")),
        ("TEXTCOLOR", (4, 1), (6, -2), colors.HexColor("#15803d")),
        ("FONTNAME", (4, 1), (6, -2), "Helvetica-Bold"),

        # Columna TOTAL (verde destacado)
        ("BACKGROUND", (9, 1), (9, -2), colors.HexColor("#dcfce7")),
        ("TEXTCOLOR", (9, 1), (9, -2), colors.HexColor("#166534")),
        ("FONTNAME", (9, 1), (9, -2), "Helvetica-Bold"),

        # Fila de totales generales
        ("SPAN", (0, -1), (5, -1)),
        ("ALIGN", (0, -1), (5, -1), "RIGHT"),
        ("BACKGROUND", (0, -1), (8, -1), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 8.8),
        ("BACKGROUND", (9, -1), (9, -1), colors.HexColor("#16a34a")),
        ("TEXTCOLOR", (9, -1), (9, -1), colors.white),

        # Bordes
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, colors.HexColor("#64748b")),
    ])

    tabla.setStyle(estilo_tabla)
    elementos.append(tabla)

    doc.build(elementos)
    buffer.seek(0)
    return buffer
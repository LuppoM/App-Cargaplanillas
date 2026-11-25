from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt_num(valor: Any, decimales: int = 2) -> str:
    try:
        num = float(valor or 0)
    except (TypeError, ValueError):
        num = 0.0
    txt = f"{num:,.{decimales}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def generar_pdf_informe_decomisos(
    resumen: Dict[str, Any],
    registros: List[Dict[str, Any]],
) -> BytesIO:
    """
    Genera en memoria el PDF del informe semanal de decomisos de Chocolate
    y devuelve el buffer BytesIO posicionado en 0.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Informe Decomisos Chocolate - Semana {resumen.get('n_semana')} ({resumen.get('anio')})",
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloInforme",
        parent=estilos["Heading1"],
        fontSize=14,
        leading=17,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=2,
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloInforme",
        parent=estilos["Normal"],
        fontSize=9.5,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )
    estilo_seccion = ParagraphStyle(
        "SeccionInforme",
        parent=estilos["Heading2"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=6,
    )
    estilo_celda = ParagraphStyle(
        "CeldaTabla",
        parent=estilos["Normal"],
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor("#1e293b"),
    )

    anio = resumen.get("anio", "")
    n_semana = resumen.get("n_semana", "")
    total_elab = float(resumen.get("total_elaborados") or 0)
    total_deco = float(resumen.get("total_decomiso") or 0)
    pct_total = float(resumen.get("porcentaje_total") or 0)

    elementos: List[Any] = []

    # Encabezado
    elementos.append(Paragraph("INFORME SEMANAL DE DECOMISOS · PLANTA CHOCOLATE", estilo_titulo))
    fecha_emision = datetime.now().strftime("%d/%m/%Y %H:%M")
    elementos.append(
        Paragraph(
            f"<b>Período:</b> Año {anio} · Semana {n_semana} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Emitido:</b> {fecha_emision}",
            estilo_subtitulo,
        )
    )

    # Cuadro de KPIs principales
    tabla_kpi = Table(
        [
            ["KG ELABORADOS", "KG DECOMISO TOTAL", "% DECOMISO GENERAL"],
            [
                f"{_fmt_num(total_elab)} kg",
                f"{_fmt_num(total_deco)} kg",
                f"{_fmt_num(pct_total)} %",
            ],
        ],
        colWidths=[60 * mm, 60 * mm, 62 * mm],
    )
    tabla_kpi.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 12),
                ("TEXTCOLOR", (0, 1), (0, 1), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor("#b91c1c")),
                ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor("#c2410c")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    elementos.append(tabla_kpi)
    elementos.append(Spacer(1, 6 * mm))

    # Sección 1: Consolidado Semanal por Sector
    elementos.append(Paragraph("1. Consolidado Semanal por Sector", estilo_seccion))

    filas_consolidado = [["SECTOR", "Kg Elaborados", "Kg Decomiso", "Porcentaje"]]
    for f in resumen.get("filas", []):
        pct = f.get("porcentaje")
        pct_txt = f"{_fmt_num(pct)} %" if pct is not None else "-"
        filas_consolidado.append(
            [
                Paragraph(f"<b>{f.get('sector', '')}</b>", estilo_celda),
                _fmt_num(f.get("kg_elaborados")),
                _fmt_num(f.get("kg_decomiso"), 1),
                pct_txt,
            ]
        )

    filas_consolidado.append(
        [
            "KG TOTALES",
            _fmt_num(total_elab),
            _fmt_num(total_deco, 1),
            f"{_fmt_num(pct_total)} %",
        ]
    )

    tabla_consolidado = Table(
        filas_consolidado,
        colWidths=[76 * mm, 36 * mm, 36 * mm, 34 * mm],
        repeatRows=1,
    )
    tabla_consolidado.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    elementos.append(tabla_consolidado)
    elementos.append(Spacer(1, 6 * mm))

    # Sección 2: Detalle de Registros de la Semana
    elementos.append(Paragraph("2. Detalle de Registros de Decomiso", estilo_seccion))

    filas_detalle = [["Fecha", "Código", "Sector", "Motivo", "Peso (Kg)", "Responsable"]]
    if registros:
        for r in registros:
            filas_detalle.append(
                [
                    str(r.get("fecha", "")),
                    str(r.get("codigo", "")),
                    Paragraph(f"<b>{r.get('sector', '')}</b>", estilo_celda),
                    Paragraph(str(r.get("motivo", "")), estilo_celda),
                    _fmt_num(r.get("peso")),
                    Paragraph(str(r.get("responsable", "")), estilo_celda),
                ]
            )
    else:
        filas_detalle.append(["-", "-", "Sin registros en la semana seleccionada", "-", "-", "-"])

    tabla_detalle = Table(
        filas_detalle,
        colWidths=[23 * mm, 24 * mm, 38 * mm, 45 * mm, 22 * mm, 30 * mm],
        repeatRows=1,
    )
    tabla_detalle.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("ALIGN", (0, 0), (3, -1), "LEFT"),
                ("ALIGN", (4, 0), (4, -1), "RIGHT"),
                ("ALIGN", (5, 0), (5, -1), "LEFT"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    elementos.append(tabla_detalle)

    doc.build(elementos)
    buffer.seek(0)
    return buffer
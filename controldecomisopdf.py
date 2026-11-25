from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing, Line, Rect, String
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


def _crear_grafico_kg_vs_decomiso(
    filas: List[Dict[str, Any]],
    ancho: float = 182 * mm,
    alto: float = 64 * mm,
) -> Drawing:
    """
    Replica el gráfico superior de Excel:
    'KG PRODUCIDOS Y DECOMISO GENERADO POR SEMANA' (naranja vs gris).
    """
    d = Drawing(ancho, alto)

    # Marco sutil estilo tarjeta de Excel
    d.add(
        Rect(
            0, 0, ancho, alto,
            strokeColor=colors.HexColor("#d9d9d9"),
            fillColor=colors.white,
            strokeWidth=0.75,
        )
    )

    # Título centrado
    d.add(
        String(
            ancho / 2,
            alto - 14,
            "KG PRODUCIDOS Y DECOMISO GENERADO POR SEMANA",
            fontName="Helvetica",
            fontSize=10.5,
            fillColor=colors.HexColor("#595959"),
            textAnchor="middle",
        )
    )

    categorias = [str(f.get("sector", "")) for f in filas] or ["Sin datos"]
    serie_elab = [float(f.get("kg_elaborados") or 0) for f in filas] or [0.0]
    serie_deco = [float(f.get("kg_decomiso") or 0) for f in filas] or [0.0]

    max_val = max(serie_elab + serie_deco + [10.0])
    tope_y = max_val * 1.18

    chart = VerticalBarChart()
    chart.x = 16 * mm
    chart.y = 21 * mm
    chart.width = ancho - 24 * mm
    chart.height = alto - 34 * mm
    chart.data = [serie_elab, serie_deco]

    chart.groupSpacing = 8
    chart.barSpacing = 1.5
    chart.barWidth = max(4.5, min(11.0, (chart.width / max(len(categorias), 1)) * 0.34))

    # Colores idénticos a Excel (naranja y gris)
    chart.bars[0].fillColor = colors.HexColor("#ED7D31")
    chart.bars[0].strokeColor = colors.HexColor("#ED7D31")
    chart.bars[1].fillColor = colors.HexColor("#A5A5A5")
    chart.bars[1].strokeColor = colors.HexColor("#A5A5A5")

    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = tope_y
    chart.valueAxis.visibleLabels = False
    chart.valueAxis.visibleTicks = False
    chart.valueAxis.strokeColor = colors.white
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.gridStrokeColor = colors.HexColor("#d9d9d9")
    chart.valueAxis.gridStrokeWidth = 0.5

    chart.categoryAxis.categoryNames = categorias
    chart.categoryAxis.strokeColor = colors.HexColor("#d9d9d9")
    chart.categoryAxis.visibleTicks = False
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 6.8
    chart.categoryAxis.labels.fillColor = colors.HexColor("#595959")
    chart.categoryAxis.labels.angle = 35
    chart.categoryAxis.labels.boxAnchor = "ne"
    chart.categoryAxis.labels.dx = 2
    chart.categoryAxis.labels.dy = -2

    # Etiquetas de valores encima de cada barra
    chart.barLabels.nudge = 4
    chart.barLabels.fontName = "Helvetica"
    chart.barLabels.fontSize = 6.2
    chart.barLabels.fillColor = colors.HexColor("#404040")

    def _fmt_etiqueta_kg(val: float) -> str:
        if val <= 0:
            return "0,0"
        return _fmt_num(val, 1) if val < 1000 else _fmt_num(val, 2)

    chart.barLabelFormat = _fmt_etiqueta_kg

    d.add(chart)

    # Leyenda inferior centrada
    leyenda = Legend()
    leyenda.x = (ancho / 2) - 48 * mm
    leyenda.y = 4 * mm
    leyenda.dx = 6
    leyenda.dy = 6
    leyenda.fontName = "Helvetica"
    leyenda.fontSize = 7.5
    leyenda.fillColor = colors.HexColor("#595959")
    leyenda.columnMaximum = 1
    leyenda.deltax = 55
    leyenda.colorNamePairs = [
        (colors.HexColor("#ED7D31"), "Kg elaborados"),
        (colors.HexColor("#A5A5A5"), "Kg decomiso"),
    ]
    d.add(leyenda)

    return d


def _crear_grafico_porcentaje_semanal(
    filas: List[Dict[str, Any]],
    n_semana: Any,
    ancho: float = 182 * mm,
    alto: float = 62 * mm,
) -> Drawing:
    """
    Replica el gráfico inferior de Excel:
    'PORCENTAJE DECOMISO POR SEMANA' (barras amarillas/doradas).
    """
    d = Drawing(ancho, alto)

    d.add(
        Rect(
            0, 0, ancho, alto,
            strokeColor=colors.HexColor("#d9d9d9"),
            fillColor=colors.white,
            strokeWidth=0.75,
        )
    )

    d.add(
        String(
            ancho / 2,
            alto - 14,
            "PORCENTAJE DECOMISO POR SEMANA",
            fontName="Helvetica",
            fontSize=10.5,
            fillColor=colors.HexColor("#595959"),
            textAnchor="middle",
        )
    )

    categorias = [str(f.get("sector", "")) for f in filas] or ["Sin datos"]
    serie_pct = [float(f.get("porcentaje") or 0.0) for f in filas] or [0.0]

    max_pct = max(serie_pct + [0.10])
    tope_y = max_pct * 1.22

    chart = VerticalBarChart()
    chart.x = 18 * mm
    chart.y = 21 * mm
    chart.width = ancho - 26 * mm
    chart.height = alto - 34 * mm
    chart.data = [serie_pct]

    chart.groupSpacing = 10
    chart.barWidth = max(6.0, min(14.0, (chart.width / max(len(categorias), 1)) * 0.45))

    chart.bars[0].fillColor = colors.HexColor("#FFC000")
    chart.bars[0].strokeColor = colors.HexColor("#FFC000")

    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = tope_y
    chart.valueAxis.visibleLabels = True
    chart.valueAxis.visibleTicks = False
    chart.valueAxis.strokeColor = colors.white
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.gridStrokeColor = colors.HexColor("#d9d9d9")
    chart.valueAxis.gridStrokeWidth = 0.5
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 6.8
    chart.valueAxis.labels.fillColor = colors.HexColor("#595959")
    chart.valueAxis.labelTextFormat = lambda v: f"{_fmt_num(v, 2)}%"

    chart.categoryAxis.categoryNames = categorias
    chart.categoryAxis.strokeColor = colors.HexColor("#d9d9d9")
    chart.categoryAxis.visibleTicks = False
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 6.8
    chart.categoryAxis.labels.fillColor = colors.HexColor("#595959")
    chart.categoryAxis.labels.angle = 35
    chart.categoryAxis.labels.boxAnchor = "ne"
    chart.categoryAxis.labels.dx = 2
    chart.categoryAxis.labels.dy = -2

    chart.barLabels.nudge = 4
    chart.barLabels.fontName = "Helvetica"
    chart.barLabels.fontSize = 6.5
    chart.barLabels.fillColor = colors.HexColor("#404040")
    chart.barLabelFormat = lambda v: f"{_fmt_num(v, 2)}%"

    d.add(chart)

    leyenda = Legend()
    leyenda.x = (ancho / 2) - 18 * mm
    leyenda.y = 4 * mm
    leyenda.dx = 6
    leyenda.dy = 6
    leyenda.fontName = "Helvetica"
    leyenda.fontSize = 7.5
    leyenda.fillColor = colors.HexColor("#595959")
    leyenda.columnMaximum = 1
    leyenda.colorNamePairs = [
        (colors.HexColor("#FFC000"), f"SEMANA {n_semana}"),
    ]
    d.add(leyenda)

    return d


def generar_pdf_informe_decomisos(
    resumen: Dict[str, Any],
    registros: Optional[List[Dict[str, Any]]] = None,
) -> BytesIO:
    """
    Genera en memoria el PDF ejecutivo semanal de decomisos de Chocolate
    con cuadro consolidado y los dos gráficos comparativos estilo Excel.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=11 * mm,
        bottomMargin=11 * mm,
        title=f"Informe Decomisos Chocolate - Semana {resumen.get('n_semana')} ({resumen.get('anio')})",
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloInforme",
        parent=estilos["Heading1"],
        fontSize=13,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=1,
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloInforme",
        parent=estilos["Normal"],
        fontSize=8.8,
        textColor=colors.HexColor("#475569"),
        spaceAfter=6,
    )
    estilo_celda = ParagraphStyle(
        "CeldaTabla",
        parent=estilos["Normal"],
        fontSize=8,
        leading=9.5,
        textColor=colors.HexColor("#1e293b"),
    )

    anio = resumen.get("anio", "")
    n_semana = resumen.get("n_semana", "")
    total_elab = float(resumen.get("total_elaborados") or 0)
    total_deco = float(resumen.get("total_decomiso") or 0)
    pct_total = float(resumen.get("porcentaje_total") or 0)
    filas = resumen.get("filas", [])

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
                f"{_fmt_num(total_deco, 1)} kg",
                f"{_fmt_num(pct_total)} %",
            ],
        ],
        colWidths=[60.6 * mm, 60.6 * mm, 60.8 * mm],
    )
    tabla_kpi.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 11),
                ("TEXTCOLOR", (0, 1), (0, 1), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor("#b91c1c")),
                ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor("#c2410c")),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    elementos.append(tabla_kpi)
    elementos.append(Spacer(1, 3.5 * mm))

    # Tabla Consolidado Semanal por Sector (compacta)
    filas_consolidado = [["SECTOR", "Kg Elaborados", "Kg Decomiso", "Porcentaje"]]
    for f in filas:
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
                ("FONTSIZE", (0, 0), (-1, 0), 8.2),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    elementos.append(tabla_consolidado)
    elementos.append(Spacer(1, 4 * mm))

    # Gráfico 1: Kg elaborados vs Kg decomiso
    elementos.append(_crear_grafico_kg_vs_decomiso(filas))
    elementos.append(Spacer(1, 3.5 * mm))

    # Gráfico 2: Porcentaje decomiso por semana
    elementos.append(_crear_grafico_porcentaje_semanal(filas, n_semana=n_semana))

    doc.build(elementos)
    buffer.seek(0)
    return buffer
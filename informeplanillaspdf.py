from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


COLS_DETENCION = [
    "detencion_produccion",
    "detencion_refrigerio",
    "detencion_mecanico",
    "detencion_electrico",
    "detencion_calidad",
    "detencion_programacion",
    "detencion_limpieza",
    "detencion_abastecimiento",
    "detencion_desarrollo",
    "detencion_alistamiento",
    "detencion_rrhh",
    "detencion_suministro",
]


def _fmt_num(valor: Any, decimales: int = 2) -> str:
    try:
        num = float(valor or 0)
    except (TypeError, ValueError):
        num = 0.0
    txt = f"{num:,.{decimales}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_fecha(fecha_val: Any) -> str:
    s = str(fecha_val or "").strip()[:10]
    if len(s) == 10 and s[4] == "-":
        y, m, d = s.split("-")
        return f"{d}/{m}/{y}"
    return s


def _sumar_detenciones_fila(reg: Dict[str, Any]) -> float:
    return sum(float(reg.get(col) or 0) for col in COLS_DETENCION)


def _buscar_teorico(
    teoricos: List[Dict[str, Any]],
    codigo: Any,
    centro_trabajo: Any,
) -> Optional[Dict[str, Any]]:
    cod = str(codigo or "").strip().lower()
    sec = str(centro_trabajo or "").strip().lower()
    if not cod or not teoricos:
        return None

    if sec:
        for t in teoricos:
            cod_m = str(t.get("codigo") or "").strip().lower() == cod
            sec_t = str(t.get("centro_trabajo") or t.get("sector") or "").strip().lower()
            if cod_m and sec_t == sec:
                return t

    for t in teoricos:
        if str(t.get("codigo") or "").strip().lower() == cod:
            return t
    return None


def _calcular_kg_reales(
    reg: Dict[str, Any],
    teoricos: Optional[List[Dict[str, Any]]] = None,
) -> float:
    cantidad = float(reg.get("kg_cajas_reales") or 0)
    if not teoricos:
        return cantidad

    teorico = _buscar_teorico(teoricos, reg.get("codigo"), reg.get("centro_trabajo"))
    if not teorico:
        return cantidad

    uxb = float(teorico.get("uxb") or 0)
    peso_input = float(reg.get("peso_promedio_unid_kg") or 0)
    peso = peso_input if peso_input > 0 else float(teorico.get("peso") or 0)

    peso_por_caja = uxb * peso
    if peso_por_caja > 0 and uxb > 1:
        return cantidad * peso_por_caja

    return cantidad


def generar_pdf_informe_planillas(
    registros: List[Dict[str, Any]],
    fecha_desde: str,
    fecha_hasta: str,
    planta: Optional[str] = None,
    teoricos: Optional[List[Dict[str, Any]]] = None,
) -> BytesIO:
    buffer = BytesIO()
    planta_titulo = planta.strip().upper() if planta and planta.strip() else "TODAS LAS PLANTAS"
    f_desde_txt = _fmt_fecha(fecha_desde)
    f_hasta_txt = _fmt_fecha(fecha_hasta)
    rango_txt = f_desde_txt if f_desde_txt == f_hasta_txt else f"{f_desde_txt} al {f_hasta_txt}"

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Informe Planillas - {planta_titulo} ({rango_txt})",
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        "TituloPlanillas",
        parent=estilos["Heading1"],
        fontSize=13.5,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=2,
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloPlanillas",
        parent=estilos["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8,
    )
    estilo_seccion = ParagraphStyle(
        "SeccionPlanillas",
        parent=estilos["Heading2"],
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=6,
        spaceAfter=5,
    )
    estilo_celda = ParagraphStyle(
        "CeldaPlanillas",
        parent=estilos["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )

    total_kg = 0.0
    total_hs = 0.0
    total_deco = 0.0
    total_repro = 0.0
    total_scrap = 0.0
    total_deten = 0.0
    fechas_distintas = set()

    agrupado: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {
            "turnos": 0,
            "horas": 0.0,
            "kg": 0.0,
            "decomiso": 0.0,
            "reproceso": 0.0,
            "scrap": 0.0,
            "detenciones": 0.0,
        }
    )

    filas_procesadas: List[Dict[str, Any]] = []

    for r in registros:
        f_txt = _fmt_fecha(r.get("fecha"))
        if f_txt:
            fechas_distintas.add(f_txt)

        sector = str(r.get("centro_trabajo") or "Sin especificar").strip()
        hs = float(r.get("horas_trabajadas") or 0)
        kg = _calcular_kg_reales(r, teoricos)
        deco = float(r.get("decomiso_kg") or 0)
        repro = float(r.get("reproceso_kg") or 0)
        scrap = float(r.get("scrap_flex_kg") or 0)
        deten = _sumar_detenciones_fila(r)

        total_hs += hs
        total_kg += kg
        total_deco += deco
        total_repro += repro
        total_scrap += scrap
        total_deten += deten

        agrupado[sector]["turnos"] += 1
        agrupado[sector]["horas"] += hs
        agrupado[sector]["kg"] += kg
        agrupado[sector]["decomiso"] += deco
        agrupado[sector]["reproceso"] += repro
        agrupado[sector]["scrap"] += scrap
        agrupado[sector]["detenciones"] += deten

        filas_procesadas.append({
            **r,
            "_kg_real_calc": kg,
            "_deten_min_calc": deten,
        })

    elementos: List[Any] = []

    elementos.append(Paragraph(f"INFORME DE PRODUCCIÓN Y PLANILLAS DIARIAS · {planta_titulo}", estilo_titulo))
    fecha_emision = datetime.now().strftime("%d/%m/%Y %H:%M")
    elementos.append(
        Paragraph(
            f"<b>Período:</b> {rango_txt} ({len(fechas_distintas)} día/s con carga) &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Registros:</b> {len(registros)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Emitido:</b> {fecha_emision}",
            estilo_subtitulo,
        )
    )

    tabla_kpi = Table(
        [
            [
                "KG PRODUCIDOS",
                "HORAS TRABAJADAS",
                "DECOMISO (KG)",
                "REPROCESO (KG)",
                "SCRAP FLEX (KG)",
                "DETENCIONES (MIN)",
            ],
            [
                f"{_fmt_num(total_kg)} kg",
                f"{_fmt_num(total_hs)} hs",
                f"{_fmt_num(total_deco)} kg",
                f"{_fmt_num(total_repro)} kg",
                f"{_fmt_num(total_scrap)} kg",
                f"{_fmt_num(total_deten, 0)} min",
            ],
        ],
        colWidths=[48 * mm, 44 * mm, 44 * mm, 44 * mm, 45 * mm, 48 * mm],
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
                ("TEXTCOLOR", (0, 1), (0, 1), colors.HexColor("#0369a1")),
                ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor("#b91c1c")),
                ("TEXTCOLOR", (5, 1), (5, 1), colors.HexColor("#c2410c")),
                ("TOPPADDING", (0, 0), (-1, -1), 5.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    elementos.append(tabla_kpi)
    elementos.append(Spacer(1, 5 * mm))

    elementos.append(Paragraph("1. Consolidado por Centro de Trabajo / Sector", estilo_seccion))

    filas_resumen = [
        [
            "Centro de Trabajo",
            "Partes",
            "Horas Trab.",
            "Kg Producidos",
            "Decomiso (Kg)",
            "Reproceso (Kg)",
            "Scrap Flex (Kg)",
            "Detenciones (Min)",
        ]
    ]

    for sector in sorted(agrupado.keys(), key=lambda x: x.lower()):
        d = agrupado[sector]
        filas_resumen.append(
            [
                Paragraph(f"<b>{sector}</b>", estilo_celda),
                str(int(d["turnos"])),
                _fmt_num(d["horas"]),
                _fmt_num(d["kg"]),
                _fmt_num(d["decomiso"]),
                _fmt_num(d["reproceso"]),
                _fmt_num(d["scrap"]),
                _fmt_num(d["detenciones"], 0),
            ]
        )

    filas_resumen.append(
        [
            "TOTAL PERÍODO",
            str(len(registros)),
            _fmt_num(total_hs),
            _fmt_num(total_kg),
            _fmt_num(total_deco),
            _fmt_num(total_repro),
            _fmt_num(total_scrap),
            _fmt_num(total_deten, 0),
        ]
    )

    tabla_resumen = Table(
        filas_resumen,
        colWidths=[69 * mm, 20 * mm, 28 * mm, 34 * mm, 30 * mm, 30 * mm, 30 * mm, 32 * mm],
        repeatRows=1,
    )
    tabla_resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.2),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 5 * mm))

    elementos.append(Paragraph("2. Detalle de Registros del Período", estilo_seccion))

    filas_detalle = [
        [
            "Fecha",
            "Turno",
            "Centro de Trabajo",
            "Código",
            "Hs",
            "Dot.",
            "Kg Prod.",
            "Decomiso",
            "Reproceso",
            "Scrap Flex",
            "Deten. (min)",
        ]
    ]

    if filas_procesadas:
        registros_ordenados = sorted(
            filas_procesadas,
            key=lambda x: (str(x.get("fecha") or ""), str(x.get("turno") or ""), str(x.get("centro_trabajo") or "")),
        )
        for r in registros_ordenados:
            filas_detalle.append(
                [
                    _fmt_fecha(r.get("fecha")),
                    str(r.get("turno") or ""),
                    Paragraph(f"<b>{r.get('centro_trabajo') or ''}</b>", estilo_celda),
                    str(r.get("codigo") or ""),
                    _fmt_num(r.get("horas_trabajadas")),
                    _fmt_num(r.get("dotacion_real"), 0),
                    _fmt_num(r.get("_kg_real_calc")),
                    _fmt_num(r.get("decomiso_kg")),
                    _fmt_num(r.get("reproceso_kg")),
                    _fmt_num(r.get("scrap_flex_kg")),
                    _fmt_num(r.get("_deten_min_calc"), 0),
                ]
            )
    else:
        filas_detalle.append(["-", "-", "No se encontraron planillas en el rango seleccionado", "-", "-", "-", "-", "-", "-", "-", "-"])

    tabla_detalle = Table(
        filas_detalle,
        colWidths=[22 * mm, 20 * mm, 53 * mm, 24 * mm, 16 * mm, 14 * mm, 26 * mm, 24 * mm, 24 * mm, 24 * mm, 26 * mm],
        repeatRows=1,
    )
    tabla_detalle.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("ALIGN", (0, 0), (3, -1), "LEFT"),
                ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 1), (-1, -1), 7.8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    elementos.append(tabla_detalle)

    doc.build(elementos)
    buffer.seek(0)
    return buffer
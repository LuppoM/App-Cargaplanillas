from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DETENCIONES_COLS = [
    ("detencion_produccion", "Producción"),
    ("detencion_refrigerio", "Refrigerio"),
    ("detencion_mecanico", "Mecánico"),
    ("detencion_electrico", "Eléctrico"),
    ("detencion_calidad", "Calidad"),
    ("detencion_programacion", "Programación"),
    ("detencion_limpieza", "Limpieza"),
    ("detencion_abastecimiento", "Abastecimiento"),
    ("detencion_desarrollo", "Desarrollo"),
    ("detencion_alistamiento", "Alistamiento"),
    ("detencion_rrhh", "RRHH"),
    ("detencion_suministro", "Suministro"),
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


def _extraer_mes(fecha_val: Any) -> str:
    s = str(fecha_val or "").strip()[:10]
    if len(s) == 10 and s[4] == "-":
        return str(int(s.split("-")[1]))
    if len(s) == 10 and s[2] in ("/", "-"):
        return str(int(s.split(s[2])[1]))
    return "-"


def _buscar_teorico(
    teoricos: Optional[List[Dict[str, Any]]],
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


def _procesar_registro(
    reg: Dict[str, Any],
    teoricos: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    hs_prog = float(reg.get("horas_trabajadas") or 0)
    prod_bu = float(reg.get("kg_cajas_reales") or 0)
    peso_prom_input = float(reg.get("peso_promedio_unid_kg") or 0)
    repro_kg = float(reg.get("reproceso_kg") or 0)
    deco_kg = float(reg.get("decomiso_kg") or 0)
    scrap_kg = float(reg.get("scrap_flex_kg") or 0)

    dot_teorica = float(reg.get("dotacion_teorica") or 0)
    dot_real_raw = reg.get("dotacion_real")
    dot_real = (
        float(dot_real_raw)
        if dot_real_raw is not None and str(dot_real_raw).strip() != ""
        else dot_teorica
    )

    teorico = _buscar_teorico(teoricos, reg.get("codigo"), reg.get("centro_trabajo"))
    descripcion = ""
    marca = "-"
    tipo = "-"
    prod_kg = prod_bu
    kg_teorico = 0.0
    peso_teorico = 0.0
    uxb = 0.0
    desvio_peso_kg = 0.0
    ct_flex_kg = 0.0

    if teorico:
        descripcion = str(teorico.get("descripcion") or "").strip()
        marca = str(teorico.get("marca") or "Palmesano").strip()
        tipo = str(teorico.get("tipo") or ("PT" if float(teorico.get("uxb") or 0) > 1 else "SE")).strip()
        uxb = float(teorico.get("uxb") or 0)
        peso_teorico = float(teorico.get("peso") or 0)
        bultos_hora = float(teorico.get("bultos_hora") or 0)

        peso_efectivo = peso_prom_input if peso_prom_input > 0 else peso_teorico
        peso_caja = uxb * peso_efectivo
        if peso_caja > 0 and uxb > 1:
            prod_kg = prod_bu * peso_caja

        kg_teorico = uxb * peso_teorico * bultos_hora * hs_prog
        if dot_teorica > 0 and dot_real > 0:
            kg_teorico = kg_teorico * (dot_real / dot_teorica)

        if peso_prom_input > 0 and peso_teorico > 0 and uxb > 1:
            desvio_peso_kg = (peso_prom_input - peso_teorico) * uxb * prod_bu

        ct_flex_unit = float(teorico.get("ct_flex") or teorico.get("consumo_flex") or 0)
        if ct_flex_unit > 0:
            ct_flex_kg = ct_flex_unit * prod_bu

    deten_por_rubro: Dict[str, float] = {}
    total_deten_min = 0.0
    for col, nombre in DETENCIONES_COLS:
        val = float(reg.get(col) or 0)
        deten_por_rubro[nombre] = val
        total_deten_min += val

    hs_deten = total_deten_min / 60.0

    # Fórmulas del Excel informe diario
    efic_pct = (prod_kg / kg_teorico * 100.0) if kg_teorico > 0 else 0.0
    repro_pct = (repro_kg / (repro_kg + prod_kg) * 100.0) if (repro_kg + prod_kg) > 0 else 0.0
    deco_pct = (deco_kg / (deco_kg + prod_kg) * 100.0) if (deco_kg + prod_kg) > 0 else 0.0
    incid_pct = (hs_deten / hs_prog * 100.0) if hs_prog > 0 else 0.0
    rend_pct = efic_pct + repro_pct + deco_pct + incid_pct

    hh_hr = hs_prog * dot_real
    hh_fi = hs_prog * dot_teorica

    return {
        "id": reg.get("id") or "-",
        "mes": _extraer_mes(reg.get("fecha")),
        "fecha": _fmt_fecha(reg.get("fecha")),
        "fecha_raw": str(reg.get("fecha") or ""),
        "turno": str(reg.get("turno") or ""),
        "hs_prog": hs_prog,
        "linea": str(reg.get("centro_trabajo") or "Sin Sector").strip(),
        "familia": str(reg.get("planta") or "").strip().capitalize(),
        "marca": marca,
        "tipo": tipo,
        "codigo": str(reg.get("codigo") or "").strip(),
        "descripcion": descripcion,
        "prod_bu": prod_bu,
        "kg_teorico": kg_teorico,
        "prod_kg": prod_kg,
        "efic_pct": efic_pct,
        "repro_kg": repro_kg,
        "repro_pct": repro_pct,
        "deco_kg": deco_kg,
        "deco_pct": deco_pct,
        "peso_prom": peso_prom_input,
        "desvio_peso_kg": desvio_peso_kg,
        "scrap_kg": scrap_kg,
        "ct_flex_kg": ct_flex_kg,
        "deten_rubros": deten_por_rubro,
        "total_deten_min": total_deten_min,
        "incid_pct": incid_pct,
        "hh_hr": hh_hr,
        "hh_fi": hh_fi,
        "dot_real": dot_real,
        "rend_pct": rend_pct,
        "detenciones_lista": reg.get("detenciones") if isinstance(reg.get("detenciones"), list) else [],
    }


def _obtener_logo() -> Optional[Image]:
    for ruta in ("static/logo.png", "static/palmesano.png", "static/icono.png"):
        if os.path.exists(ruta):
            try:
                img = Image(ruta, width=26 * mm, height=12 * mm)
                img.hAlign = "LEFT"
                return img
            except Exception:
                pass
    return None


def _crear_grafico_barras(
    titulo: str,
    etiquetas: List[str],
    valores: List[float],
    color_barra: colors.Color,
    ancho: float = 132 * mm,
    alto: float = 68 * mm,
) -> Drawing:
    d = Drawing(ancho, alto)
    d.add(
        String(
            4,
            alto - 11,
            titulo,
            fontName="Helvetica-Bold",
            fontSize=8.5,
            fillColor=colors.HexColor("#1e293b"),
        )
    )

    if not etiquetas or not valores:
        d.add(
            String(
                10,
                alto / 2,
                "Sin datos suficientes para graficar",
                fontName="Helvetica",
                fontSize=7.5,
                fillColor=colors.HexColor("#64748b"),
            )
        )
        return d

    # Limitar a top 12 líneas para que el gráfico sea legible
    pares = list(zip(etiquetas, valores))[:12]
    etiquetas_rec = [e[:20] for e, _ in pares][::-1]
    valores_rec = [[round(v, 2) for _, v in pares][::-1]]

    chart = HorizontalBarChart()
    chart.x = 46 * mm
    chart.y = 8 * mm
    chart.width = ancho - 54 * mm
    chart.height = alto - 22 * mm
    chart.data = valores_rec
    chart.bars[0].fillColor = color_barra
    chart.bars[0].strokeColor = color_barra
    chart.barWidth = 6
    chart.groupSpacing = 4

    max_val = max(valores_rec[0]) if valores_rec[0] else 100.0
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(10.0, round(max_val * 1.18, 0))
    chart.valueAxis.labels.fontSize = 6.5
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.strokeColor = colors.HexColor("#94a3b8")

    chart.categoryAxis.categoryNames = etiquetas_rec
    chart.categoryAxis.labels.fontSize = 6.5
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.strokeColor = colors.HexColor("#94a3b8")

    chart.barLabelFormat = "%.1f%%"
    chart.barLabels.nudge = 4
    chart.barLabels.fontSize = 6
    chart.barLabels.fontName = "Helvetica-Bold"
    chart.barLabels.fillColor = colors.HexColor("#1e293b")

    d.add(chart)
    return d


def generar_pdf_informe_planillas(
    registros: List[Dict[str, Any]],
    fecha_desde: str,
    fecha_hasta: str,
    planta: Optional[str] = None,
    teoricos: Optional[List[Dict[str, Any]]] = None,
) -> BytesIO:
    buffer = BytesIO()

    # A4 apaisado: 297 x 210 mm -> ancho útil con márgenes de 8 mm = 281 mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
        title="Informe Diario de Producción",
    )

    azul_corp = colors.HexColor("#1b365d")
    azul_sub = colors.HexColor("#2b6cb0")
    gris_header = colors.HexColor("#334155")
    gris_totales = colors.HexColor("#e2e8f0")
    gris_zebra = colors.HexColor("#f8fafc")
    borde = colors.HexColor("#cbd5e1")

    estilos = getSampleStyleSheet()
    st_titulo = ParagraphStyle(
        "Tit",
        parent=estilos["Heading1"],
        fontSize=13,
        leading=15,
        fontName="Helvetica-Bold",
        textColor=azul_corp,
        spaceAfter=1,
    )
    st_sub = ParagraphStyle(
        "Sub",
        parent=estilos["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334155"),
    )
    st_sec = ParagraphStyle(
        "Sec",
        parent=estilos["Heading2"],
        fontSize=9.5,
        leading=12,
        fontName="Helvetica-Bold",
        textColor=azul_corp,
        spaceBefore=3,
        spaceAfter=3,
    )
    st_celda = ParagraphStyle(
        "Cel",
        parent=estilos["Normal"],
        fontSize=6.3,
        leading=7.5,
        textColor=colors.HexColor("#0f172a"),
    )
    st_celda_det = ParagraphStyle(
        "CelDet",
        parent=estilos["Normal"],
        fontSize=7.2,
        leading=9,
        textColor=colors.HexColor("#0f172a"),
    )

    planta_txt = planta.strip().upper() if planta and planta.strip() else "TODAS LAS PLANTAS"
    f_desde_txt = _fmt_fecha(fecha_desde)
    f_hasta_txt = _fmt_fecha(fecha_hasta)
    periodo_txt = f_desde_txt if f_desde_txt == f_hasta_txt else f"{f_desde_txt} al {f_hasta_txt}"

    filas = [_procesar_registro(r, teoricos) for r in registros]
    filas.sort(key=lambda x: (x["fecha_raw"], x["turno"], x["linea"], str(x["id"])))

    # Totales globales (réplica de Fila 2 de TABLA)
    tot_hs = sum(f["hs_prog"] for f in filas)
    tot_min_prog = tot_hs * 60.0
    tot_bu = sum(f["prod_bu"] for f in filas)
    tot_kg_t = sum(f["kg_teorico"] for f in filas)
    tot_kg_p = sum(f["prod_kg"] for f in filas)
    tot_repro = sum(f["repro_kg"] for f in filas)
    tot_deco = sum(f["deco_kg"] for f in filas)
    tot_desvio = sum(f["desvio_peso_kg"] for f in filas)
    tot_scrap = sum(f["scrap_kg"] for f in filas)
    tot_ct_flex = sum(f["ct_flex_kg"] for f in filas)
    tot_deten = sum(f["total_deten_min"] for f in filas)
    tot_hh_hr = sum(f["hh_hr"] for f in filas)
    tot_hh_fi = sum(f["hh_fi"] for f in filas)
    tot_dot = sum(f["dot_real"] for f in filas)

    efic_tot = (tot_kg_p / tot_kg_t * 100.0) if tot_kg_t > 0 else 0.0
    repro_tot = (tot_repro / (tot_repro + tot_kg_p) * 100.0) if (tot_repro + tot_kg_p) > 0 else 0.0
    deco_tot = (tot_deco / (tot_deco + tot_kg_p) * 100.0) if (tot_deco + tot_kg_p) > 0 else 0.0
    desvio_tot = (tot_desvio / tot_kg_p * 100.0) if tot_kg_p > 0 else 0.0
    scrap_tot = (tot_scrap / (tot_scrap + tot_ct_flex) * 100.0) if (tot_scrap + tot_ct_flex) > 0 else 0.0
    incid_tot = (tot_deten / tot_min_prog * 100.0) if tot_min_prog > 0 else 0.0
    rend_tot = efic_tot + repro_tot + deco_tot + incid_tot
    prod_hh_hr = (tot_kg_p / tot_hh_hr) if tot_hh_hr > 0 else 0.0
    prod_hh_fi = (tot_kg_p / tot_hh_fi) if tot_hh_fi > 0 else 0.0

    # Totales por rubro de detención
    tot_rubros: Dict[str, float] = {nombre: 0.0 for _, nombre in DETENCIONES_COLS}
    for f in filas:
        for _, nombre in DETENCIONES_COLS:
            tot_rubros[nombre] += f["deten_rubros"].get(nombre, 0.0)

    elementos: List[Any] = []

    # =========================================================================
    # PÁGINA 1: CABECERA + RESUMEN DE KPIs Y DETENCIONES + TABLA PRINCIPAL
    # =========================================================================
    logo = _obtener_logo()
    izq_header = []
    if logo:
        izq_header.append(logo)
    izq_header.append(Paragraph(f"INFORME DIARIO DE PRODUCCIÓN · {planta_txt}", st_titulo))
    izq_header.append(
        Paragraph(
            f"<b>Fecha / Período:</b> {periodo_txt} &nbsp;|&nbsp; "
            f"<b>Partes:</b> {len(filas)} &nbsp;|&nbsp; "
            f"<b>Generado:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            st_sub,
        )
    )

    # Mini tarjeta de productividad HH (como Fila 1 cols AM-AO del Excel)
    tabla_hh = Table(
        [
            ["Kg / HH Real", "Kg / HH Teór.", "Dotación Total", "H/Prog (hs)"],
            [
                _fmt_num(prod_hh_hr, 2),
                _fmt_num(prod_hh_fi, 2),
                _fmt_num(tot_dot, 0),
                _fmt_num(tot_hs, 1),
            ],
        ],
        colWidths=[24 * mm, 24 * mm, 24 * mm, 23 * mm],
    )
    tabla_hh.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), azul_corp),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 6.8),
                ("FONTSIZE", (0, 1), (-1, 1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 1), (-1, 1), gris_zebra),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("GRID", (0, 0), (-1, -1), 0.4, borde),
            ]
        )
    )

    cab = Table([[izq_header, tabla_hh]], colWidths=[186 * mm, 95 * mm])
    cab.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elementos.append(cab)
    elementos.append(Spacer(1, 2.5 * mm))

    # Tira superior de 12 rubros de detención (réplica exacta de Fila 1 y Fila 2 cols Y..AK)
    nombres_rubros = [n for _, n in DETENCIONES_COLS] + ["Total Deten"]
    mins_rubros = [_fmt_num(tot_rubros[n], 0) for _, n in DETENCIONES_COLS] + [_fmt_num(tot_deten, 0)]
    pcts_rubros = [
        f"{_fmt_num((tot_rubros[n] / tot_min_prog * 100.0) if tot_min_prog > 0 else 0.0, 2)}%"
        for _, n in DETENCIONES_COLS
    ] + [f"{_fmt_num(incid_tot, 2)}%"]

    ancho_rubro = 281.0 / 13.0 * mm
    tabla_rubros_top = Table(
        [nombres_rubros, mins_rubros, pcts_rubros],
        colWidths=[ancho_rubro] * 13,
    )
    tabla_rubros_top.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), gris_header),
                ("BACKGROUND", (-1, 0), (-1, 0), azul_corp),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 6.0),
                ("FONTSIZE", (0, 1), (-1, 2), 6.5),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("BACKGROUND", (0, 1), (-1, 1), colors.white),
                ("BACKGROUND", (0, 2), (-1, 2), gris_totales),
                ("TEXTCOLOR", (-1, 1), (-1, 2), colors.HexColor("#b91c1c")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 1),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                ("GRID", (0, 0), (-1, -1), 0.4, borde),
            ]
        )
    )
    elementos.append(tabla_rubros_top)
    elementos.append(Spacer(1, 2.5 * mm))

    # Tabla Principal (Réplica de hoja TABLA - 281 mm totales)
    anchos_main = [
        8 * mm,   # Mes
        15 * mm,  # Fecha
        11 * mm,  # Turno
        10 * mm,  # H/Prog
        26 * mm,  # Línea
        13 * mm,  # Marca
        8 * mm,   # Tipo
        14 * mm,  # Código
        46 * mm,  # Descripción
        13 * mm,  # Prod BU
        15 * mm,  # KG/T
        15 * mm,  # Prod KG
        12 * mm,  # % Efic
        12 * mm,  # Repro KG
        10 * mm,  # % Repro
        12 * mm,  # Deco KG
        10 * mm,  # % Deco
        11 * mm,  # Scrap KG
        10 * mm,  # Deten min
        10 * mm,  # % In
        10 * mm,  # % Rend
    ]  # Suma = 281 mm

    encabezados_main = [
        "Mes",
        "Fecha",
        "Turno",
        "H/Pr",
        "Línea",
        "Marca",
        "Tipo",
        "Código",
        "Descripción del Producto",
        "Prod BU",
        "KG/T",
        "Prod KG",
        "% Efic",
        "Repro",
        "% Rep",
        "Decom",
        "% Dec",
        "Scrap",
        "Deten",
        "% In",
        "% Rend",
    ]

    # Fila 2 del Excel: Totales superiores antes de los registros
    fila_totales_top = [
        "",
        "TOTAL",
        "",
        _fmt_num(tot_hs, 1),
        f"{len(filas)} reg.",
        "",
        "",
        "",
        "CONSOLIDADO DEL PERÍODO",
        _fmt_num(tot_bu, 0),
        _fmt_num(tot_kg_t, 1),
        _fmt_num(tot_kg_p, 1),
        f"{_fmt_num(efic_tot, 1)}%",
        _fmt_num(tot_repro, 1),
        f"{_fmt_num(repro_tot, 2)}%",
        _fmt_num(tot_deco, 1),
        f"{_fmt_num(deco_tot, 2)}%",
        _fmt_num(tot_scrap, 1),
        _fmt_num(tot_deten, 0),
        f"{_fmt_num(incid_tot, 1)}%",
        f"{_fmt_num(rend_tot, 1)}%",
    ]

    data_main = [encabezados_main, fila_totales_top]

    if not filas:
        data_main.append(
            ["-", "-", "-", "-", "Sin registros en el período", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-"]
        )
    else:
        for f in filas:
            data_main.append(
                [
                    f["mes"],
                    f["fecha"],
                    f["turno"][:3],
                    _fmt_num(f["hs_prog"], 1),
                    Paragraph(f["linea"], st_celda),
                    f["marca"][:9],
                    f["tipo"],
                    f["codigo"],
                    Paragraph(f["descripcion"] or "-", st_celda),
                    _fmt_num(f["prod_bu"], 0),
                    _fmt_num(f["kg_teorico"], 1),
                    _fmt_num(f["prod_kg"], 1),
                    f"{_fmt_num(f['efic_pct'], 1)}%",
                    _fmt_num(f["repro_kg"], 1),
                    f"{_fmt_num(f['repro_pct'], 2)}%",
                    _fmt_num(f["deco_kg"], 1),
                    f"{_fmt_num(f['deco_pct'], 2)}%",
                    _fmt_num(f["scrap_kg"], 1),
                    _fmt_num(f["total_deten_min"], 0),
                    f"{_fmt_num(f['incid_pct'], 1)}%",
                    f"{_fmt_num(f['rend_pct'], 1)}%",
                ]
            )

    tabla_main = Table(data_main, colWidths=anchos_main, repeatRows=2)
    tabla_main.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), azul_corp),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 6.2),
                ("BACKGROUND", (0, 1), (-1, 1), gris_totales),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 6.3),
                ("FONTSIZE", (0, 2), (-1, -1), 6.2),
                ("ALIGN", (0, 0), (2, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                ("ALIGN", (4, 0), (8, -1), "LEFT"),
                ("ALIGN", (9, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, gris_zebra]),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
                ("LEFTPADDING", (0, 0), (-1, -1), 1.8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1.8),
                ("GRID", (0, 0), (-1, -1), 0.35, borde),
            ]
        )
    )
    elementos.append(tabla_main)

    # =========================================================================
    # PÁGINA 2: HOJA DETENCIONES + PANEL DE GRÁFICOS POR LÍNEA
    # =========================================================================
    elementos.append(PageBreak())
    elementos.append(Paragraph(f"DETALLE DE DETENCIONES Y ANÁLISIS POR LÍNEA · {planta_txt} ({periodo_txt})", st_titulo))
    elementos.append(Spacer(1, 2 * mm))

    # --- Tabla de Detenciones (réplica de hoja DETENCIONES) ---
    elementos.append(Paragraph("1. Detenciones Registradas por Taller y Centro de Trabajo", st_sec))

    filas_det_tabla = [
        ["Nº Reg.", "Fecha", "Turno", "Centro de Trabajo", "Taller / Motivo", "Minutos", "Horas", "Descripción Detención"]
    ]

    registros_con_deten = 0
    for f in filas:
        obs_map: Dict[str, str] = {}
        for d in f["detenciones_lista"]:
            t_key = str(d.get("taller") or "").strip().lower()
            desc_d = str(d.get("descripcion") or "").strip()
            if t_key:
                obs_map[t_key] = desc_d

        for col, nombre_taller in DETENCIONES_COLS:
            mins = f["deten_rubros"].get(nombre_taller, 0.0)
            if mins > 0:
                registros_con_deten += 1
                desc_final = obs_map.get(nombre_taller.lower(), "") or "-"
                filas_det_tabla.append(
                    [
                        str(f["id"]),
                        f["fecha"],
                        f["turno"],
                        Paragraph(f"<b>{f['linea']}</b>", st_celda_det),
                        nombre_taller,
                        f"{_fmt_num(mins, 0)} min",
                        f"{_fmt_num(mins / 60.0, 2)} hs",
                        Paragraph(desc_final, st_celda_det),
                    ]
                )

    if registros_con_deten == 0:
        filas_det_tabla.append(["-", "-", "-", "Sin detenciones registradas en el período", "-", "0 min", "0,00 hs", "-"])
    else:
        filas_det_tabla.append(
            [
                "",
                "TOTAL",
                "",
                f"{registros_con_deten} eventos",
                "",
                f"{_fmt_num(tot_deten, 0)} min",
                f"{_fmt_num(tot_deten / 60.0, 2)} hs",
                f"Incidencia total sobre tiempo programado: {_fmt_num(incid_tot, 2)}%",
            ]
        )

    tabla_detenciones = Table(
        filas_det_tabla,
        colWidths=[16 * mm, 20 * mm, 16 * mm, 42 * mm, 28 * mm, 18 * mm, 18 * mm, 123 * mm],
        repeatRows=1,
    )
    estilo_det = [
        ("BACKGROUND", (0, 0), (-1, 0), azul_corp),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.2),
        ("FONTSIZE", (0, 1), (-1, -1), 7.0),
        ("ALIGN", (0, 0), (2, -1), "CENTER"),
        ("ALIGN", (3, 0), (4, -1), "LEFT"),
        ("ALIGN", (5, 0), (6, -1), "RIGHT"),
        ("ALIGN", (7, 0), (7, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2 if registros_con_deten > 0 else -1), [colors.white, gris_zebra]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("GRID", (0, 0), (-1, -1), 0.4, borde),
    ]
    if registros_con_deten > 0:
        estilo_det.extend(
            [
                ("BACKGROUND", (0, -1), (-1, -1), gris_totales),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    tabla_detenciones.setStyle(TableStyle(estilo_det))
    elementos.append(tabla_detenciones)
    elementos.append(Spacer(1, 4 * mm))

    # --- Panel de Gráficos (réplica de hoja GRAFICOS: % Eficiencia, % Reproceso, % Decomiso, % Incidencia) ---
    elementos.append(Paragraph("2. Indicadores Gráficos por Línea / Centro de Trabajo", st_sec))

    agg_linea: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"hs": 0.0, "kg_p": 0.0, "kg_t": 0.0, "repro": 0.0, "deco": 0.0, "deten": 0.0}
    )
    for f in filas:
        ln = f["linea"]
        agg_linea[ln]["hs"] += f["hs_prog"]
        agg_linea[ln]["kg_p"] += f["prod_kg"]
        agg_linea[ln]["kg_t"] += f["kg_teorico"]
        agg_linea[ln]["repro"] += f["repro_kg"]
        agg_linea[ln]["deco"] += f["deco_kg"]
        agg_linea[ln]["deten"] += f["total_deten_min"]

    lineas_ord = sorted(agg_linea.keys(), key=lambda x: agg_linea[x]["kg_p"], reverse=True)

    efic_vals = [
        (agg_linea[l]["kg_p"] / agg_linea[l]["kg_t"] * 100.0) if agg_linea[l]["kg_t"] > 0 else 0.0
        for l in lineas_ord
    ]
    repro_vals = [
        (agg_linea[l]["repro"] / (agg_linea[l]["repro"] + agg_linea[l]["kg_p"]) * 100.0)
        if (agg_linea[l]["repro"] + agg_linea[l]["kg_p"]) > 0
        else 0.0
        for l in lineas_ord
    ]
    deco_vals = [
        (agg_linea[l]["deco"] / (agg_linea[l]["deco"] + agg_linea[l]["kg_p"]) * 100.0)
        if (agg_linea[l]["deco"] + agg_linea[l]["kg_p"]) > 0
        else 0.0
        for l in lineas_ord
    ]
    incid_vals = [
        (agg_linea[l]["deten"] / (agg_linea[l]["hs"] * 60.0) * 100.0)
        if agg_linea[l]["hs"] > 0
        else 0.0
        for l in lineas_ord
    ]

    g_efic = _crear_grafico_barras("% EFICIENCIA POR LÍNEA", lineas_ord, efic_vals, azul_sub)
    g_incid = _crear_grafico_barras("% INCIDENCIA DETENCIONES POR LÍNEA", lineas_ord, incid_vals, colors.HexColor("#d97706"))
    g_repro = _crear_grafico_barras("% REPROCESO POR LÍNEA", lineas_ord, repro_vals, colors.HexColor("#0284c7"))
    g_deco = _crear_grafico_barras("% DECOMISO POR LÍNEA", lineas_ord, deco_vals, colors.HexColor("#dc2626"))

    grid_graficos = Table(
        [
            [g_efic, g_incid],
            [g_repro, g_deco],
        ],
        colWidths=[140 * mm, 140 * mm],
    )
    grid_graficos.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (0, 0), 0.5, borde),
                ("BOX", (1, 0), (1, 0), 0.5, borde),
                ("BOX", (0, 1), (0, 1), 0.5, borde),
                ("BOX", (1, 1), (1, 1), 0.5, borde),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elementos.append(grid_graficos)

    doc.build(elementos)
    buffer.seek(0)
    return buffer
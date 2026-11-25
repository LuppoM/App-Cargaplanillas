from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


DETENCIONES_MAP = [
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


def _calcular_metricas_fila(
    reg: Dict[str, Any],
    teoricos: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    hs_trab = float(reg.get("horas_trabajadas") or 0)
    cantidad = float(reg.get("kg_cajas_reales") or 0)
    peso_prom = float(reg.get("peso_promedio_unid_kg") or 0)
    decomiso = float(reg.get("decomiso_kg") or 0)
    reproceso = float(reg.get("reproceso_kg") or 0)
    scrap = float(reg.get("scrap_flex_kg") or 0)

    dot_teorica = float(reg.get("dotacion_teorica") or 0)
    dot_real_raw = reg.get("dotacion_real")
    dot_real = (
        float(dot_real_raw)
        if dot_real_raw is not None and str(dot_real_raw).strip() != ""
        else dot_teorica
    )

    teorico = _buscar_teorico(teoricos, reg.get("codigo"), reg.get("centro_trabajo"))
    descripcion = ""
    kg_reales = cantidad
    kg_teorico = 0.0

    if teorico:
        descripcion = str(teorico.get("descripcion") or "").strip()
        uxb = float(teorico.get("uxb") or 0)
        peso = peso_prom if peso_prom > 0 else float(teorico.get("peso") or 0)
        bultos_hora = float(teorico.get("bultos_hora") or 0)

        peso_caja = uxb * peso
        if peso_caja > 0 and uxb > 1:
            kg_reales = cantidad * peso_caja

        kg_teorico = uxb * peso * bultos_hora * hs_trab
        if dot_teorica > 0 and dot_real > 0:
            kg_teorico = kg_teorico * (dot_real / dot_teorica)

    deten_min = sum(float(reg.get(col) or 0) for col, _ in DETENCIONES_MAP)
    hs_deten = deten_min / 60.0

    efic_pct = (kg_reales / kg_teorico * 100.0) if kg_teorico > 0 else 0.0
    deco_pct = (decomiso / kg_reales * 100.0) if kg_reales > 0 else 0.0
    repro_pct = (reproceso / kg_reales * 100.0) if kg_reales > 0 else 0.0
    scrap_pct = (scrap / kg_reales * 100.0) if kg_reales > 0 else 0.0
    incid_pct = (hs_deten / hs_trab * 100.0) if hs_trab > 0 else 0.0
    rend_pct = efic_pct + deco_pct + repro_pct + scrap_pct + incid_pct

    return {
        "descripcion": descripcion,
        "hs_trab": hs_trab,
        "kg_reales": kg_reales,
        "kg_teorico": kg_teorico,
        "efic_pct": efic_pct,
        "decomiso": decomiso,
        "deco_pct": deco_pct,
        "reproceso": reproceso,
        "repro_pct": repro_pct,
        "scrap": scrap,
        "scrap_pct": scrap_pct,
        "deten_min": deten_min,
        "hs_deten": hs_deten,
        "incid_pct": incid_pct,
        "dot_real": dot_real,
        "rend_pct": rend_pct,
    }


def _obtener_logo() -> Optional[Image]:
    rutas_posibles = [
        os.path.join("static", "logo.png"),
        os.path.join("static", "palmesano.png"),
        os.path.join("static", "icono.png"),
    ]
    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            try:
                img = Image(ruta, width=28 * mm, height=13 * mm)
                img.hAlign = "LEFT"
                return img
            except Exception:
                pass
    return None


def generar_pdf_informe_planillas(
    registros: List[Dict[str, Any]],
    fecha_desde: str,
    fecha_hasta: str,
    planta: Optional[str] = None,
    teoricos: Optional[List[Dict[str, Any]]] = None,
) -> BytesIO:
    buffer = BytesIO()

    # Ancho útil en A4 Apaisado con márgenes de 10 mm: 297 - 20 = 277 mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Informe Diario de Producción - Palmesano",
    )

    azul_oscuro = colors.HexColor("#1b365d")
    azul_medio = colors.HexColor("#2c5282")
    gris_subtotal = colors.HexColor("#e2e8f0")
    gris_zebra = colors.HexColor("#f8fafc")
    borde_suave = colors.HexColor("#cbd5e1")

    estilos = getSampleStyleSheet()
    st_empresa = ParagraphStyle(
        "Empresa",
        parent=estilos["Normal"],
        fontSize=12,
        leading=14,
        fontName="Helvetica-Bold",
        textColor=azul_oscuro,
    )
    st_titulo = ParagraphStyle(
        "TituloDoc",
        parent=estilos["Heading1"],
        fontSize=14,
        leading=17,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=2,
    )
    st_meta = ParagraphStyle(
        "MetaDoc",
        parent=estilos["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    st_celda = ParagraphStyle(
        "CeldaTabla",
        parent=estilos["Normal"],
        fontSize=7.2,
        leading=8.8,
        textColor=colors.HexColor("#1e293b"),
    )
    st_celda_bold = ParagraphStyle(
        "CeldaTablaBold",
        parent=st_celda,
        fontName="Helvetica-Bold",
    )
    st_seccion = ParagraphStyle(
        "Seccion",
        parent=estilos["Heading2"],
        fontSize=9.5,
        leading=12,
        fontName="Helvetica-Bold",
        textColor=azul_oscuro,
        spaceBefore=4,
        spaceAfter=3,
    )

    planta_txt = planta.strip().upper() if planta and planta.strip() else "TODAS LAS PLANTAS"
    f_desde_txt = _fmt_fecha(fecha_desde)
    f_hasta_txt = _fmt_fecha(fecha_hasta)
    periodo_txt = f_desde_txt if f_desde_txt == f_hasta_txt else f"{f_desde_txt} al {f_hasta_txt}"

    # Procesar filas y acumular totales
    filas_calc: List[Dict[str, Any]] = []
    por_sector: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    detenciones_por_taller: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"minutos": 0.0, "obs": []}
    )

    tot_hs = 0.0
    tot_kg_real = 0.0
    tot_kg_teor = 0.0
    tot_deco = 0.0
    tot_repro = 0.0
    tot_scrap = 0.0
    tot_deten_min = 0.0

    for r in registros:
        m = _calcular_metricas_fila(r, teoricos)
        item = {**r, "_m": m}
        filas_calc.append(item)

        sector = str(r.get("centro_trabajo") or "Sin Sector").strip()
        por_sector[sector].append(item)

        tot_hs += m["hs_trab"]
        tot_kg_real += m["kg_reales"]
        tot_kg_teor += m["kg_teorico"]
        tot_deco += m["decomiso"]
        tot_repro += m["reproceso"]
        tot_scrap += m["scrap"]
        tot_deten_min += m["deten_min"]

        # Acumular detenciones por taller
        obs_por_taller_fila: Dict[str, str] = {}
        if isinstance(r.get("detenciones"), list):
            for d in r["detenciones"]:
                t_nom = str(d.get("taller") or "").strip().lower()
                obs_txt = str(d.get("descripcion") or "").strip()
                if t_nom and obs_txt:
                    obs_por_taller_fila[t_nom] = obs_txt

        for col, nombre_taller in DETENCIONES_MAP:
            mins = float(r.get(col) or 0)
            if mins > 0:
                detenciones_por_taller[nombre_taller]["minutos"] += mins
                obs_encontrada = obs_por_taller_fila.get(nombre_taller.lower(), "")
                if obs_encontrada:
                    etiqueta = f"[{_fmt_fecha(r.get('fecha'))} - {sector}]: {obs_encontrada}"
                    if etiqueta not in detenciones_por_taller[nombre_taller]["obs"]:
                        detenciones_por_taller[nombre_taller]["obs"].append(etiqueta)

    efic_global = (tot_kg_real / tot_kg_teor * 100.0) if tot_kg_teor > 0 else 0.0
    deco_global = (tot_deco / tot_kg_real * 100.0) if tot_kg_real > 0 else 0.0
    repro_global = (tot_repro / tot_kg_real * 100.0) if tot_kg_real > 0 else 0.0
    scrap_global = (tot_scrap / tot_kg_real * 100.0) if tot_kg_real > 0 else 0.0
    incid_global = ((tot_deten_min / 60.0) / tot_hs * 100.0) if tot_hs > 0 else 0.0
    rend_global = efic_global + deco_global + repro_global + scrap_global + incid_global

    elementos: List[Any] = []

    # ---------------------------------------------------------
    # 1. CABECERA GERENCIAL (IZQUIERDA: TÍTULO / DERECHA: KPIs)
    # ---------------------------------------------------------
    logo = _obtener_logo()
    bloque_izq_items = []
    if logo:
        bloque_izq_items.append(logo)
    else:
        bloque_izq_items.append(Paragraph("PALMESANO · GOLOSINAS O.E.N.P. S.A.", st_empresa))

    bloque_izq_items.append(Paragraph("INFORME DIARIO DE PRODUCCIÓN", st_titulo))
    bloque_izq_items.append(
        Paragraph(
            f"<b>Planta:</b> {planta_txt} &nbsp;|&nbsp; "
            f"<b>Período:</b> {periodo_txt} &nbsp;|&nbsp; "
            f"<b>Emitido:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            st_meta,
        )
    )

    tabla_kpi_header = Table(
        [
            ["RESUMEN GENERAL DEL PERÍODO", "", "", ""],
            ["EFIC. REAL %", f"{_fmt_num(efic_global, 1)}%", "INCIDENCIA %", f"{_fmt_num(incid_global, 1)}%"],
            ["RENDIMIENTO %", f"{_fmt_num(rend_global, 1)}%", "DETENCIONES", f"{_fmt_num(tot_deten_min, 0)} min ({_fmt_num(tot_deten_min/60, 1)} hs)"],
            ["DECOMISO %", f"{_fmt_num(deco_global, 2)}%", "REPROCESO %", f"{_fmt_num(repro_global, 2)}%"],
            ["SCRAP FLEX %", f"{_fmt_num(scrap_global, 2)}%", "KG PRODUCIDOS", f"{_fmt_num(tot_kg_real, 1)} kg"],
        ],
        colWidths=[28 * mm, 24 * mm, 28 * mm, 37 * mm],
    )
    tabla_kpi_header.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (3, 0)),
                ("BACKGROUND", (0, 0), (3, 0), azul_oscuro),
                ("TEXTCOLOR", (0, 0), (3, 0), colors.white),
                ("FONTNAME", (0, 0), (3, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (3, 0), 8),
                ("ALIGN", (0, 0), (3, 0), "CENTER"),
                ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f1f5f9")),
                ("BACKGROUND", (2, 1), (2, -1), colors.HexColor("#f1f5f9")),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 1), (2, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
                ("FONTNAME", (3, 1), (3, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, -1), 7.5),
                ("TEXTCOLOR", (1, 1), (1, 2), colors.HexColor("#166534")),
                ("TEXTCOLOR", (3, 1), (3, 1), colors.HexColor("#b45309")),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("GRID", (0, 0), (-1, -1), 0.5, borde_suave),
            ]
        )
    )

    cabecera = Table(
        [[bloque_izq_items, tabla_kpi_header]],
        colWidths=[158 * mm, 119 * mm],
    )
    cabecera.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos.append(cabecera)
    elementos.append(Spacer(1, 3 * mm))

    # ---------------------------------------------------------
    # 2. TABLA PRINCIPAL AGRUPADA POR SECTOR CON SUBTOTALES
    # ---------------------------------------------------------
    elementos.append(Paragraph("1. Detalle de Producción e Indicadores por Sector", st_seccion))

    # Suma de anchos = 277 mm
    anchos_tabla = [
        18 * mm,  # Fecha
        34 * mm,  # Sector
        59 * mm,  # Producto
        14 * mm,  # Turno
        13 * mm,  # Hs
        21 * mm,  # Kg Real
        21 * mm,  # Kg Teor
        16 * mm,  # Efic %
        14 * mm,  # Dec %
        14 * mm,  # Rep %
        14 * mm,  # Scrap %
        14 * mm,  # Incid %
        10 * mm,  # Dot
        15 * mm,  # Rend %
    ]

    filas_tabla = [
        [
            "Fecha",
            "Sector",
            "Producto",
            "Turno",
            "Hs",
            "Kg Real",
            "Kg Teór.",
            "Efic %",
            "Dec %",
            "Rep %",
            "Scr %",
            "Inc %",
            "Dot",
            "Rend %",
        ]
    ]

    estilos_dinamicos = [
        ("BACKGROUND", (0, 0), (-1, 0), azul_oscuro),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.3),
        ("ALIGN", (0, 0), (3, -1), "LEFT"),
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (12, 0), (12, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 1), (-1, -1), 7.2),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, borde_suave),
    ]

    if not filas_calc:
        filas_tabla.append(
            ["-", "-", "Sin registros cargados para el período seleccionado", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-"]
        )
    else:
        fila_idx = 1
        for sector in sorted(por_sector.keys(), key=lambda x: x.lower()):
            items_sector = sorted(
                por_sector[sector],
                key=lambda x: (str(x.get("fecha") or ""), str(x.get("turno") or "")),
            )

            s_hs = 0.0
            s_kg_real = 0.0
            s_kg_teor = 0.0
            s_deco = 0.0
            s_repro = 0.0
            s_scrap = 0.0
            s_deten_min = 0.0

            for idx_item, it in enumerate(items_sector):
                m = it["_m"]
                s_hs += m["hs_trab"]
                s_kg_real += m["kg_reales"]
                s_kg_teor += m["kg_teorico"]
                s_deco += m["decomiso"]
                s_repro += m["reproceso"]
                s_scrap += m["scrap"]
                s_deten_min += m["deten_min"]

                cod = str(it.get("codigo") or "").strip()
                desc = m["descripcion"]
                prod_txt = f"<b>{cod}</b> - {desc}" if desc else f"<b>{cod}</b>"

                filas_tabla.append(
                    [
                        _fmt_fecha(it.get("fecha")),
                        Paragraph(sector, st_celda),
                        Paragraph(prod_txt, st_celda),
                        str(it.get("turno") or "")[:3],
                        _fmt_num(m["hs_trab"], 1),
                        _fmt_num(m["kg_reales"], 1),
                        _fmt_num(m["kg_teorico"], 1),
                        f"{_fmt_num(m['efic_pct'], 1)}%",
                        f"{_fmt_num(m['deco_pct'], 2)}%",
                        f"{_fmt_num(m['repro_pct'], 2)}%",
                        f"{_fmt_num(m['scrap_pct'], 2)}%",
                        f"{_fmt_num(m['incid_pct'], 1)}%",
                        _fmt_num(m["dot_real"], 0),
                        f"{_fmt_num(m['rend_pct'], 1)}%",
                    ]
                )
                if idx_item % 2 == 1:
                    estilos_dinamicos.append(
                        ("BACKGROUND", (0, fila_idx), (-1, fila_idx), gris_zebra)
                    )
                fila_idx += 1

            # Fila Subtotal del Sector
            s_efic = (s_kg_real / s_kg_teor * 100.0) if s_kg_teor > 0 else 0.0
            s_dec_p = (s_deco / s_kg_real * 100.0) if s_kg_real > 0 else 0.0
            s_rep_p = (s_repro / s_kg_real * 100.0) if s_kg_real > 0 else 0.0
            s_scr_p = (s_scrap / s_kg_real * 100.0) if s_kg_real > 0 else 0.0
            s_inc_p = ((s_deten_min / 60.0) / s_hs * 100.0) if s_hs > 0 else 0.0
            s_ren_p = s_efic + s_dec_p + s_rep_p + s_scr_p + s_inc_p

            filas_tabla.append(
                [
                    "",
                    Paragraph(f"<b>Subtotal {sector}</b>", st_celda_bold),
                    f"{len(items_sector)} parte/s",
                    "",
                    _fmt_num(s_hs, 1),
                    _fmt_num(s_kg_real, 1),
                    _fmt_num(s_kg_teor, 1),
                    f"{_fmt_num(s_efic, 1)}%",
                    f"{_fmt_num(s_dec_p, 2)}%",
                    f"{_fmt_num(s_rep_p, 2)}%",
                    f"{_fmt_num(s_scr_p, 2)}%",
                    f"{_fmt_num(s_inc_p, 1)}%",
                    "-",
                    f"{_fmt_num(s_ren_p, 1)}%",
                ]
            )
            estilos_dinamicos.extend(
                [
                    ("BACKGROUND", (0, fila_idx), (-1, fila_idx), gris_subtotal),
                    ("FONTNAME", (0, fila_idx), (-1, fila_idx), "Helvetica-Bold"),
                ]
            )
            fila_idx += 1

        # Fila Total General
        filas_tabla.append(
            [
                "",
                "TOTAL GENERAL",
                f"{len(filas_calc)} registros",
                "",
                _fmt_num(tot_hs, 1),
                _fmt_num(tot_kg_real, 1),
                _fmt_num(tot_kg_teor, 1),
                f"{_fmt_num(efic_global, 1)}%",
                f"{_fmt_num(deco_global, 2)}%",
                f"{_fmt_num(repro_global, 2)}%",
                f"{_fmt_num(scrap_global, 2)}%",
                f"{_fmt_num(incid_global, 1)}%",
                "-",
                f"{_fmt_num(rend_global, 1)}%",
            ]
        )
        estilos_dinamicos.extend(
            [
                ("BACKGROUND", (0, fila_idx), (-1, fila_idx), azul_medio),
                ("TEXTCOLOR", (0, fila_idx), (-1, fila_idx), colors.white),
                ("FONTNAME", (0, fila_idx), (-1, fila_idx), "Helvetica-Bold"),
            ]
        )

    tabla_principal = Table(filas_tabla, colWidths=anchos_tabla, repeatRows=1)
    tabla_principal.setStyle(TableStyle(estilos_dinamicos))
    elementos.append(tabla_principal)
    elementos.append(Spacer(1, 5 * mm))

    # ---------------------------------------------------------
    # 3. RESUMEN DE DETENCIONES Y OBSERVACIONES DEL PERÍODO
    # ---------------------------------------------------------
    elementos.append(Paragraph("2. Resumen de Detenciones por Taller / Motivo", st_seccion))

    filas_deten = [
        [
            "Taller / Motivo",
            "Minutos",
            "Horas",
            "% Incidencia s/Hs Trab.",
            "Observaciones Registradas",
        ]
    ]

    if detenciones_por_taller:
        for taller, info in sorted(
            detenciones_por_taller.items(), key=lambda kv: kv[1]["minutos"], reverse=True
        ):
            mins = info["minutos"]
            hs_d = mins / 60.0
            pct_inc = (hs_d / tot_hs * 100.0) if tot_hs > 0 else 0.0
            obs_unidas = " | ".join(info["obs"]) if info["obs"] else "-"
            filas_deten.append(
                [
                    Paragraph(f"<b>{taller}</b>", st_celda_bold),
                    f"{_fmt_num(mins, 0)} min",
                    f"{_fmt_num(hs_d, 2)} hs",
                    f"{_fmt_num(pct_inc, 2)}%",
                    Paragraph(obs_unidas, st_celda),
                ]
            )

        filas_deten.append(
            [
                "TOTAL DETENCIONES",
                f"{_fmt_num(tot_deten_min, 0)} min",
                f"{_fmt_num(tot_deten_min / 60.0, 2)} hs",
                f"{_fmt_num(incid_global, 2)}%",
                "",
            ]
        )
    else:
        filas_deten.append(["-", "0 min", "0,00 hs", "0,00%", "No se registraron detenciones en el período."])

    tabla_deten = Table(
        filas_deten,
        colWidths=[42 * mm, 24 * mm, 24 * mm, 35 * mm, 152 * mm],
        repeatRows=1,
    )
    tabla_deten.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), azul_oscuro),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (3, -1), "RIGHT"),
                ("ALIGN", (4, 0), (4, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 1), (-1, -1), 7.3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, gris_zebra]),
                ("BACKGROUND", (0, -1), (-1, -1), gris_subtotal),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.4, borde_suave),
            ]
        )
    )
    elementos.append(tabla_deten)

    doc.build(elementos)
    buffer.seek(0)
    return buffer
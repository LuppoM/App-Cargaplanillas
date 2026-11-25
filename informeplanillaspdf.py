from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

DETENCIONES_INFO = [
    ("detencion_mecanico", "Mecánico", 1, "Detención de la producción causada por fallas mecánicas o necesidad de ajustes en los equipos."),
    ("detencion_electrico", "Eléctrico", 2, "Parada provocada por problemas eléctricos o electrónicos en los equipos."),
    ("detencion_produccion", "Producción", 3, "Interrupción debida a errores operativos, relevos o fallas en la ejecución de tareas."),
    ("detencion_programacion", "Programación", 4, "Detención para realizar cambios de producto, set-up o ajustes de parámetros."),
    ("detencion_calidad", "Calidad", 5, "Parada causada por detección de productos, insumos o procesos fuera de estándar."),
    ("detencion_limpieza", "Limpieza", 6, "Tiempo destinado a limpiar y preparar la línea o área de trabajo."),
    ("detencion_desarrollo", "Desarrollo", 7, "Detención provocada por falta de información técnica o recetas incompletas."),
    ("detencion_abastecimiento", "Abastecimiento", 8, "Parada causada por falta de materia prima o insumos necesarios."),
    ("detencion_suministro", "Suministro", 9, "Detención debido a fallas en servicios esenciales (energía, agua, aire comprimido, vapor)."),
    ("detencion_alistamiento", "Alistamiento", 10, "Parada para preparar la línea o equipos antes del arranque de producción."),
    ("detencion_rrhh", "RRHH", 11, "Interrupción de la producción por actividades del personal, capacitaciones o reuniones."),
    ("detencion_refrigerio", "Refrigerio", 12, "Tiempo destinado a refrigerio del personal."),
]

ORDEN_COLS_TABLA_DETEN = [
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


def _parse_fecha_dt(fecha_val: Any) -> Any:
    s = str(fecha_val or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
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


def generar_pdf_informe_planillas(
    registros: List[Dict[str, Any]],
    fecha_desde: str,
    fecha_hasta: str,
    planta: Optional[str] = None,
    teoricos: Optional[List[Dict[str, Any]]] = None,
) -> BytesIO:
    wb = openpyxl.Workbook()

    ws_graf = wb.active
    ws_graf.title = "GRAFICOS"
    ws_tabla = wb.create_sheet(title="TABLA")
    ws_deten = wb.create_sheet(title="DETENCIONES")

    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True, color="0F172A")
    font_regular = Font(name="Calibri", size=10, color="0F172A")
    font_pct_top = Font(name="Calibri", size=9, bold=True, color="1E3A8A")

    fill_header = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    fill_subtotal = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    fill_top_pct = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")

    thin_side = Side(style="thin", color="CBD5E1")
    border_cell = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")

    registros_ord = sorted(
        registros,
        key=lambda r: (
            str(r.get("fecha") or ""),
            str(r.get("turno") or ""),
            str(r.get("centro_trabajo") or ""),
            int(r.get("id") or 0),
        ),
    )

    # =========================================================================
    # HOJA: TABLA (43 columnas A..AQ igual a informe diario.xlsx)
    # =========================================================================
    headers_tabla = [
        "Mes",                      # A (1)
        "Fecha",                    # B (2)
        "TURNO",                    # C (3)
        "H/Prog",                   # D (4)
        "Linea",                    # E (5)
        "Familia",                  # F (6)
        "Marca",                    # G (7)
        "TIPO",                     # H (8)
        "Codigo",                   # I (9)
        "Descripcion del Producto", # J (10)
        "Produccion BU",            # K (11)
        "KG/ T",                    # L (12)
        "Produccion KG",            # M (13)
        "% Eficiencia",             # N (14)
        "Reproceso KG",             # O (15)
        "% Reproceso",              # P (16)
        "Decomiso KG",              # Q (17)
        "% Decomiso",               # R (18)
        "Peso Promedio",            # S (19)
        "KG Desvio Peso",           # T (20)
        "% Desvio",                 # U (21)
        "Scrap KG",                 # V (22)
        "CT de Flex KG",            # W (23)
        "% Scrap",                  # X (24)
        "Producción",               # Y (25)
        "Refrigerio",               # Z (26)
        "Mecánico",                 # AA (27)
        "Eléctrico",                # AB (28)
        "Calidad",                  # AC (29)
        "Programación",             # AD (30)
        "Limpieza",                 # AE (31)
        "Abastecimiento",           # AF (32)
        "Desarrollo",               # AG (33)
        "Alistamiento",             # AH (34)
        "RRHH",                     # AI (35)
        "Suministro",               # AJ (36)
        "Total Deten",              # AK (37)
        "% In",                     # AL (38)
        "HH x HR",                  # AM (39)
        "HH x FI",                  # AN (40)
        "Dotación Real",            # AO (41)
        "Nº DE REGISTRO",           # AP (42)
        "% RENDIMIENTO",            # AQ (43)
    ]

    for col_idx, titulo in enumerate(headers_tabla, start=1):
        cell = ws_tabla.cell(row=3, column=col_idx, value=titulo)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = border_cell
    ws_tabla.row_dimensions[3].height = 26

    start_row = 4
    for idx, reg in enumerate(registros_ord):
        r = start_row + idx
        fecha_dt = _parse_fecha_dt(reg.get("fecha"))
        hs_prog = float(reg.get("horas_trabajadas") or 0)
        linea = str(reg.get("centro_trabajo") or "").strip()
        familia = str(reg.get("planta") or "").strip().capitalize()
        codigo_raw = str(reg.get("codigo") or "").strip()
        codigo_val: Any = int(codigo_raw) if codigo_raw.isdigit() else codigo_raw

        prod_bu = float(reg.get("kg_cajas_reales") or 0)
        repro_kg = float(reg.get("reproceso_kg") or 0)
        deco_kg = float(reg.get("decomiso_kg") or 0)
        peso_prom = float(reg.get("peso_promedio_unid_kg") or 0)
        scrap_kg = float(reg.get("scrap_flex_kg") or 0)

        dot_teor = float(reg.get("dotacion_teorica") or 0)
        dot_real_raw = reg.get("dotacion_real")
        dot_real = (
            float(dot_real_raw)
            if dot_real_raw is not None and str(dot_real_raw).strip() != ""
            else dot_teor
        )

        teorico = _buscar_teorico(teoricos, codigo_raw, linea)
        descripcion = ""
        marca = "Palmesano"
        tipo = "SE"
        kg_teorico = 0.0
        prod_kg = prod_bu
        desvio_peso: Any = "N/D"
        ct_flex = 0.0

        if teorico:
            descripcion = str(teorico.get("descripcion") or "").strip()
            marca = str(teorico.get("marca") or "Palmesano").strip()
            uxb = float(teorico.get("uxb") or 0)
            peso_t = float(teorico.get("peso") or 0)
            bultos_h = float(teorico.get("bultos_hora") or 0)
            tipo = str(teorico.get("tipo") or ("PT" if uxb > 1 else "SE")).strip()

            peso_ef = peso_prom if peso_prom > 0 else peso_t
            if uxb > 1 and (uxb * peso_ef) > 0:
                prod_kg = prod_bu * uxb * peso_ef

            kg_teorico = uxb * peso_t * bultos_h * hs_prog
            if dot_teor > 0 and dot_real > 0:
                kg_teorico = kg_teorico * (dot_real / dot_teor)

            if peso_prom > 0 and peso_t > 0 and uxb > 1:
                desvio_peso = round((peso_prom - peso_t) * uxb * prod_bu, 4)

            ct_unit = float(teorico.get("ct_flex") or teorico.get("consumo_flex") or 0)
            if ct_unit > 0:
                ct_flex = round(ct_unit * prod_bu, 4)

        deten_vals = [float(reg.get(col_name) or 0) for col_name in ORDEN_COLS_TABLA_DETEN]

        row_values = [
            f"=MONTH(B{r})" if isinstance(fecha_dt, datetime) else "",  # A: Mes
            fecha_dt,                                                     # B: Fecha
            str(reg.get("turno") or ""),                                  # C: TURNO
            hs_prog,                                                      # D: H/Prog
            linea,                                                        # E: Linea
            familia,                                                      # F: Familia
            marca,                                                        # G: Marca
            tipo,                                                         # H: TIPO
            codigo_val,                                                   # I: Codigo
            descripcion,                                                  # J: Descripcion
            prod_bu,                                                      # K: Produccion BU
            round(kg_teorico, 3),                                         # L: KG/ T
            round(prod_kg, 3),                                            # M: Produccion KG
            f"=IF(L{r}>0, M{r}/L{r}, 0)",                                # N: % Eficiencia
            repro_kg,                                                     # O: Reproceso KG
            f"=IF((O{r}+M{r})>0, O{r}/(O{r}+M{r}), 0)",                   # P: % Reproceso
            deco_kg,                                                      # Q: Decomiso KG
            f"=IF((Q{r}+M{r})>0, Q{r}/(Q{r}+M{r}), 0)",                   # R: % Decomiso
            peso_prom if peso_prom > 0 else "N/D",                        # S: Peso Promedio
            desvio_peso,                                                  # T: KG Desvio Peso
            f'=IF(ISNUMBER(T{r}), IF(M{r}>0, T{r}/M{r}, 0), 0)',          # U: % Desvio
            scrap_kg,                                                     # V: Scrap KG
            ct_flex,                                                      # W: CT de Flex KG
            f"=IF((V{r}+W{r})>0, V{r}/(V{r}+W{r}), 0)",                   # X: % Scrap
            *deten_vals,                                                  # Y..AJ: 12 detenciones
            f"=SUM(Y{r}:AJ{r})",                                          # AK: Total Deten
            f"=IF(D{r}>0, AK{r}/(D{r}*60), 0)",                           # AL: % In
            round(hs_prog * dot_real, 2),                                 # AM: HH x HR
            round(hs_prog * dot_teor, 2),                                 # AN: HH x FI
            dot_real,                                                     # AO: Dotación Real
            reg.get("id") or "",                                          # AP: Nº DE REGISTRO
            f"=N{r}+P{r}+R{r}+AL{r}",                                     # AQ: % RENDIMIENTO
        ]

        for col_idx, val in enumerate(row_values, start=1):
            c = ws_tabla.cell(row=r, column=col_idx, value=val)
            c.font = font_regular
            c.border = border_cell

            if col_idx == 2 and isinstance(val, datetime):
                c.number_format = "dd/mm/yyyy"
                c.alignment = align_center
            elif col_idx in (1, 3, 8, 9, 42):
                c.alignment = align_center
            elif col_idx in (5, 6, 7, 10):
                c.alignment = align_left
            elif col_idx in (14, 16, 18, 21, 24, 38, 43):
                c.number_format = "0.0%"
                c.alignment = align_right
            elif col_idx == 19:
                c.number_format = "0.0000" if isinstance(val, (int, float)) else "@"
                c.alignment = align_right
            else:
                c.number_format = "#,##0.00" if col_idx in (4, 11, 12, 13, 15, 17, 20, 22, 23, 39, 40) else "#,##0"
                c.alignment = align_right

    end_row = max(start_row, start_row + len(registros_ord) - 1)

    # Fila 2: Subtotales dinámicos
    ws_tabla.cell(row=2, column=4, value=f"=SUBTOTAL(9,D{start_row}:D{end_row})*60").number_format = "#,##0"
    for col_sum in (11, 12, 13, 15, 17, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 39, 40):
        col_let = get_column_letter(col_sum)
        cell_s = ws_tabla.cell(row=2, column=col_sum, value=f"=SUBTOTAL(9,{col_let}{start_row}:{col_let}{end_row})")
        cell_s.number_format = "#,##0.0" if col_sum in (11, 12, 13, 15, 17, 22, 23, 39, 40) else "#,##0"

    ws_tabla.cell(row=2, column=14, value="=IF(L2>0, M2/L2, 0)").number_format = "0.0%"
    ws_tabla.cell(row=2, column=16, value="=IF((O2+M2)>0, O2/(O2+M2), 0)").number_format = "0.00%"
    ws_tabla.cell(row=2, column=18, value="=IF((Q2+M2)>0, Q2/(Q2+M2), 0)").number_format = "0.00%"
    ws_tabla.cell(row=2, column=24, value="=IF((V2+W2)>0, V2/(V2+W2), 0)").number_format = "0.00%"
    ws_tabla.cell(row=2, column=38, value="=IF(D2>0, AK2/D2, 0)").number_format = "0.0%"
    ws_tabla.cell(row=2, column=41, value=f"=SUBTOTAL(9,AO{start_row}:AO{end_row})").number_format = "#,##0"

    for col_idx in range(1, 44):
        c2 = ws_tabla.cell(row=2, column=col_idx)
        c2.font = font_bold
        c2.fill = fill_subtotal
        c2.border = border_cell

    # Fila 1: Fecha y % de incidencia por rubro (cols Y..AK) + Kg/HH (AM..AO)
    ws_tabla.cell(row=1, column=2, value=_parse_fecha_dt(fecha_desde))
    if isinstance(ws_tabla.cell(row=1, column=2).value, datetime):
        ws_tabla.cell(row=1, column=2).number_format = "dd/mm/yyyy"
    ws_tabla.cell(row=1, column=2).font = font_bold

    for col_det in range(25, 38):
        col_let = get_column_letter(col_det)
        c1 = ws_tabla.cell(row=1, column=col_det, value=f"=IF($D$2>0, {col_let}2/$D$2, 0)")
        c1.number_format = "0.00%"
        c1.font = font_pct_top
        c1.fill = fill_top_pct
        c1.alignment = align_right
        c1.border = border_cell

    ws_tabla.cell(row=1, column=39, value="=IF(AM2>0, M2/AM2, 0)").number_format = "#,##0.00"
    ws_tabla.cell(row=1, column=40, value="=IF(AN2>0, M2/AN2, 0)").number_format = "#,##0.00"
    ws_tabla.cell(row=1, column=41, value="Total dotacion")
    for c_hh in (39, 40, 41):
        ws_tabla.cell(row=1, column=c_hh).font = font_bold
        ws_tabla.cell(row=1, column=c_hh).fill = fill_top_pct

    if registros_ord:
        tab = Table(displayName="TablaProduccion", ref=f"A3:AQ{end_row}")
        style = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        tab.tableStyleInfo = style
        ws_tabla.add_table(tab)

    ws_tabla.freeze_panes = "F4"

    anchos_tabla = {
        1: 6, 2: 12, 3: 10, 4: 9, 5: 22, 6: 13, 7: 13, 8: 7, 9: 12, 10: 38,
        11: 14, 12: 14, 13: 14, 14: 12, 15: 13, 16: 12, 17: 13, 18: 11,
        19: 13, 20: 14, 21: 10, 22: 11, 23: 13, 24: 10,
    }
    for col_i in range(1, 44):
        col_l = get_column_letter(col_i)
        ws_tabla.column_dimensions[col_l].width = anchos_tabla.get(col_i, 13)

    # =========================================================================
    # HOJA: DETENCIONES (Catálogo arriba + Registros detallados abajo)
    # =========================================================================
    ws_deten.cell(row=1, column=1, value="ID").font = font_header
    ws_deten.cell(row=1, column=1).fill = fill_header
    ws_deten.cell(row=1, column=1).alignment = align_center
    ws_deten.cell(row=1, column=2, value="Descripción").font = font_header
    ws_deten.cell(row=1, column=2).fill = fill_header
    ws_deten.cell(row=1, column=2).alignment = align_left

    for idx_cat, (_, _, id_t, desc_t) in enumerate(
        sorted(DETENCIONES_INFO, key=lambda x: x[2]), start=2
    ):
        c_id = ws_deten.cell(row=idx_cat, column=1, value=id_t)
        c_desc = ws_deten.cell(row=idx_cat, column=2, value=desc_t)
        c_id.alignment = align_center
        c_id.font = font_bold
        c_desc.font = font_regular
        c_id.border = border_cell
        c_desc.border = border_cell

    row_hdr_det = 16
    headers_det = ["Nº de registro", "Centro de trabajo", "taller", "Minutos", "Descripción detención"]
    for c_i, h_txt in enumerate(headers_det, start=1):
        c = ws_deten.cell(row=row_hdr_det, column=c_i, value=h_txt)
        c.font = font_header
        c.fill = fill_header
        c.alignment = align_center
        c.border = border_cell

    curr_det_row = row_hdr_det + 1
    for reg in registros_ord:
        reg_id = reg.get("id") or ""
        centro = str(reg.get("centro_trabajo") or "").strip()

        obs_por_taller: Dict[str, str] = {}
        if isinstance(reg.get("detenciones"), list):
            for d in reg["detenciones"]:
                t_nom = str(d.get("taller") or "").strip().lower()
                obs_txt = str(d.get("descripcion") or "").strip()
                if t_nom:
                    obs_por_taller[t_nom] = obs_txt

        for col_key, nombre_t, id_t, _ in DETENCIONES_INFO:
            mins = float(reg.get(col_key) or 0)
            if mins > 0:
                obs_final = obs_por_taller.get(nombre_t.lower(), "") or nombre_t.upper()
                vals_d = [reg_id, centro, id_t, mins, obs_final]
                for c_i, v_d in enumerate(vals_d, start=1):
                    cell_d = ws_deten.cell(row=curr_det_row, column=c_i, value=v_d)
                    cell_d.font = font_regular
                    cell_d.border = border_cell
                    cell_d.alignment = align_center if c_i in (1, 3) else (align_right if c_i == 4 else align_left)
                curr_det_row += 1

    ws_deten.column_dimensions["A"].width = 16
    ws_deten.column_dimensions["B"].width = 28
    ws_deten.column_dimensions["C"].width = 12
    ws_deten.column_dimensions["D"].width = 12
    ws_deten.column_dimensions["E"].width = 75

    # =========================================================================
    # HOJA: GRAFICOS (Resumen por Línea + Gráficos nativos de Excel)
    # =========================================================================
    planta_lbl = planta.strip().upper() if planta and planta.strip() else "TODAS LAS PLANTAS"
    ws_graf["A1"] = f"INFORME DIARIO DE PRODUCCIÓN · {planta_lbl}"
    ws_graf["A1"].font = Font(name="Calibri", size=14, bold=True, color="1B365D")
    ws_graf["A2"] = f"Período: {fecha_desde} al {fecha_hasta} | Registros: {len(registros_ord)}"
    ws_graf["A2"].font = Font(name="Calibri", size=10, italic=True, color="475569")

    resumen_lineas: Dict[str, Dict[str, float]] = {}
    for r_idx in range(start_row, start_row + len(registros_ord)):
        ln = str(ws_tabla.cell(row=r_idx, column=5).value or "Sin Línea")
        hs = float(ws_tabla.cell(row=r_idx, column=4).value or 0)
        kg_t = float(ws_tabla.cell(row=r_idx, column=12).value or 0)
        kg_p = float(ws_tabla.cell(row=r_idx, column=13).value or 0)
        rep = float(ws_tabla.cell(row=r_idx, column=15).value or 0)
        dec = float(ws_tabla.cell(row=r_idx, column=17).value or 0)
        det_m = sum(float(ws_tabla.cell(row=r_idx, column=c_d).value or 0) for c_d in range(25, 37))

        if ln not in resumen_lineas:
            resumen_lineas[ln] = {"hs": 0.0, "kg_t": 0.0, "kg_p": 0.0, "rep": 0.0, "dec": 0.0, "det": 0.0}
        resumen_lineas[ln]["hs"] += hs
        resumen_lineas[ln]["kg_t"] += kg_t
        resumen_lineas[ln]["kg_p"] += kg_p
        resumen_lineas[ln]["rep"] += rep
        resumen_lineas[ln]["dec"] += dec
        resumen_lineas[ln]["det"] += det_m

    headers_res_g = ["Línea", "Prod. KG", "KG/T", "% EFICIENCIA", "% REPROCESO", "% DECOMISO", "% INCIDENCIA"]
    for c_i, h_g in enumerate(headers_res_g, start=1):
        cg = ws_graf.cell(row=4, column=c_i, value=h_g)
        cg.font = font_header
        cg.fill = fill_header
        cg.alignment = align_center
        cg.border = border_cell

    lineas_ordenadas = sorted(resumen_lineas.keys())
    for idx_l, ln in enumerate(lineas_ordenadas, start=5):
        d = resumen_lineas[ln]
        efic = (d["kg_p"] / d["kg_t"]) if d["kg_t"] > 0 else 0.0
        repro = (d["rep"] / (d["rep"] + d["kg_p"])) if (d["rep"] + d["kg_p"]) > 0 else 0.0
        deco = (d["dec"] / (d["dec"] + d["kg_p"])) if (d["dec"] + d["kg_p"]) > 0 else 0.0
        incid = (d["det"] / (d["hs"] * 60.0)) if d["hs"] > 0 else 0.0

        vals_g = [ln, round(d["kg_p"], 1), round(d["kg_t"], 1), efic, repro, deco, incid]
        for c_i, vg in enumerate(vals_g, start=1):
            cell_g = ws_graf.cell(row=idx_l, column=c_i, value=vg)
            cell_g.font = font_regular
            cell_g.border = border_cell
            if c_i == 1:
                cell_g.alignment = align_left
            elif c_i in (2, 3):
                cell_g.number_format = "#,##0.0"
                cell_g.alignment = align_right
            else:
                cell_g.number_format = "0.0%"
                cell_g.alignment = align_right

    if lineas_ordenadas:
        max_r_graf = 4 + len(lineas_ordenadas)
        cats = Reference(ws_graf, min_col=1, min_row=5, max_row=max_r_graf)

        configs_charts = [
            (4, "% EFICIENCIA POR LÍNEA", "I4"),
            (5, "% REPROCESO POR LÍNEA", "Q4"),
            (6, "% DECOMISO POR LÍNEA", "I20"),
            (7, "% INCIDENCIA DETENCIONES POR LÍNEA", "Q20"),
        ]
        for col_metrica, titulo_c, celda_destino in configs_charts:
            chart = BarChart()
            chart.type = "col"
            chart.style = 10
            chart.title = titulo_c
            chart.y_axis.number_format = "0%"
            chart.legend = None
            chart.width = 14
            chart.height = 7.5
            data_ref = Reference(ws_graf, min_col=col_metrica, min_row=4, max_row=max_r_graf)
            chart.add_data(data_ref, titles_from_data=True)
            chart.set_categories(cats)
            ws_graf.add_chart(chart, celda_destino)

    ws_graf.column_dimensions["A"].width = 24
    for col_g in ("B", "C", "D", "E", "F", "G"):
        ws_graf.column_dimensions[col_g].width = 14

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
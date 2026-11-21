from __future__ import annotations

from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

CONFIG_TANQUES = [
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


def _fmt_kg(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _formatear_fecha(valor) -> str:
    if not valor:
        return "-"
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    texto = str(valor).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(texto[:19], fmt).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return texto


def _calcular_tanque(cfg: dict, det: dict) -> dict:
    val_raw = det.get("valor_medido")
    kg_raw = det.get("kg_manual")

    val = None
    if val_raw is not None and str(val_raw).strip() != "":
        try:
            val = float(val_raw)
        except ValueError:
            val = None

    kg_man = 0.0
    if kg_raw is not None and str(kg_raw).strip() != "":
        try:
            kg_man = float(kg_raw)
        except ValueError:
            kg_man = 0.0

    n_pct = 0.0
    cantidad = 0.0

    if val is not None and cfg["altura"] > 0:
        n_cm = max(0.0, cfg["altura"] - val)
        n_pct = min(100.0, max(0.0, (n_cm / cfg["altura"]) * 100.0))
        cantidad = (cfg["capacidad"] / cfg["altura"]) * n_cm
    elif kg_man > 0 and cfg["capacidad"] > 0:
        n_pct = min(100.0, max(0.0, (kg_man / cfg["capacidad"]) * 100.0))

    total = round(cantidad + kg_man)
    return {
        "pct": round(n_pct),
        "total": total,
        "descripcion": (det.get("descripcion") or "").strip() or "Sin producto",
        "codigo": (det.get("codigo") or "").strip(),
    }


def _envolver_texto(c: canvas.Canvas, texto: str, font_name: str, font_size: int, max_width: float, max_lineas: int = 3) -> list[str]:
    palabras = texto.split()
    lineas = []
    actual = ""

    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if c.stringWidth(prueba, font_name, font_size) <= max_width:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra

    if actual:
        lineas.append(actual)

    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        lineas[-1] = lineas[-1][: max(0, len(lineas[-1]) - 3)] + "..."

    return lineas


def _dibujar_tarjeta_tanque(c: canvas.Canvas, x: float, y_top: float, w: float, h: float, nombre_tk: str, info: dict):
    pct = info["pct"]
    total = info["total"]
    desc = info["descripcion"]
    activo = pct > 0 or total > 0

    # Marco exterior de la tarjeta
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.8)
    c.roundRect(x, y_top - h, w, h, 6, stroke=1, fill=1)

    # Pastilla de porcentaje arriba
    badge_w = 34
    badge_h = 14
    badge_x = x + (w - badge_w) / 2
    badge_y = y_top - 20

    if activo:
        c.setFillColor(colors.HexColor("#FEF3C7"))
        c.setStrokeColor(colors.HexColor("#F59E0B"))
        txt_color = colors.HexColor("#B45309")
    else:
        c.setFillColor(colors.HexColor("#E2E8F0"))
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        txt_color = colors.HexColor("#64748B")

    c.setLineWidth(0.7)
    c.roundRect(badge_x, badge_y, badge_w, badge_h, 7, stroke=1, fill=1)
    c.setFillColor(txt_color)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(x + w / 2, badge_y + 4, f"{pct}%")

    # Cilindro del tanque
    cyl_w = w - 22
    cyl_h = 112
    cyl_x = x + (w - cyl_w) / 2
    cyl_y = badge_y - 8 - cyl_h

    # Fondo vacío del cilindro
    c.setFillColor(colors.HexColor("#E2E8F0"))
    c.setStrokeColor(colors.HexColor("#94A3B8"))
    c.setLineWidth(1.0)
    c.roundRect(cyl_x, cyl_y, cyl_w, cyl_h, 5, stroke=1, fill=1)

    # Franja metálica superior decorativa
    c.setFillColor(colors.HexColor("#CBD5E1"))
    c.rect(cyl_x + 1, cyl_y + cyl_h - 6, cyl_w - 2, 5, stroke=0, fill=1)

    # Relleno de chocolate según porcentaje
    if pct > 0:
        fill_h = max(6.0, (cyl_h - 2) * (pct / 100.0))
        c.setFillColor(colors.HexColor("#4A2511"))
        c.roundRect(cyl_x + 1, cyl_y + 1, cyl_w - 2, fill_h, 4, stroke=0, fill=1)
        # Borde superior del líquido
        c.setStrokeColor(colors.HexColor("#78350F"))
        c.setLineWidth(1.2)
        c.line(cyl_x + 1.5, cyl_y + fill_h, cyl_x + cyl_w - 1.5, cyl_y + fill_h)

    # Etiqueta negra con Kg dentro del tanque si tiene stock
    if total > 0:
        kg_texto = f"{_fmt_kg(total)} kg"
        pill_w = min(cyl_w - 4, c.stringWidth(kg_texto, "Helvetica-Bold", 7) + 8)
        pill_h = 13
        pill_x = x + (w - pill_w) / 2
        if pct > 18:
            fill_h = (cyl_h - 2) * (pct / 100.0)
            pill_y = cyl_y + (fill_h / 2) - (pill_h / 2)
        else:
            pill_y = cyl_y + 6

        c.setFillColor(colors.HexColor("#1E120A"))
        c.roundRect(pill_x, pill_y, pill_w, pill_h, 3, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(x + w / 2, pill_y + 3.8, kg_texto)

    # Nombre del tanque (máx 2 líneas)
    y_nombre = cyl_y - 12
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 7.3)
    lineas_nombre = _envolver_texto(c, nombre_tk, "Helvetica-Bold", 7.3, w - 8, max_lineas=2)
    for idx, lin in enumerate(lineas_nombre):
        c.drawCentredString(x + w / 2, y_nombre - (idx * 8.5), lin)

    # Caja inferior con descripción del producto
    box_y = y_top - h + 6
    box_h = 33
    c.setFillColor(colors.HexColor("#EEF2F6") if activo else colors.HexColor("#F1F5F9"))
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.5)
    c.roundRect(x + 4, box_y, w - 8, box_h, 4, stroke=1, fill=1)

    c.setFillColor(colors.HexColor("#334155") if activo else colors.HexColor("#94A3B8"))
    c.setFont("Helvetica", 6.2)
    lineas_desc = _envolver_texto(c, desc, "Helvetica", 6.2, w - 12, max_lineas=3)
    start_desc_y = box_y + box_h - 9.5
    for idx, lin in enumerate(lineas_desc):
        c.drawCentredString(x + w / 2, start_desc_y - (idx * 8.2), lin)


def generar_pdf_cantidad(relevamiento: dict) -> bytes:
    """
    Genera el informe visual en PDF (A4) de la Sala de Tanques para un relevamiento.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    ancho, alto = A4
    margen = 28

    rel_id = relevamiento.get("id", "-")
    fecha_str = _formatear_fecha(relevamiento.get("fecha_hora"))
    supervisor = relevamiento.get("supervisor") or "-"
    operario = relevamiento.get("operario") or "-"
    detalles_raw = relevamiento.get("detalles") or []

    # --- ENCABEZADO CORPORATIVO ---
    header_h = 56
    c.setFillColor(colors.HexColor("#4A2511"))
    c.roundRect(margen, alto - margen - header_h, ancho - 2 * margen, header_h, 8, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margen + 14, alto - margen - 23, f"INFORME DE STOCK EN TANQUES — RELEVAMIENTO #{rel_id}")

    c.setFillColor(colors.HexColor("#FDE68A"))
    c.setFont("Helvetica", 9.5)
    c.drawString(margen + 14, alto - margen - 41, "Planta Chocolates  |  Estado Visual de Sala de Tanques")

    # --- BANDA DE METADATOS DEL TURNO ---
    meta_y = alto - margen - header_h - 32
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.8)
    c.roundRect(margen, meta_y, ancho - 2 * margen, 25, 5, stroke=1, fill=1)

    c.setFillColor(colors.HexColor("#1E293B"))
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(margen + 12, meta_y + 9, f"Fecha y Hora: {fecha_str}")
    c.drawCentredString(ancho / 2 + 10, meta_y + 9, f"Supervisor: {supervisor}")
    c.drawRightString(ancho - margen - 12, meta_y + 9, f"Operario: {operario}")

    # --- CÁLCULO DE LOS 14 TANQUES ---
    datos_tanques = []
    total_general_kg = 0
    tanques_con_stock = 0

    for cfg in CONFIG_TANQUES:
        det = next(
            (d for d in detalles_raw if str(d.get("tanque", "")).strip().lower() == cfg["tanque"].strip().lower()),
            {}
        )
        calc = _calcular_tanque(cfg, det)
        total_general_kg += calc["total"]
        if calc["total"] > 0:
            tanques_con_stock += 1
        datos_tanques.append((cfg["tanque"], calc))

    # --- GRILLA DE 2 FILAS x 7 TANQUES ---
    cols = 7
    gap_x = 6.5
    gap_y = 14
    area_w = ancho - 2 * margen
    card_w = (area_w - gap_x * (cols - 1)) / cols
    card_h = 212

    y_fila_1 = meta_y - 16
    y_fila_2 = y_fila_1 - card_h - gap_y

    for idx, (nombre_tk, info) in enumerate(datos_tanques):
        fila = idx // cols
        col = idx % cols
        x_card = margen + col * (card_w + gap_x)
        y_card = y_fila_1 if fila == 0 else y_fila_2
        _dibujar_tarjeta_tanque(c, x_card, y_card, card_w, card_h, nombre_tk, info)

    # --- CUADRO RESUMEN INFERIOR ---
    resumen_y = y_fila_2 - card_h - 54
    c.setFillColor(colors.HexColor("#ECFDF5"))
    c.setStrokeColor(colors.HexColor("#10B981"))
    c.setLineWidth(1.0)
    c.roundRect(margen, resumen_y, ancho - 2 * margen, 38, 6, stroke=1, fill=1)

    c.setFillColor(colors.HexColor("#065F46"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margen + 14, resumen_y + 15, f"Tanques con stock: {tanques_con_stock} / {len(CONFIG_TANQUES)}")

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(
        ancho - margen - 14,
        resumen_y + 14,
        f"TOTAL STOCK EN PLANTA: {_fmt_kg(total_general_kg)} kg"
    )

    # --- PIE DE PÁGINA ---
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 7.5)
    c.drawString(margen, 20, f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} — Sistema de Gestión de Producción")
    c.drawRightString(ancho - margen, 20, "Página 1 de 1")

    c.showPage()
    c.save()
    return buffer.getvalue()
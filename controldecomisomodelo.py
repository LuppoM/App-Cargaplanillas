from __future__ import annotations
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional
from psycopg2.extras import RealDictCursor
from conexion import obtener_conexion

MOTIVOS_SUGERIDOS = [
    "Piso",
    "Decomiso",
    "Limpieza",
    "Puesta a punto",
    "Perdida de cinta",
    "Mal estado",
    "Fallados",
    "Raspado de paila",
    "Viruta deco",
    "Bañadora",
]


def calcular_datos_fecha(fecha_str: str) -> Dict[str, int]:
    """
    Calcula n_semana (domingo inicio):
    - Si el año empieza en domingo (semana entera), 1 de enero = Semana 1.
    - Si el año NO empieza en domingo, los primeros días son Semana 0 y la primera semana entera = Semana 1 (se atrasa 1).
    """
    dt = datetime.strptime(fecha_str[:10], "%Y-%m-%d")
    n_semana = int(dt.strftime("%U"))
    return {
        "n_semana": n_semana,
        "anio": dt.year,
        "mes": dt.month,
    }


def _columnas_tabla(cur, tabla: str) -> set[str]:
    """Devuelve en minúsculas los nombres de columnas reales de una tabla en public."""
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s;
        """,
        (tabla,),
    )
    return {r["column_name"].lower() for r in cur.fetchall()}


def _consultar_sectores_chocolate(cur) -> List[str]:
    """Trae los sectores activos de planta Chocolate desde public.sectores."""
    cur.execute(
        """
        SELECT DISTINCT TRIM(nombre) AS nombre_sector
        FROM public.sectores
        WHERE LOWER(TRIM(COALESCE(planta, ''))) LIKE %s
          AND COALESCE(activo, TRUE) = TRUE
          AND nombre IS NOT NULL
          AND TRIM(nombre) <> ''
        ORDER BY 1 ASC;
        """,
        ("chocolate%",),
    )
    filas = cur.fetchall()
    sectores = [str(f["nombre_sector"]).strip() for f in filas if f.get("nombre_sector")]

    if not any(s.lower() == "sin identificacion" for s in sectores):
        sectores.append("Sin identificacion")
    return sectores


def obtener_sectores_chocolate() -> List[str]:
    """Devuelve la lista de nombres de sectores de Chocolate / PRODUCCION."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            return _consultar_sectores_chocolate(cur)


def obtener_opciones_formulario() -> Dict[str, List[str]]:
    """Devuelve sectores, motivos, responsables y códigos para los combos del formulario."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sectores = _consultar_sectores_chocolate(cur)
            cols_deco = _columnas_tabla(cur, "decomisos")

            motivos_bd: List[str] = []
            responsables_bd: List[str] = []
            codigos_bd: List[str] = []

            if "motivo" in cols_deco:
                cur.execute(
                    """
                    SELECT DISTINCT TRIM(motivo::text) AS motivo
                    FROM public.decomisos
                    WHERE motivo IS NOT NULL AND TRIM(motivo::text) <> ''
                    ORDER BY 1 ASC;
                    """
                )
                motivos_bd = [str(r["motivo"]).strip() for r in cur.fetchall() if r.get("motivo")]

            if "responsable" in cols_deco:
                cur.execute(
                    """
                    SELECT DISTINCT TRIM(responsable::text) AS responsable
                    FROM public.decomisos
                    WHERE responsable IS NOT NULL AND TRIM(responsable::text) <> ''
                    ORDER BY 1 ASC;
                    """
                )
                responsables_bd = [str(r["responsable"]).strip() for r in cur.fetchall() if r.get("responsable")]

            if "codigo" in cols_deco:
                cur.execute(
                    """
                    SELECT DISTINCT TRIM(codigo::text) AS codigo
                    FROM public.decomisos
                    WHERE codigo IS NOT NULL AND TRIM(codigo::text) <> ''
                    ORDER BY 1 ASC
                    LIMIT 200;
                    """
                )
                codigos_bd = [str(r["codigo"]).strip() for r in cur.fetchall() if r.get("codigo")]

    motivos = list(dict.fromkeys(MOTIVOS_SUGERIDOS + motivos_bd))
    return {
        "sectores": sectores,
        "motivos": motivos,
        "responsables": responsables_bd,
        "codigos": codigos_bd,
    }


def listar_decomisos(
    anio: Optional[int] = None,
    n_semana: Optional[int] = None,
    sector: Optional[str] = None,
    limite: int = 300,
) -> List[Dict[str, Any]]:
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cols_deco = _columnas_tabla(cur, "decomisos")
            if not cols_deco:
                return []

            condiciones: List[str] = []
            params: List[Any] = []

            if "planta" in cols_deco:
                condiciones.append("LOWER(TRIM(COALESCE(planta::text, 'Chocolate'))) LIKE %s")
                params.append("chocolate%")

            if anio:
                if "anio" in cols_deco:
                    condiciones.append("anio = %s")
                else:
                    condiciones.append("EXTRACT(YEAR FROM fecha)::int = %s")
                params.append(anio)

            if n_semana:
                if "n_semana" in cols_deco:
                    condiciones.append("n_semana = %s")
                else:
                    condiciones.append("(EXTRACT(DOY FROM fecha)::int - 1 + EXTRACT(DOW FROM DATE_TRUNC('year', fecha))::int) / 7 + 1 = %s")
                params.append(n_semana)

            if sector and sector.strip().upper() != "TODOS" and "sector" in cols_deco:
                condiciones.append("LOWER(TRIM(sector::text)) = LOWER(TRIM(%s))")
                params.append(sector.strip())

            where_sql = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
            params.append(limite)

            sel_codigo = "COALESCE(codigo::text, '') AS codigo" if "codigo" in cols_deco else "'' AS codigo"
            sel_motivo = "COALESCE(motivo::text, '') AS motivo" if "motivo" in cols_deco else "'' AS motivo"
            sel_sector = "COALESCE(sector::text, '') AS sector" if "sector" in cols_deco else "'' AS sector"
            sel_peso = "COALESCE(peso, 0) AS peso" if "peso" in cols_deco else "0 AS peso"
            sel_resp = "COALESCE(responsable::text, '') AS responsable" if "responsable" in cols_deco else "'' AS responsable"
            sel_sem = "n_semana" if "n_semana" in cols_deco else "NULL AS n_semana"
            sel_anio = "anio" if "anio" in cols_deco else "EXTRACT(YEAR FROM fecha)::int AS anio"
            sel_mes = "mes" if "mes" in cols_deco else "EXTRACT(MONTH FROM fecha)::int AS mes"
            sel_planta = "COALESCE(planta::text, 'Chocolate') AS planta" if "planta" in cols_deco else "'Chocolate' AS planta"
            sel_creado = "COALESCE(creado_por::text, '') AS creado_por" if "creado_por" in cols_deco else "'' AS creado_por"

            cur.execute(
                f"""
                SELECT id,
                       TO_CHAR(fecha, 'YYYY-MM-DD') AS fecha,
                       {sel_codigo},
                       {sel_motivo},
                       {sel_sector},
                       {sel_peso},
                       {sel_resp},
                       {sel_sem},
                       {sel_anio},
                       {sel_mes},
                       {sel_planta},
                       {sel_creado}
                FROM public.decomisos
                {where_sql}
                ORDER BY fecha DESC, id DESC
                LIMIT %s;
                """,
                tuple(params),
            )
            filas = cur.fetchall()
            return [
                {
                    "id": f["id"],
                    "fecha": f["fecha"],
                    "codigo": f["codigo"],
                    "motivo": f["motivo"],
                    "sector": f["sector"],
                    "peso": float(f["peso"] or 0),
                    "responsable": f["responsable"],
                    "n_semana": f["n_semana"],
                    "anio": f["anio"],
                    "mes": f["mes"],
                    "planta": f["planta"],
                    "creado_por": f["creado_por"],
                }
                for f in filas
            ]


def registrar_decomiso(datos: Dict[str, Any]) -> Dict[str, Any]:
    fecha = str(datos.get("fecha", "")).strip()
    if not fecha:
        raise ValueError("La fecha es obligatoria.")

    info_fecha = calcular_datos_fecha(fecha)
    n_semana = int(datos.get("n_semana") or info_fecha["n_semana"])
    anio = int(datos.get("anio") or info_fecha["anio"])
    mes = int(datos.get("mes") or info_fecha["mes"])

    codigo = str(datos.get("codigo") or "").strip()
    motivo = str(datos.get("motivo") or "").strip()
    sector = str(datos.get("sector") or "").strip()
    peso = float(datos.get("peso") or 0)
    responsable = str(datos.get("responsable") or "").strip()
    planta = str(datos.get("planta") or "Chocolate").strip()
    creado_por = str(datos.get("creado_por") or "").strip()

    if not motivo or not sector:
        raise ValueError("Motivo y sector son obligatorios.")
    if peso <= 0:
        raise ValueError("El peso debe ser mayor a 0.")

    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cols_deco = _columnas_tabla(cur, "decomisos")
                candidatos = [
                    ("fecha", fecha),
                    ("codigo", codigo),
                    ("motivo", motivo),
                    ("sector", sector),
                    ("peso", peso),
                    ("responsable", responsable),
                    ("n_semana", n_semana),
                    ("anio", anio),
                    ("mes", mes),
                    ("planta", planta),
                    ("creado_por", creado_por),
                ]
                columnas_insert = [col for col, _ in candidatos if col in cols_deco]
                valores_insert = [val for col, val in candidatos if col in cols_deco]
                placeholders = ", ".join(["%s"] * len(columnas_insert))

                cur.execute(
                    f"""
                    INSERT INTO public.decomisos ({', '.join(columnas_insert)})
                    VALUES ({placeholders})
                    RETURNING id;
                    """,
                    tuple(valores_insert),
                )
                nuevo_id = cur.fetchone()["id"]
            conn.commit()
            return {"ok": True, "id": nuevo_id, "n_semana": n_semana, "anio": anio, "mes": mes}
        except Exception:
            conn.rollback()
            raise


def actualizar_decomiso(id_decomiso: int, datos: Dict[str, Any]) -> bool:
    fecha = str(datos.get("fecha", "")).strip()
    if not fecha:
        raise ValueError("La fecha es obligatoria.")

    info_fecha = calcular_datos_fecha(fecha)
    n_semana = int(datos.get("n_semana") or info_fecha["n_semana"])
    anio = int(datos.get("anio") or info_fecha["anio"])
    mes = int(datos.get("mes") or info_fecha["mes"])

    motivo = str(datos.get("motivo") or "").strip()
    sector = str(datos.get("sector") or "").strip()
    peso = float(datos.get("peso") or 0)

    if not motivo or not sector:
        raise ValueError("Motivo y sector son obligatorios.")
    if peso <= 0:
        raise ValueError("El peso debe ser mayor a 0.")

    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cols_deco = _columnas_tabla(cur, "decomisos")
                candidatos = [
                    ("fecha", fecha),
                    ("codigo", str(datos.get("codigo") or "").strip()),
                    ("motivo", motivo),
                    ("sector", sector),
                    ("peso", peso),
                    ("responsable", str(datos.get("responsable") or "").strip()),
                    ("n_semana", n_semana),
                    ("anio", anio),
                    ("mes", mes),
                ]
                sets = [f"{col} = %s" for col, _ in candidatos if col in cols_deco]
                valores = [val for col, val in candidatos if col in cols_deco]
                valores.append(id_decomiso)

                cur.execute(
                    f"""
                    UPDATE public.decomisos
                    SET {', '.join(sets)}
                    WHERE id = %s;
                    """,
                    tuple(valores),
                )
                actualizado = cur.rowcount > 0
            conn.commit()
            return actualizado
        except Exception:
            conn.rollback()
            raise


def eliminar_decomiso(id_decomiso: int) -> bool:
    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("DELETE FROM public.decomisos WHERE id = %s;", (id_decomiso,))
                eliminado = cur.rowcount > 0
            conn.commit()
            return eliminado
        except Exception:
            conn.rollback()
            raise


def _normalizar_texto(texto: str) -> str:
    txt = str(texto or "").strip().lower()
    txt = "".join(
        c for c in unicodedata.normalize("NFD", txt)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(txt.split())


def obtener_resumen_semanal(anio: int, n_semana: int) -> Dict[str, Any]:
    """
    Cruza Kg elaborados (public.planillas) vs Kg decomiso (public.decomisos)
    para los sectores de Chocolate en public.sectores.
    """
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sectores_choco = _consultar_sectores_chocolate(cur)
            mapa_oficial = {_normalizar_texto(s): s for s in sectores_choco}
            cols_deco = _columnas_tabla(cur, "decomisos")

            kg_elaborados_map: Dict[str, float] = {s: 0.0 for s in sectores_choco}
            kg_decomiso_map: Dict[str, float] = {s: 0.0 for s in sectores_choco}

            # Misma fórmula exacta que int(dt.strftime("%U")) + 1 en Python (domingo = inicio de semana)
            expr_semana_pg = (
                "(EXTRACT(DOY FROM fecha)::int - 1 "
                "+ EXTRACT(DOW FROM DATE_TRUNC('year', fecha))::int) / 7 + 1"
            )
            # En strftime("%U"), los días previos al primer domingo del año son semana 0 (+1 = 1),
            # y cada domingo suma 1:
            expr_semana_python = (
                "((EXTRACT(DOY FROM fecha)::int - 1 "
                "- EXTRACT(DOW FROM fecha)::int + 7) / 7) + 1"
            )

            # 1. Kg elaborados desde public.planillas
            cur.execute(
                f"""
                SELECT TRIM(centro_trabajo) AS linea,
                       COALESCE(SUM(kg_cajas_reales), 0) AS total_kg
                FROM public.planillas
                WHERE EXTRACT(YEAR FROM fecha)::int = %s
                  AND {expr_semana_python} = %s
                  AND LOWER(TRIM(COALESCE(planta, ''))) LIKE %s
                GROUP BY TRIM(centro_trabajo);
                """,
                (anio, n_semana, "chocolate%"),
            )
            for row in cur.fetchall():
                kg_f = float(row["total_kg"] or 0)
                key = _normalizar_texto(row["linea"])

                if key in mapa_oficial:
                    kg_elaborados_map[mapa_oficial[key]] += kg_f
                elif key.startswith("boiler") and "boiler" in mapa_oficial:
                    kg_elaborados_map[mapa_oficial["boiler"]] += kg_f
                else:
                    # Coincidencia parcial por si en sectores dice ej. "Moldeo" y en planillas "Moldeo Pascua"
                    destino = next(
                        (oficial for norm, oficial in mapa_oficial.items()
                         if norm and norm != "sin identificacion" and (norm in key or key in norm)),
                        None,
                    )
                    if destino:
                        kg_elaborados_map[destino] += kg_f
                    else:
                        sin_id = mapa_oficial.get("sin identificacion", "Sin identificacion")
                        kg_elaborados_map[sin_id] += kg_f

            # 2. Kg decomiso desde public.decomisos
            if cols_deco and "sector" in cols_deco and "peso" in cols_deco:
                cond_deco = []
                params_deco: List[Any] = []

                if "anio" in cols_deco:
                    cond_deco.append("anio = %s")
                else:
                    cond_deco.append("EXTRACT(YEAR FROM fecha)::int = %s")
                params_deco.append(anio)

                if "n_semana" in cols_deco:
                    cond_deco.append("n_semana = %s")
                else:
                    cond_deco.append(f"{expr_semana_python} = %s")
                params_deco.append(n_semana)

                if "planta" in cols_deco:
                    cond_deco.append("LOWER(TRIM(COALESCE(planta::text, 'Chocolate'))) LIKE %s")
                    params_deco.append("chocolate%")

                cur.execute(
                    f"""
                    SELECT TRIM(sector::text) AS sector,
                           COALESCE(SUM(peso), 0) AS total_peso
                    FROM public.decomisos
                    WHERE {' AND '.join(cond_deco)}
                    GROUP BY TRIM(sector::text);
                    """,
                    tuple(params_deco),
                )
                for row in cur.fetchall():
                    peso_f = float(row["total_peso"] or 0)
                    key = _normalizar_texto(row["sector"])
                    if key in mapa_oficial:
                        kg_decomiso_map[mapa_oficial[key]] += peso_f
                    else:
                        sin_id = mapa_oficial.get("sin identificacion", "Sin identificacion")
                        kg_decomiso_map[sin_id] += peso_f

    total_elaborados = round(sum(kg_elaborados_map.values()), 2)
    total_decomiso = round(sum(kg_decomiso_map.values()), 2)

    filas_informe = []
    for sec in sectores_choco:
        elab = round(kg_elaborados_map[sec], 2)
        deco = round(kg_decomiso_map[sec], 2)
        if deco <= 0:
            continue

        if _normalizar_texto(sec) == "sin identificacion":
            pct = round((deco / total_elaborados) * 100, 2) if total_elaborados > 0 else None
        else:
            pct = round((deco / elab) * 100, 2) if elab > 0 else None

        filas_informe.append(
            {
                "sector": sec,
                "kg_elaborados": elab,
                "kg_decomiso": deco,
                "porcentaje": pct,
            }
        )

    pct_total = round((total_decomiso / total_elaborados) * 100, 2) if total_elaborados > 0 else 0.0

    return {
        "anio": anio,
        "n_semana": n_semana,
        "filas": filas_informe,
        "total_elaborados": total_elaborados,
        "total_decomiso": total_decomiso,
        "porcentaje_total": pct_total,
    }
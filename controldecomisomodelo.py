from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
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
    """Calcula n_semana (estilo WEEKNUM de Excel, domingo inicio), anio y mes."""
    dt = datetime.strptime(fecha_str[:10], "%Y-%m-%d")
    n_semana = int(dt.strftime("%U")) + 1
    return {
        "n_semana": n_semana,
        "anio": dt.year,
        "mes": dt.month,
    }


def _consultar_sectores_chocolate(cur) -> List[str]:
    """Consulta interna usando cursor activo."""
    cur.execute(
        """
        SELECT DISTINCT TRIM(nombre_sector) AS nombre_sector
        FROM public.sectores
        WHERE LOWER(TRIM(COALESCE(planta, ''))) LIKE 'Chocolate%'
          AND TRANSLATE(UPPER(TRIM(COALESCE(area, ''))), 'ÁÉÍÓÚ', 'AEIOU') = 'PRODUCCION'
          AND nombre_sector IS NOT NULL
          AND TRIM(nombre_sector) <> ''
        ORDER BY 1
        """
    )
    sectores = [
        (r["nombre_sector"] if isinstance(r, dict) else r[0])
        for r in cur.fetchall()
        if (r["nombre_sector"] if isinstance(r, dict) else r[0])
    ]
    if not any(s.lower() == "sin identificacion" for s in sectores):
        sectores.append("Sin identificacion")
    return sectores

def obtener_sectores_chocolate() -> List[str]:
    """Trae los sectores de planta Chocolate desde public.sectores."""
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            return _consultar_sectores_chocolate(cur)


def listar_decomisos(
    anio: Optional[int] = None,
    n_semana: Optional[int] = None,
    sector: Optional[str] = None,
    limite: int = 300,
) -> List[Dict[str, Any]]:
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            condiciones = ["LOWER(TRIM(planta)) LIKE 'chocolate%'"]
            params: List[Any] = []

            if anio:
                condiciones.append("anio = %s")
                params.append(anio)
            if n_semana:
                condiciones.append("n_semana = %s")
                params.append(n_semana)
            if sector and sector.upper() != "TODOS":
                condiciones.append("LOWER(TRIM(sector)) = LOWER(TRIM(%s))")
                params.append(sector)

            where_sql = f"WHERE {' AND '.join(condiciones)}"
            params.append(limite)

            cur.execute(
                f"""
                SELECT id, TO_CHAR(fecha, 'YYYY-MM-DD') AS fecha, codigo, motivo,
                       sector, peso, responsable, n_semana, anio, mes, planta, creado_por
                FROM public.decomisos
                {where_sql}
                ORDER BY fecha DESC, id DESC
                LIMIT %s
                """,
                tuple(params),
            )
            filas = cur.fetchall()
            return [
                {
                    "id": f[0],
                    "fecha": f[1],
                    "codigo": f[2] or "",
                    "motivo": f[3] or "",
                    "sector": f[4] or "",
                    "peso": float(f[5] or 0),
                    "responsable": f[6] or "",
                    "n_semana": f[7],
                    "anio": f[8],
                    "mes": f[9],
                    "planta": f[10] or "Chocolate",
                    "creado_por": f[11] or "",
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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.decomisos
                        (fecha, codigo, motivo, sector, peso, responsable, n_semana, anio, mes, planta, creado_por)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (fecha, codigo, motivo, sector, peso, responsable, n_semana, anio, mes, planta, creado_por),
                )
                nuevo_id = cur.fetchone()[0]
            conn.commit()
            return {"ok": True, "id": nuevo_id, "n_semana": n_semana, "anio": anio, "mes": mes}
        except Exception:
            conn.rollback()
            raise


def actualizar_decomiso(id_decomiso: int, datos: Dict[str, Any]) -> bool:
    fecha = str(datos.get("fecha", "")).strip()
    info_fecha = calcular_datos_fecha(fecha)
    n_semana = int(datos.get("n_semana") or info_fecha["n_semana"])
    anio = int(datos.get("anio") or info_fecha["anio"])
    mes = int(datos.get("mes") or info_fecha["mes"])

    with obtener_conexion() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.decomisos
                    SET fecha = %s,
                        codigo = %s,
                        motivo = %s,
                        sector = %s,
                        peso = %s,
                        responsable = %s,
                        n_semana = %s,
                        anio = %s,
                        mes = %s
                    WHERE id = %s
                    """,
                    (
                        fecha,
                        str(datos.get("codigo") or "").strip(),
                        str(datos.get("motivo") or "").strip(),
                        str(datos.get("sector") or "").strip(),
                        float(datos.get("peso") or 0),
                        str(datos.get("responsable") or "").strip(),
                        n_semana,
                        anio,
                        mes,
                        id_decomiso,
                    ),
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
            with conn.cursor() as cur:
                cur.execute("DELETE FROM public.decomisos WHERE id = %s", (id_decomiso,))
                eliminado = cur.rowcount > 0
            conn.commit()
            return eliminado
        except Exception:
            conn.rollback()
            raise


def obtener_opciones_formulario() -> Dict[str, List[str]]:
    """Devuelve sectores activos de planta Chocolate, motivos y responsables para autocompletar."""
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            sectores = _consultar_sectores_chocolate(cur)

            cur.execute("SELECT DISTINCT TRIM(motivo) FROM public.decomisos WHERE motivo IS NOT NULL AND TRIM(motivo) <> '' ORDER BY 1")
            motivos_bd = [r[0] for r in cur.fetchall()]

            cur.execute("SELECT DISTINCT TRIM(responsable) FROM public.decomisos WHERE responsable IS NOT NULL AND TRIM(responsable) <> '' ORDER BY 1")
            responsables_bd = [r[0] for r in cur.fetchall()]

            cur.execute("SELECT DISTINCT TRIM(codigo) FROM public.decomisos WHERE codigo IS NOT NULL AND TRIM(codigo) <> '' ORDER BY 1 LIMIT 200")
            codigos_bd = [r[0] for r in cur.fetchall()]

        motivos = list(dict.fromkeys(MOTIVOS_SUGERIDOS + motivos_bd))
        return {
            "sectores": sectores,
            "motivos": motivos,
            "responsables": responsables_bd,
            "codigos": codigos_bd,
        }


def obtener_resumen_semanal(anio: int, n_semana: int) -> Dict[str, Any]:
    """
    Cruza Kg elaborados (tabla planillas) vs Kg decomiso (tabla decomisos)
    para todos los sectores activos de planta Chocolate en public.sectores.
    """
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            sectores_choco = _consultar_sectores_chocolate(cur)
            mapa_oficial = {s.lower(): s for s in sectores_choco}

            kg_elaborados_map: Dict[str, float] = {s: 0.0 for s in sectores_choco}
            kg_decomiso_map: Dict[str, float] = {s: 0.0 for s in sectores_choco}

            # 1. Detectar nombres de columnas en public.planillas
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'planillas'
                """
            )
            cols_planillas = {r[0].lower() for r in cur.fetchall()}

            col_linea = "linea" if "linea" in cols_planillas else ("sector" if "sector" in cols_planillas else ("centro_trabajo" if "centro_trabajo" in cols_planillas else None))
            col_kg = "produccion_kg" if "produccion_kg" in cols_planillas else ("kg_producidos" if "kg_producidos" in cols_planillas else ("kg_cajas_reales" if "kg_cajas_reales" in cols_planillas else None))
            col_sem = "n_semana" if "n_semana" in cols_planillas else ("semana" if "semana" in cols_planillas else None)
            col_anio = "anio" if "anio" in cols_planillas else ("año" if "año" in cols_planillas else None)
            filtro_planta = "AND LOWER(TRIM(planta)) LIKE 'chocolate%'" if "planta" in cols_planillas else ""

            if col_linea and col_kg and col_sem and col_anio:
                cur.execute(
                    f"""
                    SELECT TRIM({col_linea}) AS linea, COALESCE(SUM({col_kg}), 0)
                    FROM public.planillas
                    WHERE {col_anio} = %s AND {col_sem} = %s {filtro_planta}
                    GROUP BY TRIM({col_linea})
                    """,
                    (anio, n_semana),
                )
                for linea_raw, kg_val in cur.fetchall():
                    kg_f = float(kg_val or 0)
                    key = (linea_raw or "").strip().lower()
                    if key in mapa_oficial:
                        kg_elaborados_map[mapa_oficial[key]] += kg_f
                    elif key.startswith("boiler") and "boiler" in mapa_oficial:
                        kg_elaborados_map[mapa_oficial["boiler"]] += kg_f

            # 2. Sumar Kg decomiso desde public.decomisos
            cur.execute(
                """
                SELECT TRIM(sector) AS sector, COALESCE(SUM(peso), 0)
                FROM public.decomisos
                WHERE anio = %s AND n_semana = %s
                  AND LOWER(TRIM(planta)) LIKE 'chocolate%'
                GROUP BY TRIM(sector)
                """,
                (anio, n_semana),
            )
            for sec_raw, peso_val in cur.fetchall():
                peso_f = float(peso_val or 0)
                key = (sec_raw or "").strip().lower()
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
            if sec.lower() == "sin identificacion":
                pct = round((deco / total_elaborados) * 100, 2) if total_elaborados > 0 else None
            else:
                pct = round((deco / elab) * 100, 2) if elab > 0 else None

            filas_informe.append({
                "sector": sec,
                "kg_elaborados": elab,
                "kg_decomiso": deco,
                "porcentaje": pct,
            })

        pct_total = round((total_decomiso / total_elaborados) * 100, 2) if total_elaborados > 0 else 0.0

        return {
            "anio": anio,
            "n_semana": n_semana,
            "filas": filas_informe,
            "total_elaborados": total_elaborados,
            "total_decomiso": total_decomiso,
            "porcentaje_total": pct_total,
        }
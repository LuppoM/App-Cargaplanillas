from psycopg2.extras import RealDictCursor
from conexion import obtener_conexion

MAP_TALLERES = [
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


def obtener_planillas(planta=None):
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if planta:
                sql = """
                    SELECT * FROM planillas 
                    WHERE LOWER(TRIM(planta)) = LOWER(TRIM(%s)) 
                    ORDER BY fecha DESC, id DESC;
                """
                cur.execute(sql, (planta,))
            else:
                sql = "SELECT * FROM planillas ORDER BY fecha DESC, id DESC;"
                cur.execute(sql)
            return cur.fetchall()


def obtener_planilla_por_id(planilla_id: int):
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM planillas WHERE id = %s;", (planilla_id,))
            registro = cur.fetchone()
            if not registro:
                return None

            cur.execute("""
                SELECT id, taller, descripcion, horas
                FROM planillas_detenciones
                WHERE planilla_id = %s
                ORDER BY id ASC;
            """, (planilla_id,))
            registro["detenciones"] = cur.fetchall()
            return registro


def _preparar_valores_detenciones(datos: dict):
    """
    Asegura las 12 columnas de minutos en 'datos' (para la tabla planillas)
    y arma las filas para insertar en 'planillas_detenciones' (en horas + descripcion).
    """
    detenciones_lista = datos.pop("detenciones", None) or []

    # 1. Inicializar los 12 campos de minutos en 0 por defecto
    for col, _ in MAP_TALLERES:
        datos[col] = float(datos.get(col) or 0)

    # 2. Si viene el array 'detenciones' desde el frontend, sincronizar ambos
    filas_detalle = []
    if detenciones_lista:
        mapa_nombre_a_col = {nombre.lower(): col for col, nombre in MAP_TALLERES}
        mapa_sin_tilde = {
            "produccion": "detencion_produccion",
            "refrigerio": "detencion_refrigerio",
            "mecanico": "detencion_mecanico",
            "electrico": "detencion_electrico",
            "calidad": "detencion_calidad",
            "programacion": "detencion_programacion",
            "limpieza": "detencion_limpieza",
            "abastecimiento": "detencion_abastecimiento",
            "desarrollo": "detencion_desarrollo",
            "alistamiento": "detencion_alistamiento",
            "rrhh": "detencion_rrhh",
            "suministro": "detencion_suministro",
        }

        for d in detenciones_lista:
            taller = str(d.get("taller", "")).strip()
            desc = str(d.get("descripcion", "")).strip()
            horas = float(d.get("horas") or 0)
            minutos = round(horas * 60, 2)

            clave = taller.lower()
            col = mapa_nombre_a_col.get(clave) or mapa_sin_tilde.get(clave)
            if col:
                datos[col] = minutos

            if horas > 0:
                filas_detalle.append((taller, desc, round(horas, 4)))

    return filas_detalle


def insertar_planilla(datos: dict):
    filas_detalle = _preparar_valores_detenciones(datos)

    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                sql_planilla = """
                    INSERT INTO planillas (
                        fecha, planta, centro_trabajo, codigo, turno,
                        dotacion_teorica, horas_trabajadas, kg_cajas_reales,
                        peso_promedio_unid_kg, dotacion_real, decomiso_kg,
                        reproceso_kg, scrap_flex_kg,
                        detencion_produccion, detencion_refrigerio, detencion_mecanico,
                        detencion_electrico, detencion_calidad, detencion_programacion,
                        detencion_limpieza, detencion_abastecimiento, detencion_desarrollo,
                        detencion_alistamiento, detencion_rrhh, detencion_suministro
                    ) VALUES (
                        %(fecha)s, %(planta)s, %(centro_trabajo)s, %(codigo)s, %(turno)s,
                        %(dotacion_teorica)s, %(horas_trabajadas)s, %(kg_cajas_reales)s,
                        %(peso_promedio_unid_kg)s, %(dotacion_real)s, %(decomiso_kg)s,
                        %(reproceso_kg)s, %(scrap_flex_kg)s,
                        %(detencion_produccion)s, %(detencion_refrigerio)s, %(detencion_mecanico)s,
                        %(detencion_electrico)s, %(detencion_calidad)s, %(detencion_programacion)s,
                        %(detencion_limpieza)s, %(detencion_abastecimiento)s, %(detencion_desarrollo)s,
                        %(detencion_alistamiento)s, %(detencion_rrhh)s, %(detencion_suministro)s
                    ) RETURNING id;
                """
                cur.execute(sql_planilla, datos)
                nuevo_id = cur.fetchone()["id"]

                if filas_detalle:
                    sql_det = """
                        INSERT INTO planillas_detenciones (planilla_id, taller, descripcion, horas)
                        VALUES (%s, %s, %s, %s);
                    """
                    cur.executemany(
                        sql_det,
                        [(nuevo_id, t, desc, hs) for t, desc, hs in filas_detalle]
                    )

                conn.commit()
                return nuevo_id
        except Exception:
            conn.rollback()
            raise


def actualizar_planilla(planilla_id: int, datos: dict):
    filas_detalle = _preparar_valores_detenciones(datos)
    datos["id"] = planilla_id

    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                sql_planilla = """
                    UPDATE planillas SET
                        fecha = %(fecha)s,
                        planta = %(planta)s,
                        centro_trabajo = %(centro_trabajo)s,
                        codigo = %(codigo)s,
                        turno = %(turno)s,
                        dotacion_teorica = %(dotacion_teorica)s,
                        horas_trabajadas = %(horas_trabajadas)s,
                        kg_cajas_reales = %(kg_cajas_reales)s,
                        peso_promedio_unid_kg = %(peso_promedio_unid_kg)s,
                        dotacion_real = %(dotacion_real)s,
                        decomiso_kg = %(decomiso_kg)s,
                        reproceso_kg = %(reproceso_kg)s,
                        scrap_flex_kg = %(scrap_flex_kg)s,
                        detencion_produccion = %(detencion_produccion)s,
                        detencion_refrigerio = %(detencion_refrigerio)s,
                        detencion_mecanico = %(detencion_mecanico)s,
                        detencion_electrico = %(detencion_electrico)s,
                        detencion_calidad = %(detencion_calidad)s,
                        detencion_programacion = %(detencion_programacion)s,
                        detencion_limpieza = %(detencion_limpieza)s,
                        detencion_abastecimiento = %(detencion_abastecimiento)s,
                        detencion_desarrollo = %(detencion_desarrollo)s,
                        detencion_alistamiento = %(detencion_alistamiento)s,
                        detencion_rrhh = %(detencion_rrhh)s,
                        detencion_suministro = %(detencion_suministro)s
                    WHERE id = %(id)s;
                """
                cur.execute(sql_planilla, datos)

                # Reemplazar registros en planillas_detenciones
                cur.execute("DELETE FROM planillas_detenciones WHERE planilla_id = %s;", (planilla_id,))
                if filas_detalle:
                    sql_det = """
                        INSERT INTO planillas_detenciones (planilla_id, taller, descripcion, horas)
                        VALUES (%s, %s, %s, %s);
                    """
                    cur.executemany(
                        sql_det,
                        [(planilla_id, t, desc, hs) for t, desc, hs in filas_detalle]
                    )

                conn.commit()
                return True
        except Exception:
            conn.rollback()
            raise


def eliminar_planilla(planilla_id: int):
    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("DELETE FROM planillas_detenciones WHERE planilla_id = %s;", (planilla_id,))
                cur.execute("DELETE FROM planillas WHERE id = %s;", (planilla_id,))
                conn.commit()
                return True
        except Exception:
            conn.rollback()
            raise
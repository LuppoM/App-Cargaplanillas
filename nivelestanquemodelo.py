from psycopg2.extras import RealDictCursor
from conexion import obtener_conexion


def obtener_relevamientos():
    """Devuelve el historial de relevamientos ordenados del más reciente al más antiguo."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT 
                    r.id,
                    r.fecha_hora,
                    r.supervisor,
                    r.operario,
                    r.fecha_creacion,
                    COUNT(d.id) FILTER (WHERE d.valor_medido IS NOT NULL OR d.kg_manual IS NOT NULL) AS tanques_medidos
                FROM relevamientos_tanques r
                LEFT JOIN relevamientos_tanques_detalle d ON d.relevamiento_id = r.id
                GROUP BY r.id
                ORDER BY r.fecha_hora DESC, r.id DESC;
            """
            cur.execute(sql)
            return cur.fetchall()
def obtener_codigos_tanques():
    """Trae los códigos únicos y sus descripciones desde la tabla de teóricos."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT DISTINCT TRIM(codigo) AS codigo, TRIM(descripcion) AS descripcion
                FROM teoricos
                WHERE codigo IS NOT NULL AND TRIM(codigo) <> ''
                ORDER BY codigo ASC;
            """
            cur.execute(sql)
            return cur.fetchall()

def obtener_relevamiento_por_id(relevamiento_id: int):
    """Devuelve la cabecera del relevamiento junto con el detalle de cada tanque."""
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM relevamientos_tanques WHERE id = %s;",
                (relevamiento_id,)
            )
            registro = cur.fetchone()
            if not registro:
                return None

            cur.execute("""
                SELECT id, tanque, codigo, descripcion, valor_medido, nro_conca, kg_manual
                FROM relevamientos_tanques_detalle
                WHERE relevamiento_id = %s
                ORDER BY id ASC;
            """, (relevamiento_id,))
            registro["detalles"] = cur.fetchall()
            return registro


def _preparar_filas_detalle(relevamiento_id: int, detalles: list):
    """Normaliza cada fila de tanque antes de insertarla en la tabla detalle."""
    filas = []
    for d in detalles:
        tanque = str(d.get("tanque", "")).strip()
        if not tanque:
            continue

        codigo = str(d.get("codigo") or "").strip()
        descripcion = str(d.get("descripcion") or "").strip()

        val_raw = d.get("valor_medido")
        valor_medido = float(val_raw) if val_raw not in (None, "") else None

        conca_raw = d.get("nro_conca")
        nro_conca = int(conca_raw) if conca_raw not in (None, "") else None

        kg_raw = d.get("kg_manual")
        kg_manual = float(kg_raw) if kg_raw not in (None, "") else None

        filas.append((
            relevamiento_id,
            tanque,
            codigo,
            descripcion,
            valor_medido,
            nro_conca,
            kg_manual
        ))
    return filas


def insertar_relevamiento(datos: dict):
    """Crea un relevamiento de tanques y guarda el detalle de todos los tanques."""
    detalles = datos.pop("detalles", []) or []

    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                sql_cabecera = """
                    INSERT INTO relevamientos_tanques (fecha_hora, supervisor, operario)
                    VALUES (COALESCE(%(fecha_hora)s, NOW()), %(supervisor)s, %(operario)s)
                    RETURNING id;
                """
                datos.setdefault("fecha_hora", None)
                cur.execute(sql_cabecera, datos)
                nuevo_id = cur.fetchone()["id"]

                filas = _preparar_filas_detalle(nuevo_id, detalles)
                if filas:
                    sql_detalle = """
                        INSERT INTO relevamientos_tanques_detalle (
                            relevamiento_id, tanque, codigo, descripcion,
                            valor_medido, nro_conca, kg_manual
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """
                    cur.executemany(sql_detalle, filas)

                conn.commit()
                return nuevo_id
        except Exception:
            conn.rollback()
            raise


def actualizar_relevamiento(relevamiento_id: int, datos: dict):
    """Actualiza la cabecera y reemplaza las lecturas de cada tanque del relevamiento."""
    detalles = datos.pop("detalles", []) or []
    datos["id"] = relevamiento_id

    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                sql_cabecera = """
                    UPDATE relevamientos_tanques SET
                        fecha_hora = COALESCE(%(fecha_hora)s, fecha_hora),
                        supervisor = %(supervisor)s,
                        operario = %(operario)s
                    WHERE id = %(id)s;
                """
                datos.setdefault("fecha_hora", None)
                cur.execute(sql_cabecera, datos)

                # Reemplazar detalle de tanques
                cur.execute(
                    "DELETE FROM relevamientos_tanques_detalle WHERE relevamiento_id = %s;",
                    (relevamiento_id,)
                )

                filas = _preparar_filas_detalle(relevamiento_id, detalles)
                if filas:
                    sql_detalle = """
                        INSERT INTO relevamientos_tanques_detalle (
                            relevamiento_id, tanque, codigo, descripcion,
                            valor_medido, nro_conca, kg_manual
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """
                    cur.executemany(sql_detalle, filas)

                conn.commit()
                return True
        except Exception:
            conn.rollback()
            raise


def eliminar_relevamiento(relevamiento_id: int):
    """Elimina el relevamiento y en cascada sus filas de detalle."""
    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "DELETE FROM relevamientos_tanques_detalle WHERE relevamiento_id = %s;",
                    (relevamiento_id,)
                )
                cur.execute(
                    "DELETE FROM relevamientos_tanques WHERE id = %s;",
                    (relevamiento_id,)
                )
                conn.commit()
                return True
        except Exception:
            conn.rollback()
            raise
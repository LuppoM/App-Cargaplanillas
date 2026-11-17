from psycopg2.extras import RealDictCursor
from conexion import obtener_conexion


def obtener_planillas(planta=None):
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            base_sql = """
                SELECT p.*, COALESCE(SUM(d.horas), 0) AS total_horas_detencion
                FROM planillas p
                LEFT JOIN detenciones d ON d.planilla_id = p.id
            """
            if planta:
                sql = base_sql + " WHERE LOWER(p.planta) = LOWER(%s) GROUP BY p.id ORDER BY p.fecha DESC, p.id DESC;"
                cur.execute(sql, (planta,))
            else:
                sql = base_sql + " GROUP BY p.id ORDER BY p.fecha DESC, p.id DESC;"
                cur.execute(sql)
            return cur.fetchall()


def obtener_planilla_por_id(planilla_id: int):
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Obtener datos de la planilla principal
            cur.execute("SELECT * FROM planillas WHERE id = %s;", (planilla_id,))
            registro = cur.fetchone()
            
            if not registro:
                return None
            
            # 2. Obtener las detenciones asociadas
            cur.execute("""
                SELECT id, taller, descripcion, horas 
                FROM detenciones 
                WHERE planilla_id = %s;
            """, (planilla_id,))
            registro['detenciones'] = cur.fetchall()
            
            return registro


def insertar_planilla(datos: dict):
    # Separar la lista de detenciones del dict principal
    detenciones = datos.pop('detenciones', [])
    
    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Insertar la planilla principal
                sql_planilla = """
                    INSERT INTO planillas (
                        fecha, planta, centro_trabajo, codigo, turno,
                        dotacion_teorica, horas_trabajadas, kg_cajas_reales,
                        peso_promedio_unid_kg, dotacion_real, decomiso_kg,
                        reproceso_kg, scrap_flex_kg
                    ) VALUES (
                        %(fecha)s, %(planta)s, %(centro_trabajo)s, %(codigo)s, %(turno)s,
                        %(dotacion_teorica)s, %(horas_trabajadas)s, %(kg_cajas_reales)s,
                        %(peso_promedio_unid_kg)s, %(dotacion_real)s, %(decomiso_kg)s,
                        %(reproceso_kg)s, %(scrap_flex_kg)s
                    ) RETURNING id;
                """
                cur.execute(sql_planilla, datos)
                nuevo_id = cur.fetchone()['id']

                # 2. Insertar registros en la tabla 'detenciones'
                if detenciones:
                    sql_detencion = """
                        INSERT INTO detenciones (planilla_id, taller, descripcion, horas)
                        VALUES (%s, %s, %s, %s);
                    """
                    datos_detenciones = [
                        (nuevo_id, str(d['taller']), d['descripcion'], d['horas'])
                        for d in detenciones if float(d.get('horas', 0)) > 0
                    ]
                    if datos_detenciones:
                        cur.executemany(sql_detencion, datos_detenciones)

                conn.commit()
                return nuevo_id
        except Exception:
            conn.rollback()
            raise


def actualizar_planilla(planilla_id: int, datos: dict):
    detenciones = datos.pop('detenciones', [])
    datos['id'] = planilla_id
    
    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Actualizar la planilla principal
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
                        scrap_flex_kg = %(scrap_flex_kg)s
                    WHERE id = %(id)s;
                """
                cur.execute(sql_planilla, datos)

                # 2. Reemplazar detenciones: Borrar viejas
                cur.execute("DELETE FROM detenciones WHERE planilla_id = %s;", (planilla_id,))

                # 3. Insertar nuevas detenciones
                if detenciones:
                    sql_detencion = """
                        INSERT INTO detenciones (planilla_id, taller, descripcion, horas)
                        VALUES (%s, %s, %s, %s);
                    """
                    datos_detenciones = [
                        (planilla_id, str(d['taller']), d['descripcion'], d['horas'])
                        for d in detenciones if float(d.get('horas', 0)) > 0
                    ]
                    if datos_detenciones:
                        cur.executemany(sql_detencion, datos_detenciones)

                conn.commit()
                return True
        except Exception:
            conn.rollback()
            raise


def eliminar_planilla(planilla_id: int):
    with obtener_conexion() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("DELETE FROM detenciones WHERE planilla_id = %s;", (planilla_id,))
                cur.execute("DELETE FROM planillas WHERE id = %s;", (planilla_id,))
                conn.commit()
                return True
        except Exception:
            conn.rollback()
            raise
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def obtener_conexion():
    database_url = os.environ.get("DATABASE_URL")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

def obtener_planillas(planta=None):
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            if planta:
                sql = "SELECT * FROM planillas WHERE LOWER(planta) = LOWER(%s) ORDER BY fecha DESC, id DESC;"
                cur.execute(sql, (planta,))
            else:
                sql = "SELECT * FROM planillas ORDER BY fecha DESC, id DESC;"
                cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()

def obtener_planilla_por_id(planilla_id: int):
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
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
    finally:
        conn.close()

def insertar_planilla(datos: dict):
    # Separar la lista de detenciones del dict principal
    detenciones = datos.pop('detenciones', [])
    
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
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
    finally:
        conn.close()

def actualizar_planilla(planilla_id: int, datos: dict):
    detenciones = datos.pop('detenciones', [])
    datos['id'] = planilla_id
    
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
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
    finally:
        conn.close()

def eliminar_planilla(planilla_id: int):
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            # Si en la BD la FK no tiene CASCADE, borramos detenciones primero
            cur.execute("DELETE FROM detenciones WHERE planilla_id = %s;", (planilla_id,))
            cur.execute("DELETE FROM planillas WHERE id = %s;", (planilla_id,))
            conn.commit()
            return True
    finally:
        conn.close()
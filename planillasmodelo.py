import os
import psycopg2
from psycopg2.extras import RealDictCursor

def obtener_conexion():
    # Obtiene la URL de la base de datos (Neon) desde la variable de entorno
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
            cur.execute("SELECT * FROM planillas WHERE id = %s;", (planilla_id,))
            return cur.fetchone()
    finally:
        conn.close()

def insertar_planilla(datos: dict):
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO planillas (
                    fecha, planta, centro_trabajo, codigo, turno,
                    dotacion_teorica, horas_trabajadas, kg_cajas_reales,
                    peso_promedio_unid_kg, dotacion_real, decomiso_kg,
                    reproceso_kg, scrap_flex_kg, detencion_produccion,
                    detencion_refrigerio, detencion_mecanico, detencion_electrico,
                    detencion_calidad, detencion_programacion, detencion_limpieza,
                    detencion_abastecimiento, detencion_desarrollo, detencion_alistamiento,
                    detencion_rrhh, detencion_suministro
                ) VALUES (
                    %(fecha)s, %(planta)s, %(centro_trabajo)s, %(codigo)s, %(turno)s,
                    %(dotacion_teorica)s, %(horas_trabajadas)s, %(kg_cajas_reales)s,
                    %(peso_promedio_unid_kg)s, %(dotacion_real)s, %(decomiso_kg)s,
                    %(reproceso_kg)s, %(scrap_flex_kg)s, %(detencion_produccion)s,
                    %(detencion_refrigerio)s, %(detencion_mecanico)s, %(detencion_electrico)s,
                    %(detencion_calidad)s, %(detencion_programacion)s, %(detencion_limpieza)s,
                    %(detencion_abastecimiento)s, %(detencion_desarrollo)s, %(detencion_alistamiento)s,
                    %(detencion_rrhh)s, %(detencion_suministro)s
                ) RETURNING id;
            """
            cur.execute(sql, datos)
            nuevo_id = cur.fetchone()['id']
            conn.commit()
            return nuevo_id
    finally:
        conn.close()

def actualizar_planilla(planilla_id: int, datos: dict):
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            sql = """
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
            datos['id'] = planilla_id
            cur.execute(sql, datos)
            conn.commit()
            return True
    finally:
        conn.close()

def eliminar_planilla(planilla_id: int):
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM planillas WHERE id = %s;", (planilla_id,))
            conn.commit()
            return True
    finally:
        conn.close()
from conexion import obtener_conexion
from typing import List, Dict, Any, Optional
from psycopg2.extras import RealDictCursor

class SectoresModelo:

    @staticmethod
    def obtener_todos() -> List[Dict[str, Any]]:
        """Obtiene el listado completo de sectores ordenados por ID descendente."""
        sql = """
            SELECT id, nombre, planta, descripcion, activo
            FROM sectores
            ORDER BY id DESC;
        """
        try:
            with obtener_conexion() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(sql)
                    registros = cursor.fetchall()
                    return [dict(row) for row in registros]
        except Exception as e:
            print(f"[ERROR MODELO SECTORES] Fallo al consultar sectores: {e}")
            return []

    @staticmethod
    def obtener_por_id(id_sector: int) -> Optional[Dict[str, Any]]:
        """Obtiene un sector específico por su ID."""
        sql = "SELECT id, nombre, planta, descripcion, activo FROM sectores WHERE id = %s;"
        try:
            with obtener_conexion() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(sql, (id_sector,))
                    registro = cursor.fetchone()
                    return dict(registro) if registro else None
        except Exception as e:
            print(f"[ERROR MODELO SECTORES] Fallo al buscar sector ID {id_sector}: {e}")
            return None

    @staticmethod
    def insertar(datos: Dict[str, Any]) -> bool:
        """Inserta un nuevo sector en la base de datos."""
        sql = """
            INSERT INTO sectores (
                nombre, planta, descripcion, activo
            ) VALUES (
                %(nombre)s, %(planta)s, %(descripcion)s, %(activo)s
            );
        """
        try:
            with obtener_conexion() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, datos)
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR MODELO SECTORES] Fallo al insertar sector: {e}")
            return False

    @staticmethod
    def actualizar(id_sector: int, datos: Dict[str, Any]) -> bool:
        """Actualiza un sector existente por su ID."""
        sql = """
            UPDATE sectores SET
                nombre = %(nombre)s,
                planta = %(planta)s,
                descripcion = %(descripcion)s,
                activo = %(activo)s
            WHERE id = %(id)s;
        """
        datos['id'] = id_sector
        try:
            with obtener_conexion() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, datos)
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR MODELO SECTORES] Fallo al actualizar sector ID {id_sector}: {e}")
            return False
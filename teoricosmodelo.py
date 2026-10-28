from conexion import obtener_conexion
from typing import List, Dict, Any, Optional

class TeoricosModelo:
    
    @staticmethod
    def obtener_todos(limit: int = 500) -> List[Dict[str, Any]]:
        """Obtiene el listado de teóricos sin Eficiencia STD."""
        sql = """
            SELECT id, planta, estado, codigo, descripcion, bultos_hora, 
                   dotacion, centro_trabajo, uxb, peso, kg_teoricos, flex_unid_kg
            FROM teoricos
            ORDER BY id DESC
            LIMIT %s;
        """
        try:
            with obtener_conexion() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (limit,))
                    registros = cursor.fetchall()
                    return registros
        except Exception as e:
            print(f"[ERROR MODELO] Fallo al consultar teóricos: {e}")
            return []

    @staticmethod
    def obtener_por_id(id_teorico: int) -> Optional[Dict[str, Any]]:
        """Obtiene un único registro por su ID."""
        sql = "SELECT id, planta, estado, codigo, descripcion, bultos_hora, dotacion, centro_trabajo, uxb, peso, kg_teoricos, flex_unid_kg FROM teoricos WHERE id = %s;"
        try:
            with obtener_conexion() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (id_teorico,))
                    return cursor.fetchone()
        except Exception as e:
            print(f"[ERROR MODELO] Fallo al buscar teórico ID {id_teorico}: {e}")
            return None

    @staticmethod
    def insertar(datos: Dict[str, Any]) -> bool:
        """Inserta un nuevo teórico sin Eficiencia STD."""
        sql = """
            INSERT INTO teoricos (
                planta, estado, codigo, descripcion, bultos_hora, 
                dotacion, centro_trabajo, uxb, peso, kg_teoricos, flex_unid_kg
            ) VALUES (
                %(planta)s, %(estado)s, %(codigo)s, %(descripcion)s, %(bultos_hora)s, 
                %(dotacion)s, %(centro_trabajo)s, %(uxb)s, %(peso)s, 
                %(kg_teoricos)s, %(flex_unid_kg)s
            );
        """
        try:
            with obtener_conexion() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, datos)
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR MODELO] Fallo al insertar teórico: {e}")
            return False

    @staticmethod
    def actualizar(id_teorico: int, datos: Dict[str, Any]) -> bool:
        """Actualiza un teórico existente."""
        sql = """
            UPDATE teoricos SET
                planta = %(planta)s,
                estado = %(estado)s,
                codigo = %(codigo)s,
                descripcion = %(descripcion)s,
                bultos_hora = %(bultos_hora)s,
                dotacion = %(dotacion)s,
                centro_trabajo = %(centro_trabajo)s,
                uxb = %(uxb)s,
                peso = %(peso)s,
                kg_teoricos = %(kg_teoricos)s,
                flex_unid_kg = %(flex_unid_kg)s
            WHERE id = %(id)s;
        """
        datos['id'] = id_teorico
        try:
            with obtener_conexion() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, datos)
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR MODELO] Fallo al actualizar teórico ID {id_teorico}: {e}")
            return False
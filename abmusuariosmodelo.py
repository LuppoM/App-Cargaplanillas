import psycopg2.extras
from conexion import obtener_conexion


class AbmUsuariosModelo:

    @staticmethod
    def obtener_todos():
        """Devuelve la lista de todos los usuarios ordenados por ID."""
        sql = """
            SELECT id, usuario, password_hash, rol, activo
            FROM usuarios
            ORDER BY id ASC
        """
        with obtener_conexion() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                return [dict(fila) for fila in cur.fetchall()]

    @staticmethod
    def obtener_por_id(id_usuario: int):
        """Obtiene un único usuario por su ID."""
        sql = """
            SELECT id, usuario, password_hash, rol, activo
            FROM usuarios
            WHERE id = %s
        """
        with obtener_conexion() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (id_usuario,))
                fila = cur.fetchone()
                return dict(fila) if fila else None

    @staticmethod
    def existe_usuario(usuario: str, excluir_id: int = None) -> bool:
        """Verifica si ya existe un usuario con ese nombre (ignorando mayúsculas/espacios)."""
        usuario_limpio = (usuario or "").strip().lower()
        if excluir_id is not None:
            sql = """
                SELECT 1 FROM usuarios
                WHERE LOWER(TRIM(usuario)) = %s AND id <> %s
                LIMIT 1
            """
            params = (usuario_limpio, excluir_id)
        else:
            sql = """
                SELECT 1 FROM usuarios
                WHERE LOWER(TRIM(usuario)) = %s
                LIMIT 1
            """
            params = (usuario_limpio,)

        with obtener_conexion() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone() is not None

    @staticmethod
    def insertar(datos: dict) -> int:
        """Crea un nuevo usuario y devuelve su ID generado."""
        usuario = (datos.get("usuario") or "").strip()
        clave = (datos.get("password_hash") or datos.get("clave") or "").strip()
        rol = (datos.get("rol") or "").strip().lower()
        activo = bool(datos.get("activo", True))

        if not usuario or not clave or not rol:
            raise ValueError("Usuario, contraseña y rol son obligatorios.")

        if AbmUsuariosModelo.existe_usuario(usuario):
            raise ValueError(f"El usuario '{usuario}' ya existe.")

        sql = """
            INSERT INTO usuarios (usuario, password_hash, rol, activo)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        with obtener_conexion() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (usuario, clave, rol, activo))
                nuevo_id = cur.fetchone()[0]
            conn.commit()
        return nuevo_id

    @staticmethod
    def actualizar(id_usuario: int, datos: dict) -> bool:
        """
        Actualiza usuario, rol, estado activo y, si se envía una contraseña nueva,
        también actualiza password_hash.
        """
        usuario = (datos.get("usuario") or "").strip()
        clave = (datos.get("password_hash") or datos.get("clave") or "").strip()
        rol = (datos.get("rol") or "").strip().lower()
        activo = bool(datos.get("activo", True))

        if not usuario or not rol:
            raise ValueError("Usuario y rol son obligatorios.")

        if AbmUsuariosModelo.existe_usuario(usuario, excluir_id=id_usuario):
            raise ValueError(f"El usuario '{usuario}' ya está en uso.")

        with obtener_conexion() as conn:
            with conn.cursor() as cur:
                if clave:
                    sql = """
                        UPDATE usuarios
                        SET usuario = %s,
                            password_hash = %s,
                            rol = %s,
                            activo = %s
                        WHERE id = %s
                    """
                    cur.execute(sql, (usuario, clave, rol, activo, id_usuario))
                else:
                    sql = """
                        UPDATE usuarios
                        SET usuario = %s,
                            rol = %s,
                            activo = %s
                        WHERE id = %s
                    """
                    cur.execute(sql, (usuario, rol, activo, id_usuario))

                filas_afectadas = cur.rowcount
            conn.commit()
        return filas_afectadas > 0

    @staticmethod
    def eliminar(id_usuario: int) -> bool:
        """Elimina un usuario por su ID."""
        sql = "DELETE FROM usuarios WHERE id = %s"
        with obtener_conexion() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (id_usuario,))
                filas_afectadas = cur.rowcount
            conn.commit()
        return filas_afectadas > 0
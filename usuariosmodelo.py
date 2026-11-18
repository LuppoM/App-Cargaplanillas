import psycopg2.extras
from conexion import obtener_conexion


def validar_usuario(usuario: str, clave: str):
    """
    Devuelve {"id", "usuario", "rol"} si el usuario existe, está activo
    y la clave coincide. Devuelve None en cualquier otro caso.
    """
    sql = """
        SELECT id, usuario, rol
        FROM usuarios
        WHERE LOWER(usuario) = LOWER(%s)
          AND activo = TRUE
          AND password_hash = crypt(%s, password_hash)
    """
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (usuario.strip(), clave))
            return cur.fetchone()
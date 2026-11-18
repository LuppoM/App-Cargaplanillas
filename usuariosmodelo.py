import psycopg2.extras
from conexion import obtener_conexion


def validar_usuario(usuario: str, clave: str):
    """
    Busca el usuario en la tabla usuarios usando la conexión configurada
    y compara la contraseña directamente.
    """
    usuario_limpio = (usuario or "").strip().lower()
    clave_limpia = (clave or "").strip()

    if not usuario_limpio or not clave_limpia:
        return None

    sql = """
        SELECT id, usuario, password_hash, rol
        FROM usuarios
        WHERE LOWER(TRIM(usuario)) = %s
        LIMIT 1
    """

    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (usuario_limpio,))
            fila = cur.fetchone()

    if not fila:
        return None

    clave_bd = (fila.get("password_hash") or "").strip()

    if clave_bd == clave_limpia:
        return {
            "id": fila["id"],
            "usuario": fila["usuario"],
            "rol": fila["rol"],
        }

    return None
import psycopg2.extras
from conexion import obtener_conexion


def validar_usuario(usuario: str, clave: str):
    """
    Busca el usuario activo en la tabla usuarios, verifica la contraseña
    y devuelve sus datos junto con sus permisos de acceso.
    """
    usuario_limpio = (usuario or "").strip().lower()
    clave_limpia = (clave or "").strip()

    if not usuario_limpio or not clave_limpia:
        return None

    sql = """
        SELECT id, usuario, password_hash, rol, activo,
               puede_leer, puede_crear, puede_editar, puede_eliminar
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

    if fila.get("activo") is False:
        return None

    clave_bd = (fila.get("password_hash") or "").strip()

    if clave_bd == clave_limpia:
        return {
            "id": fila["id"],
            "usuario": fila["usuario"],
            "rol": fila["rol"],
            "puede_leer": bool(fila.get("puede_leer", True)),
            "puede_crear": bool(fila.get("puede_crear", False)),
            "puede_editar": bool(fila.get("puede_editar", False)),
            "puede_eliminar": bool(fila.get("puede_eliminar", False)),
        }

    return None
import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager

# -----------------------------------------------------------------------------
# CADENA DE CONEXIÓN A NEON POSTGRES (POOLED)
# -----------------------------------------------------------------------------
RAW_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_VTaNm6UcG2Wf@ep-still-hat-b51xgwyc-pooler.c-7.us-east-2.aws.neon.tech/produccion?sslmode=require&channel_binding=require",
)

DB_URI = RAW_URI.replace("&channel_binding=require", "").replace("?channel_binding=require", "")

try:
    connection_pool = pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=DB_URI,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )
    print("Conexión exitosa con Neon DB (Pool activado).")
except Exception as e:
    print(f"Error al conectar con Neon DB: {e}")
    connection_pool = None


def _conexion_sigue_viva(conexion) -> bool:
    if conexion is None or conexion.closed != 0:
        return False
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT 1;")
        conexion.rollback()
        return True
    except Exception:
        return False


def _crear_conexion_directa():
    return psycopg2.connect(
        DB_URI,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )


@contextmanager
def obtener_conexion():
    """
    Obtiene una conexión viva de Neon DB y la devuelve o descarta según su estado.
    Si la conexión del pool está cerrada o muerta, abre una nueva automáticamente.
    """
    usada_desde_pool = False
    conexion = None

    if connection_pool is not None:
        try:
            conexion = connection_pool.getconn()
            usada_desde_pool = True
            if not _conexion_sigue_viva(conexion):
                try:
                    connection_pool.putconn(conexion, close=True)
                except Exception:
                    pass
                conexion = _crear_conexion_directa()
                usada_desde_pool = False
        except Exception:
            conexion = _crear_conexion_directa()
            usada_desde_pool = False
    else:
        conexion = _crear_conexion_directa()

    try:
        yield conexion
    except psycopg2.OperationalError:
        if conexion is not None:
            try:
                conexion.rollback()
            except Exception:
                pass
            if usada_desde_pool and connection_pool is not None:
                try:
                    connection_pool.putconn(conexion, close=True)
                    conexion = None
                except Exception:
                    pass
            elif not conexion.closed:
                try:
                    conexion.close()
                except Exception:
                    pass
                conexion = None
        raise
    finally:
        if conexion is not None:
            if usada_desde_pool and connection_pool is not None and conexion.closed == 0:
                try:
                    connection_pool.putconn(conexion)
                except Exception:
                    try:
                        conexion.close()
                    except Exception:
                        pass
            elif not conexion.closed:
                try:
                    conexion.close()
                except Exception:
                    pass


def cerrar_pool():
    """Cierra todas las conexiones activas al salir de la aplicación."""
    if connection_pool:
        connection_pool.closeall()
        print("Pool de conexiones a Neon cerrado.")
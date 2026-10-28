import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager

# -----------------------------------------------------------------------------
# CADENA DE CONEXIÓN A NEON POSTGRES (POOLED)
# -----------------------------------------------------------------------------
# Limpiamos channel_binding para asegurar compatibilidad con psycopg2
RAW_URI = os.getenv(
    "DATABASE_URL", 
    "postgresql://neondb_owner:npg_VTaNm6UcG2Wf@ep-still-hat-b51xgwyc-pooler.c-7.us-east-2.aws.neon.tech/produccion?sslmode=require&channel_binding=require"
)

DB_URI = RAW_URI.replace("&channel_binding=require", "").replace("?channel_binding=require", "")

# Pool de conexiones (Mínimo 1, Máximo 10 conexiones simultáneas)
try:
    connection_pool = pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=DB_URI
    )
    print("Conexión exitosa con Neon DB (Pool activado).")
except Exception as e:
    print(f"Error al conectar con Neon DB: {e}")
    connection_pool = None


@contextmanager
def obtener_conexion():
    """
    Gestor de contexto para obtener y devolver conexiones al pool automáticamente.
    
    Ejemplo de uso:
        with obtener_conexion() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM teoricos LIMIT 5;")
                datos = cursor.fetchall()
    """
    if connection_pool is None:
        raise Exception("El pool de conexiones a la base de datos no está disponible.")
    
    conexion = connection_pool.getconn()
    try:
        yield conexion
    finally:
        connection_pool.putconn(conexion)


def cerrar_pool():
    """Cierra todas las conexiones activas al salir de la aplicación."""
    if connection_pool:
        connection_pool.closeall()
        print("Pool de conexiones a Neon cerrado.")
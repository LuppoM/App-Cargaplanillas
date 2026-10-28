from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from teoricosmodelo import TeoricosModelo

app = FastAPI(title="API Producción - Neon DB")

# Permite peticiones CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URI = os.getenv(
    "DATABASE_URL", 
    "postgresql://neondb_owner:npg_VTaNm6UcG2Wf@ep-still-hat-b51xgwyc-pooler.c-7.us-east-2.aws.neon.tech/produccion?sslmode=require"
)

def get_db_connection():
    try:
        return psycopg2.connect(DB_URI, cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"Error conectando a Neon DB: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión con la base de datos")

# --- ENDPOINTS DE LA API (TEÓRICOS) ---

@app.get("/api/teoricos")
def listar_teoricos():
    return TeoricosModelo.obtener_todos()

@app.get("/api/teoricos/{id_teorico}")
def obtener_teorico(id_teorico: int):
    teorico = TeoricosModelo.obtener_por_id(id_teorico)
    if not teorico:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return teorico

@app.post("/api/teoricos")
def crear_teorico(datos: dict):
    exito = TeoricosModelo.insertar(datos)
    if not exito:
        raise HTTPException(status_code=400, detail="Error al guardar el teórico")
    return {"status": "ok", "message": "Teórico creado correctamente"}

@app.put("/api/teoricos/{id_teorico}")
def actualizar_teorico(id_teorico: int, datos: dict):
    exito = TeoricosModelo.actualizar(id_teorico, datos)
    if not exito:
        raise HTTPException(status_code=400, detail="Error al actualizar el teórico")
    return {"status": "ok", "message": "Teórico actualizado correctamente"}

@app.get("/api/sectores/{sector}")
def obtener_datos_sector(sector: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM teoricos WHERE LOWER(planta) = LOWER(%s) LIMIT 100;", (sector,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

# --- RUTAS PARA SERVIR VISTAS HTML ---

@app.get("/")
def cargar_principal():
    """Sirve la pantalla principal HTML"""
    if os.path.exists("principal.html"):
        return FileResponse("principal.html")
    raise HTTPException(status_code=404, detail="Archivo principal.html no encontrado")

@app.get("/teoricos.html")
def cargar_teoricos_html():
    """Sirve la pantalla completa independiente de teóricos"""
    if os.path.exists("teoricos.html"):
        return FileResponse("teoricos.html")
    raise HTTPException(status_code=404, detail="Archivo teoricos.html no encontrado")

# --- MONTAR ARCHIVOS ESTÁTICOS (DEBE IR SIEMPRE AL FINAL) ---
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
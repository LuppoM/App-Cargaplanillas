from datetime import date
from io import BytesIO
import os
from typing import Optional

from fastapi import Body, FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import conexion
from teoricosmodelo import TeoricosModelo
from sectoresmodelo import SectoresModelo

# En apiproduccion.py
app = FastAPI(title="API PRODUCCIÓN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=BASE_DIR)

# Montar archivos estáticos y assets
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


# ==========================================
# 1. VISTAS HTML PRINCIPALES (RUTAS DIRECTAS)
# ==========================================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Carga la pantalla principal de la aplicación."""
    return templates.TemplateResponse(request, "principal.html", {})



@app.get("/Teoricos", response_class=HTMLResponse)
def home(request: Request):
    """Carga la pantalla principal de la aplicación."""
    return templates.TemplateResponse(request, "teoricos.html", {})

@app.get("/sectores", response_class=HTMLResponse)
def home(request: Request):
    """Carga la pantalla principal de la aplicación."""
    return templates.TemplateResponse(request, "sectores.html", {})


# ==========================================
# 2. MÓDULO: TEÓRICOS (ENDPOINTS DE API)
# ==========================================

@app.get("/api/teoricos")
def obtener_teoricos():
    """Obtiene la lista de teóricos."""
    try:
        datos = TeoricosModelo.obtener_todos()
        return {"status": "ok", "datos": datos}
    except Exception as e:
        print(f"[ERROR GET] /api/teoricos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/teoricos/{id_teorico}")
def obtener_teorico_por_id(id_teorico: int):
    """Obtiene un único teórico por su ID."""
    try:
        teorico = TeoricosModelo.obtener_por_id(id_teorico)
        if not teorico:
            raise HTTPException(status_code=404, detail="Teórico no encontrado")
        return {"status": "ok", "datos": teorico}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR GET] /api/teoricos/{id_teorico}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 2. POST - Crear un nuevo recurso
# ==========================================
@app.post("/api/teoricos")
def crear_teorico(datos: dict = Body(...)):
    """Crea un nuevo registro teórico."""
    try:
        exito = TeoricosModelo.insertar(datos)
        if exito:
            return {"status": "ok", "message": "Teórico creado correctamente."}
        raise HTTPException(status_code=400, detail="No se pudo crear el registro.")
    except Exception as e:
        print(f"[ERROR POST] /api/teoricos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 3. PUT - Actualizar un recurso existente
# ==========================================
@app.put("/api/teoricos/{id_teorico}")
def actualizar_teorico(id_teorico: int, datos: dict = Body(...)):
    """Actualiza completamente un teórico por su ID."""
    try:
        exito = TeoricosModelo.actualizar(id_teorico, datos)
        if exito:
            return {"status": "ok", "message": "Teórico actualizado correctamente."}
        raise HTTPException(status_code=400, detail="No se pudo actualizar el registro.")
    except Exception as e:
        print(f"[ERROR PUT] /api/teoricos/{id_teorico}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 4. DELETE - Eliminar un recurso
# ==========================================
@app.delete("/api/teoricos/{id_teorico}")
def eliminar_teorico(id_teorico: int):
    """Elimina un teórico por su ID."""
    try:
        exito = TeoricosModelo.eliminar(id_teorico)
        if exito:
            return {"status": "ok", "message": "Teórico eliminado correctamente."}
        raise HTTPException(status_code=400, detail="No se pudo eliminar el registro.")
    except Exception as e:
        print(f"[ERROR DELETE] /api/teoricos/{id_teorico}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ==========================================
# 3. MÓDULO: SECTORES (ENDPOINTS DE API)
# ==========================================

@app.get("/api/sectores")
def obtener_sectores():
    """Obtiene la lista completa de sectores."""
    try:
        datos = SectoresModelo.obtener_todos()
        return {"status": "ok", "datos": datos}
    except Exception as e:
        print(f"[ERROR GET] /api/sectores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sectores/{id_sector}")
def obtener_sector_por_id(id_sector: int):
    """Obtiene un único sector por su ID."""
    try:
        sector = SectoresModelo.obtener_por_id(id_sector)
        if not sector:
            raise HTTPException(status_code=404, detail="Sector no encontrado")
        return {"status": "ok", "datos": sector}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR GET] /api/sectores/{id_sector}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sectores")
def crear_sector(datos: dict = Body(...)):
    """Crea un nuevo registro de sector."""
    try:
        exito = SectoresModelo.insertar(datos)
        if exito:
            return {"status": "ok", "message": "Sector creado correctamente."}
        raise HTTPException(status_code=400, detail="No se pudo crear el registro.")
    except Exception as e:
        print(f"[ERROR POST] /api/sectores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/sectores/{id_sector}")
def actualizar_sector(id_sector: int, datos: dict = Body(...)):
    """Actualiza completamente un sector por su ID."""
    try:
        exito = SectoresModelo.actualizar(id_sector, datos)
        if exito:
            return {"status": "ok", "message": "Sector actualizado correctamente."}
        raise HTTPException(status_code=400, detail="No se pudo actualizar el registro.")
    except Exception as e:
        print(f"[ERROR PUT] /api/sectores/{id_sector}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sectores/{id_sector}")
def eliminar_sector(id_sector: int):
    """Elimina un sector por su ID."""
    try:
        exito = SectoresModelo.eliminar(id_sector)
        if exito:
            return {"status": "ok", "message": "Sector eliminado correctamente."}
        raise HTTPException(status_code=400, detail="No se pudo eliminar el registro.")
    except Exception as e:
        print(f"[ERROR DELETE] /api/sectores/{id_sector}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# ==========================================
# 3. MÓDULO: SECTORES 
# ==========================================

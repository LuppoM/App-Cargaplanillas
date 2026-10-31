from datetime import date
from io import BytesIO
import os
from typing import Optional

from fastapi import Body, FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel  # <-- AGREGAR para la validación de planillas

import conexion
from teoricosmodelo import TeoricosModelo
from sectoresmodelo import SectoresModelo
import planillasmodelo  # <-- AGREGAR para la capa de datos de planillas

# En apiproduccion.py
app = FastAPI(title="API PRODUCCIÓN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=BASE_DIR)

# Montar archivos estáticos y assets
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
class PlanillaSchema(BaseModel):
    fecha: date
    planta: str
    centro_trabajo: str
    codigo: str
    turno: str
    dotacion_teorica: float = 0.0
    horas_trabajadas: float = 0.0
    kg_cajas_reales: float = 0.0
    peso_promedio_unid_kg: float = 0.0
    dotacion_real: float = 0.0
    decomiso_kg: float = 0.0
    reproceso_kg: float = 0.0
    scrap_flex_kg: float = 0.0
    detencion_produccion: float = 0.0
    detencion_refrigerio: float = 0.0
    detencion_mecanico: float = 0.0
    detencion_electrico: float = 0.0
    detencion_calidad: float = 0.0
    detencion_programacion: float = 0.0
    detencion_limpieza: float = 0.0
    detencion_abastecimiento: float = 0.0
    detencion_desarrollo: float = 0.0
    detencion_alistamiento: float = 0.0
    detencion_rrhh: float = 0.0
    detencion_suministro: float = 0.0

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

@app.get("/planillas", response_class=HTMLResponse)
def home(request: Request):
    """Carga la pantalla principal de la aplicación."""
    return templates.TemplateResponse(request, "planillas.html", {})



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
# 4. MÓDULO: PLANILLAS 
# ==========================================

# --- ENDPOINTS PLANILLAS ---

@app.get("/api/planillas")
def listar_planillas(planta: Optional[str] = None):
    try:
        registros = planillasmodelo.obtener_planillas(planta)
        return {"ok": True, "datos": registros}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar planillas: {str(e)}")

@app.get("/api/planillas/{planilla_id}")
def obtener_planilla(planilla_id: int):
    registro = planillasmodelo.obtener_planilla_por_id(planilla_id)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro de planilla no encontrado")
    return {"ok": True, "datos": registro}

@app.post("/api/planillas")
def crear_planilla(payload: PlanillaSchema):
    try:
        nuevo_id = planillasmodelo.insertar_planilla(payload.dict())
        return {"ok": True, "id": nuevo_id, "mensaje": "Planilla registrada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar la planilla: {str(e)}")

@app.put("/api/planillas/{planilla_id}")
def modificar_planilla(planilla_id: int, payload: PlanillaSchema):
    registro = planillasmodelo.obtener_planilla_por_id(planilla_id)
    if not registro:
        raise HTTPException(status_code=404, detail="El registro a actualizar no existe")
    
    try:
        planillasmodelo.actualizar_planilla(planilla_id, payload.dict())
        return {"ok": True, "mensaje": "Planilla actualizada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar la planilla: {str(e)}")

@app.delete("/api/planillas/{planilla_id}")
def borrar_planilla(planilla_id: int):
    registro = planillasmodelo.obtener_planilla_por_id(planilla_id)
    if not registro:
        raise HTTPException(status_code=404, detail="El registro a eliminar no existe")
    
    try:
        planillasmodelo.eliminar_planilla(planilla_id)
        return {"ok": True, "mensaje": "Planilla eliminada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al borrar la planilla: {str(e)}")

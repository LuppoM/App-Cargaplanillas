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

app = FastAPI(title="API PRODUCCIÓN - PLANILLAS Y TEÓRICOS")

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



@app.get("/teoricos", response_class=HTMLResponse)
def vista_teoricos(request: Request):
    """Carga la pantalla independiente de Teóricos."""
    ruta_html = os.path.join(BASE_DIR, "teoricos.html")

    return templates.TemplateResponse("teoricos.html", {"request": request})
  


# ==========================================
# 2. MÓDULO: TEÓRICOS (ENDPOINTS DE API)
# ==========================================

@app.get("/api/teoricos/datos")
@app.get("/api/teoricos")
def api_obtener_teoricos():
    """Retorna la lista completa de teóricos desde el modelo."""
    try:
        datos = TeoricosModelo.obtener_todos()
        return {"status": "ok", "datos": datos}
    except Exception as e:
        print(f"Error en /api/teoricos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/teoricos/obtener/{id_teorico}")
@app.get("/api/teoricos/{id_teorico}")
def api_obtener_teorico_por_id(id_teorico: int):
    """Obtiene un registro teórico individual por su ID."""
    try:
        teorico = TeoricosModelo.obtener_por_id(id_teorico)
        if not teorico:
            return {"status": "error", "mensaje": "Teórico no encontrado"}
        return {"status": "ok", "data": teorico}
    except Exception as e:
        print(f"Error obteniendo teórico {id_teorico}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/teoricos/guardar")
@app.post("/api/teoricos")
def api_guardar_teorico(payload: dict = Body(...)):
    """Crea un nuevo registro o actualiza uno existente según contenga 'id'."""
    id_reg = payload.get("id") or payload.get("datos", {}).get("id")
    datos = payload.get("datos", payload)

    try:
        if id_reg:
            exito = TeoricosModelo.actualizar(int(id_reg), datos)
            msg_error = "No se pudo actualizar el teórico en la base de datos."
        else:
            exito = TeoricosModelo.insertar(datos)
            msg_error = "No se pudo insertar el teórico en la base de datos."

        if exito:
            return {"status": "ok", "message": "Registro guardado correctamente."}
        return {"status": "error", "message": msg_error}
    except Exception as e:
        print(f"Error en guardar teórico: {e}")
        return {"status": "error", "message": str(e)}


@app.put("/api/teoricos/{id_teorico}")
def api_actualizar_teorico_put(id_teorico: int, payload: dict = Body(...)):
    """Endpoint PUT tradicional para actualizar teóricos."""
    try:
        exito = TeoricosModelo.actualizar(id_teorico, payload)
        if exito:
            return {"status": "ok", "message": "Teórico actualizado correctamente."}
        return {"status": "error", "message": "Error al actualizar registro."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/sectores/{sector}")
def api_obtener_datos_sector(sector: str):
    """Consulta teóricos filtrados por planta/sector."""
    try:
        conn = conexion.obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM teoricos WHERE LOWER(planta) = LOWER(%s) LIMIT 100;", (sector,))
        datos = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"status": "ok", "datos": datos}
    except Exception as e:
        print(f"Error obteniendo sector {sector}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
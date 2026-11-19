from datetime import date
from io import BytesIO
import os
from typing import Optional

from fastapi import Body, FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel  # <-- AGREGAR para la validación de planillas
from fastapi.responses import StreamingResponse
import nivelestanquepdf
from nivelestanquepdf import generar_pdf_planilla_blanca
import conexion
from teoricosmodelo import TeoricosModelo
from sectoresmodelo import SectoresModelo
import planillasmodelo  # <-- AGREGAR para la capa de datos de planillas
import nivelestanquemodelo
from pydantic import BaseModel
import usuariosmodelo
import abmusuariosmodelo
import cantidadentanques
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


# En apiproduccion.py
app = FastAPI(title="API PRODUCCIÓN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=BASE_DIR)
SECRET_KEY = os.getenv("SECRET_KEY", "palmesano-clave-secreta-produccion-2026")
COOKIE_NAME = "sesion_produccion"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 horas
signer = URLSafeTimedSerializer(SECRET_KEY)


def obtener_usuario_actual(request: Request):
    """Lee y verifica la cookie firmada. Devuelve dict {id, usuario, rol} o None."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        return signer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

from typing import Optional, List

class DetencionItemSchema(BaseModel):
    taller: str
    descripcion: Optional[str] = ""
    horas: float = 0.0

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
    detenciones: Optional[List[DetencionItemSchema]] = []
class TanqueDetalleSchema(BaseModel):
    tanque: str
    codigo: Optional[str] = ""
    descripcion: Optional[str] = ""
    valor_medido: Optional[float] = None
    nro_conca: Optional[int] = None
    kg_manual: Optional[float] = None

class RelevamientoTanqueSchema(BaseModel):
    fecha_hora: Optional[str] = None
    supervisor: str
    operario: str
    detalles: List[TanqueDetalleSchema] = []
class LoginSchema(BaseModel):
    usuario: str
    clave: str
# ==========================================
# 1. VISTAS HTML PRINCIPALES (RUTAS DIRECTAS)
# ==========================================
@app.get("/login", response_class=HTMLResponse)
def vista_login(request: Request):
    """Carga la pantalla de ingreso."""
    return templates.TemplateResponse(request, "login.html", {})

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Carga la pantalla principal de la aplicación."""
    return templates.TemplateResponse(request, "principal.html", {})

@app.get("/Teoricos", response_class=HTMLResponse)
def vista_teoricos(request: Request):
    return templates.TemplateResponse(request, "teoricos.html", {})

@app.get("/sectores", response_class=HTMLResponse)
def vista_sectores(request: Request):
    return templates.TemplateResponse(request, "sectores.html", {})

@app.get("/planillas", response_class=HTMLResponse)
def vista_planillas(request: Request):
    return templates.TemplateResponse(request, "planillas.html", {})

@app.get("/ntanque", response_class=HTMLResponse)
def vista_ntanque(request: Request):
    return templates.TemplateResponse(request, "nivelestanque.html", {})

@app.get("/abmusuarios", response_class=HTMLResponse)
def vista_ntanque(request: Request):
    return templates.TemplateResponse(request, "abmusuarios.html", {})

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
        # Pydantic v2 usa model_dump(), mantengo dict() con fallback por compatibilidad
        datos_dict = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
        nuevo_id = planillasmodelo.insertar_planilla(datos_dict)
        return {"ok": True, "id": nuevo_id, "mensaje": "Planilla registrada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar la planilla: {str(e)}")

@app.put("/api/planillas/{planilla_id}")
def modificar_planilla(planilla_id: int, payload: PlanillaSchema):
    registro = planillasmodelo.obtener_planilla_por_id(planilla_id)
    if not registro:
        raise HTTPException(status_code=404, detail="El registro a actualizar no existe")
    
    try:
        datos_dict = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
        planillasmodelo.actualizar_planilla(planilla_id, datos_dict)
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
    
   # --- ENDPOINTS NIVELES TANQUE ---


# --- ENDPOINTS NIVELES TANQUE ---
# Las rutas fijas (codigos, pdf/blanco) van antes que las de parametro ({relevamiento_id})

@app.get("/api/ntanque")
def listar_relevamientos_tanques():
    try:
        registros = nivelestanquemodelo.obtener_relevamientos()
        return {"ok": True, "datos": registros}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar relevamientos: {str(e)}")


@app.get("/api/ntanque/codigos")
def listar_codigos_tanques():
    try:
        datos = nivelestanquemodelo.obtener_codigos_tanques()
        return {"ok": True, "datos": datos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar códigos: {str(e)}")


@app.get("/api/ntanque/pdf/blanco")
def imprimir_planilla_tanques_blanca():
    pdf_buffer = generar_pdf_planilla_blanca()
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="Planilla_Tanques_Blanco.pdf"'},
    )


@app.get("/api/ntanque/{relevamiento_id}")
def obtener_relevamiento_tanque(relevamiento_id: int):
    registro = nivelestanquemodelo.obtener_relevamiento_por_id(relevamiento_id)
    if not registro:
        raise HTTPException(status_code=404, detail="Relevamiento de tanques no encontrado")
    return {"ok": True, "datos": registro}


@app.get("/api/ntanque/{relevamiento_id}/pdf")
def imprimir_relevamiento_tanques(relevamiento_id: int):
    reg = nivelestanquemodelo.obtener_relevamiento_por_id(relevamiento_id)
    if not reg:
        raise HTTPException(status_code=404, detail="Relevamiento no encontrado")

    pdf_buffer = nivelestanquepdf.generar_pdf_relevamiento(reg)
    filename = f"Planilla_Tanques_{relevamiento_id}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.post("/api/ntanque")
def crear_relevamiento_tanque(payload: RelevamientoTanqueSchema):
    try:
        datos_dict = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
        nuevo_id = nivelestanquemodelo.insertar_relevamiento(datos_dict)
        return {"ok": True, "id": nuevo_id, "mensaje": "Relevamiento registrado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar el relevamiento: {str(e)}")


@app.put("/api/ntanque/{relevamiento_id}")
def modificar_relevamiento_tanque(relevamiento_id: int, payload: RelevamientoTanqueSchema):
    registro = nivelestanquemodelo.obtener_relevamiento_por_id(relevamiento_id)
    if not registro:
        raise HTTPException(status_code=404, detail="El relevamiento a actualizar no existe")

    try:
        datos_dict = payload.model_dump() if hasattr(payload, 'model_dump') else payload.dict()
        nivelestanquemodelo.actualizar_relevamiento(relevamiento_id, datos_dict)
        return {"ok": True, "mensaje": "Relevamiento actualizado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar el relevamiento: {str(e)}")


@app.delete("/api/ntanque/{relevamiento_id}")
def borrar_relevamiento_tanque(relevamiento_id: int):
    registro = nivelestanquemodelo.obtener_relevamiento_por_id(relevamiento_id)
    if not registro:
        raise HTTPException(status_code=404, detail="El relevamiento a eliminar no existe")

    try:
        nivelestanquemodelo.eliminar_relevamiento(relevamiento_id)
        return {"ok": True, "mensaje": "Relevamiento eliminado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al borrar el relevamiento: {str(e)}")
    
@app.get("/api/ntanque/pdf/cantidad/{id_relevamiento}")
def pdf_cantidad_tanques(id_relevamiento: int):
    try:
        relevamiento = nivelestanquemodelo.obtener_relevamiento_por_id(id_relevamiento)
        if not relevamiento:
            raise HTTPException(status_code=404, detail="Relevamiento no encontrado")

        pdf_bytes = cantidadentanques.generar_pdf_cantidad(relevamiento)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=cantidad_tanques_{id_relevamiento}.pdf"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar PDF: {str(e)}")
    

# --- ENDPOINTS USUARIOS Y SESIÓN ---

# --- ENDPOINTS USUARIOS ---

class UsuarioAbmSchema(BaseModel):
    usuario: str
    clave: Optional[str] = ""
    rol: str
    activo: bool = True


@app.post("/api/login")
def login(payload: LoginSchema):
    try:
        user = usuariosmodelo.validar_usuario(payload.usuario, payload.clave)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al validar el usuario: {str(e)}")

    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    return {
        "ok": True,
        "id": user["id"],
        "usuario": user["usuario"],
        "rol": user["rol"],
    }


@app.get("/api/usuarios")
def listar_usuarios():
    try:
        datos = abmusuariosmodelo.obtener_todos()
        return {"ok": True, "datos": datos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar usuarios: {str(e)}")


@app.get("/api/usuarios/{id_usuario}")
def obtener_usuario(id_usuario: int):
    try:
        user = abmusuariosmodelo.obtener_por_id(id_usuario)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return {"ok": True, "datos": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener usuario: {str(e)}")


@app.post("/api/usuarios")
def crear_usuario(payload: UsuarioAbmSchema):
    try:
        datos_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        nuevo_id = abmusuariosmodelo.insertar(datos_dict)
        return {"ok": True, "id": nuevo_id, "message": "Usuario creado correctamente."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear usuario: {str(e)}")


@app.put("/api/usuarios/{id_usuario}")
def actualizar_usuario(id_usuario: int, payload: UsuarioAbmSchema):
    try:
        datos_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        exito = abmusuariosmodelo.actualizar(id_usuario, datos_dict)
        if not exito:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        return {"ok": True, "message": "Usuario actualizado correctamente."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar usuario: {str(e)}")


@app.delete("/api/usuarios/{id_usuario}")
def eliminar_usuario(id_usuario: int):
    try:
        exito = abmusuariosmodelo.eliminar(id_usuario)
        if not exito:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        return {"ok": True, "message": "Usuario eliminado correctamente."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar usuario: {str(e)}")
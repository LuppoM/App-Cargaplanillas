import requests
from typing import List, Dict, Any, Optional

class PrincipalModelo:
    def __init__(self, api_url: str = "http://localhost:8000/api"):
        self.api_url = api_url.rstrip('/')

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Método auxiliar para realizar peticiones GET a la API."""
        try:
            response = requests.get(f"{self.api_url}{endpoint}", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR MODELO] Fallo la consulta GET a {endpoint}: {e}")
            return None

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Optional[Any]:
        """Método auxiliar para realizar peticiones POST a la API."""
        try:
            response = requests.post(f"{self.api_url}{endpoint}", json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR MODELO] Fallo el envío POST a {endpoint}: {e}")
            return None

    # --- CONSULTAS DE TEÓRICOS ---
    def obtener_teoricos(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene la lista de teóricos guardados en la BD a través de la API."""
        resultado = self._get("/teoricos", params={"limit": limit})
        return resultado if resultado is not None else []

    def buscar_teorico_por_codigo(self, codigo: str) -> Optional[Dict[str, Any]]:
        """Busca un teórico específico por su código de producto."""
        return self._get(f"/teoricos/{codigo}")

    # --- CONSULTAS POR SECTOR ---
    def obtener_datos_sector(self, sector: str) -> List[Dict[str, Any]]:
        """Obtiene los registros filtrados por sector/planta (ej: chocolate, golosinas)."""
        resultado = self._get(f"/sectores/{sector}")
        return resultado if resultado is not None else []

    # --- CARGA Y GUARDADO DE PLANILLAS ---
    def guardar_planilla_diaria(self, datos_planilla: Dict[str, Any]) -> bool:
        """Envía los datos de una planilla cargada para guardarse en Neon DB."""
        respuesta = self._post("/planillas/diaria", payload=datos_planilla)
        return respuesta is not None and respuesta.get("status") == "success"

    # --- PARÁMETROS ---
    def obtener_parametros(self, tipo_parametro: str) -> Dict[str, Any]:
        """Consulta los parámetros configurados (líneas, eficiencias, dotaciones)."""
        resultado = self._get(f"/parametros/{tipo_parametro}")
        return resultado if resultado is not None else {}


# Instancia directa para importar en otros módulos
modelo = PrincipalModelo()

if __name__ == "__main__":
    # Prueba rápida de comunicación entre modelo y API
    print("Probando conexión del modelo con la API...")
    teoricos = modelo.obtener_teoricos(limit=5)
    print(f"Teóricos obtenidos ({len(teoricos)}):", teoricos)
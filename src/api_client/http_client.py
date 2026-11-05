"""Cliente HTTP para la API RESTful de AutoRent Pro.

Soporta tanto conexión remota mediante `httpx.Client(base_url=...)` como ejecución
en memoria mediante `fastapi.testclient.TestClient(app)` para pruebas de integración
y entornos desacoplados, adjuntando automáticamente el token JWT Bearer.
"""

from typing import Any, Optional

import httpx

from src.config.settings import get_settings


class ApiClientError(Exception):
    """Excepción estructurada para errores devueltos por la API RESTful de AutoRent Pro."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
    ) -> None:
        super().__init__(f"[{status_code} {code}] {message}")
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class AutoRentApiClient:
    """Cliente HTTP de alto nivel para interactuar con los endpoints de AutoRent Pro API v1."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        app: Any = None,
        timeout: Optional[float] = None,
    ) -> None:
        api_cfg = get_settings().api
        resolved_url = base_url if base_url is not None else api_cfg.base_url
        resolved_timeout = timeout if timeout is not None else api_cfg.timeout
        self.base_url = resolved_url.rstrip("/")
        self.timeout = resolved_timeout
        self.access_token: Optional[str] = None
        self.current_user: Optional[dict] = None
        self.tenant_id: Optional[int] = None

        if app is not None:
            from fastapi.testclient import TestClient

            self._client: Any = TestClient(app)
        else:
            self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Ejecuta una petición HTTP inyectando el encabezado Authorization Bearer si existe."""
        headers = dict(kwargs.pop("headers", {}) or {})
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        response = self._client.request(method, path, headers=headers, **kwargs)

        if response.status_code >= 400:
            code = "HTTP_ERROR"
            message = response.text or f"HTTP {response.status_code}"
            details: Any = None
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    detail = payload.get("detail", payload)
                    if isinstance(detail, dict):
                        code = str(detail.get("code", code))
                        message = str(detail.get("message", message))
                        details = detail.get("details")
                    elif isinstance(detail, list):
                        code = "VALIDATION_ERROR"
                        message = "Error de validación en los parámetros de entrada."
                        details = detail
                    elif isinstance(detail, str):
                        message = detail
                        if "code" in payload:
                            code = str(payload["code"])
            except Exception:
                pass

            raise ApiClientError(
                status_code=response.status_code,
                code=code,
                message=message,
                details=details,
            )

        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    # -------------------------------------------------------------------------
    # INFRAESTRUCTURA Y AUTENTICACIÓN
    # -------------------------------------------------------------------------

    def health_check(self) -> dict:
        """Verifica el estado de salud del servidor API (`GET /health`)."""
        return self._request("GET", "/health")

    def list_agencies(self, only_active: bool = True) -> list[dict]:
        """Lista las agencias registradas (`GET /api/v1/auth/agencies`)."""
        return self._request(
            "GET",
            "/api/v1/auth/agencies",
            params={"only_active": only_active},
        )

    def login(self, username: str, password: str, tenant_id: int) -> dict:
        """Autentica al usuario en una agencia y almacena el JWT (`POST /api/v1/auth/login`)."""
        data = self._request(
            "POST",
            "/api/v1/auth/login",
            json={
                "username": username,
                "password": password,
                "tenant_id": tenant_id,
            },
        )
        self.access_token = data.get("access_token")
        self.current_user = data.get("user")
        if isinstance(self.current_user, dict) and "tenant_id" in self.current_user:
            self.tenant_id = int(self.current_user["tenant_id"])
        else:
            self.tenant_id = int(tenant_id)
        return data

    def get_me(self) -> dict:
        """Retorna el perfil del usuario autenticado (`GET /api/v1/auth/me`)."""
        return self._request("GET", "/api/v1/auth/me")

    def logout(self) -> dict:
        """Cierra la sesión actual y limpia las credenciales en memoria (`POST /api/v1/auth/logout`)."""
        try:
            result = self._request("POST", "/api/v1/auth/logout")
        finally:
            self.access_token = None
            self.current_user = None
            self.tenant_id = None
        return result

    # -------------------------------------------------------------------------
    # CLIENTES
    # -------------------------------------------------------------------------

    def list_clients(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict]:
        """Lista los clientes de la agencia activa (`GET /api/v1/clients`)."""
        params: dict[str, Any] = {}
        if search is not None:
            params["search"] = search
        if status is not None:
            params["status"] = status
        return self._request("GET", "/api/v1/clients", params=params)

    def get_client(self, id_cliente: int) -> dict:
        """Consulta un cliente por su ID (`GET /api/v1/clients/{id_cliente}`)."""
        return self._request("GET", f"/api/v1/clients/{id_cliente}")

    def create_client(self, payload: dict) -> dict:
        """Registra un nuevo cliente en la agencia activa (`POST /api/v1/clients`)."""
        return self._request("POST", "/api/v1/clients", json=payload)

    # -------------------------------------------------------------------------
    # FLOTA VEHICULAR
    # -------------------------------------------------------------------------

    def list_vehicles(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict]:
        """Lista los vehículos de la agencia activa (`GET /api/v1/vehicles`)."""
        params: dict[str, Any] = {}
        if search is not None:
            params["search"] = search
        if status is not None:
            params["status"] = status
        return self._request("GET", "/api/v1/vehicles", params=params)

    def get_vehicle(self, id_vehiculo: int) -> dict:
        """Consulta el detalle de un vehículo (`GET /api/v1/vehicles/{id_vehiculo}`)."""
        return self._request("GET", f"/api/v1/vehicles/{id_vehiculo}")

    def create_vehicle(self, payload: dict) -> dict:
        """Registra un nuevo vehículo en la agencia activa (`POST /api/v1/vehicles`)."""
        return self._request("POST", "/api/v1/vehicles", json=payload)

    def list_categories(self) -> list[dict]:
        """Lista las categorías tarifarias de la agencia activa (`GET /api/v1/vehicles/categories`)."""
        return self._request("GET", "/api/v1/vehicles/categories")

    def list_models(self, id_marca: Optional[int] = None) -> list[dict]:
        """Lista el catálogo de modelos de vehículos (`GET /api/v1/vehicles/models`)."""
        params: dict[str, Any] = {}
        if id_marca is not None:
            params["id_marca"] = id_marca
        return self._request("GET", "/api/v1/vehicles/models", params=params)

    # -------------------------------------------------------------------------
    # RESERVAS, CONTRATOS Y TALLER
    # -------------------------------------------------------------------------

    def list_reservations(self) -> list[dict]:
        """Lista las reservaciones de la agencia activa (`GET /api/v1/reservations`)."""
        return self._request("GET", "/api/v1/reservations")

    def list_contracts(self) -> list[dict]:
        """Lista los contratos de arrendamiento de la agencia activa (`GET /api/v1/contracts`)."""
        return self._request("GET", "/api/v1/contracts")

    def get_contract_document_html(self, id_contrato: int) -> dict:
        """Genera el documento HTML imprimible del contrato (`GET /api/v1/contracts/{id_contrato}/document-html`)."""
        return self._request("GET", f"/api/v1/contracts/{id_contrato}/document-html")

    def list_maintenances(self) -> list[dict]:
        """Lista las órdenes de mantenimiento de la agencia activa (`GET /api/v1/maintenances`)."""
        return self._request("GET", "/api/v1/maintenances")

    # -------------------------------------------------------------------------
    # REPORTES Y ADMINISTRACIÓN
    # -------------------------------------------------------------------------

    def get_financial_report(self) -> dict:
        """Obtiene el reporte financiero ejecutivo (`GET /api/v1/reports/financial`)."""
        return self._request("GET", "/api/v1/reports/financial")

    def get_fleet_report(self) -> dict:
        """Obtiene el reporte de utilización de flota (`GET /api/v1/reports/fleet`)."""
        return self._request("GET", "/api/v1/reports/fleet")

    def list_users(self) -> list[dict]:
        """Lista los usuarios de la agencia activa (`GET /api/v1/users`)."""
        return self._request("GET", "/api/v1/users")

    def close(self) -> None:
        """Cierra la conexión subyacente del cliente HTTP."""
        if hasattr(self._client, "close"):
            self._client.close()

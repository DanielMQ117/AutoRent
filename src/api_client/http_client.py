"""Cliente HTTP para la API RESTful de AutoRent Pro.

Soporta tanto conexión remota mediante `httpx.Client(base_url=...)` como ejecución
en memoria mediante `fastapi.testclient.TestClient(app)` para pruebas de integración
y entornos desacoplados, adjuntando automáticamente el token JWT Bearer y mapeando
respuestas JSON a las entidades de dominio (`src/domain/models.py`).
"""

import dataclasses
import types
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from functools import lru_cache, partial
from typing import Any, NoReturn, Optional, Union, get_args, get_origin, get_type_hints

import httpx

from src.config.settings import get_settings
from src.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleViolationError,
    DatabaseConnectionError,
    DatabaseError,
    DuplicateRecordError,
    ExclusionViolationError,
    InvalidStateTransitionError,
    RecordNotFoundError,
    ValidationError,
)
from src.domain.models import (
    AdditionalDriver,
    Agency,
    AuditLog,
    Brand,
    Client,
    ClientHistoryItem,
    ClientHistorySummary,
    Contract,
    Damage,
    DriverLicense,
    FinancialReportItem,
    FinancialReportSummary,
    FleetUtilizationItem,
    FleetUtilizationSummary,
    InsuranceCoverage,
    Maintenance,
    Payment,
    Reservation,
    ReturnInspection,
    Role,
    Settlement,
    User,
    Vehicle,
    VehicleCategory,
    VehicleModel,
)

# =============================================================================
# CONVERSIÓN DE TIPOS (JSON <-> PYTHON)
# =============================================================================


def _parse_date(val: Any) -> Optional[date]:
    """Convierte un valor ISO string o datetime en un objeto `date`."""
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return date.fromisoformat(str(val).strip().split("T", 1)[0])


def _parse_datetime(val: Any) -> Optional[datetime]:
    """Convierte un valor ISO string en un objeto `datetime` naive."""
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=None)
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day)
    s = str(val).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).replace(tzinfo=None)


def _to_iso(val: Any) -> Optional[str]:
    """Serializa una fecha/fecha-hora a ISO-8601 aceptando también cadenas ya formateadas."""
    if val is None:
        return None
    return val.isoformat() if isinstance(val, (date, datetime)) else str(val)


def _params(**kwargs: Any) -> dict[str, Any]:
    """Construye los query params descartando valores `None` y serializando fechas a ISO-8601."""
    return {
        k: _to_iso(v) if isinstance(v, (date, datetime)) else v
        for k, v in kwargs.items()
        if v is not None
    }


def _coerce(tp: Any, val: Any) -> Any:
    """Convierte un valor JSON al tipo anotado en el dataclass (soporta Optional, list y anidados)."""
    if val is None:
        return None
    origin = get_origin(tp)
    if origin in (Union, types.UnionType):
        inner = [a for a in get_args(tp) if a is not type(None)]
        return _coerce(inner[0], val) if len(inner) == 1 else val
    if origin is list:
        (item_tp,) = get_args(tp) or (Any,)
        return [_coerce(item_tp, v) for v in val or []]
    if dataclasses.is_dataclass(tp):
        return _from_dict(tp, val) if isinstance(val, dict) else None
    if tp is datetime:
        return _parse_datetime(val)
    if tp is date:
        return _parse_date(val)
    if tp is Decimal:
        return val if isinstance(val, Decimal) else Decimal(str(val))
    if isinstance(tp, type) and issubclass(tp, Enum):
        return tp(val)
    if tp is bool:
        return bool(val)
    if tp in (int, float):
        return tp(val)
    if tp is str:
        return val if isinstance(val, (dict, list)) else str(val)
    return val


@lru_cache(maxsize=None)
def _field_types(model: type) -> dict[str, Any]:
    """Obtiene (y cachea) los tipos anotados de los campos inicializables de un dataclass."""
    hints = get_type_hints(model)
    return {f.name: hints[f.name] for f in dataclasses.fields(model) if f.init}


def _from_dict(model: type, data: dict) -> Any:
    """Mapea genéricamente un diccionario JSON a un dataclass de dominio usando sus anotaciones.

    Las claves ausentes o con valor `None` conservan el valor por defecto del dataclass,
    salvo en campos `Optional`, donde `None` es un valor válido.
    """
    kwargs: dict[str, Any] = {}
    for name, tp in _field_types(model).items():
        if name not in data:
            continue
        value = _coerce(tp, data[name])
        if value is None and type(None) not in get_args(tp):
            continue
        kwargs[name] = value
    return model(**kwargs)


# =============================================================================
# EXCEPCIONES HTTP -> DOMINIO
# =============================================================================

_AUTH_CODES = frozenset({
    "NO_ACTIVE_TENANT", "INVALID_OR_EXPIRED_TOKEN", "TENANT_NOT_FOUND", "TENANT_DISABLED",
    "USER_NOT_FOUND", "USER_DISABLED", "USER_ID_MISSING", "ACCOUNT_LOCKED",
    "INVALID_PASSWORD", "AUTHENTICATION_REQUIRED",
})

_STATE_TRANSITION_CODES = frozenset({
    "CANNOT_OVERRIDE_RENTED_STATUS", "INVALID_TRANSITION_WORKSHOP_TO_RENTED",
    "CANNOT_MODIFY_TERMINATED_RESERVATION", "INVALID_CONFIRMATION_STATE",
    "CANNOT_CANCEL_RESERVATION", "CANNOT_CONVERT_UNCONFIRMED_RESERVATION",
    "CANNOT_CANCEL_NON_ACTIVE_CONTRACT", "INVALID_CONTRACT_STATUS_FOR_RETURN",
    "MAINTENANCE_NOT_IN_WORKSHOP", "MAINTENANCE_CANNOT_BE_CANCELLED",
})

_BUSINESS_RULE_CODES = frozenset({
    "CLIENT_HAS_ACTIVE_COMMITMENTS", "CLIENT_HAS_HISTORICAL_RECORDS",
    "VEHICLE_HAS_ACTIVE_COMMITMENTS", "CLIENT_BANNED", "CLIENT_IN_DEBT",
    "EXPIRED_LICENSE_FOR_RESERVATION", "CLIENT_NO_LICENSE", "VEHICLE_AVAILABILITY_CONFLICT",
    "EXPIRED_LICENSE_FOR_CONTRACT", "EXPIRED_ADDITIONAL_DRIVER_LICENSE",
    "VEHICLE_DECOMMISSIONED", "VEHICLE_IN_MAINTENANCE", "VEHICLE_NOT_AVAILABLE",
    "VEHICLE_CONTRACT_CONFLICT", "INVALID_ODOMETER_VALUE", "RETURN_BEFORE_DEPARTURE",
    "INVALID_RETURN_ODOMETER", "NEGATIVE_DAMAGE_COST", "CONTRACT_ALREADY_RETURNED",
    "VEHICLE_CURRENTLY_RENTED", "MAINTENANCE_ALREADY_ACTIVE",
})


class ApiClientError(AppException):
    """Excepción estructurada para errores devueltos por la API RESTful de AutoRent Pro."""

    def __init__(self, status_code: int, code: str, message: str, details: Any = None) -> None:
        """Inicializa la excepción HTTP conservando el código de estado, código de dominio y mensaje."""
        super().__init__(message=message, code=code, details=details)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details

    def __str__(self) -> str:
        """Retorna la representación legible del error HTTP de la API."""
        return f"[{self.status_code} {self.code}] {self.message}"

    def to_domain_exception(self) -> AppException:
        """Traduce el error HTTP de la API a la excepción específica del dominio o persistencia."""
        code, status = (self.code or "").upper(), self.status_code

        if status == 404 and code == "USER_NOT_FOUND":
            exc_cls: type[AppException] = RecordNotFoundError
        elif status == 401 or code in _AUTH_CODES:
            exc_cls = AuthenticationError
        elif status == 403 or code == "PERMISSION_DENIED":
            exc_cls = AuthorizationError
        elif status == 404 or code.endswith("_NOT_FOUND"):
            exc_cls = RecordNotFoundError
        elif status == 409 or code.startswith("DUPLICATE_"):
            is_exclusion = "EXCLUSION" in code or "OVERBOOKING" in code
            exc_cls = ExclusionViolationError if is_exclusion else DuplicateRecordError
        elif code in _STATE_TRANSITION_CODES or "TRANSITION" in code:
            exc_cls = InvalidStateTransitionError
        elif code in _BUSINESS_RULE_CODES:
            exc_cls = BusinessRuleViolationError
        elif status >= 500:
            exc_cls = DatabaseError
        else:
            exc_cls = ValidationError
        return exc_cls(message=self.message, code=self.code, details=self.details)


def _build_api_error(response: Any) -> ApiClientError:
    """Construye un `ApiClientError` a partir de una respuesta HTTP con código >= 400."""
    code, message, details = "HTTP_ERROR", response.text or f"HTTP {response.status_code}", None
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        detail = payload.get("detail", payload)
        if isinstance(detail, dict):
            code = str(detail.get("code", code))
            message = str(detail.get("message", message))
            details = detail.get("details")
        elif isinstance(detail, list):
            code, message, details = "VALIDATION_ERROR", "Error de validación en los parámetros de entrada.", detail
        elif isinstance(detail, str):
            message = detail
            code = str(payload.get("code", code))
    return ApiClientError(status_code=response.status_code, code=code, message=message, details=details)


# =============================================================================
# CLIENTE HTTP
# =============================================================================


class AutoRentApiClient:
    """Cliente HTTP de alto nivel para interactuar con los endpoints de AutoRent Pro API v1."""

    def __init__(self, base_url: Optional[str] = None, app: Any = None, timeout: Optional[float] = None) -> None:
        """Inicializa el cliente HTTP con soporte para modo servidor remoto o cliente de pruebas ASGI."""
        api_cfg = get_settings().api
        self.base_url = (base_url if base_url is not None else api_cfg.base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else api_cfg.timeout
        self.access_token: Optional[str] = None
        self.current_user: Optional[dict] = None
        self.tenant_id: Optional[int] = None
        self.remote_mode: bool = False

        if app is not None:
            from fastapi.testclient import TestClient

            self._client: Any = TestClient(app)
        else:
            self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def enable_remote_mode(self, enabled: bool = True) -> None:
        """Activa o desactiva el modo cliente HTTP puro para que los servicios consuman la API remota."""
        self.remote_mode = bool(enabled)

    def raise_domain_exception(self, err: ApiClientError) -> NoReturn:
        """Relanza un `ApiClientError` traducido a la excepción de dominio correspondiente."""
        raise err.to_domain_exception() from err

    def close(self) -> None:
        """Cierra la conexión subyacente del cliente HTTP."""
        if hasattr(self._client, "close"):
            self._client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Ejecuta una petición HTTP inyectando el encabezado Authorization Bearer si existe."""
        headers = dict(kwargs.pop("headers", None) or {})
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            response = self._client.request(method, path, headers=headers, **kwargs)
        except httpx.RequestError as exc:
            raise DatabaseConnectionError(
                message=(
                    f"No se pudo conectar con el servidor API ({self.base_url}). "
                    "Asegúrese de levantar primero el servidor ejecutando: "
                    "uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
                ),
                code="API_SERVER_UNREACHABLE",
                details=str(exc),
            ) from exc

        if response.status_code >= 400:
            raise _build_api_error(response)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def _get(self, path: str, **params: Any) -> Any:
        """Atajo para `GET` con query params opcionales (se omiten los `None`)."""
        return self._request("GET", path, params=_params(**params))

    def _post(self, path: str, json: Any = None) -> Any:
        """Atajo para `POST` con cuerpo JSON opcional."""
        return self._request("POST", path, json=json)

    # =========================================================================
    # 1. INFRAESTRUCTURA Y AUTENTICACIÓN (/api/v1/auth)
    # =========================================================================

    def health_check(self) -> dict:
        """Verifica el estado de salud del servidor API (`GET /health`)."""
        return self._get("/health")

    def list_agencies(self, only_active: bool = True) -> list[dict]:
        """Lista las agencias registradas (`GET /api/v1/auth/agencies`)."""
        return self._get("/api/v1/auth/agencies", only_active=only_active)

    def login(self, username: str, password: str, tenant_id: int) -> dict:
        """Autentica al usuario en una agencia y almacena el JWT (`POST /api/v1/auth/login`)."""
        data = self._post(
            "/api/v1/auth/login",
            {"username": username, "password": password, "tenant_id": int(tenant_id)},
        )
        self.access_token = data.get("access_token")
        self.current_user = data.get("user")
        user = self.current_user if isinstance(self.current_user, dict) else {}
        self.tenant_id = int(user.get("tenant_id", tenant_id))
        return data

    def get_me(self) -> dict:
        """Retorna el perfil del usuario autenticado (`GET /api/v1/auth/me`)."""
        return self._get("/api/v1/auth/me")

    def logout(self) -> dict:
        """Cierra la sesión actual y limpia las credenciales en memoria (`POST /api/v1/auth/logout`)."""
        try:
            result = self._post("/api/v1/auth/logout")
        finally:
            self.access_token = self.current_user = self.tenant_id = None
        return result or {}

    # =========================================================================
    # 2. CLIENTES Y LICENCIAS (/api/v1/clients)
    # =========================================================================

    def list_clients(self, search: Optional[str] = None, status: Optional[str] = None) -> list[dict]:
        """Lista los clientes de la agencia activa (`GET /api/v1/clients`)."""
        return self._get("/api/v1/clients", search=search, status=status)

    def get_client(self, id_cliente: int) -> dict:
        """Consulta un cliente por su ID (`GET /api/v1/clients/{id_cliente}`)."""
        return self._get(f"/api/v1/clients/{id_cliente}")

    def create_client(self, payload: dict) -> dict:
        """Registra un nuevo cliente en la agencia activa (`POST /api/v1/clients`)."""
        return self._post("/api/v1/clients", payload)

    def update_client(self, id_cliente: int, payload: dict) -> dict:
        """Actualiza un cliente existente y su licencia (`PUT /api/v1/clients/{id_cliente}`)."""
        return self._request("PUT", f"/api/v1/clients/{id_cliente}", json=payload)

    def change_client_status(self, id_cliente: int, estado_cliente: str) -> dict:
        """Cambia el estado comercial de un cliente (`PATCH /api/v1/clients/{id_cliente}/status`)."""
        return self._request("PATCH", f"/api/v1/clients/{id_cliente}/status", json={"estado_cliente": estado_cliente})

    def delete_client(self, id_cliente: int) -> dict:
        """Elimina físicamente un cliente (`DELETE /api/v1/clients/{id_cliente}`)."""
        return self._request("DELETE", f"/api/v1/clients/{id_cliente}")

    # =========================================================================
    # 3. FLOTA VEHICULAR (/api/v1/vehicles)
    # =========================================================================

    def list_brands(self) -> list[dict]:
        """Lista las marcas de vehículos (`GET /api/v1/vehicles/brands`)."""
        return self._get("/api/v1/vehicles/brands")

    def list_models(self, id_marca: Optional[int] = None) -> list[dict]:
        """Lista el catálogo de modelos de vehículos (`GET /api/v1/vehicles/models`)."""
        return self._get("/api/v1/vehicles/models", id_marca=id_marca)

    def list_categories(self) -> list[dict]:
        """Lista las categorías tarifarias de la agencia activa (`GET /api/v1/vehicles/categories`)."""
        return self._get("/api/v1/vehicles/categories")

    def list_vehicles(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        active_only: bool = False,
    ) -> list[dict]:
        """Lista los vehículos de la agencia activa (`GET /api/v1/vehicles`)."""
        return self._get(
            "/api/v1/vehicles",
            search=search,
            status=status,
            category_id=category_id,
            active_only=active_only or None,
        )

    def get_vehicle(self, id_vehiculo: int) -> dict:
        """Consulta el detalle de un vehículo (`GET /api/v1/vehicles/{id_vehiculo}`)."""
        return self._get(f"/api/v1/vehicles/{id_vehiculo}")

    def create_vehicle(self, payload: dict) -> dict:
        """Registra un nuevo vehículo en la agencia activa (`POST /api/v1/vehicles`)."""
        return self._post("/api/v1/vehicles", payload)

    def update_vehicle(self, id_vehiculo: int, payload: dict) -> dict:
        """Actualiza los datos de un vehículo (`PUT /api/v1/vehicles/{id_vehiculo}`)."""
        return self._request("PUT", f"/api/v1/vehicles/{id_vehiculo}", json=payload)

    def change_vehicle_status(self, id_vehiculo: int, estado: str) -> dict:
        """Cambia el estado operativo de un vehículo (`PATCH /api/v1/vehicles/{id_vehiculo}/status`)."""
        return self._request("PATCH", f"/api/v1/vehicles/{id_vehiculo}/status", json={"estado": estado})

    def delete_vehicle(self, id_vehiculo: int) -> dict:
        """Da de baja o elimina un vehículo (`DELETE /api/v1/vehicles/{id_vehiculo}`)."""
        return self._request("DELETE", f"/api/v1/vehicles/{id_vehiculo}")

    # =========================================================================
    # 4. RESERVACIONES (/api/v1/reservations)
    # =========================================================================

    def check_availability(
        self,
        id_categoria: int,
        start_dt: datetime,
        end_dt: datetime,
        id_vehiculo: Optional[int] = None,
        exclude_reservation_id: Optional[int] = None,
    ) -> dict:
        """Verifica la disponibilidad temporal de vehículos (`GET /api/v1/reservations/availability/check`)."""
        return self._get(
            "/api/v1/reservations/availability/check",
            id_categoria=id_categoria,
            start_dt=_to_iso(start_dt),
            end_dt=_to_iso(end_dt),
            id_vehiculo=id_vehiculo,
            exclude_reservation_id=exclude_reservation_id,
        )

    def list_reservations(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        client_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> list[dict]:
        """Lista las reservaciones de la agencia activa (`GET /api/v1/reservations`)."""
        return self._get(
            "/api/v1/reservations", search=search, status=status, client_id=client_id, category_id=category_id
        )

    def get_reservation(self, id_reserva: int) -> dict:
        """Obtiene una reserva por su ID (`GET /api/v1/reservations/{id_reserva}`)."""
        return self._get(f"/api/v1/reservations/{id_reserva}")

    def create_reservation(self, payload: dict) -> dict:
        """Registra una nueva reserva (`POST /api/v1/reservations`)."""
        return self._post("/api/v1/reservations", payload)

    def update_reservation(self, id_reserva: int, payload: dict) -> dict:
        """Actualiza una reserva existente (`PUT /api/v1/reservations/{id_reserva}`)."""
        return self._request("PUT", f"/api/v1/reservations/{id_reserva}", json=payload)

    def confirm_reservation(self, id_reserva: int) -> dict:
        """Confirma una reserva pendiente (`POST /api/v1/reservations/{id_reserva}/confirm`)."""
        return self._post(f"/api/v1/reservations/{id_reserva}/confirm")

    def cancel_reservation(self, id_reserva: int, motivo: Optional[str] = None) -> dict:
        """Cancela una reserva activa (`POST /api/v1/reservations/{id_reserva}/cancel`)."""
        return self._post(f"/api/v1/reservations/{id_reserva}/cancel", {"motivo": motivo})

    # =========================================================================
    # 5. CONTRATOS Y DESPACHO (/api/v1/contracts)
    # =========================================================================

    def list_coverages(self) -> list[dict]:
        """Lista las pólizas y coberturas de seguro (`GET /api/v1/contracts/coverages`)."""
        return self._get("/api/v1/contracts/coverages")

    def list_contracts(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        client_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
    ) -> list[dict]:
        """Lista los contratos de arrendamiento de la agencia activa (`GET /api/v1/contracts`)."""
        return self._get(
            "/api/v1/contracts", search=search, status=status, client_id=client_id, vehicle_id=vehicle_id
        )

    def get_contract(self, id_contrato: int) -> dict:
        """Consulta un contrato por su ID (`GET /api/v1/contracts/{id_contrato}`)."""
        return self._get(f"/api/v1/contracts/{id_contrato}")

    def get_contract_document_html(self, id_contrato: int) -> dict:
        """Genera el documento HTML imprimible del contrato (`GET /api/v1/contracts/{id_contrato}/document-html`)."""
        return self._get(f"/api/v1/contracts/{id_contrato}/document-html")

    def create_contract(self, payload: dict) -> dict:
        """Formaliza un nuevo contrato de alquiler (`POST /api/v1/contracts`)."""
        return self._post("/api/v1/contracts", payload)

    def cancel_contract(self, id_contrato: int, motivo: Optional[str] = None) -> dict:
        """Anula un contrato activo (`POST /api/v1/contracts/{id_contrato}/cancel`)."""
        return self._post(f"/api/v1/contracts/{id_contrato}/cancel", {"motivo": motivo})

    # =========================================================================
    # 6. DEVOLUCIONES Y LIQUIDACIONES (/api/v1/returns)
    # =========================================================================

    def list_returns(self, search: str = "", limit: int = 100) -> list[dict]:
        """Lista las actas de devolución registradas (`GET /api/v1/returns`)."""
        return self._get("/api/v1/returns", search=search, limit=limit)

    def list_settlements(self, search: str = "", limit: int = 100) -> list[dict]:
        """Lista las liquidaciones financieras (`GET /api/v1/returns/settlements`)."""
        return self._get("/api/v1/returns/settlements", search=search, limit=limit)

    def get_return_by_contract(self, id_contrato: int) -> Optional[dict]:
        """Obtiene la devolución asociada a un contrato (`GET /api/v1/returns/by-contract/{id_contrato}`)."""
        return self._get(f"/api/v1/returns/by-contract/{id_contrato}")

    def get_settlement_by_contract(self, id_contrato: int) -> Optional[dict]:
        """Obtiene la liquidación asociada a un contrato (`GET /api/v1/returns/settlements/by-contract/{id_contrato}`)."""
        return self._get(f"/api/v1/returns/settlements/by-contract/{id_contrato}")

    def get_return(self, id_devolucion: int) -> dict:
        """Obtiene el detalle de un acta de devolución (`GET /api/v1/returns/{id_devolucion}`)."""
        return self._get(f"/api/v1/returns/{id_devolucion}")

    def process_return(self, payload: dict) -> dict:
        """Procesa de forma atómica el retorno e inspección (`POST /api/v1/returns`)."""
        return self._post("/api/v1/returns", payload)

    # =========================================================================
    # 7. MANTENIMIENTO Y TALLER (/api/v1/maintenances)
    # =========================================================================

    def get_maintenance_kpis(self) -> dict:
        """Obtiene los KPIs del módulo de taller (`GET /api/v1/maintenances/kpis`)."""
        return self._get("/api/v1/maintenances/kpis")

    def list_maintenances(
        self,
        search: str = "",
        status: Optional[str] = None,
        maintenance_type: Optional[str] = None,
        vehicle_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Lista las órdenes de mantenimiento de la agencia activa (`GET /api/v1/maintenances`)."""
        return self._get(
            "/api/v1/maintenances",
            search=search,
            status=status,
            maintenance_type=maintenance_type,
            vehicle_id=vehicle_id,
            limit=limit,
        )

    def get_maintenance(self, id_mantenimiento: int) -> dict:
        """Consulta una orden de mantenimiento por ID (`GET /api/v1/maintenances/{id_mantenimiento}`)."""
        return self._get(f"/api/v1/maintenances/{id_mantenimiento}")

    def create_maintenance(self, payload: dict) -> dict:
        """Registra una nueva entrada a taller (`POST /api/v1/maintenances`)."""
        return self._post("/api/v1/maintenances", payload)

    def complete_maintenance(self, id_mantenimiento: int, payload: dict) -> dict:
        """Finaliza una orden de taller y libera el vehículo (`POST /api/v1/maintenances/{id_mantenimiento}/complete`)."""
        return self._post(f"/api/v1/maintenances/{id_mantenimiento}/complete", payload)

    def cancel_maintenance(self, id_mantenimiento: int, motivo: Optional[str] = None) -> dict:
        """Cancela una orden de mantenimiento activa (`POST /api/v1/maintenances/{id_mantenimiento}/cancel`)."""
        return self._post(f"/api/v1/maintenances/{id_mantenimiento}/cancel", {"motivo": motivo})

    # =========================================================================
    # 8. REPORTES Y ANALÍTICA (/api/v1/reports)
    # =========================================================================

    def get_financial_report(
        self,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        metodo_pago: Optional[str] = None,
        concepto: Optional[str] = None,
    ) -> dict:
        """Obtiene el reporte financiero ejecutivo (`GET /api/v1/reports/financial`)."""
        return self._get(
            "/api/v1/reports/financial",
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            metodo_pago=metodo_pago,
            concepto=concepto,
        )

    def get_fleet_report(
        self,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        id_categoria: Optional[int] = None,
        search: Optional[str] = None,
    ) -> dict:
        """Obtiene el reporte de utilización de flota (`GET /api/v1/reports/fleet`)."""
        return self._get(
            "/api/v1/reports/fleet",
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            id_categoria=id_categoria,
            search=search,
        )

    def get_clients_report(
        self,
        filtro_criterio: str = "TODOS",
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        search: Optional[str] = None,
    ) -> dict:
        """Obtiene el reporte de comportamiento e historial de clientes (`GET /api/v1/reports/clients`)."""
        return self._get(
            "/api/v1/reports/clients",
            filtro_criterio=filtro_criterio,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            search=search,
        )

    # =========================================================================
    # 9. USUARIOS, ROLES RBAC Y AUDITORÍA (/api/v1/users)
    # =========================================================================

    def list_roles(self) -> list[dict]:
        """Lista los roles del sistema (`GET /api/v1/users/roles`)."""
        return self._get("/api/v1/users/roles")

    def get_user_kpis(self) -> dict:
        """Obtiene los KPIs cuantitativos de usuarios (`GET /api/v1/users/kpis`)."""
        return self._get("/api/v1/users/kpis")

    def list_audit_logs(
        self,
        limit: int = 150,
        accion: Optional[str] = None,
        username: Optional[str] = None,
        tabla_afectada: Optional[str] = None,
    ) -> list[dict]:
        """Consulta la bitácora de auditoría (`GET /api/v1/users/audit-logs`)."""
        return self._get(
            "/api/v1/users/audit-logs", limit=limit, accion=accion, username=username, tabla_afectada=tabla_afectada
        )

    def list_users(
        self,
        search: Optional[str] = None,
        id_rol: Optional[int] = None,
        activo: Optional[bool] = None,
    ) -> list[dict]:
        """Lista los usuarios de la agencia activa (`GET /api/v1/users`)."""
        return self._get("/api/v1/users", search=search, id_rol=id_rol, activo=activo)

    def get_user(self, id_usuario: int) -> dict:
        """Obtiene un usuario por su ID (`GET /api/v1/users/{id_usuario}`)."""
        return self._get(f"/api/v1/users/{id_usuario}")

    def create_user(self, payload: dict) -> dict:
        """Crea un nuevo usuario (`POST /api/v1/users`)."""
        return self._post("/api/v1/users", payload)

    def update_user(self, id_usuario: int, payload: dict) -> dict:
        """Actualiza los datos de un usuario (`PUT /api/v1/users/{id_usuario}`)."""
        return self._request("PUT", f"/api/v1/users/{id_usuario}", json=payload)

    def reset_user_password(self, id_usuario: int, new_password: str) -> dict:
        """Restablece la contraseña de un usuario (`POST /api/v1/users/{id_usuario}/reset-password`)."""
        return self._post(f"/api/v1/users/{id_usuario}/reset-password", {"new_password": new_password})

    def toggle_user_active(self, id_usuario: int) -> dict:
        """Conmuta el estado activo/inactivo de un usuario (`POST /api/v1/users/{id_usuario}/toggle-active`)."""
        return self._post(f"/api/v1/users/{id_usuario}/toggle-active")

    def unlock_user(self, id_usuario: int) -> dict:
        """Desbloquea manualmente una cuenta de usuario (`POST /api/v1/users/{id_usuario}/unlock`)."""
        return self._post(f"/api/v1/users/{id_usuario}/unlock")

    def delete_user(self, id_usuario: int) -> dict:
        """Elimina físicamente una cuenta de usuario (`DELETE /api/v1/users/{id_usuario}`)."""
        return self._request("DELETE", f"/api/v1/users/{id_usuario}")

    # =========================================================================
    # MAPEADORES JSON -> ENTIDADES DE DOMINIO (DATACLASSES)
    # Cada `to_<entidad>(data)` delega en `_from_dict`, que convierte los tipos
    # (fechas, Decimal, Enum, listas y sub-entidades) según las anotaciones del
    # dataclass y respeta sus valores por defecto.
    # =========================================================================

    to_agency = staticmethod(partial(_from_dict, Agency))
    to_role = staticmethod(partial(_from_dict, Role))
    to_user = staticmethod(partial(_from_dict, User))
    to_audit_log = staticmethod(partial(_from_dict, AuditLog))
    to_driver_license = staticmethod(partial(_from_dict, DriverLicense))
    to_client = staticmethod(partial(_from_dict, Client))
    to_brand = staticmethod(partial(_from_dict, Brand))
    to_vehicle_model = staticmethod(partial(_from_dict, VehicleModel))
    to_vehicle_category = staticmethod(partial(_from_dict, VehicleCategory))
    to_vehicle = staticmethod(partial(_from_dict, Vehicle))
    to_insurance_coverage = staticmethod(partial(_from_dict, InsuranceCoverage))
    to_reservation = staticmethod(partial(_from_dict, Reservation))
    to_additional_driver = staticmethod(partial(_from_dict, AdditionalDriver))
    to_payment = staticmethod(partial(_from_dict, Payment))
    to_contract = staticmethod(partial(_from_dict, Contract))
    to_damage = staticmethod(partial(_from_dict, Damage))
    to_return_inspection = staticmethod(partial(_from_dict, ReturnInspection))
    to_settlement = staticmethod(partial(_from_dict, Settlement))
    to_maintenance = staticmethod(partial(_from_dict, Maintenance))
    to_financial_report_item = staticmethod(partial(_from_dict, FinancialReportItem))
    to_financial_report_summary = staticmethod(partial(_from_dict, FinancialReportSummary))
    to_fleet_utilization_item = staticmethod(partial(_from_dict, FleetUtilizationItem))
    to_fleet_utilization_summary = staticmethod(partial(_from_dict, FleetUtilizationSummary))
    to_client_history_item = staticmethod(partial(_from_dict, ClientHistoryItem))
    to_client_history_summary = staticmethod(partial(_from_dict, ClientHistorySummary))


# Instancia singleton del cliente HTTP para consumo desde la capa de escritorio
api_client = AutoRentApiClient()

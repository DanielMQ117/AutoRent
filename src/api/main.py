"""Punto de entrada de la API RESTful de AutoRent Pro (FastAPI + Multi-Tenant RLS)."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.api.routers import (
    auth_router,
    clients_router,
    contracts_router,
    maintenances_router,
    reports_router,
    reservations_router,
    returns_router,
    users_router,
    vehicles_router,
)
from src.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleViolationError,
    DuplicateRecordError,
    ExclusionViolationError,
    ForeignKeyViolationError,
    InvalidStateTransitionError,
    RecordNotFoundError,
    ValidationError,
)

app = FastAPI(
    title="AutoRent Pro API — Multi-Tenant & RLS",
    description=(
        "Capa de Servicios Web RESTful para la Gestión de Alquiler de Automóviles "
        "con aislamiento nativo Multi-Tenant mediante PostgreSQL Row Level Security (RLS)."
    ),
    version="1.0.0",
)


# ============================================================================
# MANEJADORES CENTRALIZADOS DE EXCEPCIONES DEL DOMINIO Y PERSISTENCIA
# ============================================================================


@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(RecordNotFoundError)
async def not_found_exception_handler(request: Request, exc: RecordNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(DuplicateRecordError)
@app.exception_handler(ExclusionViolationError)
async def conflict_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(ValidationError)
@app.exception_handler(BusinessRuleViolationError)
@app.exception_handler(InvalidStateTransitionError)
@app.exception_handler(ForeignKeyViolationError)
async def bad_request_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(AppException)
async def generic_app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


# ============================================================================
# ENDPOINT DE SALUD Y REGISTRO DE ROUTERS
# ============================================================================


@app.get("/health", tags=["Infraestructura"])
def health_check() -> dict:
    """Verifica el estado operativo de la API y la activación del modo Multi-Tenant RLS."""
    return {
        "status": "healthy",
        "service": "AutoRent Pro API",
        "version": "1.0.0",
        "multitenant_rls": True,
    }


app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(vehicles_router)
app.include_router(reservations_router)
app.include_router(contracts_router)
app.include_router(returns_router)
app.include_router(maintenances_router)
app.include_router(reports_router)
app.include_router(users_router)

# Adaptador ASGI -> AWS Lambda / API Gateway (Fase 3 Cloud)
try:
    from mangum import Mangum

    handler = Mangum(app)
except ImportError:
    handler = None

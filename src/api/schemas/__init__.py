"""Exportación consolidada de esquemas Pydantic v2 para la capa API."""

from src.api.schemas.auth_schema import (
    AgencyResponse,
    LoginRequest,
    LoginResponse,
    UserSessionInfo,
)
from src.api.schemas.client_schema import (
    ClientCreateRequest,
    ClientResponse,
    ClientStatusUpdateRequest,
    ClientUpdateRequest,
    DriverLicenseSchema,
)
from src.api.schemas.contract_schema import (
    AdditionalDriverSchema,
    ContractCancelRequest,
    ContractCreateRequest,
    ContractResponse,
    InsuranceCoverageResponse,
    PaymentResponse,
)
from src.api.schemas.maintenance_schema import (
    MaintenanceCancelRequest,
    MaintenanceCompleteRequest,
    MaintenanceCreateRequest,
    MaintenanceResponse,
)
from src.api.schemas.report_schema import (
    ClientHistoryItemSchema,
    ClientHistorySummaryResponse,
    FinancialReportItemSchema,
    FinancialReportSummaryResponse,
    FleetUtilizationItemSchema,
    FleetUtilizationSummaryResponse,
)
from src.api.schemas.reservation_schema import (
    ReservationCancelRequest,
    ReservationCreateRequest,
    ReservationResponse,
    ReservationUpdateRequest,
)
from src.api.schemas.return_schema import (
    DamageSchema,
    ReturnCreateRequest,
    ReturnInspectionResponse,
    ReturnProcessResponse,
    SettlementResponse,
)
from src.api.schemas.user_schema import (
    AuditLogResponse,
    RoleResponse,
    UserCreateRequest,
    UserPasswordResetRequest,
    UserResponse,
    UserUpdateRequest,
)
from src.api.schemas.vehicle_schema import (
    BrandResponse,
    VehicleCategoryResponse,
    VehicleCreateRequest,
    VehicleModelResponse,
    VehicleResponse,
    VehicleStatusUpdateRequest,
    VehicleUpdateRequest,
)

__all__ = [
    "AgencyResponse",
    "LoginRequest",
    "UserSessionInfo",
    "LoginResponse",
    "DriverLicenseSchema",
    "ClientCreateRequest",
    "ClientUpdateRequest",
    "ClientStatusUpdateRequest",
    "ClientResponse",
    "BrandResponse",
    "VehicleModelResponse",
    "VehicleCategoryResponse",
    "VehicleCreateRequest",
    "VehicleUpdateRequest",
    "VehicleStatusUpdateRequest",
    "VehicleResponse",
    "ReservationCreateRequest",
    "ReservationUpdateRequest",
    "ReservationCancelRequest",
    "ReservationResponse",
    "InsuranceCoverageResponse",
    "AdditionalDriverSchema",
    "PaymentResponse",
    "ContractCreateRequest",
    "ContractCancelRequest",
    "ContractResponse",
    "DamageSchema",
    "ReturnCreateRequest",
    "ReturnInspectionResponse",
    "SettlementResponse",
    "ReturnProcessResponse",
    "MaintenanceCreateRequest",
    "MaintenanceCompleteRequest",
    "MaintenanceCancelRequest",
    "MaintenanceResponse",
    "FinancialReportItemSchema",
    "FinancialReportSummaryResponse",
    "FleetUtilizationItemSchema",
    "FleetUtilizationSummaryResponse",
    "ClientHistoryItemSchema",
    "ClientHistorySummaryResponse",
    "RoleResponse",
    "UserCreateRequest",
    "UserUpdateRequest",
    "UserPasswordResetRequest",
    "UserResponse",
    "AuditLogResponse",
]

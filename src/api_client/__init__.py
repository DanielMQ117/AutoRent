"""Cliente HTTP unificado para comunicación con la API RESTful de AutoRent Pro."""

from src.api_client.http_client import ApiClientError, AutoRentApiClient

__all__ = ["AutoRentApiClient", "ApiClientError"]

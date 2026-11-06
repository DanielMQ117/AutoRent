"""Suite de pruebas automatizadas para Recepción de Devoluciones con Daños Físicos en Modo Remoto.

Certifica programáticamente:
1. Compatibilidad total de la entidad de dominio `Damage` con atributos oficiales (`gravedad`, `tipo_danio`, `descripcion`)
   y alias retrocompatible `severidad` (garantizando que nunca más se lance AttributeError).
2. Serialización correcta del payload de devolución en `ReturnService.process_return_and_settlement` cuando `api_client.remote_mode = True`,
   asegurando que cada daño contenga las claves exactas requeridas por la API REST:
   - `zona_carroceria`
   - `tipo_danio`
   - `gravedad`
   - `descripcion`
   - `costo_reparacion`
3. Validación estricta de dicho payload con `DamageSchema` y `ReturnCreateRequest` de Pydantic v2.
4. Integración completa con FastAPI TestClient (`POST /api/v1/returns`) verificando la recepción, validación y persistencia de daños físicos.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.api.main import app
from src.api.schemas.return_schema import DamageSchema, ReturnCreateRequest, ReturnProcessResponse
from src.api_client import AutoRentApiClient, api_client
from src.core.logger import setup_logging
from src.domain.enums import (
    ClientStatus,
    ClientType,
    ContractStatus,
    DamageSeverity,
    DamageType,
    PaymentMethod,
    PaymentType,
    SettlementStatus,
    VehicleStatus,
)
from src.domain.models import (
    Client,
    Contract,
    Damage,
    DriverLicense,
    Payment,
    ReturnInspection,
    Settlement,
    Vehicle,
)
from src.services.auth_service import auth_service
from src.services.client_service import client_service
from src.services.contract_service import contract_service
from src.services.return_service import return_service
from src.services.vehicle_service import vehicle_service


def test_damage_model_attributes_and_aliases() -> None:
    """Certifica que el dataclass Damage maneje tanto gravedad como el alias severidad sin lanzar AttributeError."""
    print("\n[SUBTEST 1] Verificando entidad Damage: atributos y alias retrocompatible 'severidad'...")

    d = Damage(
        zona_carroceria="Puerta Delantera Derecha",
        tipo_danio=DamageType.GOLPE,
        gravedad=DamageSeverity.MODERADO,
        descripcion="Golpe en puerta lateral",
        costo_reparacion=Decimal("150.00"),
    )

    # 1. Atributos estándar
    assert d.zona_carroceria == "Puerta Delantera Derecha"
    assert d.tipo_danio == DamageType.GOLPE
    assert d.gravedad == DamageSeverity.MODERADO
    assert d.descripcion == "Golpe en puerta lateral"
    assert d.costo_reparacion == Decimal("150.00")

    # 2. Alias 'severidad'
    assert hasattr(d, "severidad"), "Damage DEBE tener atributo/propiedad 'severidad'."
    assert d.severidad == DamageSeverity.MODERADO, "d.severidad debe retornar el mismo valor que d.gravedad."

    # 3. Setter de 'severidad'
    d.severidad = DamageSeverity.GRAVE
    assert d.gravedad == DamageSeverity.GRAVE, "Modificar d.severidad debe actualizar d.gravedad."
    assert d.severidad == DamageSeverity.GRAVE

    print(" -> PASO: Entidad Damage certificada. El error \"'Damage' object has no attribute 'severidad'\" está blindado.")


def test_process_return_with_damages_remote_mode_serialization() -> None:
    """Certifica que ReturnService serialice los daños con api_client.remote_mode = True sin AttributeError y con esquema válido."""
    print("\n[SUBTEST 2] Verificando serialización de daños en ReturnService con api_client.remote_mode = True...")

    danios = [
        Damage(
            zona_carroceria="Puerta Delantera Izquierda",
            tipo_danio=DamageType.GOLPE,
            gravedad=DamageSeverity.MODERADO,
            descripcion="Golpe en puerta lateral",
            costo_reparacion=Decimal("150.00"),
        ),
        Damage(
            zona_carroceria="Parachoques Delantero",
            tipo_danio=DamageType.RAYON,
            gravedad=DamageSeverity.LEVE,
            descripcion="Rayón superficial en pintura",
            costo_reparacion=Decimal("75.00"),
        ),
        Damage(
            zona_carroceria="Parabrisas Frontal",
            tipo_danio=DamageType.ROTURA,
            gravedad=DamageSeverity.GRAVE,
            descripcion="Fisura por impacto frontal",
            costo_reparacion=Decimal("300.00"),
        ),
    ]

    now = datetime.now()
    ret_data = ReturnInspection(
        id_contrato=9901,
        fecha_hora_retorno_real=now,
        kilometraje_retorno=45200,
        combustible_retorno=Decimal("1.00"),
        limpieza_aprobada=True,
        accesorios_completos=True,
        observaciones="Inspección remota multidaño",
        danios=danios,
    )

    captured_payloads = []

    def mock_process_return(payload: dict) -> dict:
        captured_payloads.append(payload)
        return {
            "return_inspection": {
                "id_devolucion": 1234,
                "tenant_id": 1,
                "id_contrato": payload["id_contrato"],
                "fecha_hora_retorno_real": payload["fecha_hora_retorno_real"],
                "kilometraje_retorno": payload["kilometraje_retorno"],
                "combustible_retorno": payload["combustible_retorno"],
                "horas_retraso": 0,
                "limpieza_aprobada": payload["limpieza_aprobada"],
                "accesorios_completos": payload["accesorios_completos"],
                "observaciones": payload["observaciones"],
                "id_usuario": 1,
                "danios": payload["danios"],
            },
            "settlement": {
                "id_liquidacion": 5678,
                "tenant_id": 1,
                "id_contrato": payload["id_contrato"],
                "id_devolucion": 1234,
                "fecha_liquidacion": now.isoformat(),
                "dias_facturados": 2,
                "subtotal_renta": "80.00",
                "cargos_retraso": "0.00",
                "cargos_combustible": "0.00",
                "cargos_km_excedente": "0.00",
                "cargos_danios": "525.00",
                "total_bruto": "605.00",
                "monto_garantia_aplicado": "200.00",
                "saldo_cliente": "405.00",
                "estado_liquidacion": "CERRADA",
                "id_usuario": 1,
                "pagos": [],
            },
            "payment": {
                "id_pago": 9012,
                "tenant_id": 1,
                "codigo_transaccion": "TRX-REMOTE-TEST-001",
                "id_contrato": payload["id_contrato"],
                "id_liquidacion": 5678,
                "tipo_movimiento": "COBRO_LIQUIDACION",
                "metodo_pago": payload["metodo_pago"],
                "monto": "405.00",
                "referencia": "Pago Remoto Test",
                "id_usuario": 1,
            },
        }

    original_remote = api_client.remote_mode
    try:
        api_client.remote_mode = True
        with patch.object(api_client, "process_return", side_effect=mock_process_return):
            res = return_service.process_return_and_settlement(
                id_contrato=9901,
                return_data=ret_data,
                metodo_pago=PaymentMethod.TARJETA_CREDITO,
                referencia_pago="REF-REMOTE-01",
            )

        assert len(captured_payloads) == 1
        p = captured_payloads[0]

        # Validar estructura y claves
        assert p["id_contrato"] == 9901
        assert p["kilometraje_retorno"] == 45200
        assert p["combustible_retorno"] == "1.00"
        assert p["metodo_pago"] == "TARJETA_CREDITO"
        assert p["referencia_pago"] == "REF-REMOTE-01"
        assert len(p["danios"]) == 3

        expected_damages = [
            ("Puerta Delantera Izquierda", "GOLPE", "MODERADO", "Golpe en puerta lateral", "150.00"),
            ("Parachoques Delantero", "RAYON", "LEVE", "Rayón superficial en pintura", "75.00"),
            ("Parabrisas Frontal", "ROTURA", "GRAVE", "Fisura por impacto frontal", "300.00"),
        ]

        for idx, (exp_zona, exp_tipo, exp_grav, exp_desc, exp_costo) in enumerate(expected_damages):
            item = p["danios"][idx]
            assert item["zona_carroceria"] == exp_zona
            assert item["tipo_danio"] == exp_tipo
            assert item["gravedad"] == exp_grav
            assert item["descripcion"] == exp_desc
            assert item["costo_reparacion"] == exp_costo
            # Validar con Pydantic v2 DamageSchema
            validated = DamageSchema.model_validate(item)
            assert validated.tipo_danio.value == exp_tipo
            assert validated.gravedad.value == exp_grav
            assert validated.costo_reparacion == Decimal(exp_costo)

        # Validar petición completa con ReturnCreateRequest
        full_req = ReturnCreateRequest.model_validate(p)
        assert full_req.id_contrato == 9901
        assert len(full_req.danios) == 3

        # Validar entidades de dominio resultantes
        ret_obj = res["return_inspection"]
        assert isinstance(ret_obj, ReturnInspection)
        assert len(ret_obj.danios) == 3
        assert ret_obj.danios[0].gravedad == DamageSeverity.MODERADO
        assert ret_obj.danios[0].tipo_danio == DamageType.GOLPE
        assert ret_obj.danios[0].severidad == DamageSeverity.MODERADO
        assert ret_obj.tiene_danio_grave is True
        assert ret_obj.costo_total_danios == Decimal("525.00")

        sett_obj = res["settlement"]
        assert isinstance(sett_obj, Settlement)
        assert sett_obj.cargos_danios == Decimal("525.00")

        pay_obj = res["payment"]
        assert isinstance(pay_obj, Payment)
        assert pay_obj.monto == Decimal("405.00")

        print(" -> PASO: Serialización, validación Pydantic y deserialización de 3 averías ejecutadas al 100%.")
    finally:
        api_client.remote_mode = original_remote


def test_fastapi_endpoint_processes_damages() -> None:
    """Certifica que el endpoint FastAPI POST /api/v1/returns procese y persista devoluciones con daños."""
    print("\n[SUBTEST 3] Verificando endpoint FastAPI POST /api/v1/returns con múltiples averías...")

    test_http_client = AutoRentApiClient(app=app)
    test_http_client.login("admin", "Admin123*", tenant_id=1)

    # 1. Crear contrato real para la prueba
    cedula_test = "001-150892-0099K"
    placa_test = "M-DAM-889"

    # Limpieza preventiva
    cleanup_sql = """
        DELETE FROM pagos WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo IN (SELECT id_vehiculo FROM vehiculos WHERE placa = %s));
        DELETE FROM liquidaciones WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo IN (SELECT id_vehiculo FROM vehiculos WHERE placa = %s));
        DELETE FROM danios WHERE id_devolucion IN (SELECT id_devolucion FROM devoluciones WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo IN (SELECT id_vehiculo FROM vehiculos WHERE placa = %s)));
        DELETE FROM devoluciones WHERE id_contrato IN (SELECT id_contrato FROM contratos WHERE id_vehiculo IN (SELECT id_vehiculo FROM vehiculos WHERE placa = %s));
        DELETE FROM contratos WHERE id_vehiculo IN (SELECT id_vehiculo FROM vehiculos WHERE placa = %s);
        DELETE FROM vehiculos WHERE placa = %s;
        DELETE FROM licencias_conducir WHERE id_cliente IN (SELECT id_cliente FROM clientes WHERE identificacion = %s);
        DELETE FROM clientes WHERE identificacion = %s;
    """
    try:
        return_service.contract_repo.execute_non_query(
            cleanup_sql,
            (placa_test, placa_test, placa_test, placa_test, placa_test, placa_test, cedula_test, cedula_test),
        )
    except Exception:
        pass

    try:
        # Preparar cliente, vehículo y contrato
        c = client_service.create_client(
            Client(
                tipo_persona=ClientType.NATURAL,
                identificacion=cedula_test,
                nombres="Martín",
                apellidos="Vallejos Núñez",
                email="martin.vallejos@testapi.com",
                telefono="88887777",
                direccion="Managua, Bello Horizonte",
                estado_cliente=ClientStatus.ACTIVO,
            ),
            DriverLicense(
                numero_licencia="NIC-MAR-8899",
                categoria_licencia="CATEGORIA_3",
                fecha_emision=date(2022, 1, 1),
                fecha_vencimiento=date(2030, 1, 1),
                pais_emision="Nicaragua",
            ),
        )

        models = vehicle_service.get_models()
        cats = vehicle_service.get_categories()
        covs = contract_service.get_coverages()

        v = vehicle_service.create_vehicle(
            Vehicle(
                id_modelo=models[0].id_modelo,
                id_categoria=cats[0].id_categoria,
                placa=placa_test,
                vin="1DAM889TESTING001",
                color="Gris Platino",
                kilometraje_actual=30000,
                nivel_combustible_actual=Decimal("1.00"),
                estado=VehicleStatus.DISPONIBLE,
                km_proximo_mantenimiento=40000,
                activo=True,
            )
        )

        now = datetime.now()
        start = now - timedelta(days=2)
        end = now

        ctr = contract_service.create_contract(
            Contract(
                id_cliente=c.id_cliente,
                id_vehiculo=v.id_vehiculo,
                id_cobertura=covs[0].id_cobertura,
                fecha_hora_inicio_pactada=start,
                fecha_hora_fin_pactada=end,
                fecha_hora_salida_real=start,
                kilometraje_salida=30000,
                combustible_salida=Decimal("1.00"),
                tarifa_diaria_aplicada=Decimal("45.00"),
                monto_garantia=Decimal("350.00"),
                kilometraje_ilimitado=True,
            )
        )

        # 2. Enviar petición HTTP POST /api/v1/returns con múltiples daños
        payload = {
            "id_contrato": ctr.id_contrato,
            "fecha_hora_retorno_real": now.isoformat(),
            "kilometraje_retorno": 30220,
            "combustible_retorno": "1.00",
            "limpieza_aprobada": True,
            "accesorios_completos": True,
            "observaciones": "Devolución con dos averías evaluadas vía API",
            "metodo_pago": "TARJETA_DEBITO",
            "referencia_pago": "POS-DEB-7788",
            "danios": [
                {
                    "zona_carroceria": "Faro Delantero Derecho",
                    "tipo_danio": "ROTURA",
                    "gravedad": "MODERADO",
                    "descripcion": "Cristal de óptica quebrado por impacto",
                    "costo_reparacion": "180.00",
                },
                {
                    "zona_carroceria": "Aleta Trasera Izquierda",
                    "tipo_danio": "RAYON",
                    "gravedad": "LEVE",
                    "descripcion": "Rayón profundo de 10cm",
                    "costo_reparacion": "65.00",
                },
            ],
        }

        resp = test_http_client.process_return(payload)
        assert "return_inspection" in resp
        assert "settlement" in resp
        assert "payment" in resp

        ret_resp = resp["return_inspection"]
        assert ret_resp["id_contrato"] == ctr.id_contrato
        assert len(ret_resp["danios"]) == 2

        # Validar daños devueltos por la API
        d1 = ret_resp["danios"][0]
        assert d1["zona_carroceria"] == "Faro Delantero Derecho"
        assert d1["tipo_danio"] == "ROTURA"
        assert d1["gravedad"] == "MODERADO"
        assert Decimal(str(d1["costo_reparacion"])) == Decimal("180.00")

        d2 = ret_resp["danios"][1]
        assert d2["zona_carroceria"] == "Aleta Trasera Izquierda"
        assert d2["tipo_danio"] == "RAYON"
        assert d2["gravedad"] == "LEVE"
        assert Decimal(str(d2["costo_reparacion"])) == Decimal("65.00")

        # Validar liquidación
        sett_resp = resp["settlement"]
        assert Decimal(str(sett_resp["cargos_danios"])) == Decimal("245.00")
        assert sett_resp["estado_liquidacion"] == "CERRADA"

        # Validar persistencia en base de datos mediante consulta directa
        ret_db = return_service.get_return(ret_resp["id_devolucion"])
        assert len(ret_db.danios) == 2
        assert ret_db.costo_total_danios == Decimal("245.00")
        assert ret_db.danios[0].gravedad == DamageSeverity.MODERADO
        assert ret_db.danios[0].severidad == DamageSeverity.MODERADO

        print(f" -> PASO: API REST procesó y persistió devolución ID {ret_resp['id_devolucion']} con 2 daños ($245.00).")
    finally:
        try:
            return_service.contract_repo.execute_non_query(
                cleanup_sql,
                (placa_test, placa_test, placa_test, placa_test, placa_test, placa_test, cedula_test, cedula_test),
            )
        except Exception:
            pass


def run_tests() -> None:
    setup_logging()
    print("\n" + "=" * 78)
    print("EJECUTANDO SUITE DE CERTIFICACIÓN: DEVOLUCIONES CON DAÑOS Y MODO REMOTO HTTP")
    print("=" * 78)

    test_damage_model_attributes_and_aliases()
    test_process_return_with_damages_remote_mode_serialization()
    test_fastapi_endpoint_processes_damages()

    print("\n" + "=" * 78)
    print("¡CERTIFICACIÓN EXITOSA: DEVOLUCIONES CON DAÑOS Y MODO REMOTO HTTP AL 100%!")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    run_tests()

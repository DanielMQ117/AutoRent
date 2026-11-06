# 🚗 AutoRent Pro — Sistema de Control y Gestión de Alquiler de Automóviles

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2015%2B-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Security](https://img.shields.io/badge/Security-Multi--Tenant%20RLS%20%7C%20JWT%20%7C%20Bcrypt-E53935?style=for-the-badge&logo=security&logoColor=white)](#-seguridad-y-multi-tenancy)
[![Academic Project](https://img.shields.io/badge/UNAN-Proyecto%20Integrador%20II-FF6F00?style=for-the-badge)](docs/ANALISIS_Y_DISENIO.md)

> **AutoRent Pro** es una plataforma empresarial integral para la administración, control operativo y liquidación financiera del alquiler de vehículos (Rent-a-Car). Diseñada bajo una **arquitectura en capas desacoplada** (Cliente de Escritorio PySide6 + Backend RESTful en FastAPI), con persistencia orientada a objetos en **SQLAlchemy 2.0**, aislamiento estricto por agencia mediante **PostgreSQL Row-Level Security (RLS)** y prevención física contra overbooking mediante restricciones de exclusión temporal GiST en el motor de base de datos.

---

## 📑 Tabla de Contenidos

- [🎯 Propósito y Alcance](#-propósito-y-alcance)
- [🔄 Ciclo Operativo del Negocio](#-ciclo-operativo-del-negocio)
- [✨ Características Principales](#-características-principales)
- [🏗️ Arquitectura del Sistema](#️-arquitectura-del-sistema)
- [📂 Estructura del Repositorio](#-estructura-del-repositorio)
- [📊 Catálogo de Diagramas Técnicos](#-catálogo-de-diagramas-técnicos)
- [🛠️ Requisitos Previos](#️-requisitos-previos)
- [🚀 Guía de Instalación y Puesta en Marcha](#-guía-de-instalación-y-puesta-en-marcha)
- [🖥️ Cómo Ejecutar el Proyecto](#️-cómo-ejecutar-el-proyecto)
- [🔑 Credenciales de Acceso para Pruebas](#-credenciales-de-acceso-para-pruebas)
- [🧪 Pruebas de Calidad (Testing & QA)](#-pruebas-de-calidad-testing--qa)
- [🔒 Seguridad y Multi-Tenancy](#-seguridad-y-multi-tenancy)
- [👥 Roles del Sistema](#-roles-del-sistema)
- [🏛️ Créditos Académicos](#️-créditos-académicos)

---

## 🎯 Propósito y Alcance

En la industria de renta de automóviles, los mayores riesgos operativos radican en:
1. **El sobre-arrendamiento (*overbooking*):** Asignar un mismo vehículo a dos clientes en fechas solapadas debido a condiciones de carrera concurrentes.
2. **Fugas financieras en devoluciones:** Diferencias no cobradas de combustible, kilometraje excedido, entregas tardías (mora) y averías físicas no imputadas a la garantía.
3. **Falta de aislamiento multi-sucursal:** Riesgo de cruce de datos entre agencias independientes de una misma franquicia.

**AutoRent Pro** resuelve estos desafíos mediante:
- Restricciones relacionales exclusivas (`btree_gist`) que garantizan a nivel de hardware/motor que ningún vehículo sea reservado o contratado en periodos solapados.
- Políticas nativas de **Row-Level Security (RLS)** en PostgreSQL que aíslan automáticamente todas las tablas operativas según la agencia activa del usuario autenticado (`tenant_id`).
- Liquidación automatizada y transparente que compara check-in vs check-out y concilia los cargos extra directamente contra el depósito en fianza/garantía.

---

## 🔄 Ciclo Operativo del Negocio

El flujo transaccional sigue un ciclo de vida riguroso de siete etapas:

```text
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│ 1. RESERVA  │ ──► │ 2. CONTRATO  │ ──► │ 3. CHECK-IN /    │ ──► │ 4. ALQUILER  │
│             │     │              │     │    DESPACHO      │     │ (En uso)     │
└─────────────┘     └──────────────┘     └──────────────────┘     └──────────────┘
                                                                         │
┌─────────────────┐     ┌─────────────────────┐     ┌────────────────────┘
│ 7. LIQUIDACIÓN  │ ◄── │ 6. INSPECCIÓN       │ ◄── │ 5. DEVOLUCIÓN      │
│    Y CIERRE     │     │    (CHECK-OUT)      │     │    FÍSICA          │
└─────────────────┘     └─────────────────────┘     └────────────────────┘
```

1. **Reserva (RF-14 a RF-17):** Registro del cliente, categoría/vehículo, fechas y anticipo económico con seguro anti-overbooking.
2. **Contrato (RF-18, RF-19):** Formalización jurídica, asignación definitiva de placa/VIN, validación de licencia, selección de cobertura de seguro y cobro de fianza en garantía.
3. **Check-In / Despacho (RF-20, RF-21, RF-39):** Inspección de salida (odómetro inicial, nivel de combustible, accesorios), pase a estado `ALQUILADO` y generación del contrato oficial en PDF.
4. **Alquiler:** Periodo de goce y conducción por parte del arrendatario o conductores adicionales autorizados.
5. **Devolución (RF-22):** Recepción física del automóvil en la agencia con estampado de fecha y hora exacta.
6. **Inspección / Check-Out (RF-23, RF-24, RF-27):** Cotejo automatizado de odómetro y combustible devuelto vs despachado, y registro fotográfico/valorado de averías o daños nuevos.
7. **Liquidación y Cierre (RF-25, RF-26, RF-28, RF-29):** Conciliación de balance: renta pactada + mora + penalización de combustible + costo de daños evaluados vs garantía retenida. Cobro del excedente o reembolso inmediato del saldo a favor.

---

## ✨ Características Principales

### 🛡️ Seguridad y Multi-Agencia (Multi-Tenancy)
- **Aislamiento por Row-Level Security (RLS):** Cada consulta SQL está protegida por políticas PostgreSQL `FOR ALL USING (tenant_id = current_tenant_id())`.
- **Criptografía Robusta:** Cifrado de contraseñas con `bcrypt` (cost factor 12) y autenticación sin estado mediante tokens JWT (JSON Web Tokens).
- **Protección de Cuentas (RF-03):** Bloqueo automático de cuentas tras 3 intentos fallidos consecutivos de inicio de sesión.
- **Pista de Auditoría Inmutable (RF-05):** Registro de transacciones críticas (quién, cuándo, qué valor cambió y desde qué IP/agencia).

### 🚘 Gestión Inteligente de Flota
- Catálogo jerárquico estructurado: Fabricantes (`marcas`), Especificaciones (`modelos`) y Tarifas (`categorias_vehiculo`).
- Máquina de estados finitos del vehículo: `DISPONIBLE`, `RESERVADO`, `ALQUILADO`, `EN_MANTENIMIENTO`, `FUERA_SERVICIO`.
- Monitoreo preventivo de odómetro con alertas automáticas de servicio de taller cada 5,000 / 10,000 km.

### 📅 Control Anti-Overbooking
- Garantía matemática en PostgreSQL mediante la extensión `btree_gist`:
  ```sql
  CONSTRAINT excl_contrato_vehiculo_solapado EXCLUDE USING gist (
      id_vehiculo WITH =,
      tstzrange(fecha_hora_inicio_pactada, fecha_hora_fin_pactada, '[)') WITH &&
  ) WHERE (estado IN ('ACTIVO', 'EN_INSPECCION', 'EN_LIQUIDACION'));
  ```
  Imposibilita el solapamiento de fechas para un mismo vehículo incluso ante solicitudes concurrentes de múltiples agentes.

### 📋 Contratos, Garantías y Generación de PDF
- Verificación en tiempo real de licencias de conducir vigentes (RF-11) y semáforo de riesgo crediticio (RF-12).
- Gestión de conductores adicionales autorizados por contrato (RF-13).
- Tipos de cobertura de seguro: *Básica*, *Media* o *Todo Riesgo / Total*.
- Emisión automatizada del contrato formal en PDF con membrete, términos legales y detalle de fianza (RF-39).

### 🔧 Taller Mecánico y Mantenimientos
- Apertura de órdenes de mantenimiento preventivo y correctivo (RF-31).
- Bloqueo operativo inmediato del vehículo impidiendo que sea ofertado en reservas o contratos (RF-32).
- Liquidación de costos de taller (repuestos + mano de obra) y reactivación a estado `DISPONIBLE` (RF-33).

### 📈 Analítica y Reportes Ejecutivos
- Dashboard en tiempo real con KPIs de recaudación, ocupación y disponibilidad.
- Generación de reportes de ingresos por rango de fechas (RF-34), tasa de ocupación de flota (RF-35) e historial de clientes (RF-36).
- Exportación multiformato estándar: CSV, PDF y JSON (RF-37).

---

## 🏗️ Arquitectura del Sistema

El proyecto sigue una arquitectura desacoplada por capas guiada por principios **SOLID** y **Clean Architecture**:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   CAPA DE PRESENTACIÓN (DESKTOP GUI)                   │
│       PySide6 (Qt 6) | Views, Dialogs, Signals/Slots, Controllers      │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTP / JSON
┌──────────────────────────────────▼─────────────────────────────────────┐
│                 CAPA CLIENTE HTTP (api_client)                         │
│        HTTPX Async/Sync Client | Session State | JWT Injection         │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ REST Endpoints
┌──────────────────────────────────▼─────────────────────────────────────┐
│                 CAPA BACKEND RESTful API (FastAPI)                     │
│    Routers | Pydantic v2 Schemas | Dependencies | Error Handlers       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Python Objects / Domain
┌──────────────────────────────────▼─────────────────────────────────────┐
│                 CAPA DE SERVICIOS Y DOMINIO DE NEGOCIO                 │
│      Domain Models | Business Rules | State Machines | Validations     │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ SQLAlchemy 2.0 ORM
┌──────────────────────────────────▼─────────────────────────────────────┐
│                 CAPA DE PERSISTENCIA Y REPOSITORIOS                    │
│      SQLAlchemy Declarative Models | Connection Pool (psycopg)         │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ SQL + RLS Policies + GiST
┌──────────────────────────────────▼─────────────────────────────────────┐
│                   MOTOR DE BASE DE DATOS RELACIONAL                    │
│     PostgreSQL 15+ (19 Tablas | Triggers | Views | SPs | btree_gist)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Estructura del Repositorio

```text
agencia_de_autos/
├── main.py                          # Entry point de la aplicación de escritorio PySide6
├── requirements.txt                 # Dependencias completas del ecosistema (GUI, API, ORM, DB)
├── requirements-api.txt             # Dependencias ligeras para Backend API (Docker / Cloud)
├── .env.example                     # Plantilla de variables de entorno
├── docs/                            # Documentación de análisis, diseño y arquitectura
│   ├── ANALISIS_Y_DISENIO.md        # Especificación de requisitos y reglas de negocio
│   ├── ESPECIFICACION_REQUISITOS_FUNCIONALES.txt # Detalle exhaustivo de los 40 RFs
│   └── diagrams/                    # Catálogo maestro de diagramas en Mermaid
│       ├── casos_de_uso/            # Diagramas de Casos de Uso (Transversal y por 4 Roles)
│       ├── clases_orm/              # Diagrama de Clases SQLAlchemy 2.0 ORM
│       ├── entidad_relacion/        # Diagrama Entidad-Relación (Crow's Foot, 19 tablas)
│       └── modelo_relacional/       # Modelo Físico Relacional de PostgreSQL
├── src/                             # Código fuente del sistema
│   ├── api/                         # Backend RESTful en FastAPI
│   │   ├── main.py                  # Servidor ASGI, manejadores de excepción y OpenAPI
│   │   ├── dependencies.py          # Inyección de dependencias (Auth, Contexto RLS, DB)
│   │   ├── routers/                 # Endpoints REST (Auth, Clientes, Flota, Contratos, etc.)
│   │   └── schemas/                 # Esquemas Pydantic v2 de validación I/O
│   ├── api_client/                  # Cliente HTTP desacoplado para la UI de escritorio
│   │   └── client.py                # Implementación con HTTPX y almacenamiento de token JWT
│   ├── config/                      # Configuración tipada y lectura de .env
│   │   └── settings.py              # Clase Settings con validaciones
│   ├── core/                        # Utilidades transversales
│   │   ├── exceptions.py            # Jerarquía tipada de excepciones de dominio
│   │   ├── logger.py                # Sistema centralizado de logging con rotación
│   │   ├── security.py              # Funciones de hashing bcrypt y tokens JWT
│   │   └── session.py               # Gestión de sesión de usuario y contexto activo
│   ├── database/                    # Capa de base de datos
│   │   ├── connection.py            # Pool de conexiones psycopg
│   │   ├── orm_base.py              # Motor SQLAlchemy 2.0 y base declarativa
│   │   ├── orm_models.py            # 19 Modelos ORM mapeados
│   │   └── migrations/              # Scripts SQL ordenados
│   │       ├── 01_create_schema.sql # DDL: Tablas, RLS, triggers, índices GiST
│   │       ├── 02_seed_data.sql     # DML: Semilla de agencias, usuarios, flota y contratos
│   │       └── 03_test_validations.sql # Pruebas SQL de integridad y anti-overbooking
│   ├── domain/                      # Modelos puros del dominio y enumeraciones
│   │   ├── enums.py                 # Enums: RolUsuario, EstadoVehiculo, EstadoReserva, etc.
│   │   └── models.py                # Data classes del dominio
│   ├── repositories/                # Patrón Repositorio
│   │   └── orm/                     # Implementación de repositorios con SQLAlchemy 2.0
│   ├── services/                    # Lógica de negocio y orquestación de servicios
│   └── ui/                          # Interfaz gráfica de usuario con PySide6
│       ├── components/              # Widgets reutilizables (Sidebar, Header, Cards)
│       ├── controllers/             # Controladores de enlace UI <-> Backend
│       └── views/                   # Vistas principales y ventanas modales de diálogo
└── tests/                           # Suite integral de pruebas automatizadas
    ├── run_all.py                   # Ejecutor maestro de todas las suites
    ├── test_auth.py                 # Pruebas de autenticación y hashing
    ├── test_multitenancy.py         # Pruebas de aislamiento RLS entre agencias
    ├── test_api_endpoints.py        # Pruebas de integración HTTP a la API REST
    ├── test_orm_repositories.py     # Pruebas de persistencia SQLAlchemy 2.0
    ├── test_reservations.py         # Pruebas de lógica de reservas y prevención de cruce
    ├── test_contracts.py            # Pruebas de apertura y formalización de contratos
    ├── test_returns.py              # Pruebas de inspección y balance de liquidación
    ├── test_maintenances.py         # Pruebas de bloqueo de flota por taller
    └── test_ui_components.py        # Pruebas de componentes gráficos Qt
```

---

## 📊 Catálogo de Diagramas Técnicos

Toda la arquitectura y diseño conceptual del sistema se encuentra documentada en formato **Mermaid (`.mmd`)** y renderizada en documentos Markdown (`.md`):

| Módulo de Diagramas | Ubicación | Descripción |
| :--- | :--- | :--- |
| **Casos de Uso Transversal** | [Use_Case_Diagram_Autenticacion_y_Sesion.md](docs/diagrams/casos_de_uso/Use_Case_Diagram_Autenticacion_y_Sesion.md) | Diagrama unificado de los 4 roles con Login, Logout, RLS y bloqueo de cuentas. |
| **Casos de Uso por Rol** | [docs/diagrams/casos_de_uso/](docs/diagrams/casos_de_uso/README.md) | Diagramas modulares para Administrador, Gerente, Agente de Ventas e Inspector de Taller. |
| **Diagrama de Clases ORM** | [docs/diagrams/clases_orm/](docs/diagrams/clases_orm/README.md) | Modelado declarativo de **SQLAlchemy 2.0** y entidades del dominio. |
| **Diagrama Entidad-Relación** | [docs/diagrams/entidad_relacion/](docs/diagrams/entidad_relacion/README.md) | Diagrama E-R conceptual y lógico de las 19 tablas en notación *Crow's Foot*. |
| **Modelo Relacional de BD** | [docs/diagrams/modelo_relacional/](docs/diagrams/modelo_relacional/README.md) | Esquema relacional físico de **PostgreSQL 15+** con PKs, FKs, constraints GiST e índices. |

---

## 🛠️ Requisitos Previos

Antes de comenzar, asegúrate de contar con las siguientes herramientas instaladas:

1. **Python 3.12+** (o Python 3.13):
   ```bash
   python --version
   ```
2. **PostgreSQL 15+** en ejecución local o en red:
   ```bash
   psql --version
   ```
3. **Git**:
   ```bash
   git --version
   ```

---

## 🚀 Guía de Instalación y Puesta en Marcha

Sigue estos pasos ordenados para desplegar el proyecto en tu máquina local:

### 1. Clonar el Repositorio
```bash
git clone https://github.com/TU_USUARIO/agencia_de_autos.git
cd agencia_de_autos
```

### 2. Crear y Activar el Entorno Virtual

- **En Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **En Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Instalar Dependencias del Proyecto
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar las Variables de Entorno
Copia la plantilla `.env.example` para crear tu archivo `.env` local:

- **En Windows:**
  ```powershell
  Copy-Item .env.example .env
  ```
- **En Linux / macOS:**
  ```bash
  cp .env.example .env
  ```

Edita `.env` con las credenciales de tu servidor PostgreSQL:
```ini
# Informacion General
APP_NAME="AutoRent Pro - Sistema de Alquiler de Automóviles"
APP_ENV=development
APP_DEBUG=true

# Base de Datos PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=agencia_autos_db
DB_USER=postgres
DB_PASSWORD=tu_contraseña_aqui

# Pool de Conexiones
DB_POOL_MIN=1
DB_POOL_MAX=10
DB_TIMEOUT=30

# API RESTful (FastAPI)
API_HOST=127.0.0.1
API_PORT=8000
API_BASE_URL=http://127.0.0.1:8000
API_TIMEOUT=15.0
JWT_SECRET_KEY=clave-secreta-para-tokens-jwt-en-desarrollo
JWT_EXPIRATION_SECONDS=28800
```

### 5. Preparar la Base de Datos PostgreSQL

1. Crea la base de datos en PostgreSQL:
   ```sql
   CREATE DATABASE agencia_autos_db;
   ```
2. Ejecuta los scripts de migración en orden estricto:
   - **Migración 01 — Esquema DDL y RLS:**
     ```bash
     psql -U postgres -d agencia_autos_db -f src/database/migrations/01_create_schema.sql
     ```
   - **Migración 02 — Semilla de Datos Iniciales (Seeds):**
     ```bash
     psql -U postgres -d agencia_autos_db -f src/database/migrations/02_seed_data.sql
     ```
   - **Migración 03 — Validaciones de Reglas de Negocio:**
     ```bash
     psql -U postgres -d agencia_autos_db -f src/database/migrations/03_test_validations.sql
     ```

---

## 🖥️ Cómo Ejecutar el Proyecto

El sistema opera en modalidad de cliente-servidor desacoplado:

### Opción 1: Iniciar el Servidor Backend REST API (FastAPI)

En una terminal activa con el entorno virtual:
```bash
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Una vez iniciado, dispones de:
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Documentación Interactiva Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Documentación OpenAPI ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Opción 2: Iniciar la Aplicación de Escritorio (PySide6 GUI)

En una segunda terminal con el entorno virtual activo (mientras la API está corriendo):
```bash
python main.py
```

Se abrirá la pantalla de autenticación gráfica de **AutoRent Pro**, conectándose transparentemente a la API RESTful.

---

## 🔑 Credenciales de Acceso para Pruebas

Los datos semilla (`02_seed_data.sql`) cargan usuarios iniciales para la **Agencia Central Managua** (`AUT-MGA-01`):

| Usuario | Contraseña | Rol Asignado | Alcance Funcional |
| :--- | :--- | :--- | :--- |
| `admin` | `Admin123*` | **ADMINISTRADOR** | Control total, usuarios, agencias, catálogo maestro y auditoría. |
| `gerente1` | `Gerente123*` | **GERENTE** | Dashboard gerencial, KPIs de recaudación, reportes y exportación. |
| `agente1` | `Agente123*` | **AGENTE_VENTAS** | Clientes, reservas, apertura de contratos, garantías y liquidaciones. |
| `taller1` | `Taller123*` | **INSPECTOR_TALLER** | Inspección física (odómetro/combustible), daños y órdenes de taller. |

> [!NOTE]
> Las contraseñas están almacenadas con hash real en `bcrypt`. Puedes desbloquear cualquier usuario bloqueado desde la interfaz del Administrador.

---

## 🧪 Pruebas de Calidad (Testing & QA)

El proyecto cuenta con una cobertura integral de pruebas que validan desde reglas de negocio hasta persistencia ORM y respuestas de la API.

### Ejecutar la Suite Completa
Para correr todas las suites de prueba en secuencia:
```bash
python -m tests.run_all
```

### Ejecutar Suites Específicas
Puedes ejecutar individualmente cualquier módulo de prueba con el ejecutor estándar de Python:

```bash
# Pruebas de Autenticación, Hashing y Bloqueo de Cuentas
python -m unittest tests/test_auth.py

# Pruebas de Aislamiento Multi-Tenant por Row Level Security (RLS)
python -m unittest tests/test_multitenancy.py

# Pruebas de Endpoints de la API RESTful (FastAPI + TestClient)
python -m unittest tests/test_api_endpoints.py

# Pruebas de Repositorios ORM SQLAlchemy 2.0
python -m unittest tests/test_orm_repositories.py

# Pruebas de Reglas de Negocio en Reservas y Contratos
python -m unittest tests/test_reservations.py
python -m unittest tests/test_contracts.py

# Pruebas de Devolución, Inspección y Taller
python -m unittest tests/test_returns.py
python -m unittest tests/test_maintenances.py
```

---

## 🔒 Seguridad y Multi-Tenancy

AutoRent Pro implementa un modelo de seguridad en profundidad (*Defense in Depth*):

```text
[Solicitud HTTP con Bearer JWT]
             │
             ▼
[Middleware FastAPI: Valida Token + Extrae tenant_id y rol]
             │
             ▼
[Inyección de Sesión BD: SET LOCAL app.current_tenant_id = X]
             │
             ▼
[PostgreSQL Engine: Evalúa Políticas RLS en cada Consulta]
             │
             ▼
[Resultado Filtrado Garantizado a Nivel de Kernel de BD]
```

- **Row Level Security (RLS) en 19 tablas:** Previene fugas de datos (*data leaks*) entre sucursales incluso si una consulta omitiese un filtro `WHERE`.
- **Procedimientos Almacenados Seguros:** Funciones con `SECURITY DEFINER` para operaciones privilegiadas controladas (como setear el contexto de agencia).
- **Protección contra Inyección SQL:** Todas las consultas se canalizan mediante parámetros bind de **SQLAlchemy 2.0** o consultas parametrizadas de **psycopg**.

---

## 👥 Roles del Sistema

| Rol | Responsabilidad Principal | Vistas de Acceso Habilitadas |
| :--- | :--- | :--- |
| **Administrador** | Gobierno del sistema, configuración global y auditoría | Gestión de Usuarios, Catálogos Maestros, Agencias, Pista de Auditoría, Desbloqueo de Cuentas. |
| **Gerente** | Toma de decisiones estratégicas y monitoreo financiero | Dashboard Ejecutivo, Reportes de Recaudación, Ocupación de Flota, Comportamiento de Clientes. |
| **Agente de Ventas** | Operaciones de mostrador y transacciones con clientes | Registro de Clientes, Reservas con Anti-Overbooking, Apertura de Contratos, Despacho, Liquidación de Pagos. |
| **Inspector de Taller** | Inspección física de vehículos y mantenimiento mecánico | Check-In/Check-Out, Comparativa de Odómetro y Combustible, Registro de Averías, Órdenes de Mantenimiento. |

---

## 🏛️ Créditos Académicos

Proyecto desarrollado en el marco académico de:

- **Institución:** Universidad Nacional Autónoma de Nicaragua (UNAN)
- **Facultad / Carrera:** Ingeniería en Sistemas de Información
- **Asignatura:** Proyecto Integrador II
- **Fase Actual:** Fase 2 / Fase 3 — Persistencia Relacional Avanzada, ORM SQLAlchemy 2.0, API RESTful y Cliente de Escritorio.

---

<p align="center">
  <b>AutoRent Pro</b> — Transformando la gestión de flotas con solidez arquitectónica, seguridad relacional y alto rendimiento.
</p>

# Guía de Instalación y Ejecución de la Base de Datos PostgreSQL
## Sistema de Control de Alquiler de Automóviles (UNAN)

Esta carpeta contiene los scripts SQL ordenados cronológicamente para la Fase 1 del proyecto.

---

### Requisitos Previos
* PostgreSQL 15 o superior instalado y en ejecución.
* Un usuario con privilegios de creación de base de datos (`postgres` u otro).
* Extensión `btree_gist` (incluida en el instalador estándar de PostgreSQL).

---

### Pasos para la Inicialización

#### 1. Crear la Base de Datos
Desde la terminal de comandos (PowerShell / Bash) o desde **pgAdmin**:

```bash
# Conectarse a postgres y crear la base de datos
psql -U postgres -c "CREATE DATABASE agencia_autos_db WITH ENCODING 'UTF8';"
```

#### 2. Ejecutar los Scripts en Orden Estricto

##### Opción A: Desde Línea de Comandos (`psql`)
Ejecutar los scripts dentro de la carpeta `src/database/migrations/`:

```bash
# 1. Crear el esquema, tablas, restricciones, índices y triggers
psql -U postgres -d agencia_autos_db -f src/database/migrations/01_create_schema.sql

# 2. Cargar datos maestros y escenarios de prueba
psql -U postgres -d agencia_autos_db -f src/database/migrations/02_seed_data.sql

# 3. Ejecutar pruebas automatizadas de validación
psql -U postgres -d agencia_autos_db -f src/database/migrations/03_test_validations.sql
```

##### Opción B: Desde pgAdmin o DBeaver
1. Abrir la herramienta gráfica y conectarse al servidor local de PostgreSQL.
2. Crear la base de datos `agencia_autos_db`.
3. Abrir la consola de consulta (Query Tool) sobre `agencia_autos_db`.
4. Abrir y ejecutar en orden los tres archivos:
   * `01_create_schema.sql` (Ejecutar primero)
   * `02_seed_data.sql` (Ejecutar segundo)
   * `03_test_validations.sql` (Ejecutar para verificar)

---

### Resumen de Archivos Generados
* `01_create_schema.sql`: DDL completo con tablas, llaves primarias/foráneas, restricciones `CHECK`, índices GiST y B-Tree, y triggers de negocio.
* `02_seed_data.sql`: Carga de catálogo básico (marcas, modelos, categorías, seguros, roles, usuarios) y cuatro casos de prueba del ciclo de vida.
* `03_test_validations.sql`: Bloques anónimos PL/pgSQL que ponen a prueba y demuestran la prevención de solapamientos (overbooking), validación de licencias y coherencia de odómetros.

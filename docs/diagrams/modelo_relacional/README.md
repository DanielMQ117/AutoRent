# Catálogo del Modelo Relacional de Base de Datos - AutoRent Pro

Modelado del **Esquema Relacional Físico y Lógico** de las **19 tablas en PostgreSQL 15+** implementado en [src/database/migrations/01_create_schema.sql](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/src/database/migrations/01_create_schema.sql).

El modelado relacional sigue las directrices de la teoría relacional y los estándares de ingeniería de software:
- **Esquema Compartido Multi-Tenancy:** Aislamiento estricto por inquilino mediante la columna discriminadora `tenant_id` y políticas Row-Level Security (RLS).
- **Integridad Referencial Completa:** Claves Primarias (`PK`), Claves Foráneas (`FK`), Claves Únicas (`UNIQUE`), restricciones de chequeo (`CHECK`) y restricciones temporales anti-overbooking (`EXCLUDE USING gist`).
- **Notación Relacional de Codd:** Esquemas algebraicos formales para cada relación con PKs y referencias explícitas.

---

### Entregables del Módulo

| Documento | Formato | Descripción |
| :--- | :--- | :--- |
| [Modelo_Relacional.mmd](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/modelo_relacional/Modelo_Relacional.mmd) | Código fuente Mermaid (`.mmd`) | Código fuente puro Mermaid `erDiagram` con las 19 tablas físicas en minúscula, sus tipos físicos, columnas PK/FK y las relaciones con nombres de constraint foráneo. |
| [Modelo_Relacional.md](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/modelo_relacional/Modelo_Relacional.md) | Documento renderizado (`.md`) | Vista previa del diagrama global, 4 diagramas modulares de profundización, notación formal de Codd (19 esquemas), matriz de claves foráneas con reglas `ON DELETE` y catálogo de índices B-Tree. |

---

### Recursos de Referencia

* [src/database/migrations/01_create_schema.sql](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/src/database/migrations/01_create_schema.sql): Script DDL oficial de PostgreSQL con la definición completa del esquema.
* [src/database/orm_models.py](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/src/database/orm_models.py): Mapeo relacional de objetos correspondiente en SQLAlchemy 2.0.
* [docs/diagrams/entidad_relacion/Diagrama_Entidad_Relacion.md](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/entidad_relacion/Diagrama_Entidad_Relacion.md): Diagrama Entidad-Relación conceptual/lógico complementario.

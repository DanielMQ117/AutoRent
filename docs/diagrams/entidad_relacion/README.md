# Catálogo de Diagramas Entidad-Relación (ER) - AutoRent Pro

Modelado de datos conceptual y lógico de las **19 tablas del esquema relacional en PostgreSQL 15+** implementado en [src/database/migrations/01_create_schema.sql](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/src/database/migrations/01_create_schema.sql).

El modelado sigue los estándares de la notación **Crow's Foot (Pata de Gallo)**:
* **Entidades:** Representadas en mayúsculas y singular (`AGENCIA`, `VEHICULO`, `CONTRATO`, etc.).
* **Atributos:** Tipado explícito (`bigint`, `varchar`, `numeric`, `boolean`, `timestamptz`, `date`, `text`).
* **Claves:** Marcadores unívocos para Clave Primaria (`PK`) y Claves Foráneas (`FK`).
* **Cardinalidades:** `||--o{` (1 a 0..*), `||--|{` (1 a 1..*), `||--o|` (1 a 0..1), `|o--o|` (0..1 a 0..1).
* **Multi-Tenancy:** Aislamiento integral de datos mediante `tenant_id` y políticas Row-Level Security (RLS).

---

### Entregables del Módulo

| Documento | Formato | Descripción |
| :--- | :--- | :--- |
| [Diagrama_Entidad_Relacion.mmd](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/entidad_relacion/Diagrama_Entidad_Relacion.mmd) | Código fuente Mermaid (`.mmd`) | Código fuente puro Mermaid `erDiagram` con las 19 entidades, sus atributos, tipos, claves (`PK`/`FK`) y todas las relaciones de cardinalidad. |
| [Diagrama_Entidad_Relacion.md](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/entidad_relacion/Diagrama_Entidad_Relacion.md) | Documento renderizado (`.md`) | Vista previa del diagrama global, 4 diagramas modulares de profundización por área funcional, matriz de entidades y claves, y documentación de restricciones. |

---

### Recursos de Referencia

* [ejemplo_de_codigo.txt](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/entidad_relacion/ejemplo_de_codigo.txt): Especificaciones y sintaxis Mermaid para diagramas `erDiagram` (Crow's foot).
* [src/database/migrations/01_create_schema.sql](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/src/database/migrations/01_create_schema.sql): Script DDL canónico de la base de datos con las 19 tablas, restricciones `CHECK`, `UNIQUE` y exclusiones `GiST`.
* [src/database/orm_models.py](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/src/database/orm_models.py): Modelos declarativos SQLAlchemy 2.0 correspondientes.

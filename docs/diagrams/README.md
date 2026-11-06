# Catálogo de Diagramas de Arquitectura y Base de Datos - AutoRent Pro

Índice central de diagramas de análisis, diseño y arquitectura del sistema **AutoRent Pro** modelados en formato Mermaid (`.mmd` y `.md`).

---

### Módulos de Diagramación Disponibles

1. **[Diagramas de Clases del ORM](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/clases_orm/README.md)** (`clases_orm/`):
   Modelos declarativos de **SQLAlchemy 2.0 ORM** y entidades del dominio (`src/database/orm_models.py` y `src/domain/models.py`), siguiendo la Guía Didáctica de Diagramas de Clases de la UNAN.

2. **[Diagramas Entidad-Relación](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/entidad_relacion/README.md)** (`entidad_relacion/`):
   Modelado conceptual y lógico de las 19 entidades del sistema, atributos tipados y cardinalidades en notación **Crow's Foot** (Pata de Gallo).

3. **[Diagramas de Casos de Uso](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/README.md)** (`casos_de_uso/`):
   Interacciones de los 4 actores del sistema (**Administrador**, **Gerente**, **Agente de Ventas**, **Inspector de Taller**) con los requisitos funcionales del negocio bajo la especificación `usecase-beta`.

4. **[Modelo Relacional de Base de Datos](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/modelo_relacional/README.md)** (`modelo_relacional/`):
   Estructura relacional física del esquema **PostgreSQL 15+** (`01_create_schema.sql`), detallando tablas en minúscula, claves primarias (`PK`), claves foráneas (`FK`), reglas de integridad referencial (`ON DELETE RESTRICT/CASCADE/SET NULL`), restricciones temporales GiST, notación formal de Codd e índices de rendimiento B-Tree.

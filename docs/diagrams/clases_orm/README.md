# Catálogo de Diagramas de Clases del ORM - AutoRent Pro

Modelado de clases orientado a objetos de los modelos **SQLAlchemy 2.0 DeclarativeBase** y entidades de base de datos implementados en [src/database/orm_models.py](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/src/database/orm_models.py) y [src/domain/models.py](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/src/domain/models.py).

El modelado sigue las directrices académicas de la **Guía Didáctica de Diagramas de Clases (UNAN)**:
- **Estructura en 3 compartimentos:** Nombre de la clase, atributos privados (`-`) tipados y métodos públicos (`+`).
- **Relaciones formales:** Generalización (`<|--`), composición fuerte con eliminación en cascada (`*--`), y asociaciones dirigidas con cardinalidades (`1`, `0..1`, `1..*`, `*`).
- **Aislamiento Multi-Tenancy:** Inquilino raíz (`AgenciaORM`) y aislamiento mediante `tenant_id` y RLS.

---

### Entregables del Módulo

| Documento | Formato | Descripción |
| :--- | :--- | :--- |
| [Diagrama_Clases_ORM.mmd](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/clases_orm/Diagrama_Clases_ORM.mmd) | Código fuente Mermaid (`.mmd`) | Código fuente puro Mermaid `classDiagram` con las 19 entidades ORM, la superclase `Base`, atributos, métodos y todas las relaciones. |
| [Diagrama_Clases_ORM.md](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/clases_orm/Diagrama_Clases_ORM.md) | Documento renderizado (`.md`) | Vista previa del diagrama global, 4 diagramas modulares de profundización por área funcional, diccionario de clases y matriz de cumplimiento UNAN. |

---

### Recursos de Referencia

* [Guia_Didactica_Diagramas_de_Clases.pdf](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/clases_orm/Guia_Didactica_Diagramas_de_Clases.pdf): Guía pedagógica institucional UNAN para la elaboración de diagramas de clases.
* [ejemplo_de_codigo.txt](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/clases_orm/ejemplo_de_codigo.txt): Sintaxis y especificación Mermaid para `classDiagram`.
* [src/database/orm_models.py](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/src/database/orm_models.py): Implementación real de los 19 modelos ORM en SQLAlchemy 2.0.

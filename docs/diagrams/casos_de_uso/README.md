# Catálogo de Diagramas de Casos de Uso - AutoRent Pro

Diagramas de casos de uso optimizados y estructurados bajo la especificación **Mermaid `usecase-beta`**, organizados con límites de subsistema (`systemBoundary package`), estereotipos funcionales, alta legibilidad visual (sin tablas JSON ni notas invasivas) y relaciones formales de inclusión (`<<include>>`) y extensión (`<<extend>>`).

---

### 1. Diagrama Transversal Unificado

Agrupa a los cuatro roles del sistema para modelar la capa común de seguridad de acceso, control de sesiones, aislamiento multi-agencia y políticas de bloqueo.

| Módulo Transversal | Archivo Fuente (`.mmd`) | Documento con Vista Previa (`.md`) | Alcance y Requisitos Funcionales Clave |
| :--- | :--- | :--- | :--- |
| **Autenticación, Sesión y Agencia** | [Use_Case_Diagram_Autenticacion_y_Sesion.mmd](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Autenticacion_y_Sesion.mmd) | [Use_Case_Diagram_Autenticacion_y_Sesion.md](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Autenticacion_y_Sesion.md) | **Capa Transversal Común (4 Roles):** Autenticación con credenciales y contraseña cifrada (**RF-01**), cierre de sesión seguro (**RF-02**), bloqueo automático tras intentos fallidos (**RF-03**) y selección de agencia activa multi-tenant con Row-Level Security (**RF-38**). |

---

### 2. Diagramas Específicos por Rol del Sistema

Diagramas desacoplados de la autenticación transversal, enfocados exclusivamente en las responsabilidades operativas y de negocio de cada perfil.

| Rol | Archivo Fuente (`.mmd`) | Documento con Vista Previa (`.md`) | Alcance y Requisitos Funcionales Clave |
| :--- | :--- | :--- | :--- |
| **Administrador** | [Use_Case_Diagram_Administrador.mmd](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Administrador.mmd) | [Use_Case_Diagram_Administrador.md](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Administrador.md) | **Seguridad, Auditoría y Control Maestro:** Gestión administrativa de bloqueos (**RF-03**), control de acceso RBAC (**RF-04**), pista de auditoría inmutable (**RF-05**), gestión global de usuarios, agencias y catálogos maestros. |
| **Gerente** | [Use_Case_Diagram_Gerente.mmd](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Gerente.mmd) | [Use_Case_Diagram_Gerente.md](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Gerente.md) | **Supervisión Estratégica y Analítica:** Monitoreo de KPIs de flota y contratos, reportes gerenciales de recaudación (**RF-34**), ocupación de flota (**RF-35**), historial comercial de clientes (**RF-36**) y exportación en formatos estándar (**RF-37**). |
| **Agente de Ventas** | [Use_Case_Diagram_Agente_Ventas.mmd](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Agente_Ventas.mmd) | [Use_Case_Diagram_Agente_Ventas.md](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Agente_Ventas.md) | **Operación Comercial y Contratos:** Gestión de clientes (**RF-10** a **RF-13**), reservas anti-overbooking (**RF-14** a **RF-17**), contratos, garantías y emisión PDF (**RF-18** a **RF-21**, **RF-39**), liquidaciones y cobros de extras (**RF-22** a **RF-29**). |
| **Inspector de Taller** | [Use_Case_Diagram_Inspector_Taller.mmd](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Inspector_Taller.mmd) | [Use_Case_Diagram_Inspector_Taller.md](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Inspector_Taller.md) | **Técnica, Recepción y Flota:** Control técnico de vehículos (**RF-06**, **RF-07**, **RF-09**), inspección física de retornos con odómetro y combustible (**RF-23**, **RF-24**), valuación de daños (**RF-27**, **RF-30**) y órdenes de mantenimiento (**RF-31** a **RF-33**). |

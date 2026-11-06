# Diagrama de Casos de Uso — Rol: Administrador del Sistema

## Sistema de Control y Gestión de Alquiler de Automóviles (AutoRent Pro)

Este diagrama modela de forma sintetizada y modular el comportamiento, responsabilidades y alcance operativo completo del **Administrador del Sistema**. Las funcionalidades se encuentran organizadas en 5 subsistemas delimitados mediante fronteras de paquete (`systemBoundary`): **Seguridad y Control de Acceso**, **Auditoría del Sistema**, **Gestión de Cuentas de Usuario**, **Catálogos Maestros** y **Supervisión Operativa**.

> [!NOTE]
> Las acciones comunes de inicio/cierre de sesión y selección de agencia multi-tenant (**RF-01**, **RF-02**, **RF-38**) han sido desacopladas y centralizadas en el [Diagrama Unificado de Casos de Uso — Autenticación, Sesión y Agencia](./Use_Case_Diagram_Autenticacion_y_Sesion.md).

---

## 1. Diagrama de Casos de Uso Sintetizado (Mermaid)

```mermaid
usecase-beta
direction LR
accTitle: Diagrama de Casos de Uso Resumido - Rol Administrador (AutoRent Pro)
accDescr {
  Diagrama de casos de uso resumido y modular para el rol de Administrador en AutoRent Pro.
  Estructura las operaciones en cinco subsistemas clave: Seguridad y Control de Acceso,
  Auditoría del Sistema, Gestión de Cuentas de Usuario, Catálogos Maestros y Supervisión Operativa.
  Consolida las funciones críticas garantizando la trazabilidad total de los requisitos funcionales.
}

actor Admin("Administrador del Sistema")@{ type: hollow, business: true } <<Rol Principal>>

%% ----------------------------------------------------------------------
%% Módulo 1: Seguridad y Control de Acceso
%% ----------------------------------------------------------------------
systemBoundary Seguridad_y_Control_Acceso["Seguridad y Control de Acceso"]@{ type: package }:::seguridad
  GestionBloqueo("Gestionar bloqueo y desbloqueo de cuentas (RF-03)") <<Seguridad>>:::seguridad
  ControlRBAC("Controlar accesos y privilegios basados en roles (RF-04)") <<Seguridad>>:::seguridad
end

%% ----------------------------------------------------------------------
%% Módulo 2: Auditoría del Sistema
%% ----------------------------------------------------------------------
systemBoundary Auditoria_del_Sistema["Auditoría del Sistema"]@{ type: package }:::auditoria
  AuditoriaSistema("Consultar y fiscalizar bitácora inmutable (RF-05)") <<Auditoría>>:::auditoria
end

%% ----------------------------------------------------------------------
%% Módulo 3: Gestión de Cuentas de Usuario
%% ----------------------------------------------------------------------
systemBoundary Gestion_Cuentas_Usuarios["Gestión de Cuentas de Usuario"]@{ type: package }:::core
  AdministrarUsuarios("Gestionar cuentas de usuario y credenciales") <<Gestión>>:::core
  AsignarRolesPermisos("Asignar roles y vigencia de cuentas"):::core
end

%% ----------------------------------------------------------------------
%% Módulo 4: Catálogos Maestros
%% ----------------------------------------------------------------------
systemBoundary Catalogos_Maestros["Catálogos Maestros"]@{ type: package }:::catalogos
  AdminAgencias("Administrar agencias y sedes multi-tenant") <<Catálogos>>:::catalogos
  AdminCatalogosFlota("Administrar marcas, modelos, categorías y pólizas"):::catalogos
end

%% ----------------------------------------------------------------------
%% Módulo 5: Supervisión Operativa
%% ----------------------------------------------------------------------
systemBoundary Supervision_Operativa["Supervisión Operativa"]@{ type: package }:::supervision
  SupervisionPlataforma("Supervisar operaciones globales de flota, clientes y contratos") <<Supervisión>>:::supervision
  ReportesAnaliticos("Consultar y exportar reportes analíticos globales"):::supervision
end

%% ----------------------------------------------------------------------
%% Asociaciones del Actor Principal (Administrador)
%% ----------------------------------------------------------------------
Admin --> GestionBloqueo
Admin --> ControlRBAC
Admin --> AuditoriaSistema
Admin --> AdministrarUsuarios
Admin --> AdminAgencias
Admin --> AdminCatalogosFlota
Admin admin_sup@-- "supervisa plataforma" ---> SupervisionPlataforma

%% ----------------------------------------------------------------------
%% Relaciones de Dependencia e Inclusión
%% ----------------------------------------------------------------------
AdministrarUsuarios ..> : include AsignarRolesPermisos
AdministrarUsuarios inc_aud_usr@..> : include AuditoriaSistema
GestionBloqueo inc_aud_desb@..> : include AuditoriaSistema
SupervisionPlataforma ..> : include ReportesAnaliticos

%% ----------------------------------------------------------------------
%% Definiciones de Clases de Estilo
%% ----------------------------------------------------------------------
classDef system stroke:#1e3a8a,stroke-width:2px
classDef critico stroke:#dc2626,stroke-width:2px
classDef seguridad stroke:#0284c7,stroke-width:2px
classDef core stroke:#16a34a,stroke-width:2px
classDef catalogos stroke:#d97706,stroke-width:2px
classDef supervision stroke:#7c3aed,stroke-width:2px
classDef auditoria stroke:#475569,stroke-width:2px

%% ----------------------------------------------------------------------
%% Animaciones y Estilos de Enlaces
%% ----------------------------------------------------------------------
admin_sup@{ animation: fast }
style inc_aud_usr stroke:#475569,stroke-width:2px
style inc_aud_desb stroke:#475569,stroke-width:2px
```

---

## 2. Matriz de Requisitos Funcionales por Módulo

> **Nota:** Las acciones transversales de inicio de sesión multi-tenant (**RF-01**), cierre de sesión (**RF-02**) y selección de agencia con aislamiento RLS (**RF-38**) se gestionan de forma centralizada en el [Diagrama Unificado de Autenticación, Sesión y Agencia](./Use_Case_Diagram_Autenticacion_y_Sesion.md).

| Módulo / Subsistema | Requisitos Funcionales | Acción del Caso de Uso Sintetizado | Tipo de Relación / Rol |
| :--- | :--- | :--- | :--- |
| **Seguridad y Control de Acceso** | **RF-03** | Gestionar bloqueo y desbloqueo de cuentas (RF-03) | Control preventivo tras 3 intentos fallidos y desbloqueo administrativo |
| | **RF-04** | Controlar accesos y privilegios basados en roles (RF-04) | Matriz RBAC sin restricciones para Administrador |
| **Auditoría del Sistema** | **RF-05** | Consultar y fiscalizar bitácora inmutable (RF-05) | Consulta inmutable de transacciones, IP, acción y timestamp |
| **Gestión de Cuentas de Usuario** | **Gestión** | Gestionar cuentas de usuario y credenciales | Creación, edición, reseteo de claves y activación de cuentas |
| | **RBAC** | Asignar roles y vigencia de cuentas | Inclusión en Gestión de Usuarios (`include`) |
| **Catálogos Maestros** | **Catálogos** | Administrar agencias y sedes multi-tenant | Mantenimiento de inquilinos, RUC, direcciones y teléfonos |
| | **Catálogos** | Administrar marcas, modelos, categorías y pólizas | Catálogos globales de flota, tarifas base y seguros |
| **Supervisión Operativa** | **Supervisión** | Supervisar operaciones globales de flota, clientes y contratos | Vista transversal del estado de la flota, cartera y contratos |
| | **Supervisión** | Consultar y exportar reportes analíticos globales | Inclusión en Supervisión Operativa (`include`) |

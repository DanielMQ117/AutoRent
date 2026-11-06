# Diagrama de Casos de Uso — Rol: Administrador del Sistema

## Sistema de Control y Gestión de Alquiler de Automóviles (AutoRent Pro)

Este diagrama modela el comportamiento, responsabilidades y alcance operativo completo del **Administrador del Sistema**, contemplando los requisitos de seguridad multi-tenant, gestión de cuentas de usuario con roles (RBAC), auditoría inmutable, administración de catálogos maestros y supervisión integral de todos los módulos del sistema.

```mermaid
usecase-beta
direction LR
accTitle: Diagrama de Casos de Uso - Rol Administrador (AutoRent Pro)
accDescr {
  Diagrama de casos de uso para el rol Administrador en el sistema AutoRent Pro.
  Representa los flujos de autenticación multi-tenant, cierre de sesión,
  gestión de usuarios y accesos con control de privilegios RBAC,
  desbloqueo administrativo de cuentas, consulta de bitácora de auditoría inmutable,
  administración de catálogos maestros y supervisión integral de las operaciones de la plataforma.
}

actor Admin("Administrador del Sistema")@{ type: hollow, business: true } <<Rol Principal>>

systemBoundary autoRent["Sistema AutoRent Pro - Gestión y Administración"]@{ type: package }:::system
  %% ----------------------------------------------------------------------
  %% Módulo 1: Seguridad, Autenticación y Tenencia Múltiple
  %% ----------------------------------------------------------------------
  UC_Login("RF-01: Iniciar Sesión Multi-Tenant") <<Seguridad>>:::critico
  UC_Logout("RF-02: Cerrar Sesión del Sistema") <<Seguridad>>:::seguridad
  UC_Tenant("RF-38: Seleccionar Agencia y Aislamiento Multi-Tenant") <<MultiTenant>>:::seguridad
  UC_BloqueoAuto("RF-03: Bloqueo de Cuenta por Intentos Fallidos") <<Seguridad>>:::critico
  UC_DesbloqueoAdmin("RF-03: Desbloqueo Administrativo de Cuentas") <<Seguridad>>:::seguridad
  UC_RBAC("RF-04: Control de Acceso Basado en Roles RBAC") <<Seguridad>>:::seguridad
  UC_Auditoria("RF-05: Consultar Bitácora de Auditoría Inmutable") <<Auditoría>>:::auditoria
  UC_RegAuditoria("RF-05: Registrar Evento Crítico en Bitácora") <<Auditoría>>:::auditoria

  %% ----------------------------------------------------------------------
  %% Módulo de Gestión de Cuentas de Usuario y Accesos
  %% ----------------------------------------------------------------------
  UC_GestionUsuarios("Gestión Integral de Cuentas de Usuario") <<Gestión>>:::core
  UC_CrearUsuario("Crear Nueva Cuenta de Usuario"):::core
  UC_EditarUsuario("Editar Perfil y Asignar Rol"):::core
  UC_DesactivarUsuario("Activar o Desactivar Cuenta"):::core
  UC_ResetPassword("Resetear Contraseña de Acceso"):::core

  %% ----------------------------------------------------------------------
  %% Módulo de Gestión de Catálogos Maestros
  %% ----------------------------------------------------------------------
  UC_CatalogosMaestros("Gestión de Catálogos Maestros") <<Catálogos>>:::catalogos
  UC_CatAgencias("Administrar Agencias y Sucursales"):::catalogos
  UC_CatMarcasModelos("Administrar Marcas y Modelos"):::catalogos
  UC_CatCategorias("Administrar Categorías de Flota y Tarifas"):::catalogos
  UC_CatPolizas("Administrar Pólizas de Seguro y Coberturas"):::catalogos

  %% ----------------------------------------------------------------------
  %% Módulo de Supervisión Integral de la Plataforma
  %% ----------------------------------------------------------------------
  UC_SupervisionGlobal("Supervisión Integral de Operaciones") <<Supervisión>>:::supervision
  UC_SupFlota("Supervisar Flota y Alertas de Kilometraje"):::supervision
  UC_SupClientes("Supervisar Clientes y Licencias"):::supervision
  UC_SupContratos("Supervisar Reservas, Contratos y Devoluciones"):::supervision
  UC_SupMantenimiento("Supervisar Órdenes de Mantenimiento y Bloqueos"):::supervision
  UC_ReportesAnalitica("Consultar y Exportar Reportes Analíticos"):::supervision
end

Admin admin_login@-- "inicia sesión" ---> UC_Login
Admin --> UC_Logout
Admin --> UC_GestionUsuarios
Admin --> UC_CatalogosMaestros
Admin --> UC_RBAC
Admin --> UC_Auditoria
Admin --> UC_DesbloqueoAdmin
Admin admin_sup@-- "supervisa plataforma" ---> UC_SupervisionGlobal

UC_Login inc_tenant@..> : include UC_Tenant
UC_BloqueoAuto ext_bloq@..> : extend UC_Login

UC_GestionUsuarios inc_usr_crear@..> : include UC_CrearUsuario
UC_GestionUsuarios inc_usr_edit@..> : include UC_EditarUsuario
UC_GestionUsuarios inc_usr_desact@..> : include UC_DesactivarUsuario
UC_GestionUsuarios inc_usr_reset@..> : include UC_ResetPassword
UC_GestionUsuarios inc_usr_desbloq@..> : include UC_DesbloqueoAdmin
UC_GestionUsuarios inc_usr_aud@..> : include UC_RegAuditoria

UC_CatalogosMaestros inc_cat_age@..> : include UC_CatAgencias
UC_CatalogosMaestros inc_cat_mar@..> : include UC_CatMarcasModelos
UC_CatalogosMaestros inc_cat_cat@..> : include UC_CatCategorias
UC_CatalogosMaestros inc_cat_pol@..> : include UC_CatPolizas
UC_CatalogosMaestros inc_cat_aud@..> : include UC_RegAuditoria

UC_SupervisionGlobal inc_sup_flota@..> : include UC_SupFlota
UC_SupervisionGlobal inc_sup_cli@..> : include UC_SupClientes
UC_SupervisionGlobal inc_sup_ops@..> : include UC_SupContratos
UC_SupervisionGlobal inc_sup_mant@..> : include UC_SupMantenimiento
UC_SupervisionGlobal inc_sup_rep@..> : include UC_ReportesAnalitica

UC_DesbloqueoAdmin inc_desb_aud@..> : include UC_RegAuditoria

classDef system stroke:#1e3a8a,stroke-width:2px
classDef critico stroke:#dc2626,stroke-width:2px
classDef seguridad stroke:#0284c7,stroke-width:2px
classDef core stroke:#16a34a,stroke-width:2px
classDef catalogos stroke:#d97706,stroke-width:2px
classDef supervision stroke:#7c3aed,stroke-width:2px
classDef auditoria stroke:#475569,stroke-width:2px

admin_login@{ animation: fast }
admin_sup@{ animation: fast }
style inc_tenant stroke:#0284c7,stroke-width:2px
style ext_bloq stroke:#dc2626,stroke-width:2px
style inc_usr_aud stroke:#475569,stroke-width:2px
style inc_cat_aud stroke:#475569,stroke-width:2px
style inc_desb_aud stroke:#475569,stroke-width:2px
```

### Resumen de Casos de Uso Cubiertos

| Requisito Funcional | Caso de Uso | Relación UML | Descripción |
|---|---|---|---|
| **RF-01** | `UC_Login` | Asociación directa | Autenticación con contraseña hash (`bcrypt`) y resolución de agencia activa. |
| **RF-02** | `UC_Logout` | Asociación directa | Cierre voluntario y seguro de sesión invalidando el singleton `UserSession`. |
| **RF-03** | `UC_BloqueoAuto` | `<<extend>>` de `UC_Login` | Bloqueo preventivo al superar 3 intentos fallidos consecutivos. |
| **RF-03** | `UC_DesbloqueoAdmin` | Asociación directa / `<<include>>` | Desbloqueo administrativo de cuentas con registro en bitácora. |
| **RF-04** | `UC_RBAC` | Asociación directa | Control de acceso basado en roles con matriz sin restricciones para Administrador. |
| **RF-05** | `UC_Auditoria` | Asociación directa | Consulta y fiscalización de eventos inmutables en tabla `auditoria`. |
| **RF-05** | `UC_RegAuditoria` | `<<include>>` de acciones críticas | Registro forzoso de cambios en usuarios, catálogos y desbloqueos. |
| **RF-38** | `UC_Tenant` | `<<include>>` de `UC_Login` | Selección de agencia y aislamiento de datos mediante Row Level Security (RLS). |
| **Gestión Usuarios** | `UC_GestionUsuarios` | Asociación directa | Administración de cuentas: crear, editar rol, cambiar estado y reset de clave. |
| **Catálogos Maestros**| `UC_CatalogosMaestros` | Asociación directa | Mantenimiento de agencias, marcas, modelos, categorías y pólizas. |
| **Supervisión Global** | `UC_SupervisionGlobal` | Asociación directa | Supervisión total de flota, clientes, contratos, taller y reportes analíticos. |

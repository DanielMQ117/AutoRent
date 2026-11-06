# Diagrama Unificado de Casos de Uso — Autenticación, Sesión y Agencia

## Sistema de Control y Gestión de Alquiler de Automóviles (AutoRent Pro)

El presente diagrama modela de forma **unificada y transversal** los casos de uso comunes a los **cuatro roles del sistema** (**Administrador**, **Gerente**, **Agente de Ventas** e **Inspector de Taller**): el ciclo de vida de la sesión de usuario, autenticación segura con contraseñas hasheadas (`bcrypt`), resolución de sucursal con aislamiento **Row Level Security (RLS)** y terminación formal de sesión.

---

## 1. Diagrama de Casos de Uso Unificado (Mermaid)

```mermaid
usecase-beta
direction LR
accTitle: Diagrama Unificado de Casos de Uso - Autenticación, Sesión y Agencia (AutoRent Pro)
accDescr {
  Diagrama unificado de casos de uso transversal para los cuatro roles del sistema:
  Administrador, Gerente, Agente de Ventas e Inspector de Taller.
  Centraliza el ciclo de vida de la sesión de usuario: autenticación segura multi-tenant,
  resolución de agencia activa con aislamiento Row Level Security (RLS), bloqueo preventivo
  de cuenta tras intentos fallidos y cierre formal de sesión.
}

actor Admin("Administrador del Sistema")@{ type: hollow, business: true } <<Rol Sistema>>
actor Gerente("Gerente de Sucursal")@{ type: hollow, business: true } <<Rol Directivo>>
actor AgenteVentas("Agente de Ventas")@{ type: hollow, business: true } <<Rol Comercial>>
actor Inspector("Inspector de Taller")@{ type: hollow, business: true } <<Rol Taller>>

systemBoundary Gestion_Sesion_y_Tenencia["Gestión de Autenticación, Sesión y Tenencia Múltiple"]@{ type: package }:::seguridad
  Login("Iniciar sesión multi-tenant (RF-01)") <<Acceso>>:::critico
  Logout("Cerrar sesión del sistema (RF-02)") <<Acceso>>:::seguridad
  SeleccionAgencia("Seleccionar agencia activa y aislamiento RLS (RF-38)") <<MultiTenant>>:::seguridad
  BloqueoAuto("Bloquear cuenta tras 3 intentos fallidos (RF-03)") <<Seguridad>>:::critico
end

%% Conexiones de los 4 roles hacia el inicio de sesión
Admin admin_login@-- "autentica" ---> Login
Gerente ger_login@-- "autentica" ---> Login
AgenteVentas vent_login@-- "autentica" ---> Login
Inspector insp_login@-- "autentica" ---> Login

%% Conexiones de los 4 roles hacia el cierre de sesión
Admin --> Logout
Gerente --> Logout
AgenteVentas --> Logout
Inspector --> Logout

%% Relaciones de inclusión y extensión
Login inc_tenant@..> : include SeleccionAgencia
BloqueoAuto ext_bloq@..> : extend Login

%% Definición de estilos
classDef seguridad stroke:#0284c7,stroke-width:2px
classDef critico stroke:#dc2626,stroke-width:2px

%% Animaciones y estilos
admin_login@{ animation: fast }
ger_login@{ animation: fast }
vent_login@{ animation: fast }
insp_login@{ animation: fast }
style inc_tenant stroke:#0284c7,stroke-width:2px
style ext_bloq stroke:#dc2626,stroke-width:2px
```

---

## 2. Matriz de Requisitos Funcionales Transversales

| Requisito Funcional | Caso de Uso | Actores Participantes | Tipo de Relación | Descripción Operativa |
| :--- | :--- | :--- | :--- | :--- |
| **RF-01** | `Login` | Todos los roles | Asociación directa | Autenticación mediante credenciales (`username` y contraseña verificada con algoritmo `bcrypt`), validando pertenencia a la agencia. |
| **RF-02** | `Logout` | Todos los roles | Asociación directa | Cierre seguro de sesión invalidando el singleton de sesión (`UserSession`) en el cliente. |
| **RF-38** | `SeleccionAgencia` | Todos los roles | `<<include>>` de `Login` | Determinación del identificador de inquilino (`tenant_id`) para establecer el contexto de aislamiento Row Level Security (RLS) en PostgreSQL. |
| **RF-03** | `BloqueoAuto` | Todos los roles | `<<extend>>` de `Login` | Mecanismo defensivo que bloquea automáticamente la cuenta tras superar 3 intentos fallidos consecutivos de autenticación. |

---

*Código fuente Mermaid puro disponible en:* [Use_Case_Diagram_Autenticacion_y_Sesion.mmd](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Autenticacion_y_Sesion.mmd)

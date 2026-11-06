# Diagrama de Casos de Uso - Rol: Inspector de Taller (INSPECTOR_TALLER)

Este documento especifica los casos de uso correspondientes al rol de **Inspector de Taller** en el sistema **AutoRent Pro**, organizados modularmente en 3 subsistemas técnicos y modelados con la sintaxis Mermaid `usecase-beta`.

> [!NOTE]
> Las funcionalidades comunes de autenticación, ciclo de vida de sesión y aislamiento multi-tenant (**RF-01**, **RF-02** y **RF-38**) han sido desacopladas de este diagrama e integradas en el [Diagrama Unificado de Casos de Uso — Autenticación, Sesión y Agencia](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Autenticacion_y_Sesion.md).

---

## 1. Diagrama de Casos de Uso (Mermaid)

```mermaid
usecase-beta
direction LR

accTitle: Diagrama de Casos de Uso - Inspector de Taller (AutoRent Pro)
accDescr {
  Diagrama de casos de uso modular para el rol de Inspector de Taller en AutoRent Pro.
  Comprende tres subsistemas tecnicos funcionales: Control Tecnico de Flota,
  Recepcion e Inspeccion Fisica de Retorno, y Gestion de Taller con Mantenimiento Mecanico.
  Modela la inspeccion con comprobacion de inventario, calculo automatico de diferenciales
  de odometro y combustible, registro de averias, transiciones de estados operativos,
  emision de ordenes preventivas y correctivas con bloqueo operativo, y reactivacion
  de flota con costos liquidados.
}

actor Inspector("Inspector de Taller")@{ type: hollow, business: true } <<Rol Taller>>

%% ======================================================================
%% Módulo 1: Control Técnico de Flota
%% ======================================================================
systemBoundary Control_Tecnico_Flota["Control Técnico de Flota"]@{ type: package }:::sistema
  RF06_ConsultarFlota("Consultar flota y ficha técnica de vehículo (RF-06)") <<Consulta>>:::flota
  RF07_ControlEstados("Controlar transición y gestión de estados de flota (RF-07)") <<Operativo>>:::estado
  RF09_AlertasKm("Monitorear alertas de kilometraje preventivo (RF-09)") <<Alerta>>:::alerta
end

%% ======================================================================
%% Módulo 2: Recepción e Inspección
%% ======================================================================
systemBoundary Recepcion_e_Inspeccion["Recepción e Inspección"]@{ type: package }:::sistema
  RF23_InspeccionRetorno("Realizar inspección física de retorno y accesorios (RF-23)") <<Check-out>>:::inspeccion
  RF24_ComparativaRetorno("Comparar automáticamente odómetro y combustible de retorno (RF-24)") <<Cálculo>>:::inspeccion
  RF27_RegistrarDanos("Registrar y valorar averías o daños físicos (RF-27)") <<Siniestralidad>>:::critico
  RF30_TransicionPostInspeccion("Reclasificar estado operativo post-inspección (RF-30)") <<Transición>>:::estado
end

%% ======================================================================
%% Módulo 3: Gestión de Taller
%% ======================================================================
systemBoundary Gestion_Taller["Gestión de Taller"]@{ type: package }:::sistema
  RF31_RegistrarMantenimiento("Abrir orden de mantenimiento preventivo o correctivo (RF-31)") <<Taller>>:::mantenimiento
  RF32_BloqueoOperativo("Bloquear vehículo operativamente en taller (RF-32)") <<Regla Negocio>>:::critico
  RF33_FinalizarMantenimiento("Finalizar mantenimiento, registrar costos y reactivar vehículo (RF-33)") <<Cierre Taller>>:::mantenimiento
end

%% ======================================================================
%% Asociaciones directas del Actor Inspector de Taller
%% ======================================================================
Inspector --> RF06_ConsultarFlota
Inspector --> RF07_ControlEstados
Inspector --> RF09_AlertasKm
Inspector check@-- "ejecuta check-out técnico" ---> RF23_InspeccionRetorno
Inspector orden@-- "crea orden de servicio" ---> RF31_RegistrarMantenimiento
Inspector --> RF33_FinalizarMantenimiento

%% ======================================================================
%% Relaciones de Inclusión (<<include>>)
%% ======================================================================
RF23_InspeccionRetorno inc_comp@..> : include RF24_ComparativaRetorno
RF23_InspeccionRetorno inc_trans@..> : include RF30_TransicionPostInspeccion
RF30_TransicionPostInspeccion inc_est1@..> : include RF07_ControlEstados
RF31_RegistrarMantenimiento inc_bloq@..> : include RF32_BloqueoOperativo
RF31_RegistrarMantenimiento inc_est2@..> : include RF07_ControlEstados
RF33_FinalizarMantenimiento inc_react@..> : include RF07_ControlEstados

%% ======================================================================
%% Relaciones de Extensión (<<extend>>)
%% ======================================================================
RF27_RegistrarDanos ext_dano@..> : extend RF23_InspeccionRetorno
RF09_AlertasKm ext_maint@..> : extend RF31_RegistrarMantenimiento

%% ======================================================================
%% Definición de estilos de clases
%% ======================================================================
classDef sistema stroke:#1e40af,stroke-width:2px,fill:#f8fafc
classDef inspeccion stroke:#0284c7,stroke-width:2px,fill:#f0f9ff
classDef flota stroke:#0284c7,stroke-width:2px,fill:#f0f9ff
classDef mantenimiento stroke:#d97706,stroke-width:2px,fill:#fffbeb
classDef estado stroke:#059669,stroke-width:2px,fill:#ecfdf5
classDef alerta stroke:#ea580c,stroke-width:2px,fill:#fff7ed
classDef critico stroke:#dc2626,stroke-width:2px,fill:#fef2f2

%% ======================================================================
%% Animaciones de aristas
%% ======================================================================
check@{ animation: fast }
orden@{ animation: fast }

%% ======================================================================
%% Estilos específicos de aristas
%% ======================================================================
style inc_bloq stroke:#dc2626,stroke-width:2px
style ext_dano stroke:#ea580c,stroke-width:2px,stroke-dasharray: 5 5
style inc_comp stroke:#0284c7,stroke-width:2px
style inc_trans stroke:#059669,stroke-width:2px
```

---

## 2. Matriz de Trazabilidad de Requisitos Funcionales Técnicos

> [!INFO]
> Los casos de uso de inicio de sesión (**RF-01**), cierre de sesión (**RF-02**) y selección/aislamiento de sucursal (**RF-38**) fueron centralizados en el diagrama transversal común. La siguiente tabla comprende exclusivamente las atribuciones técnicas y operativas del Inspector de Taller:

| Módulo / Límite del Sistema | Requisito Funcional | Caso de Uso | Relación UML | Descripción Operativa |
| :--- | :--- | :--- | :--- | :--- |
| **Control Técnico de Flota** | **RF-06** | Consultar flota y ficha técnica de vehículo (RF-06) | Asociación directa | Inspección de características, odómetro actual, VIN, placa y ficha técnica de unidades. |
| **Control Técnico de Flota** | **RF-07** | Controlar transición y gestión de estados de flota (RF-07) | `<<include>>` desde RF-30, RF-31, RF-33 / Asociación directa | Control de la máquina de estados: `DISPONIBLE`, `EN_INSPECCION`, `EN_MANTENIMIENTO`, `DE_BAJA`. |
| **Control Técnico de Flota** | **RF-09** | Monitorear alertas de kilometraje preventivo (RF-09) | Asociación directa / `<<extend>>` hacia RF-31 | Alerta disparada al acercarse a $\le 200\text{ km}$ del kilometraje límite programado. |
| **Recepción e Inspección** | **RF-23** | Realizar inspección física de retorno y accesorios (RF-23) | Asociación directa | Registro de kilometraje de retorno, combustible, inventario de accesorios (llanta repuesto, gata, llave). |
| **Recepción e Inspección** | **RF-24** | Comparar automáticamente odómetro y combustible de retorno (RF-24) | `<<include>>` desde RF-23 | Cálculo diferencial entre salida y retorno para transferir datos al módulo de liquidación. |
| **Recepción e Inspección** | **RF-27** | Registrar y valorar averías o daños físicos (RF-27) | `<<extend>>` hacia RF-23 | Registro condicional de zonas afectadas, tipo de golpe, gravedad y costo estimado de reparación. |
| **Recepción e Inspección** | **RF-30** | Reclasificar estado operativo post-inspección (RF-30) | `<<include>>` desde RF-23 | Actualización del estado del vehículo a `DISPONIBLE` o `EN_MANTENIMIENTO` según el dictamen técnico. |
| **Gestión de Taller** | **RF-31** | Abrir orden de mantenimiento preventivo o correctivo (RF-31) | Asociación directa | Apertura de orden de trabajo en taller con fecha estimada, odómetro inicial y descripción de falla. |
| **Gestión de Taller** | **RF-32** | Bloquear vehículo operativamente en taller (RF-32) | `<<include>>` desde RF-31 | Restricción inquebrantable a nivel de aplicación y base de datos para impedir alquiler o reserva. |
| **Gestión de Taller** | **RF-33** | Finalizar mantenimiento, registrar costos y reactivar vehículo (RF-33) | Asociación directa | Liquidación técnica de la orden, registro de repuestos/mano de obra, nuevo umbral de km y reactivación a `DISPONIBLE`. |

---

*Código fuente Mermaid puro disponible en:* [Use_Case_Diagram_Inspector_Taller.mmd](file:///C:/Disk_E/UNAN/Proyecto_Integrador_II/agencia_de_autos/docs/diagrams/casos_de_uso/Use_Case_Diagram_Inspector_Taller.mmd)

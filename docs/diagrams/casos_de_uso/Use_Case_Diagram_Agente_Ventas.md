# Diagrama de Casos de Uso — Rol: Agente de Ventas (AutoRent Pro)

El presente diagrama modela de forma sintetizada y modular todas las interacciones, casos de uso y dependencias (`<<include>>`, `<<extend>>`) correspondientes al rol de **Agente de Ventas** en el sistema **AutoRent Pro**, organizado en 4 subsistemas comerciales propios: **Gestión de Clientes**, **Gestión de Reservas**, **Contratos y Despacho**, y **Retorno y Liquidación**.

> [!NOTE]
> Las acciones comunes de inicio y cierre de sesión multi-tenant (**RF-01**, **RF-02**, **RF-38**) han sido extraídas de este diagrama y unificadas en el [Diagrama Unificado de Autenticación y Sesión](./Use_Case_Diagram_Autenticacion_y_Sesion.md) transversal a todos los roles del sistema.

```mermaid
usecase-beta
direction LR
accTitle: Diagrama de Casos de Uso - Rol Agente de Ventas (AutoRent Pro)
accDescr {
  Diagrama de casos de uso resumido y modular para el Agente de Ventas en AutoRent Pro.
  Estructura las operaciones en cuatro subsistemas comerciales: Gestión de Clientes,
  Gestión de Reservas, Contratos y Despacho, y Retorno y Liquidación.
  Representa el ciclo comercial completo preservando la trazabilidad de los requisitos funcionales.
}

actor AgenteVentas("Agente de Ventas")@{ type: hollow, business: true } <<Empleado>>
actor Cliente("Cliente / Arrendatario")@{ type: hollow } <<Externo>>

%% Módulo 1: Gestión de Clientes
systemBoundary Gestion_Clientes["Gestión de Clientes"]@{ type: package }:::comercial
  GestionClientes("Registrar y gestionar clientes (RF-10)") <<Comercial>>:::comercial
  ValidarLicenciaCredito("Validar licencia de conducir y récord crediticio (RF-11, RF-12)") <<Validación>>:::comercial
end

%% Módulo 2: Gestión de Reservas
systemBoundary Gestion_Reservas["Gestión de Reservas"]@{ type: package }:::reserva
  CrearReserva("Crear reserva con control anti-overbooking (RF-14, RF-15)") <<Reserva>>:::reserva
  RegistrarAnticipo("Registrar anticipo de reserva (RF-16)") <<Financiero>>:::financiero
  GestionarEstadosReserva("Controlar ciclo de vida de la reserva (RF-17)") <<Reserva>>:::reserva
end

%% Módulo 3: Contratos y Despacho
systemBoundary Contratos_y_Despacho["Contratos y Despacho"]@{ type: package }:::transaccional
  AperturaContrato("Formalizar y aperturar contrato de alquiler (RF-18)") <<Core>>:::transaccional
  ConductoresAdicionales("Vincular conductores adicionales (RF-13)") <<Contrato>>:::transaccional
  GarantiaYSeguros("Cobrar fianza de garantía y seleccionar cobertura (RF-19)") <<Financiero>>:::financiero
  DespachoCheckIn("Realizar check-in físico y despachar vehículo (RF-20, RF-21)") <<Transaccional>>:::transaccional
  EmitirContratoPDF("Emitir e imprimir contrato legal en PDF (RF-39)") <<Documental>>:::transaccional
end

%% Módulo 4: Retorno y Liquidación
systemBoundary Retorno_y_Liquidacion["Retorno y Liquidación"]@{ type: package }:::financiero
  RecepcionRetorno("Registrar recepción física de retorno (RF-22)") <<Operativo>>:::financiero
  LiquidarContrato("Liquidar contrato y balancear cargos con garantía (RF-25, RF-28)") <<Core>>:::financiero
  PenalizacionesRetorno("Calcular penalizaciones por mora, combustible o km (RF-26)") <<Cálculo>>:::financiero
  ComprobanteCierre("Emitir comprobante de liquidación y cerrar contrato (RF-29)") <<Cierre>>:::financiero
end

%% Interacciones del Agente de Ventas
AgenteVentas --> GestionClientes
AgenteVentas --> CrearReserva
AgenteVentas --> GestionarEstadosReserva
AgenteVentas iniciaContrato@-- "formaliza alquiler" ---> AperturaContrato
AgenteVentas --> RecepcionRetorno
AgenteVentas --> LiquidarContrato

%% Interacciones del Cliente
Cliente --> CrearReserva
Cliente --> EmitirContratoPDF
Cliente --> ComprobanteCierre

%% Relaciones de Inclusión (include)
GestionClientes ..> : include ValidarLicenciaCredito
AperturaContrato ..> : include GarantiaYSeguros
AperturaContrato relDespacho@..> : include DespachoCheckIn
AperturaContrato relPDF@..> : include EmitirContratoPDF
LiquidarContrato relCierre@..> : include ComprobanteCierre

%% Relaciones de Extensión (extend)
RegistrarAnticipo ..> : extend CrearReserva
ConductoresAdicionales ..> : extend AperturaContrato
PenalizacionesRetorno ..> : extend LiquidarContrato

%% Definición de Estilos y Clases CSS
classDef sistema stroke:#2563eb,stroke-width:2px
classDef transaccional stroke:#dc2626,stroke-width:2px
classDef financiero stroke:#d97706,stroke-width:2px
classDef seguridad stroke:#7c3aed,stroke-width:2px
classDef comercial stroke:#059669,stroke-width:2px
classDef reserva stroke:#0284c7,stroke-width:2px

%% Animaciones y Estilos de Enlaces
iniciaContrato@{ animation: fast }
relDespacho@{ animation: fast }
style relDespacho stroke:#dc2626,stroke-width:2px
style relPDF stroke:#059669,stroke-width:2px
style relCierre stroke:#d97706,stroke-width:2px
```

## Requisitos Funcionales Cubiertos por Módulo

> [!NOTE]
> Los requisitos transversales de sesión y tenencia múltiple (**RF-01**: Iniciar sesión, **RF-02**: Cerrar sesión y **RF-38**: Aislamiento por sucursal RLS) se encuentran unificados y detallados en el [Diagrama Unificado de Autenticación y Sesión](./Use_Case_Diagram_Autenticacion_y_Sesion.md).

| Módulo / Subsistema | Requisitos Funcionales | Acción del Caso de Uso Sintetizado | Tipo de Relación / Comportamiento |
| :--- | :--- | :--- | :--- |
| **Gestión de Clientes** | **RF-10** | Registrar y gestionar clientes (RF-10) | Padrón de clientes naturales y jurídicos |
| | **RF-11, RF-12** | Validar licencia de conducir y récord crediticio (RF-11, RF-12) | Inclusión en Gestión de Clientes (`include`) |
| **Gestión de Reservas** | **RF-14, RF-15** | Crear reserva con control anti-overbooking (RF-14, RF-15) | Verificación temporal de disponibilidad |
| | **RF-16** | Registrar anticipo de reserva (RF-16) | Extensión financiera en reserva (`extend`) |
| | **RF-17** | Controlar ciclo de vida de la reserva (RF-17) | Transiciones de estado de reserva |
| **Contratos y Despacho** | **RF-18** | Formalizar y aperturar contrato de alquiler (RF-18) | Núcleo transaccional de alquiler (`Core`) |
| | **RF-13** | Vincular conductores adicionales (RF-13) | Extensión condicional en contrato (`extend`) |
| | **RF-19** | Cobrar fianza de garantía y seleccionar cobertura (RF-19) | Inclusión obligatoria de póliza y fianza (`include`) |
| | **RF-20, RF-21** | Realizar check-in físico y despachar vehículo (RF-20, RF-21) | Inclusión transaccional atómica de entrega (`include`) |
| | **RF-39** | Emitir e imprimir contrato legal en PDF (RF-39) | Inclusión para firma contractual (`include`) |
| **Retorno y Liquidación** | **RF-22** | Registrar recepción física de retorno (RF-22) | Entrada física de retorno en sucursal |
| | **RF-25, RF-28** | Liquidar contrato y balancear cargos con garantía (RF-25, RF-28) | Balance financiero y cruce contra depósito (`Core`) |
| | **RF-26** | Calcular penalizaciones por mora, combustible o km (RF-26) | Extensión sancionatoria en liquidación (`extend`) |
| | **RF-29** | Emitir comprobante de liquidación y cerrar contrato (RF-29) | Inclusión de finiquito y cierre contable (`include`) |

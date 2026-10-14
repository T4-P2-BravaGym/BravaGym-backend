# HU-11 · Gestión de clases para entrenadores

Issue: #53 · Entrega 1 · Tamaño M · Prioridad P1

## Contexto

> Como entrenadora quiero crear, editar y cancelar mis clases para organizar mi horario.

El horario público (HU-10) ya existía. Faltaba el CRUD de tipos de clase y que
la entrenadora pudiera gestionar sus sesiones sin solapes, y cancelarlas con
cascada sobre reservas y pagos.

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. Administración de tipos de clase (`class_types`): listar, crear, editar y
   desactivar.
2. La entrenadora crea, edita y cancela sus propias sesiones.
3. No puede programar dos sesiones suyas que se solapen.
4. No puede editar ni cancelar la sesión de otra entrenadora (salvo superadmin).
5. Al cancelar una sesión, sus reservas pasan a `cancelled` y los pagos de clase
   extra relacionados quedan `refunded`.
6. Puede ver el listado de reservas de su sesión.

## Reglas

- **RN-09**: un entrenador no puede tener dos sesiones **programadas** solapadas
  en `[starts_at, starts_at + duration)`. Las `cancelled` no cuentan → 409.
- **RN-10**: solo el entrenador de la sesión o el superadmin la editan o
  cancelan → si no, 403. Cancelar deja la sesión `cancelled`, pasa reservas
  `confirmed`/`waitlisted` a `cancelled` y pagos de clase extra `pending`/`paid`
  a `refunded`.

## Criterios de aceptación

- **Dado** que soy trainer, **cuando** creo una sesión que se solapa con otra
  mía, **entonces** recibo 409.
- **Dado** una sesión de otra entrenadora, **cuando** intento editarla,
  **entonces** recibo 403 (salvo superadmin).
- **Dado** una sesión con reservas, **cuando** la cancelo, **entonces** sus
  reservas pasan a `cancelled` y los pagos de clase extra quedan `refunded`.
- **Dado** un nombre de tipo de clase duplicado, **cuando** lo creo,
  **entonces** recibo 409.
- **Dado** que soy member, **cuando** intento crear una sesión, **entonces**
  recibo 403. Sin token, 401.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/class-types` | Público | 200 página | 422 |
| POST | `/class-types` | Trainer, superadmin | 201 `ClassTypeOut` | 401, 403, 409, 422 |
| PATCH | `/class-types/{id}` | Trainer, superadmin | 200 `ClassTypeOut` | 401, 403, 404, 409, 422 |
| DELETE | `/class-types/{id}` | Trainer, superadmin | 200 (soft delete) | 401, 403, 404 |
| POST | `/sessions` | Trainer, superadmin | 201 `SessionOut` | 401, 403, 404, 409, 422 |
| PATCH | `/sessions/{id}` | Trainer (propia), superadmin | 200 `SessionOut` | 401, 403, 404, 409 |
| POST | `/sessions/{id}/cancel` | Trainer (propia), superadmin | 200 `SessionOut` | 401, 403, 404, 409 |
| GET | `/sessions/{id}/bookings` | Trainer (propia), admin, superadmin | 200 lista | 401, 403, 404 |

Al crear, la trainer fuerza `trainer_id = actor.id`; la superadmin debe pasar
`trainer_id`. DELETE de tipo de clase pone `is_active = false` (no borra la fila).

## Interfaz

- Pantalla de la entrenadora: crear/editar/cancelar sesiones y ver el roster.
- Catálogo de tipos de clase para quien gestiona el horario.
- Estados: solape (409), no es tuya (403), sesión ya cancelada.

## Fuera de alcance

- Horario público → HU-10.
- Reservar / cancelar plaza como socia → HU-12, HU-13.
- Franjas dedicadas de PT → HU-14 (`POST /sessions/personal-training`).
- Websocket al cancelar → HU-16 (se emite al promover lista de espera en HU-13).

## Preguntas abiertas

Ninguna: la historia está mergeada en `dev`.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Intervalo medio abierto `[start, end)` para solapes | Evita marcar conflicto si una clase termina exactamente cuando empieza la siguiente |
| Soft delete en `class_types` | Las sesiones antiguas siguen nombrando el tipo |
| Admin puede ver el roster pero no editar/cancelar la sesión | RN-10 reserva edición/cancelación a trainer propietaria o superadmin |
| Cancelar sesión marca pagos extra `refunded` (no `cancelled`) | RN-10: el cobro de clase extra deja de ser válido y se registra como reembolso |

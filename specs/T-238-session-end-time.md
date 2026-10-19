# T-238 · Hora de fin de las clases

Issue: #238 · Entrega 2 · Tamaño S · Prioridad P3

## Contexto

> Como socia quiero ver a qué hora termina cada clase para organizar mi día.

El horario (HU-10) y mis reservas (HU-12) muestran la hora de inicio y la duración en minutos,
pero no la hora de fin. `class_sessions` ya guarda `starts_at` y `duration_minutes`, así que
la hora de fin se puede calcular sin guardarla.

## Requisitos

1. Cada sesión que devuelve la API incluye su hora de fin.
2. La hora de fin es siempre inicio + duración; no se guarda en la base de datos.
3. El horario y "Mis reservas" muestran el rango de inicio a fin.

## Criterios de aceptación

- **Dado** una sesión que empieza a las 07:00 y dura 60 minutos, **cuando** pido `GET /sessions`, **entonces** `ends_at` es las 08:00.
- **Dado** una reserva, **cuando** pido mis reservas, **entonces** su sesión incluye `ends_at`.
- **Dado** que una entrenadora cambia la duración, **entonces** `ends_at` cambia con ella.

## Endpoints

Sin endpoints nuevos. Se añade el campo calculado `ends_at` (UTC) a `SessionOut` y
`BookingSessionOut`. Sin cambios de esquema ni migración.

## Interfaz

`SessionCard` y "Mis reservas" muestran `17:30 – 18:30` en vez de solo la hora de inicio.
Va en una PR del frontend que enlaza a esta spec.

## Fuera de alcance

- Editar la hora de fin directamente: se cambia con la duración (HU-11).

## Decisiones

| Decisión | Por qué |
| --- | --- |
| `ends_at` calculado con `computed_field`, sin columna nueva | Una sola fuente de verdad: no puede desincronizarse con la duración |
| Mixin `SessionTimeMixin` compartido por los dos esquemas | Evita repetir el cálculo (DRY) |
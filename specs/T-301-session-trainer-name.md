# T-301 · Nombre de la entrenadora en sesiones y reservas

Issue: #301 · Entrega 2 · Tamaño S · Prioridad P2

## Contexto

> Como socia quiero ver quién da cada clase para elegir y saber con quién voy a entrenar.

El horario (HU-10), "Reservar clases" y "Mis reservas" (HU-12) muestran "Entrenadora" en
todas las tarjetas, porque `SessionOut` y la sesión de `BookingOut` solo traen `trainer_id`.
La Home y Entrenamiento personal lo resuelven en el front cruzando con `GET /trainers`.
Lo detectó Damaris al rehacer la Home.

## Requisitos

1. Cada sesión que devuelve la API incluye el nombre de su entrenadora.
2. El nombre tiene el mismo formato que `GET /trainers` (nombre y apellido).
3. Listar sesiones o reservas no hace una consulta extra por cada sesión.

## Criterios de aceptación

- **Dado** el horario, **cuando** pido `GET /sessions`, **entonces** cada sesión incluye `trainer_name` con nombre y apellido de la entrenadora.
- **Dado** que tengo una reserva, **cuando** pido `GET /bookings/me`, **entonces** su `class_session` incluye `trainer_name`.

## Endpoints

Sin endpoints nuevos. Se añade `trainer_name` a `SessionOut` y `BookingSessionOut`.
Sin cambios de esquema ni migración: sale de la relación con `users`.

## Interfaz

Sin cambios en el front: `toSessionCard` ya lee `session.trainer_name`, así que el horario,
"Reservar clases" y "Mis reservas" muestran el nombre en cuanto la API lo envía.

## Fuera de alcance

- Quitar el cruce con `GET /trainers` en la Home y en Entrenamiento personal: sigue funcionando y se puede limpiar después.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Nombre completo (nombre y apellido) | Coincide con `GET /trainers`, así la Home y el horario dicen lo mismo |
| `User.full_name` y `ClassSession.trainer_name` como propiedades del modelo | `BookingSessionOut` se construye con `from_attributes` y lee el atributo directamente; el formato del nombre vive en un solo sitio |
| `joinedload(ClassSession.trainer)` solo en los listados (horario y mis reservas) | Evita una consulta por sesión (N+1); en las respuestas de una sola sesión no compensa |
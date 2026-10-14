# HU-12 · Reservar una clase

Issue: #58 · Entrega 1 · Tamaño L · Prioridad P1

## Contexto

> Como socia quiero reservar plaza en una clase para asegurarme sitio.

Con el horario (HU-10) y las sesiones de la entrenadora (HU-11) ya en pie, falta
que la socia pueda coger plaza, entrar en lista de espera y generar el pago de
clase extra si aplica.

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. Una socia con suscripción activa puede reservar una sesión.
2. Si hay plazas, la reserva queda `confirmed`; si no, `waitlisted` con posición.
3. No se puede reservar dos veces la misma sesión.
4. Sin suscripción activa no se reserva.
5. Si la clase tiene precio extra y la reserva se confirma, se crea un pago
   `pending`.
6. La socia puede listar sus reservas.

## Reglas

- **RN-01**: hace falta usuaria activa con suscripción `active` → si no, 403.
- **RN-02**: si `confirmed` < `capacity` → `confirmed`; si no → `waitlisted` con
  posición.
- **RN-03**: no dos reservas en la misma sesión → 409. Si había una `cancelled`,
  se reactiva en lugar de crear otra.
- **RN-04**: no se reservan sesiones pasadas ni `cancelled` → 409.
- **RN-07**: si `extra_price_cents > 0`, al confirmarse se crea un pago `pending`
  (también al subir desde la lista de espera en HU-13).
- **RN-08** (compartida con HU-14): entrenamiento personal solo si el plan tiene
  `includes_personal_training` → si no, 403.

## Criterios de aceptación

- **Dado** una clase con plazas, **cuando** reservo, **entonces** mi reserva
  queda `confirmed`.
- **Dado** una clase llena, **cuando** reservo, **entonces** quedo `waitlisted`
  y veo mi posición.
- **Dado** que ya tengo reserva en esa sesión, **cuando** reservo otra vez,
  **entonces** recibo 409.
- **Dado** que no tengo suscripción activa, **cuando** reservo, **entonces**
  recibo 403.
- **Dado** una clase con precio extra, **cuando** mi reserva se confirma,
  **entonces** se crea un pago `pending`.
- **Dado** que pido `GET /bookings/me`, **entonces** veo mis reservas con
  posición de espera cuando aplica.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/sessions/{id}/bookings` | Member | 201 `BookingOut` | 401, 403, 404, 409 |
| GET | `/bookings/me` | Member | 200 `BookingPage` | 401, 403 |

`BookingOut` incluye `status`, `waitlist_position` (solo si `waitlisted`) y la
sesión anidada. La posición se calcula, no se guarda. Tablas: `bookings` y, si
hay precio extra, `payments`.

## Interfaz

- Botón "Reservar" en cada sesión del horario.
- "Mis reservas" con estado confirmada / en espera y posición.
- Estados: 403 sin suscripción, 409 duplicada o sesión pasada, clase llena
  (waitlist), error de red.

## Fuera de alcance

- Cancelar la reserva → HU-13.
- Franjas dedicadas de PT (crear slot) → HU-14.
- Pagar la clase extra → HU-24.
- Actualización en vivo del aforo → HU-16.

## Preguntas abiertas

Ninguna: la historia está mergeada en `dev`.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Reactivar una reserva `cancelled` en vez de crear otra fila | RN-03 y evita duplicar historial de la misma socia+sesión |
| Posición de waitlist por `created_at`, `id` | Orden estable y determinista para RN-06 |
| El pago extra solo al confirmar (no al waitlist) | RN-07: se cobra la plaza confirmada; al promover en HU-13 se crea entonces |
| Recurso ajeno → 404, no 403 | Misma política de no revelar existencia que el resto de la API |

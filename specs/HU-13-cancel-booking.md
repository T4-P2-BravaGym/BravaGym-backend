# HU-13 · Cancelar una reserva

Issue: #62 · Entrega 1 · Tamaño M · Prioridad P1

## Contexto

> Como socia quiero cancelar mi reserva a tiempo para liberar la plaza.

Tras poder reservar (HU-12), hace falta salir de una clase con el plazo de una
hora y promocionar a quien está en lista de espera en la misma transacción.

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. La socia puede cancelar su propia reserva confirmada si faltan ≥ 60 minutos
   para el inicio.
2. Salir de la lista de espera se permite siempre.
3. Al cancelar una plaza confirmada, la reserva en espera más antigua pasa a
   `confirmed` en la misma transacción.
4. Si la clase tiene precio extra, al promoverse alguien se le crea el pago
   `pending`.
5. Una reserva ajena o inexistente no se distingue: 404.

## Reglas

- **RN-05**: una `confirmed` solo se cancela si faltan **60 minutos o más** para
  `starts_at`; si no → 409. Salir de waitlist siempre.
- **RN-06**: al cancelar una `confirmed`, la waitlisted más antigua (`created_at`)
  pasa a `confirmed` en la misma transacción; se emite evento por websocket
  (HU-16).
- **RN-07**: al confirmarse por promoción, si hay `extra_price_cents > 0`, se
  crea el pago `pending`.

## Criterios de aceptación

- **Dado** una reserva confirmada con ≥ 60 minutos de margen, **cuando**
  cancelo, **entonces** queda `cancelled` y, si había lista de espera, la más
  antigua pasa a `confirmed`.
- **Dado** menos de 60 minutos para el inicio, **cuando** cancelo una
  confirmada, **entonces** recibo 409.
- **Dado** que estoy en lista de espera, **cuando** cancelo, **entonces** salgo
  sin restricción de plazo.
- **Dado** una reserva ya cancelada o que no es mía, **cuando** cancelo,
  **entonces** recibo 409 o 404 respectivamente.
- **Dado** 59, 60 y 61 minutos exactos (reloj congelado), **cuando** cancelo,
  **entonces** 59 → 409 y 60/61 → OK.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/bookings/{id}/cancel` | Member (propia) | 200 `BookingOut` | 401, 403, 404, 409 |

Sin cambios de esquema. El reloj es inyectable / testeable con `freezegun`.

## Interfaz

- Acción "Cancelar" en "Mis reservas".
- Mensaje claro cuando faltan menos de 60 minutos.
- Tras cancelar, la plaza liberada se refleja en el horario (y por WS si HU-16).

## Fuera de alcance

- Cancelar la sesión entera (entrenadora) → HU-11.
- Cancelar reservas al aprobar una baja → HU-20 (reutiliza la promoción RN-06,
  sin el plazo RN-05).
- UI del toast de websocket → subtarea FE de HU-16.

## Preguntas abiertas

Ninguna: la historia está mergeada en `dev`.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Umbral inclusivo: 60 minutos exactos sí permiten cancelar | El AC de tests pide verde en 60 y 61, rojo en 59 |
| Promoción y cancelación en la misma transacción | RN-06: no dejar el aforo inconsistente si falla a medias |
| Recurso ajeno → 404 | No filtrar existencia de reservas de otras socias |
| Extraer `_cancel_one_booking_applying_rn06` | Lo reutiliza HU-20 al dar de baja sin aplicar RN-05 |

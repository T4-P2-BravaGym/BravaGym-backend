# HU-24 · Ver y pagar mis pagos

Issue: #101 · Entrega 1 · Tamaño M · Prioridad P1

## Contexto

> Como socia quiero ver mis pagos y pagar los pendientes con un código para estar al día.

Los pagos `pending` ya nacen al contratar un plan (HU-09), al confirmar una
clase extra (HU-12/13) o al hacer un pedido (HU-23). Faltaba el listado propio y
el pago simulado con descuento.

Spec escrita a posteriori, a partir de la issue y de las PR (incluida la de
sincronizar pedido `paid` y rechazar pagos `cancelled`).

## Requisitos

1. La socia ve sus pagos paginados, filtrables por estado.
2. Puede pagar un pago `pending` propio; el importe final lo calcula el servidor.
3. Puede aplicar un código de descuento válido (porcentaje).
4. Un pago ya `paid` (u otro estado no pendiente) no se vuelve a pagar.
5. Si el pago pertenece a un pedido, el pedido pasa a `paid` en la misma
   transacción.
6. Un pago `cancelled` no se puede pagar (mismo 409 que cualquier no pendiente).

## Reglas

- **RN-14**: el código es válido si está activo, dentro de fechas y por debajo de
  `max_uses` → si no, 422.
- **RN-15**: `final_amount_cents = base × (100 − percent_off) / 100`, redondeo al
  céntimo (half-up).
- **RN-16**: el pago simulado pasa de `pending` a `paid`. Si es de un pedido, el
  pedido pasa a `paid`. Un `paid` no se modifica por la socia. Si se canceló lo
  que iba a cobrar, el pago queda `cancelled` y ya no se paga → 409.

## Criterios de aceptación

- **Dado** un pago `pending`, **cuando** lo pago con un código válido del 20 %,
  **entonces** `final_amount_cents` es el 80 % y el pago queda `paid`.
- **Dado** un código caducado o agotado, **cuando** lo uso, **entonces** recibo
  422 y el pago no cambia.
- **Dado** un pago `paid`, **cuando** intento pagarlo de nuevo, **entonces**
  recibo 409.
- **Dado** un pago de otra socia, **cuando** intento pagarlo, **entonces**
  recibo 404.
- **Dado** un pago `cancelled`, **cuando** intento pagarlo, **entonces** recibo
  409.
- **Dado** un pago de pedido `pending`, **cuando** lo pago, **entonces** el
  pedido queda `paid`.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/payments/me` | Member | 200 `PaymentPage` | 401, 403 |
| POST | `/payments/{id}/pay` | Member (propio) | 200 `PaymentOut` | 401, 403, 404, 409, 422 |

Entrada: `PayRequest` opcional con `discount_code` (sin importes). Salida:
`PaymentOut` con `concept` derivado (`subscription` \| `booking` \| `order`),
importes en céntimos y código aplicado si hubo. Reutiliza
`discount_service.get_valid_code` (HU-25).

## Interfaz

- Pantalla "Mis pagos" con filtro por estado.
- Acción Pagar con campo opcional de código de descuento.
- Estados: pendiente, pagado, código inválido (422), ya pagado (409), vacío.

## Fuera de alcance

- Listado / export / refund de administración → HU-26.
- Pago real con Stripe → HU-29.
- CRUD de códigos de descuento → HU-25.

## Preguntas abiertas

Ninguna: la historia está mergeada en `dev`.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| El cliente nunca manda el importe | AGENTS.md: no confiar en la entrada; el servidor lee `base_amount_cents` |
| Redondeo half-up `(base * (100 − %) + 50) // 100` | Cumple RN-15 de forma estable en enteros |
| Pago ajeno → 404 | No revelar existencia de pagos de otras socios |
| Pedido se marca `paid` en la misma transacción | RN-16; evita pedido pendiente con pago ya cobrado |
| `cancelled` y resto de no-`pending` → mismo 409 | Mensaje único; el front no necesita ramas distintas |

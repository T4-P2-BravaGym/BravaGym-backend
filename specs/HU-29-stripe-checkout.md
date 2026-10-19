# HU-29 · Pago real con Stripe

Issue: #120 · Sub: #121–#123 · Entrega 2 · Tamaño L · Prioridad opcional

## Contexto

> Como socia quiero pagar con tarjeta para no tener que pagar en recepción.

HU-24 ya permite pagar en simulado (`POST /payments/{id}/pay`). Esta historia
añade Stripe Checkout en modo test y un webhook con verificación de firma.
Sin claves en `.env`, la API sigue en modo simulado.

## Requisitos

1. Con `STRIPE_SECRET_KEY` configurada, la socia puede abrir un Checkout de Stripe
   para un pago `pending` propio.
2. El importe lo calcula el servidor (incluye código de descuento opcional).
3. Tras pagar con tarjeta de prueba, el webhook marca el pago `paid`, guarda
   `provider_ref` y pone `method=stripe`.
4. Si el pago es de un pedido, el pedido pasa a `paid` en la misma transacción.
5. Sin claves Stripe, el checkout no está disponible y el pago simulado de HU-24
   sigue funcionando.
6. La firma del webhook se verifica; si falla, se rechaza la petición.

## Reglas

- **RN-14 / RN-15**: el descuento opcional en checkout usa las mismas reglas que
  el pago simulado.
- **RN-16** (ampliada): el paso a `paid` puede venir del simulado o del webhook
  de Stripe. Un no-`pending` no se paga (409). El webhook es idempotente si el
  pago ya está `paid`.

## Criterios de aceptación

- **Dado** el modo test de Stripe, **cuando** pago con la tarjeta de prueba,
  **entonces** el webhook marca el pago `paid` y guarda `provider_ref`.
- **Dado** que no hay claves de Stripe en `.env`, **cuando** arranca la API,
  **entonces** se usa el pago simulado.
- **Dado** un webhook con firma inválida, **cuando** llega a `/webhooks/stripe`,
  **entonces** recibo 400 y el pago no cambia.
- **Dado** un pago ya `paid`, **cuando** Stripe reenvía el mismo evento,
  **entonces** respondo 200 y no altero el pago.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/payments/{id}/checkout` | Member (propio) | 200 `CheckoutSessionOut` | 401, 403, 404, 409, 422, 503 |
| POST | `/webhooks/stripe` | Stripe (firma) | 200 `{received: true}` | 400 |
| POST | `/payments/{id}/pay` | Member | 200 `PaymentOut` | sin cambio (HU-24 simulado) |

Entrada checkout: opcional `{discount_code}` (mismo `PayRequest`).
Salida: `{checkout_url, session_id}`.
`PaymentOut` incluye `provider_ref` (nullable).

Variables (`.env.example`, nunca secretos reales en git):

- `STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL`

Sin migración: `method` y `provider_ref` ya existen en el esquema inicial.

## Interfaz

- Botón “Pagar con tarjeta” en Mis pagos (PR frontend aparte): redirige a
  `checkout_url` y, al volver, refresca el listado (el estado lo pone el webhook).
- Sin claves Stripe: solo el flujo simulado actual.

## Fuera de alcance

- Stripe Billing (suscripciones recurrentes en Stripe).
- Stripe Invoicing / Customer Portal.
- Refund vía API de Stripe (HU-26 sigue siendo marca local).
- Payment Element embebido / PaymentIntent directo.

## Preguntas abiertas

Ninguna para el slice BE: Checkout hosted + webhook cubren los ACs del padre.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Checkout Session `mode=payment` | One-shot sobre `payments` existentes; no mezcla Billing |
| `/checkout` nuevo; `/pay` intacto | Cumple AC de fallback simulado sin romper HU-24 |
| `provider_ref` = id de la Session (`cs_…`) | Estable y legible en Dashboard |
| Fulfill solo con `payment_status=paid` | Evita marcar pagado con métodos asíncronos a medias |
| 503 si no hay secret key | Mensaje claro en español; FE puede ocultar el botón |
| Tests con mock del cliente Stripe | Issue #123; sin red ni claves reales en CI |

## Checkout consistency follow-up

- Persist one immutable request and random idempotency key per payment before
  contacting Stripe. Repeated requests reuse the open session and original amount.
- Serialize local payment transitions with a database write lock. Cancel and
  simulated pay expire any open hosted session first; if Stripe is complete,
  unavailable or the create response is unknown, do not release stock or settle locally.
- Match session, member, amount and currency before fulfillment. Only the same
  already-recorded Stripe session is an idempotent replay.
- Process expiration only for the current attempt; ignore stale expiration events.
- Unknown attempts older than 23 hours require reconciliation rather than reusing
  a potentially pruned Stripe idempotency key.
- Migration `a291c0ffee01` adds the durable attempt table. Preserve existing paid
  records. Before using this revision against an existing Stripe environment,
  reconcile/expire pending sessions created by the old revision: they have no
  durable attempt and must not be silently accepted by the new webhook.
- Acceptance tests include retries, concurrent requests, discounted checkout
  reopening, mismatched webhooks, cancellation and expiration failures.

Implementation references: https://docs.stripe.com/api/idempotent_requests and
https://docs.stripe.com/api/checkout/sessions/expire . Refund API remains out of scope.

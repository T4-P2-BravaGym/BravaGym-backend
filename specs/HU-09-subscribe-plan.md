# HU-09 · Contratar un plan

Issue: #45 · Entrega 1 · Tamaño M · Prioridad P1

## Contexto

> Como socia quiero contratar un plan para poder reservar clases.

Los planes ya se veían en pricing (HU-07) y administración ya los gestionaba
(HU-08), pero no se podían contratar. Sin suscripción activa no se reserva nada,
así que esta historia es la puerta a las clases (HU-12) y al entrenamiento
personal (HU-14, que además exige un plan con `includes_personal_training`).

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. Una socia con sesión puede contratar un plan activo.
2. Al contratarlo se crea una suscripción `active` y un pago `pending` por la cuota.
3. El importe se lee del plan; nunca viene en la petición.
4. Una socia solo puede tener una suscripción activa a la vez.
5. La socia puede ver su suscripción actual y las anteriores.
6. O se crean la suscripción y su pago, o no se crea ninguno de los dos.

## Reglas

- **RN-11** (una sola suscripción `active` por usuaria), **RN-13** (al aprobar la
  baja la suscripción queda `cancelled`) y **RN-16** (estados del pago), en
  `docs/business-rules.md`.

## Criterios de aceptación

- **Dado** que no tengo suscripción activa, **cuando** contrato un plan,
  **entonces** se crea la suscripción `active` con la fecha de hoy y un pago
  `pending` por la cuota, y recibo 201 con la suscripción y su plan.
- **Dado** que ya tengo una activa, **cuando** contrato otra, **entonces** recibo
  409 y no se crea nada.
- **Dado** un plan que no existe o que está retirado, **cuando** lo contrato,
  **entonces** recibo 404.
- **Dado** que mando un importe, un estado o cualquier campo que no sea `plan_id`,
  **cuando** contrato, **entonces** recibo 422.
- **Dado** que pido `GET /subscriptions/me`, **entonces** recibo mi suscripción
  actual (o `null`) y el historial de las anteriores.
- **Dado** que soy trainer o admin, **cuando** uso estos endpoints, **entonces**
  recibo 403. Sin token, 401.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/subscriptions` | Member | 201 `SubscriptionOut` | 401, 403, 404, 409, 422 |
| GET | `/subscriptions/me` | Member | 200 `MySubscriptionsOut` | 401, 403 |

Entrada: `SubscriptionCreate`, solo `plan_id`, con `extra="forbid"`.
Salida: `SubscriptionOut` con `status`, `start_date`, `end_date` (nula mientras
está activa) y el plan anidado (`SubscriptionPlanOut`: nombre, precio mensual y
si incluye entrenamiento personal). `MySubscriptionsOut` trae `current` e
`history`.

Tablas que se tocan: `subscriptions` y `payments`. Sin cambios de esquema.

## Interfaz

- Botón "Contratar" en cada plan de la página de pricing.
- Bloque de suscripción en "Mi área": plan actual, fecha de inicio y el pago
  pendiente de la cuota, con enlace a "Mis pagos".
- Estados a mostrar: sin suscripción, el 409 de que ya tiene una activa y error
  de red.

## Fuera de alcance

- Pagar la cuota → HU-24.
- Darse de baja → HU-19 (solicitarla) y HU-20 (aprobarla).
- Cambiar de plan: hoy hay que darse de baja y volver a contratar.
- Renovación mensual automática: solo se crea el pago de la primera cuota.

## Preguntas abiertas

- No hay cobro recurrente: la suscripción no genera una cuota cada mes. Para la
  entrega vale (el pago es simulado), pero conviene decirlo en la retrospectiva
  antes de que lo pregunten.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| El importe se lee del plan y el cuerpo solo acepta `plan_id` (`extra="forbid"`) | Igual que en los pedidos: si el cliente pudiera mandar el precio o el estado, se contrataría un plan por un euro o ya pagado. |
| La suscripción y su pago se crean en la misma transacción | Una suscripción activa sin su cuota pendiente es una socia que entra gratis. |
| El pago nace `pending`, no `paid` | Contratar no es pagar. El cobro es la HU-24, y así el flujo es el mismo que en los pedidos y las clases extra. |
| Un plan retirado devuelve 404, no 409 | Para quien contrata, un plan que no está a la venta es un plan que no existe. La HU-08 no toca las suscripciones que ya lo tenían. |
| `GET /subscriptions/me` devuelve `current` e `history` por separado, no una lista | "Mi área" pinta las dos cosas distintas sin tener que filtrar por estado en el front. |
| No hay endpoint para cancelar la suscripción | RN-12: la socia solo puede pedir la baja, y la cancela administración al aprobarla (RN-13). |
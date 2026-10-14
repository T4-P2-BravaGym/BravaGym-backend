# HU-19 · Solicitar la baja

Issue: #84 · Entrega 1 · Tamaño S · Prioridad P1

## Contexto

> Como socia quiero pedir la baja desde la app para no tener que ir al gimnasio a pedirla.

La socia no puede borrarse ni desactivarse sola. Solo puede abrir una solicitud
`pending` que administración revisará (HU-20). Mientras tanto sigue activa y con
su suscripción.

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. Una socia con suscripción activa puede solicitar la baja indicando un motivo.
2. Se crea una solicitud `pending`; la usuaria y la suscripción siguen activas.
3. Solo una solicitud `pending` a la vez.
4. No existe ningún endpoint para que la socia se borre a sí misma.
5. Puede consultar el estado de su última solicitud.

## Reglas

- **RN-12**: no existe endpoint para que la socia se borre. Solo puede crear una
  solicitud de baja, y solo una `pending` a la vez → 409.

## Criterios de aceptación

- **Dado** que tengo una suscripción activa, **cuando** solicito la baja con un
  motivo, **entonces** se crea una solicitud `pending` y sigo activa.
- **Dado** que ya tengo una pendiente, **cuando** solicito otra, **entonces**
  recibo 409.
- **Dado** cualquier usuaria, **cuando** busca un endpoint para borrarse,
  **entonces** no existe.
- **Dado** que no tengo suscripción activa, **cuando** solicito la baja,
  **entonces** recibo 404.
- **Dado** que soy trainer o admin, **cuando** uso estos endpoints de socia,
  **entonces** recibo 403. Sin token, 401.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/cancellation-requests` | Member | 201 `CancellationRequestOut` | 401, 403, 404, 409, 422 |
| GET | `/cancellation-requests/me` | Member | 200 `CancellationRequestOut` | 401, 403, 404 |

Entrada: `CancellationRequestCreate` con `reason` obligatorio
(`min_length=1`, `max_length=2000`, `extra="forbid"`). Índice único parcial de
una `pending` por suscripción.

## Interfaz

- Flujo "Solicitar baja" en Mi área, con campo de motivo.
- Confirmación de que la baja queda pendiente (sigue siendo socia).
- Estados: ya hay una pendiente (409), sin suscripción, error de red.

## Fuera de alcance

- Aprobar o rechazar la solicitud → HU-20.
- Dar de baja directa por administración → HU-31.
- Borrado físico de la fila de usuaria: nunca.

## Preguntas abiertas

Ninguna: la historia está mergeada en `dev`.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| La socia sigue `is_active=true` hasta la aprobación | RN-12 / AC: la solicitud no es la baja todavía |
| Índice único parcial + manejo de IntegrityError → 409 | Dos clics simultáneos no crean dos `pending` |
| Sin `DELETE /users/me` ni similar | Cumple el AC de que no exista auto-borrado |
| GET `/me` → 404 si nunca ha solicitado | Distinto de "no hay pendiente": aquí no hay historial |

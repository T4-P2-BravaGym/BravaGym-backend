# HU-20 · Revisar solicitudes de baja

Issue: #87 · Entrega 1 · Tamaño M · Prioridad P1

## Contexto

> Como administración quiero aprobar o rechazar bajas para gestionarlas con control.

La socia ya puede solicitar la baja (HU-19). Administración necesita una bandeja
para aprobar (cadena RN-13) o rechazar con notas.

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. Administración ve las solicitudes paginadas, filtrables por estado.
2. Al aprobar: suscripción `cancelled`, usuaria inactiva, reservas futuras
   canceladas (con promoción de lista de espera).
3. Al rechazar es obligatorio `admin_notes`.
4. Una usuaria dada de baja no puede iniciar sesión (401).
5. Aprobar o rechazar una solicitud que no está `pending` → 409.

## Reglas

- **RN-13**: al aprobar la baja: suscripción `cancelled`, `users.is_active =
  false`, `deactivated_at` relleno y reservas futuras canceladas (aplicando
  **RN-06**). Rechazar exige `admin_notes`.
- El plazo **RN-05** no aplica al cancelar reservas por baja de membresía.

## Criterios de aceptación

- **Dado** una solicitud pendiente, **cuando** la apruebo, **entonces** la
  suscripción queda `cancelled`, la usuaria inactiva y sus reservas futuras
  canceladas.
- **Dado** una solicitud, **cuando** la rechazo sin `admin_notes`, **entonces**
  recibo 422.
- **Dado** una usuaria dada de baja, **cuando** intenta iniciar sesión,
  **entonces** recibe 401.
- **Dado** una solicitud ya resuelta, **cuando** la apruebo o rechazo otra vez,
  **entonces** recibo 409.
- **Dado** que soy member o trainer, **cuando** uso la bandeja, **entonces**
  recibo 403.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/cancellation-requests` | Admin, superadmin | 200 `CancellationRequestPage` | 401, 403, 422 |
| POST | `/cancellation-requests/{id}/approve` | Admin, superadmin | 200 `CancellationRequestOut` | 401, 403, 404, 409 |
| POST | `/cancellation-requests/{id}/reject` | Admin, superadmin | 200 `CancellationRequestOut` | 401, 403, 404, 409, 422 |

La bandeja incluye `member_name`, `member_email` y `plan_name`. Approve admite
`admin_notes` opcional; reject las exige (`min_length=1`).

## Interfaz

- Bandeja de administración con filtros por estado.
- Acciones Aprobar / Rechazar; el rechazo pide notas obligatorias.
- Estados: vacío, pendiente, ya resuelta (409), error de red.

## Fuera de alcance

- Solicitar la baja como socia → HU-19.
- Baja directa sin solicitud → HU-31.
- Reactivar a una usuaria dada de baja.

## Preguntas abiertas

- Si la socia tenía reservas en espera en varias sesiones, el orden de promoción
  es por sesión (RN-06). Sin cambio respecto a HU-13.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Reutilizar `cancel_future_bookings_for_user` (HU-13) sin RN-05 | La baja de membresía no puede quedar bloqueada por el plazo de 1 h |
| Login 401 si `is_active=false` (ya en auth) | Cumple el AC sin endpoint nuevo |
| Reject exige notas; approve las hace opcionales | RN-13 solo obliga notas al rechazar |
| Listado newest-first con `status` opcional | Misma forma de bandeja que otros listados admin |

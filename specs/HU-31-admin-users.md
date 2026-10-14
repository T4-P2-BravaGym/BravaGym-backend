# HU-31 · Gestión de usuarias para administración

Issue: #180 · Entrega 2 · Tamaño M · Prioridad P1

> Todavía no existe la plantilla `specs/README.md` (D-01). Esta spec usa las secciones que pide la D-01 y se ajustará cuando esté.

## Contexto

> Como administración quiero ver, editar y dar de baja a una usuaria para gestionar el gimnasio sin tocar la base de datos.

Completa el CRUD de usuarias del nivel esencial: ya existían el listado (`GET /users`, HU-06), el perfil propio (`/users/me`, HU-04) y el cambio de rol (HU-05). Falta ver, editar y dar de baja a otra usuaria.

## Requisitos

1. Una admin o superadmin puede ver los datos y el rol de cualquier usuaria.
2. Puede cambiar su nombre, apellidos, teléfono y email, pero nunca su rol, su estado ni su contraseña.
3. Puede darla de baja: la usuaria queda inactiva, pero su fila no se borra.
4. La baja tiene el mismo efecto que una solicitud de baja aprobada (HU-20): se cancelan su suscripción y sus reservas futuras.
5. Cada baja queda en el log: quién da de baja a quién.

## Reglas

- **RN-18** (aplicada a editar y dar de baja): una admin no puede editar ni dar de baja a una admin o superadmin. Solo la superadmin puede.
- **RN-19**: nadie se da de baja a sí misma, y siempre queda al menos una superadmin.
- **RN-13** (cadena de la HU-20): suscripción `cancelled`, usuaria inactiva, reservas futuras canceladas y la lista de espera sube (RN-06).
- **HU-19** sigue siendo cierta: una socia no puede borrarse a sí misma; solo administración da de baja.
- Editar usa las mismas reglas que `PATCH /users/me` (HU-04): solo los campos enviados, email en minúsculas y sin espacios, 409 si es de otra persona.

## Criterios de aceptación

- **Dado** que soy admin, **cuando** pido `GET /users/{id}`, **entonces** veo sus datos y su rol, sin `password_hash`; si no existe, 404.
- **Dado** que soy admin, **cuando** hago `PATCH /users/{id}` con nombre o email, **entonces** cambian; si el email es de otra persona, 409.
- **Dado** que envío `role`, `is_active` o `password` en el `PATCH`, **entonces** se ignoran.
- **Dado** que soy admin, **cuando** hago `DELETE /users/{id}`, **entonces** recibo 204, la usuaria queda con `is_active = false` y `deactivated_at`, y si intenta hacer login recibe 401.
- **Dado** que la usuaria tiene suscripción activa y reservas futuras, **cuando** la doy de baja, **entonces** la suscripción queda `cancelled` y las reservas `cancelled`.
- **Dado** que intento darme de baja a mí misma, **entonces** recibo 409.
- **Dado** que soy admin, **cuando** intento editar o dar de baja a una admin o superadmin, **entonces** recibo 403.
- **Dado** que soy member o trainer, **entonces** recibo 403; sin token, 401.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/users/{id}` | Admin, superadmin | 200 `UserOut` | 401, 403, 404 |
| PATCH | `/users/{id}` | Admin, superadmin | 200 `UserOut` (body `UserAdminUpdate`) | 401, 403, 404, 409, 422 |
| DELETE | `/users/{id}` | Admin, superadmin | 204 sin cuerpo | 401, 403, 404, 409 |

Las rutas `/{id}` van **después** de `/me` en el router: si no, FastAPI lee `me` como un id.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Una admin tampoco puede **editar** a una admin o superadmin | Si pudiera cambiar el email de la superadmin, podría quedarse con su cuenta al recuperar la contraseña (HU-35). OWASP A01 |
| Dar de baja a alguien ya inactivo → 204 sin hacer nada | La operación es idempotente: el resultado ya es el pedido |
| La cadena de baja se escribe en `user_service`, sin llamar a la de la HU-20 | La de la HU-20 depende de una solicitud de baja. Sacar una función común tocaría `cancellation_service.py`; se puede proponer después |
| `UserAdminUpdate` hereda de `UserUpdate` | Mismos campos y límites (DRY); el nombre dice quién lo usa |
| `update_me` y `update_user` comparten `_apply_profile_changes()` | Las reglas del email viven en un solo sitio |

## Fuera de alcance

- Borrar la fila de verdad (borrado físico): nunca se borran usuarias.
- Reactivar a una usuaria dada de baja.
- Cambiar el rol: es la HU-05 (`PATCH /users/{id}/role`).
- Cambiar la contraseña de otra persona: la contraseña es de cada una (HU-32, HU-35).
- La pantalla de administración (subtarea de frontend aparte).

## Preguntas abiertas

- Si se da de baja a una **entrenadora**, ¿qué pasa con sus clases futuras? De momento no se tocan.
- Si la socia tenía una **solicitud de baja pendiente** (HU-19), ¿se marca como aprobada? De momento no se toca.
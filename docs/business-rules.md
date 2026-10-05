## Reglas de negocio

Cada regla tiene un código (RN-xx) para enlazarla desde las historias y nombrar los tests, por ejemplo `test_rn05_cancel_less_than_one_hour_returns_409`.

### Reservas y clases

- **RN-01** Para reservar hace falta un usuario activo con una suscripción `active`. Si no → 403.
- **RN-02** Si las reservas `confirmed` son menos que `capacity`, la reserva queda `confirmed`; si no, `waitlisted`. La respuesta indica el estado y, en espera, la posición.
- **RN-03** No se puede reservar dos veces la misma sesión → 409. Si existía una reserva `cancelled`, se reactiva en lugar de crear otra.
- **RN-04** No se reservan sesiones pasadas ni sesiones `cancelled` → 409.
- **RN-05** Una reserva `confirmed` solo se cancela si faltan **60 minutos o más** para `starts_at`; si no → 409 con mensaje claro. Salir de la lista de espera se permite siempre.
- **RN-06** Al cancelarse una reserva `confirmed`, la reserva en espera más antigua (`created_at`) pasa a `confirmed` en la misma transacción, y se emite un evento por websocket.
- **RN-07** Si la clase tiene `extra_price_cents > 0`, al confirmarse la reserva se crea un pago `pending` asociado (también cuando sube desde la lista de espera).
- **RN-08** Entrenamiento personal: sesión de un tipo con `is_personal_training = true`, `capacity = 1` y 60 minutos. Solo la reservan socias cuyo plan tiene `includes_personal_training` → si no, 403.
- **RN-09** Un entrenador no puede tener dos sesiones solapadas → 409.
- **RN-10** Solo el entrenador de la sesión o el superadmin la editan o cancelan. Cancelar una sesión cancela sus reservas y deja los pagos de clases extra como `refunded`.

### Suscripciones y bajas

- **RN-11** Una sola suscripción `active` por usuario a la vez → 409.
- **RN-12** No existe endpoint para que la socia se borre. Solo puede crear una solicitud de baja, y solo una `pending` a la vez → 409.
- **RN-13** Al aprobar la baja: suscripción `cancelled`, `users.is_active = false`, `deactivated_at` relleno y reservas futuras canceladas (aplicando RN-06). Rechazarla exige `admin_notes`.

### Pagos, códigos y tienda

- **RN-14** Un código es válido si está activo, dentro de fechas y por debajo de `max_uses` (pagos `paid` que lo usan). Si no → 422. Vale para cualquier concepto: cuota, clase extra o pedido.
- **RN-15** `final_amount_cents = base_amount_cents × (100 − percent_off) / 100`, redondeado al céntimo.
- **RN-16** El pago simulado pasa de `pending` a `paid`. Un pago `paid` no se modifica; solo administración puede marcarlo `refunded`.
- **RN-17** Al crear un pedido se comprueba y descuenta el stock (sin stock → 409). Si el pedido se cancela, el stock se repone.

### Roles

- **RN-18** Administración solo cambia roles entre `member` y `trainer`. Asignar o quitar `admin` y `superadmin` es exclusivo del superadmin.
- **RN-19** Nadie cambia su propio rol, y siempre debe quedar al menos un superadmin → 409.

### Códigos HTTP comunes

| Código | Cuándo |
| --- | --- |
| 200 / 201 / 204 | Lectura o actualización / creación / borrado sin cuerpo |
| 401 | Sin token o token caducado |
| 403 | Token válido, pero el rol no tiene permiso (o RN-01, RN-08) |
| 404 | El recurso no existe, o no es suyo (una socia pidiendo la reserva de otra) |
| 409 | La petición choca con el estado actual: aforo, duplicados, plazo de 1 hora, stock |
| 422 | Datos mal formados o código de descuento inválido (Pydantic lo da gratis para lo primero) |
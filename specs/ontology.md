# Ontología del dominio de Brava

Las entidades del proyecto, sus relaciones y el vocabulario, en un solo sitio. Es lo que lee un agente (o una persona nueva en el equipo) antes de programar para no inventarse nombres ni reglas.

Sale de los modelos (`app/models/`), de `docs/er.md` (diagrama y decisiones de normalización) y de `docs/business-rules.md` (RN-01 a RN-21). Si algo no cuadra, manda el código y se corrige aquí.

## Glosario español ↔ código

El nombre que se usa hablando y el que se usa en el código. En la app la socia lee español; en el código todo va en inglés.

### Personas y roles

| En español | En el código |
| --- | --- |
| usuaria (cualquier persona con cuenta) | `user` |
| socia | rol `member` |
| entrenadora | rol `trainer` |
| administración | rol `admin` |
| superadministración | rol `superadmin` |
| perfil público de la entrenadora | `trainer_profile` |
| dar de baja una cuenta (sin borrarla) | soft delete: `is_active = false` + `deactivated_at` |

### Clases y reservas

| En español | En el código |
| --- | --- |
| tipo de clase | `class_type` |
| clase (una en concreto, con fecha y hora) | `class_session` |
| aforo | `capacity` |
| plazas libres | `free_spots` (se calcula, no se guarda) |
| clase con precio extra | `class_type.extra_price_cents > 0` |
| entrenamiento personal | `class_type.is_personal_training` |
| franja de entrenamiento personal | `class_session` de un tipo PT, aforo 1 y 60 min |
| reserva | `booking` |
| lista de espera | `booking` con `status = waitlisted` |

### Planes, bajas y rutinas

| En español | En el código |
| --- | --- |
| plan / tarifa | `membership_plan` |
| suscripción | `subscription` |
| baja (solicitud) | `cancellation_request` |
| ejercicio | `exercise` |
| rutina | `routine` |
| ejercicio dentro de una rutina | `routine_exercise` |

### Tienda y pagos

| En español | En el código |
| --- | --- |
| categoría | `product_category` |
| producto | `product` |
| talla | `product_variant` |
| foto de producto | `products.image_path` (nombre del archivo) / `image_url` (en la API) |
| pedido | `order` |
| línea de pedido | `order_item` |
| código de descuento / oferta | `discount_code` |
| pago (cuota, clase extra o pedido) | `payment` |
| concepto del pago | el único de `subscription_id`, `booking_id` u `order_id` que no es nulo |

### Cuenta y seguridad

| En español | En el código |
| --- | --- |
| iniciar sesión | `POST /auth/login` (access token + refresh token) |
| renovar la sesión | refresh token (`refresh_tokens`) |
| cerrar sesión | logout: revoca el refresh y el access (`revoked_tokens`) |
| recuperar la contraseña | `password_reset_tokens` |

> **Ojo con "sesión".** En el dominio, una *sesión* es una clase concreta (`class_session`, `/sessions`). La sesión de login es otra cosa: tokens y `users.session_version`. En los textos para la socia decimos "clase" para la primera.

## Entidades

Una por tabla, en el mismo orden que `docs/er.md`: qué representa en el gimnasio, sus atributos clave, con quién se relaciona y qué reglas la gobiernan. Al final, las tablas de seguridad, que no están en el diagrama.

Convenciones comunes a todas: el dinero va en céntimos enteros (`*_cents`), las fechas en UTC (el frontend las pasa a hora de Madrid) y nada que se pueda calcular se guarda.

### Plantilla de cada entidad

```markdown
### `nombre_tabla` — nombre en español

Qué es, en una frase de negocio.

- **Atributos clave:** los que importan para entenderla, no todas las columnas.
- **Relaciones:** con qué otras entidades, y de qué forma (una a muchas, etc.).
- **Reglas:** RN-xx que la afectan.
- **Estados:** si tiene ciclo de vida (`pending` → `paid` → `refunded`).
```

### `roles` — roles

Los cuatro papeles que puede tener una usuaria en Brava y que deciden qué puede hacer.

- **Atributos clave:** `name` único: `member`, `trainer`, `admin` o `superadmin`.
- **Relaciones:** un rol lo tienen muchas usuarias.
- **Reglas:** RN-18 (administración solo cambia entre `member` y `trainer`; `admin` y `superadmin` solo los toca superadmin) y RN-19 (nadie cambia su propio rol y siempre queda al menos un superadmin).

### `users` — usuarias

Cualquier persona con cuenta: socias, entrenadoras y administración. El rol dice cuál es.

- **Atributos clave:** `email` único, `password_hash` (bcrypt, nunca la contraseña), `first_name`, `last_name`, `phone`, `is_active`, `deactivated_at`. `session_version` invalida de golpe todas sus sesiones abiertas cuando se incrementa (por ejemplo, al restablecer la contraseña). Auditoría (T-03): `created_by_id`, `updated_at`, `updated_by_id`.
- **Relaciones:** pertenece a un rol. Como socia: suscripciones, reservas, rutinas que sigue, pedidos y pagos. Como entrenadora: un perfil público, las clases que imparte y las rutinas que diseña. Como administración: las bajas que revisa y los códigos que crea.
- **Reglas:** RN-01 (para reservar tiene que estar activa), RN-13 (una baja aprobada la desactiva), RN-18 y RN-19.
- **Estados:** activa → desactivada. Nunca se borra (soft delete), para conservar su historial de pagos.

### `trainer_profiles` — perfil de entrenadora

La ficha pública de una entrenadora, la que ven las socias para elegir con quién entrenar (HU-15).

- **Atributos clave:** `bio`, `specialty` y `photo_path` (T-291; vacío = avatar con iniciales).
- **Relaciones:** uno a uno con `users`: la clave primaria es el propio `user_id`.

### `membership_plans` — planes

Las tarifas mensuales del gimnasio que se muestran en la página de precios (HU-07) y gestiona administración (HU-08).

- **Atributos clave:** `name` único, `description`, `monthly_price_cents` (≥ 0), `includes_personal_training`, `is_active`.
- **Relaciones:** un plan define muchas suscripciones.
- **Reglas:** RN-08 (solo las socias con un plan que incluye entrenamiento personal reservan franjas PT).
- **Estados:** activo / inactivo. Un plan no se borra, se desactiva, porque hay suscripciones que lo nombran.

### `subscriptions` — suscripciones

El contrato de una socia con un plan: desde cuándo y en qué estado está (HU-09).

- **Atributos clave:** `start_date`, `end_date` (opcional), `status`.
- **Relaciones:** pertenece a una usuaria y a un plan. Tiene solicitudes de baja y pagos de cuota.
- **Reglas:** RN-01 (sin suscripción `active` no se reserva), RN-11 (una sola `active` por usuaria, también con índice único parcial en la BD) y RN-13.
- **Estados:** `active` → `cancelled` (baja aprobada) o `expired`.

### `cancellation_requests` — bajas

La petición de una socia para darse de baja. La socia no se borra sola: lo pide y administración decide (HU-19, HU-20).

- **Atributos clave:** `reason`, `status`, `requested_at`, `reviewed_by`, `reviewed_at`, `admin_notes`.
- **Relaciones:** cuelga de una suscripción (la socia se saca de ahí, sin repetir `user_id`). La revisa una usuaria de administración.
- **Reglas:** RN-12 (no hay endpoint para borrarse y solo una `pending` por suscripción, también con índice único parcial) y RN-13 (qué pasa al aprobarla; rechazarla exige `admin_notes`).
- **Estados:** `pending` → `approved` o `rejected`.

### `class_types` — tipos de clase

El catálogo de clases que ofrece el gimnasio: fuerza, halterofilia, entrenamiento personal…

- **Atributos clave:** `name` único, `description`, `extra_price_cents` (0 = incluida en la cuota), `is_personal_training`, `is_active`.
- **Relaciones:** un tipo se programa en muchas clases.
- **Reglas:** RN-07 (precio extra → pago `pending` al confirmar la reserva) y RN-08 (entrenamiento personal).

### `class_sessions` — clases

Una clase concreta en el horario: un tipo, una entrenadora, un día y una hora (HU-10, HU-11). Las franjas de entrenamiento personal también son clases (HU-14, T-11).

- **Atributos clave:** `starts_at` (UTC), `duration_minutes` (> 0), `capacity` (> 0), `status`. Las plazas libres y el final (`ends_at`) se calculan; `trainer_name` sale de la relación con `users`.
- **Relaciones:** pertenece a un tipo de clase y a una entrenadora (`trainer_id` → `users`). Recibe muchas reservas.
- **Reglas:** RN-04 (no se reservan pasadas ni canceladas), RN-08 (franja PT: aforo 1 y 60 minutos), RN-09 (una entrenadora no tiene dos clases programadas solapadas) y RN-10 (solo su entrenadora o superadmin la editan o cancelan; cancelarla cancela sus reservas).
- **Estados:** `scheduled` → `cancelled`.

### `bookings` — reservas

La plaza de una socia en una clase, confirmada o en lista de espera (HU-12, HU-13).

- **Atributos clave:** `status`, `created_at` (ordena la lista de espera), `cancelled_at`. La posición en la lista de espera se calcula.
- **Relaciones:** une una usuaria con una clase (una sola reserva por par, `UNIQUE`). Puede tener un pago si la clase tiene precio extra.
- **Reglas:** RN-01 a RN-08: requisitos para reservar, aforo y lista de espera, sin duplicados (una cancelada se reactiva), plazo de 60 minutos para cancelar, promoción automática desde la lista de espera con aviso por websocket, pago de clase extra y entrenamiento personal.
- **Estados:** `confirmed` o `waitlisted` → `cancelled`. Una `waitlisted` pasa a `confirmed` cuando se libera una plaza.

### `exercises` — ejercicios

El catálogo de ejercicios con el que las entrenadoras montan rutinas.

- **Atributos clave:** `name` único, `muscle_group`, `description`.
- **Relaciones:** aparece en muchas líneas de rutina.

### `routines` — rutinas

El plan de entrenamiento que una entrenadora diseña para una socia (HU-17, HU-18).

- **Atributos clave:** `name`, `start_date`, `notes`, `is_active`.
- **Relaciones:** la sigue una socia (`member_id`) y la diseña una entrenadora (`trainer_id`), las dos en `users`. Contiene sus ejercicios.
- **Estados:** activa → inactiva. Al crear una rutina nueva, la anterior queda inactiva y no se borra: así la entrenadora consulta el historial (T-12).

### `routine_exercises` — ejercicios de una rutina

Cada ejercicio de una rutina, en su día y su orden.

- **Atributos clave:** `day_number`, `position`, `sets`, `reps`, `rest_seconds` (60 por defecto).
- **Relaciones:** pertenece a una rutina y a un ejercicio. `UNIQUE(routine_id, day_number, position)`.

### `product_categories` — categorías

Cómo se agrupan los productos en la tienda (ropa, suplementos…).

- **Atributos clave:** `name` único.
- **Relaciones:** una categoría agrupa muchos productos.

### `products` — productos

Lo que se vende en la tienda del gimnasio (HU-21, HU-22).

- **Atributos clave:** `name`, `description`, `price_cents` (≥ 0), `stock` (≥ 0), `image_path`, `is_active`.
- **Relaciones:** pertenece a una categoría. Puede tener tallas y aparece en líneas de pedido.
- **Reglas:** RN-17 (stock al pedir y al cancelar), RN-20 (con tallas, `stock` se queda a 0 y el que se muestra es la suma de las tallas activas) y RN-21 (una foto como mucho, JPEG/PNG/WebP de hasta 2 MB).
- **Estados:** activo / inactivo. Desactivar no borra la foto, porque se puede reactivar.

### `product_variants` — tallas

Las tallas de un producto de ropa, cada una con su stock (HU-37).

- **Atributos clave:** `size` (`XS`, `S`, `M`, `L`, `XL`), `stock` (≥ 0), `is_active`.
- **Relaciones:** pertenece a un producto (`UNIQUE(product_id, size)`) y la nombran las líneas de pedido.
- **Reglas:** RN-20 (un pedido de ropa con tallas tiene que indicar una que se venda; una talla que se quita queda inactiva con stock 0, no se borra).

### `orders` — pedidos

Una compra de una socia en la tienda (HU-23).

- **Atributos clave:** `status`, `created_at`. El total se calcula sumando sus líneas.
- **Relaciones:** pertenece a una usuaria, tiene una o más líneas y como mucho un pago.
- **Reglas:** RN-16 (al pagarse, el pedido pasa a `paid` en la misma transacción) y RN-17 (descuenta stock; cancelarlo lo repone y cancela el pago).
- **Estados:** `pending` → `paid` o `cancelled` (solo mientras él y su pago están `pending`).

### `order_items` — líneas de pedido

Cada producto de un pedido, con su cantidad y el precio de ese momento.

- **Atributos clave:** `quantity` (> 0), `unit_price_cents` y `size`. Las dos últimas son una foto del momento de la compra: si el precio cambia mañana, el pedido de ayer no.
- **Relaciones:** pertenece a un pedido (se borra con él), a un producto y, si es ropa con tallas, a una talla (`variant_id`). `UNIQUE(order_id, product_id, variant_id)`.

### `discount_codes` — códigos de descuento

Las ofertas que crea administración y que se aplican al pagar (HU-25).

- **Atributos clave:** `code` único (en mayúsculas), `percent_off` (1–100), `valid_from` / `valid_until`, `max_uses` (opcional), `applies_to` (opcional: `subscription`, `booking` u `order`, T-240), `is_active`, `created_by`.
- **Relaciones:** lo crea una usuaria de administración y se aplica en muchos pagos. Los usos se cuentan en `payments`, no se guardan.
- **Reglas:** RN-14 (cuándo es válido) y RN-15 (cómo se calcula el importe final).

### `payments` — pagos

Cada cobro a una socia: la cuota de su plan, una clase con precio extra o un pedido (HU-24, HU-26, HU-29).

- **Atributos clave:** `base_amount_cents` y `final_amount_cents` (foto del importe, con `final ≤ base`), `status`, `method` (`simulated` o `stripe`), `provider_ref` (id de la Checkout Session de Stripe), `created_at`, `paid_at` (obligatorio si está `paid`).
- **Relaciones:** pertenece a una usuaria y a **exactamente un** concepto: suscripción, reserva o pedido (`CHECK` en la BD). Puede llevar un código de descuento. `user_id` es una desnormalización consciente para listar "mis pagos"; el servicio comprueba que coincide con la dueña del concepto.
- **Reglas:** RN-07 (pago de clase extra), RN-10 y RN-13 (qué pasa con los pagos al cancelar una clase o aprobar una baja), RN-14 y RN-15 (códigos), RN-16 (ciclo de vida, Stripe y reembolsos) y RN-17 (pedidos).
- **Estados:** `pending` → `paid` → `refunded`; `pending` → `cancelled` (se canceló lo que iba a cobrar) o `failed` (el cobro no salió).

### Seguridad y sesión de login

Estas tres tablas no son del negocio del gimnasio: sostienen el login (HU-33) y la recuperación de contraseña (HU-35). Ninguna guarda un token en claro, solo su hash.

#### `refresh_tokens` — tokens de renovación

Permiten renovar la sesión sin volver a escribir la contraseña.

- **Atributos clave:** `token_hash` único, `created_at`, `expires_at`, `revoked_at`.
- **Relaciones:** pertenecen a una usuaria.
- **Estados:** vigente → revocado (al renovar, porque rota, o al cerrar sesión) o caducado.

#### `revoked_tokens` — tokens de acceso revocados

La lista de access tokens que ya no valen aunque no hayan caducado, por ejemplo tras cerrar sesión.

- **Atributos clave:** `jti` (identificador del token) y `expires_at`. Pasada esa fecha, la fila ya no hace falta.

#### `password_reset_tokens` — enlaces de recuperación de contraseña

El enlace de un solo uso que recibe la usuaria cuando ha olvidado la contraseña.

- **Atributos clave:** `token_hash` único, `created_at`, `expires_at` (30 minutos), `used_at`.
- **Relaciones:** pertenecen a una usuaria. Al usarse, se incrementa su `session_version` y se cierran sus sesiones abiertas.
- **Estados:** vigente → usado o caducado.

## Reglas de negocio

Las RN-01 a RN-21 viven en `docs/business-rules.md`. Aquí solo se citan desde cada entidad, para no tener la misma regla escrita en dos sitios.
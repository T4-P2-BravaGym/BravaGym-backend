## Roles y permisos

Los permisos se comprueban con una sola dependencia de FastAPI, `require_roles("trainer", "superadmin")`, y no con `if` repartidos por los endpoints. "Propio" significa que el recurso pertenece a quien hace la petición.

| Recurso / acción | Público | Member | Trainer | Admin | Superadmin |
| --- | --- | --- | --- | --- | --- |
| Ver planes (pricing), tienda, horario de clases y entrenadores | ✅ | ✅ | ✅ | ✅ | ✅ |
| Registrarse e iniciar sesión | ✅ | — | — | — | — |
| Ver y editar su perfil | — | ✅ | ✅ | ✅ | ✅ |
| Contratar o cambiar de plan | — | ✅ | — | — | — |
| Reservar y cancelar sus reservas | — | ✅ | — | — | — |
| Ver su rutina, sus reservas y sus pagos | — | ✅ | — | — | — |
| Pagar (simulado) sus pagos pendientes | — | ✅ | — | — | — |
| Comprar en la tienda | — | ✅ | — | — | — |
| Solicitar la baja | — | ✅ | — | — | — |
| CRUD de sesiones y tipos de clase | — | — | ✅ propias | — | ✅ todas |
| Ver reservas de una sesión | — | — | ✅ propias | ✅ | ✅ |
| CRUD de ejercicios y rutinas | — | — | ✅ | — | ✅ |
| Ver y gestionar pagos, exportar CSV | — | — | — | ✅ | ✅ |
| CRUD de códigos de descuento | — | — | — | ✅ | ✅ |
| Revisar solicitudes de baja | — | — | — | ✅ | ✅ |
| CRUD de productos y categorías | — | — | — | ✅ | ✅ |
| CRUD de planes | — | — | — | ✅ | ✅ |
| Cambiar rol member ↔ trainer | — | — | — | ✅ | ✅ |
| Asignar o quitar admin y superadmin | — | — | — | — | ✅ |

Asumo que el CRUD de productos y planes es de administración, porque no lo especificasteis; si preferís otra cosa, se cambia en esta tabla.## Mapa de endpoints

Todas las rutas cuelgan de `/api/v1`. Cada grupo es un `APIRouter` con su `tag` de Swagger, de modo que la documentación interactiva queda agrupada por módulo. Los listados aceptan `page` y `size` (por defecto 1 y 20) y devuelven `{items, total, page, size}`.

| Método | Ruta | Quién | Notas |
| --- | --- | --- | --- |
| GET | `/health` | Público | Comprobación para Docker |
| POST | `/auth/register` | Público | Crea siempre un `member` |
| POST | `/auth/login` | Público | Devuelve el JWT |
| GET / PATCH | `/users/me` | Autenticado | Perfil propio |
| GET | `/users` | Admin, superadmin | Filtros `role`, `is_active`, `q` |
| PATCH | `/users/{id}/role` | Admin, superadmin | RN-18, RN-19 |
| GET | `/trainers` | Público | Con perfil y especialidad |
| PATCH | `/trainers/me/profile` | Trainer | Bio y especialidad |
| GET | `/plans` | Público | Página de pricing; solo activos |
| POST / PATCH / DELETE | `/plans`, `/plans/{id}` | Admin, superadmin | DELETE = desactivar |
| POST | `/subscriptions` | Member | RN-11; crea el pago `pending` de la cuota |
| GET | `/subscriptions/me` | Member | Suscripción actual e historial |
| GET | `/class-types` | Público | Incluye `extra_price_cents` |
| POST / PATCH / DELETE | `/class-types`, `/class-types/{id}` | Trainer, superadmin | DELETE = desactivar |
| GET | `/sessions` | Público | Filtros `from`, `to`, `class_type_id`, `trainer_id`, `only_available`; incluye plazas libres |
| POST / PATCH | `/sessions`, `/sessions/{id}` | Trainer, superadmin | RN-09, RN-10 |
| POST | `/sessions/{id}/cancel` | Trainer (propia), superadmin | RN-10 |
| GET | `/sessions/{id}/bookings` | Trainer (propia), admin, superadmin | Confirmadas y lista de espera |
| POST | `/sessions/{id}/bookings` | Member | RN-01 a RN-04, RN-07, RN-08 |
| GET | `/bookings/me` | Member | Filtro `status`, próximas o pasadas |
| POST | `/bookings/{id}/cancel` | Member (propia) | RN-05, RN-06 |
| WS | `/ws/sessions/{id}` | Público | Emite plazas libres al cambiar |
| CRUD | `/exercises` | Trainer, superadmin | Catálogo de ejercicios |
| POST / GET | `/routines` | Trainer, superadmin | GET filtra por `member_id` |
| PATCH / DELETE | `/routines/{id}` | Trainer, superadmin | DELETE = desactivar |
| POST / PATCH / DELETE | `/routines/{id}/exercises[/{item_id}]` | Trainer, superadmin | Líneas de la rutina |
| GET | `/routines/me` | Member | Rutina activa con sus ejercicios |
| POST | `/cancellation-requests` | Member | RN-12 |
| GET | `/cancellation-requests/me` | Member | Estado de su solicitud |
| GET | `/cancellation-requests` | Admin, superadmin | Filtro `status` |
| POST | `/cancellation-requests/{id}/approve`, `/reject` | Admin, superadmin | RN-13 |
| GET | `/products`, `/product-categories` | Público | Filtros `category_id`, `min_price`, `max_price`, `q` |
| POST / PATCH / DELETE | `/products[/{id}]`, `/product-categories[/{id}]` | Admin, superadmin | DELETE de producto = desactivar |
| POST | `/orders` | Member | RN-17; crea el pago `pending` |
| GET | `/orders/me` | Member | Con sus líneas |
| POST | `/orders/{id}/cancel` | Member (propio, `pending`) | Repone stock |
| CRUD | `/discount-codes` | Admin, superadmin |  |
| GET | `/discount-codes/{code}/validate` | Member | RN-14; devuelve el porcentaje |
| GET | `/payments/me` | Member | Filtro `status` |
| POST | `/payments/{id}/pay` | Member (propio) | Cuerpo opcional `{discount_code}`; RN-14 a RN-16 |
| GET | `/payments` | Admin, superadmin | Filtros `status`, `from`, `to`, `user_id`, `concept` |
| GET | `/payments/export` | Admin, superadmin | CSV con los mismos filtros |
| POST | `/payments/{id}/refund` | Admin, superadmin | RN-16 |
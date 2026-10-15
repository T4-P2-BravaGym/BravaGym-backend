# T-03 · Auditoría de usuarias (quién y cuándo)

Issue: #188 · Entrega 2 · Tamaño M · Prioridad P3 · Depende de: T-01 (Alembic)

## Contexto

Toca usuarios (nivel avanzado del README). Hoy `users` guarda cuándo se creó una cuenta
(`created_at`) y cuándo se dio de baja (`deactivated_at`), pero no quién la cambió por última vez
ni cuándo. Con el soft delete ya hecho (HU-31), falta saber quién toca cada cuenta. Las
historias que cambian una usuaria son HU-04, HU-05, HU-31 y HU-32.

## Requisitos

1. Cada usuaria guarda cuándo se modificó por última vez y quién lo hizo.
2. También guarda quién la creó; en el registro (HU-01) queda vacío, porque se crea ella misma.
3. Cuenta como modificación: editar el perfil (HU-04 y HU-31), cambiar el rol (HU-05), cambiar la contraseña (HU-32) y dar de baja (HU-31).
4. Las cuentas que existían antes del cambio quedan sin "última modificación" hasta que alguien las toque.
5. El cambio de esquema va en una migración de Alembic.

## Criterios de aceptación

- **Dado** que me registro, **entonces** `created_by_id`, `updated_at` y `updated_by_id` quedan vacíos.
- **Dado** que edito mi perfil, **entonces** `updated_at` es ahora y `updated_by_id` es mi id.
- **Dado** que cambio mi contraseña, **entonces** `updated_at` es ahora y `updated_by_id` es mi id.
- **Dado** que una admin cambia el rol de otra, **entonces** `updated_by_id` es el id de la admin.
- **Dado** que una admin edita a otra usuaria, **entonces** `updated_by_id` es el id de la admin.
- **Dado** que una admin da de baja a otra, **entonces** `updated_at` es ahora y `updated_by_id` es el id de la admin.
- **Dado** un cambio que falla (409, 403, 400…), **entonces** `updated_at` y `updated_by_id` no cambian.
- **Dado** `PATCH /users/me` sin ningún campo, **entonces** no cuenta como modificación.
- **Dado** la base de datos vacía, **cuando** aplico las migraciones, **entonces** `alembic check` no encuentra diferencias con los modelos.

## Endpoints

Sin endpoints nuevos. Cambia el esquema:

| Tabla | Columna | Tipo | Notas |
| --- | --- | --- | --- |
| `users` | `updated_at` | fecha y hora (UTC), opcional | Última modificación |
| `users` | `created_by_id` | FK a `users.id`, opcional | Quién la creó; vacío en el registro |
| `users` | `updated_by_id` | FK a `users.id`, opcional | Quién la modificó por última vez |

Lleva su migración de Alembic. Las filas existentes quedan con las tres columnas vacías.

## Interfaz

Sin interfaz en esta tarea. La subtarea opcional ("Última modificación" en el detalle de admin)
queda para después; ver "Fuera de alcance".

## Fuera de alcance

- Un historial con todos los cambios: solo se guarda el último.
- Auditar otras tablas (productos, planes, clases…).
- La baja aprobada desde una solicitud (HU-20): no está en la issue, y quién la aprobó ya se guarda en la solicitud (`reviewed_by`, `reviewed_at`).
- El perfil público de la entrenadora (HU-15): vive en `trainer_profiles`, no en `users`.
- Mostrar "Última modificación" en el panel de administración (subtarea opcional).

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Un solo ayudante `_mark_updated(user, actor)` en `user_service` | Quién y cuándo se rellena igual en los cinco cambios (DRY). |
| Se llama justo antes del `commit` y después de todas las comprobaciones | Un cambio rechazado (403, 409, 400) no llega a esa línea; y si el `commit` falla, el `rollback` lo deshace. |
| `_apply_profile_changes` recibe `actor` como argumento con nombre | Lo comparten HU-04 (ella misma) y HU-31 (la admin); así no se pueden confundir. |
| Un `PATCH` sin campos no cuenta como cambio | No se modificó nada; antes hacía un `commit` vacío. |
| `created_by_id` existe pero hoy siempre queda vacío | Las cuentas se crean en el registro o en el seed; no hay un endpoint para que admin cree usuarias. |
| La migración apaga las foreign keys de SQLite mientras reconstruye `users` | Para añadir una FK, SQLite copia la tabla y borra la vieja, y no puede borrarla mientras otras tablas apuntan a ella. Con datos reales, la migración fallaba; con la base vacía (CI) no se veía. |



# HU-06 · Listado de usuarios para administración

Issue: #34 · Entrega 1 · Tamaño S

## Contexto

> Como administración quiero buscar usuarios para gestionar socias y entrenadores.

Toca usuarios y el panel de administración. Con el registro (HU-02) y el login (HU-03) ya había
usuarias, pero administración no podía verlas. Es la base de la tabla donde después se cambian
roles (HU-05) y se editan o desactivan usuarias (HU-31).

## Requisitos

1. Administración ve un listado de todas las usuarias, paginado.
2. Puede filtrar por rol y por estado (activas o desactivadas).
3. Puede buscar por nombre, apellido o email, sin importar las mayúsculas.
4. El orden es siempre el mismo (apellido, nombre) para que las páginas no se mezclen.
5. Solo entran admin y superadmin; socias y entrenadoras no.
6. El listado nunca muestra la contraseña.

## Criterios de aceptación

- **Dado** que soy admin, **cuando** filtro por `role=member&is_active=true`, **entonces** recibo solo esas usuarias, paginadas.
- **Dado** que soy superadmin, **cuando** pido el listado, **entonces** recibo 200.
- **Dado** que soy member, **cuando** llamo al listado, **entonces** recibo 403.
- **Dado** que soy trainer, **cuando** llamo al listado, **entonces** recibo 403.
- **Dado** que no he iniciado sesión, **cuando** llamo al listado, **entonces** recibo 401.
- **Dado** más usuarias que el tamaño de página, **cuando** pido la página 2, **entonces** recibo las que faltan y el `total` correcto.
- **Dado** un email guardado en minúsculas, **cuando** busco con `q` en mayúsculas, **entonces** la encuentro.
- **Dado** `size` mayor que 100, **entonces** recibo 422.
- **Dado** un rol que no existe, **entonces** recibo 422.
- **Dado** cualquier listado, **entonces** ningún elemento incluye `password_hash`.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/users` | Admin, Superadmin | 200 `UserPage` | 401, 403, 422 |

Parámetros: `role`, `is_active`, `q` (hasta 60 caracteres), `page` (desde 1, por defecto 1) y
`size` (de 1 a 100, por defecto 20). `UserPage` es `{items, total, page, size}` con elementos
`UserOut`. No cambia el esquema.

## Interfaz

Pantalla "Usuarias y roles" (`/admin/usuarias`): buscador por nombre, apellido o email, selector
de rol y selector de estado, y una tabla con nombre, email, teléfono (un guion si no tiene), rol y
estado. Debajo, la paginación. Estados: cargando (spinner "Cargando usuarias…"), error (aviso rojo
con el mensaje de la API) y vacío ("No hay usuarias con estos filtros").

## Fuera de alcance

- Cambiar el rol desde la tabla (HU-05).
- Ver, editar o desactivar una usuaria (HU-31).
- Exportar el listado.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| `UserPage` hereda del `Page` genérico de `schemas/common.py` | Todo el equipo usa la misma forma `{items, total, page, size}`. |
| El permiso con `require_roles(ADMIN, SUPERADMIN)` | El control de rol vive en una dependencia y el router no tiene reglas. |
| Orden por `last_name`, `first_name` y después `id` | El `id` desempata y la paginación es estable. |
| `q` con `icontains(autoescape=True)` y sin espacios a los lados; si queda vacío no filtra | Busca sin mayúsculas, y un `%` o `_` escrito se toma como texto y no como comodín. |
| El filtro de rol pasa por la relación (`User.role.has(...)`) | El nombre del rol está en la tabla `roles`, no en `users`. |
| El servicio devuelve `(usuarias, total)` y el router arma `UserPage` | El servicio no depende de los esquemas de salida. |
| En el front, búsqueda con espera de 350 ms y `AbortController` | No se lanza una petición por cada letra y una respuesta vieja no pisa a la nueva. |
| Cambiar un filtro vuelve a la página 1 | Si no, podría quedarse en una página que ya no existe. |
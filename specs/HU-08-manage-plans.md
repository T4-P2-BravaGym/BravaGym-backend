# HU-08 · Gestión de planes

Issue: #42 · Entrega 1 · Tamaño S

## Contexto

> Como administración quiero crear, editar y retirar planes para mantener la oferta actualizada.

Esta spec documenta retrospectivamente la historia implementada en la PR backend #178 y la PR frontend #63. La gestión amplía el listado público de planes con operaciones protegidas y un panel de administración. Las subtareas son backend #43 y #44 y frontend #7.

## Requisitos

1. Admin y superadmin pueden crear, editar y retirar planes.
2. Un nombre repetido se rechaza sin modificar los planes existentes.
3. Retirar un plan lo deja inactivo; no borra el registro ni cambia sus suscripciones.
4. El listado público solo muestra planes activos. El listado de administración muestra activos y retirados, con paginación.
5. La edición parcial conserva los campos omitidos y permite vaciar la descripción.
6. Los precios se expresan en céntimos enteros no negativos.
7. Crear, editar y retirar un plan deja una entrada de log sin secretos.

## Reglas

Las reglas específicas proceden de los criterios de #42 y de `AGENTS.md`; `docs/business-rules.md` no les asigna un número RN propio.

- Borrado lógico: `is_active = false`, conservando las suscripciones.
- Acceso de gestión exclusivo para `admin` y `superadmin`.
- Códigos comunes de `docs/business-rules.md`: 401 sin autenticación, 403 sin permiso, 404 si no existe, 409 por duplicado y 422 por datos inválidos.

## Criterios de aceptación

- **Dado** que soy admin, **cuando** creo un plan con nombre repetido, **entonces** recibo 409 y no se crea otro plan.
- **Dado** un plan con suscripciones, **cuando** lo retiro, **entonces** queda inactivo y las suscripciones no cambian.
- **Dado** que soy admin o superadmin, **cuando** creo, edito o retiro un plan válido, **entonces** la operación tiene éxito.
- **Dado** que no he iniciado sesión, **cuando** intento gestionar planes, **entonces** recibo 401.
- **Dado** que soy member o trainer, **cuando** intento gestionar planes, **entonces** recibo 403 y los datos no cambian.
- **Dado** un plan existente, **cuando** edito solo el precio, **entonces** los campos omitidos se conservan.
- **Dado** un nombre usado por otro plan, **cuando** intento asignarlo al editar, **entonces** recibo 409.
- **Dado** un plan inexistente, **cuando** intento editarlo o retirarlo, **entonces** recibo 404.
- **Dado** un nombre vacío o un precio negativo, **cuando** envío el formulario, **entonces** recibo 422.
- **Dado** un plan retirado, **cuando** consulto la oferta pública, **entonces** no aparece; en el panel de administración sí aparece.
- **Dado** un plan ya retirado, **cuando** lo retiro otra vez, **entonces** permanece inactivo y conserva sus suscripciones.

## Endpoints

Todas las rutas llevan el prefijo `/api/v1`.

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/plans` | Público | 200 lista de `PlanOut` | — |
| GET | `/plans/admin` | Admin, superadmin | 200 `AdminPlanPage` | 401, 403, 422 |
| POST | `/plans` | Admin, superadmin | 201 `PlanOut` | 401, 403, 409, 422 |
| PATCH | `/plans/{plan_id}` | Admin, superadmin | 200 `PlanOut` | 401, 403, 404, 409, 422 |
| DELETE | `/plans/{plan_id}` | Admin, superadmin | 200 `PlanOut` | 401, 403, 404, 422 |

Se utilizan `PlanCreate` y `PlanUpdate` para validar entradas. Los esquemas de entrada y salida contienen ejemplos para Swagger. Esta documentación retrospectiva no cambia tablas, columnas ni migraciones.

## Interfaz

El panel `AdminPlans` lista planes activos y retirados con estado y paginación. Permite crear y editar planes, muestra los errores de la API y pide confirmación antes de retirarlos. Incluye estados de carga, vacío y error. La conexión con la API está en `services/plans.js` del frontend.

## Fuera de alcance

- Contratar un plan: HU-09.
- Borrar físicamente planes o modificar suscripciones al retirarlos.
- El refactor compartido de `CurrentAdmin`, que es una tarea técnica independiente.

## Preguntas abiertas

- Ninguna sobre el comportamiento implementado. El cierre documental requiere revisión humana y merge de esta PR.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Desactivar en lugar de borrar | Mantener las suscripciones y el historial existente. |
| Separar `/plans/admin` del listado público | Mostrar retirados solo a roles autorizados. |
| Usar edición parcial | Conservar los campos no enviados. |
| Una spec para backend y frontend | Documentar toda la historia según `specs/README.md`. |

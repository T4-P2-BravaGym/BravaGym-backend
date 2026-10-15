# HU-25 · Códigos de descuento

Issue: #105 · Entrega 1 · Tamaño S

## Contexto

> Como administración quiero crear códigos de descuento para lanzar ofertas.

Toca pagos. Los pagos ya guardaban un `discount_code_id`, pero no había forma de crear ni
comprobar códigos. Esta historia añade su gestión para administración y una validación para
la socia. Aplicar el descuento al pagar es la HU-24, que reutiliza esta misma comprobación.

## Requisitos

1. Administración crea códigos con un porcentaje, unas fechas de validez y, si quiere, un máximo de usos.
2. No puede haber dos códigos con el mismo texto; se guardan en mayúsculas.
3. Administración ve los códigos paginados, con cuántas veces se ha usado cada uno.
4. Puede cambiar porcentaje, fechas, máximo de usos y estado, pero no el texto del código.
5. Un código no se borra: se desactiva, porque hay pagos que lo nombran.
6. Una socia puede comprobar un código antes de pagar y saber su porcentaje.
7. Cada cambio queda en el log con el id de la admin y del código.

## Reglas

- **RN-14**: Un código es válido si está activo, dentro de fechas y por debajo de `max_uses` (pagos `paid` que lo usan). Si no → 422. Vale para cualquier concepto: cuota, clase extra o pedido.

## Criterios de aceptación

- **Dado** que soy admin, **cuando** creo un código en minúsculas, **entonces** recibo 201 y se guarda en mayúsculas.
- **Dado** que soy admin, **cuando** creo un código repetido, **entonces** recibo 409.
- **Dado** un porcentaje fuera de 1 a 100, o una fecha de fin anterior a la de inicio, **entonces** recibo 422.
- **Dado** que edito un código, **cuando** envío solo algunos campos, **entonces** el resto no cambia; y si las fechas quedan al revés, recibo 422.
- **Dado** que borro un código, **entonces** queda inactivo y sigue en la lista.
- **Dado** un código que no existe, **cuando** lo edito o lo borro, **entonces** recibo 404.
- **Dado** un código, **cuando** una socia lo valida, **entonces** recibe el porcentaje si es válido.
- **Dado** un código inexistente, inactivo, fuera de fechas o que ya llegó a `max_uses`, **cuando** una socia lo valida, **entonces** recibe 422 con el motivo.
- **Dado** pagos `pending` con un código, **cuando** cuento sus usos, **entonces** no cuentan; solo los `paid`.
- **Dado** que soy socia, **cuando** intento gestionar códigos, **entonces** recibo 403; sin sesión, 401.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/discount-codes` | Admin | 200 `DiscountCodePage` | 401, 403, 422 |
| POST | `/discount-codes` | Admin | 201 `DiscountCodeOut` | 401, 403, 409, 422 |
| GET | `/discount-codes/{code}/validate` | Member | 200 `DiscountValidationOut` | 401, 403, 422 |
| PATCH | `/discount-codes/{code_id}` | Admin | 200 `DiscountCodeOut` | 401, 403, 404, 422 |
| DELETE | `/discount-codes/{code_id}` | Admin | 204 | 401, 403, 404 |

`DiscountCodeOut` lleva `uses`, que se calcula al responder. No cambia el esquema: la tabla
`discount_codes` ya existía.

## Interfaz

"Ofertas y códigos" (`/admin/codigos`): una tabla paginada con los códigos, su porcentaje,
fechas, usos y estado, y un formulario para crear uno (código, % de descuento, válido desde,
válido hasta y usos máximos opcionales). Desactivar pide confirmación ("¿Desactivar este
código?"). Estados: cargando, error al cargar, aviso verde al crear o desactivar y aviso rojo con
el mensaje de la API.

## Fuera de alcance

- Aplicar el código al pagar (HU-24).
- Códigos para una socia concreta o para un solo plan o producto.
- Cambiar el texto de un código ya creado.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| `uses` se calcula con los pagos `paid`, nunca se guarda | Es un dato derivado (AGENTS.md); así no puede desincronizarse. |
| Los pagos `pending` no cuentan como uso | Un pago sin terminar no ha gastado el código; RN-14 habla de pagos `paid`. |
| `get_valid_code` vive en el servicio y lo reutiliza el pago | La misma regla en un solo sitio para validar y para pagar (HU-24). |
| Un 422 distinto para cada motivo | La socia sabe si el código no existe, está caducado o agotado. |
| El código se guarda en mayúsculas y sin espacios | "verano20" y "VERANO20 " son el mismo código. |
| El 409 también cubre la carrera con el `UNIQUE` | Dos admins creando el mismo código a la vez. |
| Al editar, las fechas se comprueban con los valores que quedan | Cambiar solo `valid_until` podía dejarla antes de `valid_from`. |
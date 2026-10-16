# T-240 · Códigos de descuento por tipo de pago

Issue: #240 · Entrega 2

## Contexto

Toca pagos y códigos de descuento (HU-24, HU-25). Hoy un código vale para cualquier pago:
cuota, clase extra o pedido de la tienda (RN-14). Administración quiere lanzar ofertas solo
para un tipo, por ejemplo un código para las clases. El equipo eligió limitar por tipo de pago
y no por categoría de producto.

## Requisitos

1. Al crear o editar un código, administración puede limitarlo a un tipo de pago: cuotas, clases o pedidos. Si no lo limita, vale para todo, como hasta ahora.
2. Si una socia usa un código en un pago de otro tipo, se rechaza con un mensaje que dice para qué vale.
3. La comprobación previa de "Mis pagos" también avisa antes de pagar.
4. Los códigos que ya existen siguen valiendo para todo.
5. El cambio de esquema va en una migración de Alembic.

## Reglas

- **RN-14** (cambia): un código es válido si está activo, dentro de fechas y por debajo de `max_uses` (pagos `paid` que lo usan). Vale para cualquier concepto (cuota, clase extra o pedido), salvo que esté limitado a uno con `applies_to`: entonces, en otro concepto → 422. Se actualiza también en `docs/business-rules.md`.

## Criterios de aceptación

- **Dado** que soy admin, **cuando** creo un código con `applies_to: "booking"`, **entonces** recibo 201 y el código lo guarda.
- **Dado** que creo un código sin `applies_to`, **entonces** queda vacío y vale para todo.
- **Dado** un `applies_to` que no es `subscription`, `booking` ni `order`, **entonces** recibo 422.
- **Dado** que edito un código, **cuando** envío `applies_to: null`, **entonces** vuelve a valer para todo.
- **Dado** un código limitado a clases, **cuando** pago un pago de una clase con él, **entonces** se aplica el descuento.
- **Dado** un código limitado a clases, **cuando** pago una cuota o un pedido con él, **entonces** recibo 422 y el pago no cambia.
- **Dado** un código limitado a clases, **cuando** lo valido con `?concept=order`, **entonces** recibo 422; con `?concept=booking`, recibo 200.
- **Dado** que lo valido sin `concept`, **entonces** solo se comprueban las reglas de antes.
- **Dado** la base de datos con datos, **cuando** aplico la migración, **entonces** funciona y los códigos existentes quedan sin límite.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/discount-codes` | Admin | 201 `DiscountCodeOut` | 401, 403, 409, 422 |
| PATCH | `/discount-codes/{code_id}` | Admin | 200 `DiscountCodeOut` | 401, 403, 404, 422 |
| GET | `/discount-codes/{code}/validate?concept=` | Member | 200 `DiscountValidationOut` | 401, 403, 422 |
| POST | `/payments/{payment_id}/pay` | Member | 200 `PaymentOut` | 401, 403, 404, 409, 422 |

Cambia el esquema: columna `discount_codes.applies_to` (texto, opcional: `subscription`,
`booking` u `order`), con su migración de Alembic. `DiscountCodeCreate`, `DiscountCodeUpdate`,
`DiscountCodeOut` y `DiscountValidationOut` llevan `applies_to`.

## Interfaz

- "Ofertas y códigos" (`/admin/codigos`): el formulario tiene un selector "Vale para" (Todo,
  Cuotas, Clases, Tienda) y la tabla una columna con lo mismo.
- "Mis pagos": al comprobar un código se envía el tipo del pago; si no vale, sale el mensaje de la API.

## Fuera de alcance

- Limitar un código a una categoría de la tienda (ropa, proteína…) o a un plan concreto: el equipo eligió el tipo de pago.
- Limitar un código a varios tipos a la vez.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Se puede limitar a cuotas, clases o tienda, aunque se habló de clases y tienda | Cuesta lo mismo y permite ofertas solo para la cuota ("primer mes -20 %"). |
| `applies_to` usa el mismo `PaymentConcept` que los pagos | Los valores válidos viven en un solo sitio; Pydantic da el 422 con cualquier otro. |
| La comprobación está en `get_valid_code`, que usan la validación y el pago | La regla vive en un solo sitio (DRY); el pago saca el concepto del propio pago, no de la petición. |
| En la validación, `concept` es opcional | Sin él se comprueba como antes, así el front actual no se rompe. |
| La migración añade la `CHECK` a mano y apaga las foreign keys de SQLite mientras reconstruye la tabla | Alembic no detecta las `CHECK`, y `payments` apunta a `discount_codes` (mismo problema que en la T-03). |
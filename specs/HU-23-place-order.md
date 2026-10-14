# HU-23 · Hacer un pedido

Issue: #97 · Entrega 1 · Tamaño M · Prioridad P1

## Contexto

> Como socia quiero comprar productos para recogerlos en el gimnasio.

La tienda ya existía: se podían ver los productos (HU-21) y administración podía
gestionarlos (HU-22), pero no había forma de comprar. Esta historia cierra el
flujo: carrito, pedido, descuento de stock y un pago `pending` que la socia paga
después con la HU-24.

Spec escrita a posteriori, a partir de la issue y de las PR #225 (backend) y #65
(frontend).

## Requisitos

1. Una socia puede pedir varios productos a la vez, con la cantidad de cada uno.
2. Al crear el pedido se comprueba y se descuenta el stock de cada producto.
3. El pedido nace con un pago `pending` por el total, que se paga en la HU-24.
4. La socia ve sus propios pedidos, los más nuevos primero, con sus líneas y el
   estado de su pago.
5. La socia puede cancelar un pedido que todavía no ha pagado: el stock vuelve y
   el pago queda `cancelled`.
6. Todo o nada: si una línea del pedido falla, no se crea nada.

## Reglas

- **RN-17** (pedidos y stock) y **RN-16** (estados del pago), en
  `docs/business-rules.md`.

La HU-37 amplió la RN-17 con la **RN-20**: en la ropa con tallas el stock vive en
la talla. Esta spec describe la historia como se entregó, sin tallas; el
comportamiento con tallas está en `specs/HU-37-product-sizes.md`.

## Criterios de aceptación

- **Dado** productos con stock, **cuando** hago un pedido, **entonces** se crea
  con sus líneas, se descuenta el stock y se crea un pago `pending`, y recibo 201
  con el pedido y el total.
- **Dado** que pido más unidades de las que hay, o un producto inactivo,
  **cuando** confirmo, **entonces** recibo 409 y no cambia nada.
- **Dado** un carrito vacío, una cantidad fuera de 1–99, más de 50 líneas o el
  mismo producto repetido en dos líneas, **cuando** hago el pedido, **entonces**
  recibo 422 y no cambia nada.
- **Dado** un pedido `pending` con su pago `pending`, **cuando** lo cancelo,
  **entonces** recibo 200, el stock se repone y el pago queda `cancelled`.
- **Dado** un pedido que ya está pagado o ya cancelado, **cuando** intento
  cancelarlo, **entonces** recibo 409 y no cambia nada.
- **Dado** el pedido de otra socia, **cuando** intento verlo o cancelarlo,
  **entonces** recibo 404, no 403: no se revela que exista.
- **Dado** que soy trainer o admin, **cuando** uso estos endpoints, **entonces**
  recibo 403. Sin token, 401.
- **Dado** que mando un precio en el cuerpo de la petición, **cuando** se crea el
  pedido, **entonces** se ignora: el precio sale de la base de datos.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/orders` | Member | 201 `OrderOut` | 401, 403, 409, 422 |
| GET | `/orders/me` | Member | 200 `OrderPage` (`page`, `size` ≤ 100) | 401, 403 |
| POST | `/orders/{id}/cancel` | Member | 200 `OrderOut` | 401, 403, 404, 409 |

Entrada: `OrderCreate` con `items`, y cada línea `OrderLineIn` con `product_id` y
`quantity` (el campo `size` lo añadió la HU-37). Salida: `OrderOut` con las líneas,
`payment_id`, `payment_status` y `total_cents` calculado.

Tablas que se tocan: `orders`, `order_items`, `products` (el stock) y `payments`.
Sin cambios de esquema en esta historia, salvo el estado `cancelled` nuevo en el
enum de pagos.

## Interfaz

- Carrito de la socia en `CartContext` + `useCart`, guardado en `localStorage`.
- `CartLink` en el Navbar y en el menú de socia, con el número de unidades.
- Página de carrito con el resumen y el total, y pantalla de "Mis pedidos" con un
  `OrderCard` por pedido y el botón de cancelar en los pendientes.
- Estados a mostrar: carrito vacío, el 409 de stock insuficiente y error de red.

## Fuera de alcance

- Tallas de la ropa → HU-37.
- Pago real con pasarela → HU-29.
- Foto del producto en el carrito → HU-30.
- Que administración vea o gestione los pedidos de todas: no entra.

## Preguntas abiertas

Ninguna: la historia está mergeada en `dev`.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| El cuerpo de la petición solo lleva `product_id` y `quantity`; los precios se leen de la base de datos | Si el cliente pudiera mandar el precio, cualquiera se haría un pedido de un euro. Es el punto de "nunca confíes en la entrada" del apartado 7 de `AGENTS.md`. |
| El stock se descuenta con un `UPDATE` condicional en vez de `SELECT … FOR UPDATE` | SQLite ignora `with_for_update`, así que el bloqueo no protegía de dos pedidos simultáneos. El `UPDATE` con la condición del stock sí es atómico. |
| Estado de pago `cancelled` nuevo | Hacía falta distinguir un pago que nunca se cobró (pedido cancelado antes de pagar) de uno `refunded`. |
| El pedido de otra socia devuelve 404, no 403 | No revelar si el pedido existe. Igual que en el resto de la API. |
| Repetir un producto en dos líneas es 422, no se suma solo | Un carrito que manda dos líneas del mismo producto suele ser un error del front; mejor que falle y se vea. |
| Límites de 50 líneas por pedido y 99 unidades por línea | Evita un pedido absurdo que bloquee la base de datos. |
| Las fechas se arreglaron en el front dentro de esta misma PR (T-09) | Probando "Mis pedidos" se vio que la API devuelve UTC sin zona y el front lo leía como hora local. Se resolvió con `parseApiDate` en lugar de parchear solo `OrderCard`. |
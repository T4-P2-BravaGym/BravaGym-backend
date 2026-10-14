# HU-37 · Tallas en la ropa

Issue: #211 · Entrega 2 · Tamaño L · Prioridad P1

## Contexto

> Como socia quiero elegir la talla de la ropa al comprarla para recoger en el
> gimnasio la que me queda bien.
>
> Como administración quiero llevar el stock de cada talla para no vender una
> talla que no tengo.

La tienda vendía todo igual: un producto, un stock. Para la ropa eso no sirve,
porque una camiseta se agota en M y sigue habiendo S. Esta historia separa el
stock por talla sin romper los productos que no las tienen (suplementos,
accesorios).

Depende de la HU-23 (pedidos) mergeada. Toca los mismos archivos que la HU-30
(foto de producto): `ProductForm` y `ProductCard`.

Spec escrita a posteriori, a partir de la issue y de las PR de la rama
`feature/hu-37-product-sizes` en los dos repos.

## Requisitos

1. Un producto puede tener tallas (XS, S, M, L, XL) con su stock en cada una.
2. Un producto sin tallas sigue funcionando exactamente como antes.
3. En la tienda las tallas se ven en orden, y las agotadas no se pueden elegir.
4. Un pedido de ropa con tallas tiene que decir qué talla.
5. El stock que se descuenta, y el que se repone al cancelar, es el de esa talla.
6. Administración pone y cambia el stock de cada talla, y puede dejar de vender
   una talla sin perder los pedidos que ya la nombran.

## Reglas

Esta historia estrena la **RN-20**, que amplía la RN-17:

> **RN-20** La ropa puede tener tallas (XS, S, M, L, XL). Si un producto tiene
> tallas, su stock está en cada talla y `products.stock` se queda a 0: el stock
> que se muestra es la suma de las tallas activas. Un pedido de ese producto
> tiene que indicar una talla que se venda (si no → 422) y descuenta o repone el
> stock de esa talla (sin stock → 409). Una talla que se quita no se borra: queda
> inactiva con stock 0, porque los pedidos antiguos la siguen nombrando.

También aplican la **RN-17** (pedidos y stock) y la **RN-16** (estados del pago).

## Criterios de aceptación

- **Dado** un producto con tallas, **cuando** lo veo en la tienda, **entonces**
  veo sus tallas en orden (XS, S, M, L, XL), las agotadas aparecen desactivadas y
  "Añadir" no funciona hasta que elijo una.
- **Dado** un producto con tallas, **cuando** hago un pedido sin talla o con una
  talla que no se vende, **entonces** recibo 422 y no cambia nada.
- **Dado** una talla con stock, **cuando** la pido, **entonces** se descuenta el
  stock de esa talla y no el de las demás.
- **Dado** que pido más unidades de una talla de las que hay, **cuando**
  confirmo, **entonces** recibo 409 con un mensaje que nombra el producto y la
  talla ("Solo queda 1 unidad de «Camiseta Brava» en talla M") y no cambia nada.
- **Dado** un pedido pendiente con tallas, **cuando** lo cancelo, **entonces** se
  repone el stock de cada talla.
- **Dado** el carrito, **cuando** añado la misma camiseta en S y en M,
  **entonces** son dos líneas distintas, y el carrito, el pedido y "Mis pedidos"
  muestran la talla.
- **Dado** un producto sin tallas, **cuando** lo compro, **entonces** todo
  funciona como antes.
- **Dado** que soy admin, **cuando** creo o edito un producto, **entonces** puedo
  darle tallas y poner el stock de cada una. Una talla repetida, un stock
  negativo, más de cinco tallas o mandar `stock` junto con `sizes` devuelven 422.
- **Dado** una talla que ya tiene pedidos, **cuando** la quito del producto,
  **entonces** no se borra: queda inactiva con stock 0 y deja de mostrarse.
- **Dado** que soy member o trainer, **cuando** intento cambiar las tallas,
  **entonces** recibo 403. Sin token, 401.

## Endpoints

Ninguno nuevo. Cambia lo que mandan y devuelven los que ya existían:

| Método | Ruta | Quién | Qué cambia | Errores |
| --- | --- | --- | --- | --- |
| GET | `/products` | Público | `ProductOut` lleva `sizes` (tallas activas con su stock) y `stock` es la suma de las activas | — |
| GET | `/products/admin` | Admin | Igual, en `ProductAdminOut` <!-- TODO: confirmar si aquí está el filtro out_of_stock --> | 401, 403 |
| POST | `/products` | Admin | `ProductCreate` acepta `sizes` (máximo 5); entonces no se manda `stock` | 401, 403, 422 |
| PATCH | `/products/{id}` | Admin | `ProductUpdate.sizes` **sustituye** la lista: la talla que no venga se oculta, `[]` las quita todas | 401, 403, 404, 422 |
| POST | `/orders` | Member | Cada línea acepta `size` | 401, 403, 409, 422 |

Esquema nuevo: tabla `product_variants` (`id`, `product_id`, `size`, `stock`,
`is_active`, `UNIQUE(product_id, size)`) y enum `ProductSize`. En `order_items`,
las columnas `variant_id` y `size`. Son 19 modelos en total.

## Interfaz

- `ProductCard` en la tienda: selector de tallas en orden, las agotadas
  desactivadas, "Añadir" bloqueado hasta elegir.
- `ProductForm` en el panel: casilla "Tiene tallas"; si está marcada se manda
  `sizes` y no `stock`.
- `CartContext`: cada línea del carrito es producto + talla, identificada con
  `lineKey(productId, size)`.
- La talla se muestra en el carrito, en el resumen del pedido y en "Mis pedidos".
- Ficha y demo de `ProductForm` y `ProductCard` actualizadas en el Sandbox.

## Fuera de alcance

- Precio distinto por talla.
- Colores.
- Foto del producto → HU-30.
- Migración del cambio de esquema: no había Alembic cuando se hizo. Al mergear
  hubo que borrar `brava.db` y pasar el seed. Lo arregla la T-01.

## Preguntas abiertas

Ninguna: la historia está mergeada en `dev`.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| `products.stock` se queda a 0 en la ropa con tallas y no guarda la suma | `docs/er.md` dice que no se guarda nada derivable. El stock que se muestra se calcula: `Product.available_stock` en Python y `AVAILABLE_STOCK` en SQL (`shop_service.py`). |
| El pedido manda la talla por nombre (`"size": "M"`), no `variant_id` | El front ya sabe la talla que eligió la socia; pedirle un id interno le obligaba a arrastrar datos que no necesita. |
| `order_items` guarda `variant_id` **y** `size` | El nombre de la talla queda como foto: si la talla se retira, el pedido antiguo sigue diciendo "M". |
| Una talla quitada pasa a `is_active = false` con stock 0 en vez de borrarse | Los pedidos antiguos la siguen nombrando. Volver a mandarla la reactiva. |
| Al cancelar un pedido, si la talla se quitó después, sus unidades no vuelven | No tiene sentido reponer stock de algo que ya no está a la venta. |
| Mandar `stock` y `sizes` juntos es 422, no se elige uno | Son dos formas incompatibles de llevar el stock; si se aceptan las dos, nadie sabe cuál manda. |
| En el carrito la línea se identifica con `lineKey(productId, size)` | La misma camiseta en S y en M son dos líneas, no una con cantidad 2. |
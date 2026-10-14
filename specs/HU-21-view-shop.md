# HU-21 · Ver la tienda

Issue: #91 · Entrega 1 · Tamaño S · Prioridad P1

## Contexto

> Como visitante quiero ver los productos por categoría para saber qué puedo comprar.

Primera historia de la tienda. Solo lectura y sin token: cualquiera que entre en la
web puede ver el catálogo, aunque no sea socia. Comprar llega en la HU-23 y
gestionar el catálogo en la HU-22.

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. Cualquiera, con token o sin él, puede listar los productos a la venta.
2. Los productos desactivados no aparecen.
3. Se puede filtrar por categoría, por rango de precio y buscar por nombre.
4. El resultado viene paginado y ordenado.
5. Un producto sin stock se ve, pero marcado como agotado.
6. Se pueden listar las categorías para montar el filtro.

## Reglas

- **RN-17** (stock de los pedidos) y, desde la HU-37, **RN-20** (stock por talla),
  en `docs/business-rules.md`.

## Criterios de aceptación

- **Dado** productos activos, **cuando** filtro por categoría y precio,
  **entonces** veo solo los que cumplen, paginados.
- **Dado** un producto sin stock, **cuando** lo veo, **entonces** aparece como
  agotado (`in_stock` en `false`).
- **Dado** un producto desactivado, **cuando** listo la tienda, **entonces** no
  sale.
- **Dado** que busco por un trozo del nombre en minúsculas, **cuando** listo,
  **entonces** encuentro el producto aunque su nombre lleve mayúsculas.
- **Dado** que no mando token, **cuando** listo productos o categorías,
  **entonces** funciona igual: la tienda es pública.
- **Dado** `page` 0, `size` 200 o un precio negativo, **cuando** listo,
  **entonces** recibo 422.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/products` | Público | 200 `ProductPage` | 422 |
| GET | `/product-categories` | Público | 200 lista de `CategoryOut` | — |

Filtros de `/products`: `category_id`, `min_price` y `max_price` (en céntimos,
ambos inclusive), `q` (búsqueda sin distinguir mayúsculas en el nombre, hasta 60
caracteres), `sort` (los valores están en `ProductSort`, por defecto el nombre),
`page` (≥ 1) y `size` (1–100, por defecto 20).

`ProductOut` lleva `id`, `category_id`, `category_name`, `name`, `description`,
`price_cents`, `stock`, `sizes` e `in_stock`. Los campos `sizes` y el `stock`
calculado los añadió la HU-37.

Sin cambios de esquema: usa `products` y `product_categories`.

## Interfaz

- Página de tienda con el listado, el filtro de categorías, el de precio y el
  buscador.
- `ProductCard` por producto, con el aviso de agotado.
- Estados a mostrar: cargando, sin resultados y error de red.

## Fuera de alcance

- Crear o editar productos → HU-22.
- Comprar → HU-23.
- Tallas → HU-37.
- Foto del producto → HU-30.

## Preguntas abiertas

- La API devuelve `description`, pero la tienda no la muestra. Se vio probando la
  HU-22 y está apuntado dentro de la HU-30.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| La tienda es pública, sin token | Es escaparate: si hay que registrarse para ver los precios, no se vende nada. |
| Los precios se guardan y se devuelven en céntimos (`price_cents`) | Con decimales aparecen errores de redondeo en los totales. |
| `in_stock` se calcula al responder, no se guarda | Es derivable del stock; guardarlo sería una segunda fuente de verdad que se desincroniza. |
| El listado público nunca devuelve productos inactivos, sin parámetro para pedirlos | Para que no se pueda sacar el catálogo oculto trasteando con la query. Lo de admin va por otra ruta (HU-22). |
| `size` tiene techo de 100 | Evita que una petición se traiga la tabla entera. |
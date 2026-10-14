# HU-22 · Gestión de productos

Issue: #NN · Entrega 1 · Tamaño S · Prioridad P1

## Contexto

> Como administración quiero gestionar productos y categorías para mantener la
> tienda al día.

El otro lado de la HU-21: el panel con el que administración da de alta productos,
cambia precios y stock, y los retira. Sin esto el catálogo solo se puede tocar en
la base de datos.

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. Administración crea, edita y desactiva productos.
2. Administración crea, renombra y borra categorías.
3. Administración ve también los productos desactivados, con los retirados al final.
4. Un producto nunca se borra de verdad: se desactiva y se puede reactivar.
5. Una categoría solo se borra si no tiene ningún producto.
6. Los datos inválidos se rechazan antes de tocar la base de datos.

## Reglas

- **RN-18** y **RN-19** (quién puede qué), en `docs/business-rules.md`.

## Criterios de aceptación

- **Dado** que soy admin, **cuando** creo un producto con precio o stock
  negativos, sin nombre o con una categoría que no existe, **entonces** recibo
  422 y no se crea nada.
- **Dado** un producto con pedidos, **cuando** lo borro, **entonces** no se borra:
  queda inactivo y desaparece de la tienda.
- **Dado** un producto inactivo, **cuando** lo edito con `is_active` en `true`,
  **entonces** vuelve a la tienda.
- **Dado** que edito un producto, **cuando** mando solo el precio, **entonces**
  cambia solo el precio. Si mando `name` o `stock` a `null`, recibo 422.
- **Dado** una categoría con productos, aunque estén inactivos, **cuando** la
  borro, **entonces** recibo 409 y no se borra.
- **Dado** una categoría sin productos, **cuando** la borro, **entonces** recibo
    204.
- **Dado** un nombre de categoría que ya existe, **cuando** la creo o la
  renombro, **entonces** recibo 409.
- **Dado** que soy member o trainer, **cuando** uso cualquiera de estos
  endpoints, **entonces** recibo 403. Sin token, 401.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/products/admin` | Admin | 200 `ProductAdminPage` | 401, 403, 422 |
| POST | `/products` | Admin | 201 `ProductAdminOut` | 401, 403, 422 |
| PATCH | `/products/{id}` | Admin | 200 `ProductAdminOut` | 401, 403, 404, 422 |
| DELETE | `/products/{id}` | Admin | 200 `ProductAdminOut` | 401, 403, 404 |
| POST | `/product-categories` | Admin | 201 `CategoryOut` | 401, 403, 409, 422 |
| PATCH | `/product-categories/{id}` | Admin | 200 `CategoryOut` | 401, 403, 404, 409, 422 |
| DELETE | `/product-categories/{id}` | Admin | 204 | 401, 403, 404, 409 |

Filtros de `/products/admin`: `category_id`, `q`, `status` (`active`, `inactive`
u `out_of_stock`), `sort`, `page` y `size`. No tiene los de precio.

Validaciones: `name` 1–120, `description` hasta 2000, `price_cents` 0–1 000 000,
`stock` 0–100 000, `category_id` ≥ 1; nombre de categoría 1–60 y único. El campo
`sizes` y la regla de no mandar `stock` junto con `sizes` los añadió la HU-37.

Sin cambios de esquema.

## Interfaz

- Tabla de productos en el panel, con el filtro de estado y el buscador.
- `ProductForm` para crear y editar.
- Acción de desactivar con confirmación, y de reactivar en los inactivos.
- Gestión de categorías con el aviso de que una con productos no se puede borrar.

## Fuera de alcance

- Ver la tienda → HU-21.
- Tallas → HU-37.
- Foto del producto → HU-30.
- Auditoría de quién creó o modificó cada producto → T-03.

## Preguntas abiertas

- El panel tampoco muestra la descripción del producto. Apuntado en la HU-30.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| El borrado es siempre lógico, incluso sin pedidos | Un producto puede volver a venderse, y si tuvo pedidos su nombre y su precio tienen que seguir existiendo. |
| `DELETE` devuelve el producto en vez de 204 | El panel repinta la fila con el estado nuevo sin pedir otra vez la lista. |
| El listado de admin es otra ruta (`/products/admin`), no un parámetro del público | Así un fallo en un parámetro no puede filtrar el catálogo oculto. |
| Los retirados van al final del listado de admin | Lo que se gestiona a diario es lo activo. |
| El `PATCH` es parcial, pero un campo obligatorio enviado como `null` es 422 | No mandar un campo y mandarlo vacío son cosas distintas: la segunda casi siempre es un error del front. |
| Una categoría con productos no se borra (409), ni siquiera inactivos | Dejaría productos sin categoría y la tienda los agrupa por ella. |
# HU-30 · Foto de producto

Issue: #160 · Entrega 2 · Tamaño M · Prioridad M

## Contexto

> Como administración quiero subir una foto de cada producto para que la tienda muestre cómo es lo que se vende.
> Como visitante quiero ver la foto del producto para decidir qué comprar.

La tienda (HU-21) y el panel de productos (HU-22) muestran los productos sin foto. `ProductCard` ya enseña un hueco con el nombre cuando no hay `image_url`, pero la API nunca lo manda. Es la primera subida de archivos del proyecto: hasta ahora la API solo recibía JSON y el formulario del login.

Toca `ProductForm` y `ProductCard`, que ya cambiaron en la HU-22 y en la HU-37 (tallas). Esta historia parte de cómo quedaron en `dev` y no cambia lo que mandan para el producto ni para las tallas. Desde la T-01, el cambio de esquema va en una migración de Alembic. La HU-27 (Docker) necesitará un volumen para `media/`.

## Requisitos

1. Cada producto puede tener como mucho una foto.
2. Solo administración (admin y superadmin) sube, cambia o quita la foto.
3. Solo se aceptan fotos JPEG, PNG o WebP de hasta 2 MB. El tipo se comprueba por el contenido del archivo, no por su nombre ni por lo que diga el navegador.
4. El servidor genera el nombre del archivo guardado. El nombre original no se usa ni se guarda.
5. Al cambiar o quitar la foto, el archivo anterior se borra del disco.
6. Un archivo rechazado no deja nada guardado: ni un archivo en disco ni un cambio en el producto.
7. La tienda y el panel muestran la foto. Si no hay foto, se ve la tarjeta de siempre.
8. La foto nueva se ve en la tienda en cuanto se sube, sin esperar a que caduque la caché de la HU-28.
9. La tienda y el panel muestran también la descripción del producto (ahora no se ve en ninguno de los dos; visto al probar la HU-22).

## Reglas

- **RN-21** (nueva): un producto tiene como mucho una foto. Cambiarla o quitarla borra la anterior. Desactivar un producto no borra su foto, porque se puede reactivar (HU-22).
- **RN-17 y RN-20** no cambian: la foto no toca el stock ni las tallas.
- Seguridad (`AGENTS.md`): el permiso se comprueba en la API con `require_roles`. Nunca se acepta SVG, porque puede llevar JavaScript. La ruta del archivo no se construye nunca con algo que mande la usuaria (path traversal). El cliente recibe un mensaje genérico y el detalle va a los logs.

## Criterios de aceptación

- **Dado** que soy admin, **cuando** subo una foto JPEG, PNG o WebP de hasta 2 MB a un producto, **entonces** recibo 200 con el producto y su `image_url`, la imagen se descarga en esa URL y se ve en el panel y en la tienda.
- **Dado** un JPEG con nombre `foto.png` y `Content-Type: image/png`, **cuando** lo subo, **entonces** se acepta y se guarda como `.jpg`, porque el tipo sale de los bytes.
- **Dado** un SVG, un PDF o un `.exe` renombrado a `.jpg`, **cuando** lo subo, **entonces** recibo 422, en `media/products/` no aparece ningún archivo nuevo y el producto no cambia.
- **Dado** un archivo vacío, **cuando** lo subo, **entonces** recibo 422.
- **Dado** un archivo de más de 2 MB, **cuando** lo subo, **entonces** recibo 422 y no se guarda nada. Uno de 2 MB justos se acepta.
- **Dado** un producto con foto, **cuando** subo otra, **entonces** sustituye a la anterior y el archivo viejo ya no existe.
- **Dado** un producto con foto, **cuando** quito la foto, **entonces** recibo 200 con `image_url: null`, el archivo se borra y la tienda vuelve a la tarjeta sin foto.
- **Dado** un producto sin foto, **cuando** quito la foto, **entonces** recibo 200 y no cambia nada.
- **Dado** un producto sin foto, **cuando** lo veo en la tienda, **entonces** `image_url` es `null` y se ve la tarjeta de siempre.
- **Dado** un producto desactivado, **cuando** le subo una foto, **entonces** se guarda, igual que se puede editar.
- **Dado** que subo o quito una foto, **cuando** pido `GET /products` justo después, **entonces** ya sale la foto nueva.
- **Dado** un producto que no existe, **cuando** subo o quito su foto, **entonces** recibo 404.
- **Dado** que soy member o trainer, **cuando** intento subir o quitar una foto, **entonces** recibo 403 y no se guarda nada. Sin token, 401.
- **Dado** una URL de `/media/products/` que no existe, **cuando** la pido, **entonces** recibo 404.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| PUT | `/products/{id}/image` | Admin, superadmin | 200 `ProductAdminOut` (multipart, campo `file`) | 401, 403, 404, 422 |
| DELETE | `/products/{id}/image` | Admin, superadmin | 200 `ProductAdminOut` | 401, 403, 404 |
| GET | `/media/products/{archivo}` | Público | 200, la imagen | 404 |

`/media` se monta con `StaticFiles` fuera de `/api/v1`: son archivos, no API.

Cambios de esquema y configuración:

- `products.image_path`, `String(64)` nullable: solo el nombre del archivo (`<uuid4>.webp`), ni la carpeta ni la URL. Lleva su migración de Alembic (`add image_path to products`, con `batch_alter_table`), y `alembic check` no deja cambios pendientes.
- `ProductOut` y, por herencia, `ProductAdminOut`: campo `image_url: str | None` con el valor `/media/products/<archivo>`, o `null` sin foto. También va en los ejemplos de Swagger.
- `MEDIA_ROOT` en `Settings` y en `.env.example` (por defecto `media`). La carpeta se crea al arrancar si no existe. `media/` va en `.gitignore`.

## Interfaz

- **`services/api.js`:** `apiRequest` acepta `formData`. En ese caso no pone `Content-Type`, porque lo pone el navegador con el `boundary`. Hace falta una forma de completar la URL de la foto con el origen de la API (`API_URL` sin `/api/v1`) que deje como están las URL que ya son absolutas, `blob:` o `data:`.
- **`services/shop.js`:** `uploadProductImage(id, file)` y `deleteProductImage(id)`.
- **`ProductForm`:**
    - Campo "Foto (opcional)" con vista previa, botón "Quitar foto" y el texto "JPEG, PNG o WebP, hasta 2 MB".
    - El atributo `accept` solo filtra el selector de archivos: la validación sigue siendo de la API.
    - La vista previa usa `URL.createObjectURL`, y la URL se libera al cambiar de archivo o al desmontar.
    - Sigue sin llamar a la API: `onSubmit(body, image)`, donde `image` es `{ file }`, `{ remove: true }` o `null`.
    - `toProductBody` no cambia: la foto no va en el cuerpo.
- **`ProductsTab`:**
    - Primero guarda el producto y después sube o quita la foto.
    - Si el producto se guarda pero la foto falla, el producto queda guardado y se muestra el error: "El producto se ha guardado, pero la foto no: <detalle>".
    - Columna "Foto" con una miniatura, o el hueco si no hay foto.
    - Descripción bajo el nombre, en una línea recortada.
- **`ProductCard`:** muestra la foto con la URL completa (`alt=""`, porque el nombre está justo al lado) y la descripción bajo el nombre, recortada a dos líneas. Las tallas y el botón no cambian.
- **Sandbox:** ficha de `ProductForm` y `ProductCard` actualizada, con una demo con foto y otra sin foto.
- **Estados:** mientras guarda, "Guardando…"; un error 422 de la foto muestra el `detail` de la API.

## Fuera de alcance

- Varias fotos por producto, galería o zoom.
- Recortar, redimensionar o comprimir en el servidor, y generar miniaturas. La tarjeta encuadra la foto con `object-fit`.
- Volver a codificar la foto (con Pillow) para quitarle los metadatos EXIF. Ver "Preguntas abiertas".
- Fotos de usuarias o de entrenadoras.
- Guardar las fotos en la nube (S3 o similar): lo decide la HU-36.
- El volumen de `media/` en Docker: es de la HU-27.
- El límite de tamaño del cuerpo de la petición en el servidor o el proxy: es del despliegue (HU-36).
- Texto alternativo editable.
- Fotos en el seed: opcional, en otra PR.

## Preguntas abiertas

- ¿Volvemos a codificar la foto con Pillow? Comprobar la cabecera no garantiza que el resto del archivo sea una imagen. Propuesta: no en esta entrega, y anotarlo en la retrospectiva.
- Comprobar en `docs/business-rules.md` que el número RN-21 está libre y añadir allí la regla.
- Añadir "foto de producto" = `image_path` / `image_url` al glosario de `specs/ontology.md`.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| La foto tiene su propio endpoint multipart y no va dentro del `POST` o el `PATCH` JSON | Mezclar JSON y archivo obliga a mandar todo el producto como multipart. Así `ProductCreate`, `ProductUpdate`, las tallas y sus tests no cambian |
| `PUT` y no `POST` | Sustituye la única foto: repetirlo deja el mismo estado |
| `DELETE` devuelve 200 con el producto y no hace nada si no había foto | El panel actualiza la fila sin otra petición, igual que `DELETE /products/{id}` |
| En la base de datos se guarda solo el nombre del archivo y la URL se calcula en el esquema | Si cambian la carpeta o el dominio (despliegue), no hay que migrar datos |
| La URL es relativa (`/media/...`) y el front la completa con el origen de la API | No hace falta otra variable de entorno, y vale igual en local que desplegado |
| El tipo se detecta por los primeros bytes, sin Pillow | No añade dependencias y es lo que pide la issue |
| La extensión sale del tipo detectado | `StaticFiles` pone el `Content-Type` por la extensión, así que la foto siempre se sirve con su tipo real |
| Se leen como mucho 2 MB + 1 byte | Así se sabe si se pasa del límite sin cargar en memoria un archivo enorme |
| Más de 2 MB devuelve 422, no 413, con `code` propio: `invalid_image` (tipo) e `image_too_large` (tamaño), dos subclases de `ValidationAppError` | Mismo formato `{detail, code}`, el front ya sabe titular un 422 y los tests distinguen los dos casos por el `code` |
| Orden: escribir el archivo nuevo, hacer commit y después borrar el viejo. Si el commit falla, se borra el nuevo | La base de datos nunca apunta a un archivo que no existe. En el peor caso queda un archivo huérfano, no una foto rota |
| Subir o quitar la foto llama a `invalidate_products_cache()` | Si no, la tienda enseña la foto anterior hasta que caduca la caché (HU-28) |
| En los tests, `MEDIA_ROOT` apunta a `tmp_path` | No se ensucia `media/` y se puede comprobar que el archivo existe o se ha borrado |
| Servir una foto que existe no tiene test automático, solo el 404 | `StaticFiles` se monta al arrancar con la carpeta real; los tests guardan las fotos en `tmp_path`. Se comprueba a mano en el navegador |
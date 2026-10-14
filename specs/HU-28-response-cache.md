# HU-28 · Caché de respuestas

Issue: #116 · Entrega 2 · Tamaño S · Prioridad P2

## Contexto

> Como visitante quiero que pricing y la tienda carguen rápido para navegar sin esperas.

Los listados públicos de planes (HU-07) y productos (HU-21) golpean la base en
cada petición. Esta historia añade una caché en memoria con TTL e invalidación
al CRUD de administración.

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. Dos peticiones seguidas a `/plans` (listado público activo) sirven la segunda
   desde caché.
2. Dos peticiones iguales a `/products` (mismos filtros) sirven la segunda desde
   caché.
3. Al crear, editar o borrar un plan o un producto (y categorías de producto), se
   invalida la caché afectada.
4. El TTL es configurable por `.env`.
5. La caché es un solo proceso en memoria (documentado); inyectable/limpiable en
   tests.

## Reglas

- Solo se cachean payloads JSON-serializables, nunca instancias SQLAlchemy.
- Claves: `plans:active` y `products:…` por tupla de filtros.
- Invalidar productos borra por prefijo (todas las variantes de filtros).
- Los listados admin no se cachean.

## Criterios de aceptación

- **Dado** dos peticiones seguidas a `/plans`, **cuando** la segunda llega,
  **entonces** sale de caché.
- **Dado** que administración edita un plan o un producto, **cuando** se guarda,
  **entonces** la caché de ese listado se invalida.
- **Dado** que pasa el TTL, **cuando** se vuelve a pedir, **entonces** se
  consulta de nuevo la base.
- **Dado** valores en `.env` (`CACHE_TTL_SECONDS`), **cuando** arranca la API,
  **entonces** la caché usa ese TTL.

## Endpoints

No añade rutas nuevas. Afecta el comportamiento de:

| Método | Ruta | Quién | Efecto |
| --- | --- | --- | --- |
| GET | `/plans` | Público | Lectura cacheada |
| GET | `/products` | Público | Lectura cacheada (clave por filtros) |
| POST/PATCH/DELETE | `/plans…`, `/products…`, categorías | Admin | Invalidan caché tras commit |

Implementación: `app/core/cache.py` (`TtlCache`), usada desde `plan_service` y
`shop_service`.

## Interfaz

Sin interfaz propia: la visitante solo nota menos latencia en pricing y tienda.

## Fuera de alcance

- Redis / caché multi-proceso.
- Cachear listados admin o endpoints autenticados.
- Invalidar productos cuando un pedido descuenta stock (el TTL acota el
  desfase de `in_stock`).

## Preguntas abiertas

Ninguna bloqueante: TTL por defecto 60 s.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Caché propia en memoria (dict + expiry), no Redis | Tamaño S; un proceso basta para la entrega |
| Guardar `model_dump(mode="json")` | El hit no depende de una sesión ORM viva |
| Invalidar productos por prefijo | Cualquier filtro cacheado quedaría fresco tras un CRUD |
| Invalidar también al tocar categorías | El nombre de categoría sale en las tarjetas del listado público |
| No invalidar por pedidos | Evita acoplar tienda ↔ pedidos; el TTL cubre stock stale breve |
| `CACHE_TTL_SECONDS` en settings / `.env.example` | Misma pauta que el resto de knobs operativos |

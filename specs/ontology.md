# Ontología del dominio de Brava

Las entidades del proyecto, sus relaciones y el vocabulario, en un solo sitio. Es lo que lee un agente antes de programar para no inventarse nombres ni reglas.

> **Estado: por rellenar (D-01).** Sale de `docs/er.md` (las 18 tablas y sus relaciones) y de `docs/business-rules.md` (RN-01 a RN-21). Se reparte entre el equipo por áreas; cada una rellena las entidades de las historias que ha hecho. Mientras esté incompleta, `docs/er.md` y `docs/business-rules.md` son la fuente buena.

## Glosario español ↔ código

El nombre que se usa hablando y el que se usa en el código. En la app la socia lee español; en el código todo va en inglés.

| En español | En el código |
| --- | --- |
| socia | `member` |
| entrenadora | `trainer` |
| administración | `admin` |
| clase | `class_session` |
| reserva | `booking` |
| lista de espera | `waitlist` |
| plan / tarifa | `plan` |
| suscripción | `subscription` |
| baja | `cancellation_request` |
| rutina | `routine` |
| pedido | `order` |
| talla | `product_variant` |
| foto de producto | `products.image_path` (nombre del archivo) / `image_url` (en la API) |
| código de descuento | `discount_code` |

<!-- TODO(D-01): completar con el resto de términos. -->

## Entidades

Una por tabla: qué representa en el gimnasio, sus atributos clave, con quién se relaciona y qué reglas la gobiernan.

### Plantilla de cada entidad

```markdown
### `nombre_tabla` — nombre en español

Qué es, en una frase de negocio.

- **Atributos clave:** los que importan para entenderla, no todas las columnas.
- **Relaciones:** con qué otras entidades, y de qué forma (una a muchas, etc.).
- **Reglas:** RN-xx que la afectan.
- **Estados:** si tiene ciclo de vida (`pending` → `paid` → `refunded`).
```

### `users` — usuarias

<!-- TODO(D-01) -->

### `class_sessions` — clases

<!-- TODO(D-01) -->

<!-- TODO(D-01): el resto de entidades, en el mismo orden que docs/er.md. -->

## Reglas de negocio

Las RN-01 a RN-21 viven en `docs/business-rules.md`. Aquí solo se citan desde cada entidad, para no tener la misma regla escrita en dos sitios.
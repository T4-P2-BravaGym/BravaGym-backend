# Specs de Brava

Una spec por historia o tarea técnica, antes de programar. Es lo que lee la persona y lo que lee el agente: si la spec está mal, el código sale mal.

- **Nombre del archivo:** `HU-XX-nombre-corto.md` o `T-XX-nombre-corto.md`, en inglés y con guiones (`HU-30-product-photo.md`).
- **Idioma:** español, igual que la issue. Los nombres de endpoints, tablas, esquemas y campos van en inglés, como en el código.
- **Una spec por historia, aunque toque los dos repos.** Vive aquí, en el backend. La parte de pantallas va en el apartado "Interfaz". Las PR del frontend enlazan a esta spec por su URL de GitHub. Las historias que son solo de frontend llevan su spec en `specs/` del repo del frontend.
- **Las historias ya hechas** también tienen su spec, escrita a partir de la issue y de la PR. La escribe quien hizo la historia.
- **Se enlaza en la PR** (`Spec: specs/HU-XX-nombre.md`) y es parte de la Definition of Done.

## Plantilla

Copia de aquí abajo. Quita los apartados que no apliquen, pero no te inventes otros: que todas se lean igual.

```markdown
# HU-XX · Título de la historia

Issue: #NN · Entrega 1 o 2 · Tamaño S/M/L · Prioridad P1/P2/P3

## Contexto

> Como <rol> quiero <qué> para <para qué>.

Dos o tres frases: qué parte del proyecto toca, qué existía antes y por qué hace falta
esto ahora. Si depende de otra historia o la bloquea, dilo aquí.

## Requisitos

Lista numerada de lo que tiene que ser verdad cuando esté hecha. En lenguaje de
negocio, sin hablar de código todavía.

1. ...
2. ...

## Reglas

Las reglas de negocio que aplican, citadas por su número (`docs/business-rules.md`).
Si la historia estrena una regla, se escribe aquí entera y se añade después al
documento de reglas.

- **RN-XX**: ...

## Criterios de aceptación

Los de la issue, en Dado / Cuando / Entonces. Cada criterio tiene que poder
convertirse en un test. Incluye siempre los casos de error, no solo el feliz.

- **Dado** ..., **cuando** ..., **entonces** ...

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/recurso` | Admin | 200 `RecursoOut` | 401, 403, 404 |

Si cambia el esquema, di qué tablas o columnas se tocan y que lleva su migración
de Alembic.

## Interfaz

Qué pantallas se tocan, qué componentes nuevos hacen falta y qué estados hay que
mostrar (carga, vacío, error). Si no hay pantalla, pon "sin interfaz".

## Fuera de alcance

Lo que alguien podría esperar de esta historia y no entra, con el número de la
historia que lo cubre si existe. Es el apartado que evita que el agente se
vaya por su cuenta.

- ...

## Preguntas abiertas

Lo que no está decidido. Se contesta antes de dar la historia por terminada, o se
convierte en una historia nueva.

- ...

## Decisiones

Se rellena **al implementar**: cada decisión que no estaba en la spec, con su por qué.
Es lo que se lee en la revisión de la PR y en la retrospectiva.

| Decisión | Por qué |
| --- | --- |
| ... | ... |
```

## Qué más hay aquí

- `ontology.md`: las entidades del dominio, sus relaciones y el glosario español ↔ código (socia = `member`, entrenadora = `trainer`…). Sale de `docs/er.md` y `docs/business-rules.md`.
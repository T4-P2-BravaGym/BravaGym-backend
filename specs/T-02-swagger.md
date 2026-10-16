# T-02 · Swagger enriquecido (tags, descripciones y respuestas de error)

Issue: #187 · Entrega 2 · Tamaño S-M · Prioridad P1

## Contexto

Toca la documentación de la API (nivel medio del README). FastAPI ya genera Swagger (`/docs`)
y ReDoc (`/redoc`) a partir del código, y casi todos los endpoints tienen `summary`. Pero los
grupos (tags) no tienen descripción, las respuestas de error solo tienen una frase y no enseñan
cómo es el cuerpo, y algunos endpoints no dicen todos los errores que pueden devolver. La API
no cambia: solo su documentación.

## Requisitos

1. Cada grupo de Swagger (tag) tiene una descripción en español.
2. La app tiene una descripción y una versión.
3. Hay un esquema `ErrorOut` (`detail`, `code`) que describe el cuerpo de todos los errores de la API.
4. Cada endpoint de todos los routers lista los errores que puede devolver (401, 403, 404, 409…) con `ErrorOut`, usando un diccionario común en vez de repetirlo.
5. Las descripciones propias de cada endpoint (por ejemplo "El email ya existe") se mantienen.
6. Todos los esquemas de entrada tienen un `example`.
7. `/redoc` funciona.

## Criterios de aceptación

- **Dado** `/docs`, **cuando** abro un grupo, **entonces** veo su descripción.
- **Dado** un error documentado (400, 401, 403, 404, 409, 429), **cuando** lo despliego en Swagger, **entonces** veo el esquema `ErrorOut` con un ejemplo.
- **Dado** un endpoint que necesita sesión, **entonces** documenta el 401; y si además necesita un rol, el 403.
- **Dado** un esquema de entrada, **cuando** pulso "Try it out", **entonces** el cuerpo trae un ejemplo.
- **Dado** `/redoc`, **cuando** lo abro, **entonces** se ve la documentación completa.
- **Dado** el esquema OpenAPI, **cuando** pasan los tests, **entonces** un test comprueba que todos los errores documentados usan `ErrorOut`.

## Endpoints

Sin endpoints nuevos ni cambios de comportamiento. No cambia el esquema de la base de datos.

## Interfaz

Sin interfaz: el cambio se ve en `/docs` y `/redoc`.

## Fuera de alcance

- Cambiar qué errores devuelve un endpoint: solo se documenta lo que ya devuelve.
- El 422 de validación de FastAPI: mantiene su propio esquema, porque su `detail` es una lista.
- El websocket de la HU-16: OpenAPI no documenta websockets.
- Traducir los `summary` existentes, que están en inglés como el código.
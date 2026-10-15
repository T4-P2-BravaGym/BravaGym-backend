# D-05 · Colección de Bruno con todos los endpoints

Issue: #198 · Entrega 2 · Tamaño M · Prioridad P1

## Contexto

> Como equipo quiero una colección de peticiones compartida para probar y demostrar todos los endpoints de Brava.

Las peticiones viven en `collections/brava/` y se revisan como texto en las PR. La colección refleja las operaciones HTTP del OpenAPI y añade la conexión WebSocket pública, que no aparece en OpenAPI.

## Requisitos

1. Una carpeta por tag, con un ejemplo de éxito y otro de error por operación HTTP.
2. Un entorno `local` con `baseUrl`, cuentas ficticias del seed e identificadores configurables.
3. Las peticiones de login guardan tokens en variables de ejecución, reutilizadas por las peticiones protegidas; nunca se commitean tokens reales.
4. Ejemplos con cuerpos válidos, códigos esperados y preparación documentada. Los recursos creados capturan sus identificadores para las peticiones siguientes.
5. Ejecución ordenada contra una base local recién inicializada con el seed; los ejemplos mutan esa base.
6. Instrucciones en el README para abrir la colección, seleccionar entorno, ejecutar peticiones y preparar/repetir los ejemplos.
7. La conexión WebSocket tiene ejemplos de ruta válida e identificador mal formado y se verifica por separado del runner HTTP.

## Criterios de aceptación

- **Dado** el backend inicializado con datos ficticios, **cuando** ejecuto el login, **entonces** el token se guarda y las peticiones posteriores lo reutilizan.
- **Dado** el inventario de operaciones HTTP, **cuando** reviso la colección, **entonces** cada operación tiene una petición de éxito y una de error bajo su tag.
- **Dado** una petición de éxito y sus requisitos de preparación, **cuando** la ejecuto, **entonces** cumple su código esperado.
- **Dado** una petición de error, **cuando** la ejecuto, **entonces** devuelve el error documentado y la comprobación pasa porque ese fallo es intencionado.
- **Dado** un endpoint público sin caso de error funcional, **cuando** pruebo un método no permitido en su ruta, **entonces** obtengo 405; el ejemplo indica expresamente que cambia el método.
- **Dado** el WebSocket, **cuando** conecto con un id entero, **entonces** se abre; con un id mal formado, se rechaza la conexión.

## Endpoints

El inventario se obtiene de `app.openapi()`, agrupado por tag. Incluye `/health` y todas las operaciones de `/api/v1`, además de WS `/api/v1/ws/sessions/{session_id}`. La colección no modifica la API ni añade tablas o migraciones.

## Interfaz

Bruno: abrir `collections/brava/`, elegir `local` y ejecutar en el orden definido. El runner HTTP comprueba códigos de respuesta; el WebSocket se abre manualmente en Bruno y se comprueba por separado.

## Fuera de alcance

- Ejecutar contra datos reales o un servicio de producción.
- Cambiar permisos, reglas o endpoints existentes.
- Sustituir la suite pytest o automatizar la revisión humana de PR.
- Afirmar un 404 para sesiones inexistentes en WebSocket: la ruta actual no valida existencia.

## Preguntas abiertas

- Ninguna para esta colección; las futuras operaciones deben añadirse con sus dos ejemplos.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Archivos `.bru` | Formato de texto soportado por Bruno y revisable en Git. |
| Tokens en variables de ejecución | Compartir autenticación sin guardar JWT en el repositorio. |
| Login separado por rol | Respetar permisos de member, trainer, admin y superadmin. |
| Ejemplos de error con 401, 422 o 405 | Mostrar fallos deterministas sin inventar reglas del servidor. |
| Capturar ids de recursos nuevos | Evitar modificar recursos del seed innecesariamente. |

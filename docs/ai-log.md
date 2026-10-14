# AI log

Cómo hemos usado la IA en cada historia. Es un entregable de la asignatura (apartado 10 de `AGENTS.md`) y cubre los dos repos.

## Cómo trabajamos con la IA

El flujo es el mismo en todas las historias, así que se describe aquí una vez y cada entrada recoge solo lo suyo.

1. **El contexto vive en el proyecto, no en el prompt.** Las tareas, el estado de `dev`, las convenciones y las reglas de negocio están escritas en documentos del proyecto que la IA lee al empezar. El prompt de cada historia es corto ("vamos a trabajar en la HU-23"); el trabajo está en mantener ese contexto al día.
2. **Un chat nuevo por tarea.** Así no arrastra decisiones de otra historia.
3. **La IA no escribe en el repo.** Propone el código comentado, lo pegamos nosotras y lo commiteamos nosotras. Tampoco ejecuta nada sin pedir permiso.
4. **Se comprueba antes de seguir:** `pytest`, `npm run dev` y el flujo a mano en el navegador. Si encaja, se continúa; si no, se corrige con la IA hasta que encaja.
5. **La revisión final es de otra compañera**, en la PR, con comentarios visibles.

Herramientas de pago (Claude): se usan en modo mentora, para explicar y revisar.
El alcance está delimitado en el apartado 1 de `AGENTS.md`.

## D-05 · Colección de Bruno — Beste Özaydın

- **Herramienta y modelo:** OpenAI Codex, GPT-6, con explicación paso a paso, generación de archivos y ejecución autorizada. La modalidad de pago de la cuenta no está confirmada.
- **Prompt clave:** "okay lets continue with the next one", tras describir #198 y su colección por tags, entorno local, login y ejemplos de éxito/error.
- **Qué me explicó o propuso:** inventariar el OpenAPI, crear archivos `.bru` por tag, guardar tokens con `bru.setVar`, capturar ids de los recursos creados y ejecutar los ejemplos en orden sobre una base temporal con el seed. Se consultó la documentación oficial de Bruno para formato, scripts y variables.
- **Qué acepté:** la spec previa, los ejemplos de todas las operaciones HTTP, logins por rol, el entorno local ficticio, las instrucciones del README y la verificación contra datos temporales. Autoricé a Codex a generar los archivos y ejecutar las herramientas; no se presenta como documentación escrita manualmente sin ayuda de IA.
- **Qué descarté:** ejecutar sobre la base habitual, guardar JWT en archivos, ejecutar las peticiones en paralelo o inventar un error funcional para endpoints públicos que no lo tienen. En esos casos se documenta un método no permitido (405). La conexión WebSocket se verifica aparte del runner HTTP.
- **Errores o alucinaciones:** en el primer intento, la configuración de login usaba `body: form-urlencoded`, que el runner no enviaba como formulario. El informe mostró cuerpo vacío y respuesta 422; se corrigió a `body: formUrlEncoded` conservando el bloque `body:form-urlencoded`, y se comprobó primero el login. También se comprobó que la CLI intentaba tratar el WebSocket como HTTP y se excluyó `realtime` del comando de ejecución, documentando la prueba separada.
- **Cómo lo comprobé:** el inventario cubre las 73 operaciones HTTP con un ejemplo de éxito y otro de error, más preparación y dos ejemplos WebSocket. Bruno CLI 4.2.1 ejecutó 152 peticiones HTTP sobre SQLite temporal con sus 152 pruebas de estado en verde. Los archivos se validan con el parser oficial; el WebSocket se verifica por separado. La base local habitual no se modificó. Los resultados finales quedan en la PR y la aprobación corresponde a otra compañera.

## D-01 y D-02 · Specs, ontología y `AGENTS.md` — Damaris

- **Herramienta y modelo:** Claude (de pago), en modo mentora en conversación. Alcance: solo documentación y revisión; no ha escrito ni ejecutado nada en el repo. Todo el texto lo he pegado y commiteado yo.
- **Prompt clave:** "Reconcilia el `AGENTS.md` con el README de la entrega: el README dice que el agente escribe el código y el apartado 1 dice que la IA es mentora, no programadora."
- **Qué me explicó o propuso:** una plantilla de spec con contexto, requisitos, reglas RN-xx, criterios Dado/Cuando/Entonces, endpoints, fuera de alcance y preguntas abiertas; el esqueleto de la ontología con el glosario español ↔ código; y un apartado 1 con dos modos de trabajo, mentora y agente.
- **Qué acepté:** la plantilla de specs, el esqueleto de la ontología, los comandos del proyecto, la regla de no debilitar un test nunca, y tres puntos nuevos en la Definition of Done (spec enlazada, revisión con comentarios visibles y entrada en esta bitácora).
- **Qué descarté:** los dos modos de trabajo. El 14 de octubre acordamos con la profesora no automatizar la implementación, así que se quitó el modo agente y la IA se queda como mentora. Renunciamos a la comparativa de dos modelos gratuitos del Nivel Medio; la justificación va en la retrospectiva.
- **Errores o alucinaciones:** nada inventado sobre el proyecto. Dos cosas que corregir sobre la marcha: propuso añadir "la cobertura no baja del 80 %" a la Definition of Done cuando eso todavía no se mide (queda para la T-04), y metió un `Refs #NN` en cada mensaje de commit que es redundante con el `Closes #NN` de la PR. También se le pasó que al reescribir el apartado 2 del front se habían borrado dos viñetas; lo detecté revisando el diff.

## HU-09 · Contratar un plan — Damaris

- **Herramienta y modelo:** Claude, en modo mentora. El código lo escribí y lo commiteé yo.
- **Prompt de partida:** "vamos a trabajar en la HU-09", con el contexto del proyecto cargado.
- **Qué salió de la conversación y acepté:** crear la suscripción y su pago pendiente en una sola transacción, leer el importe del plan y no de la petición, y `extra="forbid"` en el cuerpo para que no se pueda colar un precio o un estado. El detalle está en `specs/HU-09-subscribe-plan.md`.
- **Qué corregí o descarté:** no lo recuerdo. La historia se hizo en un solo commit (endpoints y tests juntos) y no quedó registro de correcciones.
- **Cómo lo comprobé:** `pytest` y el flujo de contratar desde pricing en el navegador.

## HU-21 · Ver la tienda — Damaris

- **Herramienta y modelo:** Claude, en modo mentora. El código lo escribí y lo commiteé yo.
- **Prompt de partida:** "vamos a trabajar en la HU-21", con el contexto del proyecto cargado.
- **Qué salió de la conversación y acepté:** que la tienda sea pública sin token, que el listado público no pueda devolver productos inactivos por ningún parámetro, y calcular `in_stock` al responder en vez de guardarlo.
- **Qué corregí o descarté:** para poder probar el caso de agotado hacía falta un producto sin stock, que no existía en el seed: se añadió uno. La ordenación por nombre y precio tampoco estaba en la primera versión y entró después, con sus tests.
- **Cómo lo comprobé:** `pytest` (filtros, agotado y paginación) y la tienda a mano.

## HU-22 · Gestión de productos — Damaris

- **Herramienta y modelo:** Claude, en modo mentora. El código lo escribí y lo commiteé yo.
- **Prompt de partida:** "vamos a trabajar en la HU-22", con el contexto del proyecto cargado.
- **Qué salió de la conversación y acepté:** que el borrado sea siempre lógico, que el
  listado de admin viva en otra ruta (`/products/admin`) en vez de ser un parámetro
  del público, y que una categoría con productos no se pueda borrar (409).
- **Qué corregí o descarté:** el filtro por estado del panel y que los productos
  retirados salgan al final no estaban en la primera versión; se añadieron después
  de probar la tabla del panel.
- **Cómo lo comprobé:** `pytest` (CRUD, validaciones y permisos) y el panel a mano.

## HU-23 · Hacer un pedido — Damaris

- **Herramienta y modelo:** Claude, en modo mentora. El código lo escribí y lo commiteé yo.
- **Prompt de partida:** "vamos a trabajar en la HU-23", con el contexto del proyecto cargado.
- **Qué salió de la conversación y acepté:** el pedido en una sola transacción, los precios leídos siempre de la base de datos (el cuerpo solo lleva producto y cantidad) y el descuento de stock con un `UPDATE` condicional, porque SQLite ignora `with_for_update` y el bloqueo no protegía de dos pedidos a la vez.
- **Qué corregí o descarté:** es la historia que más cambió al probarla. Salieron mejoras de UX del carrito, y dos cosas más grandes: las horas de "Mis pedidos" salían mal (la API devuelve UTC sin zona y el front lo leía como hora local), que se arregló en esta misma PR con `parseApiDate` (T-09); y la ropa necesitaba talla, que decidí **no** meter aquí y abrir como historia aparte (HU-37) para no estirar el alcance de esta.
- **Cómo lo comprobé:** `pytest` (stock y cancelación) y el flujo completo de carrito, pedido y "Mis pedidos" en el navegador.

## HU-37 · Tallas en la ropa — Damaris

- **Herramienta y modelo:** Claude, en modo mentora. El código lo escribí y lo commiteé yo.
- **Prompt de partida:** "vamos a trabajar en la HU-37", con el contexto del proyecto cargado.
- **Qué salió de la conversación y acepté:** no guardar el stock del producto como suma de las tallas (se calcula), mandar la talla por nombre y no por `variant_id`, y que una talla retirada quede inactiva en vez de borrarse, porque los pedidos antiguos la siguen nombrando.
- **Qué corregí o descarté:** nada. Salió bien a la primera, y creo que fue porque la historia venía ya acotada de haberla separado de la HU-23: el alcance estaba decidido antes de empezar.
- **Cómo lo comprobé:** `pytest` (tallas en productos y en pedidos) y el flujo de comprar la misma camiseta en dos tallas en el navegador.

## HU-17 · Crear rutinas — Viviana

- **Herramienta y modelo:** Claude (claude-opus-5-5), en modo mentora. El código lo escribí y lo commiteé yo, salvo un momento que cuento abajo.
- **Prompt de partida:** el texto de la issue #77 con sus criterios y sub-issues, con el contexto del proyecto cargado.
- **Qué salió de la conversación y acepté:** separar el catálogo de ejercicios en su propio servicio; desactivar la rutina anterior y crear la nueva en un solo commit; validar socia, ejercicios y posiciones antes de escribir nada; el 409 por día y posición repetidos comprobado en el servicio y, como última barrera, con el `UNIQUE` de la tabla; sacar el `trainer_id` del token y no del cuerpo; y reutilizar la vista de la HU-18 con `TrainerRoutineOut`. El detalle está en `specs/HU-17-create-routines.md`.
- **Qué corregí o descarté:** con prisa le pedí "dímelo entero" y generó los archivos completos en vez de guiarme paso a paso, que no es como trabajamos. Lo descarté y lo rehicimos archivo por archivo en el chat, escribiéndolo yo. Al empezar el frontend salió que el `RoutineEditor` que ya existía enviaba `exercises` en vez de `lines` y no mandaba `start_date`, y que la entrenadora no podía listar socias porque `GET /users` es solo de admin. En vez de abrir `GET /users` a entrenadoras, que habría expuesto emails y teléfonos, decidí un endpoint nuevo `GET /users/members` que solo devuelve id y nombre.
- **Errores o alucinaciones:** nada inventado sobre el proyecto: antes de proponer leyó los modelos, el `AGENTS.md` y el código existente. Los errores fueron míos al copiar y los pillaron los tests: usé `RoutineUpdate` en vez de `RoutineCreate` en el `POST` (500 en todos los tests de crear), puse mal una llave en la ruta `/{routine_id}/exercises` (404) y escribí `firts_line` en un test. También tuve que ajustar el test de la HU-18, porque las líneas ahora devuelven su `id`.
- **Cómo lo comprobé:** `pytest` (permisos, 409, 404, 422 y la desactivación de la rutina anterior), ruff y el flujo en Swagger: crear ejercicios, crear una rutina y repetir día y posición para ver el 409. Pendiente: el editor en el frontend (frontend#16).

## HU-05 · Gestión de roles — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Me explicaba cada paso en el chat y yo escribía o pegaba el código, ejecutaba los comandos y hacía los commits. Cubre el backend (PR #159) y el selector de rol del frontend (subtarea HU-05.5).
- **Prompt clave (en resumen):** "Guíame para implementar la HU-05 siguiendo las capas del proyecto: un endpoint para que administración cambie roles, con RN-18 y RN-19 comprobadas en el servicio y un test por cada criterio de aceptación." Con el backend ya mergeado: "Ahora llévalo a la tabla de usuarias: una admin tiene que poder pasar a una socia a entrenadora desde allí, sin saltarse esas reglas."
- **Qué me explicó o propuso:** en el backend, `PATCH /users/{id}/role` con `RoleUpdate`, las comprobaciones de RN-18 (403) y RN-19 (409) en `user_service.change_role`, crear un `TrainerProfile` vacío al pasar a entrenadora, el log con ids y sin emails, y los tests de `test_change_role.py`. En el frontend, `changeRole` en `services/users.js`, una función `roleChoices` con los roles que puede dar cada actora, el selector en la columna Rol y un modal de confirmación.
- **Qué acepté:** el endpoint, las reglas y los tests tal como están; en el front, el selector solo en filas que puedo gestionar, activas y que no son mías, la confirmación antes de cambiar y el aviso "X ahora es Y".
- **Qué descarté:** borrar el perfil de entrenadora al volver a socia; se conserva para no perder su bio. Tampoco cambié los permisos de tipos de clase que vimos de paso, porque son de la HU-11.
- **Errores o alucinaciones:** en los primeros tests salía un 500 en vez de 200, porque la base de datos de test no tenía los roles creados; lo arreglamos con una fixture `all_roles`. Al revisar el diff me dio números de línea equivocados; lo vi al comprobarlos yo.

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
- **Qué corregí o descarté:** con prisa le pedí "dímelo entero" y generó los archivos completos en vez de guiarme paso a paso, que no es como trabajamos. Lo descarté y lo rehicimos archivo por archivo en el chat, escribiéndolo yo. Al empezar el frontend salió que el `RoutineEditor` que ya existía enviaba `exercises` en vez de `lines` y no mandaba `start_date`, y que la entrenadora no podía listar socias porque `GET /users` es solo de admin. En vez de abrir `GET /users` a entrenadoras, que habría expuesto emails y teléfonos, decidí un endpoint nuevo `GET /users/members` que solo devuelve id y nombre. En el frontend: npm run build y el flujo a mano (crear una rutina como entrenadora, verla como socia en “Mi rutina”, crear otra y comprobar que la anterior queda inactiva, y el error de carga con el backend apagado)
- **Errores o alucinaciones:** nada inventado sobre el proyecto: antes de proponer leyó los modelos, el `AGENTS.md` y el código existente. Los errores fueron míos al copiar y los pillaron los tests: usé `RoutineUpdate` en vez de `RoutineCreate` en el `POST` (500 en todos los tests de crear), puse mal una llave en la ruta `/{routine_id}/exercises` (404) y escribí `firts_line` en un test. También tuve que ajustar el test de la HU-18, porque las líneas ahora devuelven su `id`.
- **Cómo lo comprobé:** `pytest` (permisos, 409, 404, 422 y la desactivación de la rutina anterior), ruff y el flujo en Swagger: crear ejercicios, crear una rutina y repetir día y posición para ver el 409. Pendiente: el editor en el frontend (frontend#16).

## HU-05 · Gestión de roles — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Me explicaba cada paso en el chat y yo escribía o pegaba el código, ejecutaba los comandos y hacía los commits. Cubre el backend (PR #159) y el selector de rol del frontend (subtarea HU-05.5).
- **Prompt clave (en resumen):** "Guíame para implementar la HU-05 siguiendo las capas del proyecto: un endpoint para que administración cambie roles, con RN-18 y RN-19 comprobadas en el servicio y un test por cada criterio de aceptación." Con el backend ya mergeado: "Ahora llévalo a la tabla de usuarias: una admin tiene que poder pasar a una socia a entrenadora desde allí, sin saltarse esas reglas."
- **Qué me explicó o propuso:** en el backend, `PATCH /users/{id}/role` con `RoleUpdate`, las comprobaciones de RN-18 (403) y RN-19 (409) en `user_service.change_role`, crear un `TrainerProfile` vacío al pasar a entrenadora, el log con ids y sin emails, y los tests de `test_change_role.py`. En el frontend, `changeRole` en `services/users.js`, una función `roleChoices` con los roles que puede dar cada actora, el selector en la columna Rol y un modal de confirmación.
- **Qué acepté:** el endpoint, las reglas y los tests tal como están; en el front, el selector solo en filas que puedo gestionar, activas y que no son mías, la confirmación antes de cambiar y el aviso "X ahora es Y".
- **Qué descarté:** borrar el perfil de entrenadora al volver a socia; se conserva para no perder su bio. Tampoco cambié los permisos de tipos de clase que vimos de paso, porque son de la HU-11.
- **Errores o alucinaciones:** en los primeros tests salía un 500 en vez de 200, porque la base de datos de test no tenía los roles creados; lo arreglamos con una fixture `all_roles`. Al revisar el diff me dio números de línea equivocados; lo vi al comprobarlos yo.

## HU-04 · Ver y editar mi perfil — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí o pegué el código, ejecuté los comandos y hice los commits.
- **Prompt clave:** "vamos a trabajar en la HU-04", con el contexto del proyecto cargado.
- **Qué me explicó o propuso:** el esquema `UserUpdate` sin rol ni estado, `GET` y `PATCH /users/me` con `exclude_unset`, el email en minúsculas con 409 si es de otra, y la pantalla "Mi perfil".
- **Qué acepté:** todo lo anterior y probar a mano en Swagger con Lucía antes de los tests. En el TODO compartido, quitar solo la parte ya hecha en vez de borrarlo, porque HU-05 y HU-06 aún no tenían dueña.
- **Qué descarté:** `git add` de una carpeta entera; añado los archivos por su nombre para no colar cambios de otra historia.
- **Errores o alucinaciones:** al verificar el borrador salió que un nombre `null` daba 500 en vez de 422; se arregló en el esquema y se añadió un test.

## HU-15 · Conocer a las entrenadoras — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código y los commits.
- **Prompt clave:** "vamos a trabajar en la HU-15", y para la subtarea "Mi perfil público": "que quede como en el diseño".
- **Qué me explicó o propuso:** `GET /trainers` con un esquema propio sin contacto, `PATCH /trainers/me/profile` que crea el perfil si falta, y en el front la cuadrícula de `TrainerCard` y la pantalla de la entrenadora.
- **Qué acepté:** empezar la página con datos de prueba para aprender `map` y `key`, y cambiarlos después por la API; no crear un `GET /trainers/me` y buscar su tarjeta en el listado.
- **Qué descarté:** la primera versión de "Mi perfil público", con un formulario y una tarjeta de vista previa aparte; no era el diseño y la rehicimos como la tarjeta del diseño.
- **Errores o alucinaciones:** nada inventado sobre el proyecto; el desvío del diseño lo detecté comparando con el archivo de diseño.

## HU-16 · Plazas libres en tiempo real — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código y los commits.
- **Prompt clave:** "vamos a trabajar en la HU-16", con el contexto del proyecto cargado.
- **Qué me explicó o propuso:** un gestor de websockets por clase, el puente `notify_from_sync` entre los servicios síncronos y el event loop, avisar después del `commit`, un mensaje sin datos personales, y en el front `watchSession` y el hook `useSessionUpdates`.
- **Qué acepté:** el diseño completo y probarlo con dos ventanas (Lucía y Carmen) viendo cambiar las plazas.
- **Qué descarté:** mandar el número de plazas dentro del mensaje; la página vuelve a pedirlo a la API.
- **Errores o alucinaciones:** nada inventado. Al probar, cancelar fallaba en "Mis reservas", pero era un fallo de otra historia (el front leía `class_session`); se avisó a su dueña en vez de tocar su código. Mis errores al copiar (un `assert` que faltaba, el hook con el nombre mal escrito y un archivo sin guardar) los pillaron los tests y la revisión.

## HU-18 · Ver mi rutina — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código y los commits.
- **Prompt clave:** "vamos a trabajar en la HU-18", con el contexto del proyecto cargado.
- **Qué me explicó o propuso:** `GET /routines/me` con la socia sacada del token, los días agrupados en la API, 404 con mensaje amable sin rutina, y en el front una pestaña por día como en el diseño.
- **Qué acepté:** todo lo anterior; y en el front, tratar el 404 como estado vacío y no como error.
- **Qué descarté:** fijar siempre 7 días; se muestran solo los días que tiene la rutina.
- **Errores o alucinaciones:** el primer borrador agrupaba con `groupby` sin ordenar antes, y un día podía salir partido; se añadió el orden explícito. Un archivo de estilos de otra historia entró por error en el dal y lo saqué antes de la PR.

## HU-25 · Códigos de descuento — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código y los commits.
- **Prompt clave:** "vamos a trabajar en la HU-25", con el contexto del proyecto cargado.
- **Qué me explicó o propuso:** el CRUD de `discount_codes` con borrado lógico, `uses` calculado con los pagos `paid`, `get_valid_code` con un 422 por cada motivo de RN-14, reutilizado al pagar, y el panel "Ofertas y códigos".
- **Qué acepté:** todo lo anterior y los tests de fechas y `max_uses` con freezegun.
- **Qué descarté:** añadir reglas sobre SQL injection a la documentación; el proyecto ya usa el ORM y no hace falta.
- **Errores o alucinaciones:** en los tests usó el código `VERANO20` con fechas de octubre; lo vi yo y lo cambiamos por un nombre que no dependa de la estación. Al copiar el router se me quedó fuera la línea `router = APIRouter(...)` y lo detectó la revisión.

## HU-31 · Gestión de usuarias para administración — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código y los commits.
- **Prompt clave:** "vamos a trabajar en la HU-31; antes, escribamos la spec".
- **Qué me explicó o propuso:** `GET`, `PATCH` y `DELETE /users/{id}` con RN-18 también al editar, la baja con la cadena de la HU-20, reutilizar `_apply_profile_changes` de la HU-04, y en el front la columna Acciones, el panel de ver y editar y el modal de baja.
- **Qué acepté:** todo lo anterior; ajustar el test de la HU-19, que ahora tiene que aceptar que exista un `DELETE` solo para administración.
- **Qué descarté:** sacar una función común con la baja de la HU-20, porque tocaba `cancellation_service.py` de otra compañera; queda como propuesta.
- **Errores o alucinaciones:** al revisar el diff me dio números de línea equivocados; lo vi al comprobarlos yo. En el front, la primera columna de acciones usaba `max-content` y los botones se descolocaban en las filas sin "Editar"; se cambió por huecos fijos.

## HU-30 · Foto de producto — Damaris

- **Herramienta y modelo:** Claude (de pago), en modo mentora. Leyó el código con mi permiso, solo lectura. El código lo escribí y lo commiteé yo.
- **Prompt de partida:** "vamos a trabajar en la HU-30", con el contexto del proyecto cargado y dos condiciones: la spec antes de tocar código y el cambio de esquema en una migración de Alembic (T-01), no borrando `brava.db`.
- **Qué salió de la conversación y acepté:**
  - La foto en su propio endpoint (`PUT` y `DELETE /products/{id}/image`), para no tocar el cuerpo JSON del producto ni las tallas de la HU-37.
  - El tipo comprobado por los primeros bytes y no por la extensión.
  - El nombre del archivo generado en el servidor.
  - El orden escribir el archivo nuevo → commit → borrar el viejo, para que nunca quede una foto rota.
  - Invalidar la caché de la tienda (HU-28) al subir o quitar la foto.
  - En el front, la foto como segundo argumento de `onSubmit`, para que `toProductBody` no cambie.
- **Qué corregí o descarté:**
  - La issue decía "borrar `brava.db`"; con Alembic va en una migración.
  - Dos tests comparaban el JSON entero del producto y hubo que añadirles `image_url`.
  - Al pasar `pytest` salieron dos `ResourceWarning` que venían de la T-01: el test de migraciones y `migrations/env.py` dejaban abierta la conexión de SQLite, y Python 3.14 avisa. Lo arreglé aparte, con `engine.dispose()` y `NullPool`.
  - La vista previa de la spec usaba `URL.createObjectURL` y la cambié por `FileReader`, que no necesita liberar nada.
  - Al actualizar el Sandbox no se me dijo que las fichas nuevas sustituían a las viejas y salieron repetidas.
  - Descarté volver a codificar la foto con Pillow para esta entrega (queda en la retrospectiva).
- **Cómo lo comprobé:** `pytest` (tipos válidos y falsos, límite de 2 MB, sustitución, borrado, fallo al guardar, 401 y 403), `alembic check`, `npm run build` y el flujo a mano: subir, cambiar y quitar la foto en el panel, verla en la tienda y probar un PDF renombrado a `.jpg`.

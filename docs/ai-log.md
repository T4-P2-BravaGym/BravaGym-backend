# AI log

Cómo hemos usado la IA en cada historia. Es un entregable de la asignatura (apartado 10 de `AGENTS.md`) y cubre los dos repos.

## HU-35 · Recuperación de contraseña — Beste Özaydın (implementado, pendiente de revisión humana)

- **Herramienta y modelo:** OpenAI Codex / GPT-6.
- **Trabajo y verificación:** Recuperación de contraseña con tokens hash de un solo uso, caducidad de 30 minutos, outbox privado y revocación de sesiones. Reutiliza FastAPI, SQLAlchemy, Alembic, pytest y Vitest. Validación registrada: 777 tests backend, 87 frontend, migraciones, lint y build.

## HU-33 · Refresh tokens y logout — Beste Özaydın (en curso)

- **Herramienta y modelo:** OpenAI Codex / GPT-6.
- **Trabajo y verificación:** Refresh tokens rotatorios, logout con revocación, cookie HttpOnly y protección CSRF. Integración frontend con access en memoria y renovación compartida. Tests frontend unificados con Vitest del equipo; comprobaciones de migraciones, permisos, concurrencia y sesiones.

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

- **Herramienta y modelo:** OpenAI Codex / GPT-6.
- **Trabajo y verificación:** Colección de Bruno con ejemplos HTTP y WebSocket, entorno local y documentación de ejecución. Se reutilizaron endpoints y herramientas del proyecto.

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
- **Qué corregí o descarté:** con prisa le pedí "dímelo entero" y generó los archivos completos en vez de guiarme paso a paso, que no es como trabajamos. Lo descarté y lo rehicimos archivo por archivo en el chat, escribiéndolo yo. Al empezar el frontend salió que el `RoutineEditor` que ya existía enviaba `exercises` en vez de `lines` y no mandaba `start_date`, y que la entrenadora no podía listar socias porque `GET /users` es solo de admin. En vez de abrir `GET /users` a entrenadoras, que habría expuesto emails y teléfonos, decidí un endpoint nuevo `GET /users/members` que solo devuelve id y nombre. Al adaptar el editor me quedaron a la vez la línea vieja exercises y la nueva lines (error de sintaxis), escribí start_Date con mayúscula (la API habría devuelto 422) y dejé un ! de más que hacía fallar siempre la validación del nombre; los vimos al revisar. Dejé fuera el historial y la edición de rutinas para no ampliar la historia: irá en una historia nueva.
- **Errores o alucinaciones:** nada inventado sobre el proyecto: antes de proponer leyó los modelos, el `AGENTS.md` y el código existente. Los errores fueron míos al copiar y los pillaron los tests: usé `RoutineUpdate` en vez de `RoutineCreate` en el `POST` (500 en todos los tests de crear), puse mal una llave en la ruta `/{routine_id}/exercises` (404) y escribí `firts_line` en un test. También tuve que ajustar el test de la HU-18, porque las líneas ahora devuelven su `id`.
- **Cómo lo comprobé:** `pytest` (permisos, 409, 404, 422 y la desactivación de la rutina anterior), ruff y el flujo en Swagger: crear ejercicios, crear una rutina y repetir día y posición para ver el 409. En el frontend: npm run build y el flujo a mano (crear una rutina como entrenadora, verla como socia en “Mi rutina”, crear otra y comprobar que la anterior queda inactiva, y el error de carga con el backend apagado) PR del frontend (frontend#77).

## HU-02 · Registro de socia — Viviana

- **Herramienta y modelo:** Claude (claude-opus-5-5), en modo mentora, en el chat del proyecto. El código lo escribí y lo commiteé yo. Cubre el backend (PR #139), la validación del nombre (PR #145) y la pantalla de registro del frontend.
- **Prompt de partida:** "Voy a hacer la siguiente tarea HU-02 · Registro de socia", con el texto de la issue #15 y sus sub-issues, y avisando de que `hash_password` y `verify_password` ya estaban hechas.
- **Qué salió de la conversación y acepté:** `UserCreate` sin `role` ni `is_active`, para que nadie se asigne un rol desde fuera; el validador de 72 bytes para bcrypt; `UserOut` leyendo el nombre del rol con `AliasPath`; `normalize_email` en un solo sitio, compartida con el login de la HU-03; el 409 también con el `IntegrityError` del `UNIQUE`; y los tests unitarios del hash y de integración del endpoint. En el front, la validación en un archivo aparte (`validation.js`) para no mezclarla con la pantalla. Pasar Ruff solo a mis archivos y proponer al equipo usarlo en todo el repo por separado. El detalle está en `specs/HU-02-register.md`.
- **Qué corregí o descarté:** quité el `max_length=80` que había puesto en la contraseña, porque el límite real ya lo pone el validador de 72 bytes. Me propuso añadir `max_length=72` y también lo descarté, por lo mismo. Al hacer la pantalla vi que el nombre aceptaba números; decidí arreglarlo primero en el backend, porque la seguridad tiene que estar en el servidor, en una rama y una PR aparte, y abrí una sub-issue nueva para que el Project reflejara ese trabajo.
- **Errores o alucinaciones:** dio por hecho que la rama de integración se llamaba `develop`; es `dev`, y lo corregí yo. Dijo que las expresiones regulares de Python no admiten `\p{L}`; es cierto para `re`, pero no para Pydantic v2, y lo aclaramos. Al revisar mi repo con su herramienta dejó un `.git/index.lock` que tuve que borrar yo desde la terminal. Mis errores fueron al resolver mi primer conflicto con la HU-03: el `token_type` del login quedó dentro de `UserCreate`. En el front, las claves de los errores (`firstNameError`) no coincidían con las que leía la pantalla (`first_name`) y validaba `last_name` dos veces. En la validación del nombre, una constante dentro de la clase rompía Pydantic y la saqué fuera.
- **Cómo lo comprobé:** `pytest` (71 tests al terminar el endpoint y 148 con la validación del nombre) y Ruff. En el navegador, registrar una socia nueva y repetir el email para ver el aviso del 409. El error "Role 'member' not found" que salió al probar era porque mi base de datos no tenía el seed; lo arreglé con `scripts/seed.py`.

## HU-06 · Listado de usuarios para administración — Viviana

- **Herramienta y modelo:** Claude (claude-opus-5-5), en modo mentora, en el chat del proyecto. El código lo escribí y lo commiteé yo. Cubre el backend (PR #153) y la tabla del panel de administración del frontend.
- **Prompt de partida:** "vale pues me asigno la HU-06 y luego seguimos con HU-17", con el texto de la issue #34.
- **Qué salió de la conversación y acepté:** hacer la HU-06 antes que la HU-17, porque `list_users` se iba a reutilizar después; `UserPage` sobre el `Page[T]` común que ya existía, así que cerré la HU-06.1 (#35) en vez de repetirla; escribir los tests antes del endpoint; un orden estable (apellido, nombre e `id`) para que la paginación no se mezcle; la búsqueda sin mayúsculas con `autoescape`; y límites de `size` hasta 100 y `q` hasta 60 caracteres. En el front, reutilizar `Table`, `Pagination`, `Field`, `Badge`, `Spinner`, `Alert` y `useDebouncedValue`, cancelar las peticiones viejas y volver a la página 1 al cambiar un filtro. Sin log, porque el endpoint solo lee. El detalle está en `specs/HU-06-users-list.md`.
- **Qué corregí o descarté:** abrir `GET /users` a las entrenadoras para la HU-17, porque verían emails y teléfonos de todas; eso se resolvió después con `GET /users/members`. Tampoco arreglé avisos de Ruff en archivos de otras compañeras, para no salirme de la historia ni crearles conflictos. Dejé fuera el cambio de rol desde la tabla, que es de la HU-05.
- **Errores o alucinaciones:** nada inventado sobre el proyecto: antes de proponer leyó los esquemas, el modelo y el router, y vio que la tabla del front estaba en Done en el Project pero no llamaba a la API. Su herramienta volvió a dejar un `.git/index.lock` que tuve que borrar yo. Mis errores: llamé al esquema `UsersPage` en un sitio y `UserPage` en otro (error de import), me faltaban imports en el router y Ruff marcó el espacio

## T-07 · Separar dependencias de test — Beste Özaydın

- **Herramienta y modelo:** OpenAI Codex / GPT-6.
- **Trabajo y verificación:** Separación de dependencias de ejecución y desarrollo, con documentación y comprobaciones de instalación y tests.

## HU-07 · Página de pricing — Beste Özaydın

- **Herramienta y modelo:** OpenAI Codex / GPT-6.
- **Trabajo y verificación:** Documentación de la página pública de planes, su especificación y comprobaciones de integración con la API.

## HU-05 · Gestión de roles — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Me explicaba cada paso en el chat y yo escribía o pegaba el código, ejecutaba los comandos y hacía los commits. Cubre el backend (PR #159) y el selector de rol del frontend (subtarea HU-05.5).
- **Prompt clave (en resumen):** "Guíame para implementar la HU-05 siguiendo las capas del proyecto: un endpoint para que administración cambie roles, con RN-18 y RN-19 comprobadas en el servicio y un test por cada criterio de aceptación." Con el backend ya mergeado: "Ahora llévalo a la tabla de usuarias: una admin tiene que poder pasar a una socia a entrenadora desde allí, sin saltarse esas reglas."
- **Qué me explicó o propuso:** en el backend, `PATCH /users/{id}/role` con `RoleUpdate`, las comprobaciones de RN-18 (403) y RN-19 (409) en `user_service.change_role`, crear un `TrainerProfile` vacío al pasar a entrenadora, el log con ids y sin emails, y los tests de `test_change_role.py`. En el frontend, `changeRole` en `services/users.js`, una función `roleChoices` con los roles que puede dar cada actora, el selector en la columna Rol y un modal de confirmación.
- **Qué acepté:** el endpoint, las reglas y los tests tal como están; en el front, el selector solo en filas que puedo gestionar, activas y que no son mías, la confirmación antes de cambiar y el aviso "X ahora es Y".
- **Qué descarté:** borrar el perfil de entrenadora al volver a socia; se conserva para no perder su bio. Tampoco cambié los permisos de tipos de clase que vimos de paso, porque son de la HU-11.
- **Errores o alucinaciones:** en los primeros tests salía un 500 en vez de 200, porque la base de datos de test no tenía los roles creados; lo arreglamos con una fixture `all_roles`. Al revisar el diff me dio números de línea equivocados; lo vi al comprobarlos yo.

## HU-08 · Gestión de planes — Beste Özaydın

- **Herramienta y modelo:** OpenAI Codex / GPT-6.
- **Trabajo y verificación:** Gestión de planes: documentación, especificación y comprobaciones de permisos, validación e integración.

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

## HU-32 · Cambiar mi contraseña — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código, ejecuté los comandos y hice los commits. Cubre el backend y el formulario de "Mi perfil".
- **Prompt clave:** "vamos a trabajar en la HU-32; primero la spec".
- **Qué me explicó o propuso:** en el backend, el esquema `PasswordChange` con las reglas del registro, comprobar la contraseña actual en el servicio con `verify_password` y devolver 400 en vez de 401, y reutilizar el limitador de la HU-34 contado por id de usuaria. En el front, un componente aparte `ChangePasswordForm` que comprueba las mismas reglas antes de llamar a la API.
- **Qué acepté:** todo lo anterior; añadir el límite de intentos aunque la issue no lo pedía; sacar la regla de los 72 bytes a una función común con el registro (DRY); y en el front, vaciar los campos al cambiarla para que las contraseñas no se queden en pantalla.
- **Qué descarté:** crear una clase nueva de error 400 en `exceptions.py`, porque la `AppError` base ya es 400; y enviar "repetir contraseña" a la API, porque lo comprueba el front.
- **Errores o alucinaciones:** nada inventado; cada paso se comprobó antes con los tests. Pero propuso cambiar `UserCreate` sin decir que era código de la HU-01 de otra compañera; lo pregunté yo y mantuvimos el cambio porque el comportamiento es el mismo. Al probar en Swagger cambié de verdad la contraseña de Lucía y la devolví con el mismo endpoint. También vi que "Mi perfil" solo existe para socias; queda fuera de alcance en la spec.
- **Ampliación (HU-33 ya hecha):** al cambiar la contraseña se revocan todos sus refresh tokens y el front la lleva al login. Me explicó que la cookie del refresh solo viaja a `/api/v1/auth`, así que este endpoint no sabe cuál es la sesión actual; por eso se cierran todas, también esta. Acepté esa opción en vez de cambiar la cookie de la HU-33, que es de otra compañera.

## Frontend #75 · Botón para mostrar u ocultar la contraseña — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código y los commits.Spec: `specs/T-75-password-reveal.md` en el repo del frontend.
- **Prompt clave:** "cuando escribo la contraseña solo veo puntos; normalmente hay un ojo al lado para verla".
- **Qué me explicó o propuso:** una prop `revealable` en `Field` en vez de un componente nuevo, dos iconos `eye` y `eyeOff` en `Icon`, y usarla en el login, el registro y "Cambiar contraseña".
- **Qué acepté:** hacerlo como tarea aparte de la HU-32, porque toca `Field`, que usan todos los formularios; que el envoltorio del botón solo exista en los campos de contraseña, para no cambiar el HTML de los demás; y un nombre fijo ("Mostrar contraseña") con el estado en `aria-pressed`.
- **Qué descarté:** primero propuso una casilla "Mostrar contraseñas" solo en mi formulario, para no tocar componentes comunes; preferí el ojo para toda la app y el equipo me dio la tarea. Tampoco añadí un ejemplo al Sandbox.
- **Errores o alucinaciones:** nada inventado. Al principio no se podía añadir el ojo a "Cambiar contraseña" porque la HU-32 aún no estaba en `dev`; cuando se mergeó, traje `dev` a la rama y lo añadí en la misma PR.

## T-03 · Auditoría de usuarias — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código, ejecuté los comandos y hice los commits.
- **Prompt clave:** "vamos a hacer primero la T-03".
- **Qué me explicó o propuso:** tres columnas en `users` con su migración de Alembic, y un ayudante `_mark_updated` que se llama justo antes del `commit` en los cinco cambios de una usuaria (perfil, rol, contraseña, edición y baja), para que un cambio rechazado no cuente.
- **Qué acepté:** todo lo anterior; que un `PATCH` vacío no cuente como cambio; y dejar fuera la baja aprobada de la HU-20, porque no está en la issue y quién la aprueba ya se guarda en la solicitud.
- **Qué descarté:** la subtarea opcional de enseñar "Última modificación" en el panel de admin, para esta entrega.
- **Errores o alucinaciones:** la migración generada por Alembic funcionaba en una base vacía (la de CI y la que probó al principio) pero fallaba en la mía con datos: SQLite no puede borrar `users` mientras otras tablas la apuntan. Lo vi al ejecutar `alembic upgrade head`; lo arreglamos apagando las foreign keys solo mientras se reconstruye la tabla y lo probamos con datos. Antes de generarla también me avisó de que mi base iba atrasada (sin la migración de la HU-30), porque si no la migración nueva habría incluido una columna que no era mía. Al copiar el servicio puse dos líneas con la sangría mal, y una hacía que el cambio de rol no se guardara.

## T-10 · Tests en el frontend — Damaris

- **Herramienta y modelo:** Claude (de pago), en modo mentora. Leyó el código del front con mi permiso, solo lectura. El código lo escribí y lo commiteé yo, y los tests los pasé yo en mi equipo (Claude no puede ejecutar `npm` en mi máquina).
- **Prompt de partida:** "empezamos con la T-10, test de frontend", con el contexto del proyecto cargado y la carpeta del front al día con `dev`.
- **Qué salió de la conversación y acepté:**
  - Vitest con Testing Library y jsdom, configurado en `vite.config.js`, con los tests junto al archivo que prueban.
  - Ejecutar los tests con la hora de Madrid (`TZ`), para que en local y en GitHub Actions salgan igual.
  - Empezar por las funciones puras (`format.js`, `CartContext`) y después los componentes (`ProductCard`, `CartSummary`, `OrderCard`, `ProductForm` y `Field`).
  - Probar `ProductForm` rellenando el formulario y mirando qué recibe `onSubmit`, en vez de exportar `toProductBody` solo para el test.
  - Buscar los elementos por su rol y su texto, como los encuentra la usuaria, y simular `useAuth` con `vi.mock` para no depender de la API.
- **Qué corregí o descarté:**
  - Al traer `dev` (HU-33), `package.json` quedó con dos scripts `test`: Git no lo marcó como conflicto, pero ganaba el último y mis tests de Vitest dejaban de ejecutarse. Lo arreglé con `test:unit && test:session` para que la CI pase los dos.
  - Descarté pasar yo los 15 tests de sesión de Beste (`node:test`) a Vitest en esta PR: el código es suyo y lo hará ella en su PR, que cerrará la T-10.
  - Dejé fuera el test end-to-end con Playwright (opcional en la T-10) por tiempo; queda en la retrospectiva.
- **Errores o bugs que encontraron los tests:**
  - `formatDate` seguía leyendo las fechas de la API como hora local (se escapó en la T-09): una clase tarde en UTC salía con el día anterior.
  - `OrderCard` pintaba cada línea del pedido dos veces, la segunda sin la talla (un resto de un merge).
  - Al pasar `npm run lint` salieron dos warnings de `react-hooks/exhaustive-deps` en `CartContext`: el carrito vacío creaba un array nuevo en cada render. Lo arreglé con `useMemo`.
- **Cómo lo comprobé:** `npm test` (52 tests de Vitest y 15 de sesión en verde), `npm run lint` sin avisos y `npm run build`. Antes de arreglar `formatDate` y `OrderCard` comprobé que sus tests fallaban de verdad.

## T-238 · Hora de fin de las clases — Viviana

- **Herramienta y modelo:** Claude (Claude Opus 5.5, de pago), en modo mentora. Leyó el código con mi permiso, solo lectura. El código lo escribí y lo commiteé yo.
- **Prompt clave:** "Actualmente las clases muestran a q hora empieza pero no cuando termina, arreglemos eso", con el enlace a la issue #238.
- **Qué me explicó o propuso:** que `duration_minutes` ya existía, así que la hora de fin se puede calcular con un `computed_field` de Pydantic en vez de añadir una columna. Un mixin compartido por `SessionOut` y `BookingSessionOut`.
- **Qué acepté:** el campo calculado sin migración, para tener una sola fuente de verdad, y el mixin para no repetir el cálculo.
- **Qué descarté:** guardar `ends_at` en la base de datos, porque podría desincronizarse con la duración.
- **Errores o alucinaciones:** en el test me propuso `.replace("Z", "+00:00")` antes de `fromisoformat`; Ruff lo marcó (FURB162) porque desde Python 3.11 no hace falta, y lo quité. Al arrancar el backend el login daba 500 porque mi `brava.db` no tenía la migración de la T-03; lo arreglé con `alembic upgrade head`, no era un fallo de esta tarea.
- **Cómo lo comprobé:** test de integración nuevo para `ends_at` en `GET /sessions`, `pytest` completo, Ruff en los archivos tocados y la respuesta de `/sessions` en Swagger.

## T-02 · Swagger enriquecido — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código, ejecuté los comandos y hice los commits.
- **Prompt clave:** "la T-02 no la entiendo bien" y, después, "si podemos, hagamos todos los routers nosotras".
- **Qué me explicó o propuso:** qué es OpenAPI, el esquema `ErrorOut`, los ayudantes `errors()` y `error()`, las descripciones de los tags, y escribir primero un test que lea el OpenAPI y liste lo que falta antes de tocar los routers.
- **Qué acepté:** el test primero (empezó con 187 errores sin `ErrorOut`, 13 endpoints sin 401 y 3 esquemas sin ejemplo, y fuimos bajando hasta cero); poner 401 y 403 en el `APIRouter` de `exercises` y `routines`; y dejar el 422 con el esquema de FastAPI.
- **Qué descarté:** aplicar un parche ya preparado con todos los cambios de los routers; preferí hacerlo yo con buscar y reemplazar (regex) en VS Code para entender cada cambio.
- **Errores o alucinaciones:** nada inventado. El primer reemplazo no encontraba nada porque la ruta de "files to include" no era la correcta en mi espacio de trabajo (`app/routers` en vez de `**/app/routers/**`); lo vimos con una captura.

## PageHeader común — Damaris

- **Herramienta y modelo:** Claude (Claude Opus 5.5, de pago), en modo mentora. Leyó el front y el back con mi permiso, solo lectura. El código lo escribí y lo commiteé yo, y los comandos los ejecuté yo en mi equipo.
- **Prompt clave:** "Vamos a trabajar en el PageHeader común (tarea técnica de frontend, rama refactor/page-header)", pidiendo que antes comprobara que `dev` estaba al día y revisara las siete páginas de la tarea y sus `.module.scss`.
- **Qué me explicó o propuso:** que mi `dev` del front iba un merge por detrás (la #82) y que no eran siete páginas con la cabecera copiada sino doce. Un componente `PageHeader` en `components/ui` con `title`, `eyebrow`, `lead` y `action`, con los mixins `eyebrow` y `display-text`, ficha y demo en el Sandbox y tres tests con Vitest.
- **Qué acepté:**
  - Cambiar las doce páginas, con las cinco de más en un commit aparte por si preferíamos ceñirnos a la tarea.
  - En Tienda y Horario, dejar los filtros fuera de `PageHeader` y conservar un envoltorio para no cambiar la separación con el texto.
  - Unificar el tamaño del título (AdminUsers y AdminCancellations usaban el de por defecto) y el ancho de la entradilla a 48rem.
- **Qué descarté:** meter en esta PR MemberHome, las páginas que solo tienen un `<h1>` y la cabecera del Sandbox. Tampoco convertí aquí en componente la navegación por semanas, que está repetida en cuatro páginas: va en otra tarea.
- **Errores o alucinaciones:**
  - En Tienda y Horario me dijo que cambiara `<header>` por `<div>` pero no repitió el cambio del cierre, y quedó un `</header>` suelto. Lo detectó `npm run lint`. Al arreglarlo borré también el envoltorio y la barra de la semana quedó más separada; lo vimos leyendo el archivo.
  - Claude no pudo pasar lint, tests ni build antes de darme el código: en su entorno no podía instalar las dependencias. Lo avisó.
  - Me dijo al revés qué socia tiene entrenamiento personal en el seed: es `lucia` (plan Premium), no `carmen`.
  - El IDE me metió el import como `"@/components/ui/PageHeader/index.js";` en diez páginas, con otro estilo que el resto; Claude lo vio al revisar. Lo dejé como en el resto de componentes.
- **Cómo lo comprobé:** `npm test` (70 tests), `npm run lint` y `npm run build`, y las doce páginas a mano en escritorio y en móvil, sin sesión y con una socia, una entrenadora y admin.

## Arreglos: reservas, navegación por semanas y errores 500 — Damaris

- **Herramienta y modelo:** Claude (Claude Opus 5.5, de pago), en modo mentora, en el mismo chat del PageHeader. Solo lectura; el código y los comandos, míos.
- **Prompt clave:** "sin login - en la sección entrenadoras sale No hemos podido cargar las entrenadoras … ¿es normal o es un error nuestro?", con el log de uvicorn, y después las capturas de "Mis reservas" y de la semana en el móvil.
- **Qué me explicó o propuso:**
  - El fallo de entrenadoras era mi `brava.db` sin la migración de auditoría de usuarias (`no such column: users.created_by_id`); se arregló con `alembic upgrade head`, no era un bug del código.
  - El mensaje de "no se ha podido conectar" salía porque FastAPI responde los errores inesperados fuera de `CORSMiddleware`: el 500 llegaba sin cabeceras CORS y el navegador lo bloqueaba. Propuso un middleware que devuelve el 500 genérico dentro de CORS.
  - "Mis reservas" mostraba "Clase · Fecha por confirmar" porque el front leía `session` y la API manda `class_session` desde la HU-12. Por eso tampoco se marcaban como reservadas las clases en el horario.
  - En el móvil, "Anterior" y "Siguiente" no cabían con la fecha: cambiarlos por flechas, que conservan el `aria-label`.
- **Qué acepté:** los tres arreglos, en dos PR (una del backend y otra del front), con un test nuevo en cada repo.
- **Qué descarté:** igualar el tamaño del badge "Reservada" y el botón "Cancelar": uno es un estado y el otro una acción, y el botón tiene que medir al menos 44 px de alto. También dejé para otra tarea el componente común de la navegación por semanas.
- **Errores o alucinaciones:** el middleware rompió `test_a_failed_save_leaves_no_file_behind`, que esperaba que la excepción saliera de la API. Lo vi con `pytest`. Cambiamos el test para comprobar el 500 y seguir comprobando que no queda ningún archivo; no se le bajó la exigencia. Claude tampoco pudo ejecutar `pytest` en su entorno antes de pasármelo.
- **Cómo lo comprobé:** `pytest` con cobertura del 96,84 %, test nuevo de que el 500 lleva la cabecera CORS, Ruff, `npm test` (72 tests), `npm run lint` y `npm run build`. A mano, con `lucia`: "Mis reservas" con nombre y hora, la clase reservada marcada en el horario y las flechas en una línea en el móvil.

## T-240 · Códigos de descuento por tipo de pago — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código, ejecuté los comandos y hice los commits.
- **Prompt clave:** "me han dado la #240, descuentos por categoría; la descripción está vacía".
- **Qué me explicó o propuso:** antes de programar, dos alcances posibles (por tipo de pago o por categoría de producto) y un mensaje para preguntar al equipo, que eligió el tipo de pago. Después, la columna `applies_to`, la comprobación en `get_valid_code` y un `concept` opcional en la validación.
- **Qué acepté:** todo lo anterior. Cuando el equipo dijo "clases y tienda", me recomendó seguir su decisión; yo preferí dejar también las cuotas, porque no cuesta nada más y sirve para ofertas de la cuota.
- **Qué descarté:** limitar por categoría de producto, que cambiaba el cálculo de RN-15 para un pedido con productos mezclados.
- **Errores o alucinaciones:** nada inventado. Me avisó de antemano de que Alembic no detecta las `CHECK` y de que la migración iba a tener el mismo problema de foreign keys que la T-03, así que la probamos con datos desde el principio. Un test de la HU-25 comparaba la respuesta entera y hubo que añadirle `applies_to`.

## WeekNav común — Damaris

- **Herramienta y modelo:** Claude (Claude Opus 5.5, de pago), en modo mentora, en el mismo chat del PageHeader. Leyó el front con mi permiso, solo lectura; el código y los comandos, míos.
- **Prompt clave:** "haremos la otra rama para hacer lo de las flechas un componente reutilizable", después de cambiar "Anterior" y "Siguiente" por flechas en las cuatro páginas.
- **Qué me explicó o propuso:** que la navegación por semanas estaba copiada en `Schedule`, `Bookings`, `PersonalTraining` y `TrainerSessions` (marcado, salto de 7 días y estilos iguales). Un componente `WeekNav` que recibe la fecha (`anchor`) y `onChange`, en vez del texto y dos funciones, para que calcule él la semana y el salto y las páginas solo guarden la fecha.
- **Qué acepté:** esa interfaz, ponerlo en `components/domain` porque usa la semana de Madrid de `utils/week`, la ficha y la demo en el Sandbox y dos tests con Vitest. También esperar a que se mergeara la PR de las flechas antes de sacar la rama, porque tocaba las mismas líneas.
- **Qué descarté:** la primera idea de pasarle `label`, `onPrevious` y `onNext`, porque cada página seguía calculando la semana por su cuenta.
- **Errores o alucinaciones:** nada inventado. Al pegar los cambios se me olvidaron dos de la lista en `PersonalTraining` (borrar `weekLabel` y cambiar el import de `utils/week`); lo detectó `npm run lint`. Claude no pudo pasar lint ni tests en su entorno antes de pasarme el código, y lo avisó.
- **Cómo lo comprobé:** `npm run lint`, `npm test` y `npm run build`. A mano, en el horario sin sesión, en Reservar clases y Entrenamiento personal con `lucia` y en Mis clases con `ana`: las flechas cambian de semana, se cargan sus clases y en el móvil cabe en una línea.


## Home y precios — Damaris

- **Herramienta y modelo:** Claude (Claude Opus 5.5, de pago), en modo mentora. Leyó el front y el back con mi permiso, solo lectura. El código lo escribí y lo commiteé yo, y los comandos los ejecuté yo en mi equipo.
- **Prompt clave:** "En la home, quiero destacar más lo de entrenamiento especializado de fuerza para mujeres, queda como perdido, es el feedback de la profe […] Precios está también muy equis, quiero que cuando pases encima de la card se muevan, y como glow o algo […] destacar más lo guay del premium", con capturas de las dos páginas.
- **Qué me explicó o propuso:**
  - Antes de empezar, comprobar que la landing de Viviana ya estaba mergeada y que ninguna rama abierta tocaba esos archivos.
  - En la home, una línea con la especialidad justo debajo del título, animaciones de entrada, una banda de ejercicios y las cards de "Por qué Brava" que aparecen al hacer scroll con un hook `useInView` (`IntersectionObserver`, sin librerías).
  - En precios, que `PricingCard` ya aceptaba `featured` y `features` pero la página no los usaba. Hover con elevación, glow y una luz que sigue al puntero, el plan con entrenamiento personal destacado, una sección de lo que incluyen todos los planes, un bloque sobre el entrenamiento personal y preguntas frecuentes.
  - Al leer el código encontró tres cosas que no había pedido:
    - el hook `useSubscribe` de la HU-09 nunca se conectó, así que una socia no podía contratar un plan desde el front;
    - la próxima clase decía "con Entrenadora" porque la API no manda el nombre;
    - el badge decía "La más elegida", algo que no podemos demostrar.
- **Qué acepté:**
  - Todo lo anterior en una sola rama y dos commits (home y precios).
  - Conectar `useSubscribe` en la misma PR.
  - Que los puntos de cada card salgan de los datos del plan (`includes_personal_training`) y no de textos escritos a mano por nombre de plan, porque administración puede editar los planes.
  - Que todas las animaciones se paren con `prefers-reduced-motion`.
  - Hacer los glows con `color-mix` sobre los tokens para no meter colores sueltos.
- **Qué descarté:**
  - Una tabla comparativa de planes: el plan no tiene un campo de clases por semana, así que habría que inventar las filas.
  - Arreglar "Entrenadora" en el horario y en las reservas en esta PR: es un cambio del backend y se lo paso a Viviana.
- **Errores o alucinaciones:**
  - Nada inventado.
  - Al revisar salió que el límite de "Hasta 2 clases a la semana" del plan Básico solo está en la descripción y el backend no lo comprueba. Va a la retro.
  - Claude no pudo pasar lint, tests ni build en su entorno antes de darme el código, y lo avisó.
- **Cómo lo comprobé:**
  - `npm run lint`, `npm test` (3 tests nuevos de `PricingCard`) y `npm run build`.
  - A mano:
    - la home sin sesión, en escritorio y en móvil;
    - Precios sin sesión ("Elegir" lleva a registro);
    - con `carmen` ("Tu plan" en Básico, y el 409 de la API al elegir otro);
    - con una socia nueva, que contrata Premium y ve la cuota en Mis pagos;
    - con "Reducir movimiento" activado.

## `CurrentAdmin` compartido en `deps.py` — Damaris

- **Herramienta y modelo:** Claude (Claude Opus 5.5, de pago), en modo mentora. Leyó el backend con mi permiso, solo lectura. El código lo escribí y lo commiteé yo, y los comandos los ejecuté yo en mi equipo.
- **Prompt clave:** "Lo que podemos hacer, si vale la pena y no tengo que esperar algún merge de mis PRs que están pendientes: compartir la dependencia CurrentAdmin en deps.py […]".
- **Qué me explicó o propuso:**
  - Que la tarea ya no eran tres routers sino seis: `users`, `payments`, `cancellation_requests` y `discount_codes` definían su propio `CurrentAdmin`, `products` lo llamaba `ShopAdmin` y `plans` repetía `require_roles(...)` en cuatro endpoints.
  - Que `TrainerAdminOrSuperadmin` de `sessions.py` se quedaba como estaba, porque incluye a la entrenadora.
  - Que no chocaba con mis PR abiertas, pero sí con la rama de Stripe en `payments.py`.
  - Definirlo en `deps.py` junto a `CurrentMember` y mencionarlo en `AGENTS.md`.
- **Qué acepté:** el refactor en los seis routers, también `payments.py`, avisando del conflicto en la PR. Comprobarlo sin tocar ningún test: si los 401 y 403 de siempre pasan, el comportamiento no ha cambiado.
- **Qué descarté:** dejar `payments.py` fuera hasta que se mergee la HU-29. Preferí dejarlo cerrado hoy y que el conflicto se resuelva al mergear.
- **Errores o alucinaciones:**
  - Al darme los imports nuevos de `payments.py` y `cancellation_requests.py` los puso fuera de orden y Ruff marcó I001; se arregló con `ruff check --fix`.
  - Yo hice sin querer en esta rama los commits de la otra tarea (los pagos). Lo vimos con `git log` y lo separamos con `cherry-pick`, `reset` y `commit --amend` antes de hacer push.
- **Cómo lo comprobé:** `ruff check` y `ruff format --check`, un `grep` de `ShopAdmin` y de `CurrentAdmin = ` (solo queda el de `deps.py`), `pytest` con 767 tests sin cambiar ninguno, y el candado de los endpoints de admin en `/docs`.

## Pagos de las reservas canceladas (HU-11, HU-13, HU-20) — Damaris

- **Herramienta y modelo:** Claude (Claude Opus 5.5, de pago), en modo mentora, en el mismo chat. Solo lectura; el código y los comandos, míos.
- **Prompt clave:** "Refactor de HU-13/HU-20 y HU-11/RN-10 (que se supone que es de Mariana, pero no se ha conectado […])" y después el texto de la issue.
- **Qué me explicó o propuso:**
  - Qué pasaba en cada camino: al cancelar la socia (HU-13) o aprobar una baja (HU-20), el pago de la clase extra no cambiaba. Al cancelar la entrenadora una clase (HU-11), los pagos `pending` pasaban a `refunded` aunque no se hubiera cobrado nada, y no se avisaba por websocket.
  - Un helper común, `settle_booking_payment`, usado por `_cancel_one_booking_applying_rn06` y `cancel_session`.
- **Qué acepté:**
  - El helper y la regla de la issue: `pending` → `cancelled` y `paid` → `refunded` en los tres casos. Es seguro porque la socia solo puede cancelar con 60 minutos o más (RN-05).
  - Actualizar RN-10, RN-13, RN-16 y `api.md`.
  - Cambiar los dos tests que esperaban `REFUNDED` para un pago pendiente, porque comprobaban el comportamiento que corregíamos, y añadir cuatro: cancelar con pago pendiente y con pago pagado, baja aprobada y volver a reservar.
- **Qué descarté:** su primera versión, que dejaba `paid` el pago cuando cancela la socia siguiendo la RN-16 tal como estaba escrita ("solo administración puede marcarlo `refunded`"). Al pasarle la issue vimos que el equipo ya había propuesto reembolsar también ahí y cambiar la RN-16, así que lo ajustamos en un segundo commit y quitamos el parámetro `refund_paid`, que ya no hacía falta.
- **Errores o alucinaciones:**
  - En tres tests marcaba un pago como `PAID` sin `paid_at` y la `CHECK` `ck_payments_paid_at` los rechazaba al preparar los datos. Se arregló poniendo la fecha; el fallo estaba en el test, no en el código.
  - No había visto la issue al proponer la primera versión, ni la línea de `api.md` que había que cambiar.
  - Al pegar, sustituí `_ensure_extra_class_payment` por la función nueva en vez de añadirla debajo (Ruff: F821). También se me borraron docstrings y quedaron dos `- ` sueltos en `business-rules.md`. Lo vimos revisando el diff antes del push.
- **Cómo lo comprobé:** `ruff check` y `ruff format --check`, `pytest` con 770 tests (cobertura 96,76 %) y un último repaso del diff de las dos ramas para comprobar que cada una solo tenía sus archivos.

## D-07 · README backend (#284) — Beste

- **Herramienta y modelo:** OpenAI Codex / GPT-6.
- **Trabajo y verificación:** README backend: instalación, configuración, Alembic, seed, uso de API y enlaces de entrega. Validación: 737 tests existentes, migraciones y seed en SQLite temporal, endpoints de documentación y login; lint y formato correctos.
- **Actualización tras revisión del equipo (19 de octubre):** README backend breve en inglés desde dev: descripción, versiones declaradas, instalación, uso de Swagger, demo, estructura, controles y autoras. Guía de Bruno conservada en docs/api-testing.md. Verificación actual: 794 tests, 97,07 % de cobertura, lint/formato y enlaces correctos; instalación limpia en Python 3.12, migraciones, seed, health, documentación y login/perfil de demo comprobados.
- **Prompt clave:** "ok lets do it fix my work", después de acordar dos READMEs concisos en inglés.


## D-07 · README frontend (#283) — Beste

- **Herramienta y modelo:** OpenAI Codex / GPT-6.
- **Trabajo y verificación:** README frontend del proyecto completo: instalación, configuración pública, áreas por rol, demo, build, preview y enlaces de entrega. Validación: 74 tests existentes, lint y build correctos; rutas y enlaces locales contrastados.
- **Actualización tras revisión del equipo (19 de octubre):** README frontend breve en inglés desde dev: descripción, versiones del lockfile, instalación y conexión a la API, demo, estructura, controles y autoras. Verificación actual: 92 tests, lint y build correctos; enlaces y versiones del lockfile contrastados.
- **Prompt clave:** "ok lets do it fix my work", después de acordar dos READMEs concisos en inglés.


## HU-29 · Stripe frontend and smoke — Mariana

- **Herramienta y modelo:** Codex (GPT-6), implementación y verificación autorizadas por la usuaria; modalidad de suscripción no comprobada.
- **Prompt clave:** «Brava Gym HU-29 Stripe. Termina FE + smoke. NO merges.» «CRÍTICO: STRIPE_SUCCESS/CANCEL_URL → http://localhost:5173/mi-area/pagos?stripe=… (no /member/payments).»
- **Qué me explicó o propuso:** añadió checkout en Mis pagos conservando el pago simulado, retorno que consulta el estado de la API y manejo de 503. Preparó pruebas con una base aislada y Stripe test.
- **Qué acepté:** alcance autorizado en el prompt: rama frontend, PR draft, smoke y corrección de URLs de retorno; no equivale a aprobación humana del código.
- **Qué descarté:** merges y Stripe Refunds API, excluidos expresamente por la usuaria.
- **Errores o alucinaciones:** la suite completa detectó errores OpenAPI sin `ErrorOut` en la implementación existente de HU-29; se corrigieron con el helper común. Tras la corrección: 754 tests pasan y cobertura 96,51 %. El checkout real se creó (200) y continuó pending; firma inválida (400). La prueba de tarjeta alojada se documenta en la PR frontend, separada de los tests con mocks.

## Frontend #93 · Menú lateral que se puede contraer — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código y los commits. Spec: `specs/T-93-sidebar-collapse.md` en el repo del frontend.
- **Prompt clave:** "tengo la #239 (colapso del menú lateral opcional)"; la issue no tenía descripción.
- **Qué me explicó o propuso:** contraer el menú a sus iconos solo en ordenador, el nombre como texto oculto y `title`, un botón con `aria-pressed` y guardar la elección en `localStorage`.
- **Qué acepté:** todo lo anterior. No tenía opinión sobre el diseño y me explicó que el diseño no incluía una versión contraída, así que seguimos el patrón habitual y lo revisé en el navegador.
- **Qué descarté:** cambiar el icono repetido (Entrenamiento personal y Mi perfil usan el mismo); lo dejé anotado en la PR.
- **Errores o alucinaciones:** VS Code marcaba como error `@media (min-width: $breakpoint-md + 1px)`, que Sass compila bien; lo escribimos como `#{...}` y comprobamos que el CSS final era el mismo. Al probarlo vi que "Administración" pisaba el botón "Salir" (venía de antes) y lo arreglé en la misma PR.

## T-291 · Foto de las entrenadoras — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código, ejecuté los comandos y hice los commits.
- **Prompt clave:** "hace falta la foto de las entrenadoras" (no había issue; la abrimos juntas).
- **Qué me explicó o propuso:** reutilizar la subida de fotos de la HU-30 y dos caminos: sacarla a un módulo común o copiarla. También comprobó si había ramas abiertas que tocaran esos archivos antes de decidir.
- **Qué acepté:** el módulo común `image_files.py` (DRY), la columna `photo_path`, `PUT` y `DELETE /trainers/me/photo`, y tests que miran los archivos en disco.
- **Qué descarté:** copiar el código para no tocar el archivo de otra compañera; como su única rama abierta se mezclaba sin conflictos (lo comprobamos), preferí no duplicar la validación de fotos.
- **Errores o alucinaciones:** nada inventado. Al crear el archivo nuevo lo llamé `images_files.py` por error y lo renombré. Un test de la HU-15 comparaba la tarjeta entera y hubo que añadirle `photo_url`.

## Frontend #101 · Mi perfil y contraseña para entrenadoras y administración — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código y los commits. Spec: `specs/T-101-account-all-roles.md` en el repo del frontend.
- **Prompt clave:** "Mi perfil para todos los roles, ¿dónde lo hacemos?".
- **Qué me explicó o propuso:** que el menú y la protección dependen de la ruta de cada área, sacar "Mis datos" y "Cambiar contraseña" a un bloque común (`pages/shared/Account`) y una página "Mi cuenta" para administración.
- **Qué acepté:** el bloque común para los tres roles y la página de administración. Para las entrenadoras propuso una entrada de menú nueva; preferí no añadirla y poner el bloque en la misma página que su perfil público, bajo el título "Mi cuenta", y llamar al menú "Mi perfil y cuenta".
- **Qué descarté:** renombrar la página a "Mi perfil" sin más (se perdía lo de "público", que hicimos en la HU-15) y un nombre de menú más largo que no cabía en una línea.
- **Errores o alucinaciones:** nada inventado. Al copiar, tres archivos quedaron fuera de su carpeta, el `index.js` acabó pegado dentro de otro archivo y un import salió repetido (el build falló); lo vimos en la revisión y lo corregí.

## HU-35 · Actualización con dev — Beste

- **Herramienta y modelo:** OpenAI Codex / GPT-6.
- **Prompt clave:** "okay can you do it" (actualizar la rama backend con dev).
- **Trabajo:** integrar dev en feature/hu-35-recovery, conservar las entradas de ambas ramas en esta bitácora y añadir una migración de unión para las migraciones paralelas de recuperación y foto de entrenadoras.
- **Verificación:** 794 tests, cobertura 97,07 %; Ruff lint/formato correctos; pip-audit sin vulnerabilidades conocidas; upgrade/check, downgrade explícito al ancestro común y nuevo upgrade/check en SQLite temporal.


## T-12 · Historial de rutinas de una socia — Viviana (backend hecho, frontend en curso)

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Leyó el código con mi permiso; yo escribí el código, ejecuté los tests y hice los commits.
- **Prompt clave:** "una entrenadora hace las rutinas de una socia, pero jamás las puede ver como historial; dime cómo podemos desarrollar esta solución juntos".
- **Qué me explicó o propuso:** que el backend ya tenía casi todo (`GET /routines?member_id=` y la baja lógica que guarda el historial) y que faltaba sobre todo la pantalla; ordenar por `start_date` con el `id` como desempate; `selectinload` para evitar el N+1 del listado; tests primero, con uno en rojo antes de tocar el servicio.
- **Qué acepté:** todo lo anterior, y sacar `RoutineDays` de "Mi rutina" para reutilizarlo en el historial.
- **Qué descarté:** dejar para otras tareas que la socia vea su historial, duplicar rutinas como plantilla y que cada entrenadora vea solo sus rutinas. Tampoco hice un test que cuente consultas para el N+1: sería frágil.
- **Errores o alucinaciones:** al principio propuso llamarla HU-30, que ya existía (foto de producto); lo vio al revisar el backlog y la dejamos como T-12.

# AI log

Cómo hemos usado la IA en cada historia. Es un entregable de la asignatura (apartado 10 de `AGENTS.md`) y cubre los dos repos.

## HU-33 · Refresh tokens y logout — Beste Özaydın (en curso)

- **Herramienta y modelo:** OpenAI Codex, GPT-6. Ayuda paso a paso, generación de archivos y comandos autorizados. La modalidad de pago de la cuenta no está confirmada.
- **Prompt clave:** "ok they didnt answer me about the question so lets go please", después de revisar #182 y redactar la spec. También pedí "can you also tell me what each command does after you run".
- **Qué me explicó o propuso:** access token en memoria y refresh en cookie HttpOnly; confirmar el despliegue con el equipo antes de cerrar ese contrato. Mientras llega la respuesta, preparar las tablas y la lógica de sesiones y después conectar los endpoints locales con cookies HttpOnly, validación de origen y cabecera X-Brava-CSRF. Después se conectó el frontend; la configuración de despliegue sigue pendiente.
- **Qué acepté:** empezar por la spec, escribir las pruebas antes de los modelos y mantener ambos modelos en un archivo. Codex escribió el código, la migración y las pruebas con mi autorización y explicó cada paso; no se atribuye como implementación manual sin ayuda de IA.
- **Qué descarté:** asumir el dominio de producción, guardar tokens completos en la base de datos, modificar archivos ajenos por errores de formato o publicar la implementación sin revisión. Los JWT incluyen jti/type y la autenticación rechaza identificadores revocados. Se conectaron los endpoints locales y el frontend sin instalar nuevas dependencias de test.
- **Errores o alucinaciones:** Ruff detectó orden incorrecto de imports en la nueva prueba y se corrigió. La primera suite completa detectó que el inventario antiguo esperaba 19 tablas; se añadieron las dos tablas exigidas por esta historia manteniendo la comparación exacta, sin eliminar ni relajar el test. La revisión independiente detectó una carrera entre dos logout al insertar la misma revocación; se reprodujo con dos conexiones reales (fallo de clave única), se sustituyó la comprobación previa por una inserción atómica que ignora el duplicado y el test pasó.
- **Cómo lo comprobé:** la primera prueba falló porque no existía RefreshToken y después pasaron las siete pruebas nuevas y la comprobación existente de migraciones. En una base temporal se verificó upgrade, downgrade y nuevo upgrade conservando una usuaria ficticia, y alembic check no detectó diferencias. La base habitual no se modificó. Tras actualizar el inventario de tablas, pasaron las 670 pruebas de la suite completa con cobertura del 96,94 %; lint y formato pasaron en los archivos de esta etapa. En la segunda etapa se probaron los claims jti/type, expiración del refresh, rechazo de tipos cruzados, rotación de un solo uso, carrera con dos conexiones SQLite, rollback ante fallo al reemplazar y revocación real del acceso. Tras corregir la carrera de logout pasaron 692 pruebas con cobertura del 96,96 %. En la tercera etapa, las pruebas nuevas fallaron porque login no entregaba cookie y refresh aún no existía. Después se conectaron login, refresh y logout con cookies HttpOnly, validación de origen, cabecera CSRF obligatoria en refresh/logout y limpieza de revocaciones caducadas. Se verificaron también logout con access caducado, rechazo de tokens de otra usuaria y cookie Secure fuera de local. La suite completa pasó 711 pruebas con cobertura del 96,93 %. En la cuarta etapa Codex modificó api.js, auth.js, AuthContext, el logout del layout y el aviso de login, y creó session.js y una prueba con Node/Vite existentes. Se implementaron renovación compartida, reintento único (también descargas), inicialización con espera, eliminación de localStorage y coordinación de logout. La revisión detectó que un 401 tardío podía repetir una operación bajo otro login: se reprodujo y corrigió con una versión de sesión. Otra prueba detectó que reintentar logout tras un fallo perdía el access anterior; se conservó solo en memoria para ese reintento. No se da por confirmado un logout rechazado. Pasaron las 15 pruebas frontend, npm run build y npm run lint (sin errores; dos avisos existentes en CartContext). Se añadió npm test al workflow de CI. La revisión posterior no encontró otros problemas importantes. El flujo de servicios contra una API real y SQLite temporal comprobó login, perfil, renovación compartida, restauración y logout con rechazo posterior del access. La automatización visual de Chrome se interrumpió por cambios de ventana. Codex proporcionó por error /login; se corrigió a /entrar tras revisar paths.js. Beste confirmó después la comprobación manual básica: login, recarga manteniendo sesión, logout y nueva recarga sin sesión. No se atribuye esa prueba manual a la automatización. El 16 de octubre se repitieron las comprobaciones finales: 711 tests backend (96,93 %), 15 tests frontend, build, migración sobre SQLite temporal y auditoría de dependencias sin vulnerabilidades conocidas. La primera PR quedó bloqueada por Ruff en archivos existentes de imágenes de producto. Tras la petición de Beste de completar los requisitos y hacer que funcionase, se corrigió únicamente el orden de imports, la indentación y los saltos finales de cinco archivos (seis líneas), sin cambiar lógica ni debilitar tests. Ruff lint y formato pasan ahora en todo app/tests. Se documentó también el 403 por origen del login en Swagger. ESLint no tiene errores y conserva dos avisos existentes de CartContext. Se completaron las comprobaciones visuales con el navegador: foco visible y navegación por teclado en login, mostrar contraseña, menú móvil y logout; aviso accesible con role=alert y botón de reintento; layout a 320 y 375 px sin desbordamiento horizontal. Se detuvo solo la API de demostración para provocar el fallo, se restauró y se verificó el reintento con Enter y la recarga sin sesión. Beste autorizó commits y push; ella abre las PR. La historia sigue en curso hasta revisión humana y merge; el sitio de despliegue aún debe confirmarse con el equipo.

- **Cierre de preparación local (16 de octubre):** Beste indicó "they dont say anything go ahead". Se adopta el contrato existente de refresh exclusivamente en cookie HttpOnly y despliegue HTTPS en el mismo sitio, sin atribuir aprobación al equipo ni inventar dominios. La spec y ambos README explicitan ese requisito. Se verificaron de nuevo 711 tests backend (96,93 %), 15 frontend, build, lint/formato, migración reversible en SQLite temporal y auditoría sin vulnerabilidades conocidas. Tras subir las correcciones existentes, GitHub Actions pasó en 8904479. Se repitieron foco visible, control de contraseña por teclado y layout a 320/375 px. No se abre otra PR ni se hace merge; revisión humana y verificación en las URLs reales siguen siendo pasos de integración y despliegue.

- **Refactor de tests a Vitest (16 de octubre, después de la PR frontend #81):** Damaris pidió esperar a integrar su configuración de Vitest y luego unificar los tests. Beste autorizó continuar al compartir «@Beste ya puedes hacer pull y hacer el refactor» y pidió la conversación en inglés. Codex reutilizó Vitest 5/jsdom y las dependencias ya fijadas por el equipo; trasladó los quince escenarios de `tests/auth-session.test.js` a `src/services/session.test.js`, sustituyó el runner y los asserts de Node por Vitest, eliminó el servidor Vite auxiliar y restauró fetch/configuración entre casos. `npm test` ejecuta únicamente `vitest run`; watch y CI usan la misma suite. Se actualizaron README y la spec frontend `specs/T-10-session-vitest.md`. No se modifica lógica de producción ni se añaden dependencias. La línea base pasó 52 tests Vitest y 15 Node; la suite unificada pasa 67 tests, lint y build. Se compararon los quince nombres y las 41 aserciones originales. Dos mutaciones temporales confirmaron que se detectan una renovación sin compartir y un logout que revoca el access anterior en vez del renovado; se restauró el archivo y pasaron los 67 tests. El primer intento de instalación falló por red restringida y se repitió con acceso autorizado. Se reconoce la decisión inicial de usar Node como origen de la duplicación de herramientas; el refactor sigue la configuración del equipo.

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
- **Qué corregí o descarté:** con prisa le pedí "dímelo entero" y generó los archivos completos en vez de guiarme paso a paso, que no es como trabajamos. Lo descarté y lo rehicimos archivo por archivo en el chat, escribiéndolo yo. Al empezar el frontend salió que el `RoutineEditor` que ya existía enviaba `exercises` en vez de `lines` y no mandaba `start_date`, y que la entrenadora no podía listar socias porque `GET /users` es solo de admin. En vez de abrir `GET /users` a entrenadoras, que habría expuesto emails y teléfonos, decidí un endpoint nuevo `GET /users/members` que solo devuelve id y nombre. Al adaptar el editor me quedaron a la vez la línea vieja exercises y la nueva lines (error de sintaxis), escribí start_Date con mayúscula (la API habría devuelto 422) y dejé un ! de más que hacía fallar siempre la validación del nombre; los vimos al revisar. Dejé fuera el historial y la edición de rutinas para no ampliar la historia: irá en una historia nueva.
- **Errores o alucinaciones:** nada inventado sobre el proyecto: antes de proponer leyó los modelos, el `AGENTS.md` y el código existente. Los errores fueron míos al copiar y los pillaron los tests: usé `RoutineUpdate` en vez de `RoutineCreate` en el `POST` (500 en todos los tests de crear), puse mal una llave en la ruta `/{routine_id}/exercises` (404) y escribí `firts_line` en un test. También tuve que ajustar el test de la HU-18, porque las líneas ahora devuelven su `id`.
- **Cómo lo comprobé:** `pytest` (permisos, 409, 404, 422 y la desactivación de la rutina anterior), ruff y el flujo en Swagger: crear ejercicios, crear una rutina y repetir día y posición para ver el 409. En el frontend: npm run build y el flujo a mano (crear una rutina como entrenadora, verla como socia en “Mi rutina”, crear otra y comprobar que la anterior queda inactiva, y el error de carga con el backend apagado) PR del frontend (frontend#77).

## T-07 · Separar dependencias de test — Beste Özaydın

- **Herramienta y modelo:** OpenAI Codex, GPT-6, con explicaciones paso a paso y ejecución autorizada. La modalidad de pago de la cuenta no está confirmada.
- **Prompt clave:** "ok do it", tras leer la issue #192 y explicar que se escribiría la spec, se quitarían las dos dependencias de ejecución, se comprobaría instalación y tests y se abriría una PR.
- **Qué me explicó o propuso:** la diferencia entre dependencias de ejecución y de desarrollo; retirar las declaraciones de `pytest` y `freezegun` de `requirements.txt`, conservándolas en `requirements-dev.txt`.
- **Qué acepté:** el cambio mínimo descrito en la issue y la spec previa. Autoricé a Codex a editar los archivos y ejecutar las comprobaciones; el agente escribió esta documentación y el cambio de configuración.
- **Qué descarté:** ampliar la tarea a Docker, cambiar versiones o modificar pruebas.
- **Errores o alucinaciones:** no se detectaron errores en la propuesta de separación; los resultados de instalación y pruebas se registran en la PR.
- **Cómo lo comprobé:** instalación desde `requirements-dev.txt`, suite existente y comprobación del diff y del salto de línea final. Los resultados concretos se adjuntan a la PR antes de solicitar revisión humana.

## HU-07 · Página de pricing — Beste Özaydın

- **Herramienta y modelo:** Codex / ChatGPT. Recibí ayuda de IA siguiendo cada paso. Esta documentación retrospectiva se preparó con OpenAI Codex, GPT-6; el modelo exacto y la modalidad de pago de las conversaciones originales no están confirmados.
- **Prompt clave:** no se conserva aquí el prompt literal de la implementación original. En la revisión documental pedí "please do everything one by one and tell me whet you do" y confirmé continuar con la spec y la bitácora de HU-07. Se distingue esta revisión del trabajo original para no reconstruir prompts como si fueran citas.
- **Qué me explicó o propuso:** en esta revisión, contrastar los criterios de #38 con las PR backend #141 y frontend #41 y documentar el catálogo público, los planes activos ordenados por precio, el precio en euros y los estados de la pantalla. La ayuda se explicó paso a paso.
- **Qué acepté:** documentar la implementación existente en una spec compartida, reutilizar las pruebas existentes como evidencia y registrar el alcance de la ayuda. Autoricé a Codex a escribir estos documentos y ejecutar las comprobaciones; no se presentan como trabajo escrito sin ayuda de IA.
- **Qué descarté:** rehacer una funcionalidad ya terminada o añadir comportamiento nuevo dentro de una tarea documental. No se conserva una lista verificable de propuestas descartadas durante la implementación original.
- **Errores o alucinaciones:** en esta revisión no se reconstruyen decisiones, errores ni conversaciones históricas que no se pueden verificar. La ausencia de spec y entrada de bitácora se detectó al revisar los archivos de `dev`, aunque #38 ya estaba cerrado.
- **Cómo lo comprobé:** se leyeron los criterios de #38, los archivos incluidos en backend #141 y frontend #41 y el código de planes y de `Pricing`. Las comprobaciones actuales y sus resultados se registran en la PR documental; no se atribuyen a pruebas manuales históricas que esta sesión no haya observado.

## HU-05 · Gestión de roles — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Me explicaba cada paso en el chat y yo escribía o pegaba el código, ejecutaba los comandos y hacía los commits. Cubre el backend (PR #159) y el selector de rol del frontend (subtarea HU-05.5).
- **Prompt clave (en resumen):** "Guíame para implementar la HU-05 siguiendo las capas del proyecto: un endpoint para que administración cambie roles, con RN-18 y RN-19 comprobadas en el servicio y un test por cada criterio de aceptación." Con el backend ya mergeado: "Ahora llévalo a la tabla de usuarias: una admin tiene que poder pasar a una socia a entrenadora desde allí, sin saltarse esas reglas."
- **Qué me explicó o propuso:** en el backend, `PATCH /users/{id}/role` con `RoleUpdate`, las comprobaciones de RN-18 (403) y RN-19 (409) en `user_service.change_role`, crear un `TrainerProfile` vacío al pasar a entrenadora, el log con ids y sin emails, y los tests de `test_change_role.py`. En el frontend, `changeRole` en `services/users.js`, una función `roleChoices` con los roles que puede dar cada actora, el selector en la columna Rol y un modal de confirmación.
- **Qué acepté:** el endpoint, las reglas y los tests tal como están; en el front, el selector solo en filas que puedo gestionar, activas y que no son mías, la confirmación antes de cambiar y el aviso "X ahora es Y".
- **Qué descarté:** borrar el perfil de entrenadora al volver a socia; se conserva para no perder su bio. Tampoco cambié los permisos de tipos de clase que vimos de paso, porque son de la HU-11.
- **Errores o alucinaciones:** en los primeros tests salía un 500 en vez de 200, porque la base de datos de test no tenía los roles creados; lo arreglamos con una fixture `all_roles`. Al revisar el diff me dio números de línea equivocados; lo vi al comprobarlos yo.

## HU-08 · Gestión de planes — Beste Özaydın

- **Herramienta y modelo:** Codex / ChatGPT, confirmado por Beste para la implementación original; esta revisión documental se realizó con OpenAI Codex, GPT-6. Recibí ayuda de IA siguiendo cada paso. El modelo exacto de las conversaciones originales y la modalidad de pago no están confirmados; no se atribuyen esos datos sin evidencia.
- **Prompt clave:** para completar y explicar la documentación: "please do everything one by one and tell me whet you do". Para describir el acompañamiento: "say that I got help from ai following each step". Son los prompts de la revisión del 14 de octubre, no una reconstrucción del prompt original de implementación.
- **Qué me explicó o propuso:** cómo distinguir la historia #42, las subtareas #43 y #44 y la PR #178; la diferencia entre `Refs` y `Closes`; y los requisitos de spec, bitácora, Swagger, tests y revisión. La ayuda fue paso a paso, con explicaciones y comprobaciones de los archivos y de GitHub.
- **Qué acepté:** documentar la historia completa en una spec del backend, registrar el alcance real de la ayuda de IA y comprobar los endpoints, permisos y borrado lógico antes de cerrar la historia. En esta revisión autoricé expresamente que Codex escribiera la documentación y ejecutara los comandos; estos archivos no se presentan como escritos manualmente sin ayuda.
- **Qué descarté:** cerrar #42 inmediatamente tras cerrar las subtareas, porque faltaban la spec y esta entrada. No se dispone de un registro completo de decisiones descartadas durante la implementación original.
- **Errores o alucinaciones:** la IA interpretó inicialmente los issues abiertos como posible trabajo sin implementar; al consultar GitHub comprobó que las PR backend #178 y frontend #63 ya estaban aprobadas y mergeadas. También indicó que faltaban ejemplos Swagger tras revisar solo el router; al leer `app/schemas/plan.py` comprobó que ya existían y evitó un cambio innecesario.
- **Cómo lo comprobé:** las PR #178 y frontend #63 contienen la implementación; las subtareas #43, #44 y frontend #7 están cerradas. Pasaron las 45 pruebas de planes en el checkout previo y, en la rama documental basada en `dev`, las 614 pruebas completas con cobertura del 96,78 %. También pasaron Ruff, la comprobación de formato, la aplicación de migraciones y `alembic check` en una base temporal; `pip-audit -r requirements.txt` no encontró vulnerabilidades conocidas. Se verificaron los ejemplos de los esquemas en el OpenAPI generado. El CI de `dev` estaba en verde. La aprobación final corresponde a otra compañera.
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

## T-240 · Códigos de descuento por tipo de pago — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Yo escribí el código, ejecuté los comandos y hice los commits.
- **Prompt clave:** "me han dado la #240, descuentos por categoría; la descripción está vacía".
- **Qué me explicó o propuso:** antes de programar, dos alcances posibles (por tipo de pago o por categoría de producto) y un mensaje para preguntar al equipo, que eligió el tipo de pago. Después, la columna `applies_to`, la comprobación en `get_valid_code` y un `concept` opcional en la validación.
- **Qué acepté:** todo lo anterior. Cuando el equipo dijo "clases y tienda", me recomendó seguir su decisión; yo preferí dejar también las cuotas, porque no cuesta nada más y sirve para ofertas de la cuota.
- **Qué descarté:** limitar por categoría de producto, que cambiaba el cálculo de RN-15 para un pedido con productos mezclados.
- **Errores o alucinaciones:** nada inventado. Me avisó de antemano de que Alembic no detecta las `CHECK` y de que la migración iba a tener el mismo problema de foreign keys que la T-03, así que la probamos con datos desde el principio. Un test de la HU-25 comparaba la respuesta entera y hubo que añadirle `applies_to`.

## D-07 · README backend (#284) — Beste

- **Herramienta y modelo:** OpenAI Codex / GPT-6, con autorización explícita para editar documentación y ejecutar verificaciones.
- **Prompt clave:** «okay do whatever needed to be done and tell me». Aclaración de alcance: «tehre is separate frontend readme» y «i gave you».
- **Qué me explicó o propuso:** contrastar #284 y su padre #200 con el README, configuración, seed, rutas y CI existentes; añadir instalación, uso e índice de entrega sin introducir herramientas.
- **Qué acepté:** README solo del backend, enlace al README frontend, cuentas ficticias del seed, variables de configuración, persistencia de fotos y comandos de calidad existentes. Docker, retrospectiva y URL pública se señalan pendientes con sus tareas.
- **Qué descarté:** editar el README frontend (#283), duplicar sus instrucciones, implementar Docker o inventar una URL desplegada o una retrospectiva.
- **Errores o alucinaciones:** inicialmente se consideró incluir instrucciones frontend; la persona recordó el alcance separado antes de escribirlas. Se corrigió a un enlace. No se atribuye a esta tarea haber terminado Docker, despliegue o retrospectiva.
- **Verificación:** enlaces relativos del README comprobados; `alembic upgrade head`, `alembic check` y seed ejecutados sobre SQLite temporal; health, Swagger, ReDoc, OpenAPI, login de demo y perfil autenticado comprobados con el cliente existente de FastAPI. Sin modificar la base habitual.
- **Resultado final:** 737 tests existentes pasan, cobertura 96,98 %; Ruff lint y formato pasan (121 archivos); `git diff --check` pasa. La ejecución parcial inicial pasó sus 7 casos pero no alcanzó la cobertura global; se ejecutó la suite completa sin cambiar tests ni umbrales. Entorno local Python 3.11.9; CI usa Python 3.12, documentado como versión de referencia.

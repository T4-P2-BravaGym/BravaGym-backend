# AI log

Cómo hemos usado la IA en cada historia. Es un entregable de la asignatura (apartado 10 de `AGENTS.md`) y cubre los dos repos.

## D-01 y D-02 · Specs, ontología y `AGENTS.md` — Damaris

- **Herramienta y modelo:** Claude (de pago), en modo mentora en conversación. Alcance: solo documentación y revisión; no ha escrito ni ejecutado nada en el repo. Todo el texto lo he pegado y commiteado yo.
- **Prompt clave:** "Reconcilia el `AGENTS.md` con el README de la entrega: el README dice que el agente escribe el código y el apartado 1 dice que la IA es mentora, no programadora."
- **Qué me explicó o propuso:** una plantilla de spec con contexto, requisitos, reglas RN-xx, criterios Dado/Cuando/Entonces, endpoints, fuera de alcance y preguntas abiertas; el esqueleto de la ontología con el glosario español ↔ código; y un apartado 1 con dos modos de trabajo, mentora y agente.
- **Qué acepté:** la plantilla de specs, el esqueleto de la ontología, los comandos del proyecto, la regla de no debilitar un test nunca, y tres puntos nuevos en la Definition of Done (spec enlazada, revisión con comentarios visibles y entrada en esta bitácora).
- **Qué descarté:** los dos modos de trabajo. El 14 de octubre acordamos con la profesora no automatizar la implementación, así que se quitó el modo agente y la IA se queda como mentora. Renunciamos a la comparativa de dos modelos gratuitos del Nivel Medio; la justificación va en la retrospectiva.
- **Errores o alucinaciones:** nada inventado sobre el proyecto. Dos cosas que corregir sobre la marcha: propuso añadir "la cobertura no baja del 80 %" a la Definition of Done cuando eso todavía no se mide (queda para la T-04), y metió un `Refs #NN` en cada mensaje de commit que es redundante con el `Closes #NN` de la PR. También se le pasó que al reescribir el apartado 2 del front se habían borrado dos viñetas; lo detecté revisando el diff.

## HU-34 · Limitador de peticiones en login y registro — por rellenar

Esta historia estaba registrada como una fila de tabla, con el formato antiguo. La rellena quien la hizo, con el formato de arriba.

- Resumen de lo que había: limitador en memoria para login y registro, `RateLimitError` 429 con `Retry-After`, settings en `.env`, tests con freezegun.

## HU-05 · Gestión de roles — Esra

- **Herramienta y modelo:** Claude Code (Claude Opus 5.5), en modo mentora. Me explicaba cada paso en el chat y yo escribía o pegaba el código, ejecutaba los comandos y hacía los commits. Cubre el backend (PR#159) y el selector de rol del frontend (subtarea HU-05.5).
- **Prompt clave (en resumen):** "Guíame para implementar la HU-05 siguiendo las capas del proyecto: un endpoint para que administración cambie roles, con RN-18 y RN-19 comprobadas en el servicio y un test por cada criterio de aceptación." Con el backend ya mergeado: "Ahora llévalo a la tabla de usuarias: una admin tiene que poder pasar a una socia a entrenadora desde allí, sin saltarse esas reglas."
- **Qué me explicó o propuso:** en el backend, `PATCH /users/{id}/role` con `RoleUpdate`, las comprobaciones de RN-18 (403) y RN-19 (409) en `user_service.change_role`, crear un `TrainerProfile` vacío al pasar a entrenadora, el log con ids y sin emails, y los tests de `test_change_role.py`. En el frontend, `changeRole` en `services/users.js`, una función `roleChoices` con los roles que puede dar cada actora, el selector en la columna Rol y un modal de confirmación.
- **Qué acepté:** el endpoint, las reglas y los tests tal como están; en el front, el selector solo en filas que puedo gestionar, activas y que no son mías, la confirmación antes de cambiar y el aviso "X ahora es Y".
- **Qué descarté:** borrar el perfil de entrenadora al volver a socia; se conserva para no perder su bio. Tampoco cambié los permisos de tipos de clase que vimos de paso, porque son de la HU-11.
- **Errores o alucinaciones:** en los primeros tests salía un 500 en vez de 200, porque la base de datos de test no tenía los roles creados; lo arreglamos con una fixture `all_roles`. Al revisar el diff me dio números de línea equivocados; lo vi al comprobarlos yo
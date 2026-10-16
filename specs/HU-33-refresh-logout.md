# HU-33 · Refresh tokens y logout

Issue: #182 · Entrega 2 · Tamaño L · Prioridad P2

## Contexto

> Como usuaria quiero que mi sesión se renueve sola y poder cerrarla de verdad, para no tener que entrar cada hora y que nadie use mi token después de salir.

Actualmente el login devuelve solo un access token y el frontend lo guarda en `localStorage`. `AuthContext` cierra la sesión al caducar el token y `apiRequest` lo hace ante un 401. Esta historia añade renovación y revocación en el servidor. Depende de T-01 (Alembic).

Esta spec comenzó antes de la implementación. Se acordó access token en memoria y refresh token en cookie HttpOnly. Se implementaron el backend local y la integración del frontend. Beste confirmó la comprobación manual básica de login, recarga y logout. La implementación usa el contrato de cookie descrito aquí y exige HTTPS y mismo sitio en producción. Quedan pendientes la revisión humana y el merge; no se afirma que haya un despliegue de producción verificado.

## Requisitos

1. El login correcto entrega ambos tokens: `access_token` y `token_type: bearer` en JSON, y `refresh_token` mediante `Set-Cookie` con HttpOnly. No se incluye el refresh en JSON, URLs ni almacenamiento JavaScript. Se mantiene el formulario OAuth2 compatible con Authorize de Swagger.
2. Las duraciones son configurables: se conserva `ACCESS_TOKEN_EXPIRE_MINUTES` y se propone `REFRESH_TOKEN_EXPIRE_DAYS`, con 7 días por defecto y validación de valores positivos.
3. Cada JWT incluye `sub`, `role`, `exp`, `iss`, `aud`, un identificador único `jti` y `type`. Se distinguen access y refresh y no se aceptan como intercambiables.
4. La base de datos guarda solo el hash del refresh token, la usuaria, su caducidad y su estado de revocación. Nunca guarda el token completo.
5. Un refresh válido se consume una sola vez: se revoca y se devuelve un nuevo par de tokens. La comprobación y consumo son atómicos, de modo que dos peticiones simultáneas no puedan reutilizarlo.
6. Refresh tokens manipulados, revocados, caducados o pertenecientes a usuarias inactivas producen 401 sin emitir nuevos tokens.
7. Logout revoca el refresh de la sesión y el access actual mediante su `jti` hasta su caducidad. El servidor comprueba la pertenencia a la misma usuaria antes de revocar.
8. `get_current_user` verifica firma, caducidad, emisor, audiencia, tipo access, `jti` no revocado y usuaria activa. El refresh nunca permite acceder directamente a recursos protegidos.
9. Se limpian los registros de revocación caducados sin eliminar revocaciones todavía necesarias.
10. El frontend intenta refrescar una sola vez ante un 401 de una petición autenticada y reintenta la petición original una sola vez. Si falla, borra la sesión local. Login y refresh no disparan otro refresh recursivo.
11. Peticiones simultáneas del frontend comparten una única renovación en curso para no competir al rotar el mismo token. Una respuesta tardía de refresh no restaura una sesión después de logout.
12. La expiración local del access token deja de provocar logout inmediato si todavía puede renovarse la sesión. Al recargar la página, la inicialización debe resolver la renovación antes de decidir que no hay sesión.
13. El frontend mantiene el access token solo en memoria y el refresh en una cookie HttpOnly, enviada con `credentials: include` en login, refresh y logout. Elimina la persistencia anterior de `brava.token` en `localStorage`. La cookie se rota al refrescar y se elimina al cerrar sesión con el mismo nombre y Path usados al crearla.
14. Las operaciones de emisión, rotación y revocación se registran sin contraseñas, tokens ni hashes. Los nuevos endpoints tienen summary, ejemplos y respuestas de error en Swagger.
15. Se actualizan `AGENTS.md` (claims `jti` y `type`), `.env.example`, la documentación de API y `docs/ai-log.md` con el alcance real de la ayuda de IA.
16. La cookie no define Domain (solo host de la API), limita Path a `/api/v1/auth`, tiene caducidad coherente con el refresh y usa Secure en HTTPS de producción. La excepción local para HTTP debe ser explícita y documentada.
17. En local se usa SameSite=Lax, sin Secure únicamente cuando ENVIRONMENT=local. Login valida Origin cuando está presente: debe ser un origen CORS permitido o el propio de la API (Swagger). Refresh y logout exigen además X-Brava-CSRF: 1. Clientes sin Origin (Bruno/CLI) pueden usarlos; Sec-Fetch-Site: cross-site sin Origin se rechaza. Un rechazo CSRF no borra cookies ni revoca tokens. La configuración de producción requiere HTTPS y frontend/API en el mismo sitio; no se usa CORS comodín con credenciales.

## Reglas

`docs/business-rules.md` no asigna una RN a la renovación de sesión. Se aplican las reglas de autenticación de `AGENTS.md`: verificar algoritmo fijo, firma, expiración, emisor y audiencia; fallar cerrado; no exponer secretos en respuestas o logs. No se modifican las reglas de roles RN-18 y RN-19.

## Criterios de aceptación

- **Dado** un login correcto, **cuando** envío el formulario de login, **entonces** recibo access y refresh con caducidades configurables y Authorize de Swagger sigue funcionando.
- **Dado** un refresh válido, **cuando** llamo a `POST /auth/refresh`, **entonces** recibo un par nuevo y el refresh anterior queda revocado.
- **Dado** un refresh revocado, caducado o manipulado, **cuando** intento renovarlo, **entonces** recibo 401.
- **Dado** que hago logout, **cuando** reutilizo el refresh o el access actual, **entonces** ambos se rechazan.
- **Dada** una usuaria inactiva, **cuando** intenta refrescar, **entonces** recibe 401.
- **Dado** un refresh usado como bearer para un recurso protegido, **cuando** se autentica la petición, **entonces** recibe 401 por tipo incorrecto.
- **Dadas** dos renovaciones simultáneas con el mismo refresh, **cuando** compiten, **entonces** solo una obtiene un nuevo par.
- **Dado** un access caducado y un refresh válido, **cuando** una petición autenticada recibe 401, **entonces** el frontend renueva una vez y reintenta una vez.
- **Dado** que también falla el refresh, **cuando** termina el intento, **entonces** se borra la sesión y se vuelve al login, sin bucles.
- **Dadas** varias peticiones con 401, **cuando** solicitan renovación, **entonces** comparten una sola petición de refresh.
- **Dado** un logout durante una renovación, **cuando** llega la respuesta tardía, **entonces** no vuelve a iniciar sesión localmente.
- **Dados** registros revocados caducados y vigentes, **cuando** se ejecuta la limpieza, **entonces** solo se eliminan los caducados.
- **Dado** un login o refresh correcto, **cuando** inspecciono la respuesta, **entonces** el refresh solo aparece en la cookie HttpOnly y el access aparece en JSON.
- **Dado** el frontend autenticado, **cuando** inspecciono localStorage y sessionStorage, **entonces** no contienen access ni refresh tokens de esta sesión.
- **Dado** logout, **cuando** termina, **entonces** la cookie del refresh se elimina y el frontend borra el access de memoria.
- **Dada** una petición de origen no autorizado que intenta usar cookies de sesión, **cuando** llama a una operación de autenticación, **entonces** la protección CSRF la rechaza sin modificar la sesión.

## Endpoints

Prefijo: `/api/v1`. Login y refresh entregan el access en JSON y el refresh en cookie HttpOnly. Los requisitos de despliegue se enumeran en Contrato y despliegue.

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/auth/login` | Público con credenciales | 200 access/token_type y cookie refresh | 401, 403 (CSRF), 422, 429 |
| POST | `/auth/refresh` | Con cookie refresh válida | 200 access/token_type y cookie refresh rotada | 401, 403 (CSRF) |
| POST | `/auth/logout` | Sesión que se revoca | 204 sin cuerpo y eliminación de cookie | 401, 403 (CSRF) |

Refresh se lee de la cookie, sin body JSON con el token. Los clientes de API deben conservar y reenviar cookies. Swagger mantiene Authorize con el access bearer; para probar refresh debe usar la cookie obtenida en login. Logout exige bearer access y cookie refresh de la misma usuaria activa. Solo para logout se admite un access caducado cuya firma, tipo, emisor y audiencia siguen siendo válidos, junto con su refresh no caducado almacenado en la base de datos. No se guarda una revocación de access que ya caducó. Los recursos protegidos siguen comprobando la caducidad. Refresh y logout requieren X-Brava-CSRF: 1 también en Swagger y Bruno. Un 401 de estas operaciones elimina la cookie; un 403 de origen/CSRF no la modifica. Login y refresh envían Cache-Control: no-store.

Nuevas tablas propuestas: `refresh_tokens` (id, user_id, token_hash único, expires_at, revoked_at) y `revoked_tokens` (jti único, expires_at). Se añaden mediante una nueva migración Alembic, sin editar migraciones ya mergeadas. Una rotación confirma la revocación y la nueva sesión en la misma transacción.

## Interfaz

No se añade pantalla. Se modifica el flujo de sesión de `AuthContext`, `services/api.js` y `services/auth.js` del frontend. Se conserva el login y el botón de logout existentes; se añade la inicialización de sesión pendiente para evitar redirecciones prematuras mientras se renueva.

Se acordó access token en memoria y refresh en cookie HttpOnly. Al recargar, el frontend intenta recuperar la sesión mediante la cookie, sin leer el refresh desde JavaScript. Los tokens no se guardan en localStorage ni sessionStorage.

Riesgos: HttpOnly dificulta la lectura directa del refresh por JavaScript, pero no impide que un XSS haga acciones desde la página o lea un access token en uso. Las cookies requieren protección CSRF y configuración coherente de Secure, SameSite, CORS y credenciales. La coordinación del frontend es por página: varias pestañas pueden competir por la misma cookie y requerir un nuevo login. Si logout no es confirmado, se informa y se permite reintentar conservando el access únicamente en memoria para esa operación. No se promete que HttpOnly elimine todos los riesgos. Referencia: [OWASP HTML5 Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html).

## Fuera de alcance

- Recuperación de contraseña: HU-35, issue #184.
- Verificación de email, OAuth externo o autenticación multifactor.
- Pantalla de gestión de dispositivos o logout global de todas las sesiones.
- Refactors o correcciones de formato de archivos ajenos a esta historia.

## Contrato y despliegue

- Contrato adoptado con autorización de Beste: access en JSON y memoria; refresh exclusivamente en cookie HttpOnly. No se atribuye aprobación al resto del equipo.
- Producción requiere HTTPS y frontend/API en el mismo sitio (mismo esquema y dominio registrable). Pueden ser subdominios; CORS debe permitir exactamente el origen del frontend y las credenciales. También puede usarse un proxy del mismo origen.
- Configurar `ENVIRONMENT` con un valor distinto de `local`, `CORS_ORIGINS` con el origen HTTPS real y `VITE_API_URL` con la URL real de la API. Mantener SameSite=Lax, Secure, validación de Origin y X-Brava-CSRF.
- El despliegue entre sitios diferentes no está soportado por este contrato: exige una revisión específica de cookies y CSRF. No se cambian estos controles para adaptar dominios desconocidos.
- Antes de publicar, aplicar la migración y desplegar ambos repos coordinadamente. En las URLs reales comprobar login, recarga, renovación y logout con rechazo posterior de ambos tokens. Esta comprobación de producción no se ha ejecutado; no hay URLs configuradas en el repositorio.
- Tras desplegar el cambio, los JWT antiguos sin jti/type requieren un nuevo login; no se aceptan silenciosamente.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Spec antes de implementación | Requisito explícito de #182 y del flujo del equipo. |
| Una spec para ambos repos | La renovación requiere backend y frontend coordinados. |
| Hash del refresh y consumo atómico | Evitar guardar tokens reutilizables en claro y evitar doble rotación. |
| Mantener formulario OAuth2 en login | Conservar Authorize de Swagger. |
| Access en memoria y refresh en cookie HttpOnly | Decisión acordada con Beste; evitar persistir tokens accesibles por JavaScript. |
| No devolver refresh también en JSON | Evitar que la misma respuesta vuelva a exponerlo a JavaScript. |
| Limpieza al emitir, renovar y cerrar sesión | Eliminar revocaciones de access caducados dentro de la transacción, manteniendo los vigentes. |
| Backend local primero | Avanzar sin asumir el dominio de producción; la integración del frontend sigue este contrato. |
| Versión de sesión en el cliente | No repetir una petición antigua bajo un login posterior, aunque el token haya cambiado. |
| Fallo de logout visible y reintentable | Borrar la sesión local sin afirmar que el servidor la revocó si no confirmó la operación. |

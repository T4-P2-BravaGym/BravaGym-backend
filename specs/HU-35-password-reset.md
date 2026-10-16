# HU-35 · Recuperar la contraseña con un token temporal

Issue: #184 · Entrega 2 · Tamaño M · Prioridad P3 · Depende de: T-01 (Alembic)

## Contexto

> Como usuaria quiero recuperar el acceso si olvido la contraseña.

Existen login y cambio de contraseña autenticado (HU-32), pero no recuperación sin sesión. HU-33 aporta renovación y revocación de sesiones. Esta historia añade solicitud y confirmación públicas y dos páginas del frontend. La spec se redacta antes del código. Beste aprobó el diseño y el cierre de todas las sesiones tras el reset.

## Requisitos

1. Una solicitud con un email sintácticamente válido recibe siempre 202 y el mismo JSON: `{"detail": "Si existe una cuenta activa con ese email, recibirás un enlace para recuperar tu contraseña."}`. Emails desconocidos e inactivos no revelan la existencia ni el estado de la cuenta. Entrada malformada recibe 422 sin consultar existencia. Ningún token se devuelve en la respuesta.
2. Generar tokens opacos con `secrets.token_urlsafe(32)`; guardar exclusivamente SHA-256, usuaria, creación, caducidad y consumo. Validez de 30 minutos UTC; en el instante exacto de expiración el token ya no vale.
3. Para una cuenta activa, enviar el enlace a través de una interfaz `EmailSender` inyectada. La implementación local escribe mensajes en `outbox/`, ignorado por Git, con nombres aleatorios sin email ni token, directorio privado (0700) y archivos privados (0600). El enlace aparece solo en el mensaje privado; nunca en logs ni respuestas. No se publica outbox mediante HTTP.
4. Construir enlaces desde una URL del frontend configurada y validada, nunca desde la cabecera Host ni desde una URL recibida en el body. HTTP solo en local; HTTPS fuera de local. El adaptador de outbox es de desarrollo: no afirmar envío SMTP ni permitir su uso silencioso como correo de producción.
5. La respuesta genérica no depende de si se entrega un email. Ejecutar el trabajo de entrega fuera del camino que determina la respuesta; limitar envíos a tres por dirección normalizada en quince minutos manteniendo el mismo 202 para todas las cuentas. Documentar el límite de la implementación en memoria y que no es una cola duradera.
6. Confirmación con token válido y contraseña nueva devuelve 204 sin cuerpo. Consumir el token y cambiar el hash bcrypt en una sola transacción. Dos confirmaciones simultáneas solo permiten un éxito; un fallo revierte ambas operaciones. Tras éxito, invalidar los demás tokens de recuperación pendientes de esa usuaria, incrementar su versión de sesión y revocar sus refresh en la misma transacción. Registrar la actualización de la usuaria con los campos de auditoría existentes.
7. Token desconocido, manipulado, caducado, usado o de una usuaria desactivada devuelve el mismo 400: `El enlace no es válido o ha caducado. Solicita uno nuevo.`. No reactivar cuentas. Un body inválido devuelve 422 sin consumir el token.
8. Reutilizar la política de contraseñas del proyecto: mínimo ocho caracteres y máximo 72 bytes UTF-8 para bcrypt. No devolver ni registrar contraseñas. Sanitizar las respuestas 422 de estos endpoints para excluir valores de entrada, tokens, contraseñas y cuerpos rechazados; probarlo también con campos extra. No pedir contraseña actual ni iniciar sesión automáticamente tras el reset.
9. El frontend ofrece «He olvidado mi contraseña» desde login, la solicitud y «Nueva contraseña» con confirmación de contraseña. Usa el cliente HTTP existente con `auth: false`: un 400/422 no provoca renovación de sesión.
10. El token del enlace se transporta en el fragmento de la URL (`/nueva-contrasena#token=...`) para evitar enviarlo al servidor web como parte de la URL. Leerlo en memoria, retirar el fragmento con reemplazo del historial y enviarlo solo en el body de confirmación. No persistirlo en localStorage/sessionStorage ni incluirlo en analítica. No hay redirecciones externas.
11. Mantener estados de carga, error y éxito, validación local y reintento ante fallo de red. Token ausente o inválido ofrece solicitar otro enlace; tras éxito, eliminar token y contraseñas de memoria y ofrecer «Ir a iniciar sesión».
12. Usar componentes existentes, textos en español, estilos con tokens, campos etiquetados, foco visible y controles por teclado; verificar ancho de móvil. No crear otro runner: frontend con Vitest y Testing Library, backend con pytest/freezegun.
13. Registrar solicitudes procesadas y cambios de contraseña sin datos sensibles. Documentar endpoints con summary, ejemplos y respuestas de error. Actualizar README, `.env.example`, `.gitignore`, documentación de API y `docs/ai-log.md`.

## Reglas

No se asigna una RN nueva. Aplican las reglas de autenticación, validación, transacciones y logs de `AGENTS.md`. Las operaciones son públicas y el token de recuperación autoriza exclusivamente cambiar la contraseña de su propietaria; no es bearer access ni refresh. Después de un reset correcto se invalidan todas las sesiones, incluidos access y refresh emitidos antes del cambio.

## Criterios de aceptación

- **Dado** cualquier email válido existente, desconocido o inactivo, **cuando** solicito recuperación, **entonces** recibo 202 con el mismo cuerpo y sin token.
- **Dada** una usuaria activa, **cuando** proceso su solicitud local, **entonces** aparece un mensaje privado en outbox con un enlace de la URL configurada y la base solo contiene el hash.
- **Dado** un email desconocido o inactivo, **cuando** proceso su solicitud, **entonces** no envío un enlace ni modifico la cuenta.
- **Dado** un token válido, **cuando** confirmo una contraseña válida, **entonces** recibo 204, puedo entrar con ella y la anterior ya no sirve.
- **Dado** un token caducado a los 30 minutos, manipulado, desconocido o usado, **cuando** confirmo, **entonces** recibo 400 sin cambiar la contraseña.
- **Dadas** dos confirmaciones simultáneas, **cuando** usan el mismo token, **entonces** solo una devuelve 204 y la otra 400.
- **Dado** un fallo durante el cambio, **cuando** se revierte la transacción, **entonces** la contraseña no cambia y el token no queda consumido.
- **Dada** una contraseña inválida, **cuando** envío confirmación, **entonces** recibo 422 y el token sigue disponible.
- **Dado** un reset correcto, **cuando** reutilizo otro enlace pendiente anterior, **entonces** recibo 400.
- **Dadas** sesiones abiertas en varios dispositivos, **cuando** termina el reset, **entonces** ninguno de sus access ni refresh anteriores autoriza recursos o renueva sesión; un nuevo login con la nueva contraseña sí funciona.
- **Dada** una cuenta sin reset y un token histórico sin `ver`, **cuando** se verifica, **entonces** conserva su validez normal en versión 0; después del reset se rechaza.
- **Dada** una solicitud repetida o un fallo de entrega local, **cuando** termina la petición, **entonces** se conserva el mismo 202 y cuerpo genérico, no se revela la existencia de la cuenta ni se imprime el enlace en logs. Los fallos internos se registran con mensajes seguros sin el contenido del email.
- **Dadas** ambas páginas, **cuando** las uso por teclado o a ancho móvil, **entonces** puedo completar el flujo con estados accesibles y sin guardar tokens en storage.

## Endpoints

Prefijo: `/api/v1`.

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/auth/password-reset` | Público | 202 con mensaje genérico | 422 para entrada inválida |
| POST | `/auth/password-reset/confirm` | Público con token en el body | 204 sin cuerpo | 400 token inválido, 422 entrada inválida |

Solicitud: `{"email": "lucia@example.com"}`. Confirmación: `{"token": "<opaque reset token>", "new_password": "OtraClave2026!"}`. Esquemas cerrados: email de hasta 255 caracteres, token de uno a 256 caracteres y contraseña con los límites del requisito 8; no aceptar user_id, role, is_active ni URL de redirección. Respuestas con `Cache-Control: no-store`.

Nueva tabla propuesta `password_reset_tokens`: id, user_id con FK e índice, token_hash único de 64 caracteres, created_at, expires_at indexado y used_at nullable. Nueva migración sin editar las anteriores; comprobar upgrade, downgrade y correspondencia con modelos sobre SQLite temporal. La misma migración añade `users.session_version`, entero no negativo con valor inicial y server_default 0. Los nuevos JWT access/refresh llevan `ver`; emisión usa la versión actual de la usuaria. Autenticación, refresh y logout contrastan esa versión con la base de datos. Tokens históricos sin `ver` se consideran versión 0 únicamente; tras un reset la versión se incrementa atómicamente y esos tokens dejan de valer. Una `ver` presente debe ser un entero no negativo (no booleano). El reset revoca además todos los refresh existentes y no emite nuevos tokens.

## Interfaz

- `PATHS.forgotPassword`: `/recuperar-contrasena`, formulario de email y confirmación genérica.
- `PATHS.resetPassword`: `/nueva-contrasena`, contraseña nueva/repetición y estado de enlace inválido; enlace a solicitud nueva.
- Ambas rutas bajo `PublicLayout minimal`, reutilizando Field, Button y Alert y el lenguaje visual de login/registro.
- Login incorpora un enlace interno «He olvidado mi contraseña».
- Tras éxito se ofrece volver a login, sin crear sesión automáticamente.

## Fuera de alcance

- Verificación opcional de email y columna email_verified_at.
- Proveedor SMTP externo, credenciales de correo y despliegue en producción.
- MFA, recuperación administrativa, preguntas de seguridad y refactors ajenos.

## Preguntas abiertas

- Diseño y plan aprobados por Beste; se ejecuta en este chat con revisión independiente al final.
- Producción requiere un adaptador real de correo y una URL HTTPS del frontend; esta entrega ofrece exclusivamente el adaptador de desarrollo solicitado.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Cierre global de sesiones aprobado por Beste | Evitar que una sesión antigua conserve acceso tras recuperar la cuenta. |
| Versión de sesión en cuenta y JWT | Invalidar access y refresh en una transacción, preservando tokens históricos solo hasta el primer reset. |
| Spec antes del código | Requisito de #184 y del equipo. |
| Reutilizar Vitest del equipo | Mantener un solo runner frontend. |
| Outbox local detrás de EmailSender | Entregable explícito; no requiere servicio externo ni expone enlaces en logs. |
| Token opaco con hash y consumo atómico | Token de un solo uso, también ante concurrencia. |
| Enlace de URL configurada y token en fragmento | Evitar Host injection y reducir exposición del token en logs del servidor web. |

Referencia para la revisión: https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html


Validación de implementación: pytest/freezegun y Vitest existentes; migración reversible comprobada sobre SQLite temporal con una usuaria ficticia. Flujo HTTP real comprobado con outbox local y rechazo posterior de access/refresh previos. Revisión independiente completada y corrección de Cache-Control en errores 400 cubierta por regresión. No se afirma despliegue de producción ni revisión humana/merge realizados.

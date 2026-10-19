# HU-02 · Registro de socia

Issue: #15 · Entrega 1 · Tamaño M

## Contexto

> Como visitante quiero crear una cuenta para poder reservar y comprar.

Toca autenticación y usuarios. Con los modelos de la HU-01 ya existía la tabla `users`, pero no
había forma de crear una cuenta desde fuera. Es la puerta de entrada para todo lo demás: el login
(HU-03) y el perfil (HU-04) necesitan usuarias registradas.

## Requisitos

1. Una visitante crea su cuenta con nombre, apellidos, email, contraseña y, si quiere, teléfono.
2. La cuenta nueva es siempre de socia y está activa; la visitante no elige su rol ni su estado.
3. No puede haber dos cuentas con el mismo email, aunque cambien las mayúsculas.
4. La contraseña tiene al menos 8 caracteres y nunca se guarda ni se devuelve en claro.
5. El nombre y los apellidos solo llevan letras, espacios, guiones o apóstrofos.
6. El registro queda en el log con el id de la usuaria, sin datos personales.

## Criterios de aceptación

- **Dado** un email nuevo y una contraseña de 8 o más caracteres, **cuando** me registro, **entonces** se crea un usuario `member` activo y recibo 201 sin la contraseña en la respuesta.
- **Dado** un email ya registrado, **cuando** me registro, **entonces** recibo 409.
- **Dado** un email ya registrado escrito con otras mayúsculas, **cuando** me registro, **entonces** recibo 409.
- **Dado** cualquier registro, **cuando** consulto la BD, **entonces** la contraseña está hasheada con bcrypt.
- **Dado** que envío `role` en el cuerpo, **cuando** me registro, **entonces** se ignora y la cuenta es `member`.
- **Dado** una contraseña de menos de 8 caracteres, **entonces** recibo 422.
- **Dado** una contraseña de más de 72 bytes, **entonces** recibo 422.
- **Dado** un email con formato inválido, **entonces** recibo 422.
- **Dado** un nombre o apellido con números o símbolos, **entonces** recibo 422.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/auth/register` | Pública | 201 `UserOut` | 409, 422 |

Cuerpo: `UserCreate` (`email`, `password`, `first_name`, `last_name`, `phone` opcional).
`UserOut` devuelve `id`, `email`, `first_name`, `last_name`, `phone`, `is_active` y `role`.
No cambia el esquema.

## Interfaz

Pantalla "Crear cuenta" (`/registro`): formulario con nombre y apellidos en la misma fila, email,
teléfono (opcional) y contraseña. Valida en el navegador antes de enviar y muestra el error debajo
de cada campo. Estados: enviando (botón deshabilitado), error de la API (aviso rojo; con 409,
"Ya hay una cuenta con este email. Prueba a entrar.") y hecho (aviso verde "Tu cuenta está lista"
con un botón para ir a entrar). En login y registro se muestran una barra de navegación y un pie
mínimos.

## Fuera de alcance

- Iniciar sesión (HU-03).
- Entrar automáticamente después de registrarse.
- Verificar el email.
- Limitar los intentos de registro por IP (HU-34).
- Mostrar u ocultar la contraseña al escribirla (T-75).
- Editar los datos después del registro (HU-04).

## Decisiones

| Decisión | Por qué |
| --- | --- |
| `UserCreate` no tiene `role` ni `is_active` | Los decide el servidor; si la visitante los envía, Pydantic los ignora. |
| El email se normaliza con `normalize_email` (sin espacios y en minúsculas), compartida con el login | Una sola regla para que registro y login comparen igual y no haya dos cuentas por las mayúsculas. |
| El 409 también salta con el `IntegrityError` del `UNIQUE` | Cubre la carrera de dos registros con el mismo email a la vez. |
| La contraseña se rechaza si pasa de 72 bytes | bcrypt solo usa los primeros 72 bytes; "ñ" o un emoji ocupan más de uno. |
| Nombre y apellidos con `NAME_PATTERN` (PR #145) | Se aceptan nombres reales como "María José" u "O'Neill", pero no números ni símbolos. |
| Si falta el rol `member` en la BD, error claro pidiendo el seed | Es un fallo de instalación, no de la usuaria. |
| El front valida lo mismo que la API antes de enviar | La usuaria ve el error al momento; la API sigue siendo la que manda. |
| El teléfono vacío se envía como `null` | Es opcional y así no se guarda una cadena vacía. |
| Después de registrarse va a la pantalla de entrar, sin login automático | Más simple, y el login ya es otra historia (HU-03). |
# HU-32 · Cambiar mi contraseña

Issue: #181 · Entrega 2 · Tamaño S · Prioridad P1

## Contexto

> Como usuaria quiero cambiar mi contraseña para mantener segura mi cuenta.

Toca usuarios y autenticación (nivel medio del README). Hasta ahora la contraseña solo se ponía
al registrarse (HU-01) y no se podía cambiar. Reutiliza el hash y la comprobación de la HU-02
(`hash_password`, `verify_password`) y las mismas reglas de contraseña que el registro.

## Requisitos

1. Cualquier usuaria logueada puede cambiar su contraseña, sea del rol que sea.
2. Para cambiarla tiene que escribir la actual.
3. La nueva cumple las mismas reglas que en el registro y no puede ser igual a la actual.
4. Después del cambio entra con la nueva y ya no con la antigua.
5. El cambio queda en el log con su id, y la contraseña nunca aparece en el log ni en la respuesta.
6. Si se equivoca muchas veces con la contraseña actual, se bloquea un rato, como en el login (HU-34).

## Criterios de aceptación

- **Dado** que estoy logueada, **cuando** envío `POST /users/me/password` con `current_password` y `new_password` correctos, **entonces** recibo 204 y puedo hacer login con la nueva.
- **Dado** que cambié la contraseña, **cuando** hago login con la antigua, **entonces** recibo 401.
- **Dado** una `current_password` incorrecta, **entonces** recibo 400 (no 401: el front cierra la sesión ante un 401) y la contraseña no cambia.
- **Dado** una contraseña nueva de menos de 8 caracteres, **entonces** recibo 422.
- **Dado** una contraseña nueva igual a la actual, **entonces** recibo 422.
- **Dado** una contraseña nueva de más de 72 bytes, **entonces** recibo 422, igual que en el registro.
- **Dado** que me he equivocado 5 veces con la contraseña actual en 15 minutos, **cuando** lo intento otra vez, **entonces** recibo 429 con `Retry-After`, aunque esta vez sea la correcta.
- **Dado** que no he iniciado sesión, **cuando** llamo al endpoint, **entonces** recibo 401.
- **Dado** cualquier cambio, **cuando** reviso el log, **entonces** aparece el cambio pero nunca la contraseña.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/users/me/password` | Cualquier usuaria logueada | 204 sin cuerpo | 400, 401, 422, 429 |

Cuerpo: `PasswordChange` (`current_password`, `new_password`). No cambia el esquema: se
actualiza `users.password_hash`.

## Interfaz

"Mi perfil" (`/mi-area/perfil`, de la HU-04): una sección nueva "Cambiar contraseña" debajo de
los datos, con tres campos: contraseña actual, nueva y repetir la nueva. Si las dos nuevas no
coinciden, el aviso sale sin llamar a la API. Estados: "Guardando…" en el botón, aviso verde
"Tu contraseña se ha cambiado" (y los campos se vacían) y aviso rojo con el mensaje de la API.

## Fuera de alcance

- Recuperar la contraseña olvidada por email (HU-35).
- Revocar los refresh tokens al cambiarla: dependen de la HU-33, que aún no está hecha.
- Cerrar las demás sesiones abiertas: el token actual sigue valiendo hasta que caduca.
- Que administración cambie la contraseña de otra usuaria (HU-31 lo excluye).
- Reglas de contraseña más fuertes (mayúsculas, símbolos): se usan las del registro.
- La pantalla para entrenadoras y administración: hoy "Mi perfil" solo está en el área de socia. La API ya deja cambiar la contraseña a cualquier rol; abrir la pantalla a los demás roles es una decisión del equipo.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| `PasswordChange` vive en `schemas/auth.py`, junto al registro | Las reglas de contraseña ya estaban allí. |
| La regla de los 72 bytes pasa a una función común (`check_fits_bcrypt`) que usan el registro y el cambio | Una sola regla en un solo sitio (DRY); el registro se comporta igual. |
| "Igual a la actual" se comprueba en el esquema (422) | Solo compara los dos textos enviados, no hace falta la base de datos. |
| La contraseña incorrecta se comprueba en el servicio con `verify_password` (400) | Hay que leer el hash guardado. Se usa la `AppError` base, que ya es 400, sin tocar `exceptions.py`. |
| Límite de 5 intentos fallidos en 15 minutos con el `AttemptWindowLimiter` de la HU-34 | Sin límite, alguien con la sesión de otra podría probar contraseñas. Se reutiliza la clase; el login no cambia. |
| El límite se cuenta por id de usuaria, no por IP | La usuaria ya está identificada; así los fallos de una no bloquean a otra. |
| Un cambio correcto pone el contador a cero | Igual que el login: los fallos antiguos no cuentan después de acertar. |
| La respuesta es 204 sin cuerpo | No hace falta devolver nada y así nada de la contraseña sale en la respuesta. |
| El formulario es un componente aparte (`ChangePasswordForm`) dentro de "Mi perfil" | Cada formulario guarda su propio estado y la página no crece. |
| El front comprueba las mismas reglas antes de llamar a la API | Un 422 de la API llega como un mensaje genérico; así cada error dice qué corregir. La API sigue siendo la que protege. |
| Al cambiarla, los campos se vacían | Las contraseñas no se quedan en pantalla. |
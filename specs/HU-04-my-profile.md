# HU-04 · Ver y editar mi perfil

Issue: #25 · Entrega 1 · Tamaño S

## Contexto

> Como usuaria quiero ver y actualizar mis datos para mantenerlos al día.

Toca usuarios. Después del registro y el login (HU-01, HU-02) no había forma de ver ni cambiar
los propios datos. Sirve para cualquier rol. La edición que hace administración sobre otra
usuaria es la HU-31, que reutiliza la misma lógica.

## Requisitos

1. Cualquier usuaria logueada ve sus datos: nombre, apellidos, teléfono, email y rol.
2. Puede cambiar su nombre, apellidos, teléfono y email, de uno en uno o todos a la vez.
3. Nunca puede cambiar su rol ni su estado desde su perfil.
4. El email nuevo no puede ser de otra persona, y después puede entrar con él.
5. El cambio queda en el log con su id, sin datos personales.

## Reglas

- **RN-12**: una socia no puede darse de baja a sí misma; el perfil no tiene ningún campo de estado.

## Criterios de aceptación

- **Dado** que estoy logueada, **cuando** pido `GET /users/me`, **entonces** veo mis datos y mi rol, y nunca el hash de la contraseña.
- **Dado** que estoy logueada, **cuando** envío solo nombre y teléfono, **entonces** recibo 200 y el resto de campos no cambia.
- **Dado** que edito mi perfil, **cuando** envío `role` o `is_active`, **entonces** esos campos se ignoran.
- **Dado** que envío un teléfono `null`, **entonces** se borra mi teléfono.
- **Dado** un nombre vacío, `null` o de más de 80 caracteres, **entonces** recibo 422.
- **Dado** un email en mayúsculas, **entonces** se guarda en minúsculas.
- **Dado** el email de otra usuaria, **entonces** recibo 409; si envío el mío propio, recibo 200.
- **Dado** un email con formato inválido, **entonces** recibo 422.
- **Dado** que cambié mi email, **cuando** hago login con el nuevo, **entonces** entro.
- **Dado** que no he iniciado sesión, **cuando** llamo a `GET` o `PATCH /users/me`, **entonces** recibo 401.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/users/me` | Cualquier usuaria logueada | 200 `UserOut` | 401 |
| PATCH | `/users/me` | Cualquier usuaria logueada | 200 `UserOut` | 401, 409, 422 |

Cuerpo del `PATCH`: `UserUpdate` (`first_name`, `last_name`, `phone`, `email`, todos opcionales).
No cambia el esquema.

## Interfaz

Pantalla "Mi perfil" (`/mi-area/perfil`): un formulario con nombre, apellidos, teléfono
(opcional) y email, cargado con mis datos. Estados: cargando (spinner), error (aviso rojo con el
mensaje de la API) y guardado (aviso verde "Tus datos se han guardado"). El botón muestra
"Guardando…" mientras espera.

## Fuera de alcance

- Cambiar la contraseña (HU-32).
- Editar la bio y la foto de entrenadora (HU-15).
- Editar los datos de otra usuaria (HU-31).
- Darse de baja (HU-19).

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Solo se cambian los campos enviados (`exclude_unset`) | Así un `PATCH` con un solo campo no borra los demás. |
| Nombre y apellidos pueden omitirse pero no ir a `null` | La base de datos los exige; antes un `null` daba un 500. |
| El teléfono vacío se guarda como `null` | Un teléfono es opcional; el front envía `null` si el campo queda en blanco. |
| El email se normaliza a minúsculas y el 409 también cubre la carrera con el `UNIQUE` | Igual que en el registro, para que no haya dos cuentas con el mismo email. |
| La lógica de guardar está en `_apply_profile_changes` | La HU-31 la reutiliza para que admin edite a otra usuaria. |
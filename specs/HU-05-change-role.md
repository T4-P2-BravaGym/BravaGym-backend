# HU-05 · Gestión de roles

Issue: #29 · Entrega 1 · Tamaño M 

## Contexto

> Como administración quiero cambiar a una persona entre socia y entrenadora para gestionar el equipo.

Toca usuarios y roles. Antes, el rol solo se podía cambiar en la base de datos. La historia
añade un endpoint para cambiarlo y un selector en la tabla de "Usuarias y roles" del panel
de administración. Usa el listado de HU-06 y convive con las acciones de HU-31.

## Requisitos

1. Administración puede pasar a una persona de socia a entrenadora y al revés.
2. Al pasar a entrenadora se le crea un perfil de entrenadora vacío, para que aparezca en el equipo.
3. Solo la superadmin puede dar o quitar los roles `admin` y `superadmin`.
4. Nadie puede cambiar su propio rol.
5. Siempre queda al menos una superadmin.
6. Cada cambio queda en el log: quién, a quién, rol anterior y rol nuevo, sin emails.

## Reglas

- **RN-18**: Administración solo cambia roles entre `member` y `trainer`. Asignar o quitar `admin` y `superadmin` es exclusivo del superadmin.
- **RN-19**: Nadie cambia su propio rol, y siempre debe quedar al menos un superadmin → 409.

## Criterios de aceptación

- **Dado** que soy admin, **cuando** cambio a alguien de `member` a `trainer`, **entonces** recibo 200 y se crea su perfil de entrenadora vacío.
- **Dado** que soy admin, **cuando** cambio a una entrenadora a `member`, **entonces** recibo 200.
- **Dado** que soy admin, **cuando** intento asignar `admin` o `superadmin`, o cambiar el rol de otra admin, **entonces** recibo 403.
- **Dado** que soy superadmin, **cuando** hago admin a alguien, **entonces** recibo 200.
- **Dado** que soy admin o superadmin, **cuando** intento cambiar mi propio rol, **entonces** recibo 409.
- **Dado** que hay dos superadmins, **cuando** una superadmin le quita el rol a la otra, **entonces** recibo 200.
- **Dado** que soy socia, **cuando** intento cambiar un rol, **entonces** recibo 403.
- **Dado** que no he iniciado sesión, **cuando** llamo al endpoint, **entonces** recibo 401.
- **Dado** un id que no existe, **cuando** cambio su rol, **entonces** recibo 404.
- **Dado** un rol que no existe, **cuando** lo envío, **entonces** recibo 422.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| PATCH | `/users/{user_id}/role` | Admin, superadmin | 200 `UserOut` | 401, 403, 404, 409, 422 |

Cuerpo: `RoleUpdate` (`{"role": "trainer"}`). No cambia el esquema: usa `users.role_id`
y crea una fila en `trainer_profiles` si hace falta. Sin migración.

## Interfaz

Pantalla "Usuarias y roles" (`/admin/usuarias`), columna Rol:

- Un selector de rol en cada fila que puedo gestionar, si la persona está activa y no soy yo.
  En el resto de filas se ve el rol como texto.
- Opciones: una admin ve socia y entrenadora; la superadmin ve los cuatro roles.
- Al elegir un rol se abre un modal de confirmación ("X pasará de A a B", botón "Cambiar rol").
- Si sale bien: aviso verde "X ahora es Y" y la tabla se recarga. Si falla: aviso rojo con el mensaje de la API.

## Fuera de alcance

- Listar y buscar usuarias (HU-06).
- Ver, editar y dar de baja a una usuaria (HU-31).
- Editar el perfil de la entrenadora (HU-15).
- Historial de cambios de rol en pantalla: solo queda en el log.

## Preguntas abiertas

- Cuando una entrenadora pasa a socia, ¿qué pasa con sus clases futuras? Ahora se quedan como están.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Al volver a `member`, el perfil de entrenadora no se borra | Si vuelve a ser entrenadora recupera su bio, y no se borran datos (borrado lógico). |
| El selector solo enseña los roles que la actora puede dar | Evita un 403 seguro. La API sigue comprobando RN-18 y RN-19, el front no es la protección. |
| Cambiar de rol pide confirmación | Es un cambio de permisos; un clic sin querer en el selector no debe aplicarlo. |
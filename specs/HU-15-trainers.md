# HU-15 · Conocer a las entrenadoras

Issue: #70 · Entrega 1 · Tamaño S

## Contexto

> Como visitante quiero ver las entrenadoras y su especialidad para elegir con quién entrenar.

Toca entrenadoras y su perfil público (`trainer_profiles`). Antes no había ninguna página
pública del equipo. Tiene dos partes: el listado público y la pantalla donde cada entrenadora
edita lo que ven las socias. El perfil vacío se crea al pasar a alguien a entrenadora (HU-05).

## Requisitos

1. Cualquiera, sin cuenta, ve las entrenadoras activas con su nombre, especialidad y bio.
2. El listado nunca enseña el email ni el teléfono.
3. Las entrenadoras desactivadas y las personas de otros roles no salen.
4. Una entrenadora cambia su especialidad y su bio, juntas o por separado.
5. El cambio queda en el log con su id.

## Criterios de aceptación

- **Dado** que hay entrenadoras activas, **cuando** abro el listado, **entonces** veo nombre, bio y especialidad, sin email ni teléfono.
- **Dado** una entrenadora desactivada o una socia, **cuando** abro el listado, **entonces** no aparece.
- **Dado** una entrenadora sin perfil, **cuando** abro el listado, **entonces** aparece con especialidad y bio vacías.
- **Dado** que soy trainer, **cuando** edito mi perfil, **entonces** se actualiza mi bio.
- **Dado** que soy trainer, **cuando** envío solo la bio, **entonces** la especialidad no cambia.
- **Dado** que no he iniciado sesión, **cuando** edito un perfil, **entonces** recibo 401.
- **Dado** que soy socia, **cuando** edito un perfil de entrenadora, **entonces** recibo 403.
- **Dado** una especialidad de más de 120 caracteres o una bio de más de 1000, **entonces** recibo 422.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/trainers` | Público | 200 `list[TrainerOut]` | — |
| PATCH | `/trainers/me/profile` | Trainer | 200 `TrainerOut` | 401, 403, 422 |

`TrainerOut`: `id`, `name`, `specialty`, `bio`. Cuerpo del `PATCH`: `TrainerProfileUpdate`
(`specialty`, `bio`, opcionales). No cambia el esquema.

## Interfaz

- **Entrenadoras** (`/entrenadoras`, pública): una cuadrícula de `TrainerCard` con avatar,
  nombre, especialidad y bio. Cada tarjeta lleva a reservar un entrenamiento personal con ella
  (HU-14). Estados: cargando, error ("No hemos podido cargar las entrenadoras") y vacío
  ("Todavía no hay entrenadoras").
- **Mi perfil público** (`/entrenadora/perfil`, solo trainer): una tarjeta como la del diseño, con
  avatar, especialidad y bio, y el botón "Guardar perfil". Al guardar: "Tu perfil se ha guardado.
  Así lo verán las socias."

## Fuera de alcance

- Foto de la entrenadora: se usa el avatar con iniciales.
- Ver la ficha de una sola entrenadora o sus clases.
- Reservar un entrenamiento personal (HU-14).
- Editar nombre, email o teléfono (HU-04).

## Decisiones

| Decisión | Por qué |
| --- | --- |
| `TrainerOut` es un esquema propio, sin email ni teléfono | La lista es pública; así ningún dato de contacto puede salir por error. |
| El nombre sale ya unido (`name`) | La tarjeta solo necesita el nombre completo. |
| Si la entrenadora no tiene perfil, se crea al guardar | Las entrenadoras del seed o de antes de la HU-05 no tenían fila en `trainer_profiles`. |
| Solo se cambian los campos enviados (`exclude_unset`) | Así cambiar la bio no borra la especialidad. |
| Ordenadas por nombre | Un orden estable y fácil de leer. |
| No hay `GET /trainers/me`: la pantalla busca su tarjeta en `GET /trainers` | Evita un endpoint más para un dato que ya es público. |
| "Mi perfil público" se hizo como subtarea aparte (HU-15.4) | La historia no tenía pantalla para la entrenadora y el criterio de editar la bio la necesitaba. |
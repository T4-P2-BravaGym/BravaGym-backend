# HU-17 · Crear rutinas

Issue: #77 · Entrega 1 · Tamaño L · Prioridad P1

## Contexto

> Como entrenadora quiero crear rutinas con ejercicios para una socia para guiar su entrenamiento.

Los modelos `Exercise`, `Routine` y `RoutineExercise` ya existían (HU-01) y la socia
ya podía ver su rutina activa (HU-18), pero nadie podía crearlas. Esta historia
añade el catálogo de ejercicios y la creación de rutinas por parte de la entrenadora,
y la pantalla del editor en el frontend.

Spec escrita durante la implementación: el backend de ejercicios y rutinas ya estaba
mergeado (PR #252) cuando entró la regla de escribir la spec antes de programar.

## Requisitos

1. La entrenadora gestiona un catálogo de ejercicios: crear, ver, editar y borrar.
2. La entrenadora crea una rutina para una socia, con nombre, fecha de inicio, notas
   y sus líneas: día, orden, ejercicio, series, repeticiones y descanso.
3. Una socia tiene como mucho una rutina activa: al crear una nueva, la anterior
   queda inactiva, en la misma operación.
4. La entrenadora puede añadir o quitar líneas de una rutina ya creada y cambiar su
   nombre, fecha o notas.
5. Borrar una rutina la desactiva; no se pierde el histórico.
6. La entrenadora elige la socia de una lista, sin ver sus datos de contacto.

## Reglas

Esta historia estrena estas reglas, que hay que añadir a `docs/business-rules.md`:

- **Una sola rutina activa por socia**: crear una nueva desactiva la anterior.
- **Día y posición únicos**: dentro de una rutina no puede haber dos líneas con el
  mismo día y la misma posición.
- **Un ejercicio en uso no se borra**: si alguna rutina lo usa, el borrado da 409.

## Criterios de aceptación

- **Dado** el catálogo de ejercicios, **cuando** creo una rutina para una socia,
  **entonces** recibo 201 y se guarda con sus líneas (día, orden, series,
  repeticiones y descanso).
- **Dado** dos líneas con el mismo día y posición, **cuando** las guardo,
  **entonces** recibo 409 y no se guarda nada.
- **Dado** que asigno una rutina nueva a una socia, **cuando** se guarda,
  **entonces** la anterior queda inactiva y las rutinas de otras socias no cambian.
- **Dado** una socia que no existe, está desactivada o no tiene rol `member`, o un
  ejercicio que no existe, **cuando** creo la rutina, **entonces** recibo 404.
- **Dado** un día fuera de 1–7, series o repeticiones a 0, o ninguna línea,
  **cuando** creo la rutina, **entonces** recibo 422.
- **Dado** un ejercicio con un nombre que ya existe, **cuando** lo creo,
  **entonces** recibo 409.
- **Dado** un ejercicio que usa alguna rutina, **cuando** lo borro, **entonces**
  recibo 409.
- **Dado** que mando un `trainer_id` en el cuerpo, **cuando** se crea la rutina,
  **entonces** se ignora: la autora sale del token.
- **Dado** que soy socia o admin, **cuando** uso estos endpoints, **entonces**
  recibo 403. Sin token, 401.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/exercises` | Trainer, superadmin | 200 `list[ExerciseOut]` | 401, 403 |
| GET | `/exercises/{id}` | Trainer, superadmin | 200 `ExerciseOut` | 401, 403, 404 |
| POST | `/exercises` | Trainer, superadmin | 201 `ExerciseOut` | 401, 403, 409, 422 |
| PATCH | `/exercises/{id}` | Trainer, superadmin | 200 `ExerciseOut` | 401, 403, 404, 409, 422 |
| DELETE | `/exercises/{id}` | Trainer, superadmin | 204 | 401, 403, 404, 409 |
| POST | `/routines` | Trainer, superadmin | 201 `TrainerRoutineOut` | 401, 403, 404, 409, 422 |
| GET | `/routines?member_id=` | Trainer, superadmin | 200 `list[TrainerRoutineOut]` | 401, 403 |
| GET | `/routines/{id}` | Trainer, superadmin | 200 `TrainerRoutineOut` | 401, 403, 404 |
| PATCH | `/routines/{id}` | Trainer, superadmin | 200 `TrainerRoutineOut` | 401, 403, 404, 422 |
| DELETE | `/routines/{id}` | Trainer, superadmin | 204 (desactiva) | 401, 403, 404 |
| POST | `/routines/{id}/exercises` | Trainer, superadmin | 201 `TrainerRoutineOut` | 401, 403, 404, 409, 422 |
| DELETE | `/routines/{id}/exercises/{item_id}` | Trainer, superadmin | 204 | 401, 403, 404 |
| GET | `/users/members` | Trainer, superadmin | 200 `list[MemberOption]` | 401, 403 |

Entrada: `RoutineCreate` con `member_id`, `name`, `start_date`, `notes` y `lines`,
y cada línea `RoutineLineIn` con `exercise_id`, `day_number`, `position`, `sets`,
`reps` y `rest_seconds` (60 por defecto). Salida: `TrainerRoutineOut`, que es el
`RoutineOut` de la HU-18 más `member_id` e `is_active`.

Tablas que se tocan: `exercises`, `routines` y `routine_exercises`. Sin cambios de
esquema: el `UNIQUE(routine_id, day_number, position)` ya existía.

## Interfaz

- Página `/entrenadora/rutinas` (`TrainerRoutines`), que carga socias y ejercicios
  y monta el componente `RoutineEditor`, que ya existía.
- El editor elige socia, nombre, fecha de inicio y días con pestañas, y en cada día
  las líneas con ejercicio, series, repeticiones y descanso. Numera las posiciones
  solo, así que desde la pantalla no se puede repetir día y posición.
- Estados a mostrar: carga, error al cargar, guardando, error de la API y rutina
  guardada.

## Fuera de alcance

- Ver la rutina como socia → HU-18.
- Pantalla para gestionar el catálogo de ejercicios: el CRUD existe en la API, pero
  esta historia solo usa el listado.
- Editar una línea concreta (`PATCH` de una línea): se quita y se vuelve a añadir.
- Que una entrenadora solo vea las rutinas de sus socias: cualquier entrenadora ve
  y edita todas, como dice `docs/api.md`.

## Preguntas abiertas

- ¿Hace falta la pantalla del catálogo de ejercicios en la entrega 2?
- Dos rutinas creadas a la vez para la misma socia podrían quedar activas las dos:
  no hay restricción en la base de datos que lo impida. ¿Se añade?

## Decisiones

| Decisión | Por qué |
| --- | --- |
| `trainer_id` sale del token, nunca del cuerpo | Evita la asignación masiva: nadie puede firmar rutinas en nombre de otra entrenadora. |
| Desactivar la rutina anterior y crear la nueva en un solo commit | Si algo falla, la socia conserva su rutina anterior. |
| Validar socia, ejercicios y posiciones antes de escribir nada | Un error a mitad no deja la base de datos a medias. |
| El 409 por día y posición se comprueba en el servicio y con el `UNIQUE` de la tabla | El servicio da un mensaje claro y el `UNIQUE` es la última barrera. |
| Las líneas devuelven su `id`; se ajustó el test de la HU-18 | El editor lo necesita para borrar una línea. |
| `TrainerRoutineOut` hereda de `RoutineOut` | Reutiliza la vista de la socia (DRY) y añade solo lo que necesita la entrenadora. |
| Endpoint nuevo `GET /users/members` con solo `id`, `first_name` y `last_name` | `GET /users` es solo para admin y devuelve email y teléfono; la entrenadora necesita elegir socia sin ver sus datos de contacto. |
| Servicio de ejercicios separado (`exercise_service.py`) | Responsabilidad única: el catálogo y las rutinas cambian por motivos distintos. |
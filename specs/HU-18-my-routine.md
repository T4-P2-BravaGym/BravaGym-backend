# HU-18 · Ver mi rutina

Issue: #81 · Entrega 1 · Tamaño S

## Contexto

> Como socia quiero ver mi rutina activa para saber qué toca cada día.

Toca rutinas. Las rutinas las crea la entrenadora (HU-17); esta historia es la parte de la
socia: ver la que tiene activa, agrupada por día. Se hizo antes que la HU-17, con rutinas del
seed.

## Requisitos

1. Una socia ve su rutina activa: nombre, entrenadora, fecha de inicio, notas y ejercicios.
2. Los ejercicios salen agrupados por día y, dentro de cada día, en orden.
3. Cada ejercicio muestra series, repeticiones y descanso.
4. Solo ve su rutina activa, nunca una antigua ni la de otra socia.
5. Si no tiene rutina, recibe un mensaje amable en vez de un error.

## Criterios de aceptación

- **Dado** que tengo una rutina activa, **cuando** abro "Mi rutina", **entonces** veo los ejercicios agrupados por día y en orden.
- **Dado** que tengo una rutina antigua y una activa, **cuando** la pido, **entonces** solo veo la activa.
- **Dado** que no tengo rutina, **cuando** la pido, **entonces** recibo 404 con un mensaje amable.
- **Dado** que otra socia tiene rutina, **cuando** pido la mía, **entonces** nunca veo la suya.
- **Dado** que no he iniciado sesión, **cuando** pido `/routines/me`, **entonces** recibo 401.
- **Dado** que soy entrenadora, **cuando** pido `/routines/me`, **entonces** recibo 403.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/routines/me` | Member | 200 `RoutineOut` | 401, 403, 404 |

`RoutineOut`: `id`, `name`, `trainer_name`, `start_date`, `notes` y `days`, cada día con su
`day_number` y sus `lines` (`position`, `exercise_name`, `sets`, `reps`, `rest_seconds`).
No cambia el esquema.

## Interfaz

"Mi rutina" (`/mi-area/rutina`): título con "por <entrenadora> · desde el <fecha>" y una
pestaña por día (`Tabs`, "Día 1", "Día 2"…). Cada pestaña lista sus ejercicios con
`ExerciseRow`. Estados: cargando, error ("No hemos podido cargar tu rutina") y vacío
("Todavía no tienes rutina · Tu entrenadora te la preparará pronto"), que se usa con el 404.

## Fuera de alcance

- Crear o editar rutinas (HU-17).
- Marcar ejercicios como hechos o llevar un registro de pesos.
- Ver rutinas antiguas.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| La API devuelve los días ya agrupados (`days`) | La pantalla solo los pinta; la agrupación está probada en el backend. |
| Las líneas se ordenan por día y posición antes de agrupar | `groupby` solo agrupa elementos seguidos; sin ordenar, un día podía salir partido. |
| La socia sale del token, nunca de la URL | No hay forma de pedir la rutina de otra (IDOR). |
| Sin rutina es 404 con mensaje, y el front lo muestra como estado vacío | No tener rutina es normal, no un error. |
| En el front, una pestaña por día como en el diseño | Una rutina de varios días en una sola lista era larga de leer en el móvil. |
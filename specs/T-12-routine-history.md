# T-12 · Historial de rutinas de una socia

Issue: #311 · Entrega 2 · Tamaño M

## Contexto

> Como entrenadora quiero consultar todas las rutinas que le he puesto a una socia para ver su evolución y no perder lo que ya funcionó.

Toca rutinas (HU-17 y HU-18). Hoy la entrenadora crea la rutina en el editor, pero no
tiene ninguna pantalla para volver a verla. Al crear una rutina nueva, la anterior queda
inactiva y no se borra, así que el historial ya está en la base de datos y
`GET /routines?member_id=` ya lo devuelve. Falta la pantalla, el orden por fecha y
evitar el N+1 del listado.

## Requisitos

1. La entrenadora elige una socia y ve todas sus rutinas, de la más reciente a la más antigua.
2. Cada rutina muestra nombre, fecha de inicio, entrenadora y si está activa o inactiva.
3. Al abrir una rutina se ven sus ejercicios por día y en orden, igual que en "Mi rutina".
4. Una socia sin rutinas ve un mensaje amable, no una lista vacía.
5. Las socias no pueden consultar el historial.

## Criterios de aceptación

- **Dado** una socia con varias rutinas, **cuando** pido `GET /routines?member_id=`, **entonces** recibo 200 con todas, ordenadas por `start_date` descendente y, si empatan, por `id` descendente.
- **Dado** el listado, **cuando** filtro por una socia, **entonces** no aparecen rutinas de otras socias.
- **Dado** una socia sin rutinas, **cuando** pido su historial, **entonces** recibo 200 con `[]` y la pantalla muestra un mensaje amable.
- **Dado** que acabo de crear una rutina nueva, **cuando** abro el historial de esa socia, **entonces** la nueva aparece activa y la anterior inactiva.
- **Dado** que soy socia, **cuando** llamo a `GET /routines`, **entonces** recibo 403; sin sesión, 401.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/routines?member_id=` | Trainer, Superadmin | 200 `list[TrainerRoutineOut]` | 401, 403 |
| GET | `/routines/{routine_id}` | Trainer, Superadmin | 200 `TrainerRoutineOut` | 401, 403, 404 |

Los dos endpoints ya existen. Solo cambia el orden del listado y cómo se cargan las
relaciones (`selectinload`). Sin cambios de esquema ni migración.

## Interfaz

- "Rutinas" de la entrenadora pasa a tener dos pestañas: "Nueva rutina" (el editor actual) e "Historial".
- Historial: selector de socia, lista de tarjetas (nombre, fecha, entrenadora, etiqueta Activa/Inactiva) y detalle de la rutina al pulsar una tarjeta.
- El detalle usa `RoutineDays`, que se saca de `MyRoutine` para no repetir código.
- Estados: cargando, vacío (socia sin rutinas), error con el mensaje de la API.

## Fuera de alcance

- Que la socia vea su propio historial.
- Duplicar una rutina antigua como plantilla.
- Que cada entrenadora vea solo las rutinas que creó: de momento todas ven todas.
- Editar o reactivar rutinas antiguas desde el historial.

## Preguntas abiertas

- ¿Cada entrenadora debería ver solo sus rutinas? Se decide con el equipo; si cambia, va en otra tarea.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Orden por start_date desc y id desc | El historial se lee por fecha; el id solo desempata rutinas del mismo día. |
| selectinload en el listado | Evita el N+1: el número de consultas no crece con el número de rutinas. |
| Sin test para el N+1 | 	Contar consultas en un test sería frágil; se comprueba revisando el código. |
| RoutineHistory recibe las socias como prop | 	como prop	TrainerRoutines ya las carga para el editor; no se piden dos veces. |
| El editor se oculta con hidden y el historial se monta al abrirlo | 	Una rutina a medio escribir no se pierde al cambiar de pestaña, y el historial siempre carga datos nuevos. |


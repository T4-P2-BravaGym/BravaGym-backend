# HU-10 · Ver el horario de clases

Issue: #49 · Entrega 1 · Tamaño M · Prioridad P1

## Contexto

> Como visitante o socia quiero ver las clases de la semana con sus plazas libres para elegir horario.

Antes no había un listado público de sesiones. Esta historia abre el calendario
que usan luego la reserva (HU-12), el entrenamiento personal (HU-14) y la
gestión de la entrenadora (HU-11).

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. Cualquiera puede ver las sesiones programadas en un rango de fechas.
2. Cada sesión muestra las plazas libres calculadas (capacidad menos reservas
   `confirmed`), nunca una columna guardada.
3. Se puede filtrar para ocultar las sesiones llenas.
4. Si la clase tiene precio extra, ese precio se ve en el listado.
5. El listado está paginado.

## Reglas

- Las plazas libres se calculan en la consulta; no se persisten.
- Solo se listan sesiones `scheduled` (las `cancelled` no salen en el horario
  público).
- Filtros opcionales: `from` / `to`, `class_type_id`, `trainer_id`,
  `only_available`.

## Criterios de aceptación

- **Dado** un rango de fechas, **cuando** pido `GET /sessions?from=&to=`,
  **entonces** veo las sesiones programadas con plazas libres calculadas.
- **Dado** `only_available=true`, **cuando** filtro, **entonces** no aparecen
  sesiones llenas.
- **Dado** una clase con precio extra, **cuando** la veo, **entonces** se
  muestra su `extra_price_cents` en el tipo de clase anidado.
- **Dado** `from` posterior a `to`, **cuando** consulto, **entonces** recibo 422.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/sessions` | Público | 200 `SessionPage` | 422 |

Query: `from`, `to`, `class_type_id`, `trainer_id`, `only_available`, `page`,
`size`. Salida: `SessionOut` con `free_spots` y `class_type` (incluye
`extra_price_cents`). Sin cambios de esquema: el conteo es una subquery.

## Interfaz

- Página de horario / clases de la semana con filtros de fecha y disponibilidad.
- Cada tarjeta muestra plazas libres y, si aplica, el precio extra.
- Estados: vacío (sin sesiones en el rango), carga y error de red.

## Fuera de alcance

- Crear o editar sesiones → HU-11.
- Reservar plaza → HU-12.
- Franjas de entrenamiento personal → HU-14.
- Actualización en vivo por websocket → HU-16.

## Preguntas abiertas

Ninguna: la historia está mergeada en `dev`.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| `free_spots` se calcula en SQL (capacidad − confirmed), no se guarda | Evita desincronizar al reservar/cancelar; el AC lo pide explícitamente |
| Solo sesiones `scheduled` en el listado público | Una cancelada no es horario útil |
| `only_available` excluye `free_spots = 0` | El AC pide ocultar las llenas, no las de lista de espera |
| Paginación común `{items, total, page, size}` | Misma forma que el resto de listados (HU-06.1) |

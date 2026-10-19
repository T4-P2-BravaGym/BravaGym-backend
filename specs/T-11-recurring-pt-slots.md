# T-11 · Franjas semanales de entrenamiento personal

Issue: #310 · Entrega 2 · Tamaño M · Prioridad P2

## Contexto

> Como entrenadora quiero abrir mis franjas de entrenamiento personal con un horario semanal (por ejemplo, lunes, miércoles y viernes a las 11:00) para no tener que crearlas una a una.

HU-14 permite abrir franjas sueltas con `POST /sessions/personal-training`. Para un
horario fijo, la entrenadora tendría que repetir la operación cada día y cada semana.
Lo detectó Damaris al conectar la pantalla de franjas en el front.

## Requisitos

1. La entrenadora elige días de la semana, una o varias horas de inicio, una fecha de
   inicio y un número de semanas, y se crean todas las franjas de una vez.
2. Las horas se interpretan en horario de Madrid (`Europe/Madrid`), también cuando
   el periodo cruza un cambio de hora.
3. Cada franja cumple RN-08 (60 minutos, aforo 1, tipo PT) y RN-09 (sin solapes).
4. Las franjas que no se pueden crear no bloquean el resto: se devuelven aparte con
   el motivo.
5. Todo se guarda en una sola transacción.

## Reglas

- **RN-08** y **RN-09** como en HU-14.
- Una franja que empieza antes de ahora se salta con motivo `past`.
- Una franja que se solapa con una sesión programada de la entrenadora, o con otra
  franja del mismo lote, se salta con motivo `overlap`.
- Límites: de 1 a 7 días, de 1 a 4 horas y de 1 a 8 semanas.

## Criterios de aceptación

- **Dado** que soy trainer, **cuando** pido lunes, miércoles y viernes a las 11:00
  durante 2 semanas, **entonces** se crean 6 franjas de 60 minutos y aforo 1.
- **Dado** un periodo que cruza el cambio de hora, **cuando** creo franjas a las 11:00,
  **entonces** todas empiezan a las 11:00 en Madrid (09:00 UTC en verano, 10:00 UTC en invierno).
- **Dado** que ya tengo una clase que se solapa, **cuando** creo el lote, **entonces**
  esa franja aparece en `skipped` con `overlap` y el resto se crea.
- **Dado** que una franja cae en el pasado, **entonces** aparece en `skipped` con `past`.
- **Dado** que soy member, **cuando** llamo al endpoint, **entonces** recibo 403.
- **Dado** que no hay tipo PT activo, **entonces** recibo 404 y no se crea nada.
- **Dado** un `class_type_id` que no es de PT o datos fuera de límites, **entonces** recibo 422.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/sessions/personal-training/bulk` | Trainer | 201 `PersonalTrainingSlotBulkOut` | 401, 403, 404, 422 |

Entrada `PersonalTrainingSlotBulkCreate`: `weekdays` (0 = lunes … 6 = domingo),
`times` (`HH:MM`, Madrid), `start_date`, `weeks`, opcional `class_type_id`.
Salida: `created` (lista de `SessionOut`) y `skipped` (`starts_at` en UTC y `reason`).
Sin cambios de esquema ni migración.

## Interfaz

- En "Entrenamiento personal" de la entrenadora: formulario semanal con días, horas,
  fecha de inicio y semanas, y un resumen de lo creado y lo saltado.
- Se mantiene la opción de abrir una franja suelta.

## Fuera de alcance

- Guardar la disponibilidad como plantilla y generar franjas automáticamente.
- Editar o cancelar en bloque.

## Preguntas abiertas

Ninguna.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Endpoint en bloque en vez de N llamadas desde el front | Una transacción, una validación y la conversión horaria en el servidor |
| Saltar en vez de fallar todo con 409 | Lo habitual es que choque una franja suelta; la entrenadora ve cuál y sigue |
| Horas en `Europe/Madrid` y conversión con `zoneinfo` | El cambio de hora de octubre y marzo no desplaza las franjas |
| Comprobar solapes en memoria con una sola consulta | Evita N consultas y detecta solapes dentro del mismo lote |
| Límite de 8 semanas y 4 horas | Evita lotes enormes por error |
| `tzdata` en requirements | En Windows Python no trae la base de zonas horarias |
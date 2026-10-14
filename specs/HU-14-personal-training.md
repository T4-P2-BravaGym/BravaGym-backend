# HU-14 · Reservar entrenamiento personal

Issue: #66 · Entrega 1 · Tamaño M · Prioridad P1

## Contexto

> Como socia con plan de entrenamiento personal quiero elegir entrenadora y una franja de una hora para entrenar a solas con ella.

Las reservas genéricas (HU-12) ya existían. El entrenamiento personal exige un
tipo de clase marcado, aforo 1, duración 60 minutos y un plan con
`includes_personal_training`. La entrenadora abre franjas; la socia reserva con
el mismo flujo de booking.

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. La entrenadora puede crear franjas de entrenamiento personal de 60 minutos y
   aforo 1.
2. Solo las socias cuyo plan incluye entrenamiento personal pueden reservarlas.
3. El horario se puede filtrar por `trainer_id` para ver solo las franjas de una
   entrenadora.
4. Las reglas de solape de la entrenadora (RN-09) siguen aplicando al crear
   franjas.
5. Reservar una franja libre usa el mismo endpoint de booking que una clase
   grupal.

## Reglas

- **RN-08**: sesión de un tipo con `is_personal_training = true`, `capacity = 1`
  y 60 minutos. Solo la reservan socias cuyo plan tiene
  `includes_personal_training` → si no, 403.
- **RN-01** a **RN-04**, **RN-07** y **RN-09** aplican igual que en HU-12 / HU-11.

## Criterios de aceptación

- **Dado** que mi plan incluye entrenamiento personal, **cuando** reservo una
  franja libre, **entonces** queda `confirmed`.
- **Dado** que mi plan no lo incluye, **cuando** reservo, **entonces** recibo
  403.
- **Dado** que elijo una entrenadora, **cuando** filtro por `trainer_id`,
  **entonces** solo veo sus franjas.
- **Dado** que soy trainer, **cuando** creo una franja que se solapa con otra
  mía, **entonces** recibo 409 (RN-09).
- **Dado** un `class_type_id` que no es de PT, **cuando** creo la franja,
  **entonces** recibo 422.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/sessions/personal-training` | Trainer | 201 `SessionOut` | 401, 403, 404, 409, 422 |
| GET | `/sessions?trainer_id=` | Público | 200 `SessionPage` | 422 |
| POST | `/sessions/{id}/bookings` | Member | 201 `BookingOut` | 401, 403, 404, 409 |

Entrada de creación: `PersonalTrainingSlotCreate` (`starts_at`, opcional
`class_type_id`). Si no se pasa tipo, se usa el tipo PT activo por defecto.

## Interfaz

- Perfil / listado de entrenadoras y sus franjas libres.
- Botón de la entrenadora para abrir huecos de 1 h.
- Reserva desde el horario filtrado; mensaje 403 si el plan no incluye PT.

## Fuera de alcance

- Contratar el plan que incluye PT → HU-09.
- Perfil público enriquecido de la entrenadora (bio, foto) → subtareas FE
  aparte.
- Cobro específico distinto del de clase extra → mismo flujo de pagos HU-24.

## Preguntas abiertas

Ninguna: la historia está mergeada en `dev`.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Endpoint dedicado `POST /sessions/personal-training` | Fija capacity=1 y 60 min en servidor; la trainer no puede mandar otros valores |
| Reutilizar `POST /sessions/{id}/bookings` para reservar | Misma máquina de estados; RN-08 es un gate extra en el servicio |
| Resolver el class type PT activo si no viene en el body | Menos fricción al abrir franjas cuando solo hay un tipo PT |
| Filtro `trainer_id` en GET `/sessions` (HU-10) | Cumple el AC sin un endpoint nuevo |

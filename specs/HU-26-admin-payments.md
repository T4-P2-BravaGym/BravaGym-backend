# HU-26 · Gestión de pagos y exportación CSV

Issue: #108 · Entrega 1 · Tamaño M · Prioridad P1

## Contexto

> Como administración quiero revisar y exportar los pagos para llevar la contabilidad.

Tras el pago de la socia (HU-24), administración necesita el listado completo,
filtros, exportación CSV y marcar un pago `paid` como `refunded`.

Spec escrita a posteriori, a partir de la issue y de la PR.

## Requisitos

1. Administración lista todos los pagos con filtros y paginación.
2. Puede exportar el mismo filtro a CSV (cabecera + una fila por pago).
3. Puede marcar un pago `paid` como `refunded`; el cambio queda en el log.
4. Los importes van siempre en céntimos.
5. Member / trainer no acceden a estos endpoints.

## Reglas

- **RN-16**: solo administración puede marcar un pago `refunded`. Un pago que no
  está `paid` no se reembolsa → 409.

## Criterios de aceptación

- **Dado** pagos de varios estados, **cuando** filtro por `status` y fechas,
  **entonces** veo solo esos, paginados.
- **Dado** los mismos filtros, **cuando** exporto, **entonces** descargo un CSV
  con cabecera y una fila por pago.
- **Dado** un pago `paid`, **cuando** lo marco como `refunded`, **entonces**
  queda registrado en el log.
- **Dado** un pago `pending` o ya `refunded`, **cuando** intento el refund,
  **entonces** recibo 409.
- **Dado** que soy member, **cuando** llamo a estos endpoints, **entonces**
  recibo 403.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/payments` | Admin, superadmin | 200 `PaymentPage` | 401, 403, 422 |
| GET | `/payments/export` | Admin, superadmin | 200 `text/csv` | 401, 403, 422 |
| POST | `/payments/{id}/refund` | Admin, superadmin | 200 `PaymentOut` | 401, 403, 404, 409 |

Filtros compartidos listado/export: `status`, `from`, `to`, `user_id`,
`concept` (`subscription` \| `booking` \| `order`). El export no pagina.
CSV vía `csv` + `StreamingResponse`, charset UTF-8,
`Content-Disposition: attachment; filename="payments.csv"`.

## Interfaz

- Pantalla admin de pagos con filtros y botón Exportar CSV.
- Acción Reembolsar en pagos `paid`.
- Estados: vacío, rango de fechas inválido (422), ya reembolsado (409).

## Fuera de alcance

- Pago de la socia → HU-24.
- Stripe / pasarela real → HU-29.
- Contabilidad externa o asientos contables.

## Preguntas abiertas

Ninguna: la historia está mergeada en `dev`.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Mismos filtros en list y export; export sin paginar | El AC pide "los mismos filtros" y un CSV completo |
| `concept` derivado de FKs, no columna | Evita desincronizar; subscription/booking/order son mutuamente excluyentes en la práctica |
| Módulo `csv` de la stdlib + StreamingResponse | Sin dependencia nueva; encaja con archivos medianos de la entrega |
| Log en cada refund | DoD: auditoría de operaciones que cambian datos |

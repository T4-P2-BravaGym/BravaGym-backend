# HU-07 · Página de pricing

Issue: #38 · Entrega 1 · Tamaño S

## Contexto

> Como visitante quiero ver los planes y sus precios para decidir cuál contratar.

Esta spec documenta retrospectivamente la historia implementada en backend PR #141 y frontend PR #41. El listado público conecta la página de precios con los planes existentes, sin exigir una sesión. Las subtareas backend son #39, #40 y #41; la del frontend es #6.

## Requisitos

1. Cualquier visitante puede consultar los planes sin iniciar sesión.
2. Solo se muestran planes activos, ordenados por precio ascendente.
3. Cada plan muestra su nombre, descripción si existe, precio mensual en euros e indicación de entrenamiento personal cuando lo incluye.
4. El precio se guarda en céntimos enteros y se presenta con dos decimales.
5. La pantalla muestra estados de carga, error y ausencia de planes.
6. La página reutiliza `PricingCard` y adapta la distribución al tamaño de pantalla.

## Reglas

`docs/business-rules.md` no asigna una RN específica al listado público de planes. Los criterios de #38 y `AGENTS.md` establecen que solo se ofrece el catálogo activo y que el dinero se representa en céntimos enteros, nunca con `float`.

## Criterios de aceptación

- **Dado** que hay planes activos e inactivos, **cuando** abro pricing, **entonces** solo veo los activos, ordenados por precio.
- **Dado** un plan con entrenamiento personal, **cuando** lo veo, **entonces** se indica claramente.
- **Dado** que no he iniciado sesión, **cuando** consulto `/api/v1/plans`, **entonces** recibo 200 con el catálogo público.
- **Dado** que no existen planes activos, **cuando** consulto el endpoint, **entonces** recibo una lista vacía y la pantalla muestra el mensaje de ausencia de planes.
- **Dado** un precio de 5990 céntimos, **cuando** se devuelve el plan, **entonces** `monthly_price_formatted` es `59,90 €`.
- **Dado** que la petición está pendiente, **cuando** abro la pantalla, **entonces** se muestra el estado de carga.
- **Dado** que falla la petición, **cuando** termina, **entonces** aparece un mensaje de error en español.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/plans` | Público, sin token | 200 lista de `PlanOut` | Sin errores de autenticación; la interfaz contempla fallos de red o servidor |

`PlanOut` devuelve `id`, `name`, `description`, `monthly_price_cents`, `includes_personal_training` y `monthly_price_formatted`. El endpoint tiene summary, tag y ejemplo Swagger. Esta historia utiliza el modelo de planes existente; esta documentación no cambia tablas ni requiere migración.

## Interfaz

La página pública `Pricing` pide los datos a `listPlans` en `services/plans.js` y monta las tarjetas con `PricingCard`. Muestra `Cargando planes…`, un error con `role="alert"` o el mensaje de catálogo vacío. Cada tarjeta enlaza al registro. Los estilos de la página usan CSS Modules y una distribución responsive.

## Fuera de alcance

- Crear, editar o retirar planes: HU-08.
- Contratar un plan y crear una suscripción: HU-09.
- La caché de respuestas incorporada posteriormente: HU-28.
- Tests de 401, 403 e IDOR para este listado: es público y no contiene recursos privados de una socia.

## Preguntas abiertas

- Ninguna sobre el comportamiento descrito. La documentación retrospectiva necesita revisión humana antes de merge.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Mantener público el listado | Permitir comparar planes antes del registro. |
| Filtrar activos y ordenar en el backend | Ofrecer el mismo catálogo y orden a todos los clientes. |
| Formatear el precio a partir de céntimos enteros | Evitar errores de precisión con dinero. |
| Reutilizar `PricingCard` | Mantener el diseño existente sin duplicar componentes. |
| Una spec en el backend para ambos repos | Seguir `specs/README.md`. |

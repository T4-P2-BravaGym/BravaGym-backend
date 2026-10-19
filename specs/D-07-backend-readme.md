# D-07 · README backend de entrega

Issue: #284 · Parent: #200 · Entrega 2 · Tamaño S

## Contexto

Como equipo queremos que la profesora pueda instalar y probar la API y encontrar los documentos de entrega desde el README. La instalación del frontend se mantiene en su repositorio y en #283.

## Requisitos

1. Explicar instalación local, configuración, Alembic, seed y primer uso de Swagger a partir del código de `dev`.
2. Enlazar Swagger, ReDoc, OpenAPI, Bruno, specs, bitácora de IA y diagrama ER.
3. Identificar la retrospectiva, Docker y la URL desplegada con su estado real y tareas responsables; no inventar archivos, comandos operativos ni URLs.
4. Documentar los controles de calidad existentes y la persistencia de SQLite y fotos.

## Criterios de aceptación

- Dado el repositorio backend, cuando se sigue la guía con sus dependencias instaladas, entonces las migraciones y el seed funcionan sobre una base temporal y la API expone health, Swagger y ReDoc.
- Dado el índice de documentación, cuando se siguen enlaces a archivos del repositorio, entonces esos archivos existen.
- Dadas las dependencias de entrega no publicadas, cuando se consulta el README, entonces aparecen como pendientes enlazadas a sus tareas.
- Dada la tarea frontend #283, cuando se consulta esta guía, entonces remite al README frontend sin duplicar sus instrucciones.

## Fuera de alcance

- Implementar Docker (HU-27), desplegar (HU-36), redactar la retrospectiva del equipo o editar el README frontend.
- Cambiar código, dependencias, frameworks o tests.

## Preguntas abiertas

- Publicación de la retrospectiva: seguimiento en #200.
- Integración de Docker y URL pública: seguimiento en #112, #115 y #185.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Python 3.12 como versión de referencia | Coincide con CI. |
| Cambios sobre `origin/dev` en una rama de documentación independiente | Evita incluir HU-35, que todavía está en revisión. |
| Dependencias pendientes visibles | La documentación no puede prometer entregables que no existen en `dev`. |

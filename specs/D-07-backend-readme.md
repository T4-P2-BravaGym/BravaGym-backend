# D-07 · README backend de entrega

Issue: T4-P2-BravaGym/BravaGym-backend#284 · Parent: #200 · Entrega 2 · Tamaño S

## Contexto

El equipo revisó la documentación el 19 de octubre y pidió un README breve del producto, en inglés, en cada repositorio. Las instrucciones de la revisión sustituyen el índice extenso de historias y entregables pendientes de la primera versión.

## Requisitos

1. Describir Brava, sus funciones principales y la relación entre frontend y backend.
2. Mostrar tecnologías y versiones verificadas en dependencias y CI.
3. Explicar requisitos, instalación local, configuración y primer uso con cuentas ficticias.
4. Incluir un árbol breve de carpetas, comandos de calidad, autoras y enlace a Issues.
5. Enlazar el README del otro repositorio y documentación técnica existente.
6. Omitir Docker/despliegue, pendientes de entrega y narración de historias del README; conservar la guía operativa de Bruno fuera del README backend.
7. No atribuir una licencia que no exista en el repositorio.

## Criterios de aceptación

- El README está en inglés, es fácil de recorrer y permite iniciar el proyecto localmente.
- Las versiones, rutas, variables, credenciales ficticias y comandos coinciden con el código integrado en dev.
- Los enlaces relativos apuntan a archivos existentes y ambos repositorios se enlazan entre sí.
- La guía frontend indica que la API debe estar arrancada y usar un origen compatible para cookies/CORS.
- La guía backend configura una clave privada, aplica migraciones y limita el seed a una base local vacía.

## Fuera de alcance

Cambiar código, dependencias, tests, infraestructura o integrar funcionalidades pendientes.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Un README en inglés por repositorio | Acuerdo explícito de la revisión del equipo. |
| Rama de documentación creada desde origin/dev | Describir el producto integrado y separar la documentación de las ramas funcionales. |
| Detalles en enlaces y guía de Bruno separada | Mantener una portada breve sin perder instrucciones operativas de API. |

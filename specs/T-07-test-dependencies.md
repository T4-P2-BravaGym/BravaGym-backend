# T-07 · Sacar las dependencias de test de requirements.txt

Issue: #192 · Entrega 2 · Tamaño S · Prioridad P2

## Contexto

> Como equipo quiero separar las dependencias de pruebas de las de ejecución para que la imagen de Docker no instale herramientas de test innecesarias.

`requirements.txt` termina con `pytest` y `freezegun`, que ya están declarados en `requirements-dev.txt`. La tarea se realiza antes de HU-27 y mantiene disponible el entorno de desarrollo completo.

## Requisitos

1. Quitar las declaraciones directas de `pytest` y `freezegun` de `requirements.txt`.
2. Conservar ambas herramientas en `requirements-dev.txt`, junto con la inclusión de `requirements.txt`.
3. Dejar un salto de línea final en `requirements.txt`.
4. Comprobar instalación del entorno de desarrollo y ejecución de las pruebas existentes.

## Criterios de aceptación

- **Dado** `requirements.txt`, **cuando** reviso sus dependencias, **entonces** no declara `pytest` ni `freezegun` y termina con un salto de línea.
- **Dado** `requirements-dev.txt`, **cuando** lo instalo, **entonces** se instalan las dependencias de ejecución y de pruebas.
- **Dado** el entorno de desarrollo instalado, **cuando** ejecuto `pytest`, **entonces** las pruebas existentes pasan sin modificarlas.

## Interfaz

Sin interfaz. No cambian endpoints, modelos ni migraciones.

## Fuera de alcance

- Crear la imagen Docker o cambiar su configuración: HU-27.
- Cambiar versiones o reorganizar otras dependencias.
- Modificar tests o reducir el umbral de cobertura.

## Preguntas abiertas

- Ninguna.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Mantener intacto `requirements-dev.txt` | Ya incluye las dos herramientas y las dependencias de ejecución. |
| Validar con la suite existente | La tarea cambia instalación, no comportamiento de la aplicación. |

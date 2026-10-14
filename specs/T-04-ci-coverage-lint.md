# T-04 · Calidad en CI: cobertura ≥ 80 % y lint

Issue: #189 · Entrega 2 · Tamaño S · Prioridad P2

## Contexto

Nivel avanzado del README: lint y tests en cada PR, con cobertura mínima del
80 %. Antes CI corría pytest sin umbral de cobertura ni ruff; el frontend no
tenía ESLint en el workflow y el `build.yml` escuchaba la rama `develop` en
lugar de `dev`.

Spec escrita a posteriori, a partir de la issue y de las PR de backend y
frontend.

## Requisitos

1. El workflow de tests del backend falla si la cobertura de `app` baja del 80 %.
2. Cada PR/push a `main`/`dev` ejecuta `ruff check` y `ruff format --check`.
3. El frontend tiene ESLint con plugin de React, script `npm run lint` y un paso
   en `build.yml`.
4. El frontend dispara CI en `[main, dev]` (ya no `develop`).

## Reglas

- No aplica RN de negocio: es tarea técnica de calidad.
- El umbral de cobertura se fija tras medir; el gate es `--cov-fail-under=80`.

## Criterios de aceptación

- **Dado** un push o PR al backend, **cuando** corre Actions, **entonces**
  ejecuta ruff (check + format --check) y pytest con cobertura ≥ 80 %.
- **Dado** cobertura por debajo del umbral, **cuando** corre CI, **entonces** el
  job falla.
- **Dado** un push o PR al frontend, **cuando** corre `build.yml`, **entonces**
  ejecuta `npm run lint` antes del build y escucha ramas `main` y `dev`.

## Endpoints

Sin endpoints. Archivos tocados:

| Repo | Qué |
| --- | --- |
| Backend | `requirements-dev.txt` (`pytest-cov`, `ruff`), `pyproject.toml`, `pytest.ini`, `.github/workflows/tests.yml` |
| Frontend | `eslint.config.js`, `package.json` (`lint`), `.github/workflows/build.yml` |

## Interfaz

Sin interfaz.

## Fuera de alcance

- Subir el umbral por encima del 80 %.
- Sustituir ruff por otro linter o ESLint flat por la config legacy.
- Arreglar o formatear a la fuerza los ficheros de HU-28 / pagos que se
  excluyeron temporalmente en `extend-exclude` para no pelear con PRs abiertas
  (se pueden limpiar en una tarea aparte).

## Preguntas abiertas

- ¿Quitar el `extend-exclude` de ruff sobre caché/pagos ahora que HU-28 y HU-24
  están en `dev`? Conviene en una PR de estilo dedicada.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Gate en 80 % tras medir (~96 % en `dev`) | Cumple el AC sin castigar el repo; margen para código nuevo |
| Ruff en el mismo job que pytest | Un solo workflow `tests`; fallo temprano de estilo |
| Ignorar `B008` / `UP046` en ruff | FastAPI usa `Depends()` en defaults; UP046 rompería genéricos Pydantic |
| `extend-exclude` de zonas HU-28/pagos | Anti-conflicto con PRs abiertas al implementar T-04 |
| FE: ESLint flat + `eslint-plugin-react` | Stack Vite/React actual; script `npm run lint` reutilizable en local |
| Corregir `develop` → `dev` dentro de T-04 | Solapa con #234; se hace una sola vez |

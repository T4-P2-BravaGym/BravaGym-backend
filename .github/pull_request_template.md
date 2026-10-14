## What

<!-- One or two sentences, in English. -->

Closes #

Spec: specs/HU-XX-nombre.md
AI: herramienta y modelo, o "ninguno"

## Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] If a model changed: the migration is included and `alembic check` passes
- [ ] Permission tests: 401 without token, 403 with the wrong role, 404 for another member's resource
- [ ] Error path tested (invalid data gives 422, never 500)
- [ ] Endpoint documented in Swagger (summary, response_model)
- [ ] No secrets, passwords or tokens in code or logs
- [ ] Conventional Commit messages
- [ ] He leído y probado el código generado por IA, y hay entrada en `docs/ai-log.md`

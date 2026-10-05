## What

<!-- One or two sentences, in English. -->

Closes #

## Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Permission tests: 401 without token, 403 with the wrong role, 404 for another member's resource
- [ ] Error path tested (invalid data gives 422, never 500)
- [ ] Endpoint documented in Swagger (summary, response_model)
- [ ] No secrets, passwords or tokens in code or logs
- [ ] Conventional Commit messages

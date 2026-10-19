# HU-34 · Límite de intentos en login y registro

Issue: #183 · Entrega 2 · Tamaño S-M · Prioridad P2

> Todavía no existe la plantilla `specs/README.md` (D-01). Esta spec usa las secciones que pide la D-01 y se ajustará cuando esté.

## Contexto

> Como gimnasio quiero frenar los ataques de fuerza bruta contra el login.

Nivel avanzado del README (ampliación de `AGENTS.md`): límite de intentos en login y registro. Un limitador en memoria por clave (marcas de tiempo), configurable por `.env`, con `Retry-After` en 429.

## Requisitos

1. Tras 5 intentos fallidos de login con el mismo email desde la misma IP en 15 minutos, el sexto intento responde 429 con `Retry-After`, aunque la contraseña sea correcta.
2. Cuando la ventana caduca, se puede volver a intentar; un login correcto pone el contador a cero.
3. Más de 10 registros desde la misma IP en una hora → 429 con `Retry-After`.
4. Los umbrales y ventanas se configuran en `.env`.
5. El limitador es inyectable/reemplazable en tests; solo vale con un proceso (documentado en el README).

## Reglas

- Login se cuenta por clave `email normalizado + IP`; solo fallos incrementan el contador.
- Registro se cuenta por IP; cada registro exitoso (201) incrementa el contador.
- Mientras el límite está activo, no se revela si la contraseña era correcta (mismo 429).
- Un solo proceso en memoria: sin Redis. Varios workers no comparten el contador.

## Criterios de aceptación

- **Dado** 5 intentos fallidos con el mismo email desde la misma IP en 15 minutos, **cuando** hago el sexto, **entonces** recibo 429 con `Retry-After`, aunque la contraseña sea correcta.
- **Dado** que pasa la ventana, **cuando** vuelvo a intentarlo, **entonces** se permite; un login correcto pone el contador a cero.
- **Dado** más de 10 registros desde la misma IP en una hora, **entonces** 429.
- **Dado** valores en `.env`, **cuando** arranca la API, **entonces** el limitador usa esos umbrales.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| POST | `/auth/login` | Público | 200 `LoginResponse` | 401, 422, **429** |
| POST | `/auth/register` | Público | 201 `UserOut` | 409, 422, **429** |

## Decisiones

| Decisión | Por qué |
| --- | --- |
| Limitador propio (timestamps por clave), no SlowAPI | Los AC piden ventana deslizante por email+IP / IP, reset en login OK, `Retry-After` e inyectable; SlowAPI es por ruta/IP y no modela el reset |
| `time.time` (no `monotonic`) | Los tests usan `freezegun` |
| Contar solo fallos en login | Un login correcto limpia el contador (AC) |
| Contar solo registros 201 | El AC habla de «registros», no de todos los POST |
| Cabecera `Retry-After` en segundos | Estándar HTTP; el frontend puede mostrar «X minutos» |
| Variables `AUTH_LOGIN_*` / `AUTH_REGISTER_*` | Claras en `.env.example` y alineadas con el resto de settings |

## Fuera de alcance

- Mensaje de UI en el frontend (subtarea FE aparte).
- Redis / rate limit multi-proceso.
- Lockout persistente en base de datos.
- Límite en otros endpoints (`/users/me`, pagos, etc.).

## Preguntas abiertas

- Ninguna bloqueante: umbrales por defecto 5/15 min (login) y 10/1 h (registro).

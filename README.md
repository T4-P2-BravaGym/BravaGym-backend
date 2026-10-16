# Brava · API

API de Brava, gimnasio de fuerza para mujeres: reservas de clases, entrenamiento personal, rutinas, tienda, pagos y bajas, con cuatro roles (`member`, `trainer`, `admin`, `superadmin`).

**Stack:** Python 3.11+, FastAPI, SQLite, SQLAlchemy 2, Alembic, Pydantic 2, pytest. La documentación interactiva está en [`/docs`](http://localhost:8000/docs) (Swagger).

## Arrancar en local

```bash
python3 -m venv .venv
source .venv/bin/activate          # con fish: source .venv/bin/activate.fish
pip install -r requirements-dev.txt
cp .env.example .env               # y pon un SECRET_KEY de verdad:
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
alembic upgrade head               # crea las tablas (la API ya no las crea al arrancar)
python -m scripts.seed             # opcional: datos de prueba (solo con ENVIRONMENT=local)
uvicorn app.main:app --reload      # http://localhost:8000/docs
pytest                             # tests
```
## Migraciones de base de datos

El esquema se gestiona con [Alembic](https://alembic.sqlalchemy.org/). **Cualquier cambio de modelo lleva su migración.**

```bash
alembic upgrade head                                     # aplica las migraciones pendientes
alembic revision --autogenerate -m "short description"   # genera una migración tras cambiar un modelo
alembic check                                            # falla si hay cambios de modelo sin migración
alembic downgrade -1                                     # deshace la última migración
```

Cuando cambies un modelo:

1. Edita el modelo en `app/models/`.
2. Genera la migración y **revísala** en `migrations/versions/`: autogenerate no lo detecta todo (por ejemplo, renombrados o índices parciales).
3. Aplícala con `alembic upgrade head`.
4. Haz commit del modelo y de su migración juntos.

Empezar de cero (se pierden los datos locales):

```bash
rm brava.db && alembic upgrade head && python -m scripts.seed
```

Los tests no usan Alembic (BD en memoria con `create_all`), pero `tests/integration/test_migrations.py` comprueba que las migraciones producen el mismo esquema que los modelos.

## Estructura (MVC)

```
app/
  main.py            # crea la app, CORS, errores y monta los routers en /api/v1
  core/              # configuración, BD, seguridad (JWT, bcrypt), caché, rate limit, logging, errores
  models/            # Model: tablas SQLAlchemy (ver docs/er.md)
  schemas/           # View: esquemas Pydantic de entrada y salida
  routers/           # Controller: endpoints finos que llaman a los servicios
  services/          # Reglas de negocio (RN-xx), sin nada de HTTP
migrations/          # migraciones de Alembic (una por cambio de esquema)
tests/
  conftest.py        # BD SQLite en memoria y cliente de pruebas
  unit/              # tests de servicios y reglas de negocio
  integration/       # tests de endpoints: permisos, IDOR, errores
scripts/seed.py      # datos de prueba
docs/                # diagrama ER, reglas de negocio, mapa de endpoints y permisos
```

Cada archivo empieza con un comentario que dice qué va dentro y en qué historia (`TODO(HU-12)`). Lo que ya funciona es la base: configuración, base de datos, manejo de errores, CORS y `/health`.

## Sesiones: refresh y logout (HU-33, backend)

Tras aplicar las migraciones con `alembic upgrade head`, el login conserva el formulario OAuth2 y la respuesta `{access_token, token_type}` de Swagger. También entrega el refresh en la cookie `brava.refresh`, HttpOnly, SameSite=Lax, sin Domain y con Path `/api/v1/auth`. No devuelve el refresh en JSON. `ACCESS_TOKEN_EXPIRE_MINUTES` y `REFRESH_TOKEN_EXPIRE_DAYS` configuran las duraciones (60 minutos y 7 días por defecto).

`POST /api/v1/auth/refresh` usa esa cookie y devuelve un access nuevo mientras rota la cookie. `POST /api/v1/auth/logout` exige además el bearer access de la misma usuaria, revoca ambos tokens y devuelve 204. Admite un access ya caducado solo para cerrar su sesión con un refresh válido. Ambos endpoints requieren la cabecera `X-Brava-CSRF: 1`; en Swagger se introduce en el campo correspondiente. Los clientes de API deben conservar las cookies entre peticiones.

Login, refresh y logout comprueban el origen del navegador. Solo se admiten los orígenes CORS configurados y el de la propia API (Swagger). Clientes sin Origin pueden usarlos; una petición marcada `Sec-Fetch-Site: cross-site` sin Origin se rechaza. La cookie usa Secure fuera de `ENVIRONMENT=local`, donde se permite HTTP. El contrato de producción requiere HTTPS y frontend/API en el mismo sitio (mismo esquema y dominio registrable), con CORS limitado al origen real del frontend; el frontend debe incluir la integración de HU-33 para renovar automáticamente.

Las revocaciones de access caducadas se limpian al emitir, renovar o cerrar una sesión. Los JWT antiguos sin `jti` y `type` dejan de aceptarse: será necesario iniciar sesión de nuevo.

## Recuperar contraseña (HU-35)

Aplicar `alembic upgrade head` antes de usar los nuevos endpoints. `POST /api/v1/auth/password-reset` recibe `{email}` y devuelve siempre el mismo 202 para emails válidos, existan o no y estén activos o no. Entrada malformada recibe 422 sin reflejar valores sensibles. No devuelve tokens. La entrega corre como tarea de fondo de FastAPI, con una sesión SQLAlchemy propia y una interfaz `EmailSender` inyectada.

En desarrollo (`ENVIRONMENT=local`), se escribe un JSON privado por mensaje en `OUTBOX_DIR` (por defecto `outbox/`, ignorado por Git). Leer el enlace del campo `body` de ese archivo y abrirlo en el navegador; no buscarlo en la consola: nunca se imprime. No subir ni compartir estos mensajes. El directorio usa 0700 y los archivos 0600, con nombres aleatorios, y no se sirven por HTTP. Este adaptador no envía correo real. Fuera de local se usa un transporte no disponible que registra un fallo seguro, sin crear outbox ni simular un envío: hay que inyectar un `EmailSender` real para habilitar entrega en producción.

`FRONTEND_URL` es el origen configurado del frontend (local: `http://localhost:5173`). Se valida HTTP(S), sin credenciales, rutas, query ni fragmento; HTTPS es obligatorio fuera de local. No se construye desde Host. Para probar en otro puerto/host, ajustar también CORS y `VITE_API_URL`; usar el mismo hostname en frontend y API. El enlace apunta a `/nueva-contrasena#token=...`; React retira el fragmento del historial y guarda el token solo en memoria. Si se recarga después, hay que volver a abrir el enlace o solicitar otro.

El token usa `secrets.token_urlsafe(32)`, se guarda solo como SHA-256 y caduca a los 30 minutos UTC. `POST /api/v1/auth/password-reset/confirm` recibe `{token,new_password}` y devuelve 204 sin cuerpo; token inválido, caducado o usado devuelve el mismo 400. Las respuestas de recuperación usan `Cache-Control: no-store`. Se mantiene la política de ocho caracteres y máximo 72 bytes UTF-8 de bcrypt.

Un reset consume el token, invalida los demás enlaces pendientes, actualiza la contraseña y su auditoría e incrementa `users.session_version` en una transacción. Todos los access y refresh anteriores quedan rechazados: los nuevos JWT llevan `ver`, comprobado contra esa cuenta al autenticar, renovar o cerrar sesión. Los JWT históricos sin `ver` equivalen a versión 0 solo hasta el primer reset. La usuaria inicia sesión normalmente con su nueva contraseña; no hay login automático.

El limitador de entrega permite tres intentos por email normalizado cada quince minutos, también para emails desconocidos, sin cambiar el 202. Reutiliza el limitador en memoria del proyecto: solo coordina un proceso Uvicorn; no es un límite distribuido. Las tareas de fondo tampoco son una cola duradera: pueden perderse al detener el proceso; un fallo de entrega conserva el 202 genérico y se puede volver a solicitar un enlace. No se activa verificación opcional de email.

## Límite de intentos (login y registro)

`POST /auth/login` y `POST /auth/register` usan un limitador **en memoria** (`app/core/rate_limit.py`, HU-34): marcas de tiempo por clave (email+IP en login, IP en registro). Los umbrales van en `.env` (`AUTH_LOGIN_*`, `AUTH_REGISTER_*`). Si se supera el límite, la API responde **429** con cabecera `Retry-After`.

**Solo vale con un proceso.** Varios workers de Uvicorn (o varias réplicas) no comparten el contador; cada uno tiene el suyo. Para producción multi-proceso haría falta un almacén compartido (p. ej. Redis).

## Colección de Bruno (D-05)

La colección está en [`collections/brava/`](collections/brava/), con una carpeta por tag, ejemplos `success` y `error`, y comprobaciones de los códigos esperados. [`inventory.json`](collections/brava/inventory.json) relaciona cada ejemplo con su operación. La spec está en [`specs/D-05-bruno-collection.md`](specs/D-05-bruno-collection.md).

### Preparar datos locales

Los ejemplos escriben datos: crean recursos, editan perfiles, retiran planes, cancelan reservas/pedidos y aprueban una baja. **Usa una base de demostración nueva**, no tu base habitual. Con el entorno Python instalado y activado, desde la raíz del backend:

```bash
bravaDemoDir=$(mktemp -d)
export DATABASE_URL="sqlite:///$bravaDemoDir/brava.sqlite"
export ENVIRONMENT=local
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Si el puerto 8000 está ocupado, usa otro y cambia `baseUrl` y `wsBaseUrl` en Bruno. La contraseña por defecto del seed es ficticia (`BravaDemo2026!`); si usas `SEED_PASSWORD`, cambia `demoPassword` **localmente** sin subir tu contraseña a Git.

### Abrir y ejecutar

1. En Bruno, elige **Open Collection** y abre `collections/brava/`.
2. Selecciona el entorno **local**. `baseUrl` no incluye `/api/v1`: cada petición ya tiene su ruta completa. `wsBaseUrl` es la dirección equivalente con `ws://`.
3. Ejecuta las peticiones HTTP por orden: `auth`, `users`, `trainers`, `plans`, `subscriptions`, `class-types`, `sessions`, `bookings`, `exercises`, `routines`, `shop`, `discount-codes`, `payments`, `cancellation-requests`, `health`. Dentro de cada carpeta, sigue los números de archivo.
4. En `auth`, el registro genera emails ficticios únicos y fechas futuras. El login guarda `token`/`tokenMember`; los logins de preparación guardan `tokenAdmin`, `tokenTrainer`, `tokenSuperadmin` y `tokenNewMember` con `bru.setVar`. Estos JWT solo viven en memoria; no se guardan en archivos.
5. Los POST guardan ids de recursos nuevos para las siguientes peticiones. Al ejecutar una petición suelta, ejecuta primero `auth` y las peticiones previas que crean sus recursos. La pestaña **Docs** de cada petición describe la preparación.

Los ejemplos `error` **deben devolver un error**: la prueba queda verde si reciben el código previsto. Las rutas protegidas usan un token inválido (401), la validación pública usa datos inválidos (422), y las rutas públicas sin un error funcional usan un método no permitido (405), indicado explícitamente en Docs.

La aprobación de baja al final desactiva la nueva socia ficticia; por eso va después de sus pagos y suscripción. No repitas toda la colección sobre la misma base modificada: detén el servidor, prepara otro directorio temporal con el bloque anterior y ejecútala de nuevo. Los ids `seed*` del entorno corresponden al seed de una base nueva.

### Runner HTTP con CLI

Se verificó con Bruno CLI **4.2.1**. Instálala siguiendo la [documentación oficial](https://docs.usebruno.com/bru-cli/overview) y, desde `collections/brava/`, ejecuta:

```bash
bru run auth users trainers plans subscriptions class-types sessions bookings \
  exercises routines shop discount-codes payments cancellation-requests health \
  --env local --noproxy
```

Para otro puerto, añade `--env-var baseUrl=http://127.0.0.1:8765`. No uses ejecución paralela: los ejemplos comparten tokens e ids y tienen dependencias de orden. No ejecutes el runner sobre la carpeta `realtime`; la CLI HTTP no ejecuta correctamente estas conexiones.

### WebSocket (Bruno de escritorio)

En `realtime`, abre `sessions-success` y pulsa **Connect**. No se promete un mensaje inicial; reserva o cancela una clase de esa sesión en otra petición para ver `session_updated`. El ejemplo `sessions-error-invalid-id` usa `not-an-integer` y debe rechazar la conexión. Es un fallo de handshake, no una respuesta JSON HTTP. La ruta actual acepta cualquier id entero sin comprobar que exista una sesión: un id inexistente no es un ejemplo de 404 válido.

Formato y scripts de referencia: [archivos Bru](https://docs.usebruno.com/bru-lang/overview) y [variables de ejecución](https://github.com/usebruno/bruno-docs/blob/main/testing/script/javascript-reference.mdx). La colección no contiene JWT reales ni datos de personas reales.

## Cómo trabajamos con el proyecto

Todo está en [`AGENTS.md`](AGENTS.md): la IA como mentora, idioma, DRY y SOLID, MVC, seguridad, ramas, Conventional Commits y Definition of Done. Las tareas están en el GitHub Project **Brava** de la organización.

Antes de abrir una PR:

```bash
alembic check
pytest
pip-audit -r requirements.txt
```

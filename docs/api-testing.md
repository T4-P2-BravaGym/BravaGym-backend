# Bruno API testing

La colección está en [`collections/brava/`](../collections/brava/), con una carpeta por tag, ejemplos `success` y `error`, y comprobaciones de los códigos esperados. [`inventory.json`](../collections/brava/inventory.json) relaciona cada ejemplo con su operación. La spec está en [`specs/D-05-bruno-collection.md`](../specs/D-05-bruno-collection.md).

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


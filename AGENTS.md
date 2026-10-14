# Brava — instrucciones para la IA del equipo

Este archivo explica a cualquier asistente de IA (Claude, ChatGPT, Copilot…) cómo trabajamos en el proyecto Brava. Si eres una IA y lo estás leyendo: sigue estas reglas en todas tus respuestas sobre este proyecto.

## 1. Tu papel: dos modos de trabajo

Somos un equipo de cinco personas de un bootcamp y estamos aprendiendo. Dos de nosotras empiezan desde cero. El objetivo no cambia: queremos aprender a hacerlo nosotras. Pero hay dos formas de trabajar contigo y la persona dice en cuál está. Si no lo dice, estás en modo mentora.

### Modo mentora (por defecto, en una conversación)

- **No escribas ni modifiques archivos del proyecto** (código, configuración, tests, README) sin la aprobación explícita de la persona. "¿Lo hago yo?" no cuenta como aprobación; espera a un "sí, hazlo".
- **No ejecutes comandos** en el ordenador de la persona sin preguntarle antes. Eso incluye leer archivos, buscar o instalar.
- **Guía.** Explica qué hay que hacer y por qué, señala en qué archivo va cada cosa y da pistas o fragmentos cortos comentados para que la persona escriba el código. Si pide una solución completa, enséñala explicada, sin pegarla en sus archivos.
- **Adapta el nivel.** Pregunta qué sabe ya. Con quien empieza, avanza a pasos pequeños, sin jerga sin explicar, y comprueba que lo ha entendido antes de seguir.
- **Revisa con criterio.** Cuando te pidan revisar, señala errores, riesgos y mejoras concretas con el porqué. Di también lo que está bien.

### Modo agente (OpenCode, sobre una tarea pequeña con su spec)

Aquí escribes el código tú, pero el alcance lo pone la spec y la persona responde del resultado ante el equipo.

- **Sin spec no empiezas.** Cada tarea tiene la suya en `specs/` (plantilla en `specs/README.md`). Léela entera antes de escribir nada. Si no existe, pídela en lugar de suponer.
- **No te salgas del alcance.** Tocas solo los archivos que la tarea necesita y respetas el apartado "Fuera de alcance" de la spec. Si para terminar hace falta algo que no está en la spec, páralo y pregunta.
- **Si un test falla, arregla el código.** Nunca borres un test, lo marques como `skip` ni le bajes la exigencia para que pase. Si crees que el test está mal, dilo y espera respuesta.
- **Dejas la tarea verde:** `pytest` y `alembic check` pasan antes de decir que has acabado.
- **Nunca subas `.env`, secretos, claves ni la base de datos.** Si necesitas una variable nueva, añádela a `.env.example` sin valor real.
- **Rama y PR,** nunca un push directo a `dev` ni a `main` (apartado 8). Dejas la spec enlazada en la PR.
- **Registra lo que hiciste** en la bitácora (apartado 10).

### Siempre, en los dos modos

- **No inventes.** Si algo no está en este archivo, en la spec, en el documento de diseño o en el código, pregunta en lugar de suponer.
- **Responde en el idioma de la persona.** Las reglas de idioma del código están en el apartado 3.
- **Quien revisa es una persona.** Ninguna PR entra en `dev` sin que otra compañera la lea y la apruebe.

## 2. El proyecto

- **Qué es:** Brava, app de gestión de un gimnasio de fuerza para mujeres.
- **Roles:** `member` (socia), `trainer` (entrenadora), `admin` (administración) y `superadmin`.
- **Funciones:** reservas de clases con aforo, lista de espera y cancelación hasta 1 hora antes; entrenamiento personal; rutinas; tienda; pagos con códigos de descuento; solicitudes de baja.
- **Repos:**
  - `T4-P2-BravaGym/BravaGym-backend`: API.
  - `T4-P2-BravaGym/BravaGym-frontend`: web.
- **Stack backend:** Python, FastAPI, SQLite, SQLAlchemy, Alembic, Pydantic, pytest y Swagger (en `/docs`).
- **Stack frontend:** React con JavaScript (no TypeScript), Vite y SASS.
- **Entregas:** el 9 de octubre (todo el CRUD) y el 19 de octubre (ampliación).
- **Tareas:** están en el GitHub Project "Brava", una issue por historia de usuario (`HU-12 · Reservar una clase`) con sus criterios de aceptación y sus subtareas como sub-issues. Las reglas de negocio se citan como `RN-05`, y su detalle está en el documento de diseño del equipo.
- **Specs:** una por historia o tarea en `specs/` (`specs/HU-31-admin-users.md`), con la plantilla de `specs/README.md`.
- **Comandos:**

```bash
  source .venv/bin/activate              # con fish: source .venv/bin/activate.fish
  pip install -r requirements-dev.txt
  alembic upgrade head                   # crea o actualiza las tablas
  python -m scripts.seed                 # datos de prueba (solo con ENVIRONMENT=local)
  uvicorn app.main:app --reload          # http://localhost:8000/docs
  pytest                                 # todos los tests
  pytest tests/unit/test_x.py -k nombre  # un test concreto
  alembic revision --autogenerate -m "short description"
  alembic check                          # falla si hay un cambio de modelo sin migración
  pip-audit -r requirements.txt
```

Antes de abrir una PR: `alembic check`, `pytest` y `pip-audit -r requirements.txt`.

## 3. Idioma

- **En inglés:** código, nombres de variables, funciones, clases y archivos; comentarios y docstrings; mensajes de commit; nombres de ramas; descripciones de PR.
- **En el idioma de la persona:** la conversación con la IA.
- **En español:** los textos que ve la socia en la app (botones, mensajes de error, etiquetas).

## 4. Principios de código

- **DRY:** cada regla vive en un solo sitio. Si escribes lo mismo dos veces, sácalo a una función, un servicio, un componente o un mixin.
- **SOLID**, aplicado a este proyecto:
  - **S, responsabilidad única:** un router recibe y responde, un servicio aplica reglas, un modelo describe datos. Un componente de React hace una cosa.
  - **O, abierto/cerrado:** añadir un tipo de clase o un estado nuevo no debería obligar a reescribir lo que ya funciona.
  - **L, sustitución:** si una función acepta un tipo, cualquier variante de ese tipo debe funcionar igual.
  - **I, interfaces pequeñas:** esquemas Pydantic y props de componentes con solo lo que hace falta. `UserOut` no lleva la contraseña.
  - **D, inversión de dependencias:** la sesión de base de datos y el usuario actual llegan con `Depends(...)`, nunca se crean dentro de un servicio.
- **Simple antes que listo:** código legible para el resto del equipo, nombres descriptivos y funciones cortas.

## 5. Backend: MVC con FastAPI

En una API, la "vista" es la respuesta JSON. Así encaja MVC en nuestras carpetas:

| Capa | Carpeta | Qué hace | Qué NO hace |
| --- | --- | --- | --- |
| Model | `app/models/` | Tablas con SQLAlchemy | Lógica de negocio |
| View | `app/schemas/` | Esquemas Pydantic de entrada y salida (lo que se ve en la respuesta) | Consultas a la base de datos |
| Controller | `app/routers/` | Recibe la petición, valida permisos, llama al servicio y devuelve el esquema | Reglas de negocio ni consultas complejas |
| Servicios | `app/services/` | Reglas de negocio (aforo, plazo de 1 hora, stock, códigos…) | Saber nada de HTTP |
| Núcleo | `app/core/` | Configuración, seguridad JWT, base de datos, logging | — |
| Migraciones | `migrations/` | Una migración de Alembic por cada cambio de esquema | Editar migraciones ya mergeadas |

Reglas del backend:

- **Controladores finos:** cada endpoint cabe en unas pocas líneas y delega en un servicio.
- **Permisos:** con la dependencia `require_roles("trainer", "superadmin")`, nunca con `if` sueltos en el endpoint.
- **Errores:** códigos HTTP coherentes. 401 sin token; 403 sin permiso; 404 si no existe o no es suyo; 409 si choca con el estado (aforo, duplicado, plazo de 1 hora, stock); 422 si los datos son inválidos. El mensaje dice qué pasó, en español.
- **Dinero:** en céntimos enteros (`price_cents`), nunca `float`.
- **Migraciones:** cualquier cambio de modelo lleva su migración (`alembic revision --autogenerate`, revisada a mano) en el mismo commit que el modelo. Nunca se edita una migración ya mergeada: se crea otra. `alembic check` tiene que pasar.
- **Fechas:** en UTC.
- **Borrado:** usuarios y planes no se borran, se desactivan (`is_active = false`).
- **Datos derivados:** las plazas libres, los totales y la posición en la lista de espera no se guardan; se calculan.
- **Tests con pytest** para cada regla de negocio, con nombres que la citen: `test_rn05_cancel_less_than_one_hour_returns_409`. Las pruebas de tiempo se hacen con la hora congelada. La base de datos de los tests es SQLite en memoria (`conftest.py`). Hay un test que comprueba que las migraciones coinciden con los modelos (`tests/integration/test_migrations.py`).
- **Swagger:** cada endpoint lleva `summary`, `tags` y un ejemplo.
- **Logging** en las operaciones que crean, cambian o borran datos.
- **Secretos** en `.env`, que nunca se sube; `.env.example` sí se sube.

## 6. Frontend: diseño con componentes y SASS

```
src/
  components/
    ui/          # design system pieces: Button, Badge, Chip, Field, Card, Modal, Table, Pagination, Tabs…
      Button/
        Button.jsx
        Button.module.scss
        index.js
    domain/      # Brava pieces built from ui: SessionCard, WeekSchedule, PricingCard, ProductCard…
    layout/      # Navbar, Footer, SideNav, MobileTabBar
  layouts/       # PublicLayout and PrivateLayout (nav entries depend on the role)
  pages/         # one folder per screen, by area: public/, member/, trainer/, admin/
  routes/        # AppRouter, ProtectedRoute and paths.js (every URL in one place)
  context/       # AuthContext (session, token, role)
  hooks/         # useAuth and other shared logic
  services/      # API calls: api.js (the only HTTP client) + one file per module
  utils/         # formatting helpers (euros, dates)
  styles/
    _tokens.scss   # CSS custom properties from the Brava design system
    _mixins.scss   # reusable patterns: focus-ring, eyebrow, mobile…
    main.scss      # global styles, loaded once
```
Reglas del frontend:

- **Componentes:** si algo se repite dos veces, es un componente. `ui/` no sabe nada de Brava (un Button vale para cualquier app); `domain/` monta piezas de Brava con los de `ui/`. Los nombres coinciden con los del sistema de diseño.
- **Una responsabilidad por pieza:** las páginas montan componentes y piden datos a `services/`; los componentes reciben datos por props y no llaman a la API.
- **SASS por componente** con CSS Modules (`Button.module.scss`); los estilos globales solo en `styles/`.
- **Nombres de clases sin BEM en los módulos.** CSS Modules ya convierte cada clase en un nombre único (`.primary` pasa a ser `Button_primary__x7f2`), así que el bloque y el doble guion de BEM sobran. Dentro de cada `.module.scss`, clases cortas en camelCase que describen la parte o el estado: `.root`, `.title`, `.primary`, `.small`, `.isActive`, `.isDisabled`. En JSX se usan como `styles.primary`. Solo en `styles/` (globales) se usa BEM si hiciera falta. Las clases `bv-btn--primary` del sistema de diseño son la referencia visual; en React se reescriben como módulos.
- **Tokens:** nunca colores, tamaños ni espaciados sueltos; siempre los del sistema de diseño (`var(--mauve)`, `var(--space-6)`, `var(--radius-lg)`). Los mixins de SASS sirven para patrones que se repiten, no para valores.
- **Tipografías:** Bricolage Grotesque en titulares y Figtree en el texto.
- **Accesibilidad:** `<button>` y `<a href>` de verdad, `<label>` en cada campo, foco visible, contraste del sistema de diseño y controles de al menos 44 px.
- **Estados de la API siempre igual:** el mismo estado (reservada, lista de espera, pagado, pendiente…) usa siempre el mismo componente `Badge` y el mismo tono.

## 7. Seguridad

Sacado de un checklist de ciberseguridad (OWASP Top 10:2025) y adaptado a Brava. **Regla de oro:** lo que el frontend oculta no es seguridad. Cada endpoint se protege en la API, aunque la pantalla ya no muestre el botón.

### Autenticación
- **Contraseñas con bcrypt** (coste 12 o más). Nunca MD5, SHA1 ni texto plano, tampoco en logs ni en respuestas.
- **Login con mensaje genérico:** "Email o contraseña incorrectos", sin decir cuál de los dos falla ni si el email existe.
- **JWT:**
  - Al verificarlo, fija el algoritmo (`algorithms=["HS256"]`) y valida `exp`, `iss` y `aud`.
  - En el payload solo van `sub` (id) y `role`: el payload se puede leer, no está cifrado.
  - `SECRET_KEY` larga y aleatoria, en `.env`.
- **Fallar cerrado:** si algo falla al comprobar el token o el rol, se deniega (401/403), nunca se deja pasar.

### Autorización
- **Endpoints no públicos:** todos llevan `get_current_user` y, si hace falta, `require_roles(...)`.
- **Recursos de la socia** (reservas, pagos, pedidos, rutina, solicitud de baja): se filtran por `current_user.id` en la consulta. Si piden uno ajeno, la respuesta es 404.
- **El rol** sale del token y de la base de datos, nunca de lo que envíe el frontend. Nadie cambia su propio rol (RN-19).
- **Tests obligatorios por endpoint:**
  - Sin token, 401.
  - Con un rol sin permiso, 403.
  - La socia A pidiendo un recurso de la socia B, 404 (IDOR).

### Datos de entrada y salida
- **Entrada:** cada body se valida con un esquema Pydantic, con límites (`max_length`, `ge`, `le`).
- **Salida:** todos los endpoints llevan `response_model`. Nunca se devuelve el objeto de SQLAlchemy tal cual, que podría incluir `password_hash`.
- **Asignación masiva (mass assignment):**
  - Los esquemas de actualización solo incluyen los campos que se pueden cambiar; `role`, `is_active` o `user_id` nunca vienen del cliente.
  - **Precios e importes los calcula siempre el servidor**, nunca se aceptan del frontend.
- **Paginación** con tamaño máximo (`size: int = Query(20, le=100)`).
- **Consultas** siempre con el ORM o con parámetros. Nunca SQL montado con f-strings.

### Lógica de negocio y peticiones simultáneas
- **Puntos delicados:** aforo de clases, stock, usos máximos de un código y una sola suscripción activa. Si llegan dos peticiones a la vez, ninguna puede saltarse el límite.
- **Comprobación y escritura juntas,** en la misma transacción. Mejor con una operación atómica, por ejemplo `UPDATE products SET stock = stock - :qty WHERE id = :id AND stock >= :qty`, mirando cuántas filas cambió.
- **Restricciones `UNIQUE`** en la base de datos como última barrera: `UNIQUE(user_id, class_session_id)` en reservas.
- **Test de concurrencia:** dos reservas para la última plaza, y solo una queda confirmada.

### Errores y logs
- **El cliente recibe un mensaje claro y genérico;** el detalle técnico (stack trace, consulta) solo va al log. Manejador global de excepciones y `DEBUG` desactivado fuera de local.
- **Prohibido `except: pass`:** todo error capturado se registra o se vuelve a lanzar.
- **Los logs no guardan** contraseñas, tokens ni más datos personales de los necesarios: el `user_id`, no el email.
- **Tests de la ruta de error,** no solo del caso feliz: datos mal formados dan 422 controlado, nunca un 500.

### Configuración y dependencias
- **`.env`:**
  - Va en `.gitignore`.
  - `.env.example` documenta las variables sin valores reales.
  - Ningún secreto en el código.
- **CORS:** solo el origen del frontend (`http://localhost:5173` en local). Nunca `*`.
- **Swagger** (`/docs`) se queda activo porque es un entregable; en una app real se desactivaría en producción.
- **Dependencias** con versión fija (`requirements.txt`, `package-lock.json`).
- **Dependabot** activado en los dos repos.
- **En CI:** `pip-audit` y `npm audit`. Si hay tiempo, `bandit` para el código Python.

### Frontend
- **Las rutas privadas y de admin** llevan guard de sesión y de rol en React, pero eso es comodidad, no seguridad: la API decide.
- **Variables `VITE_*`:** son públicas (acaban en el navegador), así que nunca llevan secretos.
- **HTML:** nunca `dangerouslySetInnerHTML` con datos del usuario.
- **Redirección tras el login:** solo a rutas internas (`/mi-area`), nunca a una URL que venga en un parámetro.
- **Respuesta 401 de la API:** se cierra la sesión y se vuelve al login.

### Ampliación (entrega 2)
- **Stripe:** el webhook verifica la firma y es idempotente (el mismo evento dos veces no paga dos veces). Las claves van en `.env`.
- **Docker:** imagen multi-stage, usuario no root y `.env` fuera de la imagen (en `.dockerignore`).
- **Límite de intentos** en login y registro (por ejemplo con `slowapi`).

### Checklist antes de mergear un endpoint nuevo
- [ ] Autenticación y rol comprobados en la API.
- [ ] Recursos ajenos inaccesibles (filtrados por usuario).
- [ ] Esquema de entrada con límites y `response_model` de salida.
- [ ] Tests de 401, 403 e IDOR, y de la ruta de error.
- [ ] Si toca aforo, stock o códigos: operación atómica y test de concurrencia.
- [ ] Documentado en Swagger.

## 8. Forma de trabajar con Git

- **Ramas:**
  - `main` es lo entregado y `dev` es la integración.
  - Nadie hace push directo a ninguna de las dos.
  - Cada tarea va en su propia rama, creada desde `dev`: `feature/hu-12-book-class` o `fix/hu-13-cancel-deadline`.
- **Commits** en inglés con [Conventional Commits](https://www.conventionalcommits.org/):
  - **Formato:** `type(scope): description`.
    - La descripción va en imperativo, en minúscula y sin punto final.
    - Opcionalmente, un cuerpo que explique el porqué y `Refs #NN`.
  - **Tipos:**

    | Tipo | Cuándo |
    | --- | --- |
    | `feat` | Funcionalidad nueva |
    | `fix` | Corrección de un error |
    | `test` | Añadir o cambiar tests |
    | `refactor` | Cambio de código sin cambiar lo que hace |
    | `docs` | Documentación |
    | `style` | Formato, sin cambio de lógica |
    | `chore` | Configuración, dependencias, scripts |
    | `ci` | GitHub Actions |
    | `build` | Docker, empaquetado |
  - **Scope:** el módulo, por ejemplo `bookings`, `auth`, `payments`, `shop` o `ui`.
  - **Ejemplos:**
    - `feat(bookings): add waitlist promotion on cancellation`
    - `fix(auth): reject expired tokens with 401`
    - `test(bookings): cover RN-05 one-hour cancellation limit`
  - **Commits pequeños,** uno por cambio con sentido; no un único commit al final de la tarea.
  - Sin líneas de coautoría de la IA.
- **PR:**
  - Siempre hacia `dev`.
  - Descripción en inglés y con `Closes #NN` para cerrar la issue. Para cerrar una issue del otro repo: `Closes T4-P2-BravaGym/BravaGym-backend#NN`.
  - Otra compañera la revisa y la aprueba antes del merge.
- **Definition of Done** de cada historia:
  - Spec en `specs/` escrita y enlazada en la PR.
  - PR revisada por otra compañera **con comentarios visibles**, no solo un *approve*.
  - Tests en verde en GitHub Actions, incluidos los de permisos e IDOR.
  - Checklist de seguridad del apartado 7 cumplido.
  - Endpoint documentado en Swagger.
  - Log en las operaciones que cambian datos.
  - Pantalla conectada, si la tiene.
  - Si cambia un modelo, la PR incluye su migración y `alembic check` pasa.
  - Entrada en `docs/ai-log.md` si un agente generó código (apartado 10).
  - Mergeada a `dev`.

## 9. Cuando te pidan ayuda con una issue

1. Pide el número o el texto de la issue y lee sus criterios de aceptación.
2. Ayuda a dividirla en pasos pequeños: modelo → esquema → servicio → test → router → pantalla. Señala qué puntos del checklist de seguridad le afectan.
3. Para cada paso, explica qué hay que hacer y deja que la persona lo escriba. Revisa lo que escriba.
4. Antes de dar la tarea por terminada, repasa con ella los criterios de aceptación y la Definition of Done.

## 10. Bitácora de IA

Todo lo que genere un agente se registra en `docs/ai-log.md`. Es un entregable de la asignatura y vive solo en el backend; el frontend enlaza a él.

Una entrada por historia y persona, añadida en la misma PR que el código:

```markdown
## HU-XX · Nombre de la historia — Nombre de la persona

- **Herramienta y modelo:** OpenCode + <modelo>
- **Prompt clave:** el prompt que de verdad movió la tarea, copiado tal cual
- **Qué generó:** en dos líneas
- **Qué acepté:** y por qué
- **Qué rechacé:** y por qué
- **Errores o alucinaciones:** qué se inventó o qué hizo mal, y cómo se corrigió
```

Reglas:

- **Lo que no se registra no cuenta.** Si no hay entrada, la historia no está terminada.
- **Si usas una herramienta de pago** (Claude, Cursor…), dilo y di para qué: la asignatura pide delimitar su alcance.
- **Nunca pegues en la bitácora** un prompt con secretos, claves ni datos reales de personas.
- **Si no hubo agente,** no hace falta entrada.
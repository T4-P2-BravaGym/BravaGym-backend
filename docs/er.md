## Modelo de datos

El esquema tiene **18 tablas en tercera forma normal (3FN)**: 11 entran en el sprint 1 (núcleo) y 7 en el sprint 2 (bajas, tienda y pagos). El bloque Mermaid se puede pegar tal cual en el README de GitHub, que lo renderiza como diagrama ER.

```mermaid
erDiagram
    ROLES ||--o{ USERS : tiene
    USERS ||--o| TRAINER_PROFILES : perfil
    USERS ||--o{ SUBSCRIPTIONS : contrata
    MEMBERSHIP_PLANS ||--o{ SUBSCRIPTIONS : define
    SUBSCRIPTIONS ||--o{ CANCELLATION_REQUESTS : solicita_baja
    USERS ||--o{ CANCELLATION_REQUESTS : revisa
    CLASS_TYPES ||--o{ CLASS_SESSIONS : programa
    USERS ||--o{ CLASS_SESSIONS : imparte
    CLASS_SESSIONS ||--o{ BOOKINGS : recibe
    USERS ||--o{ BOOKINGS : reserva
    USERS ||--o{ ROUTINES : sigue
    USERS ||--o{ ROUTINES : disena
    ROUTINES ||--|{ ROUTINE_EXERCISES : contiene
    EXERCISES ||--o{ ROUTINE_EXERCISES : aparece_en
    PRODUCT_CATEGORIES ||--o{ PRODUCTS : agrupa
    USERS ||--o{ ORDERS : compra
    ORDERS ||--|{ ORDER_ITEMS : incluye
    PRODUCTS ||--o{ ORDER_ITEMS : vendido_en
    USERS ||--o{ PAYMENTS : paga
    SUBSCRIPTIONS ||--o{ PAYMENTS : cuota
    BOOKINGS ||--o| PAYMENTS : clase_extra
    ORDERS ||--o| PAYMENTS : pedido
    DISCOUNT_CODES ||--o{ PAYMENTS : aplica
    USERS ||--o{ DISCOUNT_CODES : crea

    ROLES {
        int id PK
        string name UK "member | trainer | admin | superadmin"
    }
    USERS {
        int id PK
        string email UK
        string password_hash
        string first_name
        string last_name
        string phone
        int role_id FK
        bool is_active
        datetime created_at
        datetime deactivated_at "nullable, soft delete"
    }
    TRAINER_PROFILES {
        int user_id PK, FK
        text bio
        string specialty
    }
    MEMBERSHIP_PLANS {
        int id PK
        string name UK
        text description
        int monthly_price_cents
        bool includes_personal_training
        bool is_active
    }
    SUBSCRIPTIONS {
        int id PK
        int user_id FK
        int plan_id FK
        date start_date
        date end_date "nullable"
        string status "active | cancelled | expired"
    }
    CANCELLATION_REQUESTS {
        int id PK
        int subscription_id FK
        text reason
        string status "pending | approved | rejected"
        datetime requested_at
        int reviewed_by FK "nullable"
        datetime reviewed_at "nullable"
        text admin_notes
    }
    CLASS_TYPES {
        int id PK
        string name UK
        text description
        int extra_price_cents "0 = incluida"
        bool is_personal_training
        bool is_active
    }
    CLASS_SESSIONS {
        int id PK
        int class_type_id FK
        int trainer_id FK
        datetime starts_at
        int duration_minutes
        int capacity
        string status "scheduled | cancelled"
    }
    BOOKINGS {
        int id PK
        int user_id FK
        int class_session_id FK
        string status "confirmed | waitlisted | cancelled"
        datetime created_at
        datetime cancelled_at "nullable"
    }
    EXERCISES {
        int id PK
        string name UK
        string muscle_group
        text description
    }
    ROUTINES {
        int id PK
        int member_id FK
        int trainer_id FK
        string name
        date start_date
        text notes
        bool is_active
    }
    ROUTINE_EXERCISES {
        int id PK
        int routine_id FK
        int exercise_id FK
        int day_number
        int position
        int sets
        int reps
        int rest_seconds
    }
    PRODUCT_CATEGORIES {
        int id PK
        string name UK
    }
    PRODUCTS {
        int id PK
        int category_id FK
        string name
        text description
        int price_cents
        int stock
        bool is_active
    }
    ORDERS {
        int id PK
        int user_id FK
        string status "pending | paid | cancelled"
        datetime created_at
    }
    ORDER_ITEMS {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
        int unit_price_cents "precio en el momento"
    }
    DISCOUNT_CODES {
        int id PK
        string code UK
        int percent_off
        date valid_from
        date valid_until
        int max_uses "nullable"
        bool is_active
        int created_by FK
    }
    PAYMENTS {
        int id PK
        int user_id FK
        int subscription_id FK "nullable"
        int booking_id FK "nullable"
        int order_id FK "nullable"
        int discount_code_id FK "nullable"
        int base_amount_cents
        int final_amount_cents
        string status "pending | paid | failed | refunded"
        string method "simulated | stripe"
        string provider_ref "nullable"
        datetime created_at
        datetime paid_at "nullable"
    }
```

### Qué tablas entran en cada sprint

| Sprint | Tablas |
| --- | --- |
| 1 — núcleo | roles, users, trainer_profiles, membership_plans, subscriptions, class_types, class_sessions, bookings, exercises, routines, routine_exercises |
| 2 — negocio | cancellation_requests, product_categories, products, orders, order_items, discount_codes, payments |

### Decisiones de normalización

- **1FN, valores atómicos:** los ejercicios de una rutina no van en un campo de texto separado por comas, sino en `routine_exercises`, una fila por ejercicio, día y posición.
- **2FN, dependencia de la clave completa:** en las tablas puente (`order_items`, `routine_exercises`) cada atributo depende del par completo. Se usa un `id` propio más una restricción `UNIQUE` sobre el par: `UNIQUE(order_id, product_id)` y `UNIQUE(routine_id, day_number, position)`.
- **3FN, sin dependencias transitivas:** los nombres de rol viven en `roles` y las categorías en `product_categories`, no repetidos como texto.
- **No se guarda nada derivable:** las plazas ocupadas se cuentan (`bookings` confirmadas), la posición en la lista de espera sale de ordenar por `created_at`, el total de un pedido es la suma de sus líneas y los usos de un código se cuentan en `payments`. Guardarlos sería duplicar datos que pueden desincronizarse.
- **La baja cuelga de la suscripción, no del usuario:** el socio se obtiene a través de `subscriptions.user_id`, así que `cancellation_requests` no repite `user_id`.
- **Excepciones justificadas:** `order_items.unit_price_cents` y los importes de `payments` son una foto del precio en ese momento, no una redundancia; si mañana sube la proteína, el pedido de ayer no cambia. `payments.user_id` es una desnormalización consciente para listar "mis pagos" y filtrar en administración sin unir tres tablas; el servicio comprueba que coincide con el dueño de la suscripción, reserva o pedido.
- **Un pago, un concepto:** `CHECK` que obliga a que exactamente uno de `subscription_id`, `booking_id` y `order_id` no sea nulo.
- **Soft delete:** el usuario nunca se borra; la baja aprobada pone `users.is_active = false`, rellena `deactivated_at` y pasa la suscripción a `cancelled`. Así se conserva el historial de pagos.

### Notas para SQLite

- Activar las claves foráneas en cada conexión (`PRAGMA foreign_keys = ON`); SQLite las ignora por defecto.
- El dinero en **céntimos enteros** (`*_cents`): SQLite no tiene tipo decimal y los `float` dan errores de redondeo.
- Los estados como texto con `CHECK (status IN (...))`, o `Enum` de SQLAlchemy, que genera ese `CHECK`.
- Fechas siempre en UTC; la conversión a hora de Madrid se hace en el frontend.
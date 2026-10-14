# HU-16 · Plazas libres en tiempo real

Issue: #73 · Entrega 2 · Tamaño M

## Contexto

> Como socia quiero ver las plazas libres actualizarse solas para reservar en cuanto se libera una.

Toca clases y reservas. Antes, las plazas libres solo cambiaban al recargar la página. La
historia añade un websocket por clase: el servidor avisa cuando una reserva o una cancelación
cambia sus plazas o su lista de espera, y la pantalla vuelve a pedir los datos. Usa las reservas
y cancelaciones de HU-12 y HU-13.

## Requisitos

1. Si tengo una clase en pantalla y otra persona reserva o cancela, el número de plazas cambia sin recargar.
2. Cuando alguien sube desde la lista de espera, también se avisa.
3. Solo se avisa a quien está mirando esa clase, no a las demás.
4. Mirar las plazas no necesita cuenta, igual que el horario.
5. El mensaje no lleva datos de nadie: solo qué clase ha cambiado.

## Reglas

- **RN-06**: Al cancelarse una reserva `confirmed`, la reserva en espera más antigua (`created_at`) pasa a `confirmed` en la misma transacción, y se emite un evento por websocket.

## Criterios de aceptación

- **Dado** que tengo abierta una clase, **cuando** otra persona reserva, **entonces** recibo `{"type": "session_updated", "session_id": N}`.
- **Dado** que tengo abierta una clase, **cuando** otra persona cancela, **entonces** recibo el mismo evento.
- **Dado** que alguien sube desde la lista de espera, **cuando** ocurre, **entonces** el evento lo refleja.
- **Dado** que no he iniciado sesión, **cuando** abro el websocket, **entonces** se conecta igual; y cuando lo cierro, el servidor deja de contarme.
- **Dado** que miro la clase A, **cuando** alguien reserva en la clase B, **entonces** no recibo nada.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| WS | `/ws/sessions/{session_id}` | Público | Mensajes `session_updated` | — |

El servidor solo envía; lo que mande el cliente se ignora. No cambia el esquema.

## Interfaz

"Mis reservas" (`/mi-area/reservas`): la página abre un websocket por cada clase que tiene en
pantalla con el hook `useSessionUpdates`. Al llegar un aviso vuelve a cargar las clases y las
reservas, así que las plazas libres y los botones se actualizan solos. Los websockets se cierran
al cambiar de clases o al salir de la página. Sin estados nuevos: se usan los de carga y error
que ya tenía la página.

## Fuera de alcance

- Mandar el número de plazas dentro del mensaje: la página vuelve a pedirlo a la API.
- Avisos en otras pantallas (horario público, clases de la entrenadora).
- Notificaciones fuera de la app (email o push).
- Varios servidores a la vez: las conexiones se guardan en memoria del proceso.

## Decisiones

| Decisión | Por qué |
| --- | --- |
| El mensaje solo dice qué clase cambió, sin plazas ni nombres | La API sigue siendo la única fuente de datos y el websocket público no expone nada. |
| Un gestor (`SessionConnectionManager`) guarda las conexiones por clase | Así un aviso solo llega a quien mira esa clase. |
| `notify_from_sync` con `asyncio.run_coroutine_threadsafe` | Los servicios de reservas son síncronos y corren en otro hilo; los websockets viven en el event loop. |
| El aviso se manda después del `commit` | Si la página recarga antes de que se guarde, vería las plazas antiguas. |
| Las conexiones cerradas se olvidan al fallar el envío | Una pestaña cerrada no debe romper el aviso a las demás. |
| El hook guarda el último callback en un `useRef` | Así no se reabren los websockets en cada render. |
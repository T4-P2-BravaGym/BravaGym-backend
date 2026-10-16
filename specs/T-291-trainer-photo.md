# T-291 · Foto de las entrenadoras

Issue: #291 · Entrega 2 · Tamaño M

## Contexto

> Como visitante quiero ver la foto de cada entrenadora para conocer al equipo antes de entrenar.

Toca entrenadoras (HU-15) y fotos (HU-30). Hoy las tarjetas de "Entrenadoras" enseñan un avatar
con las iniciales. La HU-30 ya sube fotos de productos con todas las comprobaciones; esta tarea
las saca a un módulo común y las usa también para las entrenadoras.

## Requisitos

1. Una entrenadora sube su foto (JPEG, PNG o WebP, hasta 2 MB) y la puede cambiar o quitar.
2. El listado público de entrenadoras enseña la foto; sin foto, el avatar con las iniciales.
3. Un archivo que no es una imagen o es demasiado grande se rechaza y no cambia nada.
4. Solo la entrenadora cambia su propia foto.
5. Las fotos de productos siguen funcionando igual.

## Criterios de aceptación

- **Dado** que soy entrenadora, **cuando** subo una foto válida, **entonces** recibo 200 con `photo_url` (`/media/trainers/...`) y el listado la enseña.
- **Dado** que ya tenía foto, **cuando** subo otra, **entonces** se guarda la nueva y se borra el archivo de la vieja.
- **Dado** que quito mi foto, **entonces** `photo_url` es `null`, se borra el archivo y el listado vuelve a las iniciales; sin foto, quitarla no cambia nada (200).
- **Dado** un PDF, un SVG o un archivo vacío, **entonces** recibo 422 (`invalid_image`) y no se guarda nada, aunque el nombre acabe en `.jpg`.
- **Dado** una foto de más de 2 MB, **entonces** recibo 422 (`image_too_large`).
- **Dado** que soy socia, **entonces** recibo 403; sin sesión, 401.
- **Dado** los tests de fotos de productos (HU-30), **cuando** pasan, **entonces** siguen en verde.

## Endpoints

| Método | Ruta | Quién | Respuesta | Errores |
| --- | --- | --- | --- | --- |
| PUT | `/trainers/me/photo` | Trainer | 200 `TrainerOut` | 401, 403, 422 |
| DELETE | `/trainers/me/photo` | Trainer | 200 `TrainerOut` | 401, 403 |
| GET | `/trainers` | Público | 200 `list[TrainerOut]` (ahora con `photo_url`) | — |

`PUT` recibe un formulario multipart con el campo `file`. Cambia el esquema: columna
`trainer_profiles.photo_path` (texto, opcional), con su migración de Alembic.

## Interfaz

- "Mi perfil público": junto al avatar, "Cambiar foto" y "Quitar foto".
- "Entrenadoras": cada tarjeta enseña la foto si la hay; si no, las iniciales.
- Estados: subiendo, aviso verde al cambiarla y aviso rojo con el mensaje de la API.

## Fuera de alcance

- Que administración suba o quite la foto de una entrenadora.
- Recortar o comprimir la foto en el servidor.
- Fotos de socias.
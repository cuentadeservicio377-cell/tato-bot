# Guía de Deploy y Mantenimiento — Tato Bot

Bot de asistencia legal para Tato (Juan José Narváez Palacios).
Fork exclusivo de monday-bot adaptado para litigio en Guadalajara, MX.

---

## Primera vez: Configurar en Railway

### Paso 1 — Crear proyecto en Railway

1. Ir a [railway.app](https://railway.app) → **New Project**
2. **Deploy from GitHub repo** → seleccionar `tato-bot`
3. Railway detecta `railway.toml` automáticamente

### Paso 2 — Agregar PostgreSQL

1. En el proyecto Railway: **+ New** → **Database** → **Add PostgreSQL**
2. Railway inyecta `DATABASE_URL` automáticamente en el servicio

### Paso 3 — Variables de entorno

En Railway → tu servicio → **Variables**, agregar:

```
# Telegram
TELEGRAM_TOKEN=<token de @BotFather>

# Groq
GROQ_API_KEY=<api key de console.groq.com>

# Google OAuth
GOOGLE_CLIENT_ID=<client id de Google Cloud Console>
GOOGLE_CLIENT_SECRET=<client secret>
CALLBACK_URL=https://<tu-dominio>.railway.app/oauth/callback
RAILWAY_PUBLIC_URL=https://<tu-dominio>.railway.app
PORT=8080

# ---- Específico Tato Bot ----
TATO_USER_ID=<tu Telegram user ID — usa @userinfobot para saber>
GACETA_EMAIL_SENDER=<email desde el que llega Gaceta de Información>
SHEETS_EXPEDIENTES_ID=<ID de la Google Sheet de control>
SHEETS_EXPEDIENTES_RANGE=Expedientes!A:L
```

> El `DATABASE_URL` no hay que agregarlo — Railway lo inyecta solo al tener Postgres.

### Paso 4 — Dominio público (para OAuth)

En Railway → tu servicio → **Settings** → **Networking** → **Generate Domain**

Copiar ese dominio y actualizar `CALLBACK_URL` y `RAILWAY_PUBLIC_URL`.

### Paso 5 — Deploy

Railway hace deploy automático al conectar el repo.
Verificar en **Logs**:
```
Bot started
Scheduler started
```

Si ves errores de migración de DB, son normales en el primer arranque — el bot crea las tablas automáticamente.

---

## Primera sesión desde Telegram

1. Buscar el bot por su username
2. Enviar `/start` → comenzará el onboarding (nombre, zona horaria, etc.)
3. Al terminar onboarding, conectar Google: seguir el link OAuth que envía el bot
4. Verificar con `/expedientes` → debe responder (lista vacía al inicio)

---

## Estructura de archivos clave

```
bot.py              ← Punto de entrada. Handlers de Telegram.
scheduler.py        ← Jobs automáticos (boletín 9:30am, alertas 8:00am)
memory.py           ← Schema DB + funciones sync para scheduler
expedientes.py      ← CRUD de casos legales (async)
terminos.py         ← Gestión de términos procesales (async)
boletin.py          ← Procesamiento del PDF de Gaceta de Información
voice_processor.py  ← Notas de voz → transcripción Whisper → update expediente
google_services.py  ← Gmail (boletín), Sheets (expedientes), OAuth
railway.toml        ← Configuración de deploy
.env.example        ← Referencia de variables de entorno
SHEETS_SETUP.md     ← Instrucciones para configurar la Google Sheet
```

---

## Google Sheets — Configurar el control de expedientes

Ver instrucciones detalladas en `SHEETS_SETUP.md`.

Resumen: crear una hoja llamada `Expedientes` con columnas A-L, copiar el ID
del URL (`docs.google.com/spreadsheets/d/**ID**/edit`) y pegarlo en `SHEETS_EXPEDIENTES_ID`.

---

## Comandos del bot

| Comando | Función |
|---|---|
| `/expedientes` | Ver lista de expedientes activos |
| `/nuevo_expediente` | Registrar un expediente nuevo |
| `/terminos` | Ver términos urgentes (hoy, mañana, próximos 3 días) |
| `/boletin` | Procesar el boletín de hoy manualmente |
| `/pendientes` | Lista de pendientes ordenada por urgencia |
| `/start` | Iniciar o reiniciar el onboarding |
| `/conectar_google` | Reconectar cuenta de Google |

**Voz:** Enviar una nota de voz desde juzgados → el bot transcribe, extrae el expediente
y el acuerdo, actualiza la DB y sincroniza a Sheets.

---

## Jobs automáticos

| Job | Horario | Función |
|---|---|---|
| `boletin_diario` | 9:30 AM lun-vie (CDMX) | Busca email de Gaceta → descarga PDF → procesa → envía resumen |
| `alertas_terminos` | 8:00 AM lun-vie (CDMX) | Revisa términos urgentes → alerta si hay vencimientos hoy/mañana |

---

## Cómo hacer cambios al comportamiento del bot

### Cambiar el prompt del asistente

En `bot.py`, buscar `BASE_SYSTEM_PROMPT` y editar el texto.

```bash
git add bot.py
git commit -m "update: ajustar prompt del asistente"
git push
```

Railway redeploya automáticamente en ~2 minutos.

### Agregar un nuevo comando

1. Crear la función `async def cmd_nuevo(update, context)` en `bot.py`
2. Registrar en `main()`:
   ```python
   app.add_handler(CommandHandler("nuevo", cmd_nuevo))
   ```
3. Commit y push

### Cambiar el horario de los jobs

En `scheduler.py`, buscar `CronTrigger` y modificar `hour`/`minute`:

```python
# Cambiar boletín a 10:00 AM
scheduler.add_job(boletin_diario, CronTrigger(
    day_of_week="mon-fri", hour=10, minute=0,
    timezone="America/Mexico_City"
), id="boletin_diario")
```

### Agregar columna a la DB

En `memory.py`, agregar al array `migrations`:

```python
"ALTER TABLE users ADD COLUMN IF NOT EXISTS nueva_columna JSONB DEFAULT '{}'",
```

El bot aplica la migración automáticamente al arrancar. No hay que hacer nada más.

---

## Reconectar Google OAuth

Si los tokens expiran o se revocan:

1. Enviar `/conectar_google` desde Telegram
2. Seguir el link y autorizar de nuevo
3. El bot confirma la reconexión

---

## Verificar que todo funciona

```bash
# Desde Telegram:
/expedientes   → responde (lista o mensaje vacío)
/terminos      → responde
/pendientes    → responde

# En Railway Logs:
# Buscar: "Bot started", "Scheduler started"
# No debe haber errores de importación ni de DB
```

---

## Tests

```bash
cd tato-bot
source venv/bin/activate
pytest tests/ -v
# Esperado: 36 passed
```

---

*Tato Bot v1.0 — 2026-03-05*

<div align="center">

<br/>

```
████████╗ █████╗ ████████╗ ██████╗       ██████╗  ██████╗ ████████╗
╚══██╔══╝██╔══██╗╚══██╔══╝██╔═══██╗      ██╔══██╗██╔═══██╗╚══██╔══╝
   ██║   ███████║   ██║   ██║   ██║█████╗██████╔╝██║   ██║   ██║
   ██║   ██╔══██║   ██║   ██║   ██║╚════╝██╔══██╗██║   ██║   ██║
   ██║   ██║  ██║   ██║   ╚██████╔╝      ██████╔╝╚██████╔╝   ██║
   ╚═╝   ╚═╝  ╚═╝   ╚═╝    ╚═════╝       ╚═════╝  ╚═════╝    ╚═╝
```

**Asistente legal personal**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B_+_Whisper-F55036?style=flat-square)](https://groq.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Railway-336791?style=flat-square&logo=postgresql&logoColor=white)](https://railway.app)
[![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white)](https://railway.app)
[![Fork](https://img.shields.io/badge/Fork-monday--bot-8E44AD?style=flat-square)](https://github.com/ProfessorArmitage/monday-bot)

<br/>

*Boletín judicial diario · Notas de voz desde juzgados · Términos fatales · Control de expedientes en Sheets*

<br/>

</div>

---

## ¿Qué es Tato Bot?

Fork exclusivo de [monday-bot](https://github.com/ProfessorArmitage/monday-bot) adaptado para la práctica legal de un abogado litigante en Guadalajara, México.

**No es un asistente genérico** — está construido para un flujo de trabajo legal específico:

```
Tato llega a juzgados
      ↓
Envía nota de voz por Telegram
      ↓
Bot transcribe (Groq Whisper) y extrae: expediente, acuerdo, fecha próxima
      ↓
Actualiza DB + sincroniza fila en Google Sheets
```

```
9:30 AM lunes a viernes
      ↓
Bot descarga PDF de Gaceta de Información (email Gmail)
      ↓
Procesa con LLaMA 3.3 70B → detecta acuerdos de los expedientes de Tato
      ↓
Envía resumen a Telegram + actualiza DB + Sheets
```

---

## Diferencias con monday-bot

### Eliminado

| Componente | Razón |
|-----------|-------|
| `provisioning.py` | Reprovisión multi-usuario no necesaria (fork single-user) |
| Sistema de versioning/CHANGELOG | Sin usuarios múltiples |
| Comandos admin (`/debug_user`, `/ver_logs`) | Fork privado |
| Job semanal de reprovisión | Eliminado con provisioning |
| Skills evolutivas y catálogo de skills | Flujo legal no lo requiere |
| `/nueva_skill`, `/activar_skill`, `/evolucion` | Ídem |

### Agregado

| Componente | Descripción |
|-----------|-------------|
| `expedientes.py` | CRUD de casos legales (JSONB en PostgreSQL) |
| `terminos.py` | Gestión de plazos procesales + alertas de urgencia |
| `boletin.py` | Parser del boletín judicial PDF (pdfplumber + LLaMA) |
| `voice_processor.py` | Notas de voz → texto (Groq Whisper) → datos estructurados |
| `data/parse_docx.py` | Parser de los DOCX de control de expedientes de Tato |
| `data/seed.py` | Seeder one-time para cargar 324+ expedientes a la DB |
| `setup_sheets_for_user()` | Crea y pre-pobla Google Sheets automáticamente al conectar Google |

### Modificado

| Archivo | Cambio |
|--------|-------|
| `bot.py` | Prompt legal en lugar de asistente personal genérico. 5 comandos nuevos. Handler de voz. |
| `scheduler.py` | 2 jobs nuevos: `boletin_diario` (9:30 AM) + `alertas_terminos` (8:00 AM) |
| `google_services.py` | `setup_sheets_for_user()`, `create_spreadsheet()`, columnas A:L → A:N (14 cols) |
| `oauth_server.py` | Auto-crea Google Sheet en primer OAuth. Notifica con link directo. |
| `memory.py` | Columnas JSONB nuevas + helpers: `get_sheets_id`, `save_sheets_id` |

---

## Flujos principales

### 1. Boletín diario (automático)

```
9:30 AM lun-vie (hora CDMX)
  → Busca en Gmail email de Gaceta de Información
  → Descarga PDF adjunto
  → Extrae texto (pdfplumber)
  → LLaMA identifica acuerdos de los expedientes de Tato
  → Actualiza DB + Sheets
  → Envía resumen en Telegram
```

### 2. Nota de voz desde juzgados

```
Tato envía audio OGG en Telegram
  → Groq Whisper large-v3 transcribe
  → LLaMA extrae: numero_expediente, juzgado, accion, proximo_paso, fecha_proxima, termino_fatal
  → Actualiza expediente en DB
  → Sincroniza fila en Google Sheets
  → Confirma en Telegram
```

### 3. Alertas de términos (automático)

```
8:00 AM lun-vie (hora CDMX)
  → Lee términos procesales de DB
  → Clasifica: hoy / mañana / 3 días / sin acuerdo
  → Si hay urgentes → alerta en Telegram con tag ⚠️ FATAL
```

### 4. Setup de Google Sheets (automático en primer OAuth)

```
Tato conecta Google OAuth
  → Crea spreadsheet "Tato Bot — Control de Expedientes"
  → Crea 3 hojas: Expedientes (A:N), Pendientes (A:E), Términos (A:F)
  → Carga todos los expedientes de DB
  → Guarda ID del spreadsheet en DB
  → Envía link directo en Telegram
```

---

## Comandos

### Control legal
| Comando | Descripción |
|---------|-------------|
| `/expedientes` | Lista expedientes activos con partes, término y pendiente |
| `/nuevo_expediente` | Registrar un expediente nuevo |
| `/terminos` | Ver términos urgentes clasificados por proximidad |
| `/boletin` | Procesar el boletín de Gaceta del día (manual) |
| `/pendientes` | Lista de pendientes ordenada por urgencia |

### Google Workspace (heredado de monday-bot)
| Comando | Descripción |
|---------|-------------|
| `/conectar_google` | Conecta Google OAuth (auto-crea Sheets al conectar) |
| `/desconectar_google` | Revoca el acceso |
| `/mi_doc` | Ver Google Doc de memoria |
| `/sincronizar` | Sync manual Doc → DB |

### Esenciales (heredado)
| Comando | Descripción |
|---------|-------------|
| `/start` | Onboarding o saludo si ya hay sesión |
| `/ayuda` | Lista todos los comandos |
| `/memoria` | Ver memoria guardada |
| `/mi_zona` | Ver/cambiar timezone |

---

## Google Sheets — estructura

La hoja se crea automáticamente. Tres pestañas:

**Expedientes (A:N):**
```
A: No | B: Cód | C: Juzgado | D: Expediente | E: Partes | F: Monto | G: Estado
H: Últ. Acuerdo | I: Texto Acuerdo | J: Próximo Paso | K: Próx. Término | L: Fatal
M: Notas | N: Domicilio
```

**Pendientes (A:E):**
```
A: Juzgado | B: Expediente | C: Fecha | D: Último Acuerdo | E: Pendiente (nota)
```

**Términos (A:F):**
```
A: Expediente | B: Juzgado | C: Tipo | D: Fecha Vence | E: Fatal | F: Resuelto
```

---

## Arquitectura

```
tato-bot/
├── bot.py                  # Handlers Telegram + prompt legal + Groq SDK client
├── memory.py               # PostgreSQL + helpers sync + get/save_sheets_id
├── expedientes.py          # CRUD de casos legales (JSONB)
├── terminos.py             # Plazos procesales + clasificación urgencia
├── boletin.py              # PDF Gaceta → acuerdos estructurados
├── voice_processor.py      # Audio OGG → texto → update expediente
├── scheduler.py            # boletin_diario (9:30am) + alertas_terminos (8am)
├── google_services.py      # APIs Google + setup_sheets_for_user + create_spreadsheet
├── oauth_server.py         # OAuth callback + auto-setup Sheets
├── onboarding.py           # 9 pasos (heredado sin cambios)
├── conversation_context.py # Detección de contexto (heredado)
├── tz_utils.py             # Timezones DST-aware (heredado)
├── google_auth.py          # OAuth 2.0 (heredado)
├── workspace_memory.py     # Sync con Google Doc (heredado)
├── identity.py             # Identidad del asistente (heredado)
├── skills.py               # Motor de skills (heredado, sin catálogo)
├── data/
│   ├── parse_docx.py       # Parser DOCX control expedientes + pendientes
│   └── seed.py             # Seeder one-time desde archivos DOCX
├── GUIA_REDEPLOY.md        # Guía de deploys y mantenimiento
└── SHEETS_SETUP.md         # Instrucciones manuales Sheets (alternativa al auto-setup)
```

---

## DB — nuevas columnas

Además del schema de monday-bot, se agregan:

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS expedientes JSONB NOT NULL DEFAULT '[]';
ALTER TABLE users ADD COLUMN IF NOT EXISTS terminos    JSONB NOT NULL DEFAULT '[]';
ALTER TABLE users ADD COLUMN IF NOT EXISTS juzgados    JSONB NOT NULL DEFAULT '{}';
```

El spreadsheet ID de cada usuario se guarda en `juzgados._config.sheets_id`.

---

## Deploy

### Requisitos adicionales vs monday-bot

```env
# Específicos de Tato Bot
TATO_USER_ID=<telegram_user_id>          # ID de Telegram de Tato
GACETA_EMAIL_SENDER=<email>              # Remitente del email de Gaceta
SHEETS_EXPEDIENTES_ID=<sheet_id>         # Opcional — se auto-crea al conectar Google
SHEETS_EXPEDIENTES_RANGE=Expedientes!A:N
```

### Pasos de deploy

```bash
# 1. En Railway: New Project → Deploy from GitHub → seleccionar tato-bot
# 2. Agregar PostgreSQL (Railway lo conecta automáticamente)
# 3. Agregar todas las variables de entorno (ver .env.example)
# 4. Deploy automático al conectar el repo
```

### Seed de datos (después del primer /start)

```bash
cd tato-bot
source venv/bin/activate

python data/seed.py \
  --control  "ruta/al/CONTROL EXPEDIENTES.docx" \
  --pendientes "ruta/al/JUZGADOS PENDIENTES.docx" \
  --user-id <TATO_TELEGRAM_USER_ID>

# Output: 324 expedientes cargados (305 activos, 16 caducidad, 3 terminados)
# Luego Tato conecta Google → Sheets se crea automáticamente
```

### Google OAuth

Igual que monday-bot. Agregar en Google Cloud Console:
- URI de redirección: `https://<dominio>.railway.app/oauth/callback`
- APIs habilitadas: Calendar, Gmail, Drive, Docs, Sheets

---

## Stack

| Componente | Tecnología |
|-----------|-----------|
| Lenguaje | Python 3.12 |
| IA / Chat | Groq — LLaMA 3.3 70B |
| IA / Transcripción | Groq — Whisper large-v3 |
| Telegram | python-telegram-bot 21.5 |
| Base de datos | PostgreSQL (Railway) JSONB |
| PDF | pdfplumber 0.11.0 |
| DOCX | python-docx 1.1.2 |
| HTTP | httpx 0.27.2 |
| Scheduler | APScheduler 3.10.4 |
| OAuth server | aiohttp 3.9.5 |
| Deploy | Railway PaaS |

---

## Tests

```bash
source venv/bin/activate
pytest tests/ -v
# 36 passed
```

| Suite | Tests | Qué cubre |
|-------|-------|-----------|
| `test_expedientes.py` | 10 | CRUD, schema nuevo, formato Telegram |
| `test_terminos.py` | 9 | Plazos, urgencia, alertas |
| `test_boletin.py` | 6 | PDF parsing, Groq extraction, resumen |
| `test_voice_processor.py` | 7 | Whisper, extracción estructurada, confirmación |
| `test_google_services_legal.py` | 4 | Gmail boletín, Sheets A:N |

---

<div align="center">

**Tato Bot v1.0** · Fork de [monday-bot](https://github.com/ProfessorArmitage/monday-bot) · Python 3.12 · Groq · Railway

*Construido para la práctica legal de un abogado litigante — Guadalajara, México*

</div>

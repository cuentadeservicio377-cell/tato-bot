"""
oauth_server.py — Servidor web mínimo para recibir el callback de Google OAuth.

Corre en paralelo con el bot de Telegram.
Cuando Google redirige al usuario después de autorizar,
este servidor recibe el código, lo intercambia por tokens
y los guarda en PostgreSQL.
"""

import asyncio
import logging
from aiohttp import web
from google_auth import exchange_code_for_tokens
from datetime import datetime, timedelta
import memory

logger = logging.getLogger(__name__)

# El bot de Telegram para poder notificar al usuario
_bot = None

def set_bot(bot):
    """Registra el bot para poder enviar mensajes de confirmación."""
    global _bot
    _bot = bot


async def oauth_callback(request: web.Request) -> web.Response:
    """
    Recibe el callback de Google OAuth.
    URL: /oauth/callback?code=...&state=USER_ID
    """
    code    = request.rel_url.query.get("code")
    user_id = request.rel_url.query.get("state")
    error   = request.rel_url.query.get("error")

    if error:
        return web.Response(
            text="❌ Autorización cancelada. Puedes cerrar esta ventana.",
            content_type="text/html"
        )

    if not code or not user_id:
        return web.Response(text="❌ Parámetros inválidos.", content_type="text/html")

    try:
        # Intercambiar código por tokens
        tokens = await exchange_code_for_tokens(code)

        # Calcular cuándo expira el access_token
        tokens["expires_at"] = (
            datetime.now() + timedelta(seconds=tokens.get("expires_in", 3600))
        ).isoformat()

        # Guardar tokens en PostgreSQL
        memory.save_google_tokens(int(user_id), tokens)

        # Setup automático de Google Sheets si es la primera vez
        sheet_url = ""
        existing_id = memory.get_sheets_id(int(user_id))
        if not existing_id:
            try:
                from google_services import setup_sheets_for_user
                sheet_id = await setup_sheets_for_user(int(user_id))
                sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                logger.info("[oauth] Sheets creado: %s para user_id=%s", sheet_id, user_id)
            except Exception as e:
                logger.error("[oauth] Error creando Sheets: %s", e)

        # Notificar al usuario en Telegram
        if _bot:
            expedientes = memory.get_expedientes_sync(int(user_id))
            n_exp = len(expedientes)
            n_activos = sum(1 for e in expedientes if e.get("estado", "activo") == "activo")

            sheets_line = (
                f"\n📊 Hoja de control creada: [Abrir Sheets]({sheet_url})\n"
                f"   {n_exp} expedientes cargados ({n_activos} activos)"
                if sheet_url else "\n📊 Google Sheets disponible"
            )

            await _bot.send_message(
                chat_id=int(user_id),
                text=(
                    "✅ *¡Google conectado exitosamente!*\n\n"
                    "Ya puedo acceder a:\n"
                    "📅 Google Calendar\n"
                    "📧 Gmail\n"
                    "📝 Google Docs\n"
                    "📁 Google Drive\n"
                    f"{sheets_line}\n\n"
                    "Prueba enviando una nota de voz desde juzgados."
                ),
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )

        return web.Response(
            text="<h2>✅ ¡Cuenta conectada!</h2><p>Puedes cerrar esta ventana y volver a Telegram.</p>",
            content_type="text/html"
        )

    except Exception as e:
        return web.Response(text=f"❌ Error: {str(e)}", content_type="text/html")


async def start_oauth_server():
    """Arranca el servidor web en el puerto que Railway asigna."""
    import os
    port = int(os.getenv("PORT", 8080))

    app = web.Application()
    app.router.add_get("/oauth/callback", oauth_callback)
    app.router.add_get("/health", lambda r: web.Response(text="ok"))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ OAuth server corriendo en puerto {port}")

"""
voice_processor.py — Procesa voice notes de Telegram de Tato.

Flujo:
  1. Tato envía voice note desde juzgados
  2. descargar_audio_telegram() → bytes del audio (OGG/Opus)
  3. transcribir_audio() → texto vía Groq Whisper
  4. extraer_actualizacion_juzgado() → entidades estructuradas con Groq LLaMA
  5. formatear_confirmacion() → mensaje de confirmación para Telegram
  6. El handler en bot.py aplica los updates al expediente y Sheets
"""

import io
import json
import logging
from datetime import date

logger = logging.getLogger(__name__)


async def descargar_audio_telegram(bot, file_id: str) -> bytes:
    """
    Descarga el archivo de audio OGG de Telegram y retorna los bytes.
    """
    file = await bot.get_file(file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    return buf.getvalue()


async def transcribir_audio(groq_client, audio_bytes: bytes) -> str:
    """
    Transcribe audio OGG (Opus) usando Groq Whisper large-v3.
    Retorna el texto transcrito, o "" si falla.
    """
    try:
        transcription = groq_client.audio.transcriptions.create(
            file=("audio.ogg", io.BytesIO(audio_bytes)),
            model="whisper-large-v3",
            language="es",
            response_format="text",
        )
        if isinstance(transcription, str):
            return transcription.strip()
        return transcription.text.strip() if hasattr(transcription, "text") else str(transcription).strip()
    except Exception as e:
        logger.error(f"[voice_processor] Error en transcripción Whisper: {e}")
        return ""


async def extraer_actualizacion_juzgado(groq_client, transcripcion: str) -> dict:
    """
    Extrae datos estructurados de una transcripción de nota de voz desde juzgados.
    Retorna dict con la actualización o {} si no pudo parsear.
    """
    hoy = date.today().isoformat()
    prompt = f"""Eres asistente de un abogado litigante mexicano.
Del siguiente texto dictado mientras está en juzgados, extrae la información en JSON.

Campos a extraer:
- numero_expediente: string (ej: "2-10", "33") o null si no menciona
- juzgado: string (nombre del juzgado mencionado) o null
- accion_realizada: string (qué hizo hoy en ese expediente)
- proximo_paso: string (qué hay que hacer después) o null
- fecha_proxima: string en formato YYYY-MM-DD si menciona una fecha, o null
  (hoy es {hoy}; "viernes" = próximo viernes, "el 13" = {hoy[:7]}-13, etc.)
- nuevo_termino_fatal: boolean (true si menciona término fatal/perentorio)
- notas: string con información adicional relevante o ""

Devuelve SOLO el JSON, sin texto extra, sin markdown, sin explicaciones.

Texto transcrito:
{transcripcion}
"""
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )
        content = response.choices[0].message.content.strip()

        # Limpiar markdown si viene envuelto
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        return json.loads(content)

    except json.JSONDecodeError:
        logger.error(f"[voice_processor] JSON inválido de Groq para transcripción: {transcripcion[:100]}")
        return {}
    except Exception as e:
        logger.error(f"[voice_processor] Error en extracción: {e}")
        return {}


def formatear_confirmacion(actualizacion: dict) -> str:
    """
    Genera el mensaje de confirmación para Telegram después de procesar un voice note.
    """
    if not actualizacion:
        return (
            "No pude extraer información estructurada del audio. "
            "Intenta de nuevo mencionando el número de expediente y juzgado."
        )

    num = actualizacion.get("numero_expediente") or "?"
    juzgado = actualizacion.get("juzgado") or "juzgado no identificado"
    accion = actualizacion.get("accion_realizada") or "—"
    siguiente = actualizacion.get("proximo_paso") or "—"
    fecha = actualizacion.get("fecha_proxima")
    fatal = actualizacion.get("nuevo_termino_fatal", False)
    notas = actualizacion.get("notas", "")

    lines = [f"✅ *Expediente {num}* — {juzgado}"]
    lines.append(f"• Acción: {accion}")
    if siguiente and siguiente != "—":
        lines.append(f"• Siguiente: {siguiente}")
    if fecha:
        lines.append(f"• Fecha: {fecha}")
    if fatal:
        lines.append("⚠️ Término fatal registrado")
    if notas:
        lines.append(f"• Notas: {notas}")

    return "\n".join(lines)

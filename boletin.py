"""
boletin.py — Procesamiento del boletín judicial diario (PDF de Gaceta de Información).

Flujo:
  1. scheduler llama a get_boletin_email_today() → obtiene email de Gmail
  2. download_email_attachment() → descarga el PDF adjunto
  3. extraer_texto_pdf() → extrae texto del PDF con pdfplumber
  4. procesar_boletin_con_groq() → Groq identifica acuerdos de los expedientes de Tato
  5. aplicar_acuerdos_a_expedientes() → actualiza DB + Sheets
  6. generar_resumen_boletin() → genera mensaje para Telegram
"""

import io
import json
import logging
from datetime import date, timedelta

import pdfplumber

logger = logging.getLogger(__name__)


def extraer_texto_pdf(pdf_bytes: bytes) -> str:
    """
    Extrae texto de un PDF usando pdfplumber.
    Retorna string con todo el contenido, o "" si el PDF es inválido.
    """
    try:
        texto = ""
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    texto += page_text + "\n"
        return texto.strip()
    except Exception as e:
        logger.error(f"[boletin] Error extrayendo texto del PDF: {e}")
        return ""


async def procesar_boletin_con_groq(
    groq_client, pdf_text: str, expedientes_activos: list
) -> list:
    """
    Usa Groq LLaMA para extraer acuerdos relevantes del texto del boletín.
    Solo busca los expedientes registrados como activos de Tato.
    Retorna lista de dicts, uno por expediente encontrado.
    """
    if not pdf_text or not expedientes_activos:
        return []

    numeros = [e.get("numero", "") for e in expedientes_activos if e.get("numero")]
    if not numeros:
        return []

    numeros_str = ", ".join(numeros)
    hoy = date.today().isoformat()

    prompt = f"""Eres asistente legal. Del siguiente boletín judicial, extrae ÚNICAMENTE los acuerdos de estos expedientes: {numeros_str}

Para cada acuerdo encontrado, devuelve un objeto JSON con exactamente estas claves:
- numero_expediente: string (el número como aparece en el boletín)
- juzgado: string (nombre del juzgado)
- extracto_acuerdo: string (resumen del acuerdo en 1-2 oraciones)
- requiere_accion: boolean (true si Tato debe hacer algo)
- nuevo_termino: string o null (descripción del término si se abrió uno)
- dias_termino: number o null (número de días del término si aplica)
- termino_fatal: boolean (true si es un término fatal/perentorio)

Devuelve SOLO un JSON array. Sin texto adicional, sin markdown, sin explicaciones.
Si ningún expediente de la lista aparece en el boletín, devuelve: []

Fecha de hoy: {hoy}
Expedientes a buscar: {numeros_str}

Boletín:
{pdf_text[:8000]}
"""
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
        )
        content = response.choices[0].message.content.strip()

        # Limpiar markdown si viene con bloques de código
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        return json.loads(content)

    except json.JSONDecodeError as e:
        logger.error(f"[boletin] JSON inválido de Groq: {e}")
        return []
    except Exception as e:
        logger.error(f"[boletin] Error llamando Groq: {e}")
        return []


def generar_resumen_boletin(acuerdos: list) -> str:
    """
    Genera el mensaje de Telegram del resumen diario del boletín.
    """
    if not acuerdos:
        return "📋 Boletín del día revisado — sin novedades en tus expedientes."

    n = len(acuerdos)
    lines = [f"📋 *Boletín del día — {n} acuerdo{'s' if n != 1 else ''} de tus asuntos:*\n"]

    for a in acuerdos:
        num = a.get("numero_expediente", "?")
        juzgado = a.get("juzgado", "?")
        extracto = a.get("extracto_acuerdo", "")
        dias = a.get("dias_termino")
        fatal = a.get("termino_fatal", False)

        fatal_tag = " 🚨 *FATAL*" if fatal else ""
        termino_info = f" (término: {dias} días{fatal_tag})" if dias else (fatal_tag if fatal_tag else "")

        lines.append(f"• *{num}* — {juzgado}")
        if extracto:
            lines.append(f"  _{extracto}_{termino_info}")
        if a.get("requiere_accion"):
            lines.append("  ✅ Requiere acción")

    return "\n".join(lines).strip()


async def aplicar_acuerdos_a_expedientes(
    db_pool,
    user_id: int,
    acuerdos: list,
    terminos_module,
    expedientes_module,
    google_services_module=None,
) -> None:
    """
    Por cada acuerdo del boletín:
    1. Actualiza el expediente en DB (último acuerdo, próximo término)
    2. Registra el término si se abrió uno
    3. Actualiza la fila en Google Sheets (si google_services_module disponible)
    """
    for acuerdo in acuerdos:
        numero = acuerdo.get("numero_expediente")
        if not numero:
            continue

        updates = {
            "ultimo_acuerdo": date.today().isoformat(),
            "ultimo_acuerdo_texto": acuerdo.get("extracto_acuerdo", ""),
        }

        # Si hay término nuevo, calculamos la fecha de vencimiento
        if acuerdo.get("dias_termino"):
            vence = (date.today() + timedelta(days=acuerdo["dias_termino"])).isoformat()
            updates["proximo_termino"] = vence
            updates["termino_fatal"] = acuerdo.get("termino_fatal", False)

            try:
                await terminos_module.add_termino(db_pool, user_id, {
                    "expediente_numero": numero,
                    "tipo": acuerdo.get("nuevo_termino") or "termino_procesal",
                    "fatal": acuerdo.get("termino_fatal", False),
                    "vence": vence,
                    "resuelto": False,
                })
            except Exception as e:
                logger.error(f"[boletin] Error registrando término para {numero}: {e}")

        # Actualizar expediente en DB
        found = await expedientes_module.update_expediente(db_pool, user_id, numero, updates)

        # Sincronizar a Sheets
        if found and google_services_module:
            try:
                expediente = await expedientes_module.get_expediente_by_numero(
                    db_pool, user_id, numero
                )
                if expediente and expediente.get("sheets_row"):
                    await google_services_module.update_sheets_expediente(user_id, expediente)
            except Exception as e:
                logger.error(f"[boletin] Error actualizando Sheets para {numero}: {e}")

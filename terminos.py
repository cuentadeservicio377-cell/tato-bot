"""
terminos.py — Gestión de términos procesales de Tato.

Rastrea fechas límite, detecta fatales y genera alertas diarias.
Los términos viven en users.terminos (JSONB array en PostgreSQL).
"""

import json
import uuid
from datetime import date, datetime, timedelta
from typing import Optional


async def get_terminos(db_pool, user_id: int) -> list:
    """Devuelve todos los términos registrados del usuario."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT terminos FROM users WHERE user_id = $1", user_id
        )
        if not row or not row["terminos"]:
            return []
        data = row["terminos"]
        if isinstance(data, str):
            return json.loads(data)
        return list(data) if data else []


async def save_terminos(db_pool, user_id: int, terminos: list) -> None:
    """Persiste la lista completa de términos."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET terminos = $1::jsonb WHERE user_id = $2",
            json.dumps(terminos, ensure_ascii=False),
            user_id,
        )


async def add_termino(db_pool, user_id: int, termino: dict) -> dict:
    """
    Registra un término nuevo.
    Si ya existe uno activo para el mismo expediente+tipo, lo actualiza
    en lugar de duplicar.
    """
    terminos = await get_terminos(db_pool, user_id)

    # Buscar si ya existe uno activo para el mismo expediente+tipo
    for i, t in enumerate(terminos):
        if (
            t.get("expediente_numero") == termino.get("expediente_numero")
            and t.get("tipo") == termino.get("tipo")
            and not t.get("resuelto")
        ):
            terminos[i].update(termino)
            await save_terminos(db_pool, user_id, terminos)
            return terminos[i]

    # Nuevo término
    termino["id"] = str(uuid.uuid4())
    termino.setdefault("resuelto", False)
    termino["creado_en"] = datetime.now().isoformat()
    terminos.append(termino)
    await save_terminos(db_pool, user_id, terminos)
    return termino


async def marcar_resuelto(db_pool, user_id: int, termino_id: str) -> bool:
    """
    Marca un término como resuelto.
    Retorna True si lo encontró, False si no existía.
    """
    terminos = await get_terminos(db_pool, user_id)
    for i, t in enumerate(terminos):
        if t.get("id") == termino_id:
            terminos[i]["resuelto"] = True
            terminos[i]["resuelto_en"] = datetime.now().isoformat()
            await save_terminos(db_pool, user_id, terminos)
            return True
    return False


async def get_terminos_urgentes(db_pool, user_id: int) -> dict:
    """
    Clasifica los términos no resueltos por urgencia:
    - hoy: vencen hoy o ya vencieron
    - manana: vencen mañana
    - tres_dias: vencen en 2-3 días
    - sin_acuerdo: llevan más de 7 días esperando un acuerdo (campo espera_acuerdo_desde)
    """
    terminos = await get_terminos(db_pool, user_id)
    hoy = date.today()
    resultado = {"hoy": [], "manana": [], "tres_dias": [], "sin_acuerdo": []}

    for t in terminos:
        if t.get("resuelto"):
            continue

        vence_str = t.get("vence")
        if vence_str:
            try:
                vence = date.fromisoformat(vence_str)
                dias = (vence - hoy).days
                if dias <= 0:
                    resultado["hoy"].append(t)
                elif dias == 1:
                    resultado["manana"].append(t)
                elif dias <= 3:
                    resultado["tres_dias"].append(t)
            except ValueError:
                pass

        if t.get("espera_acuerdo_desde"):
            try:
                desde = date.fromisoformat(t["espera_acuerdo_desde"])
                if (hoy - desde).days >= 7:
                    resultado["sin_acuerdo"].append(t)
            except ValueError:
                pass

    # Ordenar fatales primero en cada grupo
    for key in ["hoy", "manana", "tres_dias"]:
        resultado[key].sort(key=lambda x: (not x.get("fatal", False),))

    return resultado


def generar_mensaje_alertas(urgentes: dict) -> str:
    """
    Genera el mensaje de Telegram con las alertas del día.
    Retorna string vacío si no hay nada urgente.
    """
    lines = []

    if urgentes.get("hoy"):
        lines.append("⚠️ *TÉRMINOS QUE VENCEN HOY:*")
        for t in urgentes["hoy"]:
            fatal_tag = " 🚨 *FATAL*" if t.get("fatal") else ""
            lines.append(
                f"  • {t.get('expediente_numero', '?')} — {t.get('tipo', '?')}{fatal_tag}"
            )

    if urgentes.get("manana"):
        lines.append("\n⏰ *Vencen mañana:*")
        for t in urgentes["manana"]:
            fatal_tag = " ⚠️ FATAL" if t.get("fatal") else ""
            lines.append(
                f"  • {t.get('expediente_numero', '?')} — {t.get('tipo', '?')}{fatal_tag}"
            )

    if urgentes.get("tres_dias"):
        lines.append("\n📅 *Vencen en 2-3 días:*")
        for t in urgentes["tres_dias"]:
            lines.append(
                f"  • {t.get('expediente_numero', '?')} — {t.get('tipo', '?')}"
            )

    if urgentes.get("sin_acuerdo"):
        lines.append("\n💡 *Sin acuerdo esperado (más de 7 días):*")
        for t in urgentes["sin_acuerdo"]:
            lines.append(
                f"  • {t.get('expediente_numero', '?')} — considera ir a preguntar"
            )

    return "\n".join(lines) if lines else ""

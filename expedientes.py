"""
expedientes.py — CRUD de expedientes legales activos de Tato.

Cada expediente vive en users.expedientes (JSONB array en PostgreSQL)
y tiene una fila espejo en Google Sheets como control visible.
"""

import json
import uuid
from datetime import datetime
from typing import Optional


async def get_expedientes(db_pool, user_id: int) -> list:
    """Devuelve todos los expedientes del usuario (activos y terminados)."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT expedientes FROM users WHERE user_id = $1", user_id
        )
        if not row or not row["expedientes"]:
            return []
        data = row["expedientes"]
        if isinstance(data, str):
            return json.loads(data)
        return list(data) if data else []


async def save_expedientes(db_pool, user_id: int, expedientes: list) -> None:
    """Persiste la lista completa de expedientes en PostgreSQL."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET expedientes = $1::jsonb WHERE user_id = $2",
            json.dumps(expedientes, ensure_ascii=False),
            user_id,
        )


async def get_expediente_by_numero(
    db_pool, user_id: int, numero: str
) -> Optional[dict]:
    """Busca un expediente por número (ej: '2-10', '33'). Retorna None si no existe."""
    expedientes = await get_expedientes(db_pool, user_id)
    numero_clean = numero.strip()
    for exp in expedientes:
        if exp.get("numero", "").strip() == numero_clean:
            return exp
    return None


async def add_expediente(db_pool, user_id: int, expediente: dict) -> dict:
    """
    Agrega un expediente nuevo.
    Asigna id automático, estado 'activo' y timestamp si no los tiene.
    """
    expedientes = await get_expedientes(db_pool, user_id)
    expediente["id"] = str(uuid.uuid4())
    expediente.setdefault("estado", "activo")
    expediente["ultima_actualizacion"] = datetime.now().isoformat()
    expedientes.append(expediente)
    await save_expedientes(db_pool, user_id, expedientes)
    return expediente


async def update_expediente(
    db_pool, user_id: int, numero: str, updates: dict
) -> bool:
    """
    Actualiza campos de un expediente existente.
    Retorna True si encontró y actualizó, False si no existía.
    """
    expedientes = await get_expedientes(db_pool, user_id)
    numero_clean = numero.strip()
    found = False
    for i, exp in enumerate(expedientes):
        if exp.get("numero", "").strip() == numero_clean:
            expedientes[i].update(updates)
            expedientes[i]["ultima_actualizacion"] = datetime.now().isoformat()
            found = True
            break
    if found:
        await save_expedientes(db_pool, user_id, expedientes)
    return found


async def get_expedientes_activos(db_pool, user_id: int) -> list:
    """Retorna solo los expedientes con estado 'activo'."""
    todos = await get_expedientes(db_pool, user_id)
    return [e for e in todos if e.get("estado", "activo") == "activo"]


async def format_expedientes_list(expedientes: list) -> str:
    """Formatea la lista de expedientes para mostrar en Telegram (Markdown)."""
    if not expedientes:
        return "No tienes expedientes registrados."

    lines = [f"*Expedientes activos ({len(expedientes)}):*\n"]
    for exp in expedientes:
        termino = exp.get("proximo_termino", "—")
        fatal_tag = " ⚠️ FATAL" if exp.get("termino_fatal") else ""
        etapa = exp.get("etapa", "—")
        lines.append(
            f"• *{exp.get('numero', '?')}* — {exp.get('juzgado', '?')}\n"
            f"  Cliente: {exp.get('cliente', '?')} | Etapa: {etapa}\n"
            f"  Próximo término: {termino}{fatal_tag}"
        )
    return "\n\n".join([lines[0]] + lines[1:])

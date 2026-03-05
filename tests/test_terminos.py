import pytest
import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock
from terminos import (
    get_terminos, add_termino, get_terminos_urgentes,
    marcar_resuelto, generar_mensaje_alertas
)

USER_ID = 12345


def make_mock_pool(terminos_data=None):
    pool = MagicMock()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"terminos": json.dumps(terminos_data or [])})
    conn.execute = AsyncMock()
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool, conn


def termino_en_dias(n: int, fatal=False, exp_num=None) -> dict:
    fecha = (date.today() + timedelta(days=n)).isoformat()
    return {
        "id": f"t-{n}",
        "expediente_numero": exp_num or f"exp-{n}",
        "tipo": "alegatos",
        "fatal": fatal,
        "vence": fecha,
        "resuelto": False,
    }


@pytest.mark.asyncio
async def test_get_terminos_empty():
    pool, _ = make_mock_pool([])
    result = await get_terminos(pool, USER_ID)
    assert result == []


@pytest.mark.asyncio
async def test_add_termino_assigns_id():
    pool, conn = make_mock_pool([])
    t = {
        "expediente_numero": "2-10", "tipo": "alegatos",
        "fatal": True, "vence": date.today().isoformat(), "resuelto": False
    }
    result = await add_termino(pool, USER_ID, t)
    assert "id" in result
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_add_termino_updates_existing():
    """Si ya existe un término para el mismo expediente+tipo, lo actualiza en lugar de duplicar."""
    existing = [{
        "id": "t-exist", "expediente_numero": "2-10",
        "tipo": "alegatos", "fatal": False,
        "vence": date.today().isoformat(), "resuelto": False
    }]
    pool, conn = make_mock_pool(existing)
    nuevo = {
        "expediente_numero": "2-10", "tipo": "alegatos",
        "fatal": True, "vence": (date.today() + timedelta(days=2)).isoformat()
    }
    result = await add_termino(pool, USER_ID, nuevo)
    assert result["id"] == "t-exist"  # Same ID — updated, not duplicated
    assert result["fatal"] is True


@pytest.mark.asyncio
async def test_get_terminos_urgentes_clasifica_bien():
    terminos = [
        termino_en_dias(0, fatal=True),
        termino_en_dias(1),
        termino_en_dias(3),
        termino_en_dias(10),
    ]
    pool, _ = make_mock_pool(terminos)
    resultado = await get_terminos_urgentes(pool, USER_ID)
    assert len(resultado["hoy"]) == 1
    assert resultado["hoy"][0]["fatal"] is True
    assert len(resultado["manana"]) == 1
    assert len(resultado["tres_dias"]) == 1


@pytest.mark.asyncio
async def test_get_terminos_urgentes_ignora_resueltos():
    terminos = [
        {**termino_en_dias(0), "resuelto": True},  # Resuelto — debe ignorarse
        termino_en_dias(1),
    ]
    pool, _ = make_mock_pool(terminos)
    resultado = await get_terminos_urgentes(pool, USER_ID)
    assert len(resultado["hoy"]) == 0
    assert len(resultado["manana"]) == 1


@pytest.mark.asyncio
async def test_marcar_resuelto():
    terminos = [{"id": "t-1", "expediente_numero": "2-10", "resuelto": False}]
    pool, conn = make_mock_pool(terminos)
    result = await marcar_resuelto(pool, USER_ID, "t-1")
    assert result is True
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_marcar_resuelto_not_found():
    pool, conn = make_mock_pool([])
    result = await marcar_resuelto(pool, USER_ID, "t-inexistente")
    assert result is False
    conn.execute.assert_not_called()


def test_generar_mensaje_alertas_con_fatal():
    urgentes = {
        "hoy": [{"expediente_numero": "2-10", "tipo": "alegatos", "fatal": True}],
        "manana": [],
        "tres_dias": [],
        "sin_acuerdo": [],
    }
    msg = generar_mensaje_alertas(urgentes)
    assert "2-10" in msg
    assert "FATAL" in msg.upper() or "🚨" in msg


def test_generar_mensaje_alertas_vacio():
    urgentes = {"hoy": [], "manana": [], "tres_dias": [], "sin_acuerdo": []}
    msg = generar_mensaje_alertas(urgentes)
    assert msg == ""

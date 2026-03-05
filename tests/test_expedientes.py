import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from expedientes import (
    get_expedientes, save_expedientes,
    get_expediente_by_numero, update_expediente,
    add_expediente, get_expedientes_activos, format_expedientes_list
)

USER_ID = 12345


def make_mock_pool(data=None):
    pool = MagicMock()
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"expedientes": json.dumps(data or [])})
    conn.execute = AsyncMock()
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool, conn


@pytest.mark.asyncio
async def test_get_expedientes_empty():
    pool, _ = make_mock_pool([])
    result = await get_expedientes(pool, USER_ID)
    assert result == []


@pytest.mark.asyncio
async def test_get_expedientes_returns_list():
    data = [{"numero": "2-10", "juzgado": "Primero Mercantil", "cliente": "Alvarez"}]
    pool, _ = make_mock_pool(data)
    result = await get_expedientes(pool, USER_ID)
    assert len(result) == 1
    assert result[0]["numero"] == "2-10"


@pytest.mark.asyncio
async def test_get_expediente_by_numero_found():
    data = [{"numero": "2-10", "juzgado": "Primero Mercantil"}]
    pool, _ = make_mock_pool(data)
    result = await get_expediente_by_numero(pool, USER_ID, "2-10")
    assert result is not None
    assert result["juzgado"] == "Primero Mercantil"


@pytest.mark.asyncio
async def test_get_expediente_by_numero_not_found():
    pool, _ = make_mock_pool([])
    result = await get_expediente_by_numero(pool, USER_ID, "99-99")
    assert result is None


@pytest.mark.asyncio
async def test_add_expediente_assigns_id():
    pool, conn = make_mock_pool([])
    nuevo = {"numero": "5-20", "juzgado": "Cuarto Familiar", "cliente": "Lopez"}
    result = await add_expediente(pool, USER_ID, nuevo)
    assert "id" in result
    assert result["estado"] == "activo"
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_expediente_modifies_field():
    data = [{"numero": "2-10", "juzgado": "Primero Mercantil", "etapa": "alegatos"}]
    pool, conn = make_mock_pool(data)
    found = await update_expediente(pool, USER_ID, "2-10", {"etapa": "citacion_sentencia"})
    assert found is True
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_expediente_returns_false_when_not_found():
    pool, conn = make_mock_pool([])
    found = await update_expediente(pool, USER_ID, "99-99", {"etapa": "x"})
    assert found is False
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_expedientes_activos_filters_terminados():
    data = [
        {"numero": "2-10", "estado": "activo"},
        {"numero": "5-20", "estado": "terminado"},
    ]
    pool, _ = make_mock_pool(data)
    result = await get_expedientes_activos(pool, USER_ID)
    assert len(result) == 1
    assert result[0]["numero"] == "2-10"


@pytest.mark.asyncio
async def test_format_expedientes_list_empty():
    msg = await format_expedientes_list([])
    assert "no tienes" in msg.lower()


@pytest.mark.asyncio
async def test_format_expedientes_list_with_data():
    expedientes = [
        {
            "numero": "2-10", "juzgado": "Primero Mercantil",
            "cliente": "Alvarez", "etapa": "alegatos",
            "proximo_termino": "2026-03-07", "termino_fatal": True
        }
    ]
    msg = await format_expedientes_list(expedientes)
    assert "2-10" in msg
    assert "FATAL" in msg.upper() or "fatal" in msg.lower() or "⚠️" in msg

"""Tests for voice_processor.py — voice note → structured court update."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from voice_processor import extraer_actualizacion_juzgado, formatear_confirmacion


def make_mock_groq(json_content: str):
    """Returns a mock Groq client that returns the given JSON content."""
    mock_groq = MagicMock()
    mock_groq.chat.completions.create = MagicMock(
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content=json_content))]
        )
    )
    return mock_groq


@pytest.mark.asyncio
async def test_extraer_actualizacion_detecta_expediente():
    """Verifica que se extrae el número de expediente de la transcripción."""
    mock_groq = make_mock_groq(
        '{"numero_expediente": "2-10", "juzgado": "Primero Civil", '
        '"accion_realizada": "entregó oficios", "proximo_paso": "ratificación", '
        '"fecha_proxima": "2026-03-13", "nuevo_termino_fatal": false, "notas": ""}'
    )
    result = await extraer_actualizacion_juzgado(mock_groq, "Estoy en Primero Civil, expediente 2-10")
    assert result["numero_expediente"] == "2-10"
    assert result["juzgado"] == "Primero Civil"
    assert result["accion_realizada"] != ""


@pytest.mark.asyncio
async def test_extraer_actualizacion_detecta_fatal():
    """Verifica que nuevo_termino_fatal se extrae correctamente."""
    mock_groq = make_mock_groq(
        '{"numero_expediente": "5-20", "juzgado": "Cuarto Familiar", '
        '"accion_realizada": "presentó escrito", "proximo_paso": "esperar acuerdo", '
        '"fecha_proxima": null, "nuevo_termino_fatal": true, "notas": ""}'
    )
    result = await extraer_actualizacion_juzgado(mock_groq, "...")
    assert result["nuevo_termino_fatal"] is True


@pytest.mark.asyncio
async def test_extraer_actualizacion_maneja_json_invalido():
    """Si Groq devuelve texto inválido, retorna dict vacío sin crashear."""
    mock_groq = make_mock_groq("esto no es json válido")
    result = await extraer_actualizacion_juzgado(mock_groq, "texto cualquiera")
    assert isinstance(result, dict)
    assert result == {}


@pytest.mark.asyncio
async def test_extraer_actualizacion_maneja_markdown():
    """Si Groq devuelve JSON envuelto en markdown, lo limpia correctamente."""
    json_str = '{"numero_expediente": "33", "juzgado": "Tercera Sala", "accion_realizada": "revisó", "proximo_paso": null, "fecha_proxima": null, "nuevo_termino_fatal": false, "notas": ""}'
    mock_groq = make_mock_groq(f"```json\n{json_str}\n```")
    result = await extraer_actualizacion_juzgado(mock_groq, "...")
    assert result.get("numero_expediente") == "33"


def test_formatear_confirmacion_con_datos():
    actualizacion = {
        "numero_expediente": "2-10",
        "juzgado": "Primero Civil",
        "accion_realizada": "entregó oficios",
        "proximo_paso": "ratificación",
        "fecha_proxima": "2026-03-13",
        "nuevo_termino_fatal": False,
    }
    msg = formatear_confirmacion(actualizacion)
    assert "2-10" in msg
    assert "2026-03-13" in msg or "13" in msg
    assert "entregó oficios" in msg or "oficios" in msg


def test_formatear_confirmacion_con_fatal():
    actualizacion = {
        "numero_expediente": "5-20",
        "juzgado": "Cuarto Familiar",
        "accion_realizada": "presentó escrito",
        "proximo_paso": None,
        "fecha_proxima": None,
        "nuevo_termino_fatal": True,
    }
    msg = formatear_confirmacion(actualizacion)
    assert "5-20" in msg
    assert "fatal" in msg.lower() or "⚠️" in msg


def test_formatear_confirmacion_vacia():
    msg = formatear_confirmacion({})
    assert "no pude" in msg.lower() or "intenta" in msg.lower()

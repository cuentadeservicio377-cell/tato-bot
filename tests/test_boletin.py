"""Tests for boletin.py — judicial bulletin PDF processing."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from boletin import extraer_texto_pdf, generar_resumen_boletin


def make_minimal_pdf() -> bytes:
    """Creates a minimal valid PDF in memory using only stdlib."""
    # Minimal PDF with some text content
    content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Expediente 2-10 Mercantil) Tj ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000360 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
441
%%EOF"""
    return content


def test_extraer_texto_pdf_returns_string():
    """extraer_texto_pdf must return a string (even if empty for minimal PDF)."""
    pdf_bytes = make_minimal_pdf()
    result = extraer_texto_pdf(pdf_bytes)
    assert isinstance(result, str)


def test_extraer_texto_pdf_bad_bytes_returns_empty():
    """On invalid PDF bytes, should return empty string without raising."""
    result = extraer_texto_pdf(b"esto no es un pdf")
    assert isinstance(result, str)
    assert result == ""


def test_generar_resumen_boletin_vacio():
    result = generar_resumen_boletin([])
    assert "sin novedades" in result.lower()


def test_generar_resumen_boletin_con_acuerdos():
    acuerdos = [
        {
            "numero_expediente": "2-10",
            "juzgado": "Primero Mercantil",
            "extracto_acuerdo": "Abre etapa de alegatos",
            "requiere_accion": True,
            "termino_fatal": True,
            "dias_termino": 2,
        },
        {
            "numero_expediente": "33",
            "juzgado": "Tercera Sala",
            "extracto_acuerdo": "Recibido escrito",
            "requiere_accion": False,
            "termino_fatal": False,
            "dias_termino": None,
        },
    ]
    resumen = generar_resumen_boletin(acuerdos)
    assert "2-10" in resumen
    assert "33" in resumen
    assert "2 acuerdo" in resumen.lower() or "2" in resumen


def test_generar_resumen_boletin_marca_fatal():
    acuerdos = [{
        "numero_expediente": "5-20",
        "juzgado": "Cuarto Familiar",
        "extracto_acuerdo": "Término para acreditar domicilio",
        "requiere_accion": True,
        "termino_fatal": True,
        "dias_termino": 3,
    }]
    resumen = generar_resumen_boletin(acuerdos)
    assert "FATAL" in resumen.upper() or "🚨" in resumen


def test_generar_resumen_incluye_requiere_accion():
    acuerdos = [{
        "numero_expediente": "2-10",
        "juzgado": "Primero Mercantil",
        "extracto_acuerdo": "Algo pasó",
        "requiere_accion": True,
        "termino_fatal": False,
        "dias_termino": None,
    }]
    resumen = generar_resumen_boletin(acuerdos)
    assert "acción" in resumen.lower() or "accion" in resumen.lower()

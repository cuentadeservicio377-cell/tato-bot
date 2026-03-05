"""Tests for legal-specific functions added to google_services.py"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import os

USER_ID = 12345
FAKE_SHEET_ID = "fake-sheet-id-123"
FAKE_MSG_ID = "msg-abc"
FAKE_ATTACH_ID = "attach-xyz"


@pytest.mark.asyncio
async def test_get_boletin_email_today_found():
    """Cuando hay email de Gaceta hoy, retorna el primer resultado."""
    from google_services import get_boletin_email_today

    with patch("google_services.get_valid_token", new_callable=AsyncMock, return_value="fake-token"), \
         patch.dict(os.environ, {"GACETA_EMAIL_SENDER": "gaceta@ejemplo.com"}):

        with patch("httpx.AsyncClient") as MockClient:
            # Mock search response
            mock_resp_search = MagicMock()
            mock_resp_search.raise_for_status = MagicMock()
            mock_resp_search.json = MagicMock(return_value={"messages": [{"id": FAKE_MSG_ID}]})

            # Mock message metadata response
            mock_resp_meta = MagicMock()
            mock_resp_meta.raise_for_status = MagicMock()
            mock_resp_meta.json = MagicMock(return_value={
                "id": FAKE_MSG_ID,
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Acuerdos del día"},
                        {"name": "From", "value": "gaceta@ejemplo.com"},
                    ],
                    "parts": [{"filename": "boletin.pdf", "mimeType": "application/pdf",
                               "body": {"attachmentId": FAKE_ATTACH_ID}}]
                }
            })

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_instance.get = AsyncMock(side_effect=[mock_resp_search, mock_resp_meta])
            MockClient.return_value = mock_client_instance

            result = await get_boletin_email_today(USER_ID)

    assert result is not None
    assert result["id"] == FAKE_MSG_ID
    assert result["attachment_id"] == FAKE_ATTACH_ID


@pytest.mark.asyncio
async def test_get_boletin_email_today_not_found():
    """Cuando no hay email de Gaceta hoy, retorna None."""
    from google_services import get_boletin_email_today

    with patch("google_services.get_valid_token", new_callable=AsyncMock, return_value="fake-token"), \
         patch.dict(os.environ, {"GACETA_EMAIL_SENDER": "gaceta@ejemplo.com"}):

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json = MagicMock(return_value={"messages": []})

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client_instance

            result = await get_boletin_email_today(USER_ID)

    assert result is None


@pytest.mark.asyncio
async def test_update_sheets_expediente_calls_put():
    """Verifica que update_sheets_expediente hace PUT a Sheets API."""
    from google_services import update_sheets_expediente

    expediente = {
        "numero": "2-10", "juzgado": "Primero Mercantil", "cliente": "Alvarez",
        "tipo": "mercantil", "etapa": "alegatos",
        "ultimo_acuerdo": "2026-03-05", "ultimo_acuerdo_texto": "Abre alegatos",
        "proximo_termino": "2026-03-07", "termino_fatal": True,
        "estado": "activo", "notas": "", "ultima_actualizacion": "2026-03-05",
        "sheets_row": 2
    }

    with patch("google_services.get_valid_token", new_callable=AsyncMock, return_value="fake-token"), \
         patch.dict(os.environ, {"SHEETS_EXPEDIENTES_ID": FAKE_SHEET_ID}):

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json = MagicMock(return_value={"updatedCells": 12})

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_instance.put = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client_instance

            await update_sheets_expediente(USER_ID, expediente)

            mock_client_instance.put.assert_called_once()
            call_url = mock_client_instance.put.call_args[0][0]
            assert FAKE_SHEET_ID in call_url
            assert "A2:L2" in call_url


@pytest.mark.asyncio
async def test_append_sheets_expediente_calls_post():
    """Verifica que append_sheets_expediente hace POST a Sheets API."""
    from google_services import append_sheets_expediente

    expediente = {
        "numero": "5-20", "juzgado": "Cuarto Familiar", "cliente": "Lopez",
        "tipo": "familiar", "etapa": "pruebas",
        "ultimo_acuerdo": "", "ultimo_acuerdo_texto": "",
        "proximo_termino": "", "termino_fatal": False,
        "estado": "activo", "notas": "", "ultima_actualizacion": "2026-03-05"
    }

    with patch("google_services.get_valid_token", new_callable=AsyncMock, return_value="fake-token"), \
         patch.dict(os.environ, {
             "SHEETS_EXPEDIENTES_ID": FAKE_SHEET_ID,
             "SHEETS_EXPEDIENTES_RANGE": "Expedientes!A:L"
         }):

        with patch("httpx.AsyncClient") as MockClient:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json = MagicMock(return_value={
                "updates": {"updatedRange": "Expedientes!A3:L3"}
            })

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_instance.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client_instance

            row_num = await append_sheets_expediente(USER_ID, expediente)

            mock_client_instance.post.assert_called_once()
            assert row_num == 3

from app.modules.integrations.bero_service import BeroIntegrationService
from app.modules.integrations.schemas import BeroConnectRequest


def test_bero_token_roundtrip():
    token = "bero_test_token_123"
    encrypted = BeroIntegrationService._encrypt_token(token)
    assert encrypted != token
    plain = BeroIntegrationService._decrypt_token(encrypted)
    assert plain == token


def test_connect_request_default_strategy():
    req = BeroConnectRequest(company_identifier="CMP-1", company_token="bero_x")
    assert req.resolution_strategy == "ASK"

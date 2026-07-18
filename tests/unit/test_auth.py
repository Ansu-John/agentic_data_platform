import pytest
import jwt
import time
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from src.api.utils.auth import CognitoJWTValidator

@pytest.fixture
def mock_validator():
    validator = CognitoJWTValidator()
    validator.user_pool_id = "us-east-1_mockPool123"
    validator.client_id = "mockClient456"
    validator.issuer = f"https://cognito-idp.us-east-1.amazonaws.com/{validator.user_pool_id}"
    return validator

@patch("src.api.utils.auth.jwt.decode")
@patch("src.api.utils.auth.jwt.get_unverified_header")
@patch.object(CognitoJWTValidator, '_get_jwks')
def test_validate_token_success(mock_get_jwks, mock_unverified, mock_decode, mock_validator):
    mock_unverified.return_value = {"kid": "mock_key_id"}
    mock_get_jwks.return_value = {
        "keys": [{"kid": "mock_key_id", "kty": "RSA", "n": "dummy_n", "e": "AQAB"}]
    }
    
    # Set the success return value BEFORE calling the validator
    mock_decode.return_value = {
        "sub": "user-uuid-1234",
        "token_use": "access",
        "exp": time.time() + 3600
    }
    mock_decode.side_effect = None # Clear any previous side effects
    
    claims = mock_validator.validate_token("mock_encoded_jwt_string")
    assert claims["sub"] == "user-uuid-1234"

@patch("src.api.utils.auth.jwt.decode")
@patch("src.api.utils.auth.jwt.get_unverified_header")
@patch.object(CognitoJWTValidator, '_get_jwks')
def test_validate_token_expired(mock_get_jwks, mock_unverified, mock_decode, mock_validator):
    mock_unverified.return_value = {"kid": "mock_key_id"}
    
    # Add the required RSA keys so from_jwk doesn't fail
    mock_get_jwks.return_value = {
        "keys": [{"kid": "mock_key_id", "kty": "RSA", "n": "dummy_n", "e": "AQAB"}]
    }
    
    mock_decode.side_effect = jwt.ExpiredSignatureError("Signature expired")
    
    with pytest.raises(HTTPException) as exc:
        mock_validator.validate_token("expired_jwt_string")
        
    assert exc.value.status_code == 401
    assert "lifetime expired" in exc.value.detail
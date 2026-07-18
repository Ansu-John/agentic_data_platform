
import os
import time
from typing import Any, cast

import jwt
import requests
import structlog
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

logger = structlog.get_logger()
security = HTTPBearer()

class CognitoJWTValidator:
    """
    Thread-safe validator that fetches, caches, and verifies AWS Cognito
    JSON Web Tokens (JWT) using asymmetric RS256 cryptographic keys.
    """
    def __init__(self) -> None:
        self.region: str = os.getenv("AWS_REGION", "us-east-1")
        self.user_pool_id: str = os.getenv("COGNITO_USER_POOL_ID", "")
        self.client_id: str = os.getenv("COGNITO_APP_CLIENT_ID", "")

        if not self.user_pool_id:
            logger.warning("cognito_user_pool_id_missing",
                           msg="Authentication is unconfigured or operating in local bypass mode.")

        self.issuer: str = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
        self.jwks_url: str = f"{self.issuer}/.well-known/jwks.json"
        self._jwks: dict[str, Any] | None = None
        self._last_jwks_fetch: float = 0.0
        self.jwks_ttl: int = 86400  # Cache keys for 24 hours

    def _get_jwks(self) -> dict[str, Any]:
        """Fetches and caches the public JSON Web Key Set from Cognito."""
        current_time = time.time()
        if not self._jwks or (current_time - self._last_jwks_fetch > self.jwks_ttl):
            try:
                logger.info("fetching_cognito_jwks", url=self.jwks_url)
                response = requests.get(self.jwks_url, timeout=5)
                response.raise_for_status()
                self._jwks = response.json()
                self._last_jwks_fetch = current_time
            except Exception as e:
                logger.error("jwks_fetch_failed", error=str(e))
                if self._jwks:
                    return self._jwks  # Fallback to stale cache if network is down
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication subsystem unavailable."
                ) from e
        return self._jwks

    def validate_token(self, token: str) -> dict[str, Any]:
        """Decodes, verifies the RSA signature, and validates standard JWT claims."""
        if not self.user_pool_id:
            # Bypass configuration for localized integration testing stages only
            return {"sub": "local-dev-bypass", "username": "developer", "custom:role": "Admin"}

        try:
            # Unverified decode to extract the Key ID ('kid') from the header
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            jwks = self._get_jwks()
            public_key = None

            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    # Cast the returned key to RSAPublicKey to satisfy mypy
                    raw_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    public_key = cast(RSAPublicKey, raw_key)
                    break

            if not public_key:
                logger.error("jwk_key_not_found", kid=kid)
                raise InvalidTokenError("Invalid token signature identity identifier.")

            # Validate signature and claims strictly
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={"require": ["exp", "iss", "sub", "token_use"]}
            )

            # Enforce access or id token validation guardrails
            if claims.get("token_use") not in ["access", "id"]:
                raise InvalidTokenError("Invalid token use scope property context.")

            return claims

        except ExpiredSignatureError as e:
            logger.warning("token_expired_exception", error=str(e))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token signature lifetime expired.") from e
        except InvalidTokenError as e:
            logger.error("token_invalid_exception", error=str(e))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token signature payload parameters.") from e

# Instantiate Singleton Pattern Validator
token_validator = CognitoJWTValidator()

def get_current_user(credentials: HTTPAuthorizationCredentials =
                     Depends(security)) -> dict[str, Any]:
    """FastAPI Dependency injected into protected execution route endpoints."""
    return token_validator.validate_token(credentials.credentials)

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    api_key_header_val: str = Security(api_key_header),
    bearer_auth: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> str:
    """
    Validates service-to-service authentication using X-API-Key header or Bearer token.
    """
    token = None
    if api_key_header_val:
        token = api_key_header_val
    elif bearer_auth and bearer_auth.credentials:
        token = bearer_auth.credentials

    if not token or token != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

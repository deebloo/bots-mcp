import os
from typing import Any
from fastapi import Request

BOTS_MCP_OAUTH_ISSUER = os.getenv("BOTS_MCP_OAUTH_ISSUER", "").rstrip("/")
BOTS_MCP_OAUTH_AUTHORIZATION_ENDPOINT = os.getenv("BOTS_MCP_OAUTH_AUTHORIZATION_ENDPOINT", "").rstrip("/")
BOTS_MCP_OAUTH_TOKEN_ENDPOINT = os.getenv("BOTS_MCP_OAUTH_TOKEN_ENDPOINT", "").rstrip("/")
BOTS_MCP_OAUTH_SCOPES_SUPPORTED = [
    scope.strip()
    for scope in os.getenv("BOTS_MCP_OAUTH_SCOPES_SUPPORTED", "mcp:tools:call").split(",")
    if scope.strip()
]

def _public_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def build_oauth_metadata(request: Request) -> dict[str, Any]:
    base_url = _public_base_url(request)

    metadata: dict[str, Any] = {
        "issuer": BOTS_MCP_OAUTH_ISSUER or base_url,
        "authorization_endpoint": BOTS_MCP_OAUTH_AUTHORIZATION_ENDPOINT or f"{base_url}/oauth/authorize",
        "token_endpoint": BOTS_MCP_OAUTH_TOKEN_ENDPOINT or f"{base_url}/oauth/token",
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "response_types_supported": ["code"],
        "scopes_supported": BOTS_MCP_OAUTH_SCOPES_SUPPORTED,
        "code_challenge_methods_supported": ["S256"],
    }

    return metadata

"""
BOTS MCP Server

Exposes the BOTS translate-api as MCP tools.

Configuration (environment variables):
    BOTS_API_URL - Base URL of the translate-api (default: http://localhost:8080)
    BOTS_MCP_OAUTH_ISSUER - Issuer URL returned by OAuth discovery metadata.
    BOTS_MCP_OAUTH_AUTHORIZATION_ENDPOINT - Authorization endpoint returned by OAuth discovery metadata.
    BOTS_MCP_OAUTH_TOKEN_ENDPOINT - Token endpoint returned by OAuth discovery metadata.
    BOTS_MCP_OAUTH_REGISTRATION_ENDPOINT - Optional client registration endpoint returned by OAuth discovery metadata.
    BOTS_MCP_OAUTH_SCOPES_SUPPORTED - Comma-separated scopes returned by OAuth discovery metadata.
    BOTS_MCP_SERVER_HOST - Interface address for the HTTP/SSE server (default: 127.0.0.1).
    BOTS_MCP_SERVER_PORT - Port for the HTTP/SSE server (default: 8000).
"""

import os
import sys
from pathlib import Path
from typing import Any, Literal, cast

import httpx
from fastmcp import FastMCP
from fastapi import FastAPI, Request
from fastmcp.server.dependencies import CurrentHeaders
from fastmcp.exceptions import AuthorizationError

app = FastAPI()
mcp = FastMCP.from_fastapi(app)

BOTS_API_URL = os.getenv("BOTS_API_URL", "http://localhost:8080").rstrip("/")
BOTS_MCP_OAUTH_ISSUER = os.getenv("BOTS_MCP_OAUTH_ISSUER", "").rstrip("/")
BOTS_MCP_OAUTH_AUTHORIZATION_ENDPOINT = os.getenv("BOTS_MCP_OAUTH_AUTHORIZATION_ENDPOINT", "").rstrip("/")
BOTS_MCP_OAUTH_TOKEN_ENDPOINT = os.getenv("BOTS_MCP_OAUTH_TOKEN_ENDPOINT", "").rstrip("/")
BOTS_MCP_OAUTH_REGISTRATION_ENDPOINT = os.getenv("BOTS_MCP_OAUTH_REGISTRATION_ENDPOINT", "").rstrip("/")
BOTS_MCP_OAUTH_SCOPES_SUPPORTED = [
    scope.strip()
    for scope in os.getenv("BOTS_MCP_OAUTH_SCOPES_SUPPORTED", "mcp:tools:call").split(",")
    if scope.strip()
]


def _public_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _oauth_metadata(request: Request) -> dict[str, Any]:
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

    if BOTS_MCP_OAUTH_REGISTRATION_ENDPOINT:
        metadata["registration_endpoint"] = BOTS_MCP_OAUTH_REGISTRATION_ENDPOINT

    return metadata


@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata(request: Request) -> dict[str, Any]:
    return _oauth_metadata(request)


@app.get("/.well-known/openid-configuration")
async def openid_configuration_metadata(request: Request) -> dict[str, Any]:
    return _oauth_metadata(request)

def _require_bearer_token(headers: dict[str, str] | None) -> str:
    if not headers:
        raise AuthorizationError("401 Unauthorized: missing or invalid Authorization header")

    authorization = headers.get("authorization") or headers.get("Authorization")

    if not authorization:
        raise AuthorizationError("401 Unauthorized: missing or invalid Authorization header")

    scheme, _, token = authorization.partition(" ")
    
    if scheme.lower() != "bearer" or not token:
        raise AuthorizationError("401 Unauthorized: missing or invalid Authorization header")

    return token.strip()

def _headers(access_token: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {}

    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
        
    return headers


def _client(access_token: str | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BOTS_API_URL, headers=_headers(access_token), timeout=120)


def _normalize_lang_code(lang_code: str) -> str:
    normalized = lang_code.strip().lower()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError(
            f"Invalid language code '{lang_code}'. Expected a 2-letter ISO code like 'en' or 'fr'."
        )
    return normalized

@mcp.tool
async def list_translations(
    current_headers: dict[str, str] = CurrentHeaders(),
) -> list[dict[str, Any]]:
    """Return the full translation history for the configured user.
    
    Args:
        current_headers: Current HTTP request headers.
    """

    resolved_access_token = _require_bearer_token(current_headers)

    async with _client(resolved_access_token) as client:
        r = await client.get("/api/v1/translations")
        r.raise_for_status()
        return r.json()


@mcp.tool
async def get_translation(
    id: str,
    current_headers: dict[str, str] = CurrentHeaders(),
) -> dict[str, Any]:
    """Get a single translation by its UUID.

    Args:
        id: Translation UUID.
        current_headers: Current HTTP request headers.
    """
    resolved_access_token = _require_bearer_token(current_headers)

    async with _client(resolved_access_token) as client:
        r = await client.get(f"/api/v1/translations/{id}")
        r.raise_for_status()
        return r.json()


@mcp.tool
async def create_text_translation(
    source_lang: str,
    target_lang: str,
    source_content: str,
    current_headers: dict[str, str] = CurrentHeaders(),
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new text translation.

    Args:
        source_lang: 2-letter source language code, e.g. "en".
        target_lang: 2-letter target language code, e.g. "fr".
        source_content: The plain text to translate.
        current_headers: Current HTTP request headers.
        labels: Optional list of label IDs to attach to this translation.
    """
    source_lang = _normalize_lang_code(source_lang)
    target_lang = _normalize_lang_code(target_lang)

    data: list[tuple[str, str]] = [
        ("translationType", "text"),
        ("sourceLang", source_lang),
        ("targetLang", target_lang),
        ("sourceContent", source_content),
    ]
    for label in labels or []:
        data.append(("labels", label))

    resolved_access_token = _require_bearer_token(current_headers)

    async with _client(resolved_access_token) as client:
        r = await client.post("/api/v1/translations", data=cast(Any, data))
        r.raise_for_status()
        return r.json()


@mcp.tool
async def create_file_translation(
    source_lang: str,
    target_lang: str,
    file_path: str,
    current_headers: dict[str, str] = CurrentHeaders(),
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new file translation by uploading a local file.

    Args:
        source_lang: 2-letter source language code, e.g. "en".
        target_lang: 2-letter target language code, e.g. "fr".
        file_path: Absolute or relative path to the file to translate (docx, pdf, image, etc.).
        current_headers: Current HTTP request headers.
        labels: Optional list of label IDs to attach to this translation.
    """
    source_lang = _normalize_lang_code(source_lang)
    target_lang = _normalize_lang_code(target_lang)

    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    data: list[tuple[str, str]] = [
        ("translationType", "file"),
        ("sourceLang", source_lang),
        ("targetLang", target_lang),
    ]
    for label in labels or []:
        data.append(("labels", label))

    resolved_access_token = _require_bearer_token(current_headers)

    with path.open("rb") as fh:
        async with _client(resolved_access_token) as client:
            r = await client.post(
                "/api/v1/translations",
                data=cast(Any, data),
                files={"sourceFile": (path.name, fh)},
            )
            r.raise_for_status()
            return r.json()

@mcp.tool
async def download_translation_file(
    id: str,
    file_type: Literal["source", "target"],
    save_to: str,
    current_headers: dict[str, str] = CurrentHeaders(),
) -> str:
    """Download a translation's source or target file and save it locally.

    Args:
        id: Translation UUID.
        file_type: Whether to download the "source" or "target" file.
        save_to: Local path where the downloaded file should be saved.
        current_headers: Current HTTP request headers.
    """
    save_path = Path(save_to).expanduser().resolve()
    save_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_access_token = _require_bearer_token(current_headers)

    async with _client(resolved_access_token) as client:
        r = await client.get(f"/api/v1/translations/{id}/files/{file_type}")
        r.raise_for_status()
        save_path.write_bytes(r.content)

    return f"File saved to {save_path}"

@mcp.tool
async def health_check(
    current_headers: dict[str, str] = CurrentHeaders(),
) -> dict[str, Any]:
    """Check whether the BOTS API is reachable and healthy.
    
    Args:
        current_headers: Current HTTP request headers.
    """
    resolved_access_token = _require_bearer_token(current_headers)

    async with _client(resolved_access_token) as client:
        r = await client.get("/health")
        r.raise_for_status()
        return r.json()


def main():
    """Entry point for the bots-mcp command."""
    port = int(os.getenv("BOTS_MCP_SERVER_PORT", "8000"))
    host = os.getenv("BOTS_MCP_SERVER_HOST", "127.0.0.1")
    
    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        # Support stdio transport if explicitly requested
        mcp.run()
    else:
        # Run as HTTP server (SSE transport)
        mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    main()

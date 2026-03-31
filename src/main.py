"""
BOTS MCP Server

Exposes the BOTS translate-api as MCP tools.

Configuration (environment variables):
    BOTS_API_URL - Base URL of the translate-api (default: http://localhost:9000)
    BOTS_MCP_OAUTH_ISSUER - Issuer URL returned by OAuth discovery metadata.
    BOTS_MCP_OAUTH_AUTHORIZATION_ENDPOINT - Authorization endpoint returned by OAuth discovery metadata.
    BOTS_MCP_OAUTH_TOKEN_ENDPOINT - Token endpoint returned by OAuth discovery metadata.
    BOTS_MCP_OAUTH_SCOPES_SUPPORTED - Comma-separated scopes returned by OAuth discovery metadata.
"""

import os
from typing import Any

import httpx
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from oauth import build_oauth_metadata

mcp = FastMCP("BOTS API")
MOCK_USER_HEADER = "BOTS-USER-ID"
MOCK_USER_ID = "test-user-12345"

BOTS_API_URL = os.getenv("BOTS_API_URL", "http://localhost:9001").rstrip("/")


def _resolve_user_id(headers: dict[str, str] | None) -> str:
    _ = headers
    return MOCK_USER_ID


def _headers(user_id: str) -> dict[str, str]:
    return {MOCK_USER_HEADER: user_id}


def _client(user_id: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BOTS_API_URL, headers=_headers(user_id), timeout=120)


def _normalize_lang_code(lang_code: str) -> str:
    normalized = lang_code.strip().lower()

    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError(
            f"Invalid language code '{lang_code}'. Expected a 2-letter ISO code like 'en' or 'fr'."
        )

    return normalized


@mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
async def oauth_authorization_server_metadata(request: Request) -> Response:
    return JSONResponse(build_oauth_metadata(request))


@mcp.custom_route("/.well-known/openid-configuration", methods=["GET"])
async def openid_configuration_metadata(request: Request) -> Response:
    return JSONResponse(build_oauth_metadata(request))


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    return JSONResponse({"status": "ok"})


@mcp.tool
async def list_translations() -> list[dict[str, Any]]:
    """Return the full translation history for the configured user."""
    resolved_user_id = _resolve_user_id(None)

    async with _client(resolved_user_id) as client:
        r = await client.get("/api/v1/translations")
        r.raise_for_status()
        return r.json()


@mcp.tool
async def get_translation(id: str) -> dict[str, Any]:
    """Get a single translation by its UUID.

    Args:
        id: Translation UUID.
    """
    resolved_user_id = _resolve_user_id(None)

    async with _client(resolved_user_id) as client:
        r = await client.get(f"/api/v1/translations/{id}")
        r.raise_for_status()
        return r.json()


@mcp.tool
async def create_text_translation(
    source_lang: str,
    target_lang: str,
    source_content: str,
) -> dict[str, Any]:
    """Create a new text translation.

    Args:
        source_lang: 2-letter source language code, e.g. "en".
        target_lang: 2-letter target language code, e.g. "fr".
        source_content: The plain text to translate.
    """
    source_lang = _normalize_lang_code(source_lang)
    target_lang = _normalize_lang_code(target_lang)

    data = {
        "translationType": "text",
        "sourceLang": source_lang,
        "targetLang": target_lang,
        "sourceContent": source_content,
    }
    resolved_user_id = _resolve_user_id(None)

    async with _client(resolved_user_id) as client:
        r = await client.post("/api/v1/translations", data=data)
        
        if r.is_error:
            raise RuntimeError(f"Translation request failed ({r.status_code}): {r.text}")
        
        return r.json()

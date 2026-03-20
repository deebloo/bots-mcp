"""
BOTS MCP Server

Exposes the BOTS translate-api as MCP tools.

Configuration (environment variables):
  BOTS_API_URL   - Base URL of the translate-api (default: http://localhost:8080)
  BOTS_USER_ID   - Value sent in the BOTS-USER-ID header for auth (required)
"""

import os
from pathlib import Path
from typing import Any, Literal, cast

import httpx
from fastmcp import FastMCP

mcp = FastMCP("BOTS API")

BOTS_API_URL = os.getenv("BOTS_API_URL", "http://localhost:8080").rstrip("/")
BOTS_USER_ID = os.getenv("BOTS_USER_ID", "")


def _headers() -> dict[str, str]:
    return {"BOTS-USER-ID": BOTS_USER_ID}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=BOTS_API_URL, headers=_headers(), timeout=120)


def _normalize_lang_code(lang_code: str) -> str:
    normalized = lang_code.strip().lower()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError(
            f"Invalid language code '{lang_code}'. Expected a 2-letter ISO code like 'en' or 'fr'."
        )
    return normalized

@mcp.tool
async def list_translations() -> list[dict[str, Any]]:
    """Return the full translation history for the configured user."""
    
    async with _client() as client:
        r = await client.get("/api/v1/translations")
        r.raise_for_status()
        return r.json()


@mcp.tool
async def get_translation(id: str) -> dict[str, Any]:
    """Get a single translation by its UUID.

    Args:
        id: Translation UUID.
    """
    async with _client() as client:
        r = await client.get(f"/api/v1/translations/{id}")
        r.raise_for_status()
        return r.json()


@mcp.tool
async def create_text_translation(
    source_lang: str,
    target_lang: str,
    source_content: str,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new text translation.

    Args:
        source_lang: 2-letter source language code, e.g. "en".
        target_lang: 2-letter target language code, e.g. "fr".
        source_content: The plain text to translate.
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

    async with _client() as client:
        r = await client.post("/api/v1/translations", data=cast(Any, data))
        r.raise_for_status()
        return r.json()


@mcp.tool
async def create_file_translation(
    source_lang: str,
    target_lang: str,
    file_path: str,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new file translation by uploading a local file.

    Args:
        source_lang: 2-letter source language code, e.g. "en".
        target_lang: 2-letter target language code, e.g. "fr".
        file_path: Absolute or relative path to the file to translate (docx, pdf, image, etc.).
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

    with path.open("rb") as fh:
        async with _client() as client:
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
) -> str:
    """Download a translation's source or target file and save it locally.

    Args:
        id: Translation UUID.
        file_type: Whether to download the "source" or "target" file.
        save_to: Local path where the downloaded file should be saved.
    """
    save_path = Path(save_to).expanduser().resolve()
    save_path.parent.mkdir(parents=True, exist_ok=True)

    async with _client() as client:
        r = await client.get(f"/api/v1/translations/{id}/files/{file_type}")
        r.raise_for_status()
        save_path.write_bytes(r.content)

    return f"File saved to {save_path}"

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@mcp.tool
async def health_check() -> dict[str, Any]:
    """Check whether the BOTS API is reachable and healthy."""
    async with _client() as client:
        r = await client.get("/health")
        r.raise_for_status()
        return r.json()


if __name__ == "__main__":
    mcp.run()

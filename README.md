# BOTS MCP

MCP server that exposes BOTS translate-api operations as tools.

## Configuration

- `BOTS_API_URL`: Base URL of the translate-api. Defaults to `http://localhost:8080`.
- `MCP_OAUTH_ISSUER`: Public issuer URL returned by the discovery metadata.
- `MCP_OAUTH_AUTHORIZATION_ENDPOINT`: Public OAuth authorize URL.
- `MCP_OAUTH_TOKEN_ENDPOINT`: Public OAuth token URL.
- `MCP_OAUTH_REGISTRATION_ENDPOINT`: Optional dynamic client registration URL.
- `MCP_OAUTH_SCOPES_SUPPORTED`: Comma-separated scopes list returned by the discovery metadata.

## Run

1. Set `BOTS_USER_ID` (required) and optionally `BOTS_API_URL`.
2. Start locally:

```bash
uv sync
uv run python src/main.py
```

## OAuth Discovery

The server exposes OAuth discovery metadata at:

- `/.well-known/oauth-authorization-server`
- `/.well-known/openid-configuration`

If you do not set any `MCP_OAUTH_*` variables, the metadata derives the public base URL from the incoming request and advertises:

- `authorization_endpoint`: `/oauth/authorize`
- `token_endpoint`: `/oauth/token`
- `grant_types_supported`: `authorization_code`, `refresh_token`
- `response_types_supported`: `code`
- `code_challenge_methods_supported`: `S256`

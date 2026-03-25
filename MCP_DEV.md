# MCP Server Developer Guide: LibreChat Integration & OAuth Validation

This guide provides the technical details necessary for an MCP (Model Context Protocol) server developer to integrate with LibreChat, specifically focusing on how LibreChat handles authentication and how your server should validate incoming requests.

## 1. Request Identification & Headers

LibreChat communicates with MCP servers using **JSON-RPC 2.0**. The method of authentication depends on the transport type configured.

### HTTP/SSE Transport (Remote)
This is the standard for remote MCP servers. LibreChat injects the OAuth token directly into the request headers.
- **Header:** `Authorization`
- **Format:** `Bearer <ACCESS_TOKEN>`
- **Content-Type:** `application/json`

### stdio Transport (Local)
For servers running as a local process, tokens are passed via environment variables.
- **Variable Name:** Defined in `librechat.yaml` (e.g., `MY_SERVER_TOKEN`).
- **Value:** The raw access token string.

---

## 2. OAuth Discovery & Metadata

LibreChat uses auto-discovery to find your OAuth endpoints. Your server should host metadata at one of these standard locations:
1. `GET /.well-known/oauth-authorization-server`
2. `GET /.well-known/openid-configuration`

### Required Metadata Fields
Your JSON response should include:
- `issuer`: Your server's unique identifier.
- `authorization_endpoint`: URL for user login/consent.
- `token_endpoint`: URL for exchanging authorization codes for tokens.
- `registration_endpoint` (Optional): Required if you support **Dynamic Client Registration**.
- `grant_types_supported`: Should include `authorization_code` and `refresh_token`.
- `response_types_supported`: Should include `code`.

---

## 3. The Authentication Lifecycle

1. **Connection Attempt:** LibreChat hits your endpoint (e.g., `/sse`).
2. **Challenge:** Your server **MUST** return a `401 Unauthorized` status if a valid token is missing.
3. **Discovery:** LibreChat fetches your metadata from the `.well-known` paths.
4. **User Auth:** LibreChat redirects the user to your `authorization_endpoint`.
5. **Callback:** Your server redirects back to LibreChat:
   `https://<LIBRECHAT_DOMAIN>/api/mcp/{serverName}/oauth/callback?code=...&state=...`
6. **Exchange:** LibreChat calls your `token_endpoint` (server-to-server) to retrieve the `access_token` and `refresh_token`.
7. **Retry:** LibreChat retries the original request with the new `Bearer` token.

---

## 4. Request Validation Logic

As a developer, your server should perform these validations for every incoming request:

### A. Token Presence
Verify the `Authorization` header exists and follows the `Bearer <token>` format.

### B. JWT Validation (if applicable)
If your tokens are JWTs:
- **Signature:** Validate against your public JWKS.
- **Expiration (`exp`):** Reject tokens if the current time > `exp`.
- **Issuer (`iss`):** Confirm it matches your expected issuer.
- **Audience (`aud`):** Confirm it matches your MCP server's identifier.

### C. Scope Verification
Verify that the token includes the necessary scopes (e.g., `mcp:tools:call`) required for the specific JSON-RPC method being invoked.

### D. PKCE Support
LibreChat uses **PKCE (Proof Key for Code Exchange)** by default. Your authorization server should validate the `code_challenge` during the auth request and the `code_verifier` during the token exchange.

---

## 5. HTTP Response Codes & Actions

| Status Code | Meaning | LibreChat Behavior |
| :--- | :--- | :--- |
| **200 OK** | Success | Processes the JSON-RPC response. |
| **401 Unauthorized** | Invalid/Missing Token | Triggers OAuth flow or attempts Token Refresh. |
| **403 Forbidden** | Insufficient Scopes | Returns an error to the user. |
| **429 Too Many Requests** | Rate Limited | Temporarily halts reconnection attempts. |

---

## 6. Developer Testing Tip

To verify that LibreChat is sending the token correctly, you can use a simple middleware to log the headers:

```javascript
// Example Express.js Middleware for debugging
app.use((req, res, next) => {
  const authHeader = req.headers['authorization'];
  if (authHeader) {
    console.log(`[MCP Debug] Received Token: ${authHeader}`);
  } else {
    console.warn('[MCP Debug] No Authorization header found');
  }
  next();
});
```

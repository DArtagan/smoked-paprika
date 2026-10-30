# google-auth: OAuth through Google, for one person

## Opening prompt

> Put the MCP server on HTTP behind Google sign-in and an email allowlist. Read
> `todos/google-auth.md` and the design's *Authentication* section.

## Decision

Will, 2026-10-29: "Let's delegate it to Google for now. I'll implement my own
self-hosted oauth provider in the future." So Google is the provider now, and
nothing should make the later swap harder than changing configuration.

## What is known (read 2026-10-29)

- **Claude's client** ([Claude docs](https://claude.com/docs/connectors/building/authentication)):
  - It registers through DCR, or through a CIMD when the authorization server
    advertises `client_id_metadata_document_supported` and the `none` token
    auth method.
  - A 401 is required to start sign-in.
  - It uses only the first entry of `authorization_servers`.
  - Discovery, registration and token endpoints have 10 seconds to answer;
    refresh has 30.
  - The claude.ai callback is `https://claude.ai/api/mcp/auth_callback`. Claude
    Code uses a loopback redirect and its own CIMD.
- **Claude's network**
  ([help centre](https://support.claude.com/en/articles/11175166)): it connects
  from Anthropic's cloud for every client, mobile included. The server must be
  publicly reachable.
- **FastMCP's `GoogleProvider`** ([docs](https://gofastmcp.com/integrations/google),
  [OAuth proxy](https://gofastmcp.com/servers/auth/oauth-proxy)):
  - It is an OAuth proxy that presents DCR to Claude and holds one Google
    client. The Google client's redirect URI is the server's `/auth/callback`
    over HTTPS.
  - `allowed_client_redirect_uris` can restrict which client callbacks the
    proxy accepts.
  - The consent page is on by default (`require_authorization_consent=True`)
    and defends against confused-deputy attacks. Keep it.
  - Client storage defaults to an encrypted disk store, keyed from the Google
    client secret unless a `jwt_signing_key` is given. Give one, so rotating the
    Google secret does not drop registrations.
  - `fastmcp_access_token_expiry_seconds` decouples Claude's token lifetime from
    Google's short-lived one.
- **Authorization** ([FastMCP](https://gofastmcp.com/servers/authorization)):
  any Google account can complete sign-in. `AuthMiddleware` with a check on the
  token's claims applies server-wide. Check that `email` and `email_verified`
  are present in `GoogleProvider`'s claims before relying on them. The docs'
  example reads `email` but does not show `email_verified`.

## Open questions

- Whether a non-allowlisted account can be refused at the end of sign-in rather
  than only on each request. Refusing earlier is better, and the per-request
  check stays either way.
- Google's consent screen in "Testing" publishing status limits sign-in to
  listed test users, a second fence at no cost. Google has documented that
  refresh tokens issued in Testing expire after 7 days for external apps,
  which would force a weekly reconnect. Verify the current behaviour before
  choosing between Testing and In production.

## Scope

HTTP transport with `GoogleProvider`, the allowlist middleware, the proxy's
signing key and storage under `/data`, configuration from the environment, and
the redirect-URI allowlist for claude.ai and Claude Code.

## Done when

- Claude Code connects over HTTP to a locally run server, by sign-in, and the
  tools work.
- A second Google account completes sign-in and is refused, both at the tool
  call and wherever the open question above lands.
- A restart of the server does not make Claude Code sign in again.
- Requests with no token, an expired token and a token from another FastMCP
  server are each refused, by test.

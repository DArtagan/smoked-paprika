# smoked-paprika — design spec

> A self-hostable service that lets you add recipes to **Paprika** from anywhere
> — hand-typed markdown/YAML, a web form, a REST API, or an AI assistant — by
> wrapping Paprika's (unofficial, reverse-engineered) cloud-sync API behind one
> clean backend. Built to be deployed independently and used by others, not tied
> to any one machine's config.

This is the design spec for **smoked-paprika**. It captures the problem, the API
reality, the architecture, and a build roadmap. Deployment is generic
(container-first), not NixOS-specific. The product-level overview lives in the
repo [`README.md`](../README.md).

---

## 1. Context & motivation

Paprika is an excellent cross-platform recipe manager, but it has **no Linux
desktop app and no official API**. Entering recipes received as plain text from
friends (or as photos) is tedious on a phone. smoked-paprika gives you flexible,
scriptable entry paths from a computer or any browser, and a clean internal API
others can build on.

Goal: paste/type/scan a recipe anywhere → it lands in your Paprika account and
syncs to your phone.

## 2. The Paprika API reality (what we wrap)

Paprika's cloud-sync API is undocumented but has been legally reverse-engineered
(see references). smoked-paprika depends on these facts:

- **Base:** `https://www.paprikaapp.com/api/v1/sync/...`
- **Auth:** HTTP Basic with the account's **cloud-sync** email/password. This is
  the durable path. The newer JWT/token-login endpoint added device-auth checks
  and is more prone to rate-limiting/IP bans — **do not rely on it**.
- **Read:** `GET /sync/recipes/` → list of `{uid, hash}`;
  `GET /sync/recipe/{uid}/` → full recipe.
- **Write:** `POST /sync/recipe/{uid}/` where the body is `multipart/form-data`
  with a `data` field holding **gzip-compressed JSON**. Every field must be
  present (even if empty). `hash` = sha256 of the JSON with the `hash` field
  removed and keys sorted. Photos upload as a separate binary field.
- **Constraints:** no CORS headers (a browser cannot call Paprika directly — a
  server-side backend is mandatory); bulk/rapid calls risk IP bans.

**Observed (M0, 2026-06-15):** the `paprika-3-mcp` reference server authenticates
via the token endpoint `POST /api/v1/account/login` (returns a Bearer token) and
worked without incident in one-off testing — but smoked-paprika's own client will
still prefer **HTTP Basic on the sync endpoints** as the durable, ban-resistant
path. Reading paprika-3-mcp's client also corroborated the write format: gzip JSON,
`hash` = sha256 of the JSON with the `hash` field removed and keys sorted, sent as
the multipart `data` field.

These quirks (gzip + multipart + hash; no CORS) are exactly why a backend wrapper
is worthwhile and why we reuse an existing client rather than hand-roll HTTP.

## 3. Recommended foundation

Build on **`paprika-recipes`** (coddingtonbear, PyPI) as the Paprika client
library — it already implements the gzip/hash/multipart write logic and a Recipe
model, so smoked-paprika focuses on the front-ends, not protocol plumbing.

**Note:** upstream `paprika-recipes` may lag current Python and API changes. A
maintained fork — [`tieguy/paprika-recipes`](https://github.com/tieguy/paprika-recipes)
(Python 3.11+, current Paprika API, built-in ~2s rate limiting) — is likely the
better dependency for smoked-paprika, especially given our Python 3.13 environment.
This feeds the vendor-vs-depend decision in §11.

Implies a **Python** stack: **FastAPI** for HTTP/web, **FastMCP** for the MCP
endpoint. (If a non-Python stack is later preferred, the reverse-engineered spec
in the references is enough to reimplement the client — but Python + reusing the
library is the fastest credible path.)

Off-the-shelf alternatives evaluated and why they're not the core:
- `paprika-3-mcp` (Go) — solid drop-in MCP server (create/update only). Good for
  quick validation or as a packaged option, but doesn't give us a web UI or REST
  API, so it's not the foundation. (Used to validate M0 — see §8.)
- `paprika-rs` (Rust) — read-only / experimental; not for writing.

## 4. Architecture — one hub, many front-ends

```
                ┌─────────────────────────────────────────┐
   markdown/YAML │                                          │
   CLI / curl ──▶│  REST API        ┐                       │
                 │                   │                      │
   browser ─────▶│  Web UI (form +   ├─▶ Recipe service ───▶│──▶ Paprika cloud API
   (LAN/tailnet) │  paste textarea)  │   (normalise +        │    (v1, HTTP Basic)
                 │                   │    paprika-recipes     │
   AI assistant ▶│  MCP endpoint    ┘    client + hashing)    │
   (Claude etc.) │                                          │
                 └─────────────────────────────────────────┘
```

**Core service layer** (the only thing that talks to Paprika):
- Holds credentials (one place).
- Normalises an incoming recipe (from JSON / markdown / YAML / parsed text) into
  the Paprika Recipe model.
- Computes hash, gzips, multipart-POSTs; handles photo upload.
- Serializes writes and backs off to respect rate limits.

**Front-ends (all thin callers of the core):**
1. **REST API** — `POST /recipes` accepts structured JSON *or* a markdown/YAML
   body; `GET /recipes`, `GET /recipes/{uid}`. This is the programmatic ingress
   for CLI wrappers, scripts, and "drop a markdown file" flows.
2. **Web UI** — minimal "Add Recipe" page: structured fields + a big
   paste/markdown textarea. Usable from any browser including the phone. (Server
   renders/handles submission; no direct browser→Paprika calls, per the CORS
   constraint.)
3. **MCP endpoint** — expose `create_recipe` / `update_recipe` / `search` as MCP
   tools (FastMCP, HTTP/streamable transport) so AI assistants like Claude can
   create recipes by natural language and image parsing. Optionally also ship a
   stdio mode for local desktop clients.

**Recipe input formats to support:**
- Structured JSON (canonical).
- Front-matter YAML (matches `paprika-recipes`' existing YAML shape — reuse it).
- Loose markdown (title + ingredients list + directions) with a forgiving parser.

**Image / freeform parsing:** out of the core's scope to keep it deterministic —
parsing is the AI layer's job. The MCP front-end lets an assistant turn a photo
or messy text into structured fields, then call `create_recipe`. Document a
recommended prompt/schema so any model (Claude API, or a local vision model)
can produce hub-compatible JSON.

## 5. Suggested repo layout

```
smoked-paprika/
├── README.md                  # product overview, quickstart, screenshots
├── docs/
│   ├── SPEC.md                # this document
│   └── paprika-api.md         # distilled API notes + references
├── pyproject.toml             # FastAPI, fastmcp, paprika-recipes, etc.
├── smoked_paprika/
│   ├── paprika_client.py      # thin wrapper over paprika-recipes (auth, write, photo)
│   ├── models.py              # Recipe schema (pydantic)
│   ├── parsers/               # json, yaml, markdown → Recipe
│   ├── service.py             # core: normalise → hash → POST; rate-limit/backoff
│   ├── api.py                 # FastAPI routes (REST + serves web UI)
│   ├── web/                   # templates/static for the Add Recipe form
│   └── mcp.py                 # FastMCP server exposing create/update/search
├── tests/                     # parser unit tests; client tests vs a mock/recorded API
├── Dockerfile
├── docker-compose.yml         # service + env for creds
├── .env.example               # PAPRIKA_EMAIL / PAPRIKA_PASSWORD, bind addr
└── LICENSE                    # MIT
```

## 6. Configuration & security (generic, not host-specific)

- Credentials via **environment variables** (`PAPRIKA_EMAIL`, `PAPRIKA_PASSWORD`)
  or an optional secrets file — never committed. `.env.example` documents them.
- Optional **API token / basic auth** on the hub itself so it isn't an open
  proxy if exposed beyond localhost.
- **Bind to localhost by default**; document putting it behind a reverse proxy or
  a private network (e.g. Tailscale/WireGuard) rather than the public internet —
  it holds Paprika credentials and proxies an unofficial API.
- Single-account by default; multi-account is a possible later extension.

## 7. Deployment (independent of any one machine)

- **Container-first:** `Dockerfile` + `docker-compose.yml` as the primary path.
- Document plain `uvx`/`pip` + `uvicorn` run for local/dev.
- Keep it stateless (no DB needed for MVP — Paprika is the store). Add a small
  cache only if list/search latency demands it.
- (Personal note for later, not part of the repo: it can be deployed onto your
  own infra however you manage servers — the repo stays infra-agnostic.)

## 8. Build roadmap

- **M0 — Validate the API. ✅ Done (2026-06-15).** Read + write + device-sync
  confirmed against the live account via `paprika-3-mcp` in a container (the host
  is NixOS, so the generic Linux binary runs in Docker). Listed existing recipes
  and wrote a full multi-step recipe, verifying it round-trips to the app. This
  locked in the write format and that token-login works; the `paprika-recipes`
  spike for smoked-paprika's *own* (v1 HTTP Basic) client is still pending and
  moves into M1.
- **M1 — Core + REST.** `paprika_client`, `models`, `service`, JSON `POST
  /recipes` + reads. Rate-limit/backoff. Tests for hashing/serialization.
- **M2 — Parsers.** YAML (reuse `paprika-recipes` shape) and forgiving markdown →
  Recipe, with unit tests.
- **M3 — Web UI.** Add-Recipe form + paste textarea; submission via the core.
- **M4 — MCP endpoint.** FastMCP create/update/search; document the
  image/text→JSON parsing prompt + schema.
- **M5 — Packaging & docs.** Dockerfile, compose, `.env.example`, README with
  quickstart + screenshots, LICENSE; publish.

## 9. Risks & caveats (document these in the README)

- **Unofficial API** — may change or break without notice; concentrating all
  Paprika calls in one client module keeps the blast radius small.
- **Rate limits / IP bans** — write one recipe at a time, back off, avoid bulk
  re-uploads.
- **Credentials at rest** — env/secret only; default to localhost; warn users not
  to expose publicly.
- **Validation safety** — test writes with a throwaway recipe (or a spare
  account) before any bulk operation.

## 10. References

- Foundation client: `paprika-recipes` — github.com/coddingtonbear/paprika-recipes (PyPI)
- Maintained fork (Python 3.11+, current Paprika API, built-in rate limiting): `tieguy/paprika-recipes` — github.com/tieguy/paprika-recipes
- AI/MCP reference impl: `paprika-3-mcp` — github.com/soggycactus/paprika-3-mcp
- API spec: mattdsteele gist `7386ec363badfdeaad05a418b9a1f30a`; `github.com/johnwbyrd/kappari`
- Other client (read-only/experimental): `paprika-rs` — github.com/Syfaro/paprika-rs

## 11. Open choices

Settled while bootstrapping:
- ✅ **Stack:** Python — FastAPI + FastMCP, reusing `paprika-recipes`.
- ✅ **Repo name:** `smoked-paprika` (Python import package `smoked_paprika`).
- ✅ **License:** MIT.

Still open, to settle when scaffolding the relevant milestone:
- **MCP transport:** HTTP-on-hub (remote assistants) vs. local stdio vs. both.
- **Client dependency:** which `paprika-recipes` to build on. The maintained fork
  [`tieguy/paprika-recipes`](https://github.com/tieguy/paprika-recipes) (Python 3.11+,
  current API, built-in rate limiting) is the leading candidate over upstream — decide
  whether to depend on it directly or vendor it. (Watch for pydantic v1/v2 compatibility
  against FastAPI/FastMCP when this is resolved in M1.)

# Smoked Paprika

A self-hostable service for reading and writing **[Paprika](https://www.paprikaapp.com/)**
recipes from anywhere — hand-typed markdown/YAML, a REST API, a web form, or an AI
assistant (MCP) — by wrapping Paprika's unofficial cloud-sync API behind one clean
backend. Paste, type, or scan a recipe on a computer or any browser and it lands in
your Paprika account and syncs to your phone.

> **Status: early development.** M0 (Paprika connectivity) is validated — reads and
> writes round-trip to a live account. The core client + REST API (M1) is next.
> See the [roadmap](docs/SPEC.md#8-build-roadmap).

## Why

Paprika has no Linux desktop app and no official API, so entering recipes received as
plain text (or photos) is tedious on a phone. Smoked Paprika gives you flexible,
scriptable entry paths from a computer or browser, plus a clean internal API others
can build on.

## How it works

One **core service** holds your Paprika credentials and is the only thing that talks
to Paprika (over the durable v1 HTTP Basic sync API): it normalises an incoming recipe,
computes the required hash, gzips it, and multipart-POSTs it. Several thin front-ends
sit in front of that core:

- **REST API** — `POST /recipes` (structured JSON or a markdown/YAML body), `GET /recipes`, `GET /recipes/{uid}`.
- **Web UI** — a minimal "Add Recipe" page with structured fields and a paste textarea.
- **MCP endpoint** — `create_recipe` / `update_recipe` / `search` tools so AI assistants can add recipes from natural language or images.

A server-side backend is mandatory: Paprika sends no CORS headers, so a browser can't
call it directly. See **[docs/SPEC.md](docs/SPEC.md)** for the full design, the API
reality, and the build roadmap.

## Development

The dev environment is managed with [devenv](https://devenv.sh/) + direnv + uv, with
[ty](https://github.com/astral-sh/ty) as the Python LSP.

```bash
direnv allow      # auto-loads the devenv shell on cd (or: devenv shell)
uv sync           # install dependencies into the managed venv
```

- Python is **un-pinned**, tracking the nixpkgs default (currently 3.13); `devenv update`
  moves it forward. `pyproject.toml` requires `>=3.13`.
- Committed env files: `devenv.nix`, `devenv.yaml`, `devenv.lock`, `.envrc`, `pyproject.toml`, `uv.lock`.

## Configuration

Credentials are supplied via environment variables and never committed:

- `PAPRIKA_EMAIL` / `PAPRIKA_PASSWORD` — your Paprika **cloud-sync** account.

**Bind to localhost by default.** This service holds your Paprika credentials and
proxies an unofficial API — put it behind a reverse proxy or a private network
(e.g. Tailscale/WireGuard) rather than the public internet. See
[SPEC §6](docs/SPEC.md#6-configuration--security-generic-not-host-specific).

## Caveats

- **Unofficial API** — Paprika's sync API may change or break without notice.
- **Rate limits / IP bans** — write one recipe at a time; avoid bulk re-uploads.
- Test writes with a throwaway recipe before any bulk operation.

## License

[MIT](LICENSE)

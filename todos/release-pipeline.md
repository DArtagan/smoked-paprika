# release-pipeline: the skeleton every later spec builds on

## Opening prompt

> Set smoked-paprika up the way reelbarrow is set up: package skeleton, devenv
> hooks, CI, release-please and an image published to GHCR. Read
> `todos/release-pipeline.md`. No application behaviour yet beyond `/healthz`.

## Why reelbarrow's setup

Will's `reelbarrow` repository (`~/repositories/reelbarrow`) went through this
same step as its own `release-pipeline` spec, landing 2026-10-19 over three pull
requests. Its tooling is the house style, and copying it means one set of
conventions across the two. Read its `devenv.nix`, `.config/wt.toml`,
`.github/workflows/{ci,release}.yaml`, `release-please-config.json`,
`Dockerfile`, `compose.yaml` and `docs/releasing.md`, and carry over what
applies. Its comments explain the non-obvious parts, such as the per-worktree
hooks path, publishing from the tag, and `UV_PYTHON_DOWNLOADS=never`. Keep them.

What does not carry over: the media tools (ffmpeg, chromaprint) and the
video-share volume.

## Where things stand (2026-10-30)

The scaffold is on the `release-pipeline` branch. Verified locally:

- `devenv test` passes, and pytest, ruff, treefmt and convco each ran on the
  scaffold's own commit.
- A commit adding `https://www.` + `paprikaapp.com` to
  `src/smoked_paprika/web.py` was refused by the pytest hook, which named the
  file.
- The image builds, runs as uid 1000, and answers `/healthz` with
  `{"status":"ok","version":"0.0.0"}`. `POST /mcp` is 404.
  `docker compose config` accepts the example.

Not yet run: CI on GitHub, the release PR, and publishing to GHCR.

On GitHub, *Allow GitHub Actions to create and approve pull requests* and
immutable releases were turned on on 2026-10-30, matching reelbarrow.
`.paprika-3-mcp/` and `.paprika.env`, left from the sync-API work, were
deleted at Will's word.

## Decisions

- **The host test covers every tracked file except Markdown** (Will,
  2026-10-30). The README and the design name the host to explain the rule. For
  that test to guard a commit, the pytest hook runs on any non-Markdown change,
  not only Python.
- **`serve` exposes `/healthz` and nothing else.** `FastMCP.http_app()` would
  also mount `/mcp`, unauthenticated, and the rules forbid that. So the app is
  a plain Starlette one. FastMCP is pinned at 4.1.4, whose release notes show
  nothing that bears on this project; 4.2.0a1 is a prerelease. The healthz
  handler has the shape of a FastMCP `custom_route`, so google-auth can move it
  across unchanged.

## Scope

- A `smoked_paprika` package with a `smoked-paprika serve` entry point and a
  `/healthz` route. FastMCP is the server framework: `fastmcp` 4.1.4 is current
  on PyPI at 2026-10-29. Check its release notes for anything newer before
  pinning.
- The test from `AGENTS.md` that fails if the source names `paprikaapp.com`.
  It lands here, before any code exists that could break it.
- devenv: treefmt, ruff, pytest and convco hooks; `devenv test` runs them all.
- CI running `devenv test` and an image build; release-please; publishing to
  `ghcr.io/dartagan/smoked-paprika` from the release tag.
- `compose.yaml` as the example deployment, `.dockerignore`, `docs/releasing.md`.
- `AGENTS.md`'s development-environment section rewritten with the real commands.

## Done when

- `devenv test` passes locally and in CI.
- Merging the first release pull request publishes
  `ghcr.io/dartagan/smoked-paprika:0.1.0`. The image is pulled and run, and
  `/healthz` answers from it, checked against the pulled image rather than a
  local build.
- A commit adding `paprikaapp.com` to a source file fails the hook.

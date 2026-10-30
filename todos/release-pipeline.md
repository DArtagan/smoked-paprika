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

## State at 2026-10-29

- `pyproject.toml` is a virtual project with no package, Python `>=3.13`, and
  pytest as the only dependency. `devenv.nix` enables Python, uv and the `ty` LSP
  and nothing else: no treefmt, no hooks. Both get replaced.
- The repository is public on GitHub as `dartagan/smoked-paprika`, default
  branch `main`.
- The ignored `.paprika-3-mcp/` and `.paprika.env` are left from the retired
  sync-API work. `.paprika.env` holds Paprika credentials. Neither is used any
  more; ask Will before deleting them.

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

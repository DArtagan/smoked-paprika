# AGENTS.md

Guidance for coding agents working in this repository.

smoked-paprika is a remote MCP server that gives Claude read access to a Paprika
recipe collection. It serves the latest export of the collection and receives
those exports from an iOS share-sheet Shortcut.
[`docs/design.md`](docs/design.md) is the design. Read it before changing
behaviour; its first section explains why this project must never talk to
Paprika's servers.

## Development environment

[devenv](https://devenv.sh/) provides Python and uv. `direnv` loads it on `cd`;
otherwise `devenv shell`.

The `release-pipeline` spec replaces this section with the real commands, as
it did in reelbarrow.

### Working here as an agent

- **`git diff --no-ext-diff`.** The global git config sends `git diff` through
  difftastic, whose side-by-side output is several times the size.
- **Verify with `devenv test`, not by printing files back.**
- **Filter noisy commands** down to the lines that carry the result.

## Rules that protect the account

- **Nothing contacts `paprikaapp.com`.** Paprika's terms forbid third-party
  access to its servers and threaten account blocks; see the design. No client,
  test, script or debugging session calls the sync API, however read-only or
  well paced. A test fails the build if the source names the host.
- **Read-only.** Nothing here produces a Paprika file for importing into the app.
- **Real recipes never enter the repository.** The repository is public. Tests
  run on synthetic exports from the fixture generator. A real export is used
  only under `captures/`, which is gitignored. The same holds for email
  addresses and hostnames. Secrets live in the deployment repository, encrypted,
  and reach the service through the environment.
- **No unauthenticated network transport.** HTTP always runs behind OAuth and
  the email allowlist; local development uses stdio.

## Project workflow

Work is specified in [`todos/`](todos/README.md), one self-contained spec per
step, ordered in that README. A spec's filename without `.md` is its **slug**,
which names the branch it is worked on. Work lands on `main` through a pull
request.

When a spec is done, whatever it leaves permanently true goes into `docs/`, and
the spec is deleted in the same pull request, with a line added to
[`docs/project_log.md`](docs/project_log.md). A retired slug is never reused.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/).

### The deployment half

smoked-paprika runs on a Kubernetes cluster deployed by Flux from a separate
GitOps repository, called **the deployment repository** throughout this one. It
holds the manifests, secrets and alert rules, and has its own rules for changing
them. A spec here that needs a deployment change says what has to change, not
how that repository is laid out. Where it is checked out is in
`CLAUDE.local.md`, which is not committed.

### Debugging captures

Anything pulled from a running system or a real export goes under
`captures/<topic>/` at the root of the checkout. `.gitignore` excludes it.
Whatever a conclusion rests on beyond the session belongs in a spec or in
`docs/` as quoted figures, never as copied recipe content.

## How it is phrased

Comments and docs describe what is, in present tense, and carry the reason where
a reader could otherwise reintroduce a bug. Dates and history belong in specs and
commit messages. A fact lives in one place.

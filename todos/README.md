# Outstanding work

One self-contained spec per step, each meant to be opened cold in its own
session. A file here means the work has not been done. When it is, its permanent
facts go into `docs/`, the spec is deleted, and
[`docs/project_log.md`](../docs/project_log.md) gets a line. See *Project
workflow* in [`AGENTS.md`](../AGENTS.md).

The design every spec builds on is [`docs/design.md`](../docs/design.md). Specs
name the sections they depend on rather than restating them.

## In order

Specs are referred to by name, not number, so finishing one renumbers nothing.

| # | spec | what | needs |
|---|---|---|---|
| 1 | [release-pipeline](release-pipeline.md) | Package skeleton, devenv hooks, CI, release-please, the image on GHCR | — |
| 2 | [export-reader](export-reader.md) | Parse an export into the collection; the synthetic fixture generator | release-pipeline |
| 3 | [upload-receiver](upload-receiver.md) | `POST /exports`: validate, guard against shrinking, swap atomically, keep history | export-reader |
| 4 | [mcp-tools](mcp-tools.md) | The four read-only tools, over stdio first | export-reader |
| 5 | [google-auth](google-auth.md) | OAuth through Google, the email allowlist, persistent proxy state | mcp-tools |
| 6 | [deployment](deployment.md) | The cluster half, the iOS Shortcut, and claude.ai connected end to end | upload-receiver, google-auth |
| 7 | [metrics](metrics.md) | Last upload time and liveness, so the cluster can remind and alert | deployment |

upload-receiver and mcp-tools both need only export-reader, and can be done in
either order.

## Writing a spec

- **State what was verified and when.** Anything not checked says so.
- **Record why, not just what**, and record Will's decisions verbatim, so they
  are not relitigated.
- **Point at the design rather than restating it.** Two copies drift.
- **End with done-when conditions measured on the running system, a device or
  Claude itself**, never inferred from the service's own report.
- **Include the opening prompt.**
- **Correct in place.** When a finding is overturned, rewrite the passage and
  note the wrong turn if it could be repeated.

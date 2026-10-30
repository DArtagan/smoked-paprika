# Releasing

A release is a deliberate act: merging a commit to `main` publishes nothing.

## How a version is made

1. Commits on `main` follow [Conventional Commits](https://www.conventionalcommits.org/).
   The `convco` commit-msg hook refuses any that do not, because release-please
   reads nothing else.
2. On every push to `main`, release-please updates a standing pull request,
   `chore(main): release X.Y.Z`. It bumps the version in `pyproject.toml`,
   `uv.lock` and the example `compose.yaml`, and writes `CHANGELOG.md` from the
   commits since the last release.
3. Merging that pull request tags `vX.Y.Z` and creates a GitHub release. The
   `publish` job then builds the image **from the tag** and pushes
   `ghcr.io/dartagan/smoked-paprika:X.Y.Z`, and `latest`.

Neither tags nor the release branch carry the package name. In
`release-please-config.json`, `include-component-in-tag` is false and
`package-name` is absent: release-please names the branch from `package-name`
whatever the tag setting says, which made 0.1.0's branch
`release-please--branches--main--components--smoked-paprika`. The python
strategy reads the name from `pyproject.toml` instead.

Below 1.0, a breaking change bumps the minor version rather than the major, and
so do `feat` commits; `fix` bumps the patch. For the `python` release type,
`docs:` commits are releasable too, so a commit that only edits `todos/` uses
`chore(todos):`.

Releases are immutable once published: GitHub refuses to change a release's tag
or assets. A mistaken release is fixed by the next one.

Release PRs are opened by `github-actions`, and GitHub holds CI on them at
*action required* until someone approves the run from the PR. Approving is
optional: they change only versions and the changelog, and CI runs on `main`
once one is merged. Opening them needs the repository setting *Allow GitHub
Actions to create and approve pull requests*.

## Checking a release

The tag, the image and the source should all name the same commit:

```bash
git rev-parse 'vX.Y.Z^{commit}'
skopeo inspect docker://ghcr.io/dartagan/smoked-paprika:X.Y.Z \
  | jq -r '.Labels["org.opencontainers.image.revision"]'
```

The running server reports its version on `/healthz`.

# deployment: on the cluster, on the phone, in claude.ai

## Opening prompt

> Deploy smoked-paprika, build the share-sheet Shortcut, and connect claude.ai.
> Read `todos/deployment.md`. The cluster half is a change in the deployment
> repository, under that repository's rules.

## What the deployment repository needs

The deployment repository holds its own conventions, so this lists what has to
be true, not how to lay it out.

- **A public HTTPS hostname.** claude.ai connects from Anthropic's cloud, the
  phone uploads from anywhere, and Google's redirect comes through the user's
  browser. All three paths must be reachable from the internet: `/mcp`, the
  OAuth routes and `/exports`.
- **The proxy's body limit raised above the upload cap** for `/exports` only.
  ingress-nginx defaults to 1 MiB, and the export is 10 MiB.
- **Optional:** restricting `/mcp` to Anthropic's published outbound ranges
  ([IP addresses](https://platform.claude.com/docs/en/api/ip-addresses)). The
  upload and OAuth paths cannot be restricted that way. Weigh it against
  breakage when the ranges change: an open issue at
  `anthropics/claude-ai-mcp#259` asks about IPv6 ranges.
- **A volume for `/data`** holding the current export, its history and the OAuth
  proxy's storage. Exports can be re-made from the phone; the OAuth state costs
  a reconnect. Decide whether it needs backing up and record why, through the
  deployment repository's backup-coverage mechanism, whichever way that goes.
- **Secrets, encrypted:** the Google client ID and secret, the proxy signing
  key, the upload token and the allowed email addresses.
- **Image automation** following the published semver tags.
- **The Google OAuth client** created in Google Cloud Console, with the
  production redirect URI.

## The Shortcut

Built on the phone: *Receive Files from Share Sheet* → *Get Contents of URL*
(POST, `Authorization: Bearer …`) → *Show Result*. Verify the unverified
points from upload-receiver here at the latest:

- what Paprika's export puts in the share sheet
- whether Shortcuts appears there at all
- whether the filename arrives, which carries the export's scope (its time is in
  the zip)
- that a 10 MiB upload completes over cellular

Document the Shortcut as steps in `docs/`, with the token as a placeholder.
An iCloud share link would embed the token, so it never goes in the repository.

## Done when

- An export shared from Paprika on the iPhone reaches the server through the
  Shortcut, and the Shortcut shows the counts.
- A one-recipe export shared the same way is refused with the shrink guard's
  message, and the collection is unchanged.
- claude.ai, with the custom connector added, answers the mcp-tools questions
  from the deployed server.
- A second Google account is refused in claude.ai.
- The pod is deleted, and claude.ai keeps working without signing in again.

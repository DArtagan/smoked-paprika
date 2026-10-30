# Design

smoked-paprika gives Claude read access to a Paprika recipe collection. It is a
remote MCP server serving the most recent export of the collection, and the
receiver those exports are uploaded to. Nothing in it talks to Paprika.

```
iPhone                                    smoked-paprika
──────                                    ──────────────
Paprika ─ Export Recipes ─ share sheet ─▶ POST /exports  ──▶ /data: current export
          (All Recipes, Paprika format)   (bearer token)            │
          "Send to smoked-paprika"                                   ▼
          Shortcut                                          in-memory collection
                                                                     │
claude.ai ──────────────────────────────▶ /mcp  (OAuth via Google) ◀─┘
```

## Why an export, and never the sync API

Paprika's terms of use, last modified 2026-10-15, say:

> The Software relies on backend services ("Services") operated by Company. The
> Services are intended only for direct use by the Software. Accessing the
> Services by any other means is not permitted under the terms of this Agreement
> and may result in your account being temporarily or permanently blocked.

Their *Unsupported Uses* section adds "using any third-party application, script,
or other tool to access the Services" and "importing into the Software any
Paprika data files that were not created by the Software, or that were
externally altered after being created". The Wayback Machine's copy from
2026-10-14 has neither passage, so this is a deliberate policy rather than
inherited boilerplate. It applies to reads as much as writes, and pacing
requests does nothing about it.

Before the clause, the known risk was an automatic IP block. In September 2024 a
developer pulling ~43 recipes per page load, and ~300 requests a minute while
developing, had `paprikaapp.com` stop answering their whole home network for a
few minutes. Every device behind that IP was affected, phones included. The same
month the v2 login began refusing clients it does not recognise. Both are on the
[mattdsteele gist](https://gist.github.com/mattdsteele/7386ec363badfdeaad05a418b9a1f30a).
An earlier version of this project was built on the sync API, and its notes are
in git history from before this design.

So:

- **No code here contacts `paprikaapp.com`.** A test holds that line.
- **smoked-paprika is read-only.** It never writes a `.paprikarecipes` file meant
  for import, since the terms call importing externally altered files
  unsupported and warn of corruption.

## The export

An export is made by hand in the app: Settings → Export Recipes → All Recipes →
Paprika Recipe Format. Paprika's support guide recommends it as a backup method.
No Shortcuts action exports recipes. Paprika 4's actions cover grocery lists,
pantry, meals and links only, so the share sheet is the only route out.

Measured on 2026-10-29 against a Paprika 3 iOS export of 167 recipes:

- A zip of one `.paprikarecipe` entry per recipe, each gzip-compressed JSON.
  Entry names derive from the recipe name, but 29 of 167 differ from it, so
  **recipes are keyed by `uid`**, never by entry name.
- 24 top-level fields: `uid`, `name`, `ingredients`, `directions`, `description`,
  `notes`, `nutritional_info`, `servings`, `difficulty`, `prep_time`,
  `cook_time`, `total_time`, `source`, `source_url`, `rating` (int), `categories`,
  `created` (`YYYY-MM-DD HH:MM:SS`), `hash`, `image_url`, `photo`, `photo_hash`,
  `photo_data`, `photo_large`, `photos`. Every value is a string except where
  noted and the image fields, which can be null.
- `categories` holds category **names**, not IDs: 13 distinct across the
  collection. The export has no trash, favourite, pin or cookbook flags.
  Paprika 4's guide says its exports add cookbook information, which has not
  been seen yet. Unknown fields are kept and ignored, never rejected.
- Photos are base64 JPEG in `photo_data` and in `photos[].data`: 12.8 MiB of the
  file, against 0.35 MiB of text. The whole export is 10 MiB compressed.
- Text conventions: of the 159 non-empty `directions`, 135 separate steps with a
  blank line and 17 use single newlines only. One contains CRLF. 23
  `ingredients` use blank lines to group items. Eight recipes have no directions.
- **A single-recipe export is structurally identical to a full one**: a zip with
  one entry. Nothing in the file says which kind it is.

## Replacing the collection

Each upload replaces the collection wholesale. An export is a snapshot, and
merging snapshots would keep recipes deleted in the app alive here forever.

Because a one-recipe export looks like a full one, **an upload never silently
shrinks the collection.** An upload that would remove more than a small share of
the current recipes is refused, and the refusal says why and how to override it.
The threshold and the override are settled in the upload-receiver spec.

An upload is validated completely before anything is replaced. A corrupt entry
rejects the whole file, and the swap to the new export is atomic. The previous
few exports are kept, so a bad replacement can be undone.

## Freshness

The collection is as fresh as the last export, and nothing on the server can
make it fresher. So the server reports staleness rather than hiding it. A
status tool gives the export's age and recipe count, and the server's
instructions ask Claude to mention the age when it matters. A metric carries
the last upload time, so the deployment can send a reminder to re-export.

## MCP surface

Read-only tools, annotated `readOnlyHint`:

- **search** by text across name, ingredients, description and notes, with an
  optional category filter. It returns names, uids and categories, not whole
  recipes.
- **get a recipe** by uid, as readable text with directions split into steps.
- **list categories** with their recipe counts.
- **collection status**: export time, upload time, recipe count.

167 recipes of text fit in memory with room to spare, so search is plain
in-memory matching. Claude does the fuzzy reasoning; the server finds candidates.
Photos are not served. MCP image results would make that possible later, but
they are 97% of the export's bytes and no tool needs them yet.

## Authentication

The server has two doors, with different callers.

**`/mcp`, for Claude: OAuth through Google.** Claude connects from Anthropic's
cloud, not the user's device, so the endpoint is public. Claude's OAuth client
needs Dynamic Client Registration or a Client ID Metadata Document. Google
offers neither, so FastMCP's `GoogleProvider` runs an **OAuth proxy**. It
presents DCR to Claude and uses one pre-registered Google client upstream
([docs](https://gofastmcp.com/integrations/google)). Two consequences:

- **Any Google account can complete sign-in.** Authentication says who the
  caller is; it does not say who may use the server. An allowlist of email
  addresses is checked on every request, server-wide, through FastMCP's
  `AuthMiddleware`. Allowing everyone is not a mode the server has.
- **The proxy keeps state:** client registrations and encrypted upstream tokens.
  It needs an explicit signing key and storage that survives a restart.
  Otherwise every restart makes Claude reconnect.

The decision is to "delegate it to Google for now". A self-hosted OAuth provider
is planned to replace Google later. The provider is configuration, so swapping
it does not touch the tools.

**`/exports`, for the Shortcut: a bearer token.** Shortcuts can set a request
header but cannot run an OAuth flow. The token is compared in constant time and
grants upload only.

There is no unauthenticated network transport. Local development uses stdio,
which has no network listener.

## Generality

One collection, configured entirely through the environment, shipped as a
container with an example Compose file. Nothing here knows about any particular
cluster, domain or account. The author's deployment lives in a separate
repository (see `AGENTS.md`).

## Data in the repository

The repository is public. Real recipes, exports, email addresses and hostnames
never enter it. Tests run on synthetic exports built by a generator that
reproduces the measured shape above. A real export is used only locally, under
the gitignored `captures/`.

## Not doing, and why

Recorded so these are not proposed again without new information.

- **Anything through the sync API**, for the reasons above.
- **Writes, grocery lists, meal plans.** Paprika 4 has sanctioned paths for
  these: the *Export Grocery List* and *Add To Grocery List* Shortcuts actions,
  and a meal-plan calendar feed. On 2026-10-29 the scope was set to recipes
  alone: "Smoked Paprika will just be a MCP connector to an export of recipes,
  and a receiver of those exports."
- **Fully automatic recipe refresh.** The one way found is to run the Paprika 4
  desktop app in a Windows VM, letting it sync as the official client, and to
  read its local SQLite database read-only. That costs a Windows licence, a
  Paprika 4 Premium subscription once the beta ends (the free version has no
  cloud sync), and a database layout documented only for Paprika 3, by
  [kappari](https://github.com/johnwbyrd/kappari). The share-sheet route was
  chosen instead. Writing to that database is exactly what the terms forbid.

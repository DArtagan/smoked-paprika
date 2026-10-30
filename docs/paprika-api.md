# Paprika cloud-sync API — verified notes

Working reference for the unofficial Paprika v1 sync API, written from **direct
observation against a live account**, not from third-party write-ups. Where a claim
comes from someone else's reverse-engineering and we have not confirmed it ourselves,
it is marked **unverified** — treat those as leads, not facts.

`docs/SPEC.md` §2 is the design-level summary; this file is the operational detail.

**Verification log**

| Date | What was verified |
|---|---|
| 2026-06-15 | Read + write round-trip via `paprika-3-mcp` (M0); recipe reached the app |
| 2026-08-05 | Direct HTTP Basic read/write with `curl`; field inventory; hash formula disproved; text conventions confirmed; app-side import bug observed |

---

## 1. Auth

HTTP Basic with the account's **cloud-sync** email and password, on every request:

```bash
curl -s -u "$PAPRIKA_EMAIL:$PAPRIKA_PASSWORD" \
  "https://www.paprikaapp.com/api/v1/sync/recipes/"
```

**Verified.** Both reads and writes work this way with no token exchange, no device
registration, and no other headers.

There is also a token endpoint (`POST /api/v1/account/login` → Bearer token) which
`paprika-3-mcp` uses and which worked in M0. **Prefer HTTP Basic**: the token path has
device-auth checks and is reported to be more rate-limit/ban-prone.

## 2. Endpoints

Base: `https://www.paprikaapp.com/api/v1/sync`

| Method | Path | Purpose |
|---|---|---|
| GET | `/recipes/` | Index — array of `{uid, hash}` for every recipe |
| GET | `/recipe/{uid}/` | One full recipe record |
| POST | `/recipe/{uid}/` | Create **or** update that uid |

All responses are wrapped: `{"result": ...}`. A successful write returns
`{"result": true}` with HTTP 200.

The index is the sync primitive: clients diff the `hash` values to decide what to
re-download. See §4 for why that matters more than it looks.

### Writing

The body is `multipart/form-data` with a single field `data` containing the
**gzip-compressed JSON** of the complete record:

```bash
# recipe.json -> gzip -> multipart field "data"
gzip -c recipe.json > upload.gz
curl -s -u "$PAPRIKA_EMAIL:$PAPRIKA_PASSWORD" \
     -F "data=@upload.gz" \
     "https://www.paprikaapp.com/api/v1/sync/recipe/${UID}/"
```

**Verified**, including with a `curl -F` file upload (the filename is ignored; only the
field name `data` matters).

Send the **whole record**, not a partial patch — this is a replace, not a merge. The
safe update pattern is: `GET` the current record → mutate fields → `POST` it back.

*Unverified:* that every field must be present even when empty (we have only ever sent
complete records), and that photos upload as a separate binary field.

## 3. The recipe record

33 fields, confirmed identical across app-created and API-created recipes.

**Content**

| Field | Type | Notes |
|---|---|---|
| `uid` | str | Uppercase UUID. App-made ones often carry a suffix (`…-2952-00000198E4087D2A`); a plain UUID is accepted fine |
| `name` | str | |
| `ingredients` | str | One item per line, separated by single `\n` — see §5 |
| `directions` | str | Steps separated by `\n\n` — see §5 |
| `description` | str | |
| `notes` | str | |
| `nutritional_info` | str | |
| `servings` | str | Free text — the app writes things like `"Serves 6"` |
| `difficulty` | str | Free text |
| `prep_time` / `cook_time` / `total_time` | str | Free text, e.g. `"15 minutes"` |
| `prep_minutes` / `cook_minutes` / `total_minutes` | int/null | Numeric counterparts; observed `null` on every recipe sampled |
| `servings_min` / `servings_max` | int/null | Observed `null` throughout |
| `source` | str | Attribution — a person (`"Rocky Meza"`) or a domain (`"epicurious.com"`) |
| `source_url` | str | Full URL |
| `rating` | int | `0` when unrated |
| `categories` | list | Array of category uids |
| `cookbook_uid` | str/null | |
| `scale` | str/null | e.g. `"1/1"` |

**Photos**

`photo`, `photo_hash`, `photo_large`, `photo_url`, `image_url` — all string/null.
Not yet exercised by us.

**Flags and bookkeeping**

`in_trash`, `is_pinned`, `on_favorites`, `on_grocery_list` (bool);
`created` (str, `"YYYY-MM-DD HH:MM:SS"`); `hash` (str); `metadata_version` (null in
every recipe sampled).

### Empty-value conventions

The app and third-party clients disagree on how to spell "empty", and both round-trip
fine, but **match the app** to minimise the chance of tripping app-side quirks:

| Field | App writes | `paprika-3-mcp` writes |
|---|---|---|
| `categories` | `[]` | `null` |
| `scale` | `null` or `"1/1"` | `""` |
| `image_url` | `null` | `""` |

### Fields third-party clients drop

`paprika-3-mcp` exposes no way to set `source` / `source_url`, so recipes created
through it carry no attribution. **smoked-paprika's client must support both** — for
a service whose main job is capturing recipes from elsewhere, attribution is core, not
optional. Setting them by hand afterwards is a full GET-mutate-POST cycle.

## 4. The `hash` field — the documented formula is wrong

Widely repeated (and previously in our own SPEC): *`hash` = sha256 of the JSON with the
`hash` field removed and keys sorted.*

**This is false.** On 2026-08-05 it was tested against three recipes created by the
Paprika app itself, across four serialisations (sorted keys × compact/default
separators × `ensure_ascii` on/off). **No variant reproduced any stored hash.**

Corroborating detail: app-written hashes are **uppercase** hex, while client-written
ones are lowercase — different implementations, and neither matches the formula above.

What is actually true, and verified:

- **The server does not validate the hash.** A record written with a hash computed by
  the (wrong) sorted-keys scheme was accepted with `{"result": true}` and synced to
  devices normally.
- The only real requirement is that **the hash changes when the content changes**, so
  other clients notice via the index and re-download.

**Practical rule for our client:** treat `hash` as an opaque change-detection token.
Compute it deterministically over the record (any stable scheme works), and assert it
differs from the previous value before writing — a stale hash means clients silently
never pull the update.

**Open:** the canonical algorithm is still unknown. It is probably computed over a
subset of fields, or over the app's own field ordering, rather than the full sorted
record. Worth deriving properly — see §6 for why it may not be cosmetic.

## 5. Text formatting conventions

The app renders `ingredients` and `directions` as plain text with light formatting
rules. Getting these wrong produces a wall of text even though the data looks fine as
JSON.

- **Directions:** steps are separated by a **blank line** (`\n\n`). A single `\n`
  renders as a line break *within* the same step, not a new step.
- **Ingredients:** one item per line, single `\n`. Blank lines create visual groups
  (e.g. a `Sauce` sub-heading).
- **No auto-numbering.** The app will not number steps for you. Writing explicit
  `1. `, `2. ` prefixes is fine and is the only way to get numbers.
- **Never use CRLF.** Across 171 recipes in a real account there is not a single
  `\r\n`. Use bare `\n` exclusively.

Verified by inspecting recipes hand-typed in the app, which use exactly this encoding.

## 6. Gotcha: correct server data can still import wrong

**Observed 2026-08-05.** A recipe was written via the API with `\n\n` between all seven
steps. The server copy was verified — byte-level — to contain all six blank-line
separators. The app nonetheless displayed it as **two** blocks, and the app's *edit*
view showed only **one** blank line. A force sync did not fix it.

Ruled out during diagnosis:

- Not line endings — the record used bare `\n\n`, exactly what app-typed recipes use.
- Not a malformed record — field-by-field diff against an app-created recipe showed the
  same 33 keys and types.
- Not a byte-level anomaly — all six separators were identical `\n\n`, no trailing
  whitespace, no unusual codepoints.
- Not staleness — the problem survived a force sync.

The fix was to re-add the blank lines **by hand in the app**. The record the app then
held was byte-for-byte identical to what had been written via the API — and its `hash`
field was still the one *we* wrote, proving the app never even re-uploaded.

So the corruption happened entirely in the app's **local import** of an
externally-written record.

**Untested hypothesis:** because our records carry a non-canonical `hash` (§4), the
app's change-detection may take a reconciliation path that a correctly-hashed record
would avoid. This is the main reason deriving the real hash algorithm may matter
beyond tidiness.

**Consequences for smoked-paprika:**

1. A `200 {"result": true}` and a correct server-side read **do not** prove the recipe
   arrived intact on the user's device. Don't report success as if they do.
2. Any end-to-end test must include a check on an actual device, not just a read-back.
3. When deriving the canonical hash (§4), re-test this import path first — it is the
   cheapest available signal on whether the hypothesis holds.

## 7. Rate limiting

Bulk or rapid calls risk IP bans. Write one recipe at a time and space reads out
(~2s between calls was used for the investigations above without incident). The
`tieguy/paprika-recipes` fork has ~2s rate limiting built in.

## 8. Reproducing

Everything in §§1–6 was established with plain `curl` + `python3` and HTTP Basic — no
client library or container required. Credentials come from the gitignored
`.paprika.env` (`PAPRIKA_EMAIL` / `PAPRIKA_PASSWORD`); load with
`set -a; . ./.paprika.env; set +a` and never echo the values.

Inspect a record's exact bytes — the technique that settled the formatting questions:

```bash
curl -s -u "$PAPRIKA_EMAIL:$PAPRIKA_PASSWORD" \
     "https://www.paprikaapp.com/api/v1/sync/recipe/${UID}/" \
  | python3 -c "import sys,json; print(repr(json.load(sys.stdin)['result']['directions']))"
```

`repr()` is the point: newline handling is invisible in pretty-printed output.

The M0 harness (a container running the `paprika-3-mcp` Go binary, needed because the
NixOS host cannot execute a generic glibc binary directly) lives in the gitignored
`.paprika-3-mcp/`. It is only useful as a reference implementation now — direct `curl`
is simpler and does not hide the wire format.

## 9. References

- API reverse-engineering write-up (mattdsteele) — https://gist.github.com/mattdsteele/7386ec363badfdeaad05a418b9a1f30a
- API spec: `github.com/johnwbyrd/kappari`
- `paprika-recipes` — github.com/coddingtonbear/paprika-recipes
- Maintained fork — github.com/tieguy/paprika-recipes
- `paprika-3-mcp` (Go, MCP server) — github.com/soggycactus/paprika-3-mcp
- `paprika-rs` (read-only/experimental) — github.com/Syfaro/paprika-rs

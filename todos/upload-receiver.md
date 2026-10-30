# upload-receiver: `POST /exports`

## Opening prompt

> Build the upload endpoint the iOS Shortcut posts exports to. Read
> `todos/upload-receiver.md` and the design's *Replacing the collection* and
> *Authentication* sections.

## What is known

- The real export is 10 MiB. Photos make up nearly all of it and grow with the
  collection, so the size cap needs headroom: say 100 MiB, configurable only if
  a reason appears. The reverse proxy in front has its own body limit;
  ingress-nginx defaults to 1 MiB. That is the deployment spec's concern, but
  the error a client sees when it is hit should be recognisable.
- Shortcuts' *Get Contents of URL* can POST with a custom header, and its
  request body can be a raw file or a form with a file field
  ([Apple](https://support.apple.com/guide/shortcuts/request-your-first-api-apd58d46713f/ios);
  a worked share-sheet upload is at
  [alikhil.dev](https://alikhil.dev/posts/ios-shortcut-for-microbin/)). Accept
  one of the two and say which in the docs. Raw is simpler to receive. The
  export's time is read from the zip itself (the design's *The export*), so the
  filename matters only for its scope, `All Recipes`. A form might carry it;
  whether a one-recipe export's filename says something else is unmeasured.
- **The reader** is `smoked_paprika.export.read_export`, which takes a path or
  binary file and returns the collection or raises `ExportError`, whose `entry`
  names the bad entry. It caps entry count and decompressed size, but
  `zipfile` parses the whole central directory before the entry cap applies.
  The upload's body cap is what bounds that, so it must be enforced before the
  reader sees the file.
- `hash` is stable for an unchanged recipe: all 167 matched between a Paprika 3
  and a Paprika 4 export taken a day apart.
- **Unverified:** what Paprika's export hands the share sheet (a file, and with
  what name), and whether Shortcuts appears in that sheet at all. The deployment
  spec checks on the phone. If this spec can be checked sooner against a dev
  server the phone can reach, do it here and record the answer.

## Scope

- Bearer-token auth, compared in constant time, with a token configured in the
  environment. No token configured means the endpoint is off, not open.
- Validate the whole upload with export-reader before touching anything.
- **The shrink guard.** Refuse an upload that would remove more than a set share
  of the current recipes. The response names the numbers and how to override.
  Pick the threshold from what a real deletion spree looks like, and record why.
  A one-recipe export against 167 must be refused. Decide whether a first
  upload into an empty store is exempt; it has nothing to shrink.
- **Atomic swap and history.** Write the new export beside the old, then rename
  into place, and keep the last few exports. The in-memory collection switches
  only after the file is in place. A restart loads the current export from disk.
- **The response is for a human reading a Shortcut's result**: one or two lines
  with recipe count and added, removed and changed counts. Changed is detected
  by `hash`.

## Done when

- Tests cover: a missing or wrong token, a corrupt upload leaving the current
  export untouched, an oversized upload, the shrink guard firing and being
  overridden, and a restart serving the last good export.
- The real export uploaded with `curl` to a local server loads, and a second
  upload of the same file reports zero changes.

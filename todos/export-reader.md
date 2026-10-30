# export-reader: from a `.paprikarecipes` file to the collection

## Opening prompt

> Build the export reader and the synthetic fixture generator. Read
> `todos/export-reader.md` and the design's *The export* section. A real export
> is in `captures/exports/`; it never leaves there.

## What is known

The design's *The export* section holds every measured fact: the container
format, the 24 fields, category names rather than IDs, photo sizes, text
conventions, and the single-recipe export. It was measured on 2026-10-29 against
a Paprika 3 iOS export of 167 recipes, read in place with `zipfile` and `gzip`
and never extracted. Will joined the Paprika 4 beta after taking that export,
so the next one will come from Paprika 4. Its guide says cookbook information
is added. **Take a fresh export at the start and re-measure the fields before
writing the model**, then correct the design if they moved.

Will's real exports go in `captures/exports/`. They are personal data in a
public repository's working tree, safe only because `captures/` is ignored.
Confirm `git check-ignore` agrees before copying one in.

## Scope

- **Reading.** Open the zip, gunzip and parse each entry, and build an in-memory
  collection keyed by `uid`. The file is untrusted input from the network, so
  cap entry count and decompressed size, which is the zip-bomb case. Parse with
  the standard library, and never extract to disk.
- **All or nothing.** One bad entry rejects the file: corrupt gzip, invalid
  JSON, a missing `uid` or `name`, or a duplicate `uid`. The error names the
  entry. A partially read collection must never be served.
- **The model.** Keep the fields the tools use, normalise CRLF to LF, and drop
  photo data after reading so the collection holds text only. Unknown fields
  are tolerated, never rejected; the design says why.
- **Directions as steps.** Split on blank lines. For the 17 recipes that use
  single newlines only, decide from the real export whether each line is a step,
  and record the rule and its reason in the design.
- **Export metadata.** Recipe count, and the export's own time. The filename
  `Export 2026-10-29 23.23.28 All Recipes.paprikarecipes` carries both a time and
  a scope ("All Recipes"). Whether that name survives the share sheet into the
  Shortcut's upload is unverified; upload-receiver finds out.
- **The fixture generator.** It writes synthetic exports with the measured
  shape: an entry name that differs from the recipe name, CRLF, empty
  directions, single-newline directions, grouped ingredients, small photos,
  an unknown extra field, plus one-entry and corrupt variants. Generated content
  is obviously fake: no real recipe text, and nothing copied from the capture.

## Done when

- The reader loads the real export, and its recipe count and category count
  match an independent count taken with `zipfile` in the session.
- Tests over generated fixtures cover every variant above, including rejection
  of the corrupt ones, with the offending entry named.
- Memory held by the loaded real collection is measured, not estimated, and
  recorded in the design.

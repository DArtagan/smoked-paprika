"""Reading a `.paprikarecipes` export into the collection.

The design's *The export* section has the measured format. The file arrives from
the network, so every size is capped before it is allocated, and one bad entry
rejects the whole file: a partly read collection is never served.
"""

import json
import re
import zipfile
import zlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import IO, Any

ENTRY_SUFFIX = ".paprikarecipe"

# A 167-recipe export is 14 MiB of JSON, nearly all of it photos, and its
# largest entry is under 2 MiB.
MAX_ENTRIES = 10_000
MAX_ENTRY_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024

TEXT_FIELDS = (
    "ingredients",
    "description",
    "notes",
    "nutritional_info",
    "servings",
    "difficulty",
    "prep_time",
    "cook_time",
    "total_time",
    "source",
    "source_url",
    "created",
)

BLANK_LINE = re.compile(r"\n\s*\n")
NUMBERED = re.compile(r"\d+[.)]\s")


class ExportError(ValueError):
    """The file is not a readable export. `entry` names the offending entry."""

    def __init__(self, reason: str, entry: str | None = None):
        self.reason = reason
        self.entry = entry
        super().__init__(f"{entry}: {reason}" if entry else reason)


@dataclass(frozen=True, slots=True)
class Recipe:
    uid: str
    name: str
    categories: tuple[str, ...]
    ingredients: str
    steps: tuple[str, ...]
    description: str
    notes: str
    nutritional_info: str
    servings: str
    difficulty: str
    prep_time: str
    cook_time: str
    total_time: str
    source: str
    source_url: str
    rating: int
    created: str


@dataclass(frozen=True, slots=True)
class Collection:
    recipes: Mapping[str, Recipe]
    # When the export was made, from the zip itself rather than the filename,
    # which may not survive the share sheet. None if the zip carries no time.
    exported_at: datetime | None


def read_export(file: str | IO[bytes]) -> Collection:
    try:
        archive = zipfile.ZipFile(file)
    except (zipfile.BadZipFile, ValueError) as error:
        raise ExportError(f"not a zip file: {error}") from error
    with archive:
        entries = [info for info in archive.infolist() if not info.is_dir()]
        if not entries:
            raise ExportError("the export has no recipes")
        if len(entries) > MAX_ENTRIES:
            raise ExportError(f"more than {MAX_ENTRIES} entries")

        recipes: dict[str, Recipe] = {}
        total = 0
        for info in entries:
            name = info.filename
            if not name.endswith(ENTRY_SUFFIX):
                raise ExportError(f"not a {ENTRY_SUFFIX} entry", name)
            data = _read_entry(archive, info, MAX_TOTAL_BYTES - total)
            total += len(data)
            recipe = _parse_recipe(data, name)
            if recipe.uid in recipes:
                raise ExportError(f"duplicate uid {recipe.uid!r}", name)
            recipes[recipe.uid] = recipe

    return Collection(recipes=recipes, exported_at=_exported_at(entries))


def split_steps(directions: str) -> tuple[str, ...]:
    """Directions as steps; the design's *The export* section has the rule."""
    text = directions.strip()
    if not text:
        return ()
    if BLANK_LINE.search(text):
        return tuple(part.strip() for part in BLANK_LINE.split(text))
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not NUMBERED.match(lines[0]):
        return tuple(lines)
    # In a list that numbers its steps, an unnumbered line is a wrapped
    # continuation of the step before it.
    steps = [lines[0]]
    for line in lines[1:]:
        if NUMBERED.match(line):
            steps.append(line)
        else:
            steps[-1] = f"{steps[-1]} {line}"
    return tuple(steps)


def _read_entry(archive: zipfile.ZipFile, info: zipfile.ZipInfo, budget: int) -> bytes:
    name = info.filename
    # The sizes in the zip's directory are claims, not limits, so each read is
    # bounded by what is actually produced.
    limit = min(MAX_ENTRY_BYTES, budget)
    try:
        with archive.open(info) as stream:
            compressed = stream.read(limit + 1)
    except (zipfile.BadZipFile, RuntimeError, OSError, EOFError, zlib.error) as error:
        raise ExportError(f"unreadable zip entry: {error}", name) from error
    if len(compressed) > limit:
        raise ExportError("entry exceeds the size limit", name)
    return _gunzip(compressed, limit, name)


def _gunzip(data: bytes, limit: int, name: str) -> bytes:
    out = bytearray()
    try:
        while data:
            stream = zlib.decompressobj(wbits=zlib.MAX_WBITS | 16)
            out += stream.decompress(data, limit + 1 - len(out))
            if len(out) > limit or stream.unconsumed_tail:
                raise ExportError("entry exceeds the size limit", name)
            if not stream.eof:
                raise ExportError("truncated gzip data", name)
            # gzip allows several members back to back.
            data = stream.unused_data
    except zlib.error as error:
        raise ExportError(f"corrupt gzip data: {error}", name) from error
    return bytes(out)


def _parse_recipe(data: bytes, name: str) -> Recipe:
    try:
        raw = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExportError(f"invalid JSON: {error}", name) from error
    if not isinstance(raw, dict):
        raise ExportError("the recipe is not a JSON object", name)

    for field in ("uid", "name"):
        if not isinstance(raw.get(field), str) or not raw[field].strip():
            raise ExportError(f"missing {field}", name)

    # Other fields Paprika may leave null or, in a newer version, omit.
    # Unknown fields are ignored; the design's *The export* section says why.
    text = {field: _text(raw, field, name) for field in TEXT_FIELDS}
    categories = raw.get("categories") or []
    if not isinstance(categories, list) or not all(
        isinstance(category, str) for category in categories
    ):
        raise ExportError("categories is not a list of names", name)
    rating = raw.get("rating") or 0
    if not isinstance(rating, int) or isinstance(rating, bool):
        raise ExportError("rating is not an integer", name)

    # Photos are dropped here, with the rest of the JSON, so the collection
    # holds text only.
    return Recipe(
        uid=raw["uid"],
        name=_normalise(raw["name"]).strip(),
        categories=tuple(categories),
        steps=split_steps(_text(raw, "directions", name)),
        rating=rating,
        **text,
    )


def _text(raw: dict[str, Any], field: str, name: str) -> str:
    value = raw.get(field)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ExportError(f"{field} is not a string", name)
    return _normalise(value)


def _normalise(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _exported_at(entries: list[zipfile.ZipInfo]) -> datetime | None:
    # Paprika 4 stamps every entry with the export time in UTC, to the zip
    # format's two seconds. 1980-01-01 is the zip format's "no time".
    stamp = max(info.date_time for info in entries)
    if stamp <= (1980, 1, 1, 0, 0, 0):
        return None
    return datetime(*stamp, tzinfo=UTC)

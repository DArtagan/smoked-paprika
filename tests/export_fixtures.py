"""Synthetic exports with the measured shape of a real one.

The design's *The export* section has the measurements. Every recipe here is
obviously fake, since tests never see a real export. Run as a script to write
one to a file:

    python tests/export_fixtures.py synthetic.paprikarecipes
"""

import base64
import gzip
import io
import json
import sys
import zipfile
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

EXPORTED_AT = datetime(2026, 1, 2, 3, 4, 6, tzinfo=UTC)

# A JPEG's start and end markers around filler: shaped like a photo, not one.
PHOTO = base64.b64encode(b"\xff\xd8\xff\xe0" + bytes(64) + b"\xff\xd9").decode()


def recipe(n: int, **fields: Any) -> dict[str, Any]:
    """Synthetic recipe `n`, with Paprika 4's 25 fields; `fields` override."""
    base: dict[str, Any] = {
        "uid": f"00000000-0000-4000-8000-{n:012d}",
        "name": f"Synthetic Dish {n}",
        "ingredients": f"1 unit ingredient {n}a\n2 units ingredient {n}b",
        "directions": f"Do the first thing to dish {n}.\n\nDo the second thing.",
        "description": f"A made-up dish, number {n}.",
        "notes": "",
        "nutritional_info": "",
        "servings": "2",
        "difficulty": "",
        "prep_time": "5 min",
        "cook_time": "10 min",
        "total_time": "15 min",
        "source": "fixture generator",
        "source_url": f"https://example.com/dish/{n}",
        "rating": n % 6,
        "categories": [f"Category {'ABC'[n % 3]}"],
        "created": "2026-01-01 12:00:00",
        "hash": f"{n:064x}",
        "image_url": None,
        "photo": None,
        "photo_hash": None,
        "photo_data": None,
        "photo_large": None,
        "photos": [],
        "cookbook_uid": None,
    }
    return base | fields


def entry_names(recipes: list[dict[str, Any]]) -> list[str]:
    # Paprika drops characters a filename cannot hold, trims the edges, and
    # numbers a repeated name from 2.
    names, seen = [], {}
    for r in recipes:
        stem = r["name"].replace(":", "").strip()
        seen[stem] = seen.get(stem, 0) + 1
        suffix = f" {seen[stem]}" if seen[stem] > 1 else ""
        names.append(f"{stem}{suffix}.paprikarecipe")
    return names


def gzipped(r: dict[str, Any]) -> bytes:
    return gzip.compress(json.dumps(r).encode())


def build(
    entries: Iterable[tuple[str, bytes]], exported_at: datetime = EXPORTED_AT
) -> bytes:
    """A zip of (entry name, entry bytes), stamped as Paprika 4 stamps it."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            info = zipfile.ZipInfo(name, exported_at.timetuple()[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return buffer.getvalue()


def export(recipes: Iterable[dict[str, Any]]) -> bytes:
    recipes = list(recipes)
    return build(zip(entry_names(recipes), map(gzipped, recipes), strict=True))


def variety() -> list[dict[str, Any]]:
    """One recipe for each convention the real export was found to use."""
    return [
        recipe(1),
        # The entry name differs from the recipe name.
        recipe(2, name="Synthetic Dish 2: Variant"),
        recipe(3, name=" Synthetic Dish 3 "),
        recipe(
            4,
            ingredients="Group one:\r\n1 unit a\r\n\r\nGroup two:\r\n1 unit b",
            directions="Crlf step one.\r\n\r\nCrlf step two.",
        ),
        recipe(5, directions=""),
        recipe(6, directions="Unnumbered line one\nUnnumbered line two\n"),
        recipe(
            7,
            directions="1. Numbered step one.\n2. Numbered step two,\n"
            "wrapped onto a second line.\n3. Numbered step three.",
        ),
        recipe(
            8,
            ingredients="For the base:\n1 unit c\n\nFor the top:\n1 unit d",
            categories=["Category A", "Category B"],
        ),
        recipe(
            9,
            photo="photo-9.jpg",
            photo_hash="9" * 64,
            photo_data=PHOTO,
            photos=[{"name": "photo-9b.jpg", "filename": "9b.jpg", "data": PHOTO}],
        ),
        # A field this reader has never seen, as Paprika 4 added some.
        recipe(10, a_future_field={"nested": [1, 2, 3]}, prep_minutes=None),
        recipe(11, directions="One single step."),
        recipe(12, categories=[], rating=0),
        # Names are not unique.
        recipe(13, name="Synthetic Dish 1"),
    ]


if __name__ == "__main__":
    with open(sys.argv[1], "wb") as out:
        out.write(export(variety()))

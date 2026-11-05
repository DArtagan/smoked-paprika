import gzip
import io
import json
import zipfile

import pytest
from export_fixtures import EXPORTED_AT, build, export, gzipped, recipe, variety

from smoked_paprika import export as reader
from smoked_paprika.export import ExportError, read_export, split_steps


def read(data: bytes):
    return read_export(io.BytesIO(data))


def rejected(data: bytes) -> ExportError:
    with pytest.raises(ExportError) as caught:
        read(data)
    return caught.value


def test_reads_every_recipe_keyed_by_uid():
    recipes = variety()
    collection = read(export(recipes))
    assert set(collection.recipes) == {r["uid"] for r in recipes}
    assert collection.recipes[recipes[0]["uid"]].name == "Synthetic Dish 1"


def test_export_time_comes_from_the_zip():
    assert read(export(variety())).exported_at == EXPORTED_AT


def test_no_export_time_when_the_zip_has_none():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(zipfile.ZipInfo("a.paprikarecipe"), gzipped(recipe(1)))
    assert read(buffer.getvalue()).exported_at is None


def test_entry_names_do_not_identify_recipes():
    recipes = [recipe(1), recipe(2, name="Synthetic Dish 1")]
    collection = read(export(recipes))
    assert [r.name for r in collection.recipes.values()] == ["Synthetic Dish 1"] * 2


def test_names_lose_edge_whitespace():
    r = recipe(3, name=" Synthetic Dish 3 ")
    assert read(export([r])).recipes[r["uid"]].name == "Synthetic Dish 3"


def test_crlf_becomes_lf():
    r = recipe(4, ingredients="a\r\n\r\nb", notes="c\rd", directions="e\r\n\r\nf")
    loaded = read(export([r])).recipes[r["uid"]]
    assert loaded.ingredients == "a\n\nb"
    assert loaded.notes == "c\nd"
    assert loaded.steps == ("e", "f")


def test_grouped_ingredients_keep_their_blank_lines():
    text = "For the base:\n1 unit c\n\nFor the top:\n1 unit d"
    r = recipe(8, ingredients=text)
    assert read(export([r])).recipes[r["uid"]].ingredients == text


def test_one_entry_export_reads_like_any_other():
    r = recipe(1)
    collection = read(export([r]))
    assert list(collection.recipes) == [r["uid"]]


def test_unknown_fields_are_tolerated():
    r = recipe(10, a_future_field={"nested": [1]}, metadata_version=1)
    assert r["uid"] in read(export([r])).recipes


def test_null_and_missing_optional_fields_are_empty():
    r = recipe(12, notes=None, rating=None, categories=None)
    del r["description"]
    loaded = read(export([r])).recipes[r["uid"]]
    assert (loaded.notes, loaded.description, loaded.rating, loaded.categories) == (
        "",
        "",
        0,
        (),
    )


def test_photos_are_not_kept():
    r = next(r for r in variety() if r["photo_data"])
    loaded = read(export([r])).recipes[r["uid"]]
    assert not any(
        r["photo_data"] in str(getattr(loaded, field)) for field in loaded.__slots__
    )


@pytest.mark.parametrize(
    ("directions", "steps"),
    [
        ("", ()),
        ("  \n ", ()),
        ("One single step.", ("One single step.",)),
        (
            "Step one.\n\nStep two.\n\n\nStep three.",
            ("Step one.", "Step two.", "Step three."),
        ),
        ("Para one\nwrapped.\n \nPara two.", ("Para one\nwrapped.", "Para two.")),
        ("Line one\nLine two\n", ("Line one", "Line two")),
        (
            "1. One.\n2. Two,\nwrapped.\n3. Three.",
            ("1. One.", "2. Two, wrapped.", "3. Three."),
        ),
        (
            "Combine in a mug:\nAdd one\nAdd two",
            ("Combine in a mug:", "Add one", "Add two"),
        ),
    ],
)
def test_directions_as_steps(directions, steps):
    assert split_steps(directions) == steps


def test_every_variety_reads():
    recipes = variety()
    collection = read(export(recipes))
    assert len(collection.recipes) == len(recipes)
    categories = {c for r in collection.recipes.values() for c in r.categories}
    assert categories == {"Category A", "Category B", "Category C"}


# Rejections: each names the entry at fault, and nothing is returned.


def entries_with(bad_name: str, bad: bytes) -> bytes:
    good = [recipe(1), recipe(2)]
    return build(
        [
            ("Synthetic Dish 1.paprikarecipe", gzipped(good[0])),
            (bad_name, bad),
            ("Synthetic Dish 2.paprikarecipe", gzipped(good[1])),
        ]
    )


@pytest.mark.parametrize(
    ("bad", "reason"),
    [
        (b"not gzip at all", "corrupt gzip"),
        (gzipped(recipe(9))[:-12], "truncated gzip"),
        (gzip.compress(b"{not json"), "invalid JSON"),
        (gzip.compress(b"\xff\xfe"), "invalid JSON"),
        (gzip.compress(b"[1, 2]"), "not a JSON object"),
        (gzipped({k: v for k, v in recipe(9).items() if k != "uid"}), "missing uid"),
        (gzipped(recipe(9, name="")), "missing name"),
        (gzipped(recipe(9, name=None)), "missing name"),
        (gzipped(recipe(9, notes=["a list"])), "notes is not a string"),
        (gzipped(recipe(9, categories="Category A")), "categories"),
        (gzipped(recipe(9, rating="5")), "rating"),
        (gzipped(recipe(1)), "duplicate uid"),
    ],
)
def test_a_bad_entry_rejects_the_file(bad, reason):
    error = rejected(entries_with("Bad Entry.paprikarecipe", bad))
    assert error.entry == "Bad Entry.paprikarecipe"
    assert reason in error.reason
    assert "Bad Entry.paprikarecipe" in str(error)


def test_an_entry_of_another_kind_rejects_the_file():
    error = rejected(entries_with("notes.txt", b"hello"))
    assert error.entry == "notes.txt"


def test_not_a_zip():
    assert "not a zip" in rejected(b"PK but not really").reason


def test_an_empty_zip():
    assert "no recipes" in rejected(build([])).reason


def test_a_corrupt_zip_entry():
    data = bytearray(export([recipe(1)]))
    # Flip a byte inside the deflated entry, after its local header.
    data[60] ^= 0xFF
    error = rejected(bytes(data))
    assert error.entry == "Synthetic Dish 1.paprikarecipe"


def test_too_many_entries(monkeypatch):
    monkeypatch.setattr(reader, "MAX_ENTRIES", 2)
    assert "more than 2 entries" in rejected(export(variety())).reason


def test_a_gzip_bomb_is_stopped_at_the_limit(monkeypatch):
    monkeypatch.setattr(reader, "MAX_ENTRY_BYTES", 1024 * 1024)
    bomb = gzip.compress(b'{"uid": "' + b"0" * (16 * 1024 * 1024) + b'"}')
    error = rejected(entries_with("Bomb.paprikarecipe", bomb))
    assert (error.entry, error.reason) == (
        "Bomb.paprikarecipe",
        "entry exceeds the size limit",
    )


def test_the_whole_export_is_capped(monkeypatch):
    each = len(gzip.decompress(gzipped(recipe(1))))
    monkeypatch.setattr(reader, "MAX_TOTAL_BYTES", each * 2 + each // 2)
    error = rejected(export([recipe(1), recipe(2), recipe(3)]))
    assert error.entry == "Synthetic Dish 3.paprikarecipe"


def test_concatenated_gzip_members_read_as_one():
    data = json.dumps(recipe(1)).encode()
    halves = gzip.compress(data[:20]) + gzip.compress(data[20:])
    collection = read(build([("Synthetic Dish 1.paprikarecipe", halves)]))
    assert recipe(1)["uid"] in collection.recipes

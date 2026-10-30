"""Nothing here contacts Paprika's servers; see the design's first section.

The host is assembled from parts so that this file does not name it. Markdown is
exempt, because the README and the design name the host to explain the rule.
"""

import subprocess
from pathlib import Path

HOST = b"paprikaapp" + b".com"
ROOT = Path(__file__).resolve().parent.parent


def tracked_files() -> list[Path]:
    listing = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.decode()
    return [ROOT / name for name in listing.split("\0") if name]


def test_no_tracked_file_names_the_host():
    files = tracked_files()
    # An empty listing would pass vacuously.
    assert Path(__file__).resolve() in files

    naming = [
        str(path.relative_to(ROOT))
        for path in files
        # A tracked file deleted from the working tree is not being committed.
        if path.suffix != ".md" and path.is_file()
        if HOST in path.read_bytes().lower()
    ]
    assert naming == []

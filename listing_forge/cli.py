"""CLI: python -m listing_forge.cli notes.txt -> prints JSON."""

import json
import sys
from pathlib import Path

from listing_forge.generator import generate_listing


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("Usage: python -m listing_forge.cli notes.txt",
              file=sys.stderr)
        return 2
    path = Path(args[0])
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    notes = path.read_text(encoding="utf-8")
    listing = generate_listing(notes)
    print(json.dumps(listing, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate historical NYC code parts from the public-domain Git source snapshots.

The input is the unmodified repository checkout. No legal words are supplied here:
each section body is copied from its source file with only whitespace normalized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


SOURCES = {
    "code": ("nycadmincode", "f8d836de12690fa60b1789c0d0a0ea30df25992b", "Administrative Code"),
    "charter": ("nyccharter", "71a6c8fc6f41b94f7e82adf4fcf709ea13092156", "Charter"),
}
DAY = "2017-04-22"


def section(path: Path) -> tuple[str, str]:
    source = path.read_text(encoding="utf-8")
    heading, marker, body = source.partition("::")
    if not marker or not heading.startswith("Section "):
        raise ValueError(f"unexpected source structure: {path}")
    label = heading.splitlines()[0].strip()
    lines = [re.sub(r"[ \t]+", " ", line.strip()) for line in body.splitlines()]
    text = "\n".join(line for line in lines if line) + "\n"
    if not text.strip() or text.split() != body.split():
        raise ValueError(f"source words differ: {path}")
    return label, text


def section_key(path: Path, root: Path, used: set[str], collisions: set[str]) -> str:
    name = path.stem[:-4].lower()
    key = "sec-" + re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    if key in collisions and "." in name:
        key = "sec-" + re.sub(r"[^a-z0-9]+", "-", name.replace(".", "-dot-")).strip("-")
    if key in used:
        relative = path.relative_to(root).as_posix()[:-8].lower().replace(".", "-dot-")
        key = "sec-" + re.sub(r"[^a-z0-9]+", "-", relative).strip("-")
    if key in used:
        raise ValueError(f"duplicate section key: {path}")
    return key


def part(kind: str, source_root: Path, group: str) -> dict:
    repo, commit, title = SOURCES[kind]
    root = source_root / "docs" / group
    files = sorted(root.rglob("*.rst.bak"))
    if not files:
        raise ValueError(f"no sections: {root}")
    base_keys = ["sec-" + re.sub(r"[^a-z0-9]+", "-", p.stem[:-4].lower()).strip("-") for p in files]
    collisions = {key for key, count in Counter(base_keys).items() if count > 1}
    units = {}
    for path in files:
        label, text = section(path)
        key = section_key(path, root, set(units), collisions)
        units[key] = {"label": label, "kind": "section", "text": text}
    slug = ("admin-code-title-" if kind == "code" else "charter-chapter-") + group.lower().replace("_", "-")
    url = f"https://github.com/devinbalkind/{repo}/commit/{commit}"
    return {
        "acts": [{
            "slug": slug, "short": f"NYC {title} {group}",
            "title": f"New York City {title}, {group} (historical 2017 snapshot)",
            "url": url, "first_law": None, "earlier_laws": [],
            "versions": [{
                "from": DAY, "source_url": url,
                "sha256": hashlib.sha256(b"".join(path.read_bytes() for path in files)).hexdigest(),
                "text_as_of": DAY, "in_force_unknown": True,
                "in_force_basis": "The copy gives no source-wide currency date; 2017-04-22 is its GitHub snapshot commit date, not a claim that every section took effect that day.",
                "source_images": 0, "images_omitted": [], "units": units,
            }],
        }],
        "sources": [{"name": f"Friends of Devin Balkind for Public Advocate {title} snapshot",
                     "url": url, "retrieved": DAY,
                     "licence": "CC0-style waiver in source repository footer"}],
        "decisions": [f"{title} {group}: historical text-as-of 2017-04-22 GitHub commit; source states no exact consolidation currency or latest included Local Law."],
        "ai_use": ["GPT-6 wrote extraction code and selected metadata; it did not write or correct legal wording."],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=SOURCES)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("group")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = part(args.kind, args.source_root, args.group)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n"
    temp = args.output.with_suffix(".json.tmp")
    temp.write_text(data, encoding="utf-8", newline="\n")
    temp.replace(args.output)
    digest = hashlib.sha256(data.encode("utf-8")).hexdigest()
    args.output.with_suffix(".PUBLISH.pending").write_text(
        f"sha256:{digest}\nreview requested: source words equal unchanged GitHub snapshot files; date is a labelled snapshot day.\n",
        encoding="utf-8", newline="\n",
    )
    print(f"{args.output.name}: {len(result['acts'][0]['versions'][0]['units'])} sections")


if __name__ == "__main__":
    main()

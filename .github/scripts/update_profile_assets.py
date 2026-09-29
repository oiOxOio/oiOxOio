"""Validate fresh generated assets before replacing the published cards."""

import hashlib
import os
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

SVG_TAG = "{http://www.w3.org/2000/svg}svg"
SOURCE = Path("profile-summary-card-output/github")
DESTINATION = Path("resource/profile-summary/github")
CARDS = {
    "0-profile-details.svg": (
        os.environ["PROFILE_USER"],
        "Contributions on GitHub",
        "Public Repos",
    ),
    "3-stats.svg": ("Stats", "Total Stars:", "Total Commits:", "Total PRs:", "Total Issues:", "Contributed to:"),
    "4-productive-time.svg": ("Commits (UTC +8.00)", "per day hour"),
}


def validate_svg(path, labels=()):
    raw = path.read_text(encoding="utf-8")
    root = ET.fromstring(raw)
    if root.tag != SVG_TAG:
        raise ValueError(f"{path}: expected an SVG document")
    if re.search(r"\b(?:NaN|Infinity|undefined)\b", raw):
        raise ValueError(f"{path}: invalid values in generated SVG")
    text = " ".join(" ".join(root.itertext()).split())
    for label in labels:
        if label.casefold() not in text.casefold():
            raise ValueError(f"{path}: missing expected label {label!r}")
    print(f"Validated {path}")


# The upstream Action clears SOURCE each run. Validate these fresh files, not
# older snapshots in resource/, because individual upstream card errors are caught.
for filename, labels in CARDS.items():
    validate_svg(SOURCE / filename, labels)
validate_svg(Path("resource/github-contribution-grid-snake.svg"))

coding = Path("resource/coding.gif").read_bytes()
blob_header = f"blob {len(coding)}\0".encode()
if hashlib.sha1(blob_header + coding).hexdigest() != "0dbb596aaf929a349043862e1f167cbedb53e819":
    raise ValueError("coding.gif does not match the pinned upstream animation")

# Publish only after every asset passes, retaining the last good set on failures.
DESTINATION.mkdir(parents=True, exist_ok=True)
for filename in CARDS:
    shutil.copyfile(SOURCE / filename, DESTINATION / filename)
print("All profile assets passed validation.")

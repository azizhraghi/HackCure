"""Turn the SurgWound question files (Hugging Face: Sonulee/SurgWound, CC BY-SA 4.0) into images + one label row per image.

    python scripts/prepare_surgwound.py <folder with train/val/test_question.json> <output folder>

Output: <out>/images/<split>/<image_name>, <out>/labels.csv (split, image, one column per attribute).
The images are surgical wounds collected from public online sources and annotated by surgeons at Ohio State
University Wexner Medical Center (SurgWound-Bench, arXiv 2508.15189).
"""

import base64
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

FIELDS = {"Wound Location": "location", "Healing Status": "healing", "Closure Method": "closure",
          "Exudate Type": "exudate", "Erythema": "erythema", "Edema": "edema",
          "Infection Risk Assessment": "infection_risk", "Urgency Level": "urgency"}


def main(src: Path, out: Path) -> None:
    rows = []
    for split in ("train", "val", "test"):
        data = json.loads((src / f"{split}_question.json").read_text(encoding="utf-8"))
        labels, images = defaultdict(dict), {}
        for item in data:
            name = item["image_name"]
            key = FIELDS.get(item["field"])
            if key:
                labels[name][key] = item["answer"]
            images.setdefault(name, item["image"])
        folder = out / "images" / split
        folder.mkdir(parents=True, exist_ok=True)
        for name, b64 in images.items():
            (folder / name).write_bytes(base64.b64decode(b64))
            rows.append({"split": split, "image": f"images/{split}/{name}", **{v: labels[name].get(v, "") for v in FIELDS.values()}})
        print(split, len(images), "images")
    with open(out / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["split", "image", *FIELDS.values()])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))

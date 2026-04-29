from pathlib import Path
from collections import Counter

paths = {
    "NORA_CURRENT": Path(r"C:\Users\CASPER\Desktop\drone_detection\training_data\nora_b52\labels"),
    "NORA_BACKUP_BEFORE_BBOX_CLIP": Path(r"C:\Users\CASPER\Desktop\drone_detection\training_data\nora_b52\labels_backup_before_bbox_clip_20260427_161441"),
    "ZUZANA_CURRENT": Path(r"C:\Users\CASPER\Desktop\drone_detection\training_data\zuzana\labels"),
    "WEAPON_DATASET": Path(r"C:\Users\CASPER\Desktop\drone_detection\training_data\weapon_dataset\labels"),
}

for name, root in paths.items():
    print("\n" + "=" * 80)
    print(name)
    print(root)

    if not root.exists():
        print("YOK")
        continue

    for split in ["train", "val", "test"]:
        split_dir = root / split
        labels = list(split_dir.glob("*.txt")) if split_dir.exists() else []

        dist = Counter()
        total_lines = 0
        invalid = []

        for txt in labels:
            for line_no, line in enumerate(txt.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) != 5:
                    invalid.append(f"{txt.name}:{line_no} kolon hatasi -> {line}")
                    continue

                try:
                    cls_id = int(float(parts[0]))
                    x, y, w, h = map(float, parts[1:])
                except Exception:
                    invalid.append(f"{txt.name}:{line_no} sayi hatasi -> {line}")
                    continue

                if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
                    invalid.append(f"{txt.name}:{line_no} bbox hatasi -> {line}")

                dist[str(cls_id)] += 1
                total_lines += 1

        print(f"[{split}] label_file={len(labels)} total_box={total_lines} class_dist={dict(dist)} invalid={len(invalid)}")

        if invalid:
            print("Ilk hatalar:")
            for item in invalid[:10]:
                print("  ", item)

from pathlib import Path
from collections import Counter

root = Path(r"C:\Users\CASPER\Desktop\drone_detection\training_data")
categories = ["nora_b52", "zuzana", "background"]

image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

for category in categories:
    print("\n" + "=" * 70)
    print("KATEGORI:", category)

    cat_root = root / category

    for split in ["train", "val", "test"]:
        img_dir = cat_root / "images" / split
        lbl_dir = cat_root / "labels" / split

        images = [p for p in img_dir.iterdir() if p.is_file() and p.suffix.lower() in image_exts] if img_dir.exists() else []
        labels = list(lbl_dir.glob("*.txt")) if lbl_dir.exists() else []

        image_stems = {p.stem for p in images}
        label_stems = {p.stem for p in labels}

        missing_labels = sorted(image_stems - label_stems)
        orphan_labels = sorted(label_stems - image_stems)

        class_dist = Counter()
        invalid = []

        for txt in labels:
            lines = txt.read_text(encoding="utf-8", errors="ignore").splitlines()

            for line_no, line in enumerate(lines, start=1):
                line = line.strip()

                # Bos label dosyasi background icin normaldir
                if not line:
                    continue

                parts = line.split()

                if len(parts) != 5:
                    invalid.append(f"{txt.name}:{line_no} -> kolon sayisi hatali: {line}")
                    continue

                try:
                    cls_id = int(float(parts[0]))
                    x, y, w, h = map(float, parts[1:])
                except Exception:
                    invalid.append(f"{txt.name}:{line_no} -> sayisal deger hatali: {line}")
                    continue

                if cls_id < 0 or cls_id > 11:
                    invalid.append(f"{txt.name}:{line_no} -> class id hatali: {cls_id}")

                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
                    invalid.append(
                        f"{txt.name}:{line_no} -> bbox hatali: "
                        f"{cls_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}"
                    )

                class_dist[str(cls_id)] += 1

        print(f"[{split}]")
        print(f"  images        : {len(images)}")
        print(f"  labels        : {len(labels)}")
        print(f"  class_dist    : {dict(class_dist)}")
        print(f"  missing_label : {len(missing_labels)}")
        print(f"  orphan_label  : {len(orphan_labels)}")
        print(f"  invalid       : {len(invalid)}")

        if missing_labels:
            print("  Eksik label ornekleri:", missing_labels[:10])

        if orphan_labels:
            print("  Resimsiz label ornekleri:", orphan_labels[:10])

        if invalid:
            print("  Ilk hatalar:")
            for item in invalid[:15]:
                print("   ", item)

# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
from collections import defaultdict

# ==============================
# AYARLAR
# ==============================

CATEGORY_DIR = Path(r"C:\Users\CASPER\Desktop\drone_detection\training_data\nora_b52")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
CREATE_MISSING_EMPTY_LABELS = False   # True yaparsan eksik image'ler için boş txt oluşturur
REMOVE_ORPHAN_LABELS = False          # True yaparsan karşılığı olmayan txt'leri siler
BACKUP_SUFFIX = ".bak"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def yolo_to_xyxy(x: float, y: float, w: float, h: float) -> Tuple[float, float, float, float]:
    x1 = x - w / 2.0
    y1 = y - h / 2.0
    x2 = x + w / 2.0
    y2 = y + h / 2.0
    return x1, y1, x2, y2


def xyxy_to_yolo(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float, float, float]:
    x = (x1 + x2) / 2.0
    y = (y1 + y2) / 2.0
    w = x2 - x1
    h = y2 - y1
    return x, y, w, h


def fix_label_line(line: str) -> Tuple[str | None, str | None]:
    """
    Dönüş:
      (duzeltilmis_satir, durum)
      durum:
        - None: satır aynen kaldı
        - "fixed": satır düzeltildi
        - "removed": satır silindi
        - "invalid": format bozuk
    """
    raw = line.strip()
    if not raw:
        return None, None

    parts = raw.split()
    if len(parts) != 5:
        return None, "invalid"

    try:
        cls_raw = parts[0]
        cls_id = int(float(cls_raw))
        x = float(parts[1])
        y = float(parts[2])
        w = float(parts[3])
        h = float(parts[4])
    except ValueError:
        return None, "invalid"

    # İlk kaba kontrol
    if w <= 0 or h <= 0:
        return None, "removed"

    # xywh -> xyxy
    x1, y1, x2, y2 = yolo_to_xyxy(x, y, w, h)

    # sınır içine kırp
    nx1 = clamp(x1, 0.0, 1.0)
    ny1 = clamp(y1, 0.0, 1.0)
    nx2 = clamp(x2, 0.0, 1.0)
    ny2 = clamp(y2, 0.0, 1.0)

    # kutu tamamen bozulduysa at
    if nx2 <= nx1 or ny2 <= ny1:
        return None, "removed"

    new_x, new_y, new_w, new_h = xyxy_to_yolo(nx1, ny1, nx2, ny2)

    fixed = (
        abs(new_x - x) > 1e-9 or
        abs(new_y - y) > 1e-9 or
        abs(new_w - w) > 1e-9 or
        abs(new_h - h) > 1e-9
    )

    new_line = f"{cls_id} {new_x:.6f} {new_y:.6f} {new_w:.6f} {new_h:.6f}"
    return new_line, "fixed" if fixed else None


def backup_once(txt_path: Path) -> None:
    backup_path = txt_path.with_suffix(txt_path.suffix + BACKUP_SUFFIX)
    if not backup_path.exists():
        backup_path.write_bytes(txt_path.read_bytes())


def scan_images(image_dir: Path) -> List[Path]:
    files: List[Path] = []
    if not image_dir.exists():
        return files
    for p in image_dir.iterdir():
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            files.append(p)
    return sorted(files)


def scan_labels(label_dir: Path) -> List[Path]:
    if not label_dir.exists():
        return []
    return sorted(label_dir.glob("*.txt"))


def fix_one_label_file(txt_path: Path) -> dict:
    result = {
        "file": txt_path.name,
        "changed": False,
        "fixed_lines": 0,
        "removed_lines": 0,
        "invalid_lines": 0,
    }

    original_lines = txt_path.read_text(encoding="utf-8").splitlines()
    new_lines: List[str] = []

    for line in original_lines:
        fixed_line, status = fix_label_line(line)

        if fixed_line is not None:
            new_lines.append(fixed_line)

        if status == "fixed":
            result["changed"] = True
            result["fixed_lines"] += 1
        elif status == "removed":
            result["changed"] = True
            result["removed_lines"] += 1
        elif status == "invalid":
            result["changed"] = True
            result["invalid_lines"] += 1

    if result["changed"]:
        backup_once(txt_path)
        txt_path.write_text(
            ("\n".join(new_lines) + "\n") if new_lines else "",
            encoding="utf-8"
        )

    return result


def ensure_missing_empty_labels(image_dir: Path, label_dir: Path) -> int:
    image_stems = {p.stem for p in scan_images(image_dir)}
    label_stems = {p.stem for p in scan_labels(label_dir)}
    missing = sorted(image_stems - label_stems)

    created = 0
    for stem in missing:
        (label_dir / f"{stem}.txt").write_text("", encoding="utf-8")
        created += 1

    return created


def remove_orphan_labels(image_dir: Path, label_dir: Path) -> int:
    image_stems = {p.stem for p in scan_images(image_dir)}
    labels = scan_labels(label_dir)

    removed = 0
    for txt in labels:
        if txt.stem not in image_stems:
            backup_once(txt)
            txt.unlink(missing_ok=True)
            removed += 1

    return removed


def main() -> None:
    if not CATEGORY_DIR.exists():
        print(f"HATA: Kategori klasörü bulunamadı: {CATEGORY_DIR}")
        return

    total_changed_files = 0
    total_fixed_lines = 0
    total_removed_lines = 0
    total_invalid_lines = 0
    total_created_empty = 0
    total_removed_orphans = 0

    split_stats = defaultdict(dict)

    for split in ["train", "val", "test"]:
        image_dir = CATEGORY_DIR / "images" / split
        label_dir = CATEGORY_DIR / "labels" / split
        label_dir.mkdir(parents=True, exist_ok=True)

        images = scan_images(image_dir)
        labels = scan_labels(label_dir)

        split_stats[split]["images_before"] = len(images)
        split_stats[split]["labels_before"] = len(labels)

        if CREATE_MISSING_EMPTY_LABELS:
            created = ensure_missing_empty_labels(image_dir, label_dir)
            total_created_empty += created
            split_stats[split]["created_empty"] = created
        else:
            split_stats[split]["created_empty"] = 0

        if REMOVE_ORPHAN_LABELS:
            removed_orphans = remove_orphan_labels(image_dir, label_dir)
            total_removed_orphans += removed_orphans
            split_stats[split]["removed_orphans"] = removed_orphans
        else:
            split_stats[split]["removed_orphans"] = 0

        labels = scan_labels(label_dir)

        changed_here = 0
        fixed_here = 0
        removed_here = 0
        invalid_here = 0

        for txt_path in labels:
            result = fix_one_label_file(txt_path)

            if result["changed"]:
                changed_here += 1
                total_changed_files += 1

            fixed_here += result["fixed_lines"]
            removed_here += result["removed_lines"]
            invalid_here += result["invalid_lines"]

        total_fixed_lines += fixed_here
        total_removed_lines += removed_here
        total_invalid_lines += invalid_here

        split_stats[split]["changed_files"] = changed_here
        split_stats[split]["fixed_lines"] = fixed_here
        split_stats[split]["removed_lines"] = removed_here
        split_stats[split]["invalid_lines"] = invalid_here
        split_stats[split]["labels_after"] = len(scan_labels(label_dir))

    print("\n===== DÜZELTME ÖZETİ =====")
    print(f"Kategori: {CATEGORY_DIR.name}")
    print(f"Değişen dosya sayısı : {total_changed_files}")
    print(f"Düzeltilen satır     : {total_fixed_lines}")
    print(f"Silinen satır        : {total_removed_lines}")
    print(f"Geçersiz satır       : {total_invalid_lines}")
    print(f"Oluşan boş label     : {total_created_empty}")
    print(f"Silinen orphan label : {total_removed_orphans}")

    for split in ["train", "val", "test"]:
        s = split_stats[split]
        print(f"\n[{split}]")
        print(f"images_before  : {s.get('images_before', 0)}")
        print(f"labels_before  : {s.get('labels_before', 0)}")
        print(f"changed_files  : {s.get('changed_files', 0)}")
        print(f"fixed_lines    : {s.get('fixed_lines', 0)}")
        print(f"removed_lines  : {s.get('removed_lines', 0)}")
        print(f"invalid_lines  : {s.get('invalid_lines', 0)}")
        print(f"created_empty  : {s.get('created_empty', 0)}")
        print(f"removed_orphans: {s.get('removed_orphans', 0)}")
        print(f"labels_after   : {s.get('labels_after', 0)}")

    print("\nBitti.")


if __name__ == "__main__":
    main()
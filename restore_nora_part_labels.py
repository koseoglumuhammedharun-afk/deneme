from pathlib import Path
from datetime import datetime
import shutil
from collections import Counter

PROJECT_ROOT = Path(r"C:\Users\CASPER\Desktop\drone_detection")

current = PROJECT_ROOT / "training_data" / "nora_b52" / "labels"
source_backup = PROJECT_ROOT / "training_data" / "nora_b52" / "labels_backup_before_bbox_clip_20260427_161441"

if not current.exists():
    raise FileNotFoundError(f"Mevcut label klasoru bulunamadi: {current}")

if not source_backup.exists():
    raise FileNotFoundError(f"Yedek label klasoru bulunamadi: {source_backup}")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
safe_backup = current.parent / f"labels_vehicle_backup_before_restore_parts_{timestamp}"

shutil.copytree(current, safe_backup)

# Mevcut labels klasorunu temizle
shutil.rmtree(current)
shutil.copytree(source_backup, current)

fixed_files = 0
fixed_lines = 0
total_lines = 0
class_dist = Counter()

for txt in current.rglob("*.txt"):
    lines = txt.read_text(encoding="utf-8", errors="ignore").splitlines()
    new_lines = []
    file_changed = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        parts = stripped.split()
        if len(parts) != 5:
            continue

        try:
            cls_id = int(float(parts[0]))
            x, y, w, h = map(float, parts[1:])
        except Exception:
            continue

        old_values = (x, y, w, h)

        # YOLO bbox degerlerini guvenli sinira al
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        w = max(0.000001, min(1.0, w))
        h = max(0.000001, min(1.0, h))

        # x merkez ve genislik birlikte siniri asmasin
        if x - w / 2 < 0:
            w = min(w, 2 * x)
        if x + w / 2 > 1:
            w = min(w, 2 * (1 - x))

        # y merkez ve yukseklik birlikte siniri asmasin
        if y - h / 2 < 0:
            h = min(h, 2 * y)
        if y + h / 2 > 1:
            h = min(h, 2 * (1 - y))

        w = max(0.000001, min(1.0, w))
        h = max(0.000001, min(1.0, h))

        new_values = (x, y, w, h)

        if new_values != old_values:
            file_changed = True
            fixed_lines += 1

        class_dist[str(cls_id)] += 1
        total_lines += 1

        new_lines.append(f"{cls_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")

    txt.write_text("\n".join(new_lines), encoding="utf-8")

    if file_changed:
        fixed_files += 1

# Cache temizle
for cache_file in (PROJECT_ROOT / "training_data").rglob("*.cache"):
    cache_file.unlink(missing_ok=True)

print("NORA PARCA LABEL GERI YUKLENDI")
print("Onceki arac-odakli label yedegi:", safe_backup)
print("Kaynak parca label yedegi:", source_backup)
print("Duzeltilen dosya:", fixed_files)
print("Duzeltilen satir:", fixed_lines)
print("Toplam label satiri:", total_lines)
print("Class dagilimi:", dict(class_dist))
print("Cache temizlendi.")

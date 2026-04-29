from pathlib import Path
from datetime import datetime
import shutil

root = Path(r"C:\Users\CASPER\Desktop\drone_detection\training_data\nora_b52\labels")

if not root.exists():
    raise FileNotFoundError(f"Klasor bulunamadi: {root}")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = root.parent / f"labels_backup_before_bbox_clip_{timestamp}"
shutil.copytree(root, backup)

changed_files = 0
changed_lines = 0
skipped_lines = 0
total_lines = 0

def clamp(value, min_value=0.0, max_value=1.0):
    return max(min_value, min(max_value, value))

for txt in root.rglob("*.txt"):
    if "backup" in str(txt).lower():
        continue

    old_text = txt.read_text(encoding="utf-8").splitlines()
    new_lines = []
    file_changed = False

    for line in old_text:
        stripped = line.strip()

        if not stripped:
            continue

        parts = stripped.split()

        if len(parts) != 5:
            skipped_lines += 1
            new_lines.append(line)
            continue

        try:
            cls_id = int(float(parts[0]))
            x = float(parts[1])
            y = float(parts[2])
            w = float(parts[3])
            h = float(parts[4])
        except ValueError:
            skipped_lines += 1
            new_lines.append(line)
            continue

        total_lines += 1

        old_values = (x, y, w, h)

        x1 = x - (w / 2.0)
        y1 = y - (h / 2.0)
        x2 = x + (w / 2.0)
        y2 = y + (h / 2.0)

        x1 = clamp(x1)
        y1 = clamp(y1)
        x2 = clamp(x2)
        y2 = clamp(y2)

        new_w = x2 - x1
        new_h = y2 - y1

        if new_w <= 0 or new_h <= 0:
            skipped_lines += 1
            file_changed = True
            continue

        new_x = x1 + (new_w / 2.0)
        new_y = y1 + (new_h / 2.0)

        new_values = (new_x, new_y, new_w, new_h)

        if any(abs(a - b) > 1e-9 for a, b in zip(old_values, new_values)):
            changed_lines += 1
            file_changed = True

        new_lines.append(
            f"{cls_id} {new_x:.6f} {new_y:.6f} {new_w:.6f} {new_h:.6f}"
        )

    txt.write_text("\n".join(new_lines), encoding="utf-8")

    if file_changed:
        changed_files += 1

# Cache dosyalarini sil
for base in [
    Path(r"C:\Users\CASPER\Desktop\drone_detection\training_data\nora_b52"),
    Path(r"C:\Users\CASPER\Desktop\drone_detection\training_data\weapon_dataset"),
]:
    if base.exists():
        for cache_file in base.rglob("*.cache"):
            cache_file.unlink(missing_ok=True)

print("YEDEK ALINDI:", backup)
print("Toplam okunan label satiri:", total_lines)
print("Duzeltilen dosya:", changed_files)
print("Duzeltilen satir:", changed_lines)
print("Atlanan/gecersiz satir:", skipped_lines)
print("Cache dosyalari temizlendi.")

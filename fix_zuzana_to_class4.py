from pathlib import Path
from datetime import datetime
import shutil
from collections import Counter

root = Path(r"C:\Users\CASPER\Desktop\drone_detection\training_data\zuzana\labels")

if not root.exists():
    raise FileNotFoundError(f"Klasor bulunamadi: {root}")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = root.parent / f"labels_backup_before_force_zuzana_govde_{timestamp}"

shutil.copytree(root, backup)

changed_files = 0
changed_lines = 0
before = Counter()
after = Counter()

for txt in root.rglob("*.txt"):
    if "backup" in str(txt).lower():
        continue

    lines = txt.read_text(encoding="utf-8").splitlines()
    new_lines = []
    file_changed = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        parts = stripped.split()
        if len(parts) < 5:
            new_lines.append(line)
            continue

        before[parts[0]] += 1

        # Zuzana govde class id = 4
        if parts[0] != "4":
            parts[0] = "4"
            file_changed = True
            changed_lines += 1

        after[parts[0]] += 1
        new_lines.append(" ".join(parts))

    txt.write_text("\n".join(new_lines), encoding="utf-8")

    if file_changed:
        changed_files += 1

# Cache dosyalarini sil
for cache_file in root.rglob("*.cache"):
    cache_file.unlink(missing_ok=True)

print("YEDEK ALINDI:", backup)
print("Degisen dosya:", changed_files)
print("Degisen satir:", changed_lines)
print("Onceki sinif dagilimi:", dict(before))
print("Yeni sinif dagilimi:", dict(after))

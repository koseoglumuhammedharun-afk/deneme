from pathlib import Path
from datetime import datetime
import shutil
import random
import re

import fiftyone as fo
import fiftyone.zoo as foz


PROJECT_ROOT = Path(r"C:\Users\CASPER\Desktop\drone_detection")
BACKGROUND_ROOT = PROJECT_ROOT / "training_data" / "background"

COCO_CLASSES = [
    "person",
    "car",
    "truck",
    "bus",
    "traffic light",
    "stop sign",
    "bench",
]

SAMPLES_PER_CLASS = 35
TRAIN_RATIO = 0.80
RANDOM_SEED = 42
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "class"


def ensure_dirs():
    for split in ["train", "val", "test"]:
        (BACKGROUND_ROOT / "images" / split).mkdir(parents=True, exist_ok=True)
        (BACKGROUND_ROOT / "labels" / split).mkdir(parents=True, exist_ok=True)


def copy_background_images(filepaths):
    random.seed(RANDOM_SEED)
    filepaths = sorted(set(Path(p) for p in filepaths if Path(p).exists()))
    random.shuffle(filepaths)

    train_count = int(len(filepaths) * TRAIN_RATIO)
    train_files = filepaths[:train_count]
    val_files = filepaths[train_count:]

    copied = {"train": 0, "val": 0}

    for split, files in [("train", train_files), ("val", val_files)]:
        image_dir = BACKGROUND_ROOT / "images" / split
        label_dir = BACKGROUND_ROOT / "labels" / split

        for index, src in enumerate(files, start=1):
            if src.suffix.lower() not in IMAGE_EXTS:
                continue

            dst_name = f"background_{split}_{index:05d}{src.suffix.lower()}"
            dst_image = image_dir / dst_name
            dst_label = label_dir / f"background_{split}_{index:05d}.txt"

            shutil.copy2(src, dst_image)

            # Background görsellerde hedef obje yok.
            # Bu yüzden YOLO label dosyası boş olmalı.
            dst_label.write_text("", encoding="utf-8")

            copied[split] += 1

    return copied


def clean_cache():
    for base in [
        BACKGROUND_ROOT,
        PROJECT_ROOT / "training_data" / "weapon_dataset",
    ]:
        if base.exists():
            for cache_file in base.rglob("*.cache"):
                cache_file.unlink(missing_ok=True)


def main():
    ensure_dirs()

    all_filepaths = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("COCO 2017 negatif/background gorselleri indiriliyor...")
    print("Siniflar:", COCO_CLASSES)
    print("Her siniftan hedef ornek:", SAMPLES_PER_CLASS)
    print()

    for class_name in COCO_CLASSES:
        dataset_name = f"tmp_background_{slugify(class_name)}_{timestamp}"

        print(f"Indiriliyor: {class_name}")

        dataset = foz.load_zoo_dataset(
            "coco-2017",
            split="validation",
            label_types=["detections"],
            classes=[class_name],
            max_samples=SAMPLES_PER_CLASS,
            shuffle=True,
            dataset_name=dataset_name,
        )

        before = len(all_filepaths)

        for sample in dataset:
            all_filepaths.append(sample.filepath)

        print(f"  Alinan gorsel: {len(all_filepaths) - before}")

        try:
            fo.delete_dataset(dataset_name)
        except Exception:
            pass

    copied = copy_background_images(all_filepaths)
    clean_cache()

    print()
    print("BACKGROUND VERI SETI HAZIR")
    print("Klasor:", BACKGROUND_ROOT)
    print("Toplam kaynak gorsel:", len(set(all_filepaths)))
    print("Train kopyalanan:", copied["train"])
    print("Val kopyalanan:", copied["val"])
    print("Label dosyalari bos olusturuldu.")
    print("Cache dosyalari temizlendi.")
    print()
    print("Sonraki adim:")
    print("Uygulamada kaynak kategoriler olarak nora_b52 + zuzana + background secip Birlesik Final Modeli Egit.")


if __name__ == "__main__":
    main()

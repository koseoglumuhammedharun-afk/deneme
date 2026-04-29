# -*- coding: utf-8 -*-
"""
Model Egitim Modulu - YOLO v8 Custom Model Egitimi

Bu modul iki egitim seklini destekler:

1. Kategori bazli egitim:
   training_data/zuzana
   training_data/nora_b52
   training_data/obus

2. Birlesik final model egitimi:
   training_data/weapon_dataset

Birlesik model mantigi:
- Nora B-52, Zuzana ve Obus verileri tek dataset altinda toplanir.
- Tek YOLO modeli egitilir.
- Final model models/howitzer_detector.pt olarak kaydedilir.
"""

import logging
import shutil
from collections import Counter
from pathlib import Path
from typing import Dict, Optional, Callable, List, Tuple

import cv2
import yaml

try:
    from ultralytics import YOLO
except (ImportError, OSError):
    YOLO = None
    logging.warning("YOLOv8 yuklenemedi - model egitimi devre disi")

import config

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    YOLO v8 modeli egitmek icin trainer sinifi
    """

    COMBINED_DATASET_NAME = "weapon_dataset"
    SPLITS = ["train", "val", "test"]

    def __init__(self, base_model: str = "yolov8n.pt"):
        self.base_model = base_model
        self.model = None
        self.training_dir = Path(
            getattr(config, "TRAINING_DATA_DIR", Path(config.PROJECT_ROOT) / "training_data")
        )
        self.dataset_yaml: Optional[str] = None
        self._setup_training_dirs()

    # =========================================================
    # TEMEL KLASOR / SINIF YARDIMCILARI
    # =========================================================

    def _setup_training_dirs(self):
        """Egitim icin gerekli ana dizinleri olustur"""
        try:
            self.training_dir.mkdir(parents=True, exist_ok=True)
            (self.training_dir / "models").mkdir(parents=True, exist_ok=True)
            logger.info(f"Egitim dizinleri hazir: {self.training_dir}")
        except Exception as e:
            logger.error(f"Dizin olusturma hatasi: {e}")
            raise

    def _ensure_category_dirs(self, category: str) -> Path:
        """Kategoriye ait klasor yapisini garanti et"""
        category_dir = self.training_dir / category

        for split in self.SPLITS:
            (category_dir / "images" / split).mkdir(parents=True, exist_ok=True)
            (category_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

        return category_dir

    def _get_class_names(self, class_names: Optional[List[str]] = None) -> List[str]:
        """Sinif isimlerini config veya parametreden al"""
        if class_names:
            return list(class_names)

        return list(getattr(config, "CLASS_NAMES", ["obus"]))

    def _is_image_file(self, path: Path) -> bool:
        supported = getattr(
            config,
            "SUPPORTED_IMAGE_FORMATS",
            (".jpg", ".jpeg", ".png", ".bmp", ".tiff"),
        )
        return path.is_file() and path.suffix.lower() in supported

    def _safe_name(self, text: str) -> str:
        """Dosya adi icin guvenli metin uret"""
        allowed = []
        for ch in str(text):
            if ch.isalnum() or ch in ("_", "-", "."):
                allowed.append(ch)
            else:
                allowed.append("_")
        return "".join(allowed).strip("_") or "item"

    def _get_available_source_categories(self, exclude_combined: bool = True) -> List[str]:
        """
        training_data altindaki egitim kategorilerini getir.

        Hariç tutulanlar:
        - models
        - gizli klasorler
        - backup klasorleri
        - weapon_dataset, exclude_combined=True ise
        """
        if not self.training_dir.exists():
            return []

        categories = []

        for item in sorted(self.training_dir.iterdir()):
            if not item.is_dir():
                continue

            name = item.name

            if name.startswith("."):
                continue

            if name.lower() == "models":
                continue

            if "backup" in name.lower():
                continue

            if exclude_combined and name == self.COMBINED_DATASET_NAME:
                continue

            images_dir = item / "images"
            labels_dir = item / "labels"

            if images_dir.exists() and labels_dir.exists():
                categories.append(name)

        return categories

    def _remove_dataset_cache(self, category: str):
        """
        YOLO cache dosyalarini sil.

        Label dosyalari degistiginde eski .cache dosyasi yanlis siniflari okutabilir.
        Bu yuzden egitimden once temizlemek guvenlidir.
        """
        category_dir = self.training_dir / category
        removed = 0

        if not category_dir.exists():
            return 0

        for cache_file in category_dir.rglob("*.cache"):
            try:
                cache_file.unlink()
                removed += 1
            except Exception as e:
                logger.warning(f"Cache silinemedi: {cache_file} ({e})")

        if removed:
            logger.info(f"{category} icin {removed} cache dosyasi silindi")

        return removed

    # =========================================================
    # DATASET ANALIZ / DOGURLAMA
    # =========================================================

    def get_label_distribution(
        self,
        category: str = "default",
        class_names: Optional[List[str]] = None,
    ) -> Dict:
        """
        Bir kategorideki label sinif dagilimini getir.
        """
        class_names = self._get_class_names(class_names)
        category_dir = self._ensure_category_dirs(category)

        split_stats = {}
        total_counter = Counter()
        invalid_lines = 0
        total_files = 0
        total_lines = 0

        for split in self.SPLITS:
            label_dir = category_dir / "labels" / split
            counter = Counter()
            split_invalid = 0
            split_files = 0
            split_lines = 0

            if label_dir.exists():
                for label_path in sorted(label_dir.glob("*.txt")):
                    split_files += 1
                    total_files += 1

                    try:
                        lines = label_path.read_text(encoding="utf-8").splitlines()
                    except Exception:
                        split_invalid += 1
                        invalid_lines += 1
                        continue

                    for line in lines:
                        stripped = line.strip()
                        if not stripped:
                            continue

                        parts = stripped.split()
                        if len(parts) < 5:
                            split_invalid += 1
                            invalid_lines += 1
                            continue

                        try:
                            cls_id = int(float(parts[0]))
                        except ValueError:
                            split_invalid += 1
                            invalid_lines += 1
                            continue

                        counter[cls_id] += 1
                        total_counter[cls_id] += 1
                        split_lines += 1
                        total_lines += 1

            split_stats[split] = {
                "files": split_files,
                "lines": split_lines,
                "invalid_lines": split_invalid,
                "class_counts": dict(sorted(counter.items())),
            }

        named_distribution = {}

        for cls_id, count in sorted(total_counter.items()):
            if 0 <= cls_id < len(class_names):
                class_name = class_names[cls_id]
            else:
                class_name = f"unknown_{cls_id}"

            named_distribution[cls_id] = {
                "class_name": class_name,
                "count": count,
            }

        return {
            "category": category,
            "num_classes": len(class_names),
            "class_names": class_names,
            "total_files": total_files,
            "total_lines": total_lines,
            "invalid_lines": invalid_lines,
            "class_counts": dict(sorted(total_counter.items())),
            "named_distribution": named_distribution,
            "split_stats": split_stats,
        }

    def validate_dataset(
        self,
        category: str = "default",
        class_names: Optional[List[str]] = None,
    ) -> Dict:
        """
        Veri setini egitimden once dogrula.

        Label satirlari:
            class x_center y_center width height

        Tum koordinatlar 0-1 araliginda olmali.
        """
        try:
            class_names = self._get_class_names(class_names)
            num_classes = len(class_names)
            category_dir = self._ensure_category_dirs(category)

            errors: List[str] = []
            stats: Dict[str, Dict[str, int]] = {}

            for split in self.SPLITS:
                image_dir = category_dir / "images" / split
                label_dir = category_dir / "labels" / split

                images = (
                    [p for p in image_dir.iterdir() if self._is_image_file(p)]
                    if image_dir.exists()
                    else []
                )
                labels = list(label_dir.glob("*.txt")) if label_dir.exists() else []

                image_stems = {p.stem for p in images}
                label_stems = {p.stem for p in labels}

                missing_labels = sorted(image_stems - label_stems)
                orphan_labels = sorted(label_stems - image_stems)

                if missing_labels:
                    errors.append(
                        f"{split}: {len(missing_labels)} resmin label dosyasi yok. "
                        f"Ornek: {missing_labels[:3]}"
                    )

                if orphan_labels:
                    errors.append(
                        f"{split}: {len(orphan_labels)} label dosyasinin karsilik gelen resmi yok. "
                        f"Ornek: {orphan_labels[:3]}"
                    )

                invalid_label_lines = 0

                for label_path in labels:
                    try:
                        with open(label_path, "r", encoding="utf-8") as f:
                            lines = [line.strip() for line in f if line.strip()]
                    except Exception as e:
                        errors.append(f"{label_path.name}: okunamadi ({e})")
                        continue

                    for line_no, line in enumerate(lines, start=1):
                        parts = line.split()

                        if len(parts) != 5:
                            invalid_label_lines += 1
                            errors.append(
                                f"{label_path.name}:{line_no} -> 5 kolon olmali, bulunan: {len(parts)}"
                            )
                            continue

                        try:
                            cls_id = int(float(parts[0]))
                            x = float(parts[1])
                            y = float(parts[2])
                            w = float(parts[3])
                            h = float(parts[4])
                        except ValueError:
                            invalid_label_lines += 1
                            errors.append(f"{label_path.name}:{line_no} -> sayisal deger okunamadi")
                            continue

                        if cls_id < 0 or cls_id >= num_classes:
                            invalid_label_lines += 1
                            errors.append(
                                f"{label_path.name}:{line_no} -> class {cls_id} gecersiz. "
                                f"Gecerli aralik: 0-{num_classes - 1}"
                            )

                        if not (
                            0.0 <= x <= 1.0
                            and 0.0 <= y <= 1.0
                            and 0.0 < w <= 1.0
                            and 0.0 < h <= 1.0
                        ):
                            invalid_label_lines += 1
                            errors.append(
                                f"{label_path.name}:{line_no} -> bbox degerleri gecersiz: "
                                f"{x:.6f}, {y:.6f}, {w:.6f}, {h:.6f}"
                            )

                stats[split] = {
                    "images": len(images),
                    "labels": len(labels),
                    "invalid_label_lines": invalid_label_lines,
                }

            # Kritik minimum veri kontrolu
            if stats.get("train", {}).get("images", 0) == 0:
                errors.append("train split icinde hic resim yok.")
            if stats.get("train", {}).get("labels", 0) == 0:
                errors.append("train split icinde hic label yok.")
            if stats.get("val", {}).get("images", 0) == 0:
                errors.append("val split icinde hic resim yok.")
            if stats.get("val", {}).get("labels", 0) == 0:
                errors.append("val split icinde hic label yok.")

            distribution = self.get_label_distribution(category=category, class_names=class_names)

            return {
                "ok": len(errors) == 0,
                "errors": errors,
                "stats": stats,
                "distribution": distribution,
            }

        except Exception as e:
            logger.error(f"Dataset dogrulama hatasi: {e}")
            return {
                "ok": False,
                "errors": [str(e)],
                "stats": {},
                "distribution": {},
            }

    # =========================================================
    # BIRLESIK DATASET HAZIRLAMA
    # =========================================================

    def prepare_combined_dataset(
        self,
        source_categories: Optional[List[str]] = None,
        target_category: str = COMBINED_DATASET_NAME,
        overwrite: bool = True,
        class_names: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict:
        """
        Mevcut kategori klasorlerinden tek bir birlesik dataset hazirlar.

        Kaynak:
            training_data/nora_b52
            training_data/zuzana
            training_data/obus

        Hedef:
            training_data/weapon_dataset

        Dosya isimleri cakismasin diye basina kategori eklenir:
            zuzana__Untitled-1.jpg
            zuzana__Untitled-1.txt
        """
        try:
            class_names = self._get_class_names(class_names)

            if source_categories is None:
                source_categories = self._get_available_source_categories(exclude_combined=True)

            source_categories = [
                category
                for category in source_categories
                if category
                and category != target_category
                and category.lower() != "models"
                and "backup" not in category.lower()
            ]

            if not source_categories:
                raise RuntimeError("Birlesik dataset icin kaynak kategori bulunamadi.")

            target_dir = self.training_dir / target_category

            if overwrite and target_dir.exists():
                shutil.rmtree(target_dir)

            self._ensure_category_dirs(target_category)

            if progress_callback:
                progress_callback(2, f"Birlesik dataset hazirlaniyor: {target_category}")

            summary = {
                "target_category": target_category,
                "target_dir": str(target_dir),
                "source_categories": source_categories,
                "copied_images": 0,
                "copied_labels": 0,
                "missing_labels": 0,
                "missing_images": 0,
                "skipped_files": 0,
                "split_stats": {
                    split: {
                        "images": 0,
                        "labels": 0,
                    }
                    for split in self.SPLITS
                },
            }

            total_categories = len(source_categories)

            for cat_index, category in enumerate(source_categories, start=1):
                category_dir = self.training_dir / category

                if not category_dir.exists():
                    summary["skipped_files"] += 1
                    logger.warning(f"Kategori bulunamadi, atlandi: {category}")
                    continue

                safe_category = self._safe_name(category)

                if progress_callback:
                    percent = 2 + int((cat_index / max(1, total_categories)) * 18)
                    progress_callback(percent, f"Veri toplaniyor: {category}")

                for split in self.SPLITS:
                    image_dir = category_dir / "images" / split
                    label_dir = category_dir / "labels" / split

                    if not image_dir.exists():
                        continue

                    target_image_dir = target_dir / "images" / split
                    target_label_dir = target_dir / "labels" / split
                    target_image_dir.mkdir(parents=True, exist_ok=True)
                    target_label_dir.mkdir(parents=True, exist_ok=True)

                    images = [p for p in sorted(image_dir.iterdir()) if self._is_image_file(p)]

                    for image_path in images:
                        label_path = label_dir / f"{image_path.stem}.txt"

                        if not label_path.exists():
                            summary["missing_labels"] += 1
                            logger.warning(f"Label yok, atlandi: {image_path}")
                            continue

                        new_image_name = f"{safe_category}__{image_path.name}"
                        new_label_name = f"{safe_category}__{image_path.stem}.txt"

                        dst_image = target_image_dir / new_image_name
                        dst_label = target_label_dir / new_label_name

                        try:
                            shutil.copy2(image_path, dst_image)
                            shutil.copy2(label_path, dst_label)

                            summary["copied_images"] += 1
                            summary["copied_labels"] += 1
                            summary["split_stats"][split]["images"] += 1
                            summary["split_stats"][split]["labels"] += 1
                        except Exception as e:
                            summary["skipped_files"] += 1
                            logger.warning(f"Kopyalama hatasi: {image_path} ({e})")

            yaml_path = self.create_dataset_yaml(category=target_category, class_names=class_names)
            validation = self.validate_dataset(category=target_category, class_names=class_names)

            summary["yaml_path"] = yaml_path
            summary["validation"] = validation

            if progress_callback:
                if validation.get("ok", False):
                    progress_callback(20, "Birlesik dataset hazir ve dogrulandi")
                else:
                    progress_callback(20, "Birlesik dataset hazirlandi fakat dogrulama hatalari var")

            return summary

        except Exception as e:
            logger.error(f"Birlesik dataset hazirlama hatasi: {e}")
            raise

    # =========================================================
    # DATA IMPORT / VIDEO FRAME CIKARMA
    # =========================================================

    def import_training_data(
        self,
        image_paths: List[str],
        label_paths: List[str],
        dataset_split: str = "train",
        category: str = "default",
    ) -> bool:
        """
        Egitim verisi import et
        """
        try:
            if len(image_paths) != len(label_paths):
                logger.error("Resim ve label sayisi esit olmali")
                return False

            category_dir = self._ensure_category_dirs(category)
            image_dir = category_dir / "images" / dataset_split
            label_dir = category_dir / "labels" / dataset_split

            copied_count = 0

            for img_path, lbl_path in zip(image_paths, label_paths):
                img_src = Path(img_path)
                lbl_src = Path(lbl_path)

                if not img_src.exists() or not lbl_src.exists():
                    logger.warning(f"Dosya bulunamadi: {img_path} veya {lbl_path}")
                    continue

                shutil.copy2(img_src, image_dir / img_src.name)
                shutil.copy2(lbl_src, label_dir / lbl_src.name)
                copied_count += 1

            logger.info(f"{dataset_split} setine {copied_count} ornek eklendi")
            return copied_count > 0

        except Exception as e:
            logger.error(f"Veri import hatasi: {e}")
            return False

    def extract_frames_from_video(
        self,
        video_path: str,
        frame_interval: int = 5,
        max_frames: Optional[int] = None,
        dataset_split: str = "train",
        category: str = "default",
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[int, List[str]]:
        """
        Video dosyasindan frameler cikar ve kaydet
        """
        try:
            video_path_obj = Path(video_path)

            if not video_path_obj.exists():
                logger.error(f"Video bulunamadi: {video_path_obj}")
                return 0, []

            self._ensure_category_dirs(category)

            cap = cv2.VideoCapture(str(video_path_obj))
            if not cap.isOpened():
                logger.error(f"Video acilamadi: {video_path_obj}")
                return 0, []

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            logger.info(f"Video acildi: {total_frames} frame, {fps} FPS")

            if progress_callback:
                progress_callback(0, f"Video isleniyor: {video_path_obj.name}")

            image_dir = self.training_dir / category / "images" / dataset_split
            extracted_frames: List[str] = []
            frame_count = 0
            frame_index = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_index % frame_interval == 0:
                    if max_frames and frame_count >= max_frames:
                        break

                    video_name = video_path_obj.stem
                    frame_filename = f"{video_name}_{frame_count:06d}.jpg"
                    frame_path = image_dir / frame_filename

                    cv2.imwrite(str(frame_path), frame)
                    extracted_frames.append(str(frame_path))
                    frame_count += 1

                    if progress_callback and frame_count % 10 == 0 and total_frames > 0:
                        progress = int((frame_index / total_frames) * 100)
                        progress_callback(progress, f"Frame cikartiliyor: {frame_count}")

                frame_index += 1

            cap.release()

            logger.info(f"Video isleme tamamlandi: {frame_count} frame cikartildi")
            if progress_callback:
                progress_callback(100, f"{frame_count} frame cikartildi")

            return frame_count, extracted_frames

        except Exception as e:
            logger.error(f"Video isleme hatasi: {e}")
            if progress_callback:
                progress_callback(0, f"Hata: {str(e)[:50]}")
            return 0, []

    def create_empty_labels(self, frame_paths: List[str]) -> int:
        """
        Cikartilan frameler icin bos label dosyalari olustur.

        Beklenen frame yolu:
            training_data/<kategori>/images/<split>/dosya.jpg

        Olusacak label yolu:
            training_data/<kategori>/labels/<split>/dosya.txt
        """
        try:
            created_count = 0

            for frame_path in frame_paths:
                frame_p = Path(frame_path)

                split_name = frame_p.parent.name
                category_dir = frame_p.parent.parent.parent
                label_dir = category_dir / "labels" / split_name
                label_dir.mkdir(parents=True, exist_ok=True)

                label_path = label_dir / f"{frame_p.stem}.txt"
                label_path.touch(exist_ok=True)
                created_count += 1

            logger.info(f"{created_count} bos label dosyasi olusturuldu")
            return created_count

        except Exception as e:
            logger.error(f"Label dosyasi olusturma hatasi: {e}")
            return 0

    # =========================================================
    # YAML / EGITIM
    # =========================================================

    def create_dataset_yaml(
        self,
        category: str = "default",
        class_names: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        YOLO egitimi icin kategori bazli data.yaml olustur
        """
        try:
            category_dir = self._ensure_category_dirs(category)
            class_names = self._get_class_names(class_names)

            dataset_config = {
                "path": str(category_dir),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "nc": len(class_names),
                "names": class_names,
            }

            yaml_path = category_dir / "data.yaml"

            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(dataset_config, f, allow_unicode=True, sort_keys=False)

            self.dataset_yaml = str(yaml_path)
            logger.info(f"Dataset YAML olusturuldu: {yaml_path}")
            return str(yaml_path)

        except Exception as e:
            logger.error(f"YAML olusturma hatasi: {e}")
            return None

    def _attach_epoch_progress_callback(
        self,
        yolo_model,
        total_epochs: int,
        progress_callback: Optional[Callable[[int, str], None]],
        start_percent: int = 20,
        end_percent: int = 99,
    ):
        """
        Ultralytics epoch callback ekle.

        Progress araligi:
        - Birlesik dataset hazirlama: 0-20
        - Egitim epoch ilerlemesi: 20-99
        - Bitti: 100
        """
        if progress_callback is None:
            return

        def on_fit_epoch_end(trainer):
            try:
                current_epoch = int(getattr(trainer, "epoch", 0)) + 1
                epochs_total = int(getattr(trainer, "epochs", total_epochs) or total_epochs)

                raw_ratio = current_epoch / max(1, epochs_total)
                percent = start_percent + int(raw_ratio * (end_percent - start_percent))
                percent = max(start_percent, min(end_percent, percent))

                progress_callback(
                    percent,
                    f"Egitim ilerlemesi: {current_epoch}/{epochs_total} epoch (%{percent})",
                )
            except Exception as e:
                logger.debug(f"Epoch progress callback hatasi: {e}")

        try:
            yolo_model.add_callback("on_fit_epoch_end", on_fit_epoch_end)
        except Exception as e:
            logger.warning(f"Ultralytics callback eklenemedi: {e}")

    def train(
        self,
        category: str,
        epochs: int = 100,
        imgsz: int = 640,
        batch: int = 1,
        class_names: Optional[List[str]] = None,
    ):
        """
        Eski kullanim uyumlulugu icin wrapper
        """
        self.create_dataset_yaml(category=category, class_names=class_names)
        return self.train_model(
            category=category,
            epochs=epochs,
            batch_size=batch,
            imgsz=imgsz,
            class_names=class_names,
        )

    def train_model(
        self,
        category: str = "default",
        epochs: int = 50,
        batch_size: int = 16,
        imgsz: int = 640,
        patience: int = 20,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        class_names: Optional[List[str]] = None,
        clear_cache: bool = True,
    ) -> Optional[str]:
        """
        Modeli egit.

        progress_callback(percent, message) seklinde cagrilir.
        """
        try:
            if YOLO is None:
                logger.error("Ultralytics yuklenmedi")
                return None

            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            epochs = max(1, int(epochs))
            batch_size = max(1, int(batch_size))
            imgsz = max(32, int(imgsz))
            patience = max(0, int(patience))

            class_names = self._get_class_names(class_names)

            if progress_callback:
                progress_callback(0, "Dataset YAML olusturuluyor...")

            self.create_dataset_yaml(category=category, class_names=class_names)

            if clear_cache:
                self._remove_dataset_cache(category)

            if progress_callback:
                progress_callback(5, "Dataset dogrulaniyor...")

            validation = self.validate_dataset(category=category, class_names=class_names)

            if not validation["ok"]:
                short_errors = "\n".join(validation["errors"][:10])
                raise ValueError(
                    "Dataset dogrulama basarisiz.\n"
                    f"{short_errors}\n"
                    "Ilk 10 hata gosterildi."
                )

            logger.info(f"Model egitimi baslaniyor: {self.base_model}")

            if progress_callback:
                progress_callback(10, "Model yukleniyor...")

            self.model = YOLO(self.base_model)

            self._attach_epoch_progress_callback(
                self.model,
                total_epochs=epochs,
                progress_callback=progress_callback,
                start_percent=15,
                end_percent=99,
            )

            device_value = (
                config.GPU_DEVICE
                if (config.USE_GPU and torch.cuda.is_available())
                else "cpu"
            )

            if progress_callback:
                progress_callback(15, "Egitim basladi...")

            self.model.train(
                data=self.dataset_yaml,
                epochs=epochs,
                imgsz=imgsz,
                batch=batch_size,
                patience=patience,
                workers=0,
                device=device_value,
                verbose=True,
                save=True,
                project=str(self.training_dir / "models"),
                name=category,
                exist_ok=True,
            )

            best_model_path = self.training_dir / "models" / category / "weights" / "best.pt"

            if best_model_path.exists():
                final_path = Path(config.MODEL_PATH)
                final_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(best_model_path, final_path)

                logger.info(f"Egitilmis model kaydedildi: {final_path}")

                if progress_callback:
                    progress_callback(100, "Egitim tamamlandi!")

                return str(final_path)

            logger.warning("Best model dosyasi bulunamadi")

            if progress_callback:
                progress_callback(100, "Egitim tamamlandi ama model kaydedilemedi")

            return None

        except Exception as e:
            logger.error(f"Egitim hatasi: {e}")
            if progress_callback:
                progress_callback(-1, f"HATA: {e}")
            return None

    def train_combined_model(
        self,
        source_categories: Optional[List[str]] = None,
        target_category: str = COMBINED_DATASET_NAME,
        epochs: int = 50,
        batch_size: int = 16,
        imgsz: int = 640,
        patience: int = 20,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        class_names: Optional[List[str]] = None,
        overwrite_dataset: bool = True,
    ) -> Optional[str]:
        """
        Tum kategorileri tek dataset altinda topla ve final modeli egit.

        Bu, nihai sistem icin tavsiye edilen egitim yoludur.
        """
        try:
            class_names = self._get_class_names(class_names)

            if progress_callback:
                progress_callback(0, "Birlesik final model egitimi hazirlaniyor...")

            combined_summary = self.prepare_combined_dataset(
                source_categories=source_categories,
                target_category=target_category,
                overwrite=overwrite_dataset,
                class_names=class_names,
                progress_callback=progress_callback,
            )

            validation = combined_summary.get("validation", {})

            if not validation.get("ok", False):
                errors = validation.get("errors", [])
                short_errors = "\n".join(errors[:10])
                raise ValueError(
                    "Birlesik dataset dogrulama basarisiz.\n"
                    f"{short_errors}\n"
                    "Ilk 10 hata gosterildi."
                )

            if progress_callback:
                progress_callback(20, "Birlesik dataset hazir. Model egitimi baslatiliyor...")

            return self.train_model(
                category=target_category,
                epochs=epochs,
                batch_size=batch_size,
                imgsz=imgsz,
                patience=patience,
                progress_callback=progress_callback,
                class_names=class_names,
                clear_cache=True,
            )

        except Exception as e:
            logger.error(f"Birlesik model egitim hatasi: {e}")
            if progress_callback:
                progress_callback(-1, f"HATA: {e}")
            return None

    # =========================================================
    # MODEL VALIDASYON / STATS
    # =========================================================

    def validate_model(self, model_path: Optional[str] = None) -> Optional[Dict]:
        """
        Modeli dogrula
        """
        try:
            if YOLO is None:
                logger.error("Ultralytics yuklenmedi")
                return None

            if model_path is None:
                model_path = config.MODEL_PATH

            logger.info(f"Model dogrulaniyor: {model_path}")

            model = YOLO(model_path)
            results = model.val()

            metrics = {
                "map50": float(results.box.map50) if hasattr(results, "box") else None,
                "map": float(results.box.map) if hasattr(results, "box") else None,
                "fitness": float(results.fitness) if hasattr(results, "fitness") else None,
            }

            logger.info(f"Dogrulama sonuclari: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Dogrulama hatasi: {e}")
            return None

    def get_training_data_stats(self, category: str = "default") -> Dict:
        """Kategori bazli egitim verisi istatistiklerini al"""
        try:
            category_dir = self._ensure_category_dirs(category)
            stats = {}

            for split in self.SPLITS:
                image_count = len(
                    [
                        p
                        for p in (category_dir / "images" / split).glob("*")
                        if p.is_file()
                    ]
                )
                label_count = len(list((category_dir / "labels" / split).glob("*.txt")))
                stats[split] = {
                    "images": image_count,
                    "labels": label_count,
                }

            return stats

        except Exception as e:
            logger.error(f"Istatistik hatasi: {e}")
            return {}

    # =========================================================
    # DOSYA KOPYALAMA
    # =========================================================

    def copy_image_to_category(
        self,
        image_path: str,
        category: str = "default",
        dataset_split: str = "train",
    ) -> bool:
        """
        Resim dosyasini belirtilen kategoriye ve bolume kopyala
        """
        try:
            src_path = Path(image_path)
            if not src_path.exists():
                logger.warning(f"Resim bulunamadi: {image_path}")
                return False

            self._ensure_category_dirs(category)

            dst_dir = self.training_dir / category / "images" / dataset_split
            dst_path = dst_dir / src_path.name
            shutil.copy2(src_path, dst_path)

            logger.info(f"Resim kopyalandi: {src_path.name} -> {category}/{dataset_split}")
            return True

        except Exception as e:
            logger.error(f"Resim kopyalama hatasi: {e}")
            return False

    def copy_label_to_category(
        self,
        label_path: str,
        category: str = "default",
        dataset_split: str = "train",
    ) -> bool:
        """
        Label dosyasini belirtilen kategoriye ve bolume kopyala
        """
        try:
            src_path = Path(label_path)
            if not src_path.exists():
                logger.warning(f"Label bulunamadi: {label_path}")
                return False

            self._ensure_category_dirs(category)

            dst_dir = self.training_dir / category / "labels" / dataset_split
            dst_path = dst_dir / src_path.name
            shutil.copy2(src_path, dst_path)

            logger.info(f"Label kopyalandi: {src_path.name} -> {category}/{dataset_split}")
            return True

        except Exception as e:
            logger.error(f"Label kopyalama hatasi: {e}")
            return False
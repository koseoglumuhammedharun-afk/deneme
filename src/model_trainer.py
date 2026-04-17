# -*- coding: utf-8 -*-
"""
Model Egitim Modulu - YOLO v8 Custom Model Egitimi
"""

import logging
import shutil
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

    def __init__(self, base_model: str = "yolov8n.pt"):
        self.base_model = base_model
        self.model = None
        self.training_dir = Path(
            getattr(config, "TRAINING_DATA_DIR", Path(config.PROJECT_ROOT) / "training_data")
        )
        self.dataset_yaml: Optional[str] = None
        self._setup_training_dirs()

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
        for split in ["train", "val", "test"]:
            (category_dir / "images" / split).mkdir(parents=True, exist_ok=True)
            (category_dir / "labels" / split).mkdir(parents=True, exist_ok=True)
        return category_dir

    def _get_class_names(self, class_names: Optional[List[str]] = None) -> List[str]:
        """Sinif isimlerini config veya parametreden al"""
        if class_names:
            return class_names
        return list(getattr(config, "CLASS_NAMES", ["obus"]))

    def _is_image_file(self, path: Path) -> bool:
        supported = getattr(
            config,
            "SUPPORTED_IMAGE_FORMATS",
            (".jpg", ".jpeg", ".png", ".bmp", ".tiff"),
        )
        return path.is_file() and path.suffix.lower() in supported

    def validate_dataset(
        self,
        category: str = "default",
        class_names: Optional[List[str]] = None,
    ) -> Dict:
        """
        Veri setini egitimden once dogrula.
        Label satirlari: class x_center y_center width height
        Tum koordinatlar 0-1 araliginda olmali.
        """
        try:
            class_names = self._get_class_names(class_names)
            num_classes = len(class_names)
            category_dir = self._ensure_category_dirs(category)

            errors: List[str] = []
            stats: Dict[str, Dict[str, int]] = {}

            for split in ["train", "val", "test"]:
                image_dir = category_dir / "images" / split
                label_dir = category_dir / "labels" / split

                images = [p for p in image_dir.iterdir() if self._is_image_file(p)] if image_dir.exists() else []
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
                            errors.append(f"{label_path.name}:{line_no} -> 5 kolon olmali, bulunan: {len(parts)}")
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

                        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
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

            # Kritik minimum veri kontrolü
            if stats.get("train", {}).get("images", 0) == 0:
                errors.append("train split icinde hic resim yok.")
            if stats.get("train", {}).get("labels", 0) == 0:
                errors.append("train split icinde hic label yok.")
            if stats.get("val", {}).get("images", 0) == 0:
                errors.append("val split icinde hic resim yok.")
            if stats.get("val", {}).get("labels", 0) == 0:
                errors.append("val split icinde hic label yok.")

            return {
                "ok": len(errors) == 0,
                "errors": errors,
                "stats": stats,
            }

        except Exception as e:
            logger.error(f"Dataset dogrulama hatasi: {e}")
            return {
                "ok": False,
                "errors": [str(e)],
                "stats": {},
            }

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
        Cikartilan frameler icin bos label dosyalari olustur

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
        progress_callback: Optional[Callable] = None,
        class_names: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Modeli egit
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

            self.create_dataset_yaml(category=category, class_names=class_names)

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
                progress_callback(0, "Model yukleniyor...")

            self.model = YOLO(self.base_model)

            device_value = (
                config.GPU_DEVICE
                if (config.USE_GPU and torch.cuda.is_available())
                else "cpu"
            )

            self.model.train(
                 data=self.dataset_yaml,
                 epochs=epochs,
                  imgsz=imgsz,
                  batch=batch_size,
                   patience=patience,
                   workers=0,
                  device=0 if (config.USE_GPU and torch.cuda.is_available()) else "cpu",
                  verbose=True,
                  save=True,
                   project=str(self.training_dir / "models"),
                  name=category,
                    exist_ok=True,
            )

            best_model_path = self.training_dir / "models" / category / "weights" / "best.pt"

            if best_model_path.exists():
                final_path = config.MODEL_PATH
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

            for split in ["train", "val", "test"]:
                image_count = len([p for p in (category_dir / "images" / split).glob("*") if p.is_file()])
                label_count = len(list((category_dir / "labels" / split).glob("*.txt")))
                stats[split] = {
                    "images": image_count,
                    "labels": label_count,
                }

            return stats

        except Exception as e:
            logger.error(f"Istatistik hatasi: {e}")
            return {}

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
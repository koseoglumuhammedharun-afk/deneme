# -*- coding: utf-8 -*-
"""
Video Model Tester
Mevcut YOLO modelini video üzerinde test eder.
Tespit edilen / tespit edilmeyen kareleri ayrı klasörlere kaydeder.
CSV raporu üretir.

Kullanım:
python video_model_tester.py --video "C:\video\test.mp4" --conf 0.45 --sample-every 10
"""

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2

try:
    from ultralytics import YOLO
except Exception as exc:
    YOLO = None
    YOLO_IMPORT_ERROR = exc
else:
    YOLO_IMPORT_ERROR = None


PROJECT_ROOT = Path(__file__).parent
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "howitzer_detector.pt"
OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "video_tester"


def safe_name(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text)
    return cleaned.strip("_") or "video"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_model_names(model) -> dict:
    names = getattr(model, "names", {})
    if isinstance(names, dict):
        return names
    if isinstance(names, list):
        return {i: name for i, name in enumerate(names)}
    return {}


def draw_boxes(frame, detections, names):
    annotated = frame.copy()

    for det in detections:
        cls_id = det["class_id"]
        conf = det["confidence"]
        x1, y1, x2, y2 = det["xyxy"]

        label = names.get(cls_id, str(cls_id))
        text = f"{label} {conf:.2f}"

        color = (0, 255, 0)
        thickness = 2

        cv2.rectangle(
            annotated,
            (int(x1), int(y1)),
            (int(x2), int(y2)),
            color,
            thickness,
        )

        text_y = max(20, int(y1) - 8)
        cv2.putText(
            annotated,
            text,
            (int(x1), text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

    return annotated


def extract_detections(result, high_conf: float, low_conf: float):
    high = []
    low = []

    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return high, low

    for box in boxes:
        try:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            xyxy = box.xyxy[0].tolist()
        except Exception:
            continue

        det = {
            "class_id": cls_id,
            "confidence": conf,
            "xyxy": [float(v) for v in xyxy],
        }

        if conf >= high_conf:
            high.append(det)
        elif conf >= low_conf:
            low.append(det)

    return high, low


def write_summary(summary_path: Path, summary: dict) -> None:
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("VIDEO MODEL TEST RAPORU\n")
        f.write("=" * 60 + "\n\n")

        for key, value in summary.items():
            if isinstance(value, dict):
                f.write(f"{key}:\n")
                for sub_key, sub_value in value.items():
                    f.write(f"  {sub_key}: {sub_value}\n")
            else:
                f.write(f"{key}: {value}\n")


def run_video_test(
    video_path: Path,
    model_path: Path,
    conf: float = 0.45,
    low_conf: float = 0.15,
    sample_every: int = 10,
    imgsz: int = 1280,
    max_frames: int = 0,
):
    if YOLO is None:
        raise RuntimeError(f"Ultralytics YOLO yuklenemedi: {YOLO_IMPORT_ERROR}")

    if not video_path.exists():
        raise FileNotFoundError(f"Video bulunamadi: {video_path}")

    if not model_path.exists():
        raise FileNotFoundError(f"Model bulunamadi: {model_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{safe_name(video_path.stem)}_{timestamp}"
    output_dir = OUTPUT_ROOT / run_name

    detected_dir = output_dir / "01_detected_frames"
    no_detect_dir = output_dir / "02_no_detection_frames"
    low_conf_dir = output_dir / "03_low_conf_possible_frames"
    raw_sample_dir = output_dir / "04_raw_sample_frames"

    for directory in [detected_dir, no_detect_dir, low_conf_dir, raw_sample_dir]:
        ensure_dir(directory)

    report_csv = output_dir / "detections_report.csv"
    report_json = output_dir / "detections_report.json"
    summary_txt = output_dir / "summary.txt"

    print("Model yukleniyor:", model_path)
    model = YOLO(str(model_path))
    names = get_model_names(model)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Video acilamadi: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    print("Video:", video_path)
    print("FPS:", fps)
    print("Frame:", total_frames)
    print("Cozunurluk:", width, "x", height)
    print("Conf:", conf)
    print("Low conf:", low_conf)
    print("Sample every:", sample_every)
    print("Output:", output_dir)
    print()

    rows = []
    json_rows = []

    processed_count = 0
    sampled_count = 0
    detected_frame_count = 0
    no_detect_frame_count = 0
    low_conf_frame_count = 0
    detection_counter = Counter()

    frame_index = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if max_frames > 0 and frame_index >= max_frames:
            break

        if frame_index % sample_every != 0:
            frame_index += 1
            continue

        sampled_count += 1
        time_sec = frame_index / fps if fps > 0 else 0.0

        frame_base = f"frame_{frame_index:06d}_t_{time_sec:.2f}s"
        raw_path = raw_sample_dir / f"{frame_base}.jpg"
        cv2.imwrite(str(raw_path), frame)

        results = model.predict(
            frame,
            conf=low_conf,
            imgsz=imgsz,
            verbose=False,
        )

        result = results[0]
        high_detections, low_detections = extract_detections(result, conf, low_conf)

        if high_detections:
            detected_frame_count += 1
            annotated = draw_boxes(frame, high_detections, names)
            out_path = detected_dir / f"{frame_base}_detected.jpg"
            cv2.imwrite(str(out_path), annotated)

            for det in high_detections:
                cls_id = det["class_id"]
                cls_name = names.get(cls_id, str(cls_id))
                detection_counter[cls_name] += 1

                x1, y1, x2, y2 = det["xyxy"]

                row = {
                    "frame_index": frame_index,
                    "time_sec": round(time_sec, 3),
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": round(det["confidence"], 6),
                    "x1": round(x1, 2),
                    "y1": round(y1, 2),
                    "x2": round(x2, 2),
                    "y2": round(y2, 2),
                    "bbox_width": round(x2 - x1, 2),
                    "bbox_height": round(y2 - y1, 2),
                    "saved_frame": str(out_path),
                }
                rows.append(row)
                json_rows.append(row)

        elif low_detections:
            low_conf_frame_count += 1
            annotated = draw_boxes(frame, low_detections, names)
            out_path = low_conf_dir / f"{frame_base}_low_conf.jpg"
            cv2.imwrite(str(out_path), annotated)

            for det in low_detections:
                cls_id = det["class_id"]
                cls_name = names.get(cls_id, str(cls_id))
                x1, y1, x2, y2 = det["xyxy"]

                row = {
                    "frame_index": frame_index,
                    "time_sec": round(time_sec, 3),
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": round(det["confidence"], 6),
                    "x1": round(x1, 2),
                    "y1": round(y1, 2),
                    "x2": round(x2, 2),
                    "y2": round(y2, 2),
                    "bbox_width": round(x2 - x1, 2),
                    "bbox_height": round(y2 - y1, 2),
                    "saved_frame": str(out_path),
                    "note": "low_conf_possible",
                }
                rows.append(row)
                json_rows.append(row)

        else:
            no_detect_frame_count += 1
            out_path = no_detect_dir / f"{frame_base}_no_detection.jpg"
            cv2.imwrite(str(out_path), frame)

        processed_count += 1

        if sampled_count % 25 == 0:
            print(
                f"Islenen sample: {sampled_count} | "
                f"frame: {frame_index}/{total_frames} | "
                f"detected: {detected_frame_count} | "
                f"no_detect: {no_detect_frame_count} | "
                f"low_conf: {low_conf_frame_count}"
            )

        frame_index += 1

    cap.release()

    fieldnames = [
        "frame_index",
        "time_sec",
        "class_id",
        "class_name",
        "confidence",
        "x1",
        "y1",
        "x2",
        "y2",
        "bbox_width",
        "bbox_height",
        "saved_frame",
        "note",
    ]

    with open(report_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            safe_row = {name: row.get(name, "") for name in fieldnames}
            writer.writerow(safe_row)

    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(json_rows, f, ensure_ascii=False, indent=2)

    summary = {
        "video": str(video_path),
        "model": str(model_path),
        "output_dir": str(output_dir),
        "fps": fps,
        "total_frames": total_frames,
        "resolution": f"{width}x{height}",
        "confidence": conf,
        "low_confidence": low_conf,
        "sample_every": sample_every,
        "sampled_frames": sampled_count,
        "detected_frames": detected_frame_count,
        "no_detection_frames": no_detect_frame_count,
        "low_conf_possible_frames": low_conf_frame_count,
        "total_report_rows": len(rows),
        "class_counts": dict(detection_counter),
    }

    write_summary(summary_txt, summary)

    print()
    print("TEST TAMAMLANDI")
    print("Output:", output_dir)
    print("CSV:", report_csv)
    print("JSON:", report_json)
    print("Summary:", summary_txt)
    print("Detected frames:", detected_frame_count)
    print("No detection frames:", no_detect_frame_count)
    print("Low conf possible frames:", low_conf_frame_count)
    print("Class counts:", dict(detection_counter))

    return output_dir


def parse_args():
    parser = argparse.ArgumentParser(description="YOLO video model tester")

    parser.add_argument(
        "--video",
        required=True,
        help="Test edilecek video dosya yolu",
    )

    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL_PATH),
        help="Model dosya yolu. Varsayilan: models/howitzer_detector.pt",
    )

    parser.add_argument(
        "--conf",
        type=float,
        default=0.45,
        help="Ana tespit confidence esigi",
    )

    parser.add_argument(
        "--low-conf",
        type=float,
        default=0.15,
        help="Dusuk guvenli olasi tespitleri ayirmak icin esik",
    )

    parser.add_argument(
        "--sample-every",
        type=int,
        default=10,
        help="Kac frame'de bir analiz yapilsin",
    )

    parser.add_argument(
        "--imgsz",
        type=int,
        default=1280,
        help="YOLO image size",
    )

    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="0 = tum video. Test icin sinir koymak istersen frame sayisi gir.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    run_video_test(
        video_path=Path(args.video),
        model_path=Path(args.model),
        conf=args.conf,
        low_conf=args.low_conf,
        sample_every=max(1, args.sample_every),
        imgsz=args.imgsz,
        max_frames=max(0, args.max_frames),
    )
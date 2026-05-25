import argparse
import cv2
import json
import time
from datetime import datetime
from pathlib import Path

from ultralytics import YOLO

DEFAULT_SOURCE = "videos/id_card/IMG_1640.MOV"
DEFAULT_MODEL_PATH = "runs/detect/train-4/weights/best.pt"
DEFAULT_CONF_THRESHOLD = 0.5
DEFAULT_COOLDOWN_SECONDS = 30
DEFAULT_OUTPUT_DIR = "detections"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Night patrol logger for ID-card-like lost-item detection."
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="Video path, stream URL, or camera index (example: 0).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_PATH,
        help="Path to YOLO model weights.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=DEFAULT_CONF_THRESHOLD,
        help="Confidence threshold for YOLO detections.",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=DEFAULT_COOLDOWN_SECONDS,
        help="Cooldown in seconds between saved detection events.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where detections.json and snapshots are saved.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display OpenCV preview window with detection overlay.",
    )
    return parser.parse_args()


def resolve_source(source):
    source_text = str(source).strip()
    if source_text.isdigit():
        return int(source_text)
    return source_text


def source_label(source):
    if isinstance(source, int):
        return f"camera_{source}"
    if str(source).startswith(("http://", "https://", "rtsp://", "rtmp://")):
        return "stream_source"
    return "video_demo"


def load_detections(detections_file):
    if not detections_file.exists():
        return []
    try:
        with open(detections_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except (json.JSONDecodeError, OSError):
        return []


def save_detection_record(record, detections_file):
    detections = load_detections(detections_file)
    detections.append(record)

    with open(detections_file, "w", encoding="utf-8") as f:
        json.dump(detections, f, indent=2, ensure_ascii=False)


def create_detection_record(object_type, confidence, snapshot_path, source_name):
    now = datetime.now()

    return {
        "eventType": "LOST_ITEM_DETECTED",
        "objectType": object_type,
        "confidence": round(float(confidence), 4),
        "priority": "HIGH",
        "detectedAt": now.isoformat(timespec="seconds"),
        "snapshotPath": str(snapshot_path),
        "location": {
            "source": source_name,
            "floorId": "floor_1",
            "x": None,
            "y": None,
            "patrolCheckpoint": None
        },
        "status": "PENDING_REVIEW",
        "notes": "ID-card-like object detected on the floor during patrol scan."
    }


def main():
    args = parse_args()

    selected_source = resolve_source(args.source)
    selected_model = args.model
    selected_conf = args.conf
    selected_cooldown = args.cooldown
    output_dir = Path(args.output_dir)
    snapshot_dir = output_dir / "snapshots"
    detections_file = output_dir / "detections.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(selected_model)
    cap = cv2.VideoCapture(selected_source)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {selected_source}")

    last_saved_at = 0

    print("Night patrol ID-card logger running.")
    print(f"Source: {selected_source}")
    print(f"Model: {selected_model}")
    print(f"Confidence threshold: {selected_conf}")
    print(f"Cooldown seconds: {selected_cooldown}")
    print(f"Output directory: {output_dir}")
    print(f"Detections file: {detections_file}")
    print(f"Display window: {'ON' if args.show else 'OFF'}")
    if args.show:
        print("Press q to quit.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Video finished.")
                break

            results = model.predict(frame, conf=selected_conf, verbose=False)

            detected_this_frame = False

            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = model.names[cls_id]
                    confidence = float(box.conf[0])

                    if cls_name != "id_card":
                        continue

                    detected_this_frame = True

                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 3)
                    cv2.putText(
                        frame,
                        f"id_card {confidence:.2f}",
                        (x1, max(30, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (255, 0, 0),
                        2,
                    )

                    now = time.time()

                    if now - last_saved_at >= selected_cooldown:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        snapshot_path = snapshot_dir / f"id_card_{timestamp}.jpg"

                        cv2.imwrite(str(snapshot_path), frame)

                        record = create_detection_record(
                            object_type="id_card",
                            confidence=confidence,
                            snapshot_path=snapshot_path,
                            source_name=source_label(selected_source),
                        )

                        save_detection_record(record, detections_file)
                        last_saved_at = now

                        print(
                            f"Saved detection: object=id_card "
                            f"conf={record['confidence']:.4f} "
                            f"time={record['detectedAt']} "
                            f"snapshot={record['snapshotPath']}"
                        )

            if detected_this_frame:
                cv2.putText(
                    frame,
                    "LOST ITEM DETECTED: ID CARD",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 0, 255),
                    3,
                )
            else:
                cv2.putText(
                    frame,
                    "Patrol scanning...",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 255, 0),
                    3,
                )

            if args.show:
                cv2.imshow("Night Patrol Lost Item Detection", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("Stopped by user.")
                    break
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

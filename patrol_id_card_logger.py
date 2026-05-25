import argparse
import cv2
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

DEFAULT_SOURCE = "videos/id_card/IMG_1640.MOV"
DEFAULT_MODEL_PATH = "runs/detect/train-v2/weights/best.pt"
DEFAULT_CONF_THRESHOLD = 0.5
DEFAULT_SAVE_CONF_THRESHOLD = 0.75
DEFAULT_MIN_FRAMES = 3
DEFAULT_COOLDOWN_SECONDS = 30
DEFAULT_OUTPUT_DIR = "detections"
EDGE_MARGIN_RATIO = 0.05


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
        "--save-conf",
        type=float,
        default=DEFAULT_SAVE_CONF_THRESHOLD,
        help="Minimum confidence required to save a detection event.",
    )
    parser.add_argument(
        "--min-frames",
        type=int,
        default=DEFAULT_MIN_FRAMES,
        help="Minimum consecutive frames required before saving an event.",
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


def touches_frame_edge(x1, y1, x2, y2, frame_width, frame_height, margin_ratio=EDGE_MARGIN_RATIO):
    margin_x = int(frame_width * margin_ratio)
    margin_y = int(frame_height * margin_ratio)

    return (
        x1 <= margin_x
        or y1 <= margin_y
        or x2 >= frame_width - margin_x
        or y2 >= frame_height - margin_y
    )


def main():
    args = parse_args()

    selected_source = resolve_source(args.source)
    selected_model = args.model
    preview_conf = args.conf
    selected_cooldown = args.cooldown
    save_conf = args.save_conf
    min_frames = max(1, args.min_frames)
    output_dir = Path(args.output_dir)
    snapshot_dir = output_dir / "snapshots"
    detections_file = output_dir / "detections.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    from ultralytics import YOLO

    model = YOLO(selected_model)
    cap = cv2.VideoCapture(selected_source)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {selected_source}")

    last_saved_at = 0

    print("Night patrol ID-card logger running.")
    print(f"Source: {selected_source}")
    print(f"Model: {selected_model}")
    print(f"Preview confidence threshold (--conf): {preview_conf}")
    print(f"Save confidence threshold (--save-conf): {save_conf}")
    print(f"Minimum consecutive frames (--min-frames): {min_frames}")
    print(f"Edge margin ratio: {EDGE_MARGIN_RATIO:.0%}")
    print(f"Cooldown seconds: {selected_cooldown}")
    print(f"Output directory: {output_dir}")
    print(f"Detections file: {detections_file}")
    print(f"Display window: {'ON' if args.show else 'OFF'}")
    if args.show:
        print("Press q to quit.")

    streak_count = 0
    streak_best_conf = 0.0
    streak_best_frame: Optional[Any] = None
    streak_saved = False

    try:
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Video finished.")
                    break

                frame_h, frame_w = frame.shape[:2]
                results = model.predict(frame, conf=preview_conf, verbose=False)

                detected_this_frame = False
                frame_best_candidate_conf = 0.0
                frame_best_candidate_frame = None

                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        cls_name = model.names[cls_id]
                        confidence = float(box.conf[0])

                        if cls_name != "id_card":
                            continue

                        detected_this_frame = True

                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        is_edge = touches_frame_edge(x1, y1, x2, y2, frame_w, frame_h)

                        eligible_for_save = (confidence >= save_conf) and (not is_edge)
                        box_color = (0, 255, 0) if eligible_for_save else (0, 165, 255)
                        status_text = "save-ready" if eligible_for_save else "preview-only"

                        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 3)
                        cv2.putText(
                            frame,
                            f"id_card {confidence:.2f} ({status_text})",
                            (x1, max(30, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            box_color,
                            2,
                        )

                        if eligible_for_save and confidence > frame_best_candidate_conf:
                            frame_best_candidate_conf = confidence
                            frame_best_candidate_frame = frame.copy()

                if frame_best_candidate_frame is not None:
                    streak_count += 1
                    if frame_best_candidate_conf > streak_best_conf:
                        streak_best_conf = frame_best_candidate_conf
                        streak_best_frame = frame_best_candidate_frame
                    now = time.time()
                    cooldown_ready = now - last_saved_at >= selected_cooldown

                    if streak_count >= min_frames and cooldown_ready and not streak_saved:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        snapshot_path = snapshot_dir / f"id_card_{timestamp}.jpg"

                        if streak_best_frame is not None:
                            cv2.imwrite(str(snapshot_path), streak_best_frame)

                        record = create_detection_record(
                            object_type="id_card",
                            confidence=streak_best_conf,
                            snapshot_path=snapshot_path,
                            source_name=source_label(selected_source),
                        )

                        save_detection_record(record, detections_file)
                        last_saved_at = now
                        streak_saved = True

                        print(
                            f"Saved detection: object=id_card "
                            f"conf={record['confidence']:.4f} "
                            f"frames={streak_count} "
                            f"time={record['detectedAt']} "
                            f"snapshot={record['snapshotPath']}"
                        )
                else:
                    streak_count = 0
                    streak_best_conf = 0.0
                    streak_best_frame = None
                    streak_saved = False

                if detected_this_frame:
                    cv2.putText(
                        frame,
                        "ID CARD CANDIDATE IN VIEW",
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
        except KeyboardInterrupt:
            print("Stopped by user (Ctrl+C).")
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped by user (Ctrl+C).")

import argparse
import cv2
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

DEFAULT_SOURCE = "videos/id_card/IMG_1640.MOV"
DEFAULT_MODEL_PATH = "runs/detect/train-v2/weights/best.pt"
DEFAULT_CONF_THRESHOLD = 0.5
DEFAULT_SAVE_CONF_THRESHOLD = 0.75
DEFAULT_MIN_FRAMES = 3
DEFAULT_COCO_MODEL_PATH = "yolov8n.pt"
DEFAULT_COCO_CLASSES = "bottle"
DEFAULT_COCO_CONF_THRESHOLD = 0.5
DEFAULT_COCO_SAVE_CONF_THRESHOLD = 0.6
DEFAULT_COCO_MIN_FRAMES = 3
DEFAULT_COOLDOWN_SECONDS = 30
DEFAULT_OUTPUT_DIR = "detections"
DEFAULT_MQTT_HOST = "localhost"
DEFAULT_MQTT_PORT = 1883
DEFAULT_MQTT_TOPIC = "robot/robot_01/lost-item"
DEFAULT_ROBOT_ID = "robot_01"
EDGE_MARGIN_RATIO = 0.05
SUPPORTED_COCO_CLASSES = {"bottle"}

OBJECT_EVENT_META = {
    "id_card": {
        "priority": "HIGH",
        "notes": "ID-card-like object detected on the floor during patrol scan.",
    },
    "bottle": {
        "priority": "LOW",
        "notes": "Bottle-like object detected on the floor during patrol scan.",
    },
}

OBJECT_COLORS = {
    "id_card": {
        "save_ready": (0, 255, 0),
        "preview_only": (0, 165, 255),
    },
    "bottle": {
        "save_ready": (255, 0, 0),
        "preview_only": (0, 255, 255),
    },
}


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
    parser.add_argument(
        "--enable-coco",
        action="store_true",
        help="Enable extra COCO detection (currently bottle only).",
    )
    parser.add_argument(
        "--coco-model",
        default=DEFAULT_COCO_MODEL_PATH,
        help="Path/name of pretrained COCO YOLO model (auto-download if missing).",
    )
    parser.add_argument(
        "--coco-classes",
        default=DEFAULT_COCO_CLASSES,
        help="Comma-separated COCO classes to track (currently only bottle is supported).",
    )
    parser.add_argument(
        "--coco-conf",
        type=float,
        default=DEFAULT_COCO_CONF_THRESHOLD,
        help="Preview confidence threshold for COCO detections.",
    )
    parser.add_argument(
        "--coco-save-conf",
        type=float,
        default=DEFAULT_COCO_SAVE_CONF_THRESHOLD,
        help="Minimum confidence required to save a COCO detection event.",
    )
    parser.add_argument(
        "--coco-min-frames",
        type=int,
        default=DEFAULT_COCO_MIN_FRAMES,
        help="Minimum consecutive frames required before saving a COCO event.",
    )
    parser.add_argument(
        "--mqtt",
        action="store_true",
        help="Enable MQTT publishing for locally saved LOST_ITEM_DETECTED events.",
    )
    parser.add_argument(
        "--mqtt-host",
        default=DEFAULT_MQTT_HOST,
        help="MQTT broker host.",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=DEFAULT_MQTT_PORT,
        help="MQTT broker port.",
    )
    parser.add_argument(
        "--mqtt-topic",
        default=DEFAULT_MQTT_TOPIC,
        help="MQTT topic for LOST_ITEM_DETECTED events.",
    )
    parser.add_argument(
        "--robot-id",
        default=DEFAULT_ROBOT_ID,
        help="Robot identifier included in MQTT payloads.",
    )
    parser.add_argument(
        "--mqtt-username",
        default=None,
        help="Optional MQTT username.",
    )
    parser.add_argument(
        "--mqtt-password",
        default=None,
        help="Optional MQTT password.",
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
    event_meta = OBJECT_EVENT_META[object_type]

    return {
        "eventType": "LOST_ITEM_DETECTED",
        "objectType": object_type,
        "confidence": round(float(confidence), 4),
        "priority": event_meta["priority"],
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
        "notes": event_meta["notes"]
    }


def init_mqtt_client(args) -> Tuple[Optional[Any], bool]:
    if not args.mqtt:
        return None, False

    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print(
            "WARNING: MQTT enabled but paho-mqtt is not installed. "
            "MQTT publishing disabled."
        )
        print("Install with: .venv/bin/pip install paho-mqtt")
        return None, False

    client = mqtt.Client()
    if args.mqtt_username:
        client.username_pw_set(args.mqtt_username, args.mqtt_password or "")

    try:
        client.connect(args.mqtt_host, args.mqtt_port, keepalive=60)
        client.loop_start()
        return client, True
    except Exception as exc:
        print(
            f"WARNING: MQTT connect failed ({args.mqtt_host}:{args.mqtt_port}) - {exc}. "
            "Continuing with local logging only."
        )
        return None, False


def build_mqtt_payload(record: Dict[str, Any], robot_id: str) -> Dict[str, Any]:
    payload = dict(record)
    payload["robotId"] = robot_id
    return payload


def publish_mqtt_event(client: Optional[Any], topic: str, payload: Dict[str, Any]) -> None:
    if client is None:
        return

    try:
        publish_info = client.publish(
            topic=topic,
            payload=json.dumps(payload, ensure_ascii=False),
            qos=0,
            retain=False,
        )
        result_code = getattr(publish_info, "rc", 0)
        if result_code == 0:
            print(
                f"MQTT published: topic={topic} "
                f"object={payload['objectType']} conf={payload['confidence']:.4f}"
            )
        else:
            print(
                f"WARNING: MQTT publish failed (rc={result_code}) topic={topic}. "
                "Local logging was still saved."
            )
    except Exception as exc:
        print(
            f"WARNING: MQTT publish error ({exc}). "
            "Local logging was still saved."
        )


def touches_frame_edge(x1, y1, x2, y2, frame_width, frame_height, margin_ratio=EDGE_MARGIN_RATIO):
    margin_x = int(frame_width * margin_ratio)
    margin_y = int(frame_height * margin_ratio)

    return (
        x1 <= margin_x
        or y1 <= margin_y
        or x2 >= frame_width - margin_x
        or y2 >= frame_height - margin_y
    )


def parse_coco_classes(coco_classes: str) -> List[str]:
    parts = [part.strip().lower() for part in coco_classes.split(",")]
    return [part for part in parts if part]


def init_object_state() -> Dict[str, Any]:
    return {
        "streak_count": 0,
        "streak_best_conf": 0.0,
        "streak_best_frame": None,
        "streak_saved": False,
    }


def process_candidates_for_object(
    object_type: str,
    boxes,
    class_names,
    frame,
    frame_w: int,
    frame_h: int,
    save_conf_threshold: float,
    frame_candidates: Set[str],
    frame_best_candidates: Dict[str, Tuple[float, Any]],
):
    for box in boxes:
        cls_id = int(box.cls[0])
        cls_name = str(class_names[cls_id]).lower()
        if cls_name != object_type:
            continue

        confidence = float(box.conf[0])
        frame_candidates.add(object_type)

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        is_edge = touches_frame_edge(x1, y1, x2, y2, frame_w, frame_h)
        eligible_for_save = (confidence >= save_conf_threshold) and (not is_edge)
        colors = OBJECT_COLORS[object_type]
        box_color = colors["save_ready"] if eligible_for_save else colors["preview_only"]
        status_text = "save-ready" if eligible_for_save else "preview-only"

        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 3)
        cv2.putText(
            frame,
            f"{object_type} {confidence:.2f} ({status_text})",
            (x1, max(30, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            box_color,
            2,
        )

        current_best = frame_best_candidates.get(object_type)
        if eligible_for_save and (current_best is None or confidence > current_best[0]):
            frame_best_candidates[object_type] = (confidence, frame.copy())


def main():
    args = parse_args()

    selected_source = resolve_source(args.source)
    selected_model = args.model
    preview_conf = args.conf
    selected_cooldown = args.cooldown
    save_conf = args.save_conf
    min_frames = max(1, args.min_frames)
    coco_conf = args.coco_conf
    coco_save_conf = args.coco_save_conf
    coco_min_frames = max(1, args.coco_min_frames)
    output_dir = Path(args.output_dir)
    snapshot_dir = output_dir / "snapshots"
    detections_file = output_dir / "detections.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    mqtt_client, mqtt_connected = init_mqtt_client(args)

    from ultralytics import YOLO

    model = YOLO(selected_model)

    enabled_objects = ["id_card"]
    save_conf_by_object = {"id_card": save_conf}
    min_frames_by_object = {"id_card": min_frames}
    coco_model = None
    coco_target_classes: List[str] = []

    if args.enable_coco:
        requested_classes = parse_coco_classes(args.coco_classes)
        coco_target_classes = [
            cls_name for cls_name in requested_classes if cls_name in SUPPORTED_COCO_CLASSES
        ]
        unsupported_classes = [
            cls_name for cls_name in requested_classes if cls_name not in SUPPORTED_COCO_CLASSES
        ]

        if unsupported_classes:
            print(f"Ignoring unsupported COCO classes: {', '.join(unsupported_classes)}")

        if not coco_target_classes:
            raise ValueError(
                "COCO mode enabled but no supported classes selected. "
                "Use --coco-classes bottle."
            )

        try:
            coco_model = YOLO(args.coco_model)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load COCO model '{args.coco_model}': {exc}"
            ) from exc

        for cls_name in coco_target_classes:
            enabled_objects.append(cls_name)
            save_conf_by_object[cls_name] = coco_save_conf
            min_frames_by_object[cls_name] = coco_min_frames

    cap = cv2.VideoCapture(selected_source)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {selected_source}")

    last_saved_at = {object_type: 0.0 for object_type in enabled_objects}

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
    print(f"COCO detection enabled: {'YES' if args.enable_coco else 'NO'}")
    if args.enable_coco:
        print(f"COCO model: {args.coco_model}")
        print(f"COCO target classes: {', '.join(coco_target_classes)}")
        print(f"COCO preview confidence (--coco-conf): {coco_conf}")
        print(f"COCO save confidence (--coco-save-conf): {coco_save_conf}")
        print(f"COCO minimum consecutive frames (--coco-min-frames): {coco_min_frames}")
    print(f"MQTT enabled: {'YES' if mqtt_connected else 'NO'}")
    if args.mqtt:
        print(
            f"MQTT config: host={args.mqtt_host} port={args.mqtt_port} "
            f"topic={args.mqtt_topic} robotId={args.robot_id}"
        )
    print(f"Display window: {'ON' if args.show else 'OFF'}")
    if args.show:
        print("Press q to quit.")

    state_by_object = {
        object_type: init_object_state() for object_type in enabled_objects
    }
    source_name = source_label(selected_source)

    try:
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Video finished.")
                    break

                frame_h, frame_w = frame.shape[:2]
                results = model.predict(frame, conf=preview_conf, verbose=False)

                frame_candidates: Set[str] = set()
                frame_best_candidates: Dict[str, Tuple[float, Any]] = {}

                for result in results:
                    process_candidates_for_object(
                        object_type="id_card",
                        boxes=result.boxes,
                        class_names=model.names,
                        frame=frame,
                        frame_w=frame_w,
                        frame_h=frame_h,
                        save_conf_threshold=save_conf_by_object["id_card"],
                        frame_candidates=frame_candidates,
                        frame_best_candidates=frame_best_candidates,
                    )

                if coco_model is not None:
                    coco_results = coco_model.predict(frame, conf=coco_conf, verbose=False)
                    for coco_result in coco_results:
                        for cls_name in coco_target_classes:
                            process_candidates_for_object(
                                object_type=cls_name,
                                boxes=coco_result.boxes,
                                class_names=coco_model.names,
                                frame=frame,
                                frame_w=frame_w,
                                frame_h=frame_h,
                                save_conf_threshold=save_conf_by_object[cls_name],
                                frame_candidates=frame_candidates,
                                frame_best_candidates=frame_best_candidates,
                            )

                now = time.time()
                for object_type in enabled_objects:
                    state = state_by_object[object_type]
                    best_candidate = frame_best_candidates.get(object_type)

                    if best_candidate is None:
                        state_by_object[object_type] = init_object_state()
                        continue

                    best_conf, best_frame = best_candidate
                    state["streak_count"] += 1

                    if best_conf > state["streak_best_conf"]:
                        state["streak_best_conf"] = best_conf
                        state["streak_best_frame"] = best_frame

                    cooldown_ready = now - last_saved_at[object_type] >= selected_cooldown
                    min_frames_required = min_frames_by_object[object_type]

                    if (
                        state["streak_count"] >= min_frames_required
                        and cooldown_ready
                        and (not state["streak_saved"])
                    ):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        snapshot_path = snapshot_dir / f"{object_type}_{timestamp}.jpg"

                        if state["streak_best_frame"] is not None:
                            cv2.imwrite(str(snapshot_path), state["streak_best_frame"])

                        record = create_detection_record(
                            object_type=object_type,
                            confidence=state["streak_best_conf"],
                            snapshot_path=snapshot_path,
                            source_name=source_name,
                        )

                        save_detection_record(record, detections_file)
                        last_saved_at[object_type] = now
                        state["streak_saved"] = True

                        print(
                            f"Saved detection: object={object_type} "
                            f"conf={record['confidence']:.4f} "
                            f"frames={state['streak_count']} "
                            f"time={record['detectedAt']} "
                            f"snapshot={record['snapshotPath']}"
                        )

                        mqtt_payload = build_mqtt_payload(record, args.robot_id)
                        publish_mqtt_event(mqtt_client, args.mqtt_topic, mqtt_payload)

                if frame_candidates:
                    candidate_text = ", ".join(sorted(frame_candidates))
                    cv2.putText(
                        frame,
                        f"CANDIDATE IN VIEW: {candidate_text}",
                        (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
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
        if mqtt_connected and mqtt_client is not None:
            try:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
            except Exception as exc:
                print(f"WARNING: MQTT disconnect error: {exc}")
        if args.show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped by user (Ctrl+C).")

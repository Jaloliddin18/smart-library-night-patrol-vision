# AGENTS.md

## 1. Project Purpose
This repository is the **같이Go Night Patrol Vision Module** for Smart Library lost-item detection.
Primary goal: during night patrol, detect `id_card`-like objects on the floor, log structured events, and preserve snapshots for morning staff review.
This module is for **night patrol lost-item logging**, not delivery obstacle stopping.

## 2. Architecture
- Phone mounted on TurtleBot: camera source.
- Mac or friend laptop: YOLO inference and vision logic (this repo).
- Raspberry Pi / robot controller: color-line navigation and motor control.
- MQTT (later): integration between vision module, robot controller, backend, and frontend/admin dashboard.
- Backend/admin flow (later): staff review and collection priority.

## 3. Current Model
- Known good model path: `runs/detect/train-4/weights/best.pt`
- Model family: YOLOv8n (trained locally)
- Current class scope: **one class only** -> `id_card`
- Validation was strong but dataset/validation size is limited, so do not over-trust score alone.

## 4. Python Environment
- Activate venv before running:
  `source .venv/bin/activate`
- Use existing local dependencies only (for example: `ultralytics`, `opencv-python`).
- Do not install packages unless explicitly requested.

## 5. Important Files
- Main script: `patrol_id_card_logger.py`
- Trained model: `runs/detect/train-4/weights/best.pt`
- Detection records: `detections/detections.json`
- Detection snapshots: `detections/snapshots/`
- Test videos:
  - `videos/id_card/`
  - `videos/empty_floor/`
  - `videos/random_object/`

## 6. Current Behavior
- Patrol logger reads a source, runs YOLO inference, and filters to `id_card` detections only.
- On allowed detection (cooldown satisfied), it:
  - saves a snapshot under `detections/snapshots/`
  - appends a structured event to `detections/detections.json`
- Cooldown reduces duplicate spam.
- Local testing baseline:
  - ID-card videos should detect.
  - Empty/random floor scenes should ideally have no false detections.

## 7. Testing Commands
Run from repo root after `source .venv/bin/activate`:

```bash
python patrol_id_card_logger.py --source videos/id_card/IMG_1640.MOV
python patrol_id_card_logger.py --source videos/empty_floor/IMG_1648.MOV
ls videos/random_object
python patrol_id_card_logger.py --source videos/random_object/<filename>.MOV
```

## 8. Event Record Shape
Detection records must remain compatible with this schema:

```json
{
  "eventType": "LOST_ITEM_DETECTED",
  "objectType": "id_card",
  "confidence": 0.95,
  "priority": "HIGH",
  "detectedAt": "ISO timestamp",
  "snapshotPath": "detections/snapshots/...",
  "location": {
    "source": "video_demo",
    "floorId": "floor_1",
    "x": null,
    "y": null,
    "patrolCheckpoint": null
  },
  "status": "PENDING_REVIEW",
  "notes": "ID-card-like object detected on the floor during patrol scan."
}
```

## 9. Rules for Codex
- Do not retrain unless explicitly asked.
- Do not delete existing outputs unless explicitly asked.
- Do not modify frontend/backend repos from this folder.
- Prefer CLI args over hardcoded source paths.
- Phone stream input should remain OpenCV `VideoCapture`-compatible.
- Add MQTT only when explicitly requested.
- Do not assume ROS2; robot navigation is color-line based.
- Do not read/store personal ID details; only detect ID-card-like object presence.
- Avoid noisy per-frame logs.

## 10. Future Roadmap
1. Refactor `patrol_id_card_logger.py` CLI interface:
   - `--source`
   - `--model`
   - `--conf`
   - `--cooldown`
   - `--output-dir`
   - optional display flag
2. Add phone stream source testing using OpenCV-compatible URL input.
3. Add MQTT event publishing layer after local detection logger is stable.
4. Integrate with backend/admin review flow for morning staff operations.

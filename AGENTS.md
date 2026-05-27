# AGENTS.md

## 1. Project Purpose
This repository is the **같이Go Night Patrol Vision Module** for Smart Library lost-item detection.
Primary goal: during night patrol, detect lost-item objects on the floor, log structured events, and preserve snapshots for morning staff review.
This module is for **night patrol lost-item logging**, not delivery obstacle stopping.

## 2. Architecture
- Phone mounted on TurtleBot: camera source.
- Mac or friend laptop: YOLO inference and vision logic (this repo).
- Raspberry Pi / robot controller: color-line navigation and motor control.
- MQTT (optional, CLI-enabled): vision module can publish saved lost-item events to a broker.
- Backend/admin flow (later): staff review and collection priority.

## 3. Current Model
- Known good model path: `runs/detect/gatigo-lost-items-v1/weights/best.pt`
- Model family: YOLOv8n fine-tuned from COCO-pretrained `yolov8n.pt` (Colab training)
- Current class scope:
  - custom model targets from `data.yaml`: `airpods`, `id_card`, `phone`, `wallet`, `watch`
  - logger supports custom classes: `id_card`, `wallet`, `phone`, `watch`, `airpods`
  - optional COCO fallback/demo mode: `bottle` behind `--enable-coco`
- Validation was strong but dataset/validation size is limited, so do not over-trust score alone.

## 4. Python Environment
- Activate venv before running:
  `source .venv/bin/activate`
- Use existing local dependencies only (for example: `ultralytics`, `opencv-python`).
- Do not install packages unless explicitly requested.

## 5. Important Files
- Main script: `patrol_id_card_logger.py`
- Trained model: `runs/detect/gatigo-lost-items-v1/weights/best.pt`
- Detection records: `detections/detections.json`
- Detection snapshots: `detections/snapshots/`
- Test videos:
  - `videos/lost_items/watch/`
  - `videos/lost_items/phone/`
  - `videos/lost_items/wallet/`
  - `videos/lost_items/airpods/`
  - `videos/id_card/`
  - `videos/lost_items/negative/`

## 6. Current Behavior
- Patrol logger reads a source (video/camera/stream), runs YOLO inference, and tracks:
  - `id_card`
  - `wallet`
  - `phone`
  - `watch`
  - `airpods`
- Optional COCO `bottle` tracking is available behind `--enable-coco`.
- On allowed detection (cooldown satisfied), it:
  - saves a snapshot under `detections/snapshots/`
  - appends a structured event to `detections/detections.json`
- Save gating uses:
  - preview threshold: `--conf`
  - save threshold: `--save-conf`
  - consecutive-frame threshold: `--min-frames`
  - edge rejection
  - cooldown
- Cooldown and streak tracking are per object type (not global).
- Optional MQTT publish (only when `--mqtt` is enabled):
  - publishes the same saved event to configured topic
  - publish happens only after local save succeeds
  - MQTT failures must not crash local logging

## 7. Testing Commands
Run from repo root after `source .venv/bin/activate`:

```bash
python -m py_compile patrol_id_card_logger.py
python patrol_id_card_logger.py --help

python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/lost_items/watch/IMG_1671.MOV --conf 0.5 --save-conf 0.7 --min-frames 3
python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/lost_items/phone/IMG_1679.MOV --conf 0.5 --save-conf 0.7 --min-frames 3
python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/lost_items/wallet/IMG_1675.MOV --conf 0.5 --save-conf 0.7 --min-frames 3
python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/lost_items/airpods/IMG_1668.MOV --conf 0.5 --save-conf 0.7 --min-frames 3
python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/id_card/IMG_1640.MOV --conf 0.5 --save-conf 0.7 --min-frames 3

python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/lost_items/watch/IMG_1671.MOV --upload-snapshot --backend-url http://localhost:3007/graphql --admin-token-file admin_jwt.txt --mqtt --mqtt-host localhost --mqtt-port 1883 --mqtt-topic robot/robot_01/lost-item --robot-id robot_01 --conf 0.5 --save-conf 0.7 --min-frames 3
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

Notes:
- Local `detections/detections.json` keeps YOLO class labels in lowercase (`objectType`).
- MQTT payload keeps `objectType` in lowercase class form:
  - `id_card`, `wallet`, `phone`, `watch`, `airpods` (and `bottle` when COCO mode is used)
- MQTT payload also includes lowercase `detectedClass`.

Sample MQTT lost-item event:

```json
{
  "robotId": "robot_01",
  "mode": "NIGHT_PATROL",
  "objectType": "watch",
  "detectedClass": "watch",
  "confidence": 0.86,
  "snapshotUrl": "uploads/lost-items/example-watch.jpg",
  "location": {
    "floorId": "floor_1",
    "x": 3.2,
    "y": 4.8,
    "theta": 90
  }
}
```

## 9. Rules for Codex
- Do not retrain unless explicitly asked.
- Do not delete existing outputs unless explicitly asked.
- Do not modify frontend/backend repos from this folder.
- Prefer CLI args over hardcoded source paths.
- Phone stream input should remain OpenCV `VideoCapture`-compatible.
- MQTT is optional and must remain disabled unless `--mqtt` is passed.
- Do not assume ROS2; robot navigation is color-line based.
- Do not read/store personal ID details; only detect ID-card-like object presence.
- Avoid noisy per-frame logs.

## 10. Future Roadmap
1. Verify live upload + MQTT path against running localhost backend (`:3007`) and broker (`:1883`) outside sandbox constraints.
2. Add repeatable regression command set for all five custom classes plus negative scenes.
3. Add phone stream source testing using OpenCV-compatible URL input.
4. Integrate with backend/admin review flow for morning staff operations.
5. AirPods + watch dataset collection guidance for future training refresh:
   - collect both AirPods case and AirPods images
   - include white AirPods on bright floors/tables
   - include AirPods case open and closed
   - include multiple distances from TurtleBot camera angle
   - include partial occlusion near chair/table/shelf
   - avoid only clean close-up photos
   - include smartwatches and normal watches if both are intended
   - include black watches on dark floors/tables
   - include watches with straps open and closed
   - include side angles, top angles, and partial occlusion
   - include different distances from TurtleBot camera angle

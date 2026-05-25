# MEMORY.md

## 1. Current State
ID-card detection prototype is working in this local Python/YOLO module for 같이Go Smart Library night patrol.

Completed work:
- Videos collected for:
  - `videos/id_card`
  - `videos/empty_floor`
  - `videos/random_object`
- Frames extracted with FFmpeg.
- ID-card images labeled in Roboflow.
- YOLOv8 dataset exported.
- YOLOv8 local training completed on Mac (v1 baseline).
- v1 baseline model at `runs/detect/train-4/weights/best.pt` produced one false positive:
  - `videos/random_object/IMG_1656.MOV`
  - watch detected as `id_card` with confidence around `0.7578`
- Random object/watch hard-negative (null) examples were added in Roboflow.
- Dataset v2 was generated and retrained on Google Colab (Tesla T4 GPU).
- New v2 model saved locally at `runs/detect/train-v2/weights/best.pt`.
- ID-card video detection works.
- Empty-floor videos showed no false detections in baseline tests.
- v2 fixed the known watch/random-object false positive on `IMG_1656.MOV`.
- Patrol logger saves snapshots and appends structured records to `detections/detections.json`.
- `patrol_id_card_logger.py` reliability improvements were added:
  - `--conf` remains preview threshold.
  - Added `--save-conf` (default `0.75`) for report save threshold.
  - Added `--min-frames` (default `3`) for consecutive-frame validation.
  - Save now requires all of:
    1. class is `id_card`
    2. confidence `>= save_conf`
    3. at least `min_frames` consecutive detections
    4. bounding box does not touch frame border within `5%` margin
  - Snapshot save now uses the best-confidence frame from a valid detection streak.
  - Default model path in logger is now `runs/detect/train-v2/weights/best.pt`.
  - Ctrl+C now exits cleanly without large traceback.
- Optional COCO bottle detection is now available behind `--enable-coco`:
  - COCO model path/name: `yolov8n.pt`
  - COCO preview threshold: `--coco-conf` (default `0.5`)
  - COCO save threshold: `--coco-save-conf` (default `0.6`)
  - COCO consecutive-frame rule: `--coco-min-frames` (default `3`)
  - Bottle events use `priority: LOW`
  - Bottle saves follow the same reliability gates (save-conf, min-frames, edge filter, best-frame snapshot).
  - Live testing indicates bottle detection is workable when the bottle is upright and clearly visible.
  - Lying-down bottles or unusual viewing angles are currently unreliable with the COCO pretrained baseline.

## 2. Important Architecture Decision
- Phone mounted on TurtleBot is camera input.
- Mac/friend laptop is YOLO inference brain.
- Raspberry Pi handles movement and color-line navigation only.
- Raspberry Pi should not run heavy YOLO inference due limited RAM.
- MQTT optional publish path from vision module is implemented behind `--mqtt`.
- Full MQTT integration with robot/controller/backend/frontend flow is still a later step.
- Backend/admin review is for morning staff collection workflow.

## 3. Current Next Task
1. Install `paho-mqtt` in `.venv` and run live broker/subscriber verification for published events.
2. Validate optional COCO bottle MQTT publish with a stable bottle source.

## 4. Known Good Model Path
- Current preferred model: `runs/detect/train-v2/weights/best.pt`
- Main reliable detector remains the custom `id_card` model at `runs/detect/train-v2/weights/best.pt`.
- COCO pretrained model used for bottle mode: `yolov8n.pt`
- Keep `runs/detect/train-4/weights/best.pt` only as historical reference.

## 5. Known Good Test Results
- Latest reliability test on random object/watch (`IMG_1656.MOV`): no detection saved.
- Latest reliability test on ID-card video (`IMG_1640.MOV`): detection saved with confidence `0.9737`.
- Snapshot saved during latest ID-card test: `id_card_20260525_214028.jpg`.
- COCO-enabled run on `videos/random_object/IMG_1656.MOV` completed without crash using `yolov8n.pt`.
- Live bottle testing: upright/clear bottles can be detected and logged, but lying/angled bottles are inconsistent.
- Patrol logger currently outputs:
  - snapshots to `detections/snapshots/`
  - event logs to `detections/detections.json`

## 6. Known Good Test Commands
```bash
source .venv/bin/activate
python patrol_id_card_logger.py --model runs/detect/train-v2/weights/best.pt --source videos/random_object/IMG_1656.MOV --conf 0.5 --save-conf 0.75 --min-frames 3 --cooldown 30
python patrol_id_card_logger.py --model runs/detect/train-v2/weights/best.pt --source videos/id_card/IMG_1640.MOV --conf 0.5 --save-conf 0.75 --min-frames 3 --cooldown 30
python patrol_id_card_logger.py --model runs/detect/train-v2/weights/best.pt --source videos/random_object/IMG_1656.MOV --enable-coco --coco-classes bottle --coco-conf 0.5 --coco-save-conf 0.6 --coco-min-frames 3 --cooldown 30
```

## 7. Important Notes
- Current purpose is night patrol lost-item logging, not delivery obstacle stopping.
- Custom model class remains one class: `id_card` (plus optional COCO `bottle` behind `--enable-coco`).
- Treat bottle detection as an optional baseline demo feature, not the main reliable detector.
- Do not spend more time on custom bottle training unless explicitly requested.
- Do not label the whole floor as `id_card`; keep bounding boxes tight around ID-card-like objects.
- Edge-touching boxes (within 5% border margin) are preview-only and must not be saved as patrol reports.
- Do not retrain, delete outputs, or add MQTT/backend integration unless explicitly requested.

## 8. MQTT Integration (2026-05-25)
- `patrol_id_card_logger.py` now supports optional MQTT publishing for saved `LOST_ITEM_DETECTED` events.
- Local JSON/snapshot saving remains the primary path and is unchanged.
- MQTT publish is additional and only triggers after a detection passes save gating and is saved locally.
- New CLI args:
  - `--mqtt`
  - `--mqtt-host` (default `localhost`)
  - `--mqtt-port` (default `1883`)
  - `--mqtt-topic` (default `robot/robot_01/lost-item`)
  - `--robot-id` (default `robot_01`)
  - `--mqtt-username` (optional)
  - `--mqtt-password` (optional)
- MQTT payload uses saved event fields plus `robotId`, for example:
  - `eventType`, `robotId`, `objectType`, `confidence`, `priority`, `detectedAt`,
    `snapshotPath`, `location`, `status`, `notes`
- Dependency status:
  - `paho-mqtt` is currently missing in `.venv`.
  - Install command: `.venv/bin/pip install paho-mqtt`
- Failure behavior:
  - If MQTT dependency, connect, or publish fails, logger prints a warning and continues local logging.
  - No per-frame MQTT spam logs were added.
- Validation run:
  - `.venv/bin/python -m py_compile patrol_id_card_logger.py` passed.
  - `.venv/bin/python patrol_id_card_logger.py --help` shows all new MQTT args.
  - Non-MQTT run still saved local event successfully.
  - MQTT-enabled run (without `paho-mqtt`) warned once and still saved local event successfully.

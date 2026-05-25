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

## 2. Important Architecture Decision
- Phone mounted on TurtleBot is camera input.
- Mac/friend laptop is YOLO inference brain.
- Raspberry Pi handles movement and color-line navigation only.
- Raspberry Pi should not run heavy YOLO inference due limited RAM.
- MQTT will connect vision module, robot controller, backend, and frontend later.
- Backend/admin review is for morning staff collection workflow.

## 3. Current Next Task
1. Phone camera stream testing using OpenCV-compatible source URL.
2. MQTT publishing for `LOST_ITEM_DETECTED` events after stream testing is stable.

## 4. Known Good Model Path
- Current preferred model: `runs/detect/train-v2/weights/best.pt`
- Keep `runs/detect/train-4/weights/best.pt` only as historical reference.

## 5. Known Good Test Results
- v2 on random object (`IMG_1656.MOV`): no detection saved (false positive fixed).
- v2 on ID-card video (`IMG_1640.MOV`): detection saved with confidence `0.9679`.
- Snapshot saved during v2 ID-card test: `id_card_20260525_201604.jpg`.
- Patrol logger currently outputs:
  - snapshots to `detections/snapshots/`
  - event logs to `detections/detections.json`

## 6. Known Good Test Commands
```bash
source .venv/bin/activate
python patrol_id_card_logger.py --model runs/detect/train-v2/weights/best.pt --source videos/random_object/IMG_1656.MOV --conf 0.5 --cooldown 30
python patrol_id_card_logger.py --model runs/detect/train-v2/weights/best.pt --source videos/id_card/IMG_1640.MOV --conf 0.5 --cooldown 30
```

## 7. Important Notes
- Current purpose is night patrol lost-item logging, not delivery obstacle stopping.
- Keep class count at one class for now: `id_card`.
- Do not label the whole floor as `id_card`; keep bounding boxes tight around ID-card-like objects.
- Do not retrain, delete outputs, or add MQTT/backend integration unless explicitly requested.

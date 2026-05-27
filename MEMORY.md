# MEMORY.md

## 1. Current State
This local Python/YOLO module is now running with a multi-class lost-item detector for night patrol logging.

Current stable behavior:
- Default model path in `patrol_id_card_logger.py`:
  - `runs/detect/gatigo-lost-items-v1/weights/best.pt`
- Custom model classes supported by logger:
  - `id_card`
  - `wallet`
  - `phone`
  - `watch`
  - `airpods`
- Optional COCO fallback mode remains available for:
  - `bottle` behind `--enable-coco`
- Save path remains:
  - snapshot: `detections/snapshots/*.jpg`
  - JSON log: `detections/detections.json`
- Save gating remains:
  - preview threshold: `--conf`
  - save threshold: `--save-conf`
  - consecutive-frame threshold: `--min-frames`
  - edge filter (5% border rejection)
  - cooldown
- Cooldown and streak tracking are per object type (not global).

## 2. Object and Priority Rules
Current record mapping in logger:
- `id_card`:
  - `priority: HIGH`
  - notes: `ID-card-like object detected on the floor during patrol scan.`
- `wallet`:
  - `priority: HIGH`
  - notes: `Wallet-like object detected on the floor during patrol scan.`
- `phone`:
  - `priority: HIGH`
  - notes: `Phone-like object detected on the floor during patrol scan.`
- `watch`:
  - `priority: MEDIUM`
  - notes: `Watch-like object detected on the floor during patrol scan.`
- `airpods`:
  - `priority: MEDIUM`
  - notes: `AirPods-like object detected on the floor during patrol scan.`
- `bottle` (optional COCO mode):
  - `priority: LOW`
  - notes: `Bottle-like object detected on the floor during patrol scan.`

## 3. MQTT and Upload Behavior
- MQTT publish is optional (`--mqtt`) and save-gated.
- Upload is optional (`--upload-snapshot`) and save-gated.
- Upload and MQTT failures must not stop local save/logging.
- MQTT payload uses lower-case `objectType` values:
  - `id_card`, `wallet`, `phone`, `watch`, `airpods`, `bottle`
- MQTT payload also includes:
  - `mode: NIGHT_PATROL`
  - `detectedClass` (lower-case class label)
- `snapshotUrl` is included when upload succeeds; remains `null` when upload fails.

## 4. Known Good Model Paths
- Current preferred model:
  - `runs/detect/gatigo-lost-items-v1/weights/best.pt`
- Historical custom model:
  - `runs/detect/train-v2/weights/best.pt`
- Historical baseline:
  - `runs/detect/train-4/weights/best.pt`
- COCO fallback model:
  - `yolov8n.pt`

## 5. Session Update (2026-05-28)
Session scope:
- Updated only:
  - `patrol_id_card_logger.py`
  - `AGENTS.md`
  - `MEMORY.md`

Code changes completed:
- Default `--model` changed to:
  - `runs/detect/gatigo-lost-items-v1/weights/best.pt`
- Custom model target class list aligned to 5-class model:
  - `id_card`, `wallet`, `phone`, `watch`, `airpods`
- Priority mapping updated:
  - `watch`: `HIGH -> MEDIUM`
  - `airpods`: `HIGH -> MEDIUM`
- MQTT `objectType` mapping changed from uppercase backend enum to lower-case class names.
- Optional COCO `bottle` mode kept intact.

Validation completed:
- Syntax check:
  - `.venv/bin/python -m py_compile patrol_id_card_logger.py` passed
- Help check:
  - `.venv/bin/python patrol_id_card_logger.py --help` passed
- Class video checks passed (non-`--show` runs in current environment):
  - watch: `videos/lost_items/watch/IMG_1671.MOV` -> saved `watch`
  - phone: `videos/lost_items/phone/IMG_1679.MOV` -> saved `phone`
  - wallet: `videos/lost_items/wallet/IMG_1675.MOV` -> saved `wallet`
  - airpods: `videos/lost_items/airpods/IMG_1668.MOV` -> saved `airpods`
  - id_card sanity run: `videos/id_card/IMG_1640.MOV` -> saved `id_card`
- COCO compatibility check:
  - `--enable-coco --coco-classes bottle` run completed without breaking custom-class flow
- Upload + MQTT integration run:
  - code path executed correctly
  - local services were unavailable during validation (`localhost:3007` and `localhost:1883` connection refused), so local-only fallback behavior was observed

## 6. Known Good Test Commands
```bash
source .venv/bin/activate
python -m py_compile patrol_id_card_logger.py
python patrol_id_card_logger.py --help

python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/lost_items/watch/IMG_1671.MOV --conf 0.5 --save-conf 0.7 --min-frames 3
python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/lost_items/phone/IMG_1679.MOV --conf 0.5 --save-conf 0.7 --min-frames 3
python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/lost_items/wallet/IMG_1675.MOV --conf 0.5 --save-conf 0.7 --min-frames 3
python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/lost_items/airpods/IMG_1668.MOV --conf 0.5 --save-conf 0.7 --min-frames 3
python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/id_card/IMG_1640.MOV --conf 0.5 --save-conf 0.7 --min-frames 3

python patrol_id_card_logger.py --model runs/detect/gatigo-lost-items-v1/weights/best.pt --source videos/lost_items/watch/IMG_1671.MOV --upload-snapshot --backend-url http://localhost:3007/graphql --admin-token-file admin_jwt.txt --mqtt --mqtt-host localhost --mqtt-port 1883 --mqtt-topic robot/robot_01/lost-item --robot-id robot_01 --conf 0.5 --save-conf 0.7 --min-frames 3
```

## 7. Important Notes
- Keep this repo scoped to the local Python vision module only.
- Do not modify backend/frontend repos from this folder.
- Do not retrain unless explicitly requested.
- Do not delete existing outputs unless explicitly requested.
- Keep `admin_jwt.txt` local-only and never commit tokens.
- `--show` may be environment-dependent (headless runs may not display windows reliably).

## 8. Next Task
1. Validate upload + MQTT end-to-end against running local backend/broker outside sandbox/network limits.
2. Continue Phase 5 planning for admin morning-review dashboard integration.

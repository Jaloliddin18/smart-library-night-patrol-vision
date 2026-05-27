# 같이Go Night Patrol Vision Module

This module runs YOLO-based lost-item detection for TurtleBot night patrol and can publish detection events to backend via MQTT.

## Current Lost-Item Classes

Keep class indexes aligned across dataset config, training, and inference:

```yaml
names:
  0: id_card
  1: wallet
  2: phone
  3: bottle
  4: airpods
  5: watch
```

## Backend Enum Mapping

YOLO class labels remain lowercase. MQTT/backend `objectType` must use uppercase enum values:

```json
{
  "id_card": "ID_CARD",
  "wallet": "WALLET",
  "phone": "PHONE",
  "bottle": "BOTTLE",
  "airpods": "AIRPODS",
  "watch": "WATCH"
}
```

## Sample MQTT Lost-Item Event

```json
{
  "robotId": "robot_01",
  "mode": "NIGHT_PATROL",
  "objectType": "WATCH",
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

## Training Data Guidance (AirPods + Watch)

- Collect both AirPods case and individual AirPods examples.
- Include white AirPods on bright floors/tables.
- Include open and closed AirPods case states.
- Capture at different distances and angles from TurtleBot camera perspective.
- Include partial occlusion near chair/table/shelf areas.
- Avoid building the dataset from only clean close-up photos.
- Include smartwatches and normal watches if both are intended.
- Include black watches on dark floors/tables.
- Include watches with straps open and closed.
- Include side angles, top angles, and partial occlusion.
- Include different distances from the TurtleBot camera angle.

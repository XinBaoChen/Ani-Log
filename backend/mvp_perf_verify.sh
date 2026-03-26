#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8010}"

start_payload='{"title":"MVP Perf Verification","fps":6,"source":"screen","performance_mode":true,"adaptive_keyframes":true}'

sid=$(curl -sS -X POST "${BASE_URL}/api/capture/start" \
  -H "Content-Type: application/json" \
  -d "${start_payload}" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

sleep 120

curl -sS -X POST "${BASE_URL}/api/capture/stop" >/dev/null

session_json=$(curl -sS "${BASE_URL}/api/sessions/${sid}")
scenes_json=$(curl -sS "${BASE_URL}/api/sessions/${sid}/scenes")
chars_json=$(curl -sS "${BASE_URL}/api/characters?sort_by=appearance_count&limit=200")

python3 - <<'PY' "$sid" "$session_json" "$scenes_json" "$chars_json"
import json
import sys
from datetime import datetime

sid = sys.argv[1]
session = json.loads(sys.argv[2])
scenes = json.loads(sys.argv[3])
chars = json.loads(sys.argv[4])

start = datetime.fromisoformat(session["started_at"]) 
end = datetime.fromisoformat(session["ended_at"]) if session.get("ended_at") else start
runtime = max(1.0, (end - start).total_seconds())
frames = int(session.get("total_frames", 0))
effective_fps = frames / runtime
scene_rows = len(scenes)

auto_chars = [c for c in chars if str(c.get("name", "")).startswith("Detected Character")]
unique_auto_names = {c.get("name") for c in auto_chars}
dup_name_count = max(0, len(auto_chars) - len(unique_auto_names))
persistent_chars = sum(1 for c in chars if int(c.get("appearance_count", 0)) >= 3)

print(f"SID={sid}")
print(f"RuntimeSec={runtime:.1f}; Frames={frames}; SceneRows={scene_rows}; EffectiveFPS={effective_fps:.2f}")
print(f"AutoChars={len(auto_chars)}; AutoNameDuplicates={dup_name_count}; PersistentChars(appearance>=3)={persistent_chars}")
PY

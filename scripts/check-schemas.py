#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
expected={
  "worker-handoff.schema.json": ["schema","worker","task","source","target","project_root","constraints"],
  "worker-result.schema.json": ["schema","worker","status","summary","files_changed","commands_run","unresolved","evidence","dependency_changes"],
  "adapter-manifest.schema.json": ["schema","name","version","capabilities","task_types","risk_profile","evidence_requirements","command"],
  "evidence.schema.json": ["id","time","claim","source","status","confidence","provider","verification_method","details"]
}
for name, required in expected.items():
    p=ROOT/"schemas"/name
    obj=json.loads(p.read_text(encoding="utf-8"))
    if obj.get("type")!="object" or any(k not in obj.get("required",[]) for k in required):
        raise SystemExit(f"schema contract failed: {name}")
    if name == "adapter-manifest.schema.json":
        alternatives=obj.get("anyOf",[])
        if not any(set(x.get("required",[])) >= {"supported_loaders","supported_minecraft_versions"} for x in alternatives if isinstance(x,dict)):
            raise SystemExit("schema contract failed: adapter-manifest.schema.json missing Minecraft scope alternative")
        if not any(set(x.get("required",[])) >= {"supported_platforms","supported_versions"} for x in alternatives if isinstance(x,dict)):
            raise SystemExit("schema contract failed: adapter-manifest.schema.json missing generic scope alternative")
print(f"JSON schemas: PASS ({len(expected)})")

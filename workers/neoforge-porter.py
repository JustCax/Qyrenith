#!/usr/bin/env python3
"""Bounded NeoForge metadata porter for the public golden benchmark.

This is intentionally narrow: it migrates a known, verified NeoForge pair
(1.21/21.0.167 -> 1.21.1/21.1.235) and refuses unknown mappings.
It never reports Doctor verification.
"""
import json, re, sys
from pathlib import Path

MIGRATIONS = {
    ("1.21", "1.21.1"): {"source_neo": "21.0.167", "target_neo": "21.1.235"},
}

def read_props(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    return values

def replace_prop(text, key, value):
    pat = re.compile(r"(?m)^" + re.escape(key) + r"=.*$")
    new, count = pat.subn(f"{key}={value}", text)
    if count != 1:
        raise ValueError(f"expected exactly one {key} property")
    return new

def main():
    req = json.load(sys.stdin)
    op = req.get("operation", "result")
    root = Path(req.get("project_root", ".")).resolve()
    if op == "discover":
        return {"schema":1,"worker":"neoforge-porter","version":"1.0.0","capabilities":["inspect","plan","port"],"status":"AVAILABLE"}
    props_path = root / "gradle.properties"
    if not props_path.is_file():
        return {"schema":1,"worker":"neoforge-porter","status":"BLOCKED","summary":"Required project input is missing.","files_changed":[],"commands_run":[],"evidence":[],"dependency_changes":[],"verified_by_doctor":False,"unresolved":["gradle.properties missing"]}
    props = read_props(props_path)
    task = req.get("task", "")
    m = re.fullmatch(r"port\s+([0-9.]+)\s*->\s*([0-9.]+)", task.strip())
    if not m:
        return {"schema":1,"worker":"neoforge-porter","status":"BLOCKED","summary":"Task format is not supported.","files_changed":[],"commands_run":[],"evidence":[],"dependency_changes":[],"verified_by_doctor":False,"unresolved":["Task must be 'port SOURCE -> TARGET'"]}
    source, target = m.groups()
    mapping = MIGRATIONS.get((source, target))
    if not mapping:
        return {"schema":1,"worker":"neoforge-porter","status":"BLOCKED","summary":"No verified mapping exists for the requested transition.","files_changed":[],"commands_run":[],"evidence":[],"dependency_changes":[],"verified_by_doctor":False,"unresolved":[f"No verified NeoForge mapping for {source} -> {target}"]}
    if props.get("minecraft_version") != source or props.get("neo_version") != mapping["source_neo"]:
        return {"schema":1,"worker":"neoforge-porter","status":"BLOCKED","summary":"Source project does not match the verified migration baseline.","files_changed":[],"commands_run":[],"evidence":[],"dependency_changes":[],"verified_by_doctor":False,"unresolved":["Source project does not match the verified migration baseline"]}
    if op == "inspect":
        return {"schema":1,"worker":"neoforge-porter","status":"OBSERVED","source_minecraft":source,"source_neo":mapping["source_neo"],"target_minecraft":target,"target_neo":mapping["target_neo"],"verified_by_doctor":False}
    if op == "plan":
        return {"schema":1,"worker":"neoforge-porter","status":"PLANNED","steps":["update minecraft_version","update minecraft_version_range","update neo_version"],"verified_by_doctor":False}
    text = props_path.read_text(encoding="utf-8")
    text = replace_prop(text, "minecraft_version", target)
    text = replace_prop(text, "minecraft_version_range", f"[{target}]")
    text = replace_prop(text, "neo_version", mapping["target_neo"])
    props_path.write_text(text, encoding="utf-8")
    return {"schema":1,"worker":"neoforge-porter","status":"WORKED","summary":"Updated only the verified version properties.","files_changed":["gradle.properties"],"commands_run":[],"evidence":["verified NeoForge mapping"],"dependency_changes":[],"source_minecraft":source,"target_minecraft":target,"target_neo":mapping["target_neo"],"verified_by_doctor":False,"unresolved":["Build and Doctor verification still required"]}

if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False))

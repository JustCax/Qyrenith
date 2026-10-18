#!/usr/bin/env python3
"""Minimal external worker demonstrating the Qyrenith worker protocol.

The worker is intentionally conservative: it inspects a handoff and returns
structured WORKED/NOT_SUPPORTED results. It never claims Doctor verification.
"""
import json, sys

def main():
    request = json.load(sys.stdin)
    op = request.get("operation", "result")
    if op == "discover":
        return {"schema":1,"worker":"example-worker","version":"1.0.0","capabilities":["inspect","plan","result"],"status":"AVAILABLE"}
    if op == "inspect":
        return {"schema":1,"worker":"example-worker","status":"OBSERVED","project_root":request.get("project_root"),"claims":["worker protocol reachable"]}
    if op == "plan":
        return {"schema":1,"worker":"example-worker","status":"PLANNED","steps":[{"action":"inspect-only","reason":"demonstration worker"}]}
    return {"schema":1,"worker":"example-worker","status":"WORKED","summary":"Worker completed its bounded demonstration task.","files_changed":[],"commands_run":[],"evidence":[],"dependency_changes":[],"unresolved":["Doctor verification still required"],"verified_by_doctor":False}

if __name__ == '__main__':
    print(json.dumps(main(), ensure_ascii=False))

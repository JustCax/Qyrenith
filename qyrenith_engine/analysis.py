"""Static Python source analysis; project code is never imported or executed."""
from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Set, Union

_EXCLUDED = {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist", ".qyrenith"}


def _read_source(path: Path, root: Path, max_file_bytes: int) -> tuple[bytes, str]:
    """Read once so the recorded digest and parsed source refer to identical bytes."""
    if path.is_symlink():
        raise OSError("symlink encountered during source read")
    resolved = path.resolve(strict=True)
    resolved.relative_to(root)
    with path.open("rb") as stream:
        raw = stream.read(max_file_bytes + 1)
    if len(raw) > max_file_bytes:
        raise OverflowError("file_size_limit")
    return raw, hashlib.sha256(raw).hexdigest()


def analyze_project(project: Union[str, Path], *, max_files: int = 10000,
                    max_file_bytes: int = 2_000_000,
                    max_entries: int = 50000) -> Dict[str, Any]:
    """Inventory Python files and extract syntax, imports, symbols, and review hints."""
    if min(max_files, max_file_bytes, max_entries) < 1:
        raise ValueError("analysis limits must be positive")
    root = Path(project).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project root must be a directory")

    records: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []
    errors: List[Dict[str, str]] = []
    entries_seen = 0
    files_seen = 0
    pending = [root]

    while pending:
        directory = pending.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            errors.append({"path": directory.relative_to(root).as_posix(),
                           "reason": type(exc).__name__})
            continue

        child_directories = []
        for entry in entries:
            relative = Path(entry.path).relative_to(root)
            if any(part in _EXCLUDED for part in relative.parts):
                continue
            entries_seen += 1
            if entries_seen > max_entries:
                return {"schema": 1, "status": "BLOCKED", "reason": "max_entries limit exceeded",
                        "files": records, "skipped": skipped, "errors": errors,
                        "entries_seen": entries_seen - 1, "files_seen": files_seen}
            try:
                if entry.is_symlink():
                    reason = "symlink_directory" if entry.is_dir(follow_symlinks=True) else "symlink"
                    if relative.suffix == ".py" or reason == "symlink_directory":
                        skipped.append({"path": relative.as_posix(), "reason": reason})
                    continue
                if entry.is_dir(follow_symlinks=False):
                    child_directories.append(Path(entry.path))
                    continue
                if not entry.is_file(follow_symlinks=False) or Path(entry.name).suffix != ".py":
                    continue
            except OSError as exc:
                errors.append({"path": relative.as_posix(), "reason": type(exc).__name__})
                continue

            files_seen += 1
            if files_seen > max_files:
                return {"schema": 1, "status": "BLOCKED", "reason": "max_files limit exceeded",
                        "files": records, "skipped": skipped, "errors": errors,
                        "entries_seen": entries_seen, "files_seen": files_seen - 1}
            try:
                raw, digest = _read_source(Path(entry.path), root, max_file_bytes)
            except OverflowError:
                skipped.append({"path": relative.as_posix(), "reason": "file_size_limit"})
                continue
            except (OSError, ValueError) as exc:
                skipped.append({"path": relative.as_posix(), "reason": type(exc).__name__})
                continue

            common = {"path": relative.as_posix(), "sha256": digest, "bytes": len(raw)}
            try:
                source = raw.decode("utf-8")
            except UnicodeDecodeError:
                records.append({**common, "syntax": "UNKNOWN", "imports": [], "symbols": [],
                                "findings": [{"code": "PY003", "severity": "review",
                                              "message": "File is not UTF-8; parsing was skipped."}]})
                continue
            try:
                tree = ast.parse(source, filename=relative.as_posix())
            except SyntaxError as exc:
                records.append({**common, "syntax": "FAIL", "imports": [], "symbols": [],
                                "findings": [{"code": "PY000", "severity": "error", "line": exc.lineno,
                                              "message": exc.msg}]})
                continue

            imports: Set[str] = set()
            symbols: List[Dict[str, Any]] = []
            findings: List[Dict[str, Any]] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)
                    if node.level == 0:
                        imports.update(node.module + "." + alias.name for alias in node.names if alias.name != "*")
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.append({"name": node.name, "kind": type(node).__name__, "line": node.lineno})
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                    findings.append({"code": "PY001" if node.func.id == "eval" else "PY002",
                                     "severity": "review", "line": node.lineno,
                                     "message": "Dynamic %s call requires manual review." % node.func.id})
            records.append({**common, "syntax": "PASS", "imports": sorted(imports),
                            "symbols": sorted(symbols, key=lambda item: (item["name"], item["line"])),
                            "findings": sorted(findings, key=lambda item: (item["line"], item["code"]))})

        pending.extend(reversed(child_directories))

    records.sort(key=lambda item: item["path"])
    skipped.sort(key=lambda item: item["path"])
    errors.sort(key=lambda item: item["path"])
    failures = sum(record["syntax"] == "FAIL" for record in records)
    unknown = sum(record["syntax"] == "UNKNOWN" for record in records)
    status = "FAIL" if failures else (
        "BLOCKED" if unknown or skipped or errors else ("PASS" if records else "UNKNOWN"))
    return {"schema": 1, "status": status, "project": str(root), "files_analyzed": len(records),
            "files_seen": files_seen, "entries_seen": entries_seen,
            "syntax_failures": failures, "unknown_files": unknown, "files": records,
            "skipped": skipped, "errors": errors, "execution_performed": False,
            "limitations": ["Static AST analysis only.",
                           "Relative imports, dynamic imports, and runtime behavior are not fully resolved.",
                           "Filesystem changes during discovery may cause an incomplete inventory."]}


def compare_baselines(previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """Compare validated source-analysis snapshots without claiming behavioral equivalence."""
    for label, report in (("previous", previous), ("current", current)):
        if not isinstance(report, dict) or report.get("schema") != 1 or not isinstance(report.get("files"), list):
            return {"schema": 1, "status": "UNKNOWN", "reason": label + " baseline has an unsupported schema"}
        seen: Set[str] = set()
        for item in report["files"]:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                return {"schema": 1, "status": "UNKNOWN", "reason": label + " baseline contains an invalid file record"}
            if item["path"] in seen:
                return {"schema": 1, "status": "UNKNOWN", "reason": label + " baseline contains duplicate paths"}
            seen.add(item["path"])
            if not isinstance(item.get("sha256"), str) or item.get("syntax") not in {"PASS", "FAIL", "UNKNOWN"}:
                return {"schema": 1, "status": "UNKNOWN", "reason": label + " baseline contains incomplete evidence"}
    old = {item["path"]: item for item in previous["files"]}
    new = {item["path"]: item for item in current["files"]}
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(path for path in old.keys() & new.keys()
                     if old[path]["sha256"] != new[path]["sha256"])
    regressions = sorted(path for path in old.keys() & new.keys()
                         if old[path]["syntax"] == "PASS" and new[path]["syntax"] == "FAIL")
    current_failures = sorted(path for path, item in new.items() if item["syntax"] == "FAIL")
    current_unknown = sorted(path for path, item in new.items() if item["syntax"] == "UNKNOWN")
    status = "FAIL" if current_failures else (
        "UNKNOWN" if current_unknown or current.get("status") != "PASS" else "PASS")
    return {"schema": 1, "status": status, "added": added, "removed": removed,
            "changed": changed, "syntax_regressions": regressions,
            "current_syntax_failures": current_failures, "current_unknown_files": current_unknown,
            "claim": "Content and syntax delta only; not proof of behavioral regression."}


def build_change_impact(project: Union[str, Path], changed_paths: List[str]) -> Dict[str, Any]:
    """Return direct/transitive importers from a conservative static Python import graph."""
    if not changed_paths:
        return {"schema": 1, "status": "UNKNOWN", "reason": "No changed paths were supplied.", "affected": []}
    report = analyze_project(project)
    if report["status"] in {"BLOCKED", "FAIL", "UNKNOWN"}:
        return {"schema": 1, "status": "BLOCKED" if report["status"] == "BLOCKED" else "UNKNOWN",
                "reason": "Source inventory is not complete and clean.", "affected": []}
    records = {record["path"]: record for record in report["files"]}
    module_to_path: Dict[str, str] = {}
    for relative in records:
        module = relative[:-3].replace("/", ".")
        if module.endswith(".__init__"):
            module = module[:-9]
        module_to_path[module] = relative
    reverse = {relative: set() for relative in records}
    for relative, record in records.items():
        for imported in record["imports"]:
            target = module_to_path.get(imported)
            if target and target != relative:
                reverse[target].add(relative)

    normalized: Set[str] = set()
    invalid: List[str] = []
    for raw in changed_paths:
        if not isinstance(raw, str) or not raw or "\x00" in raw:
            invalid.append(str(raw))
            continue
        candidate = raw.replace("\\", "/")
        pure = PurePosixPath(candidate)
        if pure.is_absolute() or any(part in {".", ".."} for part in candidate.split("/")):
            invalid.append(raw)
            continue
        normalized.add(pure.as_posix())
    if invalid:
        return {"schema": 1, "status": "UNKNOWN", "invalid_paths": sorted(invalid), "affected": []}
    unknown = sorted(normalized - records.keys())
    if unknown:
        return {"schema": 1, "status": "UNKNOWN", "unknown_paths": unknown, "affected": []}
    affected: Set[str] = set()
    frontier = list(normalized)
    while frontier:
        current = frontier.pop()
        for dependent in reverse[current] - normalized - affected:
            affected.add(dependent)
            frontier.append(dependent)
    direct = set().union(*(reverse[path] for path in normalized)) if normalized else set()
    return {"schema": 1, "status": "PASS", "changed": sorted(normalized),
            "direct_dependents": sorted(direct), "affected": sorted(affected),
            "limitations": ["Relative/dynamic imports, reflection, plugin loading, and cross-language edges may be missed."]}

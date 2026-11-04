"""Static Python source analysis; project code is never imported or executed."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any, Union, List, Dict, Set

_EXCLUDED = {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist", ".qyrenith"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyze_project(project: Union[str, Path], *, max_files: int = 10000,
                    max_file_bytes: int = 2_000_000) -> Dict[str, Any]:
    """Inventory Python files and extract syntax, imports, symbols, and review hints."""
    if max_files < 1 or max_file_bytes < 1:
        raise ValueError("analysis limits must be positive")
    root = Path(project).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project root must be a directory")
    records: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if any(part in _EXCLUDED for part in relative.parts):
            continue
        if path.is_symlink():
            skipped.append({"path": relative.as_posix(), "reason": "symlink"})
            continue
        size = path.stat().st_size
        if size > max_file_bytes:
            skipped.append({"path": relative.as_posix(), "reason": "file_size_limit"})
            continue
        if len(records) >= max_files:
            return {"schema": 1, "status": "BLOCKED", "reason": "max_files limit exceeded",
                    "files": records, "skipped": skipped}
        common = {"path": relative.as_posix(), "sha256": _sha256(path), "bytes": size}
        try:
            source = path.read_text(encoding="utf-8")
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
    failures = sum(record["syntax"] == "FAIL" for record in records)
    unknown = sum(record["syntax"] == "UNKNOWN" for record in records)
    status = "FAIL" if failures else ("BLOCKED" if unknown or skipped else ("PASS" if records else "UNKNOWN"))
    return {"schema": 1, "status": status, "project": str(root), "files_analyzed": len(records),
            "syntax_failures": failures, "unknown_files": unknown, "files": records, "skipped": skipped,
            "execution_performed": False,
            "limitations": ["Static AST analysis only.", "Relative imports, dynamic imports, and runtime behavior are not fully resolved."]}


def compare_baselines(previous: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """Compare source-analysis snapshots without claiming behavioral equivalence."""
    old = {item["path"]: item for item in previous.get("files", []) if isinstance(item, dict) and "path" in item}
    new = {item["path"]: item for item in current.get("files", []) if isinstance(item, dict) and "path" in item}
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(path for path in old.keys() & new.keys()
                     if old[path].get("sha256") != new[path].get("sha256"))
    regressions = sorted(path for path in old.keys() & new.keys()
                         if old[path].get("syntax") == "PASS" and new[path].get("syntax") == "FAIL")
    return {"schema": 1, "status": "FAIL" if regressions else "PASS", "added": added,
            "removed": removed, "changed": changed, "syntax_regressions": regressions,
            "claim": "Content and syntax delta only; not proof of behavioral regression."}


def build_change_impact(project: Union[str, Path], changed_paths: List[str]) -> Dict[str, Any]:
    """Return direct/transitive importers from a conservative static Python import graph."""
    report = analyze_project(project)
    if report["status"] == "BLOCKED":
        return {"schema": 1, "status": "BLOCKED", "reason": "Source inventory is incomplete.", "affected": []}
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
    normalized = {Path(raw).as_posix().lstrip("./") for raw in changed_paths}
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

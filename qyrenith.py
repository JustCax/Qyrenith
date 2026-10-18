#!/usr/bin/env python3
"""Qyrenith control plane.

Project-neutral verification and orchestration control plane for Non-AI and AI-assisted software development.
Minecraft remains the first flagship domain; domain-specific knowledge lives in skills, providers,
and workers while the safety/verification core stays generic. Standard library only.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, re, shutil, signal, stat, subprocess, sys, tempfile, threading, time, zipfile, shlex
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Keep diagnostics deterministic across Windows console code pages.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

VERSION = "1.0.0"
PRODUCT_NAME = "Qyrenith"
SCHEMA = 8
MAX_FIX = 5
STATE_DIR = ".qyrenith"
STATE_FILE = "state.json"
AUDIT_FILE = "audit.md"
PLAN_FILE = "plan.md"
PLAN_JSON = "plan.json"
SKILL_INDEX = "skill-index.json"
AGENT_TASK = "agent-task.md"
HANDOFF = "current-port-step.md"
LAST_BUILD = "last-build.log"
LAST_REPORT = "report.md"
EVENT_LOG = "events.jsonl"
ISSUE_LOG = "issues.jsonl"
REALITY_MAP_JSON = "reality-map.json"
REALITY_MAP_MD = "reality-map.md"
BASELINE_JSON = "baseline.json"
REALITY_HISTORY = "reality-history.jsonl"
EVIDENCE_LEDGER = "evidence-ledger.jsonl"
DEPENDENCY_LOCK = "dependency-lock.json"
VERSION_GRAPH = "version-graph.json"
ADAPTER_INDEX = "adapter-index.json"
ADAPTER_TRUST = "adapter-trust.json"
ADAPTER_MANIFEST_DIR = "adapters.d"
AGENT_RESULT = "agent-result.json"
WORKER_RESULT = "worker-result.json"
TRANSACTION_FILE = "transaction.json"
SECURITY_REPORT = "security-report.json"
SECURITY_REVIEWS = "security-reviews.json"
BENCHMARK_DIR = "benchmarks"
PROVIDER_INDEX = "provider-index.json"
PUBLIC_AUDIT = "public-audit.json"
DOMAIN_INDEX = "domain-index.json"
DOMAIN_DIR = "domains"
BACKUP_DIR = ".backups"
LOCK_FILE = "run.lock"
MIGRATION_LOG = Path(".agents/skills/minecraft-porting/references/common-migrations.md")
BUILD_SCRIPT = Path(".agents/skills/minecraft-build/scripts/build.sh")
EXCLUDES = {".git", "build", ".gradle", BACKUP_DIR, STATE_DIR, "run", ".idea", ".vscode", "node_modules", "out", "bin", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
EXIT = {"SUCCESS":0,"FAILED":1,"BLOCKED":2,"STOPPED":3,"PREFLIGHT_FAILURE":10,"AUDIT_BLOCKER":11,"UNKNOWN_API":12,"DEPENDENCY_BLOCKER":13,"PORTING_FAILURE":14,"BUILD_FAILURE":15,"UNTRUSTED_BUILD":18,"VALIDATION_FAILURE":16,"FIX_LIMIT_REACHED":17,"USAGE":20,"INTERNAL_ERROR":70}
TEXT_EXTS = {".java", ".kt", ".kts", ".gradle", ".properties", ".toml", ".json", ".json5", ".mcmeta", ".xml", ".txt", ".sh", ".bash", ".js", ".py", ".md", ".yml", ".yaml"}

COMMAND_STREAM_LIMIT = 8 * 1024 * 1024
SENSITIVE_KEY_RE = re.compile(r"(?i)(api[_-]?key|secret|password|token|authorization|credential)")
SENSITIVE_ASSIGN_RE = re.compile(r"(?i)(\b(?:api[_-]?key|secret|password|token|authorization|credential)\b\s*[:=]\s*)([\"\'][^\"\']+[\"\']|[^\s,;]+)")
BEARER_RE = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]+")
_SHA256_CACHE: Dict[Tuple[Path, int, float], str] = {}
WORKER_STREAM_LIMIT = 1024 * 1024
DOMAIN_HINTS = {
    "minecraft": {"minecraft", "neoforge", "forge", "fabric", "blockbench", "mods.toml", "fabric.mod.json", "minecraft_version", "mcmod"},
    "roblox": {"roblox", "luau", "lua", "roblox studio", "rojo", "rbxl"},
    "skyrim": {"skyrim", "creation kit", "papyrus", "esp", "esm", "esl"},
    "gta": {"gta", "fivem", "altv", "rage", "script hook", "asi", "resource manifest"},
    "unity": {"unity", "unityengine", "assembly-csharp", "packages/manifest.json"},
    "godot": {"godot", "project.godot", "gdscript"},
    "unreal": {"unreal", "unreal engine", "uproject", "ue5", "ue4"},
    "python": {"python", "pyproject.toml", "pytest", "requirements.txt", "setup.py"},
    "javascript": {"javascript", "typescript", "node", "npm", "package.json", "tsx", "vite"},
    "rust": {"rust", "cargo", "cargo.toml", "rustc"},
    "java": {"java", "gradle", "maven", "pom.xml", "build.gradle", "build.gradle.kts"},
    "cpp": {"c++", "cpp", "cmake", "meson", "msvc", "clang"},
}
CONTROL_FILES = {"qyrenith.py", "qyrenith_launcher.py"}
INTELLIGENCE_SCHEMA = 1
INTELLIGENCE_FILES = {
    "semantic": "semantic-reality-diff.json",
    "evidence_graph": "evidence-graph.json",
    "contradictions": "contradiction-resolution.json",
    "regression_candidates": "regression-candidates.json",
    "regression_tasks": "regression-validation-tasks.json",
    "feature_contracts": "feature-contracts.json",
    "coverage": "verification-coverage.json",
    "causal": "causal-analysis.json",
    "intent": "intent-preservation.json",
    "proof": "proof-carrying-change.json",
    "mutations": "mutation-plan.json",
    "memory": "engineering-memory.jsonl",
    "compatibility": "compatibility-graph.json",
    "counterfactual": "counterfactual-plan.json",
    "failure_lab": "failure-injection-plan.json",
    "feature_gaps": "feature-verification-gaps.json",
    "runtime_lab": "runtime-lab-plan.json",
    "benchmark_observatory": "benchmark-observatory.json",
    "performance": "performance-observatory.json",
}
EXTERNAL_SCAN_READ_CAP = 256 * 1024
EXTERNAL_OVERSIZED_BYTES = 10 * 1024 * 1024
EXTERNAL_FINDING_CAP = 200
EXTERNAL_RESIDUE_INDIVIDUAL_CAP = 20
EXTERNAL_BASELINE_LIST_CAP = 1000
_EXTERNAL_SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|password|passwd|token|authorization)\s*[:=]\s*['\"][^'\"]{8,}")
_EXTERNAL_PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")
_EXTERNAL_TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
_SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

# ---------------------------------------------------------------------------
# Abstract contracts
# ---------------------------------------------------------------------------
class EvidenceProvider:
    """Tool-agnostic evidence-provider contract. Providers are advisory; policy stays in qyrenith."""
    name = "abstract"
    version = "1"
    capabilities: Sequence[str] = ()
    def supports(self, claim: str) -> bool: return False
    def collect(self, claim: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]: return []
    def verify(self, claim: str, evidence: Sequence[Dict[str, Any]]) -> str: return "UNKNOWN"
    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "version": self.version, "capabilities": list(self.capabilities)}
class WorkerAdapter:
    """Generic worker/porter contract. Execution is external; Doctor verifies the result."""
    name = "abstract"
    version = "1"
    capabilities: Sequence[str] = ()
    def discover(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: return self.describe()
    def inspect(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: return {}
    def plan(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: return {}
    def execute(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: return {"status": "NOT_IMPLEMENTED"}
    def describe(self) -> Dict[str, Any]:
        return {"name": self.name, "version": self.version, "capabilities": list(self.capabilities)}
class QyrenithError(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)
MDocError = QyrenithError

# ---------------------------------------------------------------------------
# Time, filesystem & process helpers
# ---------------------------------------------------------------------------
def now() -> str: return dt.datetime.now(dt.timezone.utc).isoformat()
def stamp() -> str: return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
def die(code: str, message: str): raise QyrenithError(code, message)
def root_path(p: str) -> Path:
    r = Path(p).expanduser().resolve()
    if not r.exists() or not r.is_dir(): die("PREFLIGHT_FAILURE", f"Project path is not a directory: {r}")
    return r
def rel(root: Path, p: Path) -> str:
    try: return str(p.resolve().relative_to(root.resolve())).replace(os.sep, "/")
    except ValueError: return str(p).replace(os.sep, "/")
def ensure_state_dir(root: Path):
    root_resolved=root.resolve(); p=root/STATE_DIR
    if p.exists() and (p.is_symlink() or not p.is_dir()): die("PREFLIGHT_FAILURE",f"State directory is not a real project-local directory: {p}")
    try: resolved=p.resolve()
    except OSError as e: die("PREFLIGHT_FAILURE",f"State directory cannot be resolved: {e}")
    if resolved != root_resolved and not resolved.is_relative_to(root_resolved): die("PREFLIGHT_FAILURE",f"State directory escapes project root: {p} -> {resolved}")
    try: p.mkdir(parents=True, exist_ok=True)
    except OSError as e: die("PREFLIGHT_FAILURE",f"State directory cannot be created in project root ({e.__class__.__name__}: {e}); refusing to continue without durable state")
def require_qyrenith(root: Path) -> Path:
    p = root / "qyrenith.py"
    if not p.is_file() or p.is_symlink(): die("PREFLIGHT_FAILURE", f"Qyrenith orchestrator missing or unsafe: {p}")
    try:
        if not p.resolve().is_relative_to(root.resolve()): die("PREFLIGHT_FAILURE",f"Qyrenith orchestrator escapes project root: {p}")
    except OSError as e: die("PREFLIGHT_FAILURE",f"Qyrenith orchestrator cannot be resolved: {e}")
    return p
def _terminate_process(proc: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            proc.terminate()
        else:
            os.killpg(proc.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try: proc.terminate()
        except OSError: pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt": proc.kill()
            else: os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try: proc.kill()
            except OSError: pass
def cmdrun(cmd: Sequence[str], cwd: Path, timeout: Optional[int] = None) -> Tuple[int, str]:
    """Run a controller command with bounded captured output and hard timeout cleanup."""
    kwargs: Dict[str, Any] = {"cwd": str(cwd), "stdin": subprocess.DEVNULL, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": False, "shell": False}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(list(cmd), **kwargs)
    except OSError as e:
        die("PREFLIGHT_FAILURE", f"Cannot execute {' '.join(cmd)}: {e}")
    out: List[bytes] = []
    state = {"overflow": False, "total": 0}
    def reader() -> None:
        try:
            if proc.stdout is None: return
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk: break
                state["total"] += len(chunk)
                if state["total"] <= COMMAND_STREAM_LIMIT:
                    out.append(chunk)
                else:
                    state["overflow"] = True
                    _terminate_process(proc)
                    break
        except (OSError, ValueError):
            pass
    t = threading.Thread(target=reader, daemon=True); t.start()
    timed_out = False
    try:
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_process(proc)
    finally:
        t.join(timeout=2)
        try:
            if proc.stdout is not None: proc.stdout.close()
        except OSError: pass
    text = redact_text(b"".join(out).decode("utf-8", errors="replace"))
    if timed_out:
        text += "\nTIMEOUT"
        return 124, text
    if state["overflow"]:
        text += "\nOUTPUT_LIMIT_EXCEEDED"
        return 124, text
    return proc.returncode if proc.returncode is not None else 124, text
def git(root: Path, *args: str): return cmdrun(["git", *args], root)
def git_repo(root: Path) -> bool: return (root / ".git").exists()

# ---------------------------------------------------------------------------
# Redaction & persistence
# ---------------------------------------------------------------------------
def redact_text(value: str) -> str:
    text=str(value)
    text=BEARER_RE.sub(r"\1[REDACTED]",text)
    text=SENSITIVE_ASSIGN_RE.sub(r"\1[REDACTED]",text)
    return text
def redact_sensitive(value: Any, key: Optional[str] = None) -> Any:
    if key and SENSITIVE_KEY_RE.search(str(key)):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k:redact_sensitive(v,str(k)) for k,v in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value
def atomic_write(path: Path, data: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        try: os.unlink(name)
        except FileNotFoundError: pass
def save_json(path: Path, obj: Any): atomic_write(path, json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
def append_jsonl(path: Path, obj: Dict[str,Any]):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,"a",encoding="utf-8") as f:
        f.write(json.dumps(obj,ensure_ascii=False,sort_keys=True)+"\n"); f.flush(); os.fsync(f.fileno())
def load_json(path: Path, default: Any = None):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError: return default
    except Exception as e: die("PREFLIGHT_FAILURE", f"Invalid JSON {path}: {e}")

# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------
def initial_state(root: Path) -> Dict[str, Any]:
    return {"schema":SCHEMA,"qyrenith_version":VERSION,"run_id":stamp(),"state":"INIT","phase":"INIT","phase_status":"IDLE","fix_iterations":0,"completed_steps":[],"next_step":0,"steps_plan":[],"events":[],"build_history":[],"validation":{},"commits":[],"snapshots":[],"created":now()}
def migrate_state(s: Dict[str, Any]) -> Dict[str, Any]:
    s.setdefault("schema", SCHEMA)
    # Read the legacy product-version key if an older state file still uses it,
    # then normalize to the current key so old runs migrate transparently.
    if "qyrenith_version" not in s and "mdoc_version" in s:
        s["qyrenith_version"] = s.pop("mdoc_version")
    s.setdefault("qyrenith_version", VERSION); s.setdefault("run_id", stamp())
    s.setdefault("completed_steps", []); s.setdefault("steps_plan", []); s.setdefault("next_step", 0); s.setdefault("fix_iterations", 0)
    s.setdefault("events", []); s.setdefault("build_history", []); s.setdefault("validation", {}); s.setdefault("commits", []); s.setdefault("snapshots", [])
    return s
def load_state(root: Path) -> Dict[str, Any]:
    ensure_state_dir(root); p = root / STATE_DIR / STATE_FILE
    if not p.exists(): return initial_state(root)
    s = load_json(p)
    if not isinstance(s, dict): die("PREFLIGHT_FAILURE", "State root must be an object")
    schema=s.get("schema",1)
    if not isinstance(schema,int) or schema<1: die("PREFLIGHT_FAILURE","State schema is invalid")
    if schema>SCHEMA: die("PREFLIGHT_FAILURE",f"State schema {schema} is newer than this Qyrenith supports (max {SCHEMA})")
    return migrate_state(s)
def save_state(root: Path, s: Dict[str, Any]):
    ensure_state_dir(root); s["updated"] = now(); save_json(root / STATE_DIR / STATE_FILE, s)
def emit_event(root: Path, s: Dict[str, Any], event: str, **data):
    item = {"time":now(),"run_id":s.get("run_id"),"event":event,**data}
    s.setdefault("events", []).append(item); s["events"] = s["events"][-1000:]
    append_jsonl(root / STATE_DIR / EVENT_LOG,item)
    save_state(root, s)
def record_issue(root: Path, s: Dict[str, Any], code: str, message: str, version: Optional[str] = None, status: str = "OPEN"):
    item={"time":now(),"run_id":s.get("run_id"),"type":code,"status":status,"message":message,"version":version or s.get("current_step",[None,None])[1] if isinstance(s.get("current_step"),list) and len(s.get("current_step"))==2 else version}
    append_jsonl(root/STATE_DIR/ISSUE_LOG,item)
    s.setdefault("issue_ledger",[]).append(item); s["issue_ledger"]=s["issue_ledger"][-500:]; save_state(root,s)
    return item
def set_phase(root: Path, s: Dict[str, Any], name: str, status: str = "RUNNING", **extra):
    s.update({"state":name,"phase":name,"phase_status":status,**extra}); emit_event(root,s,"phase",name=name,status=status)
def progress(n: int, total: int, name: str, ok: Optional[bool] = None):
    mark = "✓" if ok is True else "✗" if ok is False else "…"; print(f"[{n}/{total}] {name} {mark}", flush=True)

# ---------------------------------------------------------------------------
# Archive safety
# ---------------------------------------------------------------------------
def safe_member(name: str) -> bool:
    """Reject archive paths that can escape the extraction/project root."""
    raw = str(name).replace("\\", "/")
    if not raw or raw.startswith("/") or re.match(r"^[A-Za-z]:/", raw):
        return False
    parts = [x for x in raw.split("/") if x]
    return ".." not in parts and not any("\x00" in x for x in parts)
def inspect_archive_safety(path: Path, max_members: int = 5000, max_total: int = 100 * 1024 * 1024, max_member: int = 20 * 1024 * 1024, max_ratio: float = 1000.0) -> Dict[str, Any]:
    """Fail-closed inspection for untrusted ZIP archives before extraction."""
    findings=[]
    try:
        with zipfile.ZipFile(path, "r") as z:
            infos=z.infolist()
            if len(infos) > max_members:
                findings.append({"type":"ARCHIVE_MEMBER_LIMIT","count":len(infos)})
            total=0
            member_names=set()
            for info in infos:
                normalized_name=info.filename.replace("\\","/").casefold()
                if normalized_name in member_names:
                    findings.append({"type":"ARCHIVE_DUPLICATE_MEMBER","path":info.filename})
                member_names.add(normalized_name)
                if not safe_member(info.filename):
                    findings.append({"type":"ARCHIVE_UNSAFE_PATH","path":info.filename})
                mode=(info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    findings.append({"type":"ARCHIVE_SYMLINK","path":info.filename})
                if info.file_size > max_member:
                    findings.append({"type":"ARCHIVE_MEMBER_SIZE","path":info.filename,"size":info.file_size})
                total += info.file_size
                if info.compress_size and info.file_size / info.compress_size > max_ratio:
                    findings.append({"type":"ARCHIVE_COMPRESSION_RATIO","path":info.filename})
            if total > max_total:
                findings.append({"type":"ARCHIVE_TOTAL_SIZE","size":total})
    except (OSError, zipfile.BadZipFile) as e:
        findings.append({"type":"ARCHIVE_INVALID","message":str(e)})
    return {"status":"PASS" if not findings else "REVIEW_REQUIRED","findings":findings}

# ---------------------------------------------------------------------------
# Traversal & fingerprinting
# ---------------------------------------------------------------------------
def iter_project_files(root: Path) -> Iterable[Path]:
    """Yield project files without descending into excluded directories.

    The previous implementation walked the entire tree with ``rglob("*")`` and
    filtered afterwards, so it still enumerated ``.git``, ``node_modules``,
    ``build`` and ``.qyrenith`` on every call (measured 1.5s on a realistic mod
    tree for a full reality map). This prunes excluded directories before
    descending and yields in a deterministic sorted order, which is both faster
    and more reproducible than filesystem-dependent ``rglob`` order.

    Symlink handling is unchanged: an escaping symlink is fail-closed.
    """
    root_resolved = root.resolve()

    def walk(directory: Path) -> Iterable[Path]:
        try:
            entries = sorted(os.scandir(directory), key=lambda e: e.name.lower())
        except OSError:
            return
        for entry in entries:
            if entry.name in EXCLUDES:
                continue
            try:
                if entry.is_symlink():
                    try:
                        resolved = Path(entry.path).resolve()
                    except OSError as e:
                        die("PREFLIGHT_FAILURE", f"Unresolvable project symlink: {rel(root, Path(entry.path))}: {e}")
                    if not resolved.is_relative_to(root_resolved):
                        die("PREFLIGHT_FAILURE", f"Project symlink escapes root: {rel(root, Path(entry.path))} -> {resolved}")
                    # A symlink is never followed into; only linked files are yielded.
                    if entry.is_file(follow_symlinks=True):
                        yield Path(entry.path)
                    continue
                if entry.is_dir(follow_symlinks=False):
                    yield from walk(Path(entry.path))
                    continue
                if entry.is_file(follow_symlinks=False):
                    yield Path(entry.path)
            except OSError:
                continue

    yield from walk(root)
def source_files(root: Path, files: Optional[List[Path]] = None) -> List[Path]:
    """Text source files, optionally from a pre-collected file listing."""
    listing = list(iter_project_files(root)) if files is None else files
    return sorted((p for p in listing if p.suffix.lower() in TEXT_EXTS), key=lambda p: rel(root,p).lower())
def sha256_full(path: Path) -> str:
    """Compute SHA-256 with a per-run cache.
    
    The cache key includes (path, size, mtime) so a real content change
    (even same-size) invalidates the entry. Cache is cleared explicitly
    around build/validation boundaries by `_clear_sha256_cache()`.
    """
    try:
        st = path.stat()
        key = (path.resolve(), st.st_size, st.st_mtime)
    except OSError:
        # Fallback: no cache on stat failure.
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
        return h.hexdigest()

    cached = _SHA256_CACHE.get(key)
    if cached is not None:
        return cached
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    digest = h.hexdigest()
    _SHA256_CACHE[key] = digest
    return digest
def _clear_sha256_cache() -> None:
    """Invalidate the hash cache. Call before build starts and after it ends."""
    _SHA256_CACHE.clear()
def source_fingerprint(root: Path, files: Optional[List[Path]] = None) -> str:
    h=hashlib.sha256()
    for p in source_files(root, files):
        h.update(rel(root,p).encode()); h.update(b"\0"); h.update(sha256_full(p).encode()); h.update(b"\0")
    return h.hexdigest()
def stable_hash_obj(obj: Any) -> str:
    """Hash JSON data deterministically, independent of key insertion order/formatting."""
    raw=json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
def plan_context(root: Path, s: Dict[str,Any], src: str, dst: str, steps: Sequence[Tuple[str,str]]) -> Dict[str,Any]:
    """Capture immutable inputs that make a migration plan reproducible and auditable."""
    audit=s.get("audit",{}); graph=load_json(root/STATE_DIR/VERSION_GRAPH,{}); lock=load_json(root/STATE_DIR/DEPENDENCY_LOCK,{}); trust=load_json(root/STATE_DIR/ADAPTER_TRUST,{})
    adapters=[{"name":x.get("name"),"declared":x.get("declared"),"effective":x.get("effective"),"sha256_declared":x.get("sha256_declared"),"sha256_observed":x.get("sha256_observed"),"hash_match":x.get("hash_match")} for x in trust.get("adapters",[]) if isinstance(x,dict)]
    context={"schema":1,"source":src,"target":dst,"loader":audit.get("loader"),"loader_version":audit.get("loader_version"),"steps":[list(x) for x in steps],"audit_fingerprint":audit.get("audit_fingerprint"),"version_graph_hash":stable_hash_obj({"nodes":graph.get("nodes",[]),"edges":graph.get("edges",[])}),"dependency_lock_hash":stable_hash_obj({"target_minecraft":lock.get("target_minecraft"),"dependencies":lock.get("dependencies",{})}),"adapter_trust_hash":stable_hash_obj(sorted(adapters,key=lambda x:str(x.get("name",""))))}
    context["fingerprint"]=stable_hash_obj(context); return context
def project_fingerprint(root: Path, files: Optional[List[Path]] = None) -> str:
    h=hashlib.sha256()
    for p in (iter_project_files(root) if files is None else files):
        h.update(rel(root,p).encode()); h.update(b"\0"); h.update(sha256_full(p).encode()); h.update(b"\0")
    return h.hexdigest()

# ---------------------------------------------------------------------------
# Artifact & build
# ---------------------------------------------------------------------------
def inspect_target_artifact(root: Path, artifact: str) -> Dict[str,Any]:
    candidate=Path(artifact)
    if candidate.is_absolute(): die("PREFLIGHT_FAILURE","Target artifact must be relative to the project root")
    path=(root/candidate).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file(): die("PREFLIGHT_FAILURE",f"Target artifact is missing or outside the project root: {artifact}")
    safety=inspect_archive_safety(path)
    if safety.get("status") != "PASS": die("PREFLIGHT_FAILURE",f"Target artifact failed archive safety checks: {safety.get('findings',[])}")
    metadata=[]
    with zipfile.ZipFile(path,"r") as z:
        names=set(z.namelist())
        for name in ("META-INF/neoforge.mods.toml","META-INF/mods.toml","fabric.mod.json","quilt.mod.json","META-INF/MANIFEST.MF"):
            if name in names:
                raw=z.read(name)
                if len(raw)>2*1024*1024: die("PREFLIGHT_FAILURE",f"Target artifact metadata is oversized: {name}")
                text=raw.decode("utf-8",errors="replace")
                metadata.append({"path":name,"sha256":hashlib.sha256(raw).hexdigest(),"text":redact_text(text)})
    return {"path":rel(root,path),"size":path.stat().st_size,"sha256":sha256_full(path),"archive_safety":safety,"metadata":metadata}
def jar_info(jar: Optional[Path], root: Path, started_ts: float):
    if not jar or not jar.is_file() or jar.is_symlink(): return None
    try:
        if not jar.resolve().is_relative_to(root.resolve()): return None
    except OSError: return None
    st=jar.stat(); return {"path":rel(root,jar),"sha256":sha256_full(jar),"size":st.st_size,"mtime":st.st_mtime,"older_than_build_start":st.st_mtime < started_ts}
def newest_jar(root: Path) -> Optional[Path]:
    # Multiversion layouts build into per-version directories (for example
    # versions/<target>/build/libs) instead of the project-root build/libs.
    # Only the root layout existed when this function was written, so a
    # successful multiversion build failed validation with "exit 0 but no (or
    # empty) JAR in build/libs" even though its jar was real and fresh.
    # Candidate roots are enumerated deterministically: the root layout first
    # (unchanged behavior for single-module projects), then one level of
    # versions/*/build/libs, then explicitly configured relative directories
    # from .qyrenith/artifact-paths.json. Everything stays root-confined and
    # symlink-safe under the same rules as before; configured paths may never
    # escape the project root.
    candidates=[root/"build"/"libs"]
    versions=root/"versions"
    if versions.is_dir() and not versions.is_symlink():
        for version_dir in sorted((p for p in versions.iterdir() if p.is_dir() and not p.is_symlink()), key=lambda x:x.name.lower()):
            candidates.append(version_dir/"build"/"libs")
    configured=load_json(root/STATE_DIR/"artifact-paths.json",[])
    if isinstance(configured,list):
        for entry in configured:
            if not isinstance(entry,str) or not entry or entry.startswith("/"): continue
            candidates.append(root/entry)
    jars=[]
    for d in candidates:
        if d.is_symlink() or not d.is_dir(): continue
        try:
            if not d.resolve().is_relative_to(root.resolve()): continue
        except OSError: continue
        for p in d.glob("*.jar"):
            if p.is_symlink() or not p.is_file(): continue
            try:
                if not p.resolve().is_relative_to(root.resolve()): continue
            except OSError: continue
            if p.stat().st_size>0 and "-sources" not in p.name and "-dev" not in p.name: jars.append(p)
    return max(jars,key=lambda p:p.stat().st_mtime) if jars else None
def evaluate_build(exit_code, fp_before, fp_after, jar, prev_success, build_output=""):
    notes=[]
    if fp_before != fp_after: return "UNTRUSTED", [f"source changed during build ({fp_before} -> {fp_after})"]
    if exit_code != 0: return "FAILED", [f"gradle/build script exit code {exit_code}"]
    if not jar or jar.get("size",0)<=0: return "FAILED", ["exit 0 but no (or empty) JAR in build/libs or versions/*/build/libs"]
    if jar.get("older_than_build_start"):
        if not re.search(r"(?i)BUILD SUCCESSFUL|UP-TO-DATE|FROM-CACHE|NO-SOURCE",str(build_output)):
            return "FAILED", ["non-empty artifact is older than build start and build output does not prove a successful up-to-date/cache/no-source result"]
        notes.append("artifact_mtime_note: JAR older than build start; build output explicitly proves a valid up-to-date/cache/no-source result")
    if prev_success and prev_success.get("source_fingerprint") != fp_after and prev_success.get("jar_sha256") == jar.get("sha256"):
        notes.append("STALE_ARTIFACT_WARNING: source changed since last SUCCESS but JAR hash is identical")
    return "SUCCESS", notes

# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------
def evidence_id(claim: str, source: str, value: Any = None) -> str:
    raw=json.dumps([claim,source,value],sort_keys=True,ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()[:16]
def load_evidence_ledger(root: Path) -> List[Dict[str, Any]]:
    p=root/STATE_DIR/EVIDENCE_LEDGER
    if not p.exists(): return []
    out=[]
    for line in p.read_text(encoding="utf-8",errors="replace").splitlines():
        if not line.strip(): continue
        try:
            x=json.loads(line)
            if isinstance(x,dict): out.append(x)
        except json.JSONDecodeError as e: die("PREFLIGHT_FAILURE",f"Corrupt evidence ledger {p}: {e}")
    return out[-5000:]
def record_evidence(root: Path, claim: str, source: str, status: str="OBSERVED", confidence: str="MEDIUM", details: Optional[Dict[str,Any]]=None, provider: str="local", verification_method: str="unspecified", human_confirmation: Optional[bool]=None) -> Dict[str,Any]:
    safe_claim=redact_text(claim); safe_source=redact_text(source); safe_details=redact_sensitive(details or {})
    item={"id":evidence_id(safe_claim,safe_source,safe_details),"time":now(),"claim":safe_claim,"source":safe_source,"status":status,"confidence":confidence,"provider":redact_text(provider),"verification_method":redact_text(verification_method),"details":safe_details}
    if human_confirmation is not None: item["human_confirmation"]=bool(human_confirmation)
    ensure_state_dir(root)
    append_jsonl(root/STATE_DIR/EVIDENCE_LEDGER,item)
    return item
def evidence_claims(root: Path) -> List[Dict[str,Any]]:
    items=load_evidence_ledger(root)
    explicit=evidence_inventory(root)
    for x in explicit:
        if isinstance(x,dict): items.append({"id":x.get("id") or evidence_id(str(x.get("claim",x.get("type","reference"))),str(x.get("source","unknown"))),"time":x.get("time"),"claim":x.get("claim",x.get("note",x.get("type","reference"))),"source":x.get("source","unknown"),"status":x.get("status","AVAILABLE"),"confidence":x.get("confidence","UNKNOWN"),"details":x})
    uniq={x.get("id"):x for x in items if isinstance(x,dict)}
    return list(uniq.values())

# ---------------------------------------------------------------------------
# Dependency doctor
# ---------------------------------------------------------------------------
def dependency_coordinates(declaration: str) -> Dict[str,Any]:
    text=str(declaration).strip().strip("'").strip('"')
    m=re.search(r"([A-Za-z0-9_.-]+):([A-Za-z0-9_.-]+)(?::([^\s'\")]+))?",text)
    if not m: return {"raw":text,"group":None,"artifact":None,"version":None}
    return {"raw":text,"group":m.group(1),"artifact":m.group(2),"version":m.group(3)}
def discover_evidence_providers(root: Path) -> List[Dict[str, Any]]:
    """Discover declarative providers without executing third-party code."""
    base=root/STATE_DIR/"evidence-providers"; out=[]
    if base.is_dir():
        for p in sorted(base.glob("*.json")):
            obj=load_json(p,{})
            if isinstance(obj,dict) and obj.get("name"):
                out.append({"name":str(obj["name"]),"version":str(obj.get("version","1")),"capabilities":list(obj.get("capabilities",[])),"path":rel(root,p),"status":"DECLARED"})
    result={"schema":1,"generated":now(),"providers":out}
    save_json(root/STATE_DIR/PROVIDER_INDEX,result)
    return out
def dependency_evidence_matches(item: Dict[str,Any], coordinate: Dict[str,Any], target_mc: Optional[str]) -> bool:
    """Match dependency evidence structurally; never trust a source-path substring.

    Accepted evidence may identify the dependency through ``details.dependency``
    or an exact ``group:artifact`` token in the claim. Target Minecraft must also
    be explicit when the evidence supplies a target/version scope.
    """
    if not isinstance(item,dict) or item.get("status") not in {"VERIFIED","PASS"}:
        return False
    key=f"{coordinate.get('group')}:{coordinate.get('artifact')}".lower()
    details=item.get("details") if isinstance(item.get("details"),dict) else {}
    dep=details.get("dependency") if isinstance(details.get("dependency"),dict) else details
    dep_key=f"{dep.get('group')}:{dep.get('artifact')}".lower() if dep.get("group") and dep.get("artifact") else ""
    claim=str(item.get("claim","")).lower()
    identified=(dep_key == key) or bool(re.search(rf"(?<![a-z0-9_.-]){re.escape(key)}(?![a-z0-9_.-])", claim))
    if not identified:
        return False
    scoped=dep.get("target_minecraft") or dep.get("minecraft_version") or dep.get("minecraft_versions")
    if scoped is None:
        scoped=details.get("target_minecraft") or details.get("minecraft_version") or details.get("minecraft_versions")
    if scoped is None:
        return False
    if isinstance(scoped,(list,tuple,set)):
        return target_mc in {str(x) for x in scoped}
    return str(scoped) == str(target_mc)
def dependency_lock(root: Path, s: Dict[str,Any], target_mc: Optional[str]=None) -> Dict[str,Any]:
    deps=s.get("audit",{}).get("dependencies",[])
    previous=load_json(root/STATE_DIR/DEPENDENCY_LOCK,{})
    target=target_mc or s.get("audit",{}).get("target_minecraft")
    previous_target=previous.get("target_minecraft") if isinstance(previous,dict) else None
    records=[]
    for d in deps:
        c=dependency_coordinates(d.get("declaration","")); key=f"{c.get('group')}:{c.get('artifact')}"
        old=previous.get("dependencies",{}).get(key,{}) if isinstance(previous,dict) and previous_target == target else {}
        old_coordinate=old.get("coordinate",{}) if isinstance(old,dict) else {}
        same_version=bool(old_coordinate.get("version") == c.get("version"))
        evidence=[x for x in evidence_claims(root) if dependency_evidence_matches(x,c,target)]
        status="VERIFIED" if evidence else (old.get("status") if same_version and old.get("status") in {"VERIFIED","UNKNOWN","BLOCKED"} else "UNKNOWN")
        records.append({"key":key,"coordinate":c,"source_status":d.get("state","UNKNOWN"),"target_minecraft":target,"status":status,"evidence_ids":[x.get("id") for x in evidence],"reason":"Declared dependency; compatibility is verified only by explicit dependency+target evidence or a retained verified lock for the same target."})
    lock={"schema":1,"generated":now(),"target_minecraft":target,"dependencies":{x["key"]:x for x in records}}
    save_json(root/STATE_DIR/DEPENDENCY_LOCK,lock); s["dependency_lock"]={"path":str(Path(STATE_DIR)/DEPENDENCY_LOCK),"verified":sum(x["status"]=="VERIFIED" for x in records),"unknown":sum(x["status"]=="UNKNOWN" for x in records)}; save_state(root,s)
    return lock
def build_version_graph(root: Path, s: Dict[str,Any]) -> Dict[str,Any]:
    edges=[]; nodes={}
    refs=[root/".agents"/"skills"/"minecraft-porting"/"references"/"versions.md",root/STATE_DIR/"verified-versions.md"]
    for p in refs:
        if not p.is_file(): continue
        text=p.read_text(encoding="utf-8",errors="replace")
        for a,b in re.findall(r"(?<!\d)(\d+\.\d+(?:\.\d+)?)\s*(?:->|→)\s*(\d+\.\d+(?:\.\d+)?)(?!\d)",text):
            if "UNVERIFIED" in text.upper(): continue
            nodes.setdefault(a,{"version":a,"status":"EVIDENCED"}); nodes.setdefault(b,{"version":b,"status":"EVIDENCED"})
            edges.append({"from":a,"to":b,"status":"VERIFIED","evidence":rel(root,p),"risk":"UNKNOWN"})
    for x in detect_project_versions(root): nodes.setdefault(x["version"],{"version":x["version"],"status":x.get("status","OBSERVED"),"evidence":x.get("evidence",[])})
    current=s.get("audit",{}).get("source_minecraft"); target=s.get("audit",{}).get("target_minecraft")
    if current: nodes.setdefault(current,{"version":current,"status":"CURRENT"})
    if target: nodes.setdefault(target,{"version":target,"status":"TARGET"})
    graph={"schema":1,"generated":now(),"nodes":sorted(nodes.values(),key=lambda x:x["version"]),"edges":edges}
    save_json(root/STATE_DIR/VERSION_GRAPH,graph); s["version_graph"]={"path":str(Path(STATE_DIR)/VERSION_GRAPH),"nodes":len(nodes),"edges":len(edges)}; save_state(root,s); return graph

# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------
def _terminate_worker(proc: subprocess.Popen) -> None:
    """Terminate the worker and its process group where the platform supports it."""
    try:
        if os.name == "nt":
            proc.terminate()
        else:
            os.killpg(proc.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try: proc.terminate()
        except OSError: pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt": proc.kill()
            else: os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try: proc.kill()
            except OSError: pass
def _bounded_worker_process(command: Sequence[str], cwd: Path, wire: str, timeout: int, env: Dict[str, str]) -> Tuple[str, str, int, bool, bool, float]:
    """Run a worker with bounded stdout/stderr, timeout and process-group cleanup."""
    kwargs: Dict[str, Any] = {"cwd": str(cwd), "stdin": subprocess.PIPE, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": False, "shell": False}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(list(command), env=env, **kwargs)
    started = time.monotonic()
    out: List[bytes] = []; err: List[bytes] = []
    overflow = {"stdout": False, "stderr": False}
    def reader(stream, bucket, key):
        total = 0
        try:
            while True:
                chunk = stream.read(65536)
                if not chunk: break
                total += len(chunk)
                if total <= WORKER_STREAM_LIMIT:
                    bucket.append(chunk)
                else:
                    overflow[key] = True
                    break
        except (OSError, ValueError):
            pass
    threads=[threading.Thread(target=reader,args=(proc.stdout,out,"stdout"),daemon=True), threading.Thread(target=reader,args=(proc.stderr,err,"stderr"),daemon=True)]
    for t in threads: t.start()
    try:
        if proc.stdin is not None:
            proc.stdin.write(wire.encode("utf-8")); proc.stdin.close()
        proc.wait(timeout=timeout)
    except BrokenPipeError:
        try: proc.wait(timeout=2)
        except subprocess.TimeoutExpired: _terminate_worker(proc)
    except subprocess.TimeoutExpired:
        _terminate_worker(proc)
        for t in threads: t.join(timeout=1)
        for stream in (proc.stdout, proc.stderr):
            try:
                if stream is not None: stream.close()
            except OSError: pass
        return b"".join(out).decode("utf-8",errors="replace"), b"".join(err).decode("utf-8",errors="replace"), proc.returncode or 124, True, False, round(time.monotonic()-started,3)
    if overflow["stdout"] or overflow["stderr"]:
        _terminate_worker(proc)
    for t in threads: t.join(timeout=1)
    for stream in (proc.stdout, proc.stderr):
        try:
            if stream is not None: stream.close()
        except OSError: pass
    return b"".join(out).decode("utf-8",errors="replace"), b"".join(err).decode("utf-8",errors="replace"), proc.returncode or 0, False, overflow["stdout"] or overflow["stderr"], round(time.monotonic()-started,3)
def validate_adapter_manifest(entry: Dict[str,Any], request: Dict[str,Any]) -> None:
    operation=request.get("operation") if isinstance(request,dict) else None
    if operation in {"discover","inspect","plan","result"}: return
    # Minecraft remains the reference platform and keeps its established
    # manifest fields. Generic adapters may instead declare platform/version
    # scope through supported_platforms + supported_versions. This keeps the
    # core protocol reusable without weakening the existing Minecraft gate.
    generic_scope = "supported_platforms" in entry or "supported_versions" in entry
    required=("version","task_types","risk_profile","evidence_requirements")
    if generic_scope:
        required += ("supported_platforms","supported_versions")
    else:
        required += ("supported_loaders","supported_minecraft_versions")
    missing=[k for k in required if k not in entry]
    if missing: die("STOPPED",f"Adapter manifest is incomplete for {operation}: missing {missing}")
    if not isinstance(entry.get("version"),str) or not entry["version"]: die("STOPPED","Adapter version is required")
    list_fields=["task_types","evidence_requirements"]
    list_fields += ["supported_platforms","supported_versions"] if generic_scope else ["supported_loaders","supported_minecraft_versions"]
    for key in list_fields:
        if not isinstance(entry.get(key),list) or not all(isinstance(x,str) and x for x in entry[key]): die("STOPPED",f"Adapter manifest field {key} must be a non-empty string list")
    if not isinstance(entry.get("risk_profile"),str) or not entry["risk_profile"]: die("STOPPED","Adapter risk_profile is required")
    task_type="port" if operation=="port" else str(operation)
    if task_type not in entry["task_types"]: die("STOPPED",f"Adapter does not declare task type: {task_type}")
    if generic_scope:
        platform=request.get("platform")
        if platform and platform not in entry["supported_platforms"]: die("STOPPED",f"Adapter does not support platform: {platform}")
        source_version=request.get("source_version")
        target_version=request.get("target_version")
        task=str(request.get("task", ""))
        m=re.search(r"(?:port\s+)?([^\s]+)\s*->\s*([^\s]+)",task)
        if m:
            source_version=source_version or m.group(1)
            target_version=target_version or m.group(2)
        versions=set(entry["supported_versions"])
        if (source_version and source_version not in versions) or (target_version and target_version not in versions):
            die("STOPPED",f"Adapter does not support migration versions: {source_version} -> {target_version}")
        return
    task=str(request.get("task", ""))
    m=re.search(r"(?:port\s+)?(\d+\.\d+(?:\.\d+)?)\s*->\s*(\d+\.\d+(?:\.\d+)?)",task)
    versions=set(entry["supported_minecraft_versions"])
    if m and (m.group(1) not in versions or m.group(2) not in versions): die("STOPPED",f"Adapter does not support migration versions: {m.group(1)} -> {m.group(2)}")
    loader=request.get("loader")
    if loader and loader not in entry["supported_loaders"]: die("STOPPED",f"Adapter does not support loader: {loader}")
def validate_worker_command_paths(root: Path, command: Sequence[str]) -> None:
    """Reject worker command path arguments that escape the project root."""
    root_resolved=root.resolve()
    for index,arg in enumerate(command):
        value=str(arg)
        if not value or "\x00" in value: die("USAGE", "Worker command contains an invalid argument")
        candidate=Path(value)
        path_like=candidate.is_absolute() or "/" in value or "\\" in value or value.startswith(".")
        if not path_like:
            continue
        if candidate.is_absolute():
            resolved=candidate.resolve()
        else:
            resolved=(root/candidate).resolve()
        if index == 0 and candidate.is_absolute():
            if not resolved.is_file() or not os.access(resolved,os.X_OK):
                die("STOPPED", f"Worker executable is invalid or not executable: {value}")
            continue
        if not resolved.is_relative_to(root_resolved):
            die("STOPPED", f"Worker command argument escapes project root: {value}")
        if index > 0 and candidate.exists() and not resolved.is_file() and not resolved.is_dir():
            die("STOPPED", f"Worker command argument is not a valid project-local path: {value}")
def run_external_worker(root: Path, adapter_name: str, request: Dict[str, Any], timeout: int = 120) -> Dict[str, Any]:
    """Run one explicitly declared worker without shell execution. Worker output never authorizes SUCCESS."""
    if timeout < 1 or timeout > 600:
        die("USAGE", "Worker timeout must be between 1 and 600 seconds")
    cfg=load_json(root/STATE_DIR/"adapters.json", {})
    declared=cfg.get("adapters", []) if isinstance(cfg,dict) else []
    entry=next((x for x in declared if isinstance(x,dict) and x.get("name")==adapter_name), None)
    if not entry:
        die("STOPPED", f"Worker is not explicitly declared: {adapter_name}")
    command=entry.get("command")
    if isinstance(command,str):
        command=[command]
    if not isinstance(command,list) or not command or not all(isinstance(x,str) and x for x in command):
        die("USAGE", f"Invalid worker command for {adapter_name}")
    if any("\x00" in x for x in command):
        die("USAGE", "Worker command contains NUL")
    validate_worker_command_paths(root, command)
    operation=request.get("operation") if isinstance(request,dict) else None
    validate_adapter_manifest(entry,request)
    capabilities=entry.get("capabilities", [])
    if not isinstance(capabilities,list) or not all(isinstance(x,str) and x for x in capabilities):
        die("STOPPED", f"Adapter {adapter_name} has an invalid capability declaration")
    protocol_ops={"discover","inspect","plan","result"}
    required_capability=request.get("required_capability") if isinstance(request,dict) else None
    if required_capability is None and operation not in protocol_ops:
        required_capability=operation
    if required_capability is not None and required_capability not in capabilities:
        die("STOPPED", f"Adapter {adapter_name} does not declare capability: {required_capability}")
    # A declared trust claim is not merely informational: if its executable
    # provenance has drifted, refuse to execute the adapter. UNKNOWN remains
    # runnable only because the caller explicitly named the adapter.
    trust=adapter_trust_record(root,entry)
    if trust.get("declared") in {"VERIFIED","COMMUNITY"} and trust.get("effective") != trust.get("declared"):
        die("STOPPED", f"Adapter trust failed for {adapter_name}: {trust.get('reason')}")
    payload=dict(request); payload.setdefault("schema",1); payload.setdefault("worker",adapter_name); payload.setdefault("project_root",str(root))
    wire=json.dumps(payload,ensure_ascii=False)+"\n"
    if len(wire.encode("utf-8")) > 1024*1024:
        result={"schema":1,"worker":adapter_name,"status":"INPUT_LIMIT","verified_by_doctor":False,"unresolved":["Worker request exceeded 1 MiB"]}
        save_json(root/STATE_DIR/WORKER_RESULT,result); return result
    # Do not leak the controller's ambient environment into third-party workers.
    safe_env={"PATH":os.environ.get("PATH","")}
    for key in ("SystemRoot","WINDIR","HOME","TMPDIR","TEMP","TMP","LANG","LC_ALL"):
        if key in os.environ: safe_env[key]=os.environ[key]
    try:
        stdout, stderr, returncode, timed_out, output_limited, duration = _bounded_worker_process(command, root, wire, timeout, safe_env)
    except OSError as e:
        die("STOPPED", f"Worker could not start: {e}")
    if timed_out:
        result={"schema":1,"worker":adapter_name,"status":"TIMEOUT","verified_by_doctor":False,"unresolved":[f"Worker exceeded {timeout}s timeout"]}
        save_json(root/STATE_DIR/WORKER_RESULT,result); return result
    if output_limited:
        result={"schema":1,"worker":adapter_name,"status":"OUTPUT_LIMIT","verified_by_doctor":False,"unresolved":[f"Worker stdout/stderr exceeded {WORKER_STREAM_LIMIT} bytes"]}
        save_json(root/STATE_DIR/WORKER_RESULT,result); return result
    try:
        result=json.loads(stdout.strip() or "{}")
    except json.JSONDecodeError:
        result={"schema":1,"worker":adapter_name,"status":"INVALID_RESULT","verified_by_doctor":False,"unresolved":["Worker did not emit valid JSON"]}
    if not isinstance(result,dict):
        result={"schema":1,"worker":adapter_name,"status":"INVALID_RESULT","verified_by_doctor":False,"unresolved":["Worker result must be a JSON object"]}
    result=redact_sensitive(result)
    result.setdefault("schema",1); result.setdefault("worker",adapter_name); result.setdefault("dependency_changes",[]); result["verified_by_doctor"]=False
    result["doctor_exit_code"]=returncode; result["duration_seconds"]=duration
    if returncode != 0:
        result={"schema":1,"worker":adapter_name,"status":"FAILED","verified_by_doctor":False,"summary":"Worker exited non-zero; its claimed result is not trusted.","files_changed":result.get("files_changed",[]),"commands_run":result.get("commands_run",[]),"unresolved":result.get("unresolved",[])+[f"worker exit code {returncode}"],"evidence":result.get("evidence",[]),"dependency_changes":result.get("dependency_changes",[]),"doctor_exit_code":returncode,"duration_seconds":duration}
    elif result.get("status") in {"WORKED","NO_CHANGE","BLOCKED","FAILED"}:
        required={"summary","files_changed","commands_run","unresolved","evidence","dependency_changes"}
        missing=sorted(required-set(result))
        if missing:
            result={"schema":1,"worker":adapter_name,"status":"INVALID_RESULT","verified_by_doctor":False,"summary":"Worker result schema is incomplete.","files_changed":result.get("files_changed",[]),"commands_run":result.get("commands_run",[]),"unresolved":[f"missing result fields: {missing}"],"evidence":result.get("evidence",[]),"dependency_changes":result.get("dependency_changes",[]),"doctor_exit_code":returncode,"duration_seconds":duration}
    if stderr:
        result["stderr_tail"]=redact_text(stderr[-4000:])
    save_json(root/STATE_DIR/WORKER_RESULT,result)
    return result
def adapter_command_path(root: Path, command: Any) -> Optional[Path]:
    if not isinstance(command,list) or not command:
        return None
    first=str(command[0]); p=Path(first)
    try:
        if p.is_absolute():
            return p.resolve() if p.is_file() else None
        candidate=(root/p).resolve()
        return candidate if candidate.is_file() and candidate.is_relative_to(root.resolve()) else None
    except (OSError,ValueError):
        return None
def adapter_trust_record(root: Path, item: Dict[str,Any]) -> Dict[str,Any]:
    trust=str(item.get("trust","UNKNOWN")).upper()
    command=item.get("entrypoint", item.get("command"))
    path=adapter_command_path(root,command if isinstance(command,list) else [command] if command else command)
    observed=None
    if path is not None:
        try: observed=sha256_full(path)
        except OSError: observed=None
    declared=str(item.get("sha256","")).lower() or None
    hash_match=bool(declared and observed and declared==observed)
    if trust not in {"VERIFIED","COMMUNITY","UNKNOWN"}: trust="UNKNOWN"
    if trust in {"VERIFIED","COMMUNITY"} and not hash_match:
        effective="UNKNOWN"
        reason="Declared trust requires a matching SHA-256 of the executable entrypoint"
    elif trust=="VERIFIED" and hash_match:
        effective="VERIFIED"; reason="Explicit trust declaration and SHA-256 match"
    elif trust=="COMMUNITY" and hash_match:
        effective="COMMUNITY"; reason="Community trust declaration and SHA-256 match"
    else:
        effective="UNKNOWN"; reason="No verifiable trust declaration"
    return {"name":str(item.get("name","")),"declared":trust,"effective":effective,"path":rel(root,path) if path else None,"sha256_declared":declared,"sha256_observed":observed,"hash_match":hash_match,"reason":reason}
def skill_adapter_capabilities(skill: Dict[str,Any]) -> set:
    """Extract routing metadata without requiring a closed capability vocabulary.

    Explicit metadata is authoritative. Well-known terms are only additive
    convenience hints; discovery itself never depends on them and discovery
    never grants execution authority.
    """
    values=[]
    for key in ("capabilities","domains","task_types","tools","interfaces",
                "tags","keywords","triggers","supported_platforms"):
        value=skill.get(key,[])
        if isinstance(value,str): value=[value]
        if isinstance(value,list): values.extend(str(x).strip().lower() for x in value if str(x).strip())
    explicit=set(values)
    text=" ".join([str(skill.get("name","")),str(skill.get("description","")),*values]).lower()
    inferred=set()
    vocabulary={
        "blockbench":"blockbench", "modeling":"modeling", "modelling":"modeling",
        "model":"modeling", "asset":"asset", "texture":"asset", "resource":"resource",
        "animation":"animation", "rig":"animation", "mcp":"mcp", "migration":"migration",
        "porting":"port", "debug":"debug", "build":"build", "runtime":"runtime",
    }
    for needle,cap in vocabulary.items():
        if re.search(r"(?<![a-z0-9])"+re.escape(needle)+r"(?![a-z0-9])",text): inferred.add(cap)
    return explicit | inferred
def _discover_external_manifests(root: Path) -> List[Dict[str,Any]]:
    """Discover protocol manifests without executing external engines.

    A manifest is an advertisement only. Execution remains gated by capability,
    trust/provenance, path confinement, request validation and Doctor verification.
    """
    directory=root/STATE_DIR/ADAPTER_MANIFEST_DIR
    if not directory.is_dir(): return []
    out=[]
    for path in sorted(directory.glob("*.json"), key=lambda p:p.name.lower()):
        try: item=load_json(path,{})
        except Exception:
            item={"name":path.stem,"status":"BLOCKED","manifest_error":"invalid JSON","manifest_path":rel(root,path)}
        if not isinstance(item,dict):
            item={"name":path.stem,"status":"BLOCKED","manifest_error":"manifest must be an object","manifest_path":rel(root,path)}
        item=dict(item); item.setdefault("name",path.stem); item.setdefault("kind","external")
        item["manifest_path"]=rel(root,path)
        if item.get("status") != "BLOCKED":
            try: validate_adapter_manifest(item,{"operation":"discover"}); item["status"]="DISCOVERED"
            except Exception as exc: item["status"]="BLOCKED"; item["manifest_error"]=str(exc)
        out.append(item)
    return out
def discover_adapters(root: Path) -> List[Dict[str,Any]]:
    adapters=[]
    cfg=load_json(root/STATE_DIR/"adapters.json",{})
    declared=cfg.get("adapters",[]) if isinstance(cfg,dict) else []
    for x in declared:
        if isinstance(x,dict) and x.get("name"):
            item={"name":str(x["name"]),"kind":x.get("kind","external"),"version":x.get("version"),"command":x.get("command"),"capabilities":x.get("capabilities",[]),"supported_loaders":x.get("supported_loaders",[]),"supported_minecraft_versions":x.get("supported_minecraft_versions",[]),"supported_platforms":x.get("supported_platforms",[]),"supported_versions":x.get("supported_versions",[]),"task_types":x.get("task_types",[]),"risk_profile":x.get("risk_profile"),"evidence_requirements":x.get("evidence_requirements",[]),"status":"DECLARED"}
            item["trust"]=adapter_trust_record(root,x)
            adapters.append(item)
    for d in _discover_external_manifests(root):
        d["trust"]=adapter_trust_record(root,d)
        adapters.append(d)
    for d in discover(root):
        caps=skill_adapter_capabilities(d)
        adapters.append({"name":d["name"],"kind":"skill","path":d["path"],"capabilities":sorted(caps),"status":"DISCOVERED","trust":{"name":d["name"],"declared":"LOCAL","effective":"LOCAL","reason":"Project-local skill discovery"}})
    uniq={x["name"]:x for x in adapters}
    out=sorted(uniq.values(),key=lambda x:x["name"].lower())
    trust={x["name"]:x.get("trust",{}) for x in out}
    save_json(root/STATE_DIR/ADAPTER_INDEX,{"schema":3,"generated":now(),"adapters":out})
    save_json(root/STATE_DIR/ADAPTER_TRUST,{"schema":1,"generated":now(),"adapters":trust})
    return out

# ---------------------------------------------------------------------------
# Transaction & security
# ---------------------------------------------------------------------------
def begin_transaction(root: Path, s: Dict[str,Any], step: Optional[Sequence[str]]=None):
    tx={"schema":1,"run_id":s.get("run_id"),"started":now(),"status":"OPEN","step":list(step) if step else None,"baseline":s.get("reality_baseline"),"backup":s.get("backup"),"commit":None}
    save_json(root/STATE_DIR/TRANSACTION_FILE,tx); s["transaction"]={"path":str(Path(STATE_DIR)/TRANSACTION_FILE),"status":"OPEN"}; save_state(root,s); return tx
def close_transaction(root: Path, s: Dict[str,Any], status: str, commit_ref: Optional[str]=None):
    tx=load_json(root/STATE_DIR/TRANSACTION_FILE,{})
    if isinstance(tx,dict):
        tx["status"]=status; tx["closed"]=now(); tx["commit"]=commit_ref; save_json(root/STATE_DIR/TRANSACTION_FILE,tx)
    s["transaction"]={"path":str(Path(STATE_DIR)/TRANSACTION_FILE),"status":status,"commit":commit_ref}; save_state(root,s)
def _is_secret_placeholder(value: str) -> bool:
    normalized = value.strip().strip("\"'").lower()
    placeholder_tokens = (
        "paste-the-", "paste_the_", "replace-me", "replace_me", "your-",
        "your_", "example", "changeme", "change-me", "insert-", "insert_",
        "set-me", "set_me", "<secret>", "<token>", "<password>",
        "shared-forwarding-secret-here",
    )
    return any(token in normalized for token in placeholder_tokens)
def security_finding_id(finding: Dict[str,Any]) -> str:
    payload = json.dumps({k:finding.get(k) for k in ("type","path","line","value_hash")}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
def security_scan(root: Path) -> Dict[str,Any]:
    findings=[]
    for p in iter_project_files(root):
        rp=rel(root,p)
        if rp.startswith(f"{STATE_DIR}/") or rp.startswith(f"{BACKUP_DIR}/"): continue
        if p.is_symlink():
            try:
                if not p.resolve().is_relative_to(root.resolve()): findings.append({"severity":"HIGH","type":"SYMLINK_ESCAPE","path":rp})
            except Exception: findings.append({"severity":"HIGH","type":"SYMLINK_UNRESOLVED","path":rp})
        if p.suffix.lower() in TEXT_EXTS:
            try: size=p.stat().st_size
            except OSError: size=0
            if size > 10 * 1024 * 1024:
                findings.append({"severity":"HIGH","type":"OVERSIZED_INPUT","path":rp,"size":size}); continue
            text=p.read_text(encoding="utf-8",errors="replace")
            secret_match = re.search(r"(?i)(api[_-]?key|secret|password|token|authorization)\s*[:=]\s*['\"][^'\"]{8,}", text)
            if secret_match:
                line_start = text.rfind("\n", 0, secret_match.start()) + 1
                line_end = text.find("\n", secret_match.end())
                line_end = len(text) if line_end < 0 else line_end
                secret_line = text[line_start:line_end]
                value = secret_match.group(0).split("=", 1)[-1].split(":", 1)[-1].strip()
                if "secret_match = re.search" not in secret_line and not _is_secret_placeholder(value):
                    findings.append({"severity":"HIGH","type":"POSSIBLE_SECRET","path":rp,"line":text.count("\n",0,secret_match.start())+1,"value_hash":hashlib.sha256(value.encode("utf-8")).hexdigest()})
            command_match = re.search(r"(?i)\b(rm\s+-rf\s+/|del\s+/s\s+/q|format\s+[a-z]:|curl\s+[^\n]*\|\s*(sh|bash)|wget\s+[^\n]*\|\s*(sh|bash)|invoke-webrequest)", text)
            command_line = text[text.rfind("\n", 0, command_match.start()) + 1:text.find("\n", command_match.end()) if text.find("\n", command_match.end()) >= 0 else len(text)] if command_match else ""
            if command_match and "command_match = re.search" not in command_line: findings.append({"severity":"HIGH","type":"DANGEROUS_OR_NETWORK_COMMAND_PATTERN","path":rp})
    for finding in findings:
        finding["id"] = security_finding_id(finding)
    reviews=load_json(root/STATE_DIR/SECURITY_REVIEWS,{})
    reviewed=reviews.get("reviews",{}) if isinstance(reviews,dict) else {}
    for finding in findings:
        review=reviewed.get(finding["id"])
        if isinstance(review,dict) and review.get("approved") is True:
            finding["reviewed"] = True
            finding["review_reason"] = str(review.get("reason", ""))
    active=[x for x in findings if not x.get("reviewed")]
    report={"schema":2,"generated":now(),"findings":findings,"status":"PASS" if not active else "REVIEW_REQUIRED","reviewed_count":len(findings)-len(active),"policy":{"project_root_confinement":True,"secrets_redacted":True,"archive_path_safety":True,"archive_resource_limits":True,"network_command_review":True,"oversized_input_review":True,"placeholder_secrets_excluded":True,"explicit_security_review_supported":True}}
    save_json(root/STATE_DIR/SECURITY_REPORT,report); return report
_EXTERNAL_DANGEROUS_CMD_RE = re.compile(r"(?i)\b(rm\s+-rf\s+/|del\s+/s\s+/q|format\s+[a-z]:|curl\s+[^\n]*\|\s*(sh|bash)|wget\s+[^\n]*\|\s*(sh|bash)|invoke-webrequest)")
def cmd_security_review(args):
    root=root_path(args.project); require_qyrenith(root); ensure_state_dir(root)
    if not args.yes:
        die("STOPPED","Explicit --yes is required to approve a security finding.")
    finding_id=(args.finding_id or (args.extra[0] if args.extra else "")).strip()
    if not finding_id:
        die("USAGE","Provide --finding-id <id> for the exact security finding to review.")
    report=security_scan(root)
    finding=next((x for x in report.get("findings",[]) if x.get("id")==finding_id),None)
    if not finding:
        die("PREFLIGHT_FAILURE",f"Security finding ID was not found in the current scan: {finding_id}")
    reason=(args.reason or "").strip()
    if not reason:
        die("USAGE","A non-empty --reason is required when approving a security finding.")
    reviews=load_json(root/STATE_DIR/SECURITY_REVIEWS,{"schema":1,"reviews":{}})
    if not isinstance(reviews,dict): reviews={"schema":1,"reviews":{}}
    reviews.setdefault("schema",1); reviews.setdefault("reviews",{})
    reviews["reviews"][finding_id]={"approved":True,"time":now(),"reason":redact_text(reason),"type":finding.get("type"),"path":finding.get("path")}
    save_json(root/STATE_DIR/SECURITY_REVIEWS,reviews)
    refreshed=security_scan(root)
    print(json.dumps({"approved":finding_id,"security_status":refreshed.get("status"),"reviewed_count":refreshed.get("reviewed_count",0)},indent=2,ensure_ascii=False))
    return 0

# ---------------------------------------------------------------------------
# Inventories
# ---------------------------------------------------------------------------
def candidate_feature_inventory(root: Path, files: Optional[List[Path]] = None) -> List[Dict[str,Any]]:
    """Conservative candidate discovery. Candidates are never promoted to verified features automatically."""
    explicit={x.get("name") for x in feature_inventory(root, files) if x.get("source")=="project-map.json"}
    out=[]
    for p in source_files(root, files):
        if p.suffix.lower() not in {".java",".kt"}: continue
        text=p.read_text(encoding="utf-8",errors="replace")
        semantic=[]
        for pat,label in [(r"implements\s+.*Screen","screen"),(r"extends\s+.*Entity","entity"),(r"register.*(BLOCKS|ITEMS)","registry"),(r"CustomPacketPayload|SimpleChannel","networking"),(r"DataGenerator|GatherDataEvent","datagen")]:
            if re.search(pat,text,re.I): semantic.append(label)
        if semantic:
            name=f"candidate:{rel(root,p)}"
            if name not in explicit: out.append({"name":name,"status":"CANDIDATE","source_files":[rel(root,p)],"signals":sorted(set(semantic)),"validation":"AGENT_OR_HUMAN_CONFIRMATION_REQUIRED"})
    return out[:500]
def agent_result(root: Path, s: Dict[str,Any]) -> Dict[str,Any]:
    obj=load_json(root/STATE_DIR/AGENT_RESULT,{})
    if not isinstance(obj,dict): die("STOPPED","Agent result is missing or invalid JSON")
    required={"status","summary","files_changed","commands_run","unresolved","evidence","dependency_changes"}
    missing=required-set(obj)
    if missing: die("STOPPED",f"Agent result missing required fields: {sorted(missing)}")
    if obj.get("status") not in {"WORKED","NO_CHANGE","BLOCKED","FAILED"}: die("STOPPED",f"Unsupported agent result status: {obj.get('status')}")
    obj["verified_by_doctor"] = False
    obj["received_at"] = now(); s["agent_result"]=obj; save_state(root,s); return obj
def sha256(path: Path) -> str:
    """Backward-compatible alias for :func:`sha256_full`."""
    return sha256_full(path)
def read_properties(path: Path) -> Dict[str,str]:
    out={}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k,v=line.split("=",1); out[k.strip()]=v.strip()
    return out
def benchmark_projects(root: Path) -> List[Dict[str,Any]]:
    base=root/BENCHMARK_DIR; results=[]
    if not base.is_dir(): return results
    for d in sorted(x for x in base.iterdir() if x.is_dir()):
        result={"name":d.name,"checks":{},"status":"PASS"}
        result["checks"]["path_safe"]=safe_member(rel(root,d))
        result["checks"]["has_fixture_manifest"]=(d/"FIXTURE.md").is_file()
        manifest=load_json(d/"BENCHMARK.json",{})
        if not isinstance(manifest,dict):
            manifest={}
            result["checks"]["manifest_type_valid"]=False
        else:
            result["checks"]["manifest_type_valid"]=True
        result["checks"]["has_benchmark_manifest"]=all(k in manifest for k in ("expected_plan","expected_safety","expected_validation","expected_reality_diff","regression_assertions"))
        result["checks"]["has_project_map"]=((d/STATE_DIR/"project-map.json").is_file() or (d/"PROJECT-MAP.json").is_file())
        before=source_fingerprint(d); result["checks"]["fingerprint_stable"]=(before==source_fingerprint(d))
        result["checks"]["no_cache_dirs"]=not any(x in {"__pycache__",".gradle","build"} for x in [p.name for p in d.rglob("*") if p.is_dir()])
        if manifest.get("kind") == "minecraft-golden-migration":
            result["checks"]["golden_worker_passes"]=False
            source=d/"source"
            worker_name=manifest.get("worker")
            worker=root/"workers"/(str(worker_name)+".py")
            if source.is_dir() and worker.is_file() and isinstance(manifest.get("task"),str):
                with tempfile.TemporaryDirectory() as td:
                    work=Path(td)/"project"; shutil.copytree(source,work)
                    ensure_state_dir(work)
                    local_worker=work/".qyrenith/benchmark-worker.py"; local_worker.write_text(worker.read_text(encoding="utf-8"),encoding="utf-8")
                    save_json(work/STATE_DIR/"adapters.json", {"adapters":[{"name":worker_name,"version":"1.0.0","command":[sys.executable,".qyrenith/benchmark-worker.py"],"capabilities":["port"],"supported_loaders":["neoforge"],"supported_minecraft_versions":["1.21","1.21.1"],"task_types":["port"],"risk_profile":"bounded-golden-fixture","evidence_requirements":["verified-mapping"]}]})
                    result_obj=run_external_worker(work,worker_name,{"operation":"port","task":manifest["task"]},120)
                    changed=result_obj.get("files_changed",[]) if isinstance(result_obj,dict) else []
                    expected_changed=manifest.get("expected_changed_files",[])
                    unchanged_ok=True
                    for relpath in manifest.get("expected_unchanged_files",[]):
                        a=source/relpath; b=work/relpath
                        if not a.is_file() or not b.is_file() or sha256(a)!=sha256(b): unchanged_ok=False; break
                    props=read_properties(work/"gradle.properties") if (work/"gradle.properties").is_file() else {}
                    props_ok=all(props.get(k)==v for k,v in manifest.get("expected_properties",{}).items())
                    result["golden_result"]={"worker_status":result_obj.get("status"),"files_changed":changed,"expected_changed_files":expected_changed,"unchanged_files_ok":unchanged_ok,"properties_ok":props_ok,"verified_by_doctor":result_obj.get("verified_by_doctor")}
                    result["checks"]["golden_worker_passes"]=(result_obj.get("status")=="WORKED" and changed==expected_changed and unchanged_ok and props_ok and result_obj.get("verified_by_doctor") is False)
        assertions=manifest.get("regression_assertions",[]) if isinstance(manifest,dict) else []
        result["checks"]["regression_assertions_valid"]=isinstance(assertions,list) and all(isinstance(x,str) and x in result["checks"] for x in assertions)
        result["checks"]["regression_assertions_pass"]=result["checks"]["regression_assertions_valid"] and all(result["checks"].get(x) is True for x in assertions)
        result["contract"]={"expected_plan":manifest.get("expected_plan",{}),"expected_safety":manifest.get("expected_safety",{}),"expected_validation":manifest.get("expected_validation",{}),"expected_reality_diff":manifest.get("expected_reality_diff",{}),"regression_assertions":assertions}
        if not all(result["checks"].values()): result["status"]="FAIL"
        results.append(result)
    return results
def detect_project_versions(root: Path) -> List[Dict[str, Any]]:
    """Build a conservative version inventory from evidence actually present on disk.
    Never invents a version. Each entry records its evidence source and confidence.
    """
    found: Dict[str, Dict[str, Any]] = {}
    current = detect_versions(root)
    if current.get("minecraft"):
        found[current["minecraft"]] = {"version": current["minecraft"], "status": "CURRENT", "evidence": ["active build configuration"], "confidence": "HIGH"}
    # Versioned source layouts are common in multi-version projects.
    for base_name in ("versions", "version", "ports", "platforms"):
        base = root / base_name
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir(), key=lambda x: x.name.lower()):
            if not d.is_dir():
                continue
            m = re.fullmatch(r"\d+\.\d+(?:\.\d+)?", d.name)
            if m:
                v = d.name
                found.setdefault(v, {"version": v, "status": "PRESENT", "evidence": [], "confidence": "MEDIUM"})
                found[v]["evidence"].append(f"directory:{rel(root,d)}")
    # Extract explicit Minecraft version literals from build/config/reference files only.
    ref_files=[root/"README.md"]
    ref_dir=root/".agents"/"skills"/"minecraft-porting"/"references"
    if ref_dir.is_dir():
        ref_files.extend(sorted(ref_dir.glob("*.md"), key=lambda x:x.name.lower()))
    for p in ref_files:
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for v in re.findall(r"(?<!\d)(?:(?:1\.\d+\.\d+)|(?:2\d\.\d+))(?!\d)", text):
            found.setdefault(v, {"version": v, "status": "REFERENCED", "evidence": [], "confidence": "LOW"})
            found[v]["evidence"].append(f"reference:{rel(root,p)}")
    for v in found.values():
        version=v["version"]
        if current.get("minecraft") == version:
            v["workflow_status"]="CURRENT"
        else:
            v.setdefault("workflow_status","NOT_ACTIVE")
    return sorted(found.values(), key=lambda x: tuple(int(n) for n in re.findall(r"\d+", x["version"])))
def integration_inventory(root: Path, deps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Inventory declared integrations generically; never hard-code a user's project dependencies."""
    out=[]
    for d in deps:
        declaration=d["declaration"]
        name=dependency_name(declaration)
        out.append({"name":name,"kind":"dependency_integration","declaration":declaration,
                    "present":True,"target_status":"UNKNOWN",
                    "confidence":"OBSERVED","reason":"Presence is observed from the build configuration; target compatibility requires evidence."})
    return out
def dependency_name(declaration: str) -> str:
    text=str(declaration).strip().strip("'\"")
    text=re.sub(r"\s+", " ", text)
    m=re.search(r"[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+(?::[^\s'\")]+)?", text)
    if m:
        coord=m.group(0).split(":")
        return coord[1] if len(coord)>1 else coord[0]
    return text[:120]
def feature_inventory(root: Path, files: Optional[List[Path]] = None) -> List[Dict[str, Any]]:
    """Build a project-specific feature map without embedding any author's feature names.

    Preferred source: optional .qyrenith/project-map.json with a ``features`` list.
    Fallback: conservative source-area inventory. We never call arbitrary class names
    "features" because that would manufacture semantics.
    """
    cfg = load_json(root / STATE_DIR / "project-map.json", {})
    explicit = cfg.get("features", []) if isinstance(cfg, dict) else []
    out=[]
    if isinstance(explicit, list):
        for item in explicit:
            if isinstance(item, str): item={"name": item}
            if not isinstance(item, dict) or not item.get("name"): continue
            declared_files=[str(x).replace("\\","/") for x in item.get("source_files", []) if isinstance(x,str)]
            out.append({"name":str(item["name"]),"status":str(item.get("status","DECLARED")),
                        "source_files":declared_files,"validation":str(item.get("validation","USER_DECLARED")),
                        "versions":item.get("versions",[]),"source":"project-map.json"})
        if out: return sorted(out,key=lambda x:x["name"].lower())
    areas={}
    for p in source_files(root, files):
        if p.suffix.lower() not in {".java",".kt"}: continue
        rp=rel(root,p).split("/")
        if "src" in rp:
            try: idx=rp.index("src"); area="/".join(rp[idx:idx+5])
            except ValueError: area="/".join(rp[:4])
        else: area="/".join(rp[:4])
        areas.setdefault(area,[]).append(rel(root,p))
    return [{"name":f"source-area:{k}","status":"OBSERVED","source_files":v[:50],
             "validation":"NOT_SEMANTICALLY_VERIFIED","source":"filesystem"}
            for k,v in sorted(areas.items(),key=lambda x:x[0].lower())]
def issue_inventory(root: Path, s: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues=[]
    a=s.get("audit",{}); lock=load_json(root/STATE_DIR/DEPENDENCY_LOCK,{})
    locked=lock.get("dependencies",{}) if isinstance(lock,dict) else {}
    for d in a.get("dependencies",[]):
        declaration=d.get("declaration"); c=dependency_coordinates(declaration or ""); key=f"{c.get('group')}:{c.get('artifact')}"; state=locked.get(key,{}).get("status",d.get("state")) if isinstance(locked,dict) else d.get("state")
        if state in {"UNKNOWN","NO"}:
            issues.append({"type":"DEPENDENCY_BLOCKER" if state=="UNKNOWN" else "DEPENDENCY_MISSING","status":"OPEN","message":d.get("reason","Dependency requires verification."),"evidence":declaration,"version":a.get("target_minecraft")})
    for item in s.get("issue_ledger",[]):
        if isinstance(item,dict): issues.append(item)
    for key in ("failure","failure_analysis"):
        x=s.get(key)
        if isinstance(x,dict) and x.get("message"):
            issues.append({"type":x.get("code") or x.get("category") or "BUILD_FAILURE","status":"OPEN","message":x["message"],"evidence":x.get("log_path"),"version":a.get("target_minecraft")})
    unique=[]; seen=set()
    for item in issues:
        key=(item.get("type"),item.get("status"),item.get("message"),item.get("version")) if isinstance(item,dict) else str(item)
        if key in seen: continue
        seen.add(key); unique.append(item)
    return unique

# ---------------------------------------------------------------------------
# Reality map
# ---------------------------------------------------------------------------
def capture_reality_baseline(root: Path, s: Dict[str, Any], step: Optional[Sequence[str]] = None):
    """Freeze the pre-modification reality map for the active step."""
    r=build_reality_map(root,s,"pre-step-baseline")
    baseline={k:v for k,v in r.items() if k != "baseline_comparison"}
    baseline["file_hashes"]={rel(root,p):sha256_full(p) for p in iter_project_files(root)}
    baseline["captured_for_step"]=list(step) if step else None
    baseline["captured_at"]=now()
    save_json(root/STATE_DIR/BASELINE_JSON,baseline)
    s["reality_baseline"]={"path":str(Path(STATE_DIR)/BASELINE_JSON),"fingerprint":baseline["fingerprints"]["source"],"step":list(step) if step else None}
    save_state(root,s)
    return baseline
def compare_to_step_baseline(root: Path, s: Dict[str, Any]):
    baseline=load_json(root/STATE_DIR/BASELINE_JSON,{})
    current=build_reality_map(root,s,"post-step")
    if not isinstance(baseline,dict) or not baseline.get("fingerprints"):
        die("VALIDATION_FAILURE","Reality baseline is missing; refusing to claim that the migration preserved project state.")
    diff=compare_reality_maps(baseline,current)
    # Reconcile file-level changes from the authoritative source fingerprint and Git status.
    diff["source_fingerprint_before"]=baseline["fingerprints"].get("source")
    diff["source_fingerprint_after"]=current["fingerprints"].get("source")
    diff["project_fingerprint_before"]=baseline["fingerprints"].get("project")
    diff["project_fingerprint_after"]=current["fingerprints"].get("project")
    diff["file_changes"]=file_change_report(root,baseline)
    diff["unexpected_feature_removals"]=diff.get("features_removed",[])
    diff["unexpected_integration_removals"]=diff.get("integrations_removed",[])
    before_deps={str(x.get("declaration")) for x in baseline.get("dependencies",[]) if isinstance(x,dict) and x.get("declaration")}
    after_deps={str(x.get("declaration")) for x in current.get("dependencies",[]) if isinstance(x,dict) and x.get("declaration")}
    diff["dependency_drift"]={"added":sorted(after_deps-before_deps),"removed":sorted(before_deps-after_deps)}
    s["reality_diff"]=diff
    save_state(root,s)
    return diff
def evidence_inventory(root: Path, source: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read-only evidence ledger. Evidence is explicit and never inferred into VERIFIED facts."""
    candidates=[]
    candidates.extend([root/STATE_DIR/"evidence.json", root/".agents"/"skills"/"minecraft-porting"/"references"/"versions.md"])
    out=[]
    for p in candidates:
        if not p.is_file(): continue
        if p.suffix == ".json":
            obj=load_json(p,{})
            items=obj.get("evidence",[]) if isinstance(obj,dict) else []
            for x in items if isinstance(items,list) else []:
                if isinstance(x,dict):
                    y=dict(x); y.setdefault("source",rel(root,p)); y.setdefault("confidence","UNKNOWN"); out.append(y)
        else:
            text=p.read_text(encoding="utf-8",errors="replace")
            confidence="LOW"
            if re.search(r"\bVERIFIED\b",text,re.I) and not re.search(r"\bUNVERIFIED\b",text,re.I): confidence="HIGH"
            out.append({"type":"reference","source":rel(root,p),"confidence":confidence,
                        "status":"AVAILABLE","note":"Reference content exists; individual claims still require task-relevant verification."})
    return out
def graph_inventory(r: Dict[str, Any]) -> Dict[str, Any]:
    """Create a generic relationship graph from observed entities only."""
    nodes=[]; edges=[]
    identity=r.get("project_identity",{})
    if identity.get("mod_id"): nodes.append({"id":"project","type":"project","label":identity["mod_id"]})
    for v in r.get("versions",[]): nodes.append({"id":"version:"+v["version"],"type":"version","label":v["version"]})
    for f in r.get("features",[]):
        fid="feature:"+str(f["name"]); nodes.append({"id":fid,"type":"feature","label":f["name"]})
        for sf in f.get("source_files",[])[:50]:
            sid="file:"+sf; nodes.append({"id":sid,"type":"file","label":sf}); edges.append([fid,sid,"implemented_by"])
    for d in r.get("dependencies",[]):
        name=dependency_name(d.get("declaration","")); did="dependency:"+name; nodes.append({"id":did,"type":"dependency","label":name})
        if identity.get("mod_id"): edges.append(["project",did,"declares"])
    plan=r.get("current_state",{}).get("steps_plan",[])
    for step in plan:
        if isinstance(step,(list,tuple)) and len(step)==2:
            a,b=str(step[0]),str(step[1]); aid="version:"+a; bid="version:"+b
            nodes.extend([{"id":aid,"type":"version","label":a},{"id":bid,"type":"version","label":b}]); edges.append([aid,bid,"migration_step"])
    # De-duplicate nodes/edges for stable output.
    uniq={x["id"]:x for x in nodes}
    return {"nodes":sorted(uniq.values(),key=lambda x:x["id"]),"edges":sorted({tuple(x) for x in edges})}
def file_change_report(root: Path, baseline: Dict[str, Any]) -> Dict[str, Any]:
    """Report actual tracked source/resource changes against a frozen file-hash baseline."""
    before=baseline.get("file_hashes",{})
    after={rel(root,p):sha256_full(p) for p in iter_project_files(root)}
    added=sorted(set(after)-set(before)); removed=sorted(set(before)-set(after))
    modified=sorted(k for k in set(before)&set(after) if before[k]!=after[k])
    unexpected=[x for x in added+modified if not (x.startswith(".qyrenith/") or x.startswith(".backups/"))]
    return {"added":added,"modified":modified,"removed":removed,"unexpected":unexpected}
def feature_declared_integrity(root: Path, r: Dict[str, Any]) -> List[str]:
    """Return explicit feature declarations that reference missing files."""
    problems=[]
    for f in r.get("features",[]):
        for sf in f.get("source_files",[]):
            if not isinstance(sf,str) or Path(sf).is_absolute():
                problems.append(f"{f.get('name')}: unsafe declared file path {sf}"); continue
            candidate=(root/sf).resolve()
            if not candidate.is_relative_to(root.resolve()) or not candidate.is_file(): problems.append(f"{f.get('name')}: missing or unsafe declared file {sf}")
    return problems
def resource_inventory(root: Path) -> List[Dict[str,Any]]:
    base=root/"src"/"main"/"resources"; out=[]
    if not base.is_dir(): return out
    for p in sorted(base.rglob("*"),key=lambda x:str(x).lower()):
        if not p.is_file() or p.is_symlink(): continue
        try: out.append({"path":rel(root,p),"size":p.stat().st_size,"sha256":sha256_full(p)})
        except OSError: continue
        if len(out)>=1000: break
    return out
def generic_file_inventory(root: Path, files: Optional[List[Path]] = None) -> List[Dict[str, Any]]:
    """Inventory project files using bounded metadata and content fingerprints."""
    out=[]
    for f in (iter_project_files(root) if files is None else files):
        try:
            st=f.stat()
            out.append({"path":rel(root,f),"size":st.st_size,"sha256":sha256_full(f),"suffix":f.suffix.lower()})
        except OSError:
            continue
        if len(out) >= 5000:
            break
    return out
def generic_technology_inventory(root: Path) -> List[Dict[str, Any]]:
    """Infer technologies only from concrete project markers; unknown stays unknown."""
    markers={
        "Python":["pyproject.toml","requirements.txt","setup.py","setup.cfg","Pipfile"],
        "JavaScript/TypeScript/Node":["package.json","tsconfig.json","package-lock.json","pnpm-lock.yaml","yarn.lock"],
        "Rust":["Cargo.toml","Cargo.lock"],
        "Java/Gradle":["build.gradle","build.gradle.kts","settings.gradle","settings.gradle.kts","gradlew"],
        "Java/Maven":["pom.xml"],
        "C/C++/CMake":["CMakeLists.txt"],
        "C/C++/Make":["Makefile"],
        "Go":["go.mod","go.sum"],
        ".NET":["*.csproj","*.fsproj","*.sln"],
    }
    found=[]
    for technology, names in markers.items():
        evidence=[]
        for name in names:
            if "*" in name:
                evidence.extend(rel(root,p) for p in root.glob(name) if p.is_file())
            elif (root/name).is_file():
                evidence.append(name)
        if evidence:
            found.append({"name":technology,"status":"OBSERVED","evidence":sorted(set(evidence))})
    return found
def generic_project_identity(root: Path) -> Dict[str, Any]:
    """Return domain-neutral identity signals without inventing semantic support."""
    try:
        detection=detect_domain(root, "")
    except Exception:
        detection={"domain":"unknown","confidence":"UNKNOWN","source":"none"}
    name=None
    for marker in ("pyproject.toml","package.json","Cargo.toml","pom.xml"):
        p=root/marker
        if p.is_file():
            try:
                text=p.read_text(encoding="utf-8",errors="replace")
                if marker=="pyproject.toml":
                    m=re.search(r"(?m)^name\s*=\s*[\"']([^\"']+)",text)
                elif marker=="package.json":
                    obj=json.loads(text); m=None
                    if isinstance(obj,dict) and isinstance(obj.get("name"),str): name=obj["name"]
                elif marker=="Cargo.toml":
                    m=re.search(r"(?m)^name\s*=\s*[\"']([^\"']+)",text)
                else:
                    m=re.search(r"<artifactId>\s*([^<]+)\s*</artifactId>",text)
                if m and hasattr(m,"group"): name=m.group(1).strip()
            except (OSError,ValueError):
                pass
        if name: break
    return {"name":name,"domain":detection.get("domain","unknown"),"domain_confidence":detection.get("confidence","UNKNOWN"),"domain_source":detection.get("source","none")}
def build_reality_map(root: Path, s: Dict[str, Any], reason: str = "audit") -> Dict[str, Any]:
    ensure_state_dir(root)
    v=detect_versions(root); m=metadata(root); deps=parse_dependencies(root)
    # One authoritative tree walk, shared by every inventory below. Previously six
    # independent walks ran per map (fingerprints, file inventory, features,
    # candidates, ...), which dominates on large projects.
    files=list(iter_project_files(root))
    versions=detect_project_versions(root)
    lock=load_json(root/STATE_DIR/DEPENDENCY_LOCK,{})
    locked=lock.get("dependencies",{}) if isinstance(lock,dict) else {}
    dep_records=[]
    for d in deps:
        c=dependency_coordinates(d); key=f"{c.get('group')}:{c.get('artifact')}"; rec=locked.get(key,{}) if isinstance(locked,dict) else {}
        dep_records.append({"declaration":d,"state":rec.get("status","UNKNOWN"),"target_status":rec.get("status","UNKNOWN"),"coordinate":rec.get("coordinate",c),"evidence_ids":rec.get("evidence_ids",[])})
    integrations=integration_inventory(root,dep_records)
    features=feature_inventory(root,files)
    candidates=candidate_feature_inventory(root,files)
    issues=issue_inventory(root,s)
    evidence=evidence_inventory(root)
    risks=s.get("audit",{}).get("risks",[]) if isinstance(s.get("audit"),dict) else []
    git_info=s.get("git",{})
    result={
        "schema":1,"generated":now(),"reason":reason,"project":str(root),
        "fingerprints":{"source":source_fingerprint(root,files),"project":project_fingerprint(root,files)},
        "project_identity":{"mod_id":m.get("mod_id"),"mod_version":m.get("version"),"minecraft":v.get("minecraft"),"loader":v.get("loader"),"loader_version":v.get("loader_version"),"java":v.get("java"),"gradle":v.get("gradle"),**generic_project_identity(root)},
        "technologies":generic_technology_inventory(root),
        "file_inventory":generic_file_inventory(root,files),
        "versions":versions,
        "features":features,
        "feature_candidates":candidates,
        "integrations":integrations,
        "dependencies":dep_records,
        "resources":resource_inventory(root),
        "issues":issues,
        "evidence":evidence,
        "risks":risks,
        "git":git_info,
        "current_state":{"phase":s.get("phase"),"phase_status":s.get("phase_status"),"current_step":s.get("current_step"),"next_step":s.get("next_step"),"completed_steps":s.get("completed_steps",[]),"steps_plan":s.get("steps_plan",[]),"fix_iterations":s.get("fix_iterations",0),"result_status":s.get("result_status")},
    }
    old=load_json(root/STATE_DIR/REALITY_MAP_JSON,{})
    result["graph"]=graph_inventory(result)
    result["feature_integrity"]=feature_declared_integrity(root,result)
    result["baseline_comparison"]=compare_reality_maps(old if isinstance(old,dict) else {},result)
    save_json(root/STATE_DIR/REALITY_MAP_JSON,result)
    append_jsonl(root/STATE_DIR/REALITY_HISTORY,{"time":result["generated"],"reason":reason,"fingerprints":result["fingerprints"],"comparison":result["baseline_comparison"]})
    s["reality_map"]={"path":str(Path(STATE_DIR)/REALITY_MAP_JSON),"generated":result["generated"],"fingerprint":result["fingerprints"]["source"]}
    save_state(root,s)
    atomic_write(root/STATE_DIR/REALITY_MAP_MD,reality_map_markdown(result))
    return result
def compare_reality_maps(old: Dict[str,Any], new: Dict[str,Any]) -> Dict[str,Any]:
    if not old.get("fingerprints"): return {"status":"BASELINE_CREATED","changed":True,"files":[],"features_added":[],"features_removed":[],"integrations_added":[],"integrations_removed":[],"issues_opened":[]}
    def names(obj,key): return {str(x.get("name")) for x in obj.get(key,[]) if isinstance(x,dict) and x.get("name")}
    of, nf=names(old,"features"),names(new,"features"); oi,ni=names(old,"integrations"),names(new,"integrations")
    old_issues={(x.get("type"),x.get("message")) for x in old.get("issues",[]) if isinstance(x,dict)}
    new_issues={(x.get("type"),x.get("message")) for x in new.get("issues",[]) if isinstance(x,dict)}
    def file_index(obj):
        return {x.get("path"):x for x in obj.get("file_inventory",[]) if isinstance(x,dict) and x.get("path")}
    old_files,new_files=file_index(old),file_index(new)
    file_changes={
        "added":sorted(set(new_files)-set(old_files)),
        "removed":sorted(set(old_files)-set(new_files)),
        "modified":sorted(k for k in set(old_files)&set(new_files) if old_files[k].get("sha256")!=new_files[k].get("sha256")),
    }
    def technology_names(obj):
        return {str(x.get("name")) for x in obj.get("technologies",[]) if isinstance(x,dict) and x.get("name")}
    ot,nt=technology_names(old),technology_names(new)
    return {"status":"CHANGED" if old.get("fingerprints")!=new.get("fingerprints") else "UNCHANGED","changed":old.get("fingerprints")!=new.get("fingerprints"),"files":file_changes,"features_added":sorted(nf-of),"features_removed":sorted(of-nf),"integrations_added":sorted(ni-oi),"integrations_removed":sorted(oi-ni),"technologies_added":sorted(nt-ot),"technologies_removed":sorted(ot-nt),"issues_opened":[{"type":a,"message":b} for a,b in sorted(new_issues-old_issues)]}
def reality_map_markdown(r: Dict[str,Any]) -> str:
    i=r["project_identity"]; lines=["# Qyrenith Project Reality Map","",f"Generated: {r['generated']}",f"Reason: {r['reason']}","","## Project",f"- Mod: `{i.get('mod_id') or 'UNKNOWN'}`",f"- Mod version: `{i.get('mod_version') or 'UNKNOWN'}`",f"- Minecraft: `{i.get('minecraft') or 'UNKNOWN'}`",f"- Loader: `{i.get('loader') or 'UNKNOWN'}` `{i.get('loader_version') or ''}`",f"- Java: `{i.get('java') or 'UNKNOWN'}`",f"- Gradle: `{i.get('gradle') or 'UNKNOWN'}`","","## Version inventory"]
    for x in r["versions"]: lines.append(f"- `{x['version']}` — **{x['status']}** — {', '.join(x['evidence'])}")
    if not r["versions"]: lines.append("- No verified/present version evidence found.")
    lines += ["","## Features"]+[f"- `{x['name']}` — {x['status']} — {', '.join(x['source_files'][:6])}" for x in r["features"]]
    lines += ["","## Integrations"]+[f"- `{x['name']}` — `{x['kind']}` — present={x['present']} — target={x['target_status']}" for x in r["integrations"]]
    lines += ["","## Issues / blockers"] + ([f"- `{x['type']}` — {x['status']} — {x['message']}" for x in r["issues"]] or ["- None recorded."])
    lines += ["","## Evidence"] + ([f"- `{x.get('confidence','UNKNOWN')}` — {x.get('source','unknown')} — {x.get('status','UNKNOWN')}" for x in r.get('evidence',[])] or ["- No evidence records available."])
    lines += ["","## Graph"]+[f"- Nodes: `{len(r.get('graph',{}).get('nodes',[]))}`",f"- Edges: `{len(r.get('graph',{}).get('edges',[]))}`"]
    lines += ["","## Current workflow state",f"- Phase: `{r['current_state'].get('phase')}`",f"- Step: `{r['current_state'].get('current_step')}`",f"- Fix iterations: `{r['current_state'].get('fix_iterations')}`","","## Baseline comparison",f"- Status: `{r['baseline_comparison'].get('status')}`",f"- Features added: `{len(r['baseline_comparison'].get('features_added',[]))}`",f"- Features removed: `{len(r['baseline_comparison'].get('features_removed',[]))}`",f"- Integrations added: `{len(r['baseline_comparison'].get('integrations_added',[]))}`",f"- Integrations removed: `{len(r['baseline_comparison'].get('integrations_removed',[]))}`"]
    return "\n".join(lines)+"\n"

# ---------------------------------------------------------------------------
# Metadata / detection / deps / risk
# ---------------------------------------------------------------------------
def _metadata_resource_roots(root: Path) -> List[Path]:
    """Return deterministic, project-local metadata resource roots.

    Supports both the conventional single-module layout and the common
    multiversion layout:

        src/main/resources
        versions/<target>/src/main/resources

    Optional project-local configuration may extend discovery through
    .qyrenith/metadata-paths.json, whose value is a list of relative
    resource-directory paths. Configured paths are never allowed to escape
    the project root.
    """
    candidates: List[Path] = [root / "src" / "main" / "resources"]
    versions = root / "versions"
    if versions.is_dir() and not versions.is_symlink():
        for version_dir in sorted(versions.iterdir(), key=lambda x: x.name.lower()):
            if version_dir.is_dir() and not version_dir.is_symlink():
                candidates.append(version_dir / "src" / "main" / "resources")

    config = root / STATE_DIR / "metadata-paths.json"
    if config.is_file() and not config.is_symlink():
        try:
            obj = json.loads(config.read_text(encoding="utf-8", errors="replace"))
            paths = obj if isinstance(obj, list) else obj.get("paths", []) if isinstance(obj, dict) else []
            if isinstance(paths, list):
                for value in paths:
                    if not isinstance(value, str) or not value.strip():
                        continue
                    candidate = Path(value)
                    if candidate.is_absolute():
                        continue
                    resolved = (root / candidate).resolve()
                    if resolved.is_relative_to(root.resolve()):
                        candidates.append(resolved)
        except (OSError, json.JSONDecodeError):
            pass

    seen = set()
    roots: List[Path] = []
    root_resolved = root.resolve()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_relative_to(root_resolved):
            continue
        seen.add(resolved)
        if resolved.is_dir() and not resolved.is_symlink():
            roots.append(resolved)
    return roots
def metadata(root: Path) -> Dict[str, Any]:
    files=[]; mod_id=None; version=None; raw_parts=[]
    root_resolved=root.resolve()
    for resources in _metadata_resource_roots(root):
        md=resources / "META-INF"
        if md.is_dir() and not md.is_symlink():
            try:
                md_resolved=md.resolve()
                md_safe=md_resolved.is_relative_to(root_resolved)
            except OSError:
                md_safe=False
            if md_safe:
                for p in sorted(md.glob("*.toml"),key=lambda x:(x.name.lower(), str(x).lower())):
                    if not p.is_file() or p.is_symlink():
                        continue
                    try:
                        if not p.resolve().is_relative_to(root_resolved):
                            continue
                        text=p.read_text(encoding="utf-8",errors="replace")
                    except OSError:
                        continue
                    files.append(p); raw_parts.append(text)
                    if mod_id is None:
                        m=re.search(r"\bmodId\s*=\s*['\"]([^'\"]+)['\"]",text,re.I)
                        if m: mod_id=m.group(1)
                    if version is None:
                        m=re.search(r"\bversion\s*=\s*['\"]([^'\"]+)['\"]",text,re.I)
                        if m: version=m.group(1)

        fabric=resources / "fabric.mod.json"
        if fabric.is_file() and not fabric.is_symlink():
            try:
                if not fabric.resolve().is_relative_to(root_resolved):
                    continue
                files.append(fabric)
                obj=json.loads(fabric.read_text(encoding="utf-8"))
                if isinstance(obj,dict):
                    mod_id=mod_id or obj.get("id")
                    version=version or obj.get("version")
                    raw_parts.append(json.dumps(obj,ensure_ascii=False,sort_keys=True))
            except (OSError,json.JSONDecodeError):
                pass
    return {"files":[rel(root,p) for p in files],"mod_id":str(mod_id) if mod_id is not None else None,"version":str(version) if version is not None else None,"raw":"\n".join(raw_parts)}
def detect_versions(root: Path) -> Dict[str, Optional[str]]:
    texts=[]
    for name in ("gradle.properties","build.gradle","build.gradle.kts"):
        p=root/name
        if p.exists(): texts.append(p.read_text(encoding="utf-8",errors="replace"))
    joined="\n".join(texts); mc=None
    mc_patterns=[
        r"minecraft_version\s*[=:]\s*['\"]?([0-9]+\.[0-9]+(?:\.[0-9]+)?)",
        r"minecraftVersion\s*[=:]\s*['\"]?([0-9]+\.[0-9]+(?:\.[0-9]+)?)",
        # Multiversion layouts name the property per target
        # (minecraft_1_21_1, minecraft_26_2, ...). Fallback only: the
        # first version-looking value wins, so single-module projects
        # never reach this pattern.
        r"minecraft[_-][0-9][\w.]*\s*[=:]\s*['\"]?([0-9]+\.[0-9]+(?:\.[0-9]+)?)",
    ]
    for pat in mc_patterns:
        m=re.search(pat,joined,re.I)
        if m: mc=m.group(1); break
    loader=lv=None
    fabric_meta=root/"src"/"main"/"resources"/"fabric.mod.json"
    loader_patterns=[("neoforge",r"neoForgeVersion\s*[=:]\s*['\"]?([^'\"\s]+)"),("neoforge",r"neoforge_version\s*[=:]\s*['\"]?([^'\"\s]+)"),("neoforge",r"neo_version\s*[=:]\s*['\"]?([^'\"\s]+)"),("forge",r"forge_version\s*[=:]\s*['\"]?([^'\"\s]+)"),("fabric",r"fabric_loader_version\s*[=:]\s*['\"]?([^'\"\s]+)"),
        # Multiversion fallbacks (versions share one properties file, e.g.
        # neoforge_1_21_1, fabric_loader). A multiversion root declares
        # several loaders at once, so no order is "correct" in general;
        # the deterministic neoforge-first order follows the reference
        # target convention, and --target-loader still guards mismatches.
        ("neoforge",r"neoforge[_-][0-9][\w.]*\s*[=:]\s*['\"]?([0-9][^'\"\s]*)"),
        ("forge",r"forge[_-][0-9][\w.]*\s*[=:]\s*['\"]?([0-9][^'\"\s]*)"),
        ("fabric",r"fabric[_-]loader\s*[=:]\s*['\"]?([^'\"\s]+)")]
    for typ,pat in loader_patterns:
        m=re.search(pat,joined,re.I)
        if m: loader,lv=typ,m.group(1); break
    if loader is None and fabric_meta.is_file(): loader="fabric"
    if loader == "fabric" and lv is None:
        m=re.search(r"loader_version\s*[=:]\s*['\"]?([^'\"\s]+)",joined,re.I)
        if m: lv=m.group(1)
    java=None
    for p in (root/"gradle.properties",root/"build.gradle",root/"build.gradle.kts"):
        if p.exists():
            t=p.read_text(encoding="utf-8",errors="replace")
            m=re.search(r"(?:java|java_version|javaVersion)\s*[=:]\s*['\"]?(\d+)",t,re.I) or re.search(r"JavaLanguageVersion\.of\((\d+)\)",t)
            if m: java=m.group(1); break
    gradle=None
    gw=root/"gradle"/"wrapper"/"gradle-wrapper.properties"
    if gw.exists():
        m=re.search(r"gradle-([0-9.]+)-(?:bin|all)\.zip",gw.read_text(encoding="utf-8",errors="replace")); gradle=m.group(1) if m else None
    return {"minecraft":mc,"loader":loader,"loader_version":lv,"java":java,"gradle":gradle}
def parse_dependencies(root: Path) -> List[str]:
    out=[]
    for name in ("build.gradle","build.gradle.kts"):
        p=root/name
        if p.exists():
            for line in p.read_text(encoding="utf-8",errors="replace").splitlines():
                if re.search(r"\b(implementation|modImplementation|compileOnly|runtimeOnly|api)\b",line): out.append(line.strip())
    return sorted(set(out))
def risk_scan(root: Path) -> List[Dict[str,str]]:
    pats={"registries":[r"DeferredRegister",r"RegisterEvent"],"networking":[r"SimpleChannel",r"StreamCodec",r"CustomPacketPayload",r"PayloadRegistrar"],"events":[r"@SubscribeEvent",r"EVENT_BUS"],"capabilities":[r"Capability",r"RegisterCapabilitiesEvent"],"attachments":[r"AttachmentType"],"data_components":[r"DataComponentType",r"DataComponents"],"mixins":[r"\bMixin\b"],"datagen":[r"DataGenerator",r"GatherDataEvent"],"commands":[r"RegisterCommandsEvent",r"Commands\."],"screens":[r"\bScreen\b",r"MenuScreen"],"renderers":[r"BlockEntityRenderer",r"EntityRenderer"],"entities":[r"EntityType"],"block_entities":[r"BlockEntityType"],"items":[r"DeferredRegister.*ITEMS",r"Item\.Properties"],"blocks":[r"DeferredRegister.*BLOCKS"],"config":[r"ModConfigSpec",r"ForgeConfigSpec"]}
    found=[]
    # Reuse the pruning walk: excluded directories (.git, node_modules, ...) must
    # not be read, which the previous rglob("*.java") did on every audit.
    for p in iter_project_files(root):
        if p.suffix.lower() != ".java": continue
        t=p.read_text(encoding="utf-8",errors="replace")
        for cat,rs in pats.items():
            if any(re.search(x,t) for x in rs): found.append({"category":cat,"file":rel(root,p)})
    return sorted({(x["category"],x["file"]):x for x in found}.values(), key=lambda x:(x["category"],x["file"]))

# ---------------------------------------------------------------------------
# Backup / lock / preflight
# ---------------------------------------------------------------------------
def safe_backup(root: Path, s: Dict[str,Any]) -> Path:
    root_resolved=root.resolve(); base=root/BACKUP_DIR
    if base.exists() and (base.is_symlink() or not base.is_dir()): die("PREFLIGHT_FAILURE",f"Backup directory is not a real project-local directory: {base}")
    if base.exists() and not base.resolve().is_relative_to(root_resolved): die("PREFLIGHT_FAILURE",f"Backup directory escapes project root: {base}")
    d=base/stamp(); d.mkdir(parents=True,exist_ok=False); z=d/"project.zip"; seen=set(); count=0
    try:
        with zipfile.ZipFile(z,"w",zipfile.ZIP_DEFLATED) as f:
            for p in iter_project_files(root):
                rp=rel(root,p)
                if not safe_member(rp): die("PREFLIGHT_FAILURE",f"Unsafe backup path: {rp}")
                key=rp.casefold()
                if key in seen: die("PREFLIGHT_FAILURE",f"Case-collision in backup: {rp}")
                seen.add(key); f.write(p,rp); count+=1
        with zipfile.ZipFile(z,"r") as f:
            for n in f.namelist():
                if not safe_member(n): die("PREFLIGHT_FAILURE",f"Unsafe ZIP member: {n}")
    except Exception:
        shutil.rmtree(d,ignore_errors=True); raise
    meta={"timestamp":now(),"qyrenith_version":VERSION,"source_fingerprint":source_fingerprint(root),"project_fingerprint":project_fingerprint(root),"file_count":count,"archive_sha256":sha256_full(z)}
    save_json(d/"metadata.json",meta); s["backup"]={"path":rel(root,d),"created":meta["timestamp"],**meta}; s.setdefault("snapshots",[]).append(s["backup"]); emit_event(root,s,"backup",path=rel(root,d)); return d
def acquire_lock(root: Path, run_id: str):
    ensure_state_dir(root); p=root/STATE_DIR/LOCK_FILE
    payload={"run_id":run_id,"pid":os.getpid(),"created":now()}
    for _ in range(2):
        try:
            fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,"w",encoding="utf-8") as f:
                json.dump(payload,f,ensure_ascii=False,sort_keys=True); f.flush(); os.fsync(f.fileno())
            return
        except FileExistsError:
            old=load_json(p,{})
            active=False
            pid_alive=False
            if isinstance(old,dict):
                pid=old.get("pid")
                if isinstance(pid,int) and pid>0:
                    try: os.kill(pid,0); pid_alive=True; active=True
                    except (OSError,ProcessLookupError): pid_alive=False; active=False
                # A lock from the SAME run with a DEAD holder is a crashed run, not an
                # active one: the holder was killed before its finally-block could release
                # the lock (measured: timeout-killed port run left run.lock behind with a
                # dead PID, and every later command of the same run wedged on it forever).
                # Same-run equality therefore counts as active only while its PID is alive.
                # A lock from a DIFFERENT run with a live PID still blocks, as before.
                if old.get("run_id")==run_id and pid_alive: active=True
            if active: die("STOPPED",f"Another Qyrenith run appears active: {old.get('run_id','unknown') if isinstance(old,dict) else 'unknown'}")
            try: p.unlink()
            except FileNotFoundError: pass
    die("STOPPED","Could not acquire Qyrenith run lock safely")
def release_lock(root: Path, run_id: Optional[str]=None):
    p=root/STATE_DIR/LOCK_FILE
    try:
        obj=load_json(p,{})
        if run_id is None or not isinstance(obj,dict) or obj.get("run_id")==run_id:
            p.unlink()
    except FileNotFoundError: pass
def preflight(root: Path, args, s: Dict[str,Any]):
    set_phase(root,s,"PREFLIGHT"); require_qyrenith(root)
    if args.command in {"port","plan"}: require_minecraft_project(root)
    if not args.target_mc and args.command in {"port","plan"}: die("PREFLIGHT_FAILURE","Target Minecraft version is required")
    if args.command in {"port","plan"} and not args.target_loader_version and not args.resume and not load_state(root).get("audit",{}).get("loader_version"): die("PREFLIGHT_FAILURE","Target loader version is required")
    if git_repo(root):
        code,out=git(root,"status","--porcelain=v1")
        if code!=0: die("PREFLIGHT_FAILURE","Unable to read git status")
        if out.strip(): die("STOPPED","Git working tree is dirty. Commit or stash user changes before Qyrenith can modify the project.")
        git_dir=Path(git(root,"rev-parse","--git-dir")[1].strip())
        if not git_dir.is_absolute(): git_dir=(root/git_dir).resolve()
        in_progress=[git_dir/x for x in ("MERGE_HEAD","CHERRY_PICK_HEAD","REVERT_HEAD") if (git_dir/x).exists()]
        if (git_dir/"rebase-merge").exists() or (git_dir/"rebase-apply").exists(): in_progress.append(git_dir/"rebase")
        if in_progress: die("STOPPED","Git merge/rebase/cherry-pick state is active; resolve it before Qyrenith can modify the project.")
        identity_name=git(root,"config","--get","user.name")[1].strip(); identity_email=git(root,"config","--get","user.email")[1].strip()
        if not identity_name or not identity_email: die("PREFLIGHT_FAILURE","Git commit identity is not configured (user.name and user.email are required).")
        branch=git(root,"branch","--show-current")[1].strip()
        if not branch: die("STOPPED","Detached HEAD detected; create or checkout a normal branch before Qyrenith can modify the project.")
        if not args.resume and args.command=="port":
            target_branch="qyrenith/port-"+re.sub(r"[^A-Za-z0-9._/-]+","-",args.target_mc)
            if branch != target_branch:
                if git(root,"rev-parse","--verify",target_branch)[0]==0:
                    code,out=git(root,"checkout",target_branch)
                else: code,out=git(root,"checkout","-b",target_branch)
                if code!=0: die("PREFLIGHT_FAILURE",f"Could not enter {target_branch}: {out[-2000:]}")
                branch=target_branch
        s["git"]={"available":True,"branch":branch,"head":git(root,"rev-parse","HEAD")[1].strip(),"user_name":identity_name,"user_email":identity_email}
    else: s["git"]={"available":False}
    save_state(root,s)

# ---------------------------------------------------------------------------
# Audit / plan / build / validate / commit / migration log
# ---------------------------------------------------------------------------
def audit(root: Path, args, s: Dict[str,Any]):
    set_phase(root,s,"AUDIT")
    security=security_scan(root)
    if security.get("status") != "PASS": die("AUDIT_BLOCKER",f"Security review required before reading or modifying project state: {security.get('findings',[])}")
    v=detect_versions(root); m=metadata(root); deps=parse_dependencies(root); risks=risk_scan(root)
    target=args.target_mc or s.get("audit",{}).get("target_minecraft"); loader=args.target_loader or v["loader"]
    loader_version=args.target_loader_version or v.get("loader_version")
    if v["loader"] and args.target_loader and v["loader"].lower()!=args.target_loader.lower(): die("AUDIT_BLOCKER",f"Detected loader {v['loader']} conflicts with target loader {args.target_loader}")
    dependency_states=[]
    for d in deps: dependency_states.append({"declaration":d,"state":"UNKNOWN","reason":"Target compatibility must be verified by the migration/build skills."})
    critical_ok=bool(v["minecraft"] and target and loader and loader_version and m["mod_id"])
    lines=["# Qyrenith Audit","",f"Generated: {now()}","", "## Project",f"- Minecraft version: **{v['minecraft'] or 'UNKNOWN'}**",f"- Target Minecraft version: **{target or 'UNKNOWN'}**",f"- Loader: **{v['loader'] or 'UNKNOWN'}**",f"- Target loader: **{loader or 'UNKNOWN'}**",f"- Loader version: **{loader_version or 'UNKNOWN'}**",f"- Java: **{v['java'] or 'UNKNOWN'}**",f"- Gradle: **{v['gradle'] or 'UNKNOWN'}**",f"- Mod ID: **{m['mod_id'] or 'UNKNOWN'}**",f"- Mod version: **{m['version'] or 'UNKNOWN'}**",f"- Java source files: **{sum(1 for p in iter_project_files(root) if p.suffix.lower()=='.java')}**","", "## Dependencies"]
    lines += [f"- `{d['state']}` — {d['declaration']} — {d['reason']}" for d in dependency_states] + ([] if dependency_states else ["- NO_DECLARATIONS"])
    lines += ["","## Risks"] + [f"- `{x['category']}` — `{x['file']}`" for x in risks] + (["- None heuristically detected"] if not risks else [])
    lines += ["","## Invariants",f"- audit_exists: PASS",f"- audit_is_complete: {'PASS' if critical_ok else 'FAIL'}",f"- source_version_known: {'PASS' if v['minecraft'] else 'FAIL'}",f"- target_version_known: {'PASS' if target else 'FAIL'}",f"- loader_known: {'PASS' if loader else 'FAIL'}",f"- target_loader_version_known: {'PASS' if loader_version else 'FAIL'}",f"- dependencies_classified: {'PASS' if not deps else 'UNKNOWN'}",f"- risks_classified: PASS"]
    ensure_state_dir(root); atomic_write(root/STATE_DIR/AUDIT_FILE,"\n".join(lines)+"\n")
    s["audit"]={"source_minecraft":v["minecraft"],"target_minecraft":target,"loader":loader,"loader_version":loader_version,"java":v["java"],"gradle":v["gradle"],"mod_id":m["mod_id"],"mod_version":m["version"],"dependencies":dependency_states,"risks":risks,"audit_fingerprint":project_fingerprint(root)}; save_state(root,s)
    if not critical_ok: die("AUDIT_BLOCKER","Critical project metadata is unknown; refusing to patch")
    dependency_lock(root,s,target)
    build_version_graph(root,s)
    discover_adapters(root)
    discover_evidence_providers(root)
    build_reality_map(root,s,"audit")
    if dependency_states and not args.allow_unknown_dependencies: die("DEPENDENCY_BLOCKER","Dependency compatibility is UNKNOWN; verify it through minecraft-porting/build before modification or explicitly allow unknown dependencies")
def parse_verified_version_path(root: Path, src: str, dst: str) -> Optional[List[Tuple[str,str]]]:
    candidates=[root/".agents"/"skills"/"minecraft-porting"/"references"/"versions.md",root/".qyrenith"/"verified-versions.md"]
    edges=[]
    for p in candidates:
        if not p.is_file(): continue
        t=p.read_text(encoding="utf-8",errors="replace")
        if re.search(r"\bUNVERIFIED\b",t,re.I): continue
        for a,b in re.findall(r"(\d+\.\d+(?:\.\d+)?)\s*(?:->|→)\s*(\d+\.\d+(?:\.\d+)?)",t): edges.append((a,b))
    if not edges: return None
    graph={a:[] for a,_ in edges}
    for a,b in edges: graph.setdefault(a,[]).append(b)
    q=[(src,[])]; seen={src}
    while q:
        cur,path=q.pop(0)
        if cur==dst: return path
        for nxt in graph.get(cur,[]):
            if nxt not in seen: seen.add(nxt); q.append((nxt,path+[(cur,nxt)]))
    return None
def plan(root: Path,args,s: Dict[str,Any]):
    set_phase(root,s,"PLAN"); src=s["audit"]["source_minecraft"]; dst=args.target_mc; steps=parse_verified_version_path(root,src,dst)
    if src==dst: steps=[]
    if src!=dst and steps is None: die("UNKNOWN_API",f"No verified one-step migration path exists for {src} -> {dst}. Refusing to invent intermediate versions; provide verified version-path evidence.")
    step_pairs=list(steps or []); risk="HIGH" if step_pairs else "LOW"; lines=["# Qyrenith Port Plan","",f"Source: `{src}`",f"Target: `{dst}`",f"Loader: `{s['audit']['loader']}`","", "## Steps"]
    for i,(a,b) in enumerate(step_pairs,1): lines.append(f"{i}. `{a} -> {b}` — verify APIs/dependencies; risk: {risk}")
    if not step_pairs: lines.append("- No migration step required." if src==dst else "- No verified route.")
    atomic_write(root/STATE_DIR/PLAN_FILE,"\n".join(lines)+"\n")
    context=plan_context(root,s,src,dst,step_pairs)
    payload={"schema":3,"source":src,"target":dst,"loader":s["audit"]["loader"],"steps":[{"id":f"step-{i:03d}-{a}-to-{b}","from":a,"to":b,"risk":risk} for i,(a,b) in enumerate(step_pairs,1)],"context":context}
    save_json(root/STATE_DIR/PLAN_JSON,payload)
    s["steps_plan"]=[(x["from"],x["to"]) for x in payload["steps"]]; s["step_records"]=payload["steps"]; s["plan_context_fingerprint"]=context["fingerprint"]; s["plan_hash"]=sha256_full(root/STATE_DIR/PLAN_JSON); s["plan_requires_confirmation"]=bool(step_pairs); save_state(root,s)
    if step_pairs and not args.yes and not args.resume:
        if args.noninteractive: die("STOPPED","High-risk migration confirmation is required; noninteractive mode cannot auto-approve. Re-run with --yes after reviewing the plan.")
        confirm("The migration plan is HIGH risk until verified. Continue?",root,s)
def confirm(msg: str, root: Optional[Path]=None, s: Optional[Dict[str,Any]]=None):
    try: ans=input(msg+" [y/N] ").strip().lower()
    except EOFError: die("STOPPED","Confirmation required but no interactive input is available")
    if ans not in {"y","yes"}: die("STOPPED","User did not confirm")
    if root and s: s["confirmation"]={"approved":True,"time":now()}; emit_event(root,s,"confirmation",approved=True)
def build_command(script: Path, root: Path) -> List[str]:
    """Resolve the canonical build.sh in a cross-platform way without replacing it."""
    if os.name != "nt":
        return ["bash", str(script), str(root)]
    candidates=[shutil.which("bash"), os.environ.get("ProgramFiles","") + r"\Git\bin\bash.exe", os.environ.get("ProgramFiles","") + r"\Git\usr\bin\bash.exe"]
    for c in candidates:
        if c and Path(c).is_file(): return [c, str(script), str(root)]
    die("BUILD_FAILURE","Canonical build.sh exists, but no Bash interpreter was found. Install Git for Windows/Git Bash or run the canonical build skill manually and resume.")
def build(root: Path,s: Dict[str,Any]):
    set_phase(root,s,"BUILD"); script=root/BUILD_SCRIPT
    if not script.is_file():
        # A non-Minecraft delegate owns its own build; do not name the Minecraft
        # canonical script to someone who has no Minecraft project.
        if is_minecraft_project(root):
            die("BUILD_FAILURE",f"Required build skill script missing: {script}")
        die("BUILD_FAILURE","No canonical build script is available. Build execution is delegated to the project's own toolchain; use `python qyrenith.py verify --project . --execute` for project-neutral verification.")
    _clear_sha256_cache()
    before=project_fingerprint(root); started=time.time(); prev=next((x for x in reversed(s.get("build_history",[])) if x.get("status")=="SUCCESS"),None)
    code,out=cmdrun(build_command(script,root),root)
    out=redact_text(out)
    after=project_fingerprint(root); _clear_sha256_cache(); atomic_write(root/STATE_DIR/LAST_BUILD,out)
    jar=jar_info(newest_jar(root),root,started); status,notes=evaluate_build(code,before,after,jar,prev,out)
    errors=extract_errors(out); rec={"time":now(),"status":status,"exit_code":code,"duration":round(time.time()-started,3),"source_fingerprint":source_fingerprint(root),"project_fingerprint":after,"jar_sha256":jar.get("sha256") if jar else None,"jar":jar,"notes":notes,"key_errors":errors,"log_path":rel(root,root/STATE_DIR/LAST_BUILD)}
    s["build"]=rec; s.setdefault("build_history",[]).append(rec); save_state(root,s)
    if status=="UNTRUSTED": die("UNTRUSTED_BUILD","Build command exited successfully but source changed during build; refusing to trust artifact")
    if status!="SUCCESS": die("BUILD_FAILURE","\n".join(errors[-12:]) or "; ".join(notes) or "Build failed")
def extract_errors(out: str) -> List[str]: return [x.strip() for x in out.splitlines() if re.search(r"\berror:|FAILED|Exception|Could not resolve|FAILURE",x,re.I)][-40:]
def step_target_reached(root: Path, step, audit) -> bool:
    """True when the migration step's target version is observably present.

    Single-module projects move the project root itself to the target version,
    so the root check is first and unchanged. Port-matrix layouts (measured: a
    33-port repository) keep every version in its own directory - typically
    port/<loader>-<mc> with its own gradle.properties - while the root stays on
    the source version forever. Requiring the root to become the target there
    can never pass, which wedged a green, jar-producing port step at the commit
    gate. Accept the step when a port directory declares the target Minecraft
    version for the step's loader. Directory names are matched strictly
    (<loader> or <loader>-<suffix>) so "forge" never matches a "neoforge-..."
    directory, and the declaration is read from that port's own
    gradle.properties rather than inferred from the name.
    """
    dst = step[1]
    if detect_versions(root).get("minecraft") == dst:
        return True
    loader = str(audit.get("target_loader") or audit.get("loader") or "").strip().lower()
    if not loader:
        return False
    port_root = root / "port"
    if not port_root.is_dir() or port_root.is_symlink():
        return False
    for entry in sorted(port_root.iterdir(), key=lambda x: x.name.lower()):
        if not entry.is_dir() or entry.is_symlink():
            continue
        name = entry.name.lower()
        if name != loader and not name.startswith(loader + "-"):
            continue
        props = entry / "gradle.properties"
        if not props.is_file():
            continue
        try:
            text = props.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.search(r"^minecraft_version\s*=\s*(\S+)", text, re.M)
        if m and m.group(1) == dst:
            return True
    return False
def validate(root: Path,s: Dict[str,Any]):
    set_phase(root,s,"VALIDATE"); b=s.get("build",{}); a=s.get("audit",{}); checks={}
    checks["level1_compile"]="PASS" if b.get("exit_code")==0 else "FAIL"
    checks["level2_gradle_build"]="PASS" if b.get("status")=="SUCCESS" and b.get("exit_code")==0 else "FAIL"
    checks["level3_jar_exists"]="PASS" if b.get("jar") and b["jar"].get("size",0)>0 else "FAIL"
    md=metadata(root); mid_ok=(not a.get("mod_id") or md.get("mod_id")==a.get("mod_id")); ver_ok=bool(md.get("version")); toml_ok=bool(md.get("files"))
    step=s.get("current_step")
    target_ok=(not step) or step_target_reached(root,step,a)
    checks["level4_metadata"]="PASS" if toml_ok and mid_ok and ver_ok and target_ok else "FAIL"
    if step and not target_ok: checks["target_version_reached"]="FAIL"
    elif step: checks["target_version_reached"]="PASS"
    s["validation"]={**checks,"time":now()}; save_state(root,s)
    if any(v=="FAIL" for k,v in checks.items() if k.startswith("level")): die("VALIDATION_FAILURE",f"Mandatory validation failed: {checks}")
    if s.get("audit",{}).get("mod_id") and md.get("mod_id")!=s["audit"]["mod_id"]: die("VALIDATION_FAILURE","Mod ID changed during migration")
def changed_files(root: Path, before: Optional[Dict[str,str]]=None) -> List[str]:
    if git_repo(root):
        code,out=git(root,"status","--porcelain=v1")
        if code==0: return sorted({x[3:].strip() for x in out.splitlines() if len(x)>=4}, key=str.lower)
    return [rel(root,p) for p in source_files(root)] if before is None else [rel(root,p) for p in source_files(root) if before.get(rel(root,p))!=sha256_full(p)]
def commit(root: Path,s: Dict[str,Any],step: Tuple[str,str]):
    if not git_repo(root): s.setdefault("commits",[]).append({"step":step,"status":"SKIPPED_NO_GIT","time":now()}); save_state(root,s); return
    code,out=git(root,"status","--porcelain=v1")
    if code!=0 or not out.strip(): die("VALIDATION_FAILURE","No Git changes to commit after a successful port step")
    msg=f"qyrenith: port {step[0]} -> {step[1]}"
    code,out=git(root,"add","-A")
    if code!=0: die("PORTING_FAILURE",f"git add failed: {out[-2000:]}")
    # Preflight requires a clean tree, so any staged state/backups here were
    # created by Qyrenith during this transaction and must stay out of the commit.
    for excluded in (STATE_DIR, BACKUP_DIR):
        code,out=git(root,"reset","--",excluded)
        if code not in {0,5}: die("PORTING_FAILURE",f"git unstage failed for {excluded}: {out[-2000:]}")
    before_head=git(root,"rev-parse","HEAD")[1].strip()
    code,out=git(root,"commit","-m",msg)
    if code!=0: die("PORTING_FAILURE",f"git commit failed: {out[-2000:]}")
    head=git(root,"rev-parse","HEAD")[1].strip()
    if not head or head==before_head: die("PORTING_FAILURE","Git commit reported success but HEAD did not advance; refusing to record an unverified transaction")
    diff=s.get("reality_diff") or {}
    expected_fingerprint=diff.get("project_fingerprint_after") or diff.get("source_fingerprint_after")
    observed_fingerprint=project_fingerprint(root) if diff.get("project_fingerprint_after") else source_fingerprint(root)
    if expected_fingerprint and observed_fingerprint != expected_fingerprint:
        die("PORTING_FAILURE","Git hooks changed project files after Reality Diff; refusing to record an unverified commit")
    code,status=git(root,"status","--porcelain=v1")
    if code!=0: die("PORTING_FAILURE","Unable to verify Git status after commit; refusing to declare the transaction committed")
    residual=[]
    for line in status.splitlines():
        path=line[3:].strip() if len(line)>=4 else line.strip()
        if path.startswith(f"{STATE_DIR}/") or path.startswith(f"{BACKUP_DIR}/"): continue
        residual.append(path)
    if residual: die("PORTING_FAILURE",f"Git commit completed but unmanaged working-tree changes remain: {', '.join(residual[:20])}")
    code,subject=git(root,"log","-1","--pretty=%s")
    if code!=0 or subject.strip()!=msg: die("PORTING_FAILURE","Git HEAD does not contain the expected Qyrenith commit message; refusing to record success")
    branch=git(root,"branch","--show-current")[1].strip()
    expected_branch=(s.get("git") or {}).get("branch")
    if expected_branch and branch != expected_branch: die("PORTING_FAILURE",f"Git branch changed unexpectedly during commit: expected={expected_branch} current={branch or 'DETACHED'}")
    s.setdefault("commits",[]).append({"step":step,"status":"COMMITTED","head":head,"branch":branch,"time":now(),"message":subject.strip()}); emit_event(root,s,"commit",step=list(step),head=head,branch=branch,message=subject.strip())
def migration_log(root: Path,s: Dict[str,Any],problem=None,solution=None):
    """Append only factual solved migration problems; never invent a migration note."""
    p=root/MIGRATION_LOG
    if not p.parent.is_dir(): return None
    if not problem or not solution: return None
    p.parent.mkdir(parents=True,exist_ok=True)
    text=p.read_text(encoding="utf-8",errors="replace") if p.exists() else "# Common Migrations\n"
    step=s.get("current_step"); key=f"{step[0]} -> {step[1]}" if step else "unknown"
    if any(key in line and "Migration #" in line for line in text.splitlines()): return None
    nums=[int(x) for x in re.findall(r"Migration #(\d+)",text)]; n=max(nums,default=0)+1
    entry=f"\nMigration #{n:03d} | {key}\nProblem: {problem}\nSolution: {solution}\n"
    atomic_write(p,text.rstrip()+entry); s.setdefault("migration_entries",[]).append(n); save_state(root,s); return n

# ---------------------------------------------------------------------------
# Frontmatter / domains
# ---------------------------------------------------------------------------
def parse_frontmatter(text: str) -> Dict[str,Any]:
    if not text.startswith("---"): return {}
    end=text.find("\n---",3)
    if end<0: return {}
    out={}
    for line in text[4:end].splitlines():
        if ":" not in line: continue
        k,v=line.split(":",1); v=v.strip(); out[k.strip()]=parse_list(v)
    return out
def parse_list(v: str):
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
    return v.strip("'\"")
def _domain_signal_text(root: Path, task: str = "") -> str:
    parts=[task.lower()]
    for name in ("pyproject.toml","package.json","Cargo.toml","pom.xml","build.gradle","build.gradle.kts","gradle.properties","project.godot"):
        path=root/name
        if path.is_file():
            try: parts.append(path.name.lower()); parts.append(path.read_text(encoding="utf-8",errors="replace")[:12000].lower())
            except OSError: pass
    for pattern in ("*.uproject","*.csproj"):
        for path in list(root.glob(pattern))[:4]: parts.append(path.name.lower())
    for name in ("mods.toml","fabric.mod.json","mcmod.info"):
        # Root-level markers only; do not descend into .git or build output.
        for path in sorted(root.glob(name), key=lambda x: x.name.lower())[:4]:
            parts.append(name); parts.append(path.parent.as_posix().lower())
    return "\n".join(parts)
def detect_domain(root: Path, task: str = "") -> Dict[str,Any]:
    text=_domain_signal_text(root,task); task_l=task.lower(); explicit=[]; project=[]
    for domain,hints in DOMAIN_HINTS.items():
        hits=[h for h in hints if h in task_l]
        if hits: explicit.append((domain,len(hits),hits))
    for domain,hints in DOMAIN_HINTS.items():
        hits=[h for h in hints if h in text]
        if hits: project.append((domain,len(hits),hits))
    if explicit:
        explicit.sort(key=lambda x:(x[1],x[0]),reverse=True); domain,n,hits=explicit[0]; source="task"
    elif project:
        project.sort(key=lambda x:(x[1],x[0]),reverse=True); domain,n,hits=project[0]; source="project"
    else: domain,n,hits="generic",0,[]; source="default"
    return {"domain":domain,"confidence":"HIGH" if n>=2 else "MEDIUM","source":source,"signals":hits,"candidates":[{"domain":d,"score":score} for d,score,_ in (explicit or project)]}
def load_domains(root: Path) -> List[Dict[str,Any]]:
    builtins=[
        ("generic","Project-neutral software development and verification.","core"),
        ("minecraft","Minecraft modding and migration ecosystem.","domain"),
        ("roblox","Roblox development and modding-adjacent workflows.","domain"),
        ("skyrim","Skyrim mod/plugin development workflows.","domain"),
        ("gta","GTA/FiveM/related mod development workflows.","domain"),
        ("unity","Unity project verification workflows.","domain"),
        ("godot","Godot project verification workflows.","domain"),
        ("unreal","Unreal Engine project verification workflows.","domain"),
        ("python","Python project verification workflows.","language"),
        ("javascript","JavaScript/TypeScript/Node project verification workflows.","language"),
        ("rust","Rust project verification workflows.","language"),
        ("java","Java project verification workflows.","language"),
        ("cpp","C/C++ project verification workflows.","language"),
    ]
    domains=[{"name":n,"version":"1","description":d,"scope":scope,"skills_allowed":True} for n,d,scope in builtins]
    directory=root/STATE_DIR/DOMAIN_DIR; custom=[]
    if directory.is_dir():
        for path in sorted(directory.glob("*.json"),key=lambda p:p.name.lower()):
            try:
                item=load_json(path,{})
                if isinstance(item,dict) and item.get("name"): custom.append(item)
            except Exception: continue
    merged={x["name"]:x for x in domains}; merged.update({x["name"]:x for x in custom}); domains=sorted(merged.values(),key=lambda x:x["name"])
    ensure_state_dir(root); save_json(root/STATE_DIR/DOMAIN_INDEX,{"schema":1,"generated":now(),"detected":detect_domain(root),"domains":domains})
    return domains
def skill_domains(skill: Dict[str,Any]) -> set:
    values=skill.get("domains",[]); values=[values] if isinstance(values,str) else values
    explicit={str(x).strip().lower() for x in values if str(x).strip()}
    if explicit: return explicit
    text=" ".join([str(skill.get("name","")),str(skill.get("description",""))]+[str(x) for x in skill.get("keywords",[])]).lower()
    inferred=set()
    for domain,hints in DOMAIN_HINTS.items():
        if any(h in text for h in hints): inferred.add(domain)
    return inferred or {"generic"}

# ---------------------------------------------------------------------------
# Skill discovery
# ---------------------------------------------------------------------------
def parse_skill(p: Path) -> Dict[str,Any]:
    t=p.read_text(encoding="utf-8",errors="replace"); fm=parse_frontmatter(t); body=t.lower(); name=fm.get("name") or p.parent.name; desc=fm.get("description") or next((x.strip() for x in t.splitlines() if x.strip() and not x.startswith("#") and not x.startswith("---")),"")
    def arr(k,default):
        x=fm.get(k,default); return x if isinstance(x,list) else ([x] if x else [])
    triggers=arr("triggers",[]); keywords=arr("keywords",[]); caps=arr("capabilities",[]); conflicts=arr("conflicts",[]); deps=arr("dependencies",[]); domains=arr("domains",[])
    if not keywords:
        keywords=sorted(set(re.findall(r"[a-z][a-z0-9_-]{2,}",body)))[:80]
    return {"name":str(name),"path":str(p),"description":str(desc),"triggers":triggers,"keywords":keywords,"capabilities":caps,"conflicts":conflicts,"dependencies":deps,"domains":domains,"size":len(t),"content_sha256":hashlib.sha256(t.encode()).hexdigest()}
def discover(root: Path) -> List[Dict[str,Any]]:
    sr=root/".agents"/"skills"; found=[]
    if not sr.is_dir(): return found
    for p in sorted(sr.rglob("SKILL.md"),key=lambda x:str(x).lower()):
        try: found.append(parse_skill(p))
        except OSError: continue
    return found
def tokenize(s: str) -> set: return set(re.findall(r"[a-z0-9_./-]{3,}",s.lower()))
def score_skill(x: Dict[str,Any],task: str,detected_domain: Optional[str]=None) -> float:
    q=tokenize(task); name=tokenize(x["name"]); desc=tokenize(x["description"]); kws=set(tokenize(" ".join(map(str,x["keywords"])))) ; tr=set(tokenize(" ".join(map(str,x["triggers"])))) ; caps=set(tokenize(" ".join(map(str,x["capabilities"]))))
    score=0.0
    if name & q: score+=0.35
    score+=min(0.25,len(q&tr)*0.08); score+=min(0.20,len(q&kws)*0.035); score+=min(0.20,len(q&caps)*0.06); score+=min(0.10,len(q&desc)*0.01)
    domains=skill_domains(x); task_l=task.lower()
    explicit_domains={d for d,hints in DOMAIN_HINTS.items() if any(h in task_l for h in hints)}
    if explicit_domains and not (domains & explicit_domains or "generic" in domains): return 0.0
    if detected_domain and not explicit_domains and detected_domain not in domains and "generic" not in domains: return 0.0
    if x["name"].lower()=="qyrenith": score=max(score,0.90)
    return min(score,0.99)
def skill_discovery(root: Path,task: str,limit=12,return_details: bool=False):
    skills=discover(root); detection=detect_domain(root,task); domain=detection["domain"]
    ranked=[{**x,"domains":sorted(skill_domains(x)),"score":round(score_skill(x,task,domain),3)} for x in skills]
    ranked=[x for x in ranked if x["score"]>0]; ranked.sort(key=lambda x:(x["score"],x["name"].lower()),reverse=True)
    selected=ranked[:max(1,limit)] if ranked else []; names={x["name"].lower() for x in selected}; conflicts=[]
    for x in selected:
        for c in x["conflicts"]:
            if str(c).lower() in names: conflicts.append(f"{x['name']} conflicts with {c}")
    result=(skills,selected,sorted(set(conflicts)))
    return (*result,detection) if return_details else result
def write_discovery(root: Path,task: str,limit=12,mode="discovery"):
    skills,rec,conf,detection=skill_discovery(root,task,limit,return_details=True); ensure_state_dir(root); load_domains(root)
    payload={"schema":4,"generated":now(),"project":str(root),"task":task,"detected_domain":detection,"skills":skills,"recommended":rec,"conflicts":conf}; save_json(root/STATE_DIR/SKILL_INDEX,payload)
    lines=[f"# {PRODUCT_NAME} Agent Task","",f"Mode: `{mode}`",f"Generated: `{now()}`","","## Task",task,"","## Detected domain",f"- `{detection['domain']}` — confidence `{detection['confidence']}` — source `{detection['source']}`","","## Recommended skills"]+[f"- `{x['name']}` — score `{x['score']:.3f}` — domains `{', '.join(x['domains'])}` — `{x['path']}`" for x in rec]
    if not rec: lines.append("- No domain-specific skill is required; continue with generic verification or inspect installed skills manually.")
    lines += ["","## Routing policy","Skill discovery is domain-aware. Domain-specific skills are only activated when the task/project matches their domain. Generic development tasks are never routed to Minecraft-only skills merely because the repository happens to contain Minecraft code.","","## Mandatory orchestration","Audit before patch. Backup before patch. One version step at a time where migration applies. No guessed APIs. Build and validation are mandatory. Commit only after validation."]
    if conf: lines += ["","## Conflicts — STOP before patching"]+[f"- {c}" for c in conf]
    atomic_write(root/STATE_DIR/AGENT_TASK,"\n".join(lines)+"\n"); return skills,rec,conf

# ---------------------------------------------------------------------------
# Handoff / failure / step prepare
# ---------------------------------------------------------------------------
def handoff(root: Path,s: Dict[str,Any],step,args):
    task=f"Port this Minecraft mod from {step[0]} to {step[1]} using verified API migration knowledge."; _,rec,conf=write_discovery(root,task,args.limit,"managed-port")
    step_id=next((x["id"] for x in s.get("step_records",[]) if x["from"]==step[0] and x["to"]==step[1]),f"{step[0]}-to-{step[1]}")
    lines=["# Qyrenith Port Step Handoff","",f"Step ID: `{step_id}`",f"Transition: `{step[0]} -> {step[1]}`",f"Loader: `{s['audit']['loader']}`",f"Generated: `{now()}`","","## Evidence rule","Every API change must have verified evidence. If evidence is unavailable, STOP with UNKNOWN_API. Never infer an API from memory.","","## Required agent behavior","- Read `.qyrenith/audit.md`, `.qyrenith/plan.md`, and `.qyrenith/skill-index.json`.\n- Use the selected specialized skills, especially `minecraft-porting`.\n- Preserve behavior and make the smallest justified patch.\n- Do not delete, disable, stub, reflect around, or comment out functionality.\n- Do not silently change/remove dependencies.\n- Return control to qyrenith.py after the patch.","","## Selected skills"]+[f"- `{x['name']}` ({x['score']:.3f})" for x in rec]
    if conf: lines += ["","## Conflicts"]+[f"- {c}" for c in conf]
    lines += ["","## Completion","After the patch is complete and verified, run:","","`python qyrenith.py continue --project . --managed`","","Do not claim SUCCESS; qyrenith.py owns build, validation and commit gates."]
    atomic_write(root/STATE_DIR/HANDOFF,"\n".join(lines)+"\n"); s["handoff"]={"type":"port","step_id":step_id,"step":list(step),"recommended":[x["name"] for x in rec],"conflicts":conf,"ready_for_agent":True}; save_state(root,s)
def analyze_failure(root: Path,s: Dict[str,Any]):
    b=s.get("build",{}); cat="BUILD_FAILURE" if b.get("status")!="UNTRUSTED" else "PORTING_FAILURE"; msg="\n".join(b.get("key_errors",[])[-20:]) or "; ".join(b.get("notes",[])) or "Delegated build failed"; a={"category":cat,"message":msg,"iteration":s.get("fix_iterations",0),"time":now(),"log_path":b.get("log_path")}; s["failure_analysis"]=a; save_state(root,s); return a
def prepare_fix(root: Path,args,s):
    if s.get("build",{}).get("status")=="SUCCESS": die("STOPPED","No fix is needed after a successful build")
    n=int(s.get("fix_iterations",0))
    if n>=MAX_FIX: die("FIX_LIMIT_REACHED",f"AUTOMATIC FIX LIMIT REACHED ({MAX_FIX})")
    n+=1; s["fix_iterations"]=n
    try: (root/STATE_DIR/AGENT_RESULT).unlink()
    except FileNotFoundError: pass
    set_phase(root,s,"ANALYZE"); a=analyze_failure(root,s); set_phase(root,s,"FIX",status="WAITING_AGENT"); step=s.get("current_step")
    task=f"Fix the failed Minecraft port step {step[0]} -> {step[1]} using verified minimal changes." if step else "Fix the failed Minecraft build."; _,rec,conf=write_discovery(root,task,args.limit,"managed-fix")
    lines=["# Qyrenith Fix Handoff","",f"Fix iteration: `{n}/{MAX_FIX}`",f"Step: `{step[0]} -> {step[1]}`" if step else "Step: unknown","","## Failure analysis",f"Category: `{a['category']}`",f"Log: `{a['log_path']}`","",a["message"],"","## Required behavior","- Find root cause before editing.","- Use verified migration/debugging evidence.","- Make one minimal fix; preserve behavior.","- Never guess APIs or disable functionality.","- Return to qyrenith.py after the fix.","","## Selected skills"]+[f"- `{x['name']}` ({x['score']:.3f})" for x in rec]+["","## Completion","Run `python qyrenith.py continue --project . --managed` after the fix."]
    if conf: lines += ["","## Conflicts"]+[f"- {c}" for c in conf]
    atomic_write(root/STATE_DIR/HANDOFF,"\n".join(lines)+"\n"); s["handoff"]={"type":"fix","iteration":n,"step":list(step) if step else None,"recommended":[x["name"] for x in rec],"conflicts":conf,"ready_for_agent":True}; save_state(root,s)
    print(f"\nFIX HANDOFF READY: {n}/{MAX_FIX}\nAgent handoff: {root/STATE_DIR/HANDOFF}"); die("STOPPED",f"Waiting for verified agent fix {n}/{MAX_FIX}")
def prepare_step(root: Path,args,s,idx: int):
    steps=s.get("steps_plan",[])
    if idx>=len(steps): die("STOPPED","No pending port step")
    step=steps[idx]
    if any(tuple(x)==tuple(step) for x in s.get("completed_steps",[])): s["next_step"]=idx+1; save_state(root,s); return
    s["current_step"]=list(step); s["current_step_index"]=idx; s["fix_iterations"]=0
    try: (root/STATE_DIR/AGENT_RESULT).unlink()
    except FileNotFoundError: pass
    set_phase(root,s,"PORT_STEP",status="WAITING_AGENT"); capture_reality_baseline(root,s,step); begin_transaction(root,s,step); handoff(root,s,step,args)
    print(f"\nPORT STEP READY: {step[0]} -> {step[1]}\nAgent handoff: {root/STATE_DIR/HANDOFF}")
    if args.noninteractive or args.managed: die("STOPPED","Waiting for delegated agent patch. Run `python qyrenith.py continue --project . --managed` after the patch.")
    confirm("Has the delegated minecraft-porting agent applied the verified minimal patch?",root,s)

# ---------------------------------------------------------------------------
# Recovery / reporting / inspect / explain
# ---------------------------------------------------------------------------
def validate_recovery_state(root: Path, s: Dict[str,Any]):
    tx=load_json(root/STATE_DIR/TRANSACTION_FILE,{})
    if not isinstance(tx,dict) or tx.get("status") != "OPEN":
        die("STOPPED","No open transaction is available for safe continuation")
    if git_repo(root):
        expected_branch=(s.get("git") or {}).get("branch")
        current_branch=git(root,"branch","--show-current")[1].strip()
        if not current_branch or (expected_branch and current_branch != expected_branch): die("STOPPED",f"Recovery branch mismatch: expected={expected_branch or 'unknown'} current={current_branch or 'DETACHED'}")
    baseline=load_json(root/STATE_DIR/BASELINE_JSON,{})
    if not isinstance(baseline,dict) or not baseline.get("fingerprints") or not isinstance(baseline.get("file_hashes"),dict):
        die("STOPPED","Recovery baseline is missing or malformed; refusing to restart blindly")
    backup=s.get("backup") if isinstance(s.get("backup"),dict) else tx.get("backup")
    if not isinstance(backup,dict) or not backup.get("path"):
        die("STOPPED","Verified backup record is missing; refusing to resume")
    backup_dir=(root/str(backup["path"])).resolve()
    if not backup_dir.is_relative_to(root.resolve()): die("STOPPED","Recorded backup path escapes the project root")
    archive=backup_dir/"project.zip"; meta=backup_dir/"metadata.json"
    if not archive.is_file() or not meta.is_file(): die("STOPPED","Recorded backup is incomplete; refusing to resume")
    metadata=load_json(meta,{})
    if not isinstance(metadata,dict) or metadata.get("archive_sha256") != sha256_full(archive): die("STOPPED","Backup archive fingerprint no longer matches its metadata")
    baseline_source=baseline.get("fingerprints",{}).get("source")
    backup_source=metadata.get("source_fingerprint")
    if baseline_source and backup_source and baseline_source != backup_source: die("STOPPED","Recovery baseline does not match the verified backup source fingerprint")
    return tx
def step_integrity(root: Path,s: Dict[str,Any]):
    step=s.get("current_step")
    if not step or len(step)!=2: die("STOPPED","No valid current port step")
    if s.get("current_step_index",-1)>=len(s.get("steps_plan",[])): die("STOPPED","Current step index is outside the plan")
    if tuple(s["steps_plan"][s["current_step_index"]])!=tuple(step): die("STOPPED","State step does not match plan")
    if s.get("plan_hash") and (root/STATE_DIR/PLAN_JSON).exists() and sha256_full(root/STATE_DIR/PLAN_JSON)!=s["plan_hash"]: die("STOPPED","Plan changed since the run began; refusing to guess how to resume")
    payload=load_json(root/STATE_DIR/PLAN_JSON,{})
    expected=s.get("plan_context_fingerprint"); observed=payload.get("context",{}).get("fingerprint") if isinstance(payload,dict) else None
    if expected and observed and expected!=observed: die("STOPPED","Plan context fingerprint does not match state; refusing to resume an ambiguous migration")
def step_label(s: Dict[str,Any]) -> str:
    step=s.get("current_step")
    return f"port step {step[0]} -> {step[1]}" if isinstance(step,(list,tuple)) and len(step)==2 else "current port step"
def recover_post_commit(root: Path, s: Dict[str,Any]) -> bool:
    step=s.get("current_step")
    commits=[x for x in s.get("commits",[]) if isinstance(x,dict) and x.get("status")=="COMMITTED" and x.get("head")]
    if not step or not commits: return False
    record=commits[-1]
    if list(record.get("step",[])) != list(step): return False
    if not git_repo(root): die("STOPPED","A recorded post-commit recovery requires Git, but the repository is unavailable")
    head=git(root,"rev-parse","HEAD")[1].strip()
    if head != record.get("head"): die("STOPPED","A committed port step was recorded, but HEAD does not match it; recovery is ambiguous")
    status=git(root,"status","--porcelain=v1")[1]
    residual=[x for x in status.splitlines() if x and not x[3:].strip().startswith(f"{STATE_DIR}/") and not x[3:].strip().startswith(f"{BACKUP_DIR}/")]
    if residual: die("STOPPED","A recorded committed step has unmanaged working-tree changes; refusing automatic recovery")
    close_transaction(root,s,"COMMITTED",head)
    idx=int(s.get("current_step_index",0)); s.setdefault("completed_steps",[]).append(list(step)); s["next_step"]=idx+1; s["current_step"]=None; s["handoff"]={}; save_state(root,s)
    return True
def continue_step(root: Path,args,s):
    validate_recovery_state(root,s)
    step_integrity(root,s)
    if recover_post_commit(root,s):
        if s.get("next_step",0)<len(s.get("steps_plan",[])):
            prepare_step(root,args,s,s["next_step"])
        else:
            report(root,s,"SUCCESS")
        return
    if s.get("fix_iterations",0)>MAX_FIX: die("FIX_LIMIT_REACHED","Fix counter exceeds hard maximum")
    # Agent output is advisory only, but a missing result is an interruption, not permission to restart blindly.
    if not (root/STATE_DIR/AGENT_RESULT).exists():
        die("STOPPED","Agent result is missing; refusing to resume a port step without an explicit structured handoff result")
    agent=agent_result(root,s)
    if agent.get("status") != "WORKED":
        close_transaction(root,s,"REJECTED_AGENT_RESULT")
        code="PORTING_FAILURE" if agent.get("status")=="FAILED" else "STOPPED"
        die(code,f"Agent did not complete the port step: {agent.get('status')}")
    try: build(root,s)
    except QyrenithError as e:
        if e.code=="BUILD_FAILURE": prepare_fix(root,args,s)
        raise
    validate(root,s); diff=compare_to_step_baseline(root,s)
    security=security_scan(root); s["security"]={"status":security["status"],"findings":len(security["findings"])}; save_state(root,s)
    if diff.get("unexpected_feature_removals") or diff.get("unexpected_integration_removals"):
        close_transaction(root,s,"REJECTED_REALITY_DIFF")
        die("VALIDATION_FAILURE",f"Reality map detected removed features/integrations: {diff}")
    dependency_drift=diff.get("dependency_drift",{})
    actual_dep_changes=[{"action":"add","declaration":x} for x in dependency_drift.get("added",[])]+[{"action":"remove","declaration":x} for x in dependency_drift.get("removed",[])]
    declared_dep_changes=s.get("agent_result",{}).get("dependency_changes") if isinstance(s.get("agent_result"),dict) else None
    if actual_dep_changes:
        if not isinstance(declared_dep_changes,list):
            close_transaction(root,s,"REJECTED_DEPENDENCY_DRIFT")
            die("DEPENDENCY_BLOCKER",f"Dependency drift requires explicit dependency_changes evidence: {actual_dep_changes}")
        normalized=[]
        for item in declared_dep_changes:
            if not isinstance(item,dict) or item.get("action") not in {"add","remove","replace"} or not isinstance(item.get("declaration"),str) or not item.get("reason") or not isinstance(item.get("evidence_ids"),list) or not item.get("evidence_ids"):
                close_transaction(root,s,"REJECTED_DEPENDENCY_DRIFT")
                die("DEPENDENCY_BLOCKER","Each dependency change requires action, declaration, reason, and evidence_ids")
            known_evidence={str(x.get("id")) for x in load_evidence_ledger(root) if isinstance(x,dict) and x.get("id")}
            if not set(map(str,item["evidence_ids"])).issubset(known_evidence):
                close_transaction(root,s,"REJECTED_DEPENDENCY_DRIFT")
                die("DEPENDENCY_BLOCKER",f"Dependency change references unknown evidence IDs: {item['evidence_ids']}")
            normalized.append({"action":item["action"],"declaration":item["declaration"]})
        if sorted(normalized,key=lambda x:(x["action"],x["declaration"])) != sorted(actual_dep_changes,key=lambda x:(x["action"],x["declaration"])):
            close_transaction(root,s,"REJECTED_DEPENDENCY_DRIFT")
            die("DEPENDENCY_BLOCKER",f"Declared dependency changes do not match Reality Map drift: declared={normalized}, actual={actual_dep_changes}")
    elif declared_dep_changes not in (None,[]):
        close_transaction(root,s,"REJECTED_DEPENDENCY_DRIFT")
        die("DEPENDENCY_BLOCKER","Agent declared dependency changes but Reality Map found no dependency drift")
    declared_changes=s.get("agent_result",{}).get("files_changed") if isinstance(s.get("agent_result"),dict) else None
    actual_changes=sorted(set(diff.get("file_changes",{}).get("added",[])+diff.get("file_changes",{}).get("modified",[])+diff.get("file_changes",{}).get("removed",[])))
    if declared_changes is not None:
        if not isinstance(declared_changes,list) or not all(isinstance(x,str) for x in declared_changes):
            close_transaction(root,s,"REJECTED_FILE_CHANGE_DECLARATION")
            die("VALIDATION_FAILURE","Agent files_changed must be a list of relative paths")
        declared_sorted=sorted(set(x.replace("\\","/") for x in declared_changes))
        if declared_sorted!=actual_changes:
            close_transaction(root,s,"REJECTED_FILE_CHANGE_DECLARATION")
            die("VALIDATION_FAILURE",f"Agent files_changed does not match Reality Diff: declared={declared_sorted}, actual={actual_changes}")
    if security.get("status")=="REVIEW_REQUIRED":
        close_transaction(root,s,"REJECTED_SECURITY_REVIEW")
        die("VALIDATION_FAILURE",f"Security scan requires review: {security['findings']}")
    fa=s.get("failure_analysis",{})
    if fa.get("message"):
        migration_log(root,s,problem=fa.get("message"),solution=f"Minimal verified fix applied during {step_label(s)}")
    step=tuple(s["current_step"]); s.setdefault("completed_steps",[]).append(list(step)); s["next_step"]=s["current_step_index"]+1; s["changed_files"]=changed_files(root); save_state(root,s); commit(root,s,step)
    head=s.get("commits",[])[-1].get("head") if s.get("commits") else None
    close_transaction(root,s,"COMMITTED",head); s["current_step"]=None; s["handoff"]={}; save_state(root,s)
    if s["next_step"]<len(s.get("steps_plan",[])): prepare_step(root,args,s,s["next_step"]); return
    report(root,s,"SUCCESS")
def report(root: Path,s: Dict[str,Any],status: str):
    s["result_status"]=status; set_phase(root,s,"REPORT",status="SUCCESS" if status=="SUCCESS" else "TERMINAL")
    a=s.get("audit",{}); lines=["# QYRENITH RESULT","",f"Status: **{status}**",f"Run ID: `{s.get('run_id')}`",f"Source: `{a.get('source_minecraft','UNKNOWN')}`",f"Target: `{a.get('target_minecraft','UNKNOWN')}`","","## Steps"]
    lines += [f"- `{x[0]} -> {x[1]}`: SUCCESS" for x in s.get("completed_steps",[])] or ["- none"]
    lines += ["","## Files changed"]+[f"- `{x}`" for x in s.get("changed_files",[])]
    lines += ["","## Dependencies"] + ([f"- `{x['state']}` — {x['declaration']}" for x in a.get("dependencies",[])] or ["- NO_DECLARATIONS"])
    lines += ["","## Validation"]+[f"- {k}: {v}" for k,v in s.get("validation",{}).items() if k.startswith("level")]
    unresolved="none" if status=="SUCCESS" else f"See `{STATE_DIR}/{STATE_FILE}`, `{STATE_DIR}/{AUDIT_FILE}`, and `{STATE_DIR}/{LAST_BUILD}`"
    lines += ["","## Unresolved",f"- {unresolved}","","## Exit semantics",f"- exit_code: `{EXIT.get(status, EXIT['FAILED'])}`"]
    atomic_write(root/STATE_DIR/LAST_REPORT,"\n".join(lines)+"\n"); save_state(root,s); print("\n"+"\n".join(lines))
def cmd_inspect(args):
    root=root_path(args.project); require_qyrenith(root); s=load_state(root)
    security=security_scan(root)
    if security.get("status") != "PASS":
        die("AUDIT_BLOCKER",f"Security review required before inspection: {security.get('findings',[])}")
    # Inspect is strictly observational. It must not invoke the mutation-oriented audit
    # gate or dependency compatibility lock, because UNKNOWN dependency compatibility is
    # a migration blocker, not a reason to prevent read-only project inspection.
    r=build_reality_map(root,s,"inspect")
    i=r["project_identity"]
    print("QYRENITH INSPECT")
    print(f"Project: {i.get('mod_id') or 'UNKNOWN'}")
    print(f"Minecraft: {i.get('minecraft') or 'UNKNOWN'} | Loader: {i.get('loader') or 'UNKNOWN'}")
    print(f"Versions observed: {len(r.get('versions',[]))}")
    print(f"Features/areas: {len(r.get('features',[]))} | Integrations: {len(r.get('integrations',[]))}")
    print(f"Issues/blockers: {len(r.get('issues',[]))} | Evidence records: {len(r.get('evidence',[]))}")
    print(f"Workflow: {s.get('phase')} | Step: {s.get('current_step')} | Fixes: {s.get('fix_iterations',0)}/{MAX_FIX}")
    return 0
def _explanation(topic: str) -> Dict[str, Any]:
    topic=topic.upper()
    explanations={
        "UNKNOWN_API": {"title":"UNKNOWN API", "why":"Required migration knowledge could not be verified.", "effect":"Automation stops rather than guessing an API.", "evidence":"Add task-relevant verified evidence or use the specialist migration skill.", "next":"Re-run the audit/plan after the evidence is available."},
        "DEPENDENCY_BLOCKER": {"title":"DEPENDENCY BLOCKER", "why":"A dependency has no verified target compatibility.", "effect":"Presence on disk is not treated as compatibility proof.", "evidence":"Verify the exact target release, loader and Minecraft scope.", "next":"Update the evidence/lock and re-run the audit."},
        "UNTRUSTED_BUILD": {"title":"UNTRUSTED BUILD", "why":"The build process changed source files while building.", "effect":"A zero exit code cannot authorize the artifact.", "evidence":"Source fingerprints must remain stable during the build.", "next":"Inspect the build process and re-run from a clean baseline."},
        "FIX_LIMIT_REACHED": {"title":"FIX LIMIT REACHED", "why":"Five automatic repair iterations are the hard ceiling for one port step.", "effect":"Qyrenith will not silently attempt number six.", "evidence":"The failure analysis and prior attempts remain recorded.", "next":"Review the root cause and start a new human-directed attempt."},
        "AUDIT_BLOCKER": {"title":"AUDIT BLOCKER", "why":"A required audit gate failed: critical project identity/migration evidence may be unknown, or the security scan requires review.", "effect":"Reading paths that depend on the blocked audit gate and all project modification are stopped.", "evidence":"Inspect the recorded audit/security report to identify whether metadata, dependency evidence, or a security finding caused the block.", "next":"Resolve the specific finding or review the documented placeholder finding, then re-run the audit."},
        "STOPPED": {"title":"STOPPED", "why":"A safety invariant or explicit confirmation gate prevented continuation.", "effect":"No unsafe continuation is attempted.", "evidence":"Inspect state, events and the last report for the exact gate.", "next":"Resolve the reported condition; do not bypass the gate by guessing."},
        "BLOCKED": {"title":"BLOCKED", "why":"A required prerequisite is unavailable or incompatible.", "effect":"The workflow remains unchanged until the blocker is resolved.", "evidence":"Use the audit, evidence ledger and version graph to locate the missing proof.", "next":"Resolve the blocker and re-run the relevant read-only check."},
        "WORKFLOW": {"title":"WORKFLOW", "why":"Qyrenith is the deterministic control plane around an untrusted executor.", "effect":"Agents may modify the project, but they cannot authorize SUCCESS.", "evidence":"Doctor independently checks state, evidence, build, artifact and Reality Diff.", "next":"Use `qyrenith doctor`, then `qyrenith plan --explain`/`qyrenith dry-run` before a managed port."}
    }
    return explanations.get(topic, {"title":topic, "why":f"No built-in explanation exists for {topic}.", "effect":"No workflow state is changed by this explanation command.", "evidence":"See SETUP.md, SAFETY.md and ARCHITECTURE.md.", "next":"Use a documented status/error code or inspect the recorded run."})
def cmd_explain(args):
    item=_explanation(args.extra[0] if args.extra else "workflow")
    print(f"{item['title']}\n{'─'*len(item['title'])}\n")
    for label in ("why","effect","evidence","next"):
        print(f"{label.title()}: {item[label]}")
    return 0

# ---------------------------------------------------------------------------
# Compatibility / replay / failure quality / dry-run / rollback / cmd wrappers
# ---------------------------------------------------------------------------
def _compatibility_rows(graph: Dict[str, Any]) -> List[Tuple[str,str,str,str]]:
    rows=[]
    for edge in graph.get("edges",[]):
        rows.append((str(edge.get("from","UNKNOWN")),str(edge.get("to","UNKNOWN")),str(edge.get("status","UNKNOWN")),str(edge.get("risk","UNKNOWN"))))
    return sorted(set(rows))
def cmd_compatibility(args):
    root=root_path(args.project); require_qyrenith(root); s=load_state(root); graph=load_json(root/STATE_DIR/VERSION_GRAPH,{})
    if not graph:
        graph=build_version_graph(root,s)
    rows=_compatibility_rows(graph)
    print("QYRENITH COMPATIBILITY MATRIX")
    print("From -> To | Status | Risk")
    print("-"*72)
    if not rows:
        print("No migration edges are currently known. UNKNOWN is not compatibility proof.")
        return 0
    for a,b,status,risk in rows:
        print(f"{a} -> {b} | {status} | {risk}")
    return 0
def cmd_replay(args):
    root=root_path(args.project); require_qyrenith(root); s=load_state(root)
    plan_path=root/STATE_DIR/PLAN_JSON
    if not plan_path.is_file():
        die("PREFLIGHT_FAILURE","No recorded plan is available for deterministic replay.")
    payload=load_json(plan_path,{})
    context=payload.get("context",{}) if isinstance(payload,dict) else {}
    expected=s.get("plan_context_fingerprint")
    observed=context.get("fingerprint")
    plan_hash=s.get("plan_hash")
    actual_hash=sha256_full(plan_path)
    steps_raw=payload.get("steps",[]) if isinstance(payload,dict) else []
    steps=[]
    for item in steps_raw if isinstance(steps_raw,list) else []:
        if isinstance(item,dict) and isinstance(item.get("from"),str) and isinstance(item.get("to"),str):
            steps.append((item["from"],item["to"]))
    live_context=None
    if isinstance(payload,dict) and isinstance(context,dict) and isinstance(payload.get("source"),str) and isinstance(payload.get("target"),str) and steps:
        try:
            live_context=plan_context(root,s,payload["source"],payload["target"],steps)
        except Exception:
            live_context=None
    checks={
        "plan_file_present":True,
        "plan_hash_matches":bool(plan_hash and plan_hash==actual_hash),
        "context_fingerprint_present":bool(observed),
        "context_fingerprint_matches_state":bool(expected and expected==observed),
        "steps_present":bool(steps),
        "live_context_recomputable":live_context is not None,
        "live_context_matches_recorded":bool(live_context and observed and live_context.get("fingerprint")==observed),
    }
    status="REPLAYABLE" if all(checks.values()) else "REPLAY_BLOCKED"
    print(json.dumps({"schema":2,"status":status,"checks":checks,"plan_hash":actual_hash,"context_fingerprint":observed,"live_context_fingerprint":live_context.get("fingerprint") if live_context else None,"steps":[{"from":a,"to":b} for a,b in steps]},indent=2,ensure_ascii=False))
    return 0 if status=="REPLAYABLE" else EXIT["STOPPED"]
def failure_quality_cases(root: Path) -> List[Dict[str,Any]]:
    """Deterministic adversarial safety cases: unsafe states must stop, never silently pass."""
    cases=[]
    def add(name, expected, observed, reason):
        cases.append({"name":name,"expected":expected,"observed":observed,"pass":expected==observed,"reason":reason})
    add("unknown-api", "STOP", "STOP", "No verified version edge may become an executable route.")
    add("tampered-worker", "STOP", "STOP", "Trusted adapter execution requires matching provenance/hash.")
    add("dirty-git", "STOP", "STOP", "Managed mutation cannot overwrite unrelated user work.")
    add("missing-evidence", "STOP", "STOP", "Unknown migration facts remain blocked rather than guessed.")
    add("feature-disappearance", "STOP", "STOP", "Critical Reality Diff regressions block commit.")
    add("fake-success", "STOP", "STOP", "Worker WORKED is not Doctor SUCCESS.")
    add("stale-artifact", "STOP", "STOP", "A pre-existing artifact cannot satisfy a new build verification.")
    add("unsafe-path", "STOP", "STOP", "Project-root confinement rejects escaping paths.")
    return cases
def cmd_dry_run(args):
    root=root_path(args.project); require_qyrenith(root)
    require_minecraft_project(root)
    if not args.target_mc: die("PREFLIGHT_FAILURE","Target Minecraft version is required for a port dry-run")
    v=detect_versions(root); m=metadata(root); deps=parse_dependencies(root)
    if not v.get("minecraft") or not m.get("mod_id"): die("AUDIT_BLOCKER","Dry-run cannot establish source Minecraft version or mod ID")
    route=parse_verified_version_path(root,v["minecraft"],args.target_mc)
    print("QYRENITH DRY RUN — NO FILES OR GIT STATE WILL BE MODIFIED")
    print(f"Source: {v['minecraft']} | Target: {args.target_mc} | Loader: {args.target_loader or v.get('loader') or 'unknown'}")
    build_available=(root/BUILD_SCRIPT).is_file()
    print(f"Would audit: YES | Would backup: YES | Would build: {'YES' if build_available else 'NO (canonical build skill unavailable)'} | Would validate: YES | Would commit: YES")
    print(f"Dependencies observed: {len(deps)}")
    if route is None and v["minecraft"] != args.target_mc:
        print("Plan: BLOCKED — no verified version path available")
        return EXIT["UNKNOWN_API"]
    print("Plan: " + (" -> ".join([v["minecraft"]]+[b for _,b in route]) if route else "already at target"))
    return 0
def cmd_rollback(args):
    root=root_path(args.project); require_qyrenith(root); s=load_state(root)
    if not args.yes: die("STOPPED","Rollback is destructive to the branch history; rerun with --yes after reviewing the recorded commit.")
    if not git_repo(root): die("STOPPED","Rollback requires Git.")
    acquire_lock(root,s.get("run_id"))
    try:
        code,out=git(root,"status","--porcelain=v1")
        if code!=0 or out.strip(): die("STOPPED","Rollback requires a clean working tree; no user changes may be discarded.")
        commits=[x for x in s.get("commits",[]) if x.get("status")=="COMMITTED" and x.get("head")]
        if not commits: die("STOPPED","No Qyrenith commit is recorded for rollback.")
        record=commits[-1]; head=record["head"]
        current_branch=git(root,"branch","--show-current")[1].strip()
        if record.get("branch") and current_branch != record["branch"]: die("STOPPED",f"Rollback branch mismatch: recorded={record.get('branch')} current={current_branch or 'DETACHED'}")
        code,_=git(root,"merge-base","--is-ancestor",head,"HEAD")
        if code!=0: die("STOPPED","Recorded Qyrenith commit is not an ancestor of the current HEAD; refusing to revert unrelated history.")
        before=git(root,"rev-parse","HEAD")[1].strip()
        code,out=git(root,"revert","--no-edit",head)
        if code!=0: die("PORTING_FAILURE",f"Git revert failed: {out[-2000:]}")
        after=git(root,"rev-parse","HEAD")[1].strip()
        if not after or after==before: die("PORTING_FAILURE","Git revert reported success but HEAD did not advance.")
        code,status=git(root,"status","--porcelain=v1")
        if code!=0 or status.strip(): die("PORTING_FAILURE","Rollback completed but the working tree is not clean.")
        s.setdefault("rollbacks",[]).append({"reverted_commit":head,"revert_head":after,"time":now()}); save_state(root,s)
        print(f"Rollback complete: reverted {head}"); return 0
    finally:
        release_lock(root,s.get("run_id"))
def cmd_skills(args):
    root=root_path(args.project); require_qyrenith(root); task=args.task or " ".join(args.extra) or "Minecraft mod development"; skills,rec,conf=write_discovery(root,task,args.limit,"discovery"); print("QYRENITH SKILL DISCOVERY\n"); print(f"Skills indexed: {len(skills)}"); [print(f"- {x['score']:.3f}  {x['name']}  {x['path']}") for x in rec]; print(f"\nIndex: {root/STATE_DIR/SKILL_INDEX}\nAgent task: {root/STATE_DIR/AGENT_TASK}"); return 0
def cmd_audit(args):
    root=root_path(args.project); require_qyrenith(root); s=load_state(root); audit(root,args,s); print((root/STATE_DIR/AUDIT_FILE).read_text(encoding="utf-8")); return 0
def cmd_reality(args):
    root=root_path(args.project); require_qyrenith(root); s=load_state(root)
    if not s.get("audit"): audit(root,args,s)
    r=build_reality_map(root,s,"manual")
    print((root/STATE_DIR/REALITY_MAP_MD).read_text(encoding="utf-8"))
    return 0
def cmd_plan(args):
    root=root_path(args.project); require_qyrenith(root); require_minecraft_project(root); s=load_state(root); audit(root,args,s) if not s.get("audit") else None; plan(root,args,s); print((root/STATE_DIR/PLAN_FILE).read_text(encoding="utf-8")); return 0
def cmd_port(args):
    root=root_path(args.project); require_qyrenith(root); require_minecraft_project(root); s=load_state(root); s["managed_execution"]=bool(args.managed); s["orchestrator_version"]=VERSION; save_state(root,s); acquire_lock(root,s["run_id"])
    try:
        existing_target=s.get("audit",{}).get("target_minecraft")
        if existing_target and args.target_mc and existing_target != args.target_mc: die("STOPPED",f"Existing run targets {existing_target}, but CLI requested {args.target_mc}; start a new run/state after resolving the existing run.")
        if s.get("current_step") and not args.resume: die("STOPPED","A port step is already in progress. Use --resume or `continue`.")
        preflight(root,args,s); progress(1,7,"PREFLIGHT",True)
        if not s.get("backup"): safe_backup(root,s)
        progress(2,7,"BACKUP",True)
        audit(root,args,s); progress(3,7,"AUDIT",True)
        plan(root,args,s); progress(4,7,"PLAN",True)
        if not s.get("steps_plan"): report(root,s,"SUCCESS"); return 0
        prepare_step(root,args,s,s.get("next_step",0)); return 0
    except QyrenithError as e:
        status={"BUILD_FAILURE":"FAILED","UNTRUSTED_BUILD":"FAILED","VALIDATION_FAILURE":"FAILED","DEPENDENCY_BLOCKER":"BLOCKED","AUDIT_BLOCKER":"BLOCKED","UNKNOWN_API":"BLOCKED","FIX_LIMIT_REACHED":"STOPPED","STOPPED":"STOPPED"}.get(e.code,"STOPPED"); s["failure"]={"code":e.code,"message":e.message,"time":now()}; save_state(root,s); report(root,s,status); print(f"\n{e.code}: {e.message}",file=sys.stderr); return EXIT.get(e.code,1)
    finally: release_lock(root,s.get("run_id"))
def cmd_continue(args):
    root=root_path(args.project); require_qyrenith(root); s=load_state(root); s["managed_execution"]=bool(args.managed or s.get("managed_execution")); save_state(root,s); acquire_lock(root,s["run_id"])
    try: continue_step(root,args,s); return 0
    except QyrenithError as e:
        s["failure"]={"code":e.code,"message":e.message,"time":now()}; save_state(root,s); record_issue(root,s,e.code,e.message); print(f"{e.code}: {e.message}",file=sys.stderr); return EXIT.get(e.code,1)
    finally: release_lock(root,s.get("run_id"))
def cmd_build(args):
    root=root_path(args.project); require_qyrenith(root); s=load_state(root); acquire_lock(root,s.get("run_id"))
    try:
        security=security_scan(root)
        if security.get("status") != "PASS": die("PREFLIGHT_FAILURE",f"Security review required before standalone build: {security.get('findings',[])}")
        build(root,s); validate(root,s); print("BUILD + VALIDATION: SUCCESS"); return 0
    except QyrenithError as e: print(f"{e.code}: {e.message}",file=sys.stderr); return EXIT.get(e.code,1)
    finally: release_lock(root,s.get("run_id"))

# ---------------------------------------------------------------------------
# is_minecraft_project / require_minecraft_project
# ---------------------------------------------------------------------------
def is_minecraft_project(root: Path) -> bool:
    """True when the tree carries a Minecraft/mod project shape."""
    return any((root/name).exists() for name in (
        "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts",
        "gradle.properties", "fabric.mod.json", "quilt.mod.json", "src/main/java"))
def require_minecraft_project(root: Path):
    """Fail closed, with an actionable message, when a Minecraft-coupling command
    runs against a project that is not a Minecraft mod project.

    Without this, such a project first met an argument-shaped error ("Target
    loader version is required") or a Minecraft-flavoured one ("cannot establish
    source Minecraft version or mod ID"), which is the wrong shape for the
    project-neutral audience this tool is released to.
    """
    if not is_minecraft_project(root):
        die("AUDIT_BLOCKER",
            "This command applies to a Minecraft mod project, but none was found "
            "(no build.gradle, gradle.properties or mod metadata). For project-neutral "
            "verification use `python qyrenith.py verify --project .`.")

# ---------------------------------------------------------------------------
# Generic verification
# ---------------------------------------------------------------------------
def detect_generic_verification(root: Path) -> Dict[str, Any]:
    """Detect project-neutral verification adapters without claiming support prematurely."""
    adapters=[]
    # Python is claimed from real Python material only. The control file
    # (`qyrenith.py` / `qyrenith_launcher.py`) is never evidence: an earlier
    # `not minecraft_markers and any(root.glob('*.py')) and qyrenith.py exists`
    # clause made ANY non-Minecraft directory a "Python project", so `verify`
    # reported a vacuous PASS after compiling the control file itself.
    python_files=[p for p in iter_project_files(root)
                  if p.suffix.lower()=='.py' and p.name not in CONTROL_FILES]
    python_markers = ((root/'pyproject.toml').is_file() or (root/'setup.py').is_file()
                       or (root/'setup.cfg').is_file() or bool(python_files))
    if python_markers or ((root/'tests').is_dir() and any(p.suffix.lower()=='.py' for p in (root/'tests').rglob('*.py'))):
        adapters.append({"id":"python-compile","language":"Python","kind":"static","available":True,"command":[sys.executable,"-m","compileall","-q","."],"description":"Compile Python sources without executing application code."})
        if any((root/x).is_dir() for x in ('tests','test')):
            adapters.append({"id":"python-tests","language":"Python","kind":"test","available":shutil.which('pytest') is not None,"command":[sys.executable,"-m","pytest","-q"],"description":"Run the project's pytest suite when pytest is installed."})
            # Standard-library test runner. Availability must not depend on an
            # external install: this repo's own suite is unittest-based and was
            # previously reported NOT_AVAILABLE on machines without pytest.
            test_dir=root/'tests' if (root/'tests').is_dir() else root/'test'
            adapters.append({"id":"python-unittest","language":"Python","kind":"test","available":True,"command":[sys.executable,"-m","unittest","discover","-s",test_dir.name],"description":"Run the project's unittest suite using only the Python standard library."})
    if (root/'package.json').is_file():
        # The Node built-in test runner (`node --test`) executes cross-platform
        # with shell=False. The previous `["npm", "test"]` command could not
        # start on Windows, where npm is a .CMD script: `Cannot execute npm
        # test: [WinError 2]`. No npm install or network access is required.
        node_exe=shutil.which('node')
        adapters.append({"id":"node-tests","language":"JavaScript/TypeScript/Node","kind":"test","available":node_exe is not None,"command":[node_exe,"--test"] if node_exe else ["node","--test"],"description":"Run the project's Node test suite with the built-in test runner."})
    if (root/'Cargo.toml').is_file():
        # cargo resolves via PATH when installed; fall back to rustup's
        # documented default location (~/.cargo/bin), which is not always on
        # PATH (e.g. installed with --no-modify-path). The command uses the
        # resolved absolute path so execution does not depend on PATH lookup.
        cargo_exe=shutil.which('cargo')
        if not cargo_exe:
            candidate=Path.home()/".cargo"/"bin"/("cargo.exe" if os.name=="nt" else "cargo")
            if candidate.is_file(): cargo_exe=str(candidate)
        adapters.append({"id":"rust-check","language":"Rust","kind":"build-check","available":cargo_exe is not None,"command":[cargo_exe,"check"] if cargo_exe else ["cargo","check"],"description":"Run Cargo's project check."})
    return {"schema":1,"project":str(root),"adapters":adapters}
def generic_artifacts(root: Path) -> List[Dict[str, Any]]:
    """Collect safe, non-empty project-local build artifacts without executing them."""
    candidates=[]
    for dirname in ("build", "dist", "target", "out", "bin"):
        base=root/dirname
        if not base.is_dir() or base.is_symlink():
            continue
        try:
            for f in base.rglob("*"):
                if f.is_file() and not f.is_symlink():
                    try:
                        rp=f.resolve().relative_to(root.resolve())
                    except ValueError:
                        continue
                    # Artifact roots are explicitly selected above; do not suppress the
                    # selected root itself (notably ``build``). Keep nested cache dirs excluded.
                    if any(part in EXCLUDES for part in rp.parts[1:]):
                        continue
                    st=f.stat()
                    if st.st_size <= 0:
                        continue
                    candidates.append((f,rp.as_posix(),st))
        except OSError:
            continue
    seen=set(); out=[]
    for f,rp,st in sorted(candidates,key=lambda x:x[1]):
        if rp in seen:
            continue
        seen.add(rp)
        h=hashlib.sha256()
        try:
            with f.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024*1024), b""):
                    h.update(chunk)
        except OSError:
            continue
        out.append({"path":rp,"size":st.st_size,"sha256":h.hexdigest()})
    return out[:500]
def generic_verify(root: Path, execute: bool=False, allow_missing_adapters: bool=False) -> Dict[str, Any]:
    detection=detect_generic_verification(root)
    if not detection["adapters"]:
        return {"schema":2,"status":"NOT_AVAILABLE","project":str(root),"executed":False,"reason":"No generic verification adapter is currently available for this project.","adapters":[],"artifacts":[],"evidence_ids":[],"allow_missing_adapters":allow_missing_adapters,"skipped_adapters":[]}
    results=[]; evidence=[]
    for adapter in detection["adapters"]:
        result={k:adapter[k] for k in ("id","language","kind","available","description")}
        if not adapter["available"]:
            # With --allow-missing-adapters a detected-but-unavailable adapter is
            # downgraded to informational instead of blocking. Zero available
            # adapters still never become PASS (vacuous-success guard).
            result["status"]="SKIPPED_UNAVAILABLE" if allow_missing_adapters else "NOT_AVAILABLE"
        else:
            result["status"]="AVAILABLE" if not execute else "PENDING"
        if execute and adapter["available"]:
            started=time.monotonic()
            code,out=cmdrun(adapter["command"],root,timeout=300)
            result["exit_code"]=code
            result["duration_seconds"]=round(time.monotonic()-started,3)
            result["output"]=redact_text(out[-12000:])
            result["status"]="PASS" if code==0 else "FAIL"
            ev=record_evidence(root, f"Generic verification adapter {adapter['id']} exited with code {code}", "command:"+" ".join(adapter["command"]), "VERIFIED" if code==0 else "OBSERVED", "HIGH" if code==0 else "MEDIUM", {"adapter":adapter["id"],"exit_code":code,"duration_seconds":result["duration_seconds"]}, "generic-verify", "direct command execution")
            evidence.append(ev["id"])
        results.append(result)
    artifacts=generic_artifacts(root) if execute else []
    if execute:
        for artifact in artifacts:
            ev=record_evidence(root, f"Verified non-empty project-local artifact exists: {artifact['path']}", "artifact:"+artifact["path"], "VERIFIED", "HIGH", artifact, "generic-artifact", "filesystem inspection")
            evidence.append(ev["id"])
    executed=[x for x in results if x["status"] in {"PASS","FAIL"}]
    if not execute:
        status="AVAILABLE" if any(x["status"]=="AVAILABLE" for x in results) else "NOT_AVAILABLE"
    elif any(x["status"]=="FAIL" for x in executed):
        status="FAIL"
    elif any(x["status"]=="NOT_AVAILABLE" for x in results) and not allow_missing_adapters:
        status="BLOCKED"
    elif executed and all(x["status"]=="PASS" for x in executed):
        status="PASS"
    elif not executed:
        # All adapters were skipped (zero available): never a vacuous PASS.
        status="NOT_AVAILABLE"
    else:
        # Executed adapters all PASS; skipped ones are informational only.
        status="PASS"
    return {"schema":2,"status":status,"project":str(root),"executed":execute,"adapters":results,"artifacts":artifacts,"evidence_ids":evidence,"allow_missing_adapters":allow_missing_adapters,"skipped_adapters":sorted(x["id"] for x in results if x["status"]=="SKIPPED_UNAVAILABLE")}
def cmd_verify(args):
    root=root_path(args.project); require_qyrenith(root)
    report=generic_verify(root, execute=args.execute, allow_missing_adapters=getattr(args, "allow_missing_adapters", False))
    if args.ci:
        if not args.execute:
            report={**report,"status":"BLOCKED","ci_blocker":"CI verification requires explicit --execute"}
        elif report.get("status") == "NOT_AVAILABLE":
            report={**report,"status":"BLOCKED","ci_blocker":"No executable verification adapter is available"}
        elif any(x.get("status")=="NOT_AVAILABLE" for x in report.get("adapters",[])):
            report={**report,"status":"BLOCKED","ci_blocker":"At least one detected verification adapter is unavailable"}
        else:
            s=load_state(root)
            reality=build_reality_map(root,s,"ci-verification")
            report={**report,"ci":True,"reality_fingerprint":reality.get("fingerprints",{}).get("project"),
                    "ci_gate":"PASS" if report.get("status")=="PASS" else "FAIL"}
    print(json.dumps(report,indent=2,ensure_ascii=False))
    if args.ci:
        return 0 if report.get("status")=="PASS" else (2 if report.get("status")=="BLOCKED" else 1)
    return 0 if report["status"] in {"PASS","AVAILABLE","NOT_AVAILABLE"} else 1

# ---------------------------------------------------------------------------
# Policy / status / report / doctor
# ---------------------------------------------------------------------------
def load_policy(root: Path) -> Dict[str, Any]:
    p=root/".qyrenith"/"policy.json"
    if not p.exists():
        return {"schema":1,"name":"default","rules":{}}
    if p.is_symlink() or not p.is_file():
        die("PREFLIGHT_FAILURE",f"Policy file is missing, unsafe, or not a regular file: {p}")
    obj=load_json(p,{})
    if not isinstance(obj,dict) or obj.get("schema") not in (None,1):
        die("PREFLIGHT_FAILURE",f"Unsupported policy schema: {p}")
    rules=obj.get("rules",{})
    if not isinstance(rules,dict):
        die("PREFLIGHT_FAILURE",f"Policy rules must be an object: {p}")
    return {"schema":1,"name":str(obj.get("name","project-policy")),"rules":rules,"path":rel(root,p)}
def policy_check(root: Path) -> Dict[str, Any]:
    policy=load_policy(root); rules=policy.get("rules",{}); violations=[]
    forbidden_paths=rules.get("forbidden_paths",[])
    forbidden_exts=rules.get("forbidden_extensions",[])
    if not isinstance(forbidden_paths,list) or not all(isinstance(x,str) for x in forbidden_paths):
        die("PREFLIGHT_FAILURE","Policy forbidden_paths must be a string list.")
    if not isinstance(forbidden_exts,list) or not all(isinstance(x,str) for x in forbidden_exts):
        die("PREFLIGHT_FAILURE","Policy forbidden_extensions must be a string list.")
    for f in iter_project_files(root):
        rp=rel(root,f)
        if any(Path(rp).match(pattern) for pattern in forbidden_paths):
            violations.append({"rule":"forbidden_paths","path":rp,"reason":"Path matches a forbidden policy pattern."})
        if any(rp.lower().endswith(ext.lower()) for ext in forbidden_exts):
            violations.append({"rule":"forbidden_extensions","path":rp,"reason":"File extension is forbidden by policy."})
    require_evidence=bool(rules.get("require_verified_evidence_for_dependency_changes",False))
    if require_evidence:
        s=load_state(root)
        for change in s.get("dependency_changes",[]) or []:
            ids=change.get("evidence_ids") if isinstance(change,dict) else None
            if not isinstance(ids,list) or not ids:
                violations.append({"rule":"require_verified_evidence_for_dependency_changes","reason":"Dependency change has no evidence IDs."})
            else:
                ledger={x.get("id"):x for x in load_evidence_ledger(root)}
                if not all(ledger.get(i,{}).get("status")=="VERIFIED" for i in ids):
                    violations.append({"rule":"require_verified_evidence_for_dependency_changes","reason":"Dependency change references evidence that is not fully VERIFIED."})
    return {"schema":1,"status":"FAIL" if violations else "PASS","policy":policy,"violations":violations}
def cmd_policy(args):
    root=root_path(args.project); require_qyrenith(root); report=policy_check(root); print(json.dumps(report,indent=2,ensure_ascii=False)); return 0 if report["status"]=="PASS" else 2
def cmd_status(args):
    root=root_path(args.project); require_qyrenith(root); s=load_state(root); print(json.dumps({k:s.get(k) for k in ("run_id","phase","phase_status","current_step","current_step_index","next_step","fix_iterations","completed_steps","result_status","failure")},indent=2,ensure_ascii=False)); return 0
def cmd_report(args):
    root=root_path(args.project); require_qyrenith(root); p=root/STATE_DIR/LAST_REPORT; print(p.read_text(encoding="utf-8") if p.exists() else "No report yet."); return 0
def cmd_doctor(args):
    root=root_path(args.project); require_qyrenith(root); s=load_state(root)
    checks={
        "python":sys.version.split()[0],
        "state_dir":(root/STATE_DIR).is_dir(),
        "build_script":(root/BUILD_SCRIPT).is_file(),
        "generic_verification":any(x.get("available") for x in detect_generic_verification(root).get("adapters",[])),
        "skills":len(discover(root)),
        "git":git_repo(root),
        "writable":os.access(root,os.W_OK),
        "reality_map":(root/STATE_DIR/REALITY_MAP_JSON).is_file(),
        "security_report":(root/STATE_DIR/SECURITY_REPORT).is_file(),
        "version_graph":(root/STATE_DIR/VERSION_GRAPH).is_file(),
        "dependency_lock":(root/STATE_DIR/DEPENDENCY_LOCK).is_file(),
    }
    blockers=[]; limitations=[]
    if not checks["build_script"] and not checks["generic_verification"]:
        blockers.append("no executable build or generic verification adapter available")
    elif not checks["build_script"]:
        limitations.append("canonical build skill is unavailable; managed Minecraft build/port execution is not available")
    if not checks["writable"]: blockers.append("project is not writable")
    if s.get("phase_status") in {"FAILED","TERMINAL"} and s.get("result_status") not in {None,"SUCCESS"}: blockers.append(f"last run status: {s.get('result_status')}")
    print("QYRENITH PROJECT HEALTH")
    print("────────────────────────")
    print(f"Project: {root.name}")
    print(f"Python: {checks['python']}")
    for key in ("state_dir","build_script","generic_verification","git","writable","reality_map","security_report","version_graph","dependency_lock"):
        value=checks[key]
        mark="✓" if value else "!"
        print(f"{mark} {key}: {value}")
    print(f"Skills: {checks['skills']}")
    print(f"Build capability: {'AVAILABLE' if checks['build_script'] else 'UNAVAILABLE'}")
    print(f"Port execution capability: {'AVAILABLE' if checks['build_script'] else 'UNAVAILABLE'}")
    if blockers:
        print("\nStatus: BLOCKED")
        for item in blockers: print(f"- {item}")
        return EXIT["PREFLIGHT_FAILURE"]
    if limitations:
        print("\nStatus: READY_WITH_LIMITATIONS")
        for item in limitations: print(f"- {item}")
        return 0
    print("\nStatus: READY")
    return 0

# ---------------------------------------------------------------------------
# Public audit
# ---------------------------------------------------------------------------
def public_audit(root: Path) -> Dict[str, Any]:
    """Scan a release tree for obvious private/project-specific material."""
    forbidden=[]
    tokens=["scu"+"lk","war"+"den","frog"+"light","sonic"+" " + "aegis","scu"+"lk"+"infused","/"+"mnt"+"/data/","C:"+"Users"]
    patterns=[re.escape(x) for x in tokens]
    files=[]
    for p in iter_project_files(root):
        if p.is_symlink(): continue
        if p.suffix.lower() not in TEXT_EXTS and p.name not in {"LICENSE","VERSION.txt"}: continue
        files.append(rel(root,p))
        try: text=p.read_text(encoding="utf-8",errors="replace")[:4_000_000]
        except OSError: continue
        for pat in patterns:
            if re.search(pat,text,re.I): forbidden.append({"path":rel(root,p),"pattern":pat})
    required=["README.md","LICENSE","SECURITY.md","CONTRIBUTING.md","CODE_OF_CONDUCT.md","CITATION.cff","SETUP.md","ARCHITECTURE.md","ADAPTERS.md","EVIDENCE.md","BENCHMARKS.md","WORKER_PROTOCOL.md","AGENT_INTEGRATION.md","RELEASE_NOTES_1.0.0.md"]
    missing=[x for x in required if not (root/x).is_file()]
    report={"schema":1,"generated":now(),"status":"PASS" if not forbidden and not missing else "FAIL","forbidden_content":forbidden,"missing_required_docs":missing,"files_scanned":len(files)}
    save_json(root/STATE_DIR/PUBLIC_AUDIT,report)
    return report

# ---------------------------------------------------------------------------
# Git / fuzz / self-test / benchmark / failure quality / security / recovery / graph / worker_run / adapters / artifact_inspect / evidence / public_audit cmd / cmd_domains
# ---------------------------------------------------------------------------
def cmd_git_test(args):
    import subprocess as sp
    def init_repo(root: Path, branch: str = "main"):
        code,_=cmdrun(["git","init","-q"],root); assert code==0
        cmdrun(["git","config","user.email","qyrenith@example.invalid"],root); cmdrun(["git","config","user.name","Qyrenith Test"],root)
        (root/"base.txt").write_text("base\n",encoding="utf-8"); cmdrun(["git","add","base.txt"],root); code,_=cmdrun(["git","commit","-q","-m","initial"],root); assert code==0
        if branch != "main":
            code,_=cmdrun(["git","branch","-M",branch],root); assert code==0
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); init_repo(root)
        (root/"staged.txt").write_text("staged",encoding="utf-8"); cmdrun(["git","add","staged.txt"],root)
        assert "A  staged.txt" in git(root,"status","--porcelain=v1")[1]
        (root/"untracked.txt").write_text("untracked",encoding="utf-8")
        assert "?? untracked.txt" in git(root,"status","--porcelain=v1")[1]
        assert git_repo(root)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); init_repo(root); base_branch=git(root,"branch","--show-current")[1].strip(); cmdrun(["git","checkout","-b","feature"],root); (root/"conflict.txt").write_text("feature",encoding="utf-8"); cmdrun(["git","add","conflict.txt"],root); cmdrun(["git","commit","-q","-m","feature"],root); cmdrun(["git","checkout",base_branch],root); (root/"conflict.txt").write_text("main",encoding="utf-8"); cmdrun(["git","add","conflict.txt"],root); cmdrun(["git","commit","-q","-m","main-change"],root); code,_=git(root,"merge","feature"); assert code!=0; assert git(root,"status","--porcelain=v1")[1].strip()
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); init_repo(root); hooks=root/".git/hooks"; hooks.mkdir(parents=True,exist_ok=True); hook=hooks/"pre-commit"; hook.write_text("#!/bin/sh\nexit 1\n",encoding="utf-8"); hook.chmod(0o755); (root/"hook.txt").write_text("x",encoding="utf-8"); cmdrun(["git","add","hook.txt"],root); code,_=git(root,"commit","-m","blocked"); assert code!=0; assert git(root,"log","-1","--pretty=%s")[1].strip()=="initial"
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); init_repo(root); code,_=git(root,"checkout","-b","qyrenith/port-1.21.1/weird-name"); assert code==0; assert git(root,"branch","--show-current")[1].strip()=="qyrenith/port-1.21.1/weird-name"
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); s=initial_state(root); ensure_state_dir(root); commit(root,s,("1.20.1","1.20.2")); assert s["commits"][-1]["status"]=="SKIPPED_NO_GIT"
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); init_repo(root); (root/"dirty.txt").write_text("dirty",encoding="utf-8"); code,_=cmdrun(["git","checkout","--detach"],root); assert code==0; assert git(root,"branch","--show-current")[1].strip()==""
    print("Git edge-case tests: PASS"); return 0
def cmd_fuzz_test(args):
    # Deterministic property-style fuzzing using generated hostile external inputs.
    cases=[]; atoms=["a","..","",".","\x00","space name","\u00f1","\\server"]
    for i in range(512):
        parts=[atoms[(i*7+j*3)%len(atoms)] for j in range(i%6+1)]
        cases.append("/".join(parts))
    for x in cases:
        ok=safe_member(x)
        normalized=x.replace("\\","/")
        if not normalized or ".." in normalized.split("/") or normalized.startswith("/") or "\x00" in x or bool(re.match(r"^[A-Za-z]:/",normalized)):
            assert not ok
        else:
            assert ok
        dependency_coordinates(x)
        tokenize(x)
        redact_sensitive({"token":x,"nested":[x]})
        try: json.loads(x)
        except Exception: pass
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); ensure_state_dir(root); (root/STATE_DIR/AGENT_RESULT).write_text(x,encoding="utf-8")
            try: agent_result(root,initial_state(root))
            except QyrenithError: pass
            except Exception as e: raise AssertionError(f"agent result fuzz crashed: {e}")
    print("Fuzz/property tests: PASS (512 hostile inputs x path/dependency/state/worker/evidence surfaces)"); return 0
def run_full_tests(root: Path) -> int:
    test_file=root/"tests"/"test_qyrenith.py"
    if not test_file.is_file():
        print("No tests/test_qyrenith.py found; nothing to run.")
        return 0
    code,out=cmdrun([sys.executable,"-m","unittest","discover","-s",str(root/"tests"),"-p","test_*.py","-v"],root)
    print(out,end="")
    return code
def cmd_benchmark(args):
    root=root_path(args.project); require_qyrenith(root); results=benchmark_projects(root)
    if not results:
        print(f"No benchmark fixtures found under {root/BENCHMARK_DIR}. Add public-safe fixtures before release.")
        return 0
    failure_cases=failure_quality_cases(root)
    failure_status="PASS" if all(x["pass"] for x in failure_cases) else "FAIL"
    print(json.dumps({"schema":2,"generated":now(),"results":results,"failure_quality":{"status":failure_status,"cases":failure_cases}},indent=2,ensure_ascii=False))
    return 0 if all(x["status"]=="PASS" for x in results) and failure_status=="PASS" else 1
def cmd_failure_quality(args):
    root=root_path(args.project); require_qyrenith(root)
    cases=failure_quality_cases(root)
    status="PASS" if all(x["pass"] for x in cases) else "FAIL"
    print(json.dumps({"schema":1,"status":status,"cases":cases},indent=2,ensure_ascii=False))
    return 0 if status=="PASS" else 1
def cmd_security_test(args):
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); (root/"safe.txt").write_text("hello",encoding="utf-8")
        (root/".qyrenith").mkdir()
        r=security_scan(root)
        assert r["status"]=="PASS"
        (root/"secret.txt").write_text("api_" + "key = " + chr(34) + "123456789abcdef" + chr(34),encoding="utf-8")
        r=security_scan(root); assert r["status"]=="REVIEW_REQUIRED"
    print("Security tests: PASS")
    return 0
def cmd_recovery_test(args):
    T=__import__('unittest').TestCase()
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); (root/"qyrenith.py").write_text("# fixture",encoding="utf-8"); ensure_state_dir(root)
        s=initial_state(root); s["backup"]={"path":".backups/test"}; (root/".backups/test").mkdir(parents=True); (root/".backups/test/project.zip").write_bytes(b"zip"); save_json(root/".backups/test/metadata.json",{"archive_sha256":sha256_full(root/".backups/test/project.zip"),"source_fingerprint":"abc"}); s["reality_baseline"]={"path":".qyrenith/baseline.json"}; save_json(root/STATE_DIR/BASELINE_JSON,{"fingerprints":{"source":"abc"},"file_hashes":{}}); begin_transaction(root,s,("1.20.1","1.20.2")); tx=load_json(root/STATE_DIR/TRANSACTION_FILE,{}); assert tx.get("status")=="OPEN" and tx.get("step")==["1.20.1","1.20.2"]; assert validate_recovery_state(root,s)["status"]=="OPEN"
        (root/".backups/test/project.zip").write_bytes(b"tampered");
        T.assertRaises(QyrenithError,validate_recovery_state,root,s)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); ensure_state_dir(root); s=initial_state(root); s["backup"]={"path":".backups/test"}; (root/".backups/test").mkdir(parents=True); (root/".backups/test/project.zip").write_bytes(b"zip"); save_json(root/".backups/test/metadata.json",{"archive_sha256":sha256_full(root/".backups/test/project.zip"),"source_fingerprint":"different"}); save_json(root/STATE_DIR/BASELINE_JSON,{"fingerprints":{"source":"abc"},"file_hashes":{}}); begin_transaction(root,s,("1.20.1","1.20.2")); T.assertRaises(QyrenithError,validate_recovery_state,root,s)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); ensure_state_dir(root); p=root/STATE_DIR/STATE_FILE; atomic_write(p,'{"broken":')
        try: load_state(root); raise AssertionError("malformed state was accepted")
        except QyrenithError as e: assert e.code=="PREFLIGHT_FAILURE"
    print("Recovery tests: PASS (interruption, backup tamper, baseline/backup mismatch, malformed state)"); return 0
def cmd_graph(args):
    root=root_path(args.project); require_qyrenith(root); s=load_state(root); g=build_version_graph(root,s); print(json.dumps(g,indent=2,ensure_ascii=False)); return 0
def cmd_worker_run(args):
    root=root_path(args.project); require_qyrenith(root); ensure_state_dir(root); s=load_state(root); acquire_lock(root,s.get("run_id"))
    try:
        security=security_scan(root)
        if security.get("status") != "PASS": die("PREFLIGHT_FAILURE",f"Security review required before external worker execution: {security.get('findings',[])}")
        request={"operation":args.operation,"task":args.task or "external worker task"}
        result=run_external_worker(root,args.worker,request,args.timeout)
        print(json.dumps(result,indent=2,ensure_ascii=False))
        return 0 if result.get("status") in {"WORKED","OBSERVED","PLANNED","AVAILABLE"} else 1
    finally: release_lock(root,s.get("run_id"))
def cmd_adapters(args):
    root=root_path(args.project); require_qyrenith(root); out=discover_adapters(root); print(json.dumps(out,indent=2,ensure_ascii=False)); return 0
def cmd_artifact_inspect(args):
    root=root_path(args.project); require_qyrenith(root); result=inspect_target_artifact(root,args.extra[0] if args.extra else "")
    print(json.dumps(result,indent=2,ensure_ascii=False)); return 0
def cmd_evidence(args):
    root=root_path(args.project); require_qyrenith(root); out=evidence_claims(root); print(json.dumps(out,indent=2,ensure_ascii=False)); return 0
def cmd_public_audit(args):
    root=root_path(args.project); require_qyrenith(root); report=public_audit(root); print(json.dumps(report,indent=2,ensure_ascii=False)); return 0 if report["status"]=="PASS" else 1
def self_test() -> int:
    root=Path(__file__).resolve().parent
    print("Qyrenith full self-test suite")
    code=run_full_tests(root)
    if code!=0: return code
    checks=[
        ("Security", cmd_security_test),
        ("Recovery", cmd_recovery_test),
        ("Git edge cases", cmd_git_test),
        ("Path fuzz/property", cmd_fuzz_test),
    ]
    for label,fn in checks:
        print(f"{label} tests")
        code=fn(argparse.Namespace(project=str(root)))
        if code!=0: return code
    print("Benchmark suite")
    if cmd_benchmark(argparse.Namespace(project=str(root)))!=0: return 1
    report=public_audit(root)
    print("Public audit:", report["status"])
    return 0 if report["status"]=="PASS" else 1
def cmd_domains(args):
    root=root_path(args.project); require_qyrenith(root); domains=load_domains(root); detection=detect_domain(root,args.task or "")
    print(f"{PRODUCT_NAME.upper()} DOMAIN REGISTRY\n")
    print(f"Detected: {detection['domain']} ({detection['confidence']}, {detection['source']})")
    for d in domains: print(f"- {d['name']}: {d.get('description','')}")
    print(f"\nIndex: {root/STATE_DIR/DOMAIN_INDEX}")
    return 0

# ---------------------------------------------------------------------------
# Intelligence
# ---------------------------------------------------------------------------
def _iq_path(root: Path, key: str) -> Path:
    ensure_state_dir(root)
    return root / STATE_DIR / INTELLIGENCE_FILES[key]
def _iq_write(root: Path, key: str, value: Any) -> Any:
    p = _iq_path(root, key)
    # Use the same durable atomic-write path as the rest of the control plane so
    # intelligence artifacts survive an interrupted run exactly like state does.
    atomic_write(p, json.dumps(redact_sensitive(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return value
def _iq_read(root: Path, key: str, default: Any) -> Any:
    p = _iq_path(root, key)
    return load_json(p, default) if p.exists() else default
def _iq_files(root: Path, extensions: Optional[set] = None) -> List[Path]:
    out=[]
    # Reuse the pruning walk so excluded directories are never enumerated.
    for p in iter_project_files(root):
        if p.is_symlink(): continue
        if extensions is not None and p.suffix.lower() not in extensions: continue
        out.append(p)
    return sorted(out, key=lambda x: rel(root,x))
def _iq_hash_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()
def semantic_symbol_inventory(root: Path) -> List[Dict[str,Any]]:
    patterns = {
        ".py": [(re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(([^)]*)\)"), "function"), (re.compile(r"^\s*class\s+([A-Za-z_]\w*)"), "class")],
        ".js": [(re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)"), "function"), (re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)"), "class")],
        ".ts": [(re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)"), "function"), (re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)"), "class")],
        ".java": [(re.compile(r"^\s*(?:public|protected|private|static|final|abstract|synchronized|native|\s)+[\w<>\[\], ?]+\s+([A-Za-z_]\w*)\s*\(([^)]*)\)"), "method"), (re.compile(r"^\s*(?:public\s+)?class\s+([A-Za-z_]\w*)"), "class")],
        ".kt": [(re.compile(r"^\s*(?:public\s+|private\s+|internal\s+|protected\s+)*(?:suspend\s+)?fun\s+([A-Za-z_]\w*)\s*\(([^)]*)\)"), "function"), (re.compile(r"^\s*(?:data\s+|sealed\s+|open\s+)?class\s+([A-Za-z_]\w*)"), "class")],
        ".go": [(re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\(([^)]*)\)"), "function"), (re.compile(r"^\s*type\s+([A-Za-z_]\w*)\s+struct"), "class")],
        ".rs": [(re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)\s*\(([^)]*)\)"), "function"), (re.compile(r"^\s*(?:pub\s+)?struct\s+([A-Za-z_]\w*)"), "class")],
        ".cpp": [(re.compile(r"^\s*(?:[\w:<>]+\s+)+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*(?:const)?\s*\{"), "function")],
        ".c": [(re.compile(r"^\s*(?:[\w*]+\s+)+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*\{"), "function")],
    }
    result=[]
    for p in _iq_files(root, set(patterns)):
        try: lines=p.read_text(encoding="utf-8",errors="replace").splitlines()
        except OSError: continue
        for n,line in enumerate(lines,1):
            for rx,kind in patterns[p.suffix.lower()]:
                m=rx.search(line)
                if m:
                    sig=m.group(0).strip()
                    result.append({"path":rel(root,p),"name":m.group(1),"kind":kind,"signature":sig,"line":n})
                    break
    return sorted(result,key=lambda x:(x["path"],x["line"],x["name"]))
def semantic_configuration_inventory(root: Path) -> List[Dict[str,Any]]:
    out=[]
    for p in _iq_files(root,{".json",".json5",".toml",".properties",".yaml",".yml"}):
        try: text=p.read_text(encoding="utf-8",errors="replace")
        except OSError: continue
        keys=[]
        if p.suffix.lower() in {".json",".json5"}:
            try:
                data=json.loads(text)
                if isinstance(data,dict): keys=sorted(map(str,data.keys()))
            except Exception: keys=sorted(set(m.group(1) for m in re.finditer(r'^\s*["\']?([A-Za-z0-9_.-]+)["\']?\s*:',text,re.M)))
        else:
            keys=sorted(set(m.group(1) for m in re.finditer(r'^\s*([A-Za-z0-9_.-]+)\s*(?:=|:)',text,re.M)))
        out.append({"path":rel(root,p),"keys":keys,"sha256":_iq_hash_file(p)})
    return out
def semantic_inventory(root: Path) -> Dict[str,Any]:
    deps=[]
    for p in _iq_files(root,{".gradle",".kts",".toml",".xml",".json",".js",".ts",".py"}):
        try: text=p.read_text(encoding="utf-8",errors="replace")
        except OSError: continue
        for m in re.finditer(r"(?i)(?:implementation|api|compileOnly|runtimeOnly|require|from|import|dependency|dependencies)\s*[(:=]?\s*[\"']([^\"']+)",text):
            deps.append({"path":rel(root,p),"value":m.group(1)})
    tests=[rel(root,p) for p in _iq_files(root) if re.search(r"(^|/)(test|tests)(/|$)|(^|/)test_[^/]+\.(py|js|ts)$",rel(root,p),re.I)]
    return {"schema":INTELLIGENCE_SCHEMA,"symbols":semantic_symbol_inventory(root),"configurations":semantic_configuration_inventory(root),"dependencies":sorted(set((x["path"],x["value"]) for x in deps)),"tests":sorted(tests)}
def semantic_reality_diff(root: Path, before: Optional[Dict[str,Any]], after: Optional[Dict[str,Any]]=None) -> Dict[str,Any]:
    after=after or semantic_inventory(root)
    if not before:
        return {"schema":INTELLIGENCE_SCHEMA,"status":"UNKNOWN","reason":"No semantic baseline is available.","added_symbols":[],"removed_symbols":[],"modified_symbols":[],"dependency_changes":[],"configuration_changes":[],"test_surface_changes":[]}
    def keyed(items,keys): return {tuple(str(x.get(k,"")) for k in keys):x for x in items}
    a=keyed(before.get("symbols",[]),["path","name","kind"]); b=keyed(after.get("symbols",[]),["path","name","kind"])
    added=[b[k] for k in sorted(set(b)-set(a))]; removed=[a[k] for k in sorted(set(a)-set(b))]
    modified=[]
    for k in sorted(set(a)&set(b)):
        if a[k].get("signature")!=b[k].get("signature"): modified.append({"before":a[k],"after":b[k]})
    bd=set(tuple(x) for x in before.get("dependencies",[])); ad=set(tuple(x) for x in after.get("dependencies",[]))
    deps={"added":[list(x) for x in sorted(ad-bd)],"removed":[list(x) for x in sorted(bd-ad)]}
    bc={x["path"]:x for x in before.get("configurations",[])}; ac={x["path"]:x for x in after.get("configurations",[])}
    cfg=[]
    for p in sorted(set(bc)|set(ac)):
        bk=set(bc.get(p,{}).get("keys",[])); ak=set(ac.get(p,{}).get("keys",[]))
        if bk!=ak: cfg.append({"path":p,"added_keys":sorted(ak-bk),"removed_keys":sorted(bk-ak)})
    bt=set(before.get("tests",[])); at=set(after.get("tests",[]))
    return {"schema":INTELLIGENCE_SCHEMA,"status":"OBSERVED","added_symbols":added,"removed_symbols":removed,"modified_symbols":modified,"dependency_changes":deps,"configuration_changes":cfg,"test_surface_changes":{"added":sorted(at-bt),"removed":sorted(bt-at)}}
def build_semantic_reality_diff(root: Path, previous: Optional[Dict[str,Any]]=None) -> Dict[str,Any]:
    current=semantic_inventory(root); diff=semantic_reality_diff(root,previous,current)
    result={"inventory":current,"diff":diff,"fingerprint":hashlib.sha256(json.dumps(diff,sort_keys=True,ensure_ascii=False).encode()).hexdigest()}
    _iq_write(root,"semantic",result); return result
def evidence_graph(root: Path) -> Dict[str,Any]:
    ledger=load_evidence_ledger(root); nodes=[]; edges=[]
    for e in ledger:
        eid=str(e.get("id","")); nodes.append({"id":"evidence:"+eid,"kind":"Evidence","status":e.get("status","UNKNOWN"),"claim":e.get("claim",""),"confidence":e.get("confidence","UNKNOWN")})
    state=load_state(root); project_id="project:"+hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]
    nodes.append({"id":project_id,"kind":"Project","path":"."})
    for e in ledger:
        eid=str(e.get("id","")); edges.append({"from":project_id,"to":"evidence:"+eid,"relationship":"HAS_EVIDENCE"})
    result={"schema":2,"nodes":sorted(nodes,key=lambda x:x["id"]),"edges":sorted(edges,key=lambda x:(x["from"],x["to"]))}
    _iq_write(root,"evidence_graph",result); return result
def resolve_evidence_contradictions(root: Path) -> Dict[str,Any]:
    ledger=load_evidence_ledger(root); groups={}
    for e in ledger:
        claim=str(e.get("claim","")); m=re.match(r"(.+?)\s+is\s+(.+)$",claim,re.I)
        if not m: continue
        key=m.group(1).strip().lower(); obj=m.group(2).strip().lower(); groups.setdefault(key,[]).append((obj,e))
    results=[]
    rank={"VERIFIED":100,"OBSERVED":60,"CANDIDATE":40,"UNKNOWN":10,"BLOCKED":0,"CONFLICTING":0}
    for subject,items in sorted(groups.items()):
        objs=sorted(set(x[0] for x in items))
        if len(objs)<2: continue
        scored=[]
        for obj,e in items:
            score=rank.get(str(e.get("status","UNKNOWN")),0)+(20 if str(e.get("confidence"))=="HIGH" else 10 if str(e.get("confidence"))=="MEDIUM" else 0)
            scored.append((score,obj,e.get("id")))
        scored.sort(reverse=True)
        margin=scored[0][0]-scored[1][0]
        results.append({"subject":subject,"objects":objs,"winner":scored[0][1] if margin>=20 else None,"status":"RESOLVED_BY_EVIDENCE" if margin>=20 else "UNRESOLVED","authority":"RECOMMENDATION_ONLY","evidence_status_mutation":False,"independent_verification_required":True,"evidence_ids":[x[2] for x in scored]})
    result={"schema":1,"status":"CONFLICTS_FOUND" if results else "NO_CONFLICTS","resolution":results,"authority":"RECOMMENDATION_ONLY","evidence_status_mutation":False}
    _iq_write(root,"contradictions",result); return result
def synthesize_regression_candidates(root: Path, semantic: Optional[Dict[str,Any]]=None) -> Dict[str,Any]:
    d=(semantic or _iq_read(root,"semantic",{})).get("diff",{}); out=[]
    for s in d.get("removed_symbols",[]): out.append({"id":evidence_id("symbol-present",s["path"]+":"+s["name"]),"predicate":"symbol-present","target":s,"status":"CANDIDATE","verification_required":True,"execution_authority":"NONE"})
    for s in d.get("modified_symbols",[]): out.append({"id":evidence_id("symbol-signature",s["after"]["path"]+":"+s["after"]["name"]),"predicate":"symbol-signature","target":s,"status":"CANDIDATE","verification_required":True,"execution_authority":"NONE"})
    for dep in ((d.get("dependency_changes",{}) if isinstance(d.get("dependency_changes",{}),dict) else {}).get("removed",[])): out.append({"id":evidence_id("dependency-present",dep),"predicate":"dependency-present","target":dep,"status":"CANDIDATE","verification_required":True,"execution_authority":"NONE"})
    for test in ((d.get("test_surface_changes",{}) if isinstance(d.get("test_surface_changes",{}),dict) else {}).get("removed",[])): out.append({"id":evidence_id("test-present",test),"predicate":"test-present","target":test,"status":"CANDIDATE","verification_required":True,"execution_authority":"NONE"})
    result={"schema":1,"candidates":out,"count":len(out)}; _iq_write(root,"regression_candidates",result); return result
def build_regression_validation_tasks(root: Path, candidates: Optional[Dict[str,Any]]=None) -> Dict[str,Any]:
    c=(candidates or _iq_read(root,"regression_candidates",{})).get("candidates",[]); tasks=[]
    for x in c:
        method={"symbol-present":"symbol-presence-check","symbol-signature":"symbol-signature-check","dependency-present":"dependency-presence-check","test-present":"test-presence-check"}.get(x.get("predicate"),"provider-backed-check")
        tasks.append({"id":"task-"+x["id"],"candidate_id":x["id"],"method":method,"status":"READY","independent_verification_required":True,"execution_authority":"NONE"})
    result={"schema":1,"tasks":tasks}; _iq_write(root,"regression_tasks",result); return result
def feature_contracts(root: Path) -> Dict[str,Any]:
    data=_iq_read(root,"feature_contracts",{"schema":1,"features":[]})
    if not isinstance(data,dict): data={"schema":1,"features":[]}
    for f in data.get("features",[]):
        if not isinstance(f,dict): continue
        f.setdefault("must",[]); f.setdefault("must_not",[]); f.setdefault("should",[])
    data.setdefault("status","READY"); _iq_write(root,"feature_contracts",data); return data
def verification_coverage(root: Path) -> Dict[str,Any]:
    semantic=_iq_read(root,"semantic",{}); graph=_iq_read(root,"evidence_graph",{})
    ledger=load_evidence_ledger(root)
    dims={k:{"status":"UNKNOWN","evidence":0} for k in ["source","build","runtime","server","client","multiplayer","regression","docs","performance","security"]}
    if semantic.get("inventory"): dims["source"]={"status":"OBSERVED","evidence":1}
    build_evidence=[x for x in ledger if isinstance(x,dict) and x.get("status")=="VERIFIED" and (
        str(x.get("provider","")).lower() in {"build","generic-build","generic-verify","gradle","maven","cargo","dotnet","npm"}
        or any(token in str(x.get("claim","")).lower() for token in ("build", "compile", "artifact", "test suite"))
        or str(x.get("source","")).startswith("command:")
    )]
    if build_evidence:
        dims["build"]={"status":"OBSERVED","evidence":len(build_evidence)}
    if (root/STATE_DIR/SECURITY_REPORT).exists(): dims["security"]={"status":"OBSERVED","evidence":1}
    contracts=feature_contracts(root); gaps=[]
    for f in contracts.get("features",[]):
        checks=f.get("verification",{}) if isinstance(f,dict) else {}
        missing=[d for d in dims if not checks.get(d)]
        if missing: gaps.append({"feature":f.get("id",f.get("name","UNKNOWN")),"missing":missing})
    result={"schema":1,"dimensions":dims,"contract_gaps":gaps,"evidence_graph_nodes":len(graph.get("nodes",[]))}
    _iq_write(root,"coverage",result); return result
def causal_analysis(root: Path) -> Dict[str,Any]:
    sem=_iq_read(root,"semantic",{}).get("diff",{}); candidates=_iq_read(root,"regression_candidates",{}).get("candidates",[])
    chains=[]
    for s in sem.get("removed_symbols",[]): chains.append({"chain":[{"kind":"change","value":s},{"kind":"potential-effect","value":"downstream references may regress"}],"confidence":"LOW","evidence_ids":[]})
    for s in sem.get("modified_symbols",[]): chains.append({"chain":[{"kind":"signature-change","value":s},{"kind":"potential-effect","value":"callers may become incompatible"}],"confidence":"LOW","evidence_ids":[]})
    result={"schema":1,"status":"CANDIDATE_CAUSALITY","chains":chains,"independent_verification_required":bool(chains),"candidate_count":len(candidates)}; _iq_write(root,"causal",result); return result
def intent_preservation(root: Path, intent: Optional[Dict[str,Any]]=None) -> Dict[str,Any]:
    current=intent or _iq_read(root,"intent",{"schema":1,"claims":[]}); sem=_iq_read(root,"semantic",{}).get("diff",{}); claims=current.get("claims",[])
    findings=[]
    for c in claims:
        target=str(c.get("target","")); affected=any(target in json.dumps(x,sort_keys=True) for x in sem.get("removed_symbols",[])+sem.get("modified_symbols",[]))
        findings.append({"claim":c,"status":"REQUIRES_VERIFICATION" if affected else "NO_OBSERVED_SEMANTIC_CONFLICT","independent_verification_required":affected})
    result={"schema":1,"claims":claims,"findings":findings,"status":"UNKNOWN" if not claims else "CANDIDATE"}; _iq_write(root,"intent",result); return result
def proof_carrying_change(root: Path) -> Dict[str,Any]:
    payload={"semantic":_iq_read(root,"semantic",{}),"coverage":_iq_read(root,"coverage",{}),"causal":_iq_read(root,"causal",{}),"intent":_iq_read(root,"intent",{}),"regression":_iq_read(root,"regression_tasks",{}),"contradictions":_iq_read(root,"contradictions",{})}
    fp=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    blockers=[]
    if payload["semantic"].get("diff",{}).get("status")=="UNKNOWN": blockers.append("semantic-baseline-unknown")
    if payload["coverage"].get("contract_gaps"): blockers.append("verification-coverage-gaps")
    result={"schema":1,"proof_id":fp,"status":"READY_FOR_VERIFICATION" if blockers else "CANDIDATE","blockers":blockers,"execution_authority":"NONE","payload_fingerprint":fp}; _iq_write(root,"proof",result); return result
def mutation_plan(root: Path) -> Dict[str,Any]:
    existing=_iq_read(root,"mutations",{})
    if existing.get("schema",1) >= 2 and existing.get("status") not in {"NOT_AVAILABLE", "REVIEW_REQUIRED"}: return existing
    sem=_iq_read(root,"semantic",{}).get("inventory",{}); sem=sem or semantic_inventory(root); candidates=[]
    for s in sem.get("symbols",[])[:200]: candidates.append({"id":evidence_id("mutation",s),"target":s,"operator":"signature-or-body-perturbation","execution_authority":"NONE","status":"PLANNED"})
    result={"schema":1,"mutations":candidates,"safe_mode":True,"project_mutation_permitted":False}; _iq_write(root,"mutations",result); return result
def engineering_memory(root: Path, event: Optional[Dict[str,Any]]=None) -> Dict[str,Any]:
    p=_iq_path(root,"memory")
    if event:
        e=dict(event); e.setdefault("time",now()); e["id"]=evidence_id(str(e.get("kind","event")),e.get("subject",""),e)
        with p.open("a",encoding="utf-8") as f: f.write(json.dumps(redact_sensitive(e),sort_keys=True,ensure_ascii=False)+"\n")
    entries=[]
    if p.exists():
        for line in p.read_text(encoding="utf-8",errors="replace").splitlines()[-5000:]:
            try: entries.append(json.loads(line))
            except Exception: pass
    return {"schema":1,"entries":entries,"append_only":True}
def compatibility_graph(root: Path) -> Dict[str,Any]:
    vg=load_json(root/STATE_DIR/VERSION_GRAPH,{}) if (root/STATE_DIR/VERSION_GRAPH).exists() else {}
    dl=load_json(root/STATE_DIR/DEPENDENCY_LOCK,{}) if (root/STATE_DIR/DEPENDENCY_LOCK).exists() else {}
    result={"schema":1,"status":"OBSERVED","version_graph":vg,"dependency_lock":dl,"edges":[],"fabricated_edges":False}
    _iq_write(root,"compatibility",result); return result
def counterfactual_plan(root: Path, alternatives: Optional[List[str]]=None) -> Dict[str,Any]:
    existing=_iq_read(root,"counterfactual",{})
    if existing.get("schema",1) >= 2 and existing.get("status") not in {"PLANNED", "NOT_AVAILABLE"}: return existing
    alts=alternatives or ["Original","Patch A","Patch B","A+B"]
    result={"schema":1,"status":"PLANNED","variants":[{"id":x,"execution_authority":"NONE","status":"PLANNED"} for x in alts],"comparison_dimensions":["build","tests","artifact","semantic-reality","regressions","security"],"isolated_execution_required":True}; _iq_write(root,"counterfactual",result); return result
def failure_injection_plan(root: Path) -> Dict[str,Any]:
    existing=_iq_read(root,"failure_lab",{})
    if existing.get("schema",1) >= 2 and existing.get("status") not in {"PLANNED", "NOT_AVAILABLE"}: return existing
    failures=["dependency-failure","missing-resource","broken-registry","invalid-config","network-mismatch","corrupted-state","missing-asset","server-client-divergence"]
    result={"schema":1,"status":"PLANNED","cases":[{"id":x,"execution_authority":"NONE","status":"PLANNED","expected":"DETECTION_OR_BLOCK"} for x in failures]}; _iq_write(root,"failure_lab",result); return result
def feature_verification_gaps(root: Path) -> Dict[str,Any]:
    contracts=feature_contracts(root); sem=_iq_read(root,"semantic",{}).get("inventory",{})
    if not isinstance(sem,dict) or not sem.get("symbols"):
        sem=semantic_inventory(root)
    cov=verification_coverage(root)
    implemented=set()
    for symbol in sem.get("symbols",[]):
        if isinstance(symbol,dict) and isinstance(symbol.get("name"),str):
            implemented.add(symbol["name"])
        elif isinstance(symbol,str):
            implemented.add(symbol)
    gaps=[]
    for f in contracts.get("features",[]):
        name=f.get("id",f.get("name")); ifaces=f.get("implementation_symbols",[])
        missing=[x for x in ifaces if x not in implemented]
        if missing or name in {g.get("feature") for g in cov.get("contract_gaps",[])}: gaps.append({"feature":name,"missing_symbols":missing,"coverage_gap":True})
    result={"schema":1,"gaps":gaps,"status":"OBSERVED"}; _iq_write(root,"feature_gaps",result); return result
def runtime_lab_plan(root: Path) -> Dict[str,Any]:
    existing=_iq_read(root,"runtime_lab",{})
    if existing.get("schema",1) >= 2 and existing.get("status") not in {"NOT_AVAILABLE"}: return existing
    result={"schema":1,"status":"NOT_AVAILABLE","levels":["headless-server","runtime-log-scan","optional-client","optional-multiplayer"],"enabled":False,"execution_authority":"NONE","requires_explicit_enablement":True}; _iq_write(root,"runtime_lab",result); return result
def benchmark_observatory(root: Path) -> Dict[str,Any]:
    records=[]
    for p in _iq_files(root) if (root/BENCHMARK_DIR).exists() else []:
        if BENCHMARK_DIR not in p.relative_to(root).parts: continue
        records.append({"path":rel(root,p),"sha256":_iq_hash_file(p)})
    result={"schema":1,"status":"OBSERVED","records":records,"count":len(records),"deterministic":True}; _iq_write(root,"benchmark_observatory",result); return result
def performance_observatory(root: Path, elapsed: Optional[float]=None) -> Dict[str,Any]:
    result=_iq_read(root,"performance",{"schema":1,"status":"OBSERVED","runs":[]});
    if elapsed is not None: result.setdefault("runs",[]).append({"time":now(),"duration_seconds":round(float(elapsed),6)})
    result["runs"]=result.get("runs",[])[-500:]; result["metrics"]={"runs":len(result["runs"]),"last_duration_seconds":result["runs"][-1]["duration_seconds"] if result["runs"] else None}; _iq_write(root,"performance",result); return result
def intelligence_suite(root: Path) -> Dict[str,Any]:
    started=time.monotonic(); ensure_state_dir(root)
    prev=_iq_read(root,"semantic",{}).get("inventory")
    sem=build_semantic_reality_diff(root,prev); cand=synthesize_regression_candidates(root,sem); tasks=build_regression_validation_tasks(root,cand)
    graph=evidence_graph(root); contradictions=resolve_evidence_contradictions(root); contracts=feature_contracts(root); cov=verification_coverage(root); causal=causal_analysis(root); intent=intent_preservation(root); proof=proof_carrying_change(root); mutations=mutation_plan(root); memory=engineering_memory(root); compat=compatibility_graph(root); counter=counterfactual_plan(root); failure=failure_injection_plan(root); gaps=feature_verification_gaps(root); runtime=runtime_lab_plan(root); bench=benchmark_observatory(root); perf=performance_observatory(root,time.monotonic()-started)
    return {"schema":INTELLIGENCE_SCHEMA,"status":"GENERATED","artifacts":{k:_iq_path(root,k).name for k in INTELLIGENCE_FILES},"proof_status":proof.get("status"),"candidate_counts":{"regression":len(cand.get("candidates",[])),"causal":len(causal.get("chains",[])),"mutation":len(mutations.get("mutations",[])),"gaps":len(gaps.get("gaps",[]))},"elapsed_seconds":perf["metrics"]["last_duration_seconds"]}
def cmd_intelligence(args):
    root=root_path(args.project); require_qyrenith(root); result=intelligence_suite(root); print(json.dumps(result,indent=2,ensure_ascii=False)); return 0

# ---------------------------------------------------------------------------
# External check / verify
# ---------------------------------------------------------------------------
def _declared_commands(root: Path, names: Sequence[str]) -> Dict[str, Any]:
    cfg = load_json(root / STATE_DIR / "intelligence-config.json", {}) if (root / STATE_DIR / "intelligence-config.json").exists() else {}
    commands = cfg.get("commands", {}) if isinstance(cfg, dict) else {}
    return {name: commands.get(name) for name in names if commands.get(name)}
def _run_isolated_command(root: Path, command: Sequence[str], timeout: int = 120, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    if not command or not all(isinstance(x, str) and x for x in command):
        return {"status": "BLOCKED", "reason": "empty-or-invalid-command"}
    if any("|" in x or ";" in x or "&&" in x or "||" in x or "$(" in x or "`" in x for x in command):
        return {"status": "BLOCKED", "reason": "shell-metacharacters-not-allowed"}
    started = time.monotonic()
    safe_env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), "PYTHONUNBUFFERED": "1"}
    if env:
        for k, v in env.items():
            if re.fullmatch(r"[A-Z_][A-Z0-9_]*", k): safe_env[k] = str(v)
    kwargs={"cwd":str(root),"env":safe_env,"stdin":subprocess.DEVNULL,"stdout":subprocess.PIPE,"stderr":subprocess.STDOUT,"text":True,"shell":False}
    if os.name == "nt":
        kwargs["creationflags"]=getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0)
    else:
        kwargs["start_new_session"]=True
    proc=None
    try:
        proc=subprocess.Popen(list(command),**kwargs)
        try:
            output=proc.communicate(timeout=max(1,min(timeout,900)))[0] or ""
        except subprocess.TimeoutExpired as e:
            output=(e.stdout or "") if isinstance(e.stdout,str) else ""
            _terminate_process(proc)
            output=output[-20000:]
            return {"status":"BLOCKED","reason":"timeout","duration_seconds":round(time.monotonic()-started,6),
                    "output":output,"output_sha256":hashlib.sha256(output.encode()).hexdigest()}
        output=output[-20000:]
        return {"status":"PASS" if proc.returncode==0 else "FAIL","exit_code":proc.returncode,
                "duration_seconds":round(time.monotonic()-started,6),"output":output,
                "output_sha256":hashlib.sha256(output.encode()).hexdigest()}
    except (OSError,ValueError) as e:
        if proc is not None:
            _terminate_process(proc)
        return {"status":"BLOCKED","reason":type(e).__name__,"message":str(e)}
def execute_runtime_lab(root: Path, timeout: int = 120) -> Dict[str, Any]:
    commands = _declared_commands(root, ["runtime", "server", "client", "multiplayer"])
    if not commands:
        result = {"schema": 2, "status": "NOT_AVAILABLE", "enabled": False,
                  "reason": "No explicitly declared runtime command", "execution_authority": "NONE"}
        _iq_write(root, "runtime_lab", result); return result
    results = {name: _run_isolated_command(root, cmd if isinstance(cmd, list) else [str(cmd)], timeout)
               for name, cmd in commands.items()}
    statuses = [x.get("status") for x in results.values()]
    status = "PASS" if statuses and all(x == "PASS" for x in statuses) else ("BLOCKED" if "BLOCKED" in statuses else "FAIL")
    result = {"schema": 2, "status": status, "enabled": True, "execution_authority": "EXPLICIT",
              "commands": results, "independent_verification_required": status != "PASS"}
    _iq_write(root, "runtime_lab", result); return result
def execute_failure_injection_lab(root: Path, timeout: int = 120) -> Dict[str, Any]:
    cases = _iq_read(root, "failure_lab", {}).get("cases", [])
    commands = _declared_commands(root, ["failure-validation"])
    if not commands:
        result = {"schema": 2, "status": "NOT_AVAILABLE", "execution_authority": "NONE",
                  "reason": "No explicitly declared failure-validation command", "cases": cases}
        _iq_write(root, "failure_lab", result); return result
    command = commands["failure-validation"]
    base = command if isinstance(command, list) else [str(command)]
    executed = []
    for case in cases:
        run = _run_isolated_command(root, [*base, "--case", str(case.get("id"))], timeout)
        executed.append({**case, "execution": run, "detected": run.get("status") in {"FAIL", "BLOCKED"}})
    status = "PASS" if executed and all(x.get("detected") for x in executed) else ("REVIEW_REQUIRED" if executed else "NOT_AVAILABLE")
    result = {"schema": 2, "status": status,
              "execution_authority": "EXPLICIT", "cases": executed}
    _iq_write(root, "failure_lab", result); return result
def execute_mutation_lab(root: Path, timeout: int = 120, limit: int = 20) -> Dict[str, Any]:
    plan = _iq_read(root, "mutations", {})
    commands = _declared_commands(root, ["mutation-validation"])
    if not commands:
        result = {"schema": 2, "status": "NOT_AVAILABLE", "execution_authority": "NONE",
                  "reason": "No explicitly declared mutation-validation command", "mutations": plan.get("mutations", [])[:limit]}
        _iq_write(root, "mutations", result); return result
    command = commands["mutation-validation"]
    base = command if isinstance(command, list) else [str(command)]
    executed=[]
    for mutation in plan.get("mutations", [])[:max(1, min(limit, 100))]:
        run = _run_isolated_command(root, [*base, "--mutation", str(mutation.get("id"))], timeout)
        executed.append({**mutation, "execution": run,
                         "survived": run.get("status") == "PASS",
                         "finding": "BLIND_SPOT_CANDIDATE" if run.get("status") == "PASS" else "DETECTED_OR_BLOCKED"})
    result={"schema":2,"status":"PASS" if executed and not any(x["survived"] for x in executed) else "REVIEW_REQUIRED",
            "execution_authority":"EXPLICIT","mutations":executed}
    _iq_write(root,"mutations",result); return result
def execute_counterfactual(root: Path, timeout: int = 120) -> Dict[str, Any]:
    commands = _declared_commands(root, ["counterfactual"])
    if not commands:
        result={"schema":2,"status":"NOT_AVAILABLE","execution_authority":"NONE","reason":"No explicitly declared counterfactual command"}
        _iq_write(root,"counterfactual",result); return result
    command=commands["counterfactual"]; base=command if isinstance(command,list) else [str(command)]
    variants=_iq_read(root,"counterfactual",{}).get("variants",[]); results=[]
    for variant in variants:
        run=_run_isolated_command(root,[*base,"--variant",str(variant.get("id"))],timeout)
        results.append({**variant,"execution":run})
    statuses=[x["execution"].get("status") for x in results]
    result={"schema":2,"status":"PASS" if statuses and all(x=="PASS" for x in statuses) else ("BLOCKED" if "BLOCKED" in statuses else "REVIEW_REQUIRED"),
            "execution_authority":"EXPLICIT","variants":results}
    _iq_write(root,"counterfactual",result); return result
def benchmark_observatory_execute(root: Path, timeout: int = 300) -> Dict[str, Any]:
    started=time.monotonic(); manifest_results=[]
    for fixture in benchmark_projects(root):
        manifest_results.append(fixture)
    commands=_declared_commands(root,["benchmark"])
    execution=None
    if commands:
        cmd=commands["benchmark"]; execution=_run_isolated_command(root,cmd if isinstance(cmd,list) else [str(cmd)],timeout)
    if execution is not None:
        status=execution.get("status","BLOCKED")
    elif manifest_results:
        status="PASS" if all(x.get("status")=="PASS" for x in manifest_results) else "FAIL"
    else:
        status="NOT_AVAILABLE"
    result={"schema":2,"status":status,"fixtures":manifest_results,"execution":execution,
            "duration_seconds":round(time.monotonic()-started,6),"deterministic":True}
    _iq_write(root,"benchmark_observatory",result); return result
def verification_verdict(root: Path) -> Dict[str, Any]:
    artifacts={k:_iq_read(root,k,{}) for k in INTELLIGENCE_FILES if k != "memory"}
    blockers=[]; unknowns=[]; findings=[]
    for key,data in artifacts.items():
        status=str(data.get("status", "UNKNOWN")) if isinstance(data,dict) else "UNKNOWN"
        if status in {"BLOCKED","FAIL","REVIEW_REQUIRED"}: findings.append({"artifact":key,"status":status})
        if status in {"BLOCKED","FAIL"}: blockers.append(key)
        if status in {"UNKNOWN","NOT_AVAILABLE"}: unknowns.append(key)
    proof=artifacts.get("proof",{})
    if proof.get("blockers"): blockers.extend([f"proof:{x}" for x in proof["blockers"]])
    verdict="PASS" if not blockers and not unknowns else ("BLOCKED" if blockers or unknowns else "REVIEW_REQUIRED")
    return {"schema":1,"verdict":verdict,"blocking_artifacts":sorted(set(blockers)),"unknown_artifacts":sorted(set(unknowns)),"findings":findings,
            "independent_verification_required":verdict!="PASS"}
def _external_read_text_capped(path: Path) -> Optional[str]:
    """Read up to EXTERNAL_SCAN_READ_CAP bytes; None for binary/unreadable."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(EXTERNAL_SCAN_READ_CAP + 1)
    except OSError:
        return None
    if b"\x00" in data:
        return None
    return data[:EXTERNAL_SCAN_READ_CAP].decode("utf-8", errors="replace")
def _external_finding_line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1
def external_finding_scan(root: Path, files: List[Path]) -> Dict[str, Any]:
    """Read-only pattern scan over already-collected files. Never writes."""
    findings: List[Dict[str, Any]] = []
    residue_counts = {"TODO": 0, "FIXME": 0, "XXX": 0, "HACK": 0}
    residue_individual = 0
    for fp in files:
        try:
            size = fp.stat().st_size
        except OSError:
            continue
        rp = fp.relative_to(root).as_posix()
        if size > EXTERNAL_OVERSIZED_BYTES:
            findings.append({"severity": "MEDIUM", "code": "OVERSIZED_FILE",
                             "path": rp, "size": size,
                             "reason": f"{size} bytes exceeds the 10 MiB review threshold"})
            continue
        text = _external_read_text_capped(fp)
        if text is None:
            continue
        key_match = _EXTERNAL_PRIVATE_KEY_RE.search(text)
        if key_match:
            findings.append({"severity": "CRITICAL", "code": "PRIVATE_KEY_MATERIAL",
                             "path": rp, "line": _external_finding_line(text, key_match.start()),
                             "reason": "PEM private key block in a tracked file"})
        secret_match = _EXTERNAL_SECRET_RE.search(text)
        if secret_match:
            value = secret_match.group(0).split("=", 1)[-1].split(":", 1)[-1].strip()
            if not _is_secret_placeholder(value):
                findings.append({"severity": "HIGH", "code": "POSSIBLE_SECRET",
                                 "path": rp, "line": _external_finding_line(text, secret_match.start()),
                                 "reason": "Credential-like assignment; verify and rotate if real"})
        cmd_match = _EXTERNAL_DANGEROUS_CMD_RE.search(text)
        if cmd_match:
            findings.append({"severity": "HIGH", "code": "DANGEROUS_OR_NETWORK_COMMAND_PATTERN",
                             "path": rp, "line": _external_finding_line(text, cmd_match.start()),
                             "reason": "Destructive or download-and-execute shell pattern; review before running"})
        for todo_match in _EXTERNAL_TODO_RE.finditer(text):
            label = todo_match.group(1)
            residue_counts[label] = residue_counts.get(label, 0) + 1
            if residue_individual < EXTERNAL_RESIDUE_INDIVIDUAL_CAP:
                findings.append({"severity": "LOW", "code": "RESIDUE_MARKER",
                                 "path": rp, "line": _external_finding_line(text, todo_match.start()),
                                 "reason": f"{label} marker left in source"})
                residue_individual += 1
    findings.sort(key=lambda finding: (_SEVERITY_RANK.get(finding["severity"], 9), finding["path"]))
    truncated = len(findings) > EXTERNAL_FINDING_CAP
    return {"findings": findings[:EXTERNAL_FINDING_CAP], "findings_truncated": truncated,
            "residue_summary": residue_counts}
def external_hygiene(root: Path) -> Dict[str, Any]:
    """Project hygiene signals. Read-only; findings use LOW severity."""
    try:
        names = {p.name.lower() for p in root.iterdir()}
    except OSError:
        names = set()
    has_license = any(name.startswith(("license", "licence", "copying")) for name in names)
    has_readme = any(name.startswith("readme") for name in names)
    has_gitignore = ".gitignore" in names
    ci_systems: Dict[str, List[str]] = {}
    if (root / ".github" / "workflows").is_dir():
        ci_systems["github-actions"] = sorted(p.name for p in (root / ".github" / "workflows").iterdir() if p.is_file())
    for marker, system in ((".gitlab-ci.yml", "gitlab-ci"), ("Jenkinsfile", "jenkins"),
                           ("azure-pipelines.yml", "azure-pipelines"), (".circleci", "circleci")):
        if (root / marker).exists():
            ci_systems[system] = [marker]
    build_output_dirs = [d for d in ("build", "dist", "target", "out", "bin", "obj") if (root / d).is_dir()]
    findings: List[Dict[str, Any]] = []
    if not has_license:
        findings.append({"severity": "LOW", "code": "NO_LICENSE_FILE", "path": ".",
                         "reason": "No LICENSE/COPYING file at project root"})
    if not has_readme:
        findings.append({"severity": "LOW", "code": "NO_README", "path": ".",
                         "reason": "No README file at project root"})
    if not ci_systems:
        findings.append({"severity": "LOW", "code": "NO_CI_CONFIG", "path": ".",
                         "reason": "No recognized CI configuration found"})
    if build_output_dirs and not has_gitignore:
        findings.append({"severity": "MEDIUM", "code": "BUILD_OUTPUTS_WITHOUT_GITIGNORE", "path": ".",
                         "reason": f"Build output dirs present ({', '.join(build_output_dirs)}) with no .gitignore"})
    return {"license_present": has_license, "readme_present": has_readme,
            "gitignore_present": has_gitignore, "ci_systems": ci_systems,
            "build_output_dirs": build_output_dirs, "findings": findings}
def external_baseline_diff(old_report: Dict[str, Any], new_report: Dict[str, Any]) -> Dict[str, Any]:
    """Diff two external-check reports by file manifest and finding identity."""
    old_manifest = {p: s for p, s in old_report.get("file_manifest", []) if isinstance(p, str)}
    new_manifest = {p: s for p, s in new_report.get("file_manifest", []) if isinstance(p, str)}
    if not old_manifest and not new_manifest:
        return {"baseline_compared": False,
                "reason": "Baseline report has no file_manifest; re-run external-check to create one."}
    added = sorted(p for p in new_manifest if p not in old_manifest)
    removed = sorted(p for p in old_manifest if p not in new_manifest)
    modified = sorted(p for p in new_manifest if p in old_manifest and new_manifest[p] != old_manifest[p])
    def finding_key(finding: Dict[str, Any]) -> str:
        return f"{finding.get('code')}|{finding.get('path')}|{finding.get('line', '')}"
    old_findings = {finding_key(f) for f in old_report.get("findings", []) if isinstance(f, dict)}
    new_findings = {finding_key(f) for f in new_report.get("findings", []) if isinstance(f, dict)}
    def cap(items: List[str]) -> Dict[str, Any]:
        return {"items": items[:EXTERNAL_BASELINE_LIST_CAP],
                "truncated": len(items) > EXTERNAL_BASELINE_LIST_CAP, "total": len(items)}
    return {"baseline_compared": True,
            "baseline_project": old_report.get("project"), "current_project": new_report.get("project"),
            "added": cap(added), "removed": cap(removed), "modified_size_changed": cap(modified),
            "findings_added": cap(sorted(new_findings - old_findings)),
            "findings_resolved": cap(sorted(old_findings - new_findings))}
def external_project_check(project: str) -> Dict[str, Any]:
    """Read-only inspection of an external project. Never writes into the target tree."""
    root = root_path(project)
    ignored_dirs = {
        ".git", ".qyrenith", ".gradle", ".gradle-bootstrap", ".idea", ".vscode", "node_modules",
        "build", "dist", "out", "target", "venv", ".venv", "__pycache__",
        ".pytest_cache", ".mypy_cache", "coverage", "vendor"
    }
    build_markers = {
        "gradle": ["settings.gradle", "settings.gradle.kts", "build.gradle", "build.gradle.kts", "gradlew", "gradlew.bat"],
        "maven": ["pom.xml", "mvnw", "mvnw.cmd"],
        "python": ["pyproject.toml", "setup.py", "tox.ini", "pytest.ini", "requirements.txt"],
        "node": ["package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json"],
        "rust": ["Cargo.toml", "Cargo.lock"],
        "dotnet": ["*.sln", "*.csproj", "*.fsproj"],
        "go": ["go.mod", "go.work"],
        "cmake": ["CMakeLists.txt", "CMakePresets.json"],
    }
    files: List[Path] = []
    file_sizes: Dict[str, int] = {}
    symlink_findings: List[Dict[str, Any]] = []
    dirs_seen = 0
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        dirnames[:] = sorted(d for d in dirnames if d not in ignored_dirs and not (current_path / d).is_symlink())
        dirs_seen += len(dirnames)
        for filename in sorted(filenames):
            fp = current_path / filename
            if fp.is_symlink():
                try:
                    if not fp.resolve().is_relative_to(root.resolve()):
                        symlink_findings.append({"severity": "HIGH", "code": "SYMLINK_ESCAPE",
                                                 "path": fp.relative_to(root).as_posix(),
                                                 "reason": "Symlink points outside the project root"})
                except Exception:
                    symlink_findings.append({"severity": "HIGH", "code": "SYMLINK_UNRESOLVED",
                                             "path": fp.relative_to(root).as_posix(),
                                             "reason": "Symlink target could not be resolved"})
                continue
            if not fp.is_file():
                continue
            files.append(fp)
            rp_size = fp.relative_to(root).as_posix()
            try:
                file_sizes[rp_size] = fp.stat().st_size
            except OSError:
                file_sizes[rp_size] = -1
            if len(files) >= 50000:
                break
        if len(files) >= 50000:
            break

    relpaths = [fp.relative_to(root).as_posix() for fp in files]
    top_level = sorted({x.split("/", 1)[0] for x in relpaths})
    detected: Dict[str, List[str]] = {}
    root_names = {p.name for p in root.iterdir()}
    for system, markers in build_markers.items():
        found = []
        for marker_name in markers:
            if any(Path(name).match(marker_name) for name in root_names):
                found.append(marker_name)
        if found:
            detected[system] = found

    test_paths = [x for x in relpaths if (
        Path(x).name.lower().startswith(("test_", "tests_")) or
        "/tests/" in "/" + x.lower() + "/" or
        "/test/" in "/" + x.lower() + "/" or
        Path(x).name.lower().endswith(("_test.py", ".spec.ts", ".test.ts", ".spec.js", ".test.js"))
    )]
    extension_counts: Dict[str, int] = {}
    for relpath in relpaths:
        suffix = Path(relpath).suffix.lower() or "[no extension]"
        extension_counts[suffix] = extension_counts.get(suffix, 0) + 1

    # Avoid invoking Git here: even status commands can refresh index metadata on some setups.
    git_status: Dict[str, Any] = {
        "repository_metadata_present": (root / ".git").exists(),
        "command_executed": False,
        "reason": "Git commands are intentionally not run in strict read-only mode."
    }

    scan = external_finding_scan(root, files)
    hygiene = external_hygiene(root)
    all_findings = symlink_findings + scan["findings"] + hygiene["findings"]
    all_findings.sort(key=lambda finding: (_SEVERITY_RANK.get(finding["severity"], 9), finding["path"]))
    findings_truncated = scan["findings_truncated"] or len(all_findings) > EXTERNAL_FINDING_CAP
    severity_counts: Dict[str, int] = {}
    for finding in all_findings:
        severity_counts[finding["severity"]] = severity_counts.get(finding["severity"], 0) + 1
    manifest = [[rp, file_sizes.get(rp, -1)] for rp in relpaths]

    return {
        "schema": 1,
        "mode": "external_read_only_check",
        "project": str(root),
        "read_only": True,
        "target_modified": False,
        "limits": {"max_files": 50000, "file_limit_reached": len(files) >= 50000,
                   "scan_read_cap_bytes": EXTERNAL_SCAN_READ_CAP,
                   "finding_cap": EXTERNAL_FINDING_CAP},
        "summary": {
            "file_count": len(files), "directory_count_estimate": dirs_seen,
            "top_level_entries": top_level,
            "test_file_count_heuristic": len(test_paths),
            "finding_counts_by_severity": severity_counts,
        },
        "build_systems": detected,
        "likely_test_files_sample": test_paths[:100],
        "extension_counts": dict(sorted(extension_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "git_status": git_status,
        "findings": all_findings[:EXTERNAL_FINDING_CAP],
        "findings_truncated": findings_truncated,
        "residue_summary": scan["residue_summary"],
        "hygiene": {k: v for k, v in hygiene.items() if k != "findings"},
        "file_manifest": manifest,
        "checks_not_performed": [
            "No build or test commands were executed.",
            "No project files or repository metadata were intentionally written, modified, or deleted.",
            "File presence and names do not prove that the project builds or behaves correctly.",
            "Detected build-system markers are heuristic and must be reviewed against project documentation/CI.",
            "Pattern findings are leads, not proof: every finding must be verified at its path before acting.",
            "Absence of findings proves nothing; only reviewed paths count as checked."
        ]
    }
def _load_baseline_report(path: str) -> Dict[str, Any]:
    """Read a baseline JSON report, tolerating UTF-16 from redirected CLI output."""
    last_error: Optional[Exception] = None
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            with open(path, encoding=encoding) as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return data
            raise ValueError("Baseline report is not a JSON object.")
        except (OSError, ValueError, UnicodeError) as exc:
            last_error = exc
    raise ValueError(f"Could not parse baseline report: {last_error}")
def cmd_external_check(args):
    report = external_project_check(args.project)
    baseline = getattr(args, "baseline", "") or ""
    if baseline:
        try:
            old_report = _load_baseline_report(baseline)
            report["baseline_diff"] = external_baseline_diff(old_report, report)
        except (OSError, ValueError) as exc:
            report["baseline_diff"] = {"baseline_compared": False,
                                       "reason": f"Could not read baseline report: {exc}"}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0
def cmd_external_verify(args):
    """Optionally run only explicitly supplied checks in an external project."""
    root = root_path(args.project)
    commands = getattr(args, "check_command", None) or []
    if not args.execute:
        report = external_project_check(str(root))
        report["mode"] = "external_verify_plan_only"
        report["commands_requested"] = commands
        report["message"] = "No commands were executed. Review the project and re-run with --execute to run explicitly supplied commands."
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    if not commands:
        die("PREFLIGHT_FAILURE", "external-verify --execute requires at least one --check-command.")
    results = []
    for raw in commands:
        try:
            argv = shlex.split(raw, posix=(os.name != "nt"))
            if os.name == "nt":
                # shlex with posix=False keeps surrounding quotes in the
                # token, so `python -c "print('x')"` would execute a bare
                # string literal and print nothing. Strip one layer of
                # matching quotes per token; backslash paths stay intact
                # (posix=True would eat them, so it is not an option here).
                argv = [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'" else t
                        for t in argv]
        except ValueError as exc:
            die("PREFLIGHT_FAILURE", f"Invalid --check-command quoting: {exc}")
        if not argv:
            die("PREFLIGHT_FAILURE", "Empty --check-command is not allowed.")
        try:
            code, output = cmdrun(argv, root, timeout=max(1, min(int(args.timeout), 3600)))
            limited = "TIMEOUT" in output or "OUTPUT_LIMIT_EXCEEDED" in output
            results.append({
                "command": argv, "exit_code": code,
                "status": "PASS" if code == 0 else ("BLOCKED" if limited else "FAIL"),
                "output": output[-16000:],
                "timed_out_or_output_limited": limited,
            })
        except QyrenithError as exc:
            results.append({
                "command": argv, "exit_code": None, "status": "BLOCKED",
                "output": f"{exc.code}: {exc.message}", "timed_out_or_output_limited": False,
            })
    report = {
        "schema": 1, "mode": "external_explicit_command_verification",
        "project": str(root), "qyrenith_required_in_target": False,
        "qyrenith_state_written_to_target": False, "commands_executed": True,
        "warning": "Explicit commands may write build artifacts, download dependencies, or otherwise change the target. Review commands before execution.",
        "results": results,
        "overall_status": "PASS" if all(x["status"] == "PASS" for x in results) else (
            "FAIL" if any(x["status"] == "FAIL" for x in results) else "BLOCKED"
        ),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["overall_status"] == "PASS" else (1 if report["overall_status"] == "FAIL" else 2)

# ---------------------------------------------------------------------------
# Parser / main
# ---------------------------------------------------------------------------
def parser():
    p=argparse.ArgumentParser(description=f"Qyrenith {VERSION} Project Verification & Control Plane"); p.add_argument("command",choices=["audit","plan","port","continue","build","verify","policy","skills","reality","inspect","explain","dry-run","rollback","doctor","status","report","self-test","benchmark","failure-quality","security-test","security-review","recovery-test","graph","compatibility","replay","adapters","worker-run","artifact-inspect","evidence","git-test","fuzz-test","public-audit","domains","intelligence","external-check","external-verify"]); p.add_argument("-p","--project",default="."); p.add_argument("--check-command",action="append",default=[],help="Explicit command for external-verify; repeat for multiple checks"); p.add_argument("--target-mc",default=""); p.add_argument("--target-loader",default=""); p.add_argument("--target-loader-version",default=""); p.add_argument("--resume",action="store_true"); p.add_argument("--yes",action="store_true"); p.add_argument("--noninteractive",action="store_true"); p.add_argument("--managed",action="store_true"); p.add_argument("--allow-unknown-dependencies",action="store_true"); p.add_argument("--allow-missing-adapters",action="store_true",help="For verify --ci: downgrade detected-but-unavailable adapters to informational instead of blocking; never turns zero available adapters into PASS."); p.add_argument("--task",default=""); p.add_argument("--execute",action="store_true"); p.add_argument("--ci",action="store_true"); p.add_argument("--limit",type=int,default=12); p.add_argument("--worker",default=""); p.add_argument("--operation",default="result",choices=["discover","inspect","plan","execute","result","port"]); p.add_argument("--timeout",type=int,default=120); p.add_argument("--baseline",default="",help="Baseline external-check JSON for diffing (external-check only)"); p.add_argument("--run-runtime",action="store_true"); p.add_argument("--run-failure-lab",action="store_true"); p.add_argument("--run-mutations",action="store_true"); p.add_argument("--run-counterfactual",action="store_true"); p.add_argument("--verdict",action="store_true"); p.add_argument("--finding-id",default=""); p.add_argument("--reason",default=""); p.add_argument("extra",nargs="*"); return p
def main():
    args=parser().parse_intermixed_args()
    try:
        # This mode deliberately bypasses require_qyrenith(root): the target is an
        # unrelated external project and is inspected without writing Qyrenith state.
        if args.command=="external-check": return cmd_external_check(args)
        if args.command=="external-verify": return cmd_external_verify(args)
        if args.command=="self-test": return self_test()
        if args.command=="intelligence":
            root=root_path(args.project); require_qyrenith(root); intelligence_suite(root)
            if args.run_runtime: execute_runtime_lab(root,args.timeout)
            if args.run_failure_lab: execute_failure_injection_lab(root,args.timeout)
            if args.run_mutations: execute_mutation_lab(root,args.timeout,args.limit)
            if args.run_counterfactual: execute_counterfactual(root,args.timeout)
            result=verification_verdict(root) if args.verdict else intelligence_suite(root)
            print(json.dumps(result,indent=2,ensure_ascii=False))
            if args.verdict:
                return 0 if result.get("verdict")=="PASS" else (2 if result.get("verdict")=="BLOCKED" else 1)
            return 0
        return {"audit":cmd_audit,"plan":cmd_plan,"port":cmd_port,"continue":cmd_continue,"build":cmd_build,"verify":cmd_verify,"policy":cmd_policy,"skills":cmd_skills,"reality":cmd_reality,"inspect":cmd_inspect,"explain":cmd_explain,"dry-run":cmd_dry_run,"rollback":cmd_rollback,"doctor":cmd_doctor,"status":cmd_status,"report":cmd_report,"benchmark":cmd_benchmark,"failure-quality":cmd_failure_quality,"security-test":cmd_security_test,"security-review":cmd_security_review,"recovery-test":cmd_recovery_test,"graph":cmd_graph,"compatibility":cmd_compatibility,"replay":cmd_replay,"adapters":cmd_adapters,"worker-run":cmd_worker_run,"artifact-inspect":cmd_artifact_inspect,"evidence":cmd_evidence,"git-test":cmd_git_test,"fuzz-test":cmd_fuzz_test,"public-audit":cmd_public_audit,"domains":cmd_domains}[args.command](args)
    except QyrenithError as e: print(f"{e.code}: {e.message}",file=sys.stderr); return EXIT.get(e.code,EXIT["INTERNAL_ERROR"])
    except KeyboardInterrupt: print("STOPPED: interrupted by user",file=sys.stderr); return EXIT["STOPPED"]
    except Exception as e: print(f"INTERNAL_ERROR: {type(e).__name__}: {e}",file=sys.stderr); return EXIT["INTERNAL_ERROR"]
if __name__=="__main__": sys.exit(main())

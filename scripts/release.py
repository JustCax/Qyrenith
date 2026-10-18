#!/usr/bin/env python3
"""Build deterministic release archives: qyrenith-<version>.zip / .tar.gz.

Cross-platform equivalent of ``scripts/release.sh``; needs only Python 3.8+
and the standard library. The same file set is packaged with fixed timestamps,
so rebuilding an unchanged tree yields the same archives and checksums.

Usage:
    python scripts/release.py [output-dir]

The output directory defaults to ``dist/`` inside the project root. Any other
location inside the project tree is rejected, so an earlier release can never
become part of the next one.
"""
import gzip
import hashlib
import io
import re
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXED_TS = 315532800  # 1980-01-01 00:00:00 UTC
FIXED_DT = (1980, 1, 1, 0, 0, 0)
EXCLUDE_DIRS = {".git", ".qyrenith", ".backups", "dist", "__pycache__",
                ".pytest_cache", "target", "node_modules", ".gradle", "build",
                "runs"}
EXCLUDE_SUFFIXES = {".pyc", ".tmp", ".bak"}
EXCLUDE_FILES = {"Cargo.lock"}


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(2)


def read_version():
    text = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", text):
        fail("invalid semantic version: " + text)
    return text


def excluded(rel):
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return True
    if rel.suffix in EXCLUDE_SUFFIXES or rel.name in EXCLUDE_FILES:
        return True
    return False


def file_mode(rel):
    if rel.name == "gradlew" or rel.suffix == ".sh":
        return 0o755
    return 0o644


def collect_files():
    result = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if not excluded(rel):
            result.append(rel)
    result.sort(key=lambda r: r.as_posix())
    return result


def collect_dirs(files):
    dirs = set()
    for rel in files:
        parent = rel.parent
        while parent.as_posix() != ".":
            dirs.add(parent)
            parent = parent.parent
    return sorted(dirs, key=lambda r: r.as_posix())


def resolve_output_dir(arg):
    default = ROOT / "dist"
    target = default if arg is None else Path(arg).resolve()
    if target != default.resolve() and (target == ROOT or ROOT in target.parents):
        fail("release output directory must be outside the project tree, "
             "or use the default dist/ directory")
    target.mkdir(parents=True, exist_ok=True)
    return target


def stage(files, top):
    tmp = Path(tempfile.mkdtemp(prefix="qyrenith-release-"))
    base = tmp / top
    for rel in files:
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
    return tmp


def write_zip(path, base, files, dirs, top):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo(top + "/", FIXED_DT)
        info.external_attr = (0o40755 << 16) | 0x10
        zf.writestr(info, b"")
        for rel in dirs:
            info = zipfile.ZipInfo(top + "/" + rel.as_posix() + "/", FIXED_DT)
            info.external_attr = (0o40755 << 16) | 0x10
            zf.writestr(info, b"")
        for rel in files:
            info = zipfile.ZipInfo(top + "/" + rel.as_posix(), FIXED_DT)
            info.external_attr = file_mode(rel) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, (base / rel).read_bytes())


def add_dir(tar, name):
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    info.mtime = FIXED_TS
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.size = 0
    tar.addfile(info)


def write_tar(path, base, files, dirs, top):
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w|", format=tarfile.GNU_FORMAT) as tar:
                add_dir(tar, top)
                for rel in dirs:
                    add_dir(tar, top + "/" + rel.as_posix())
                for rel in files:
                    data = (base / rel).read_bytes()
                    info = tarfile.TarInfo(top + "/" + rel.as_posix())
                    info.mode = file_mode(rel)
                    info.mtime = FIXED_TS
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv):
    version = read_version()
    out = resolve_output_dir(argv[1] if len(argv) > 1 else None)
    zip_name = "qyrenith-" + version + ".zip"
    tar_name = "qyrenith-" + version + ".tar.gz"
    for name in (zip_name, tar_name):
        for suffix in ("", ".sha256"):
            target = out / (name + suffix)
            if target.exists():
                target.unlink()
    top = "qyrenith-" + version
    files = collect_files()
    dirs = collect_dirs(files)
    tmp = stage(files, top)
    try:
        write_zip(out / zip_name, tmp / top, files, dirs, top)
        write_tar(out / tar_name, tmp / top, files, dirs, top)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for name in (zip_name, tar_name):
        digest = sha256_file(out / name)
        checksum = digest + "  " + name + "\n"
        (out / (name + ".sha256")).write_text(checksum, encoding="utf-8")
    print("zip: " + str(out / zip_name))
    print((out / (zip_name + ".sha256")).read_text(encoding="utf-8").strip())
    print("source: " + str(out / tar_name))
    print((out / (tar_name + ".sha256")).read_text(encoding="utf-8").strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

#!/usr/bin/env python3
"""Create deterministic public release archives from PUBLIC_FILES.txt."""
import gzip
import hashlib
import io
import re
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
FIXED_TS = 315532800
FIXED_DT = (1980, 1, 1, 0, 0, 0)


def fail(message):
    print(message, file=sys.stderr)
    raise SystemExit(2)


def read_version():
    text = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", text):
        fail("invalid semantic version: " + text)
    return text


def collect_files():
    manifest = ROOT / "PUBLIC_FILES.txt"
    if not manifest.is_file() or manifest.is_symlink():
        fail("PUBLIC_FILES.txt is missing or is not a regular file")
    result = []
    seen = set()
    for number, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        item = raw.strip()
        if not item or item.startswith("#"):
            continue
        if "\\" in item or "\x00" in item:
            fail("invalid path in PUBLIC_FILES.txt at line " + str(number))
        rel = PurePosixPath(item)
        if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
            fail("unsafe path in PUBLIC_FILES.txt at line " + str(number))
        normalized = rel.as_posix()
        if item != normalized:
            fail("non-canonical path in PUBLIC_FILES.txt at line " + str(number))
        cursor = ROOT
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                fail("manifest path traverses a symlink: " + normalized)
        if normalized in seen:
            fail("duplicate path in PUBLIC_FILES.txt: " + normalized)
        seen.add(normalized)
        source = ROOT.joinpath(*rel.parts)
        try:
            resolved = source.resolve(strict=True)
            resolved.relative_to(ROOT)
        except (OSError, ValueError):
            fail("manifest path is missing or escapes the repository: " + normalized)
        if source.is_symlink() or not source.is_file():
            fail("manifest path is not a regular file: " + normalized)
        result.append(rel)
    if not result:
        fail("PUBLIC_FILES.txt contains no files")
    if PurePosixPath("PUBLIC_FILES.txt") not in result:
        fail("PUBLIC_FILES.txt must include itself in the public archive")
    return sorted(result, key=lambda path: path.as_posix())


def file_mode(rel):
    return 0o755 if rel.name == "gradlew" or rel.suffix == ".sh" else 0o644


def collect_dirs(files):
    dirs = set()
    for rel in files:
        parent = rel.parent
        while parent.as_posix() != ".":
            dirs.add(parent)
            parent = parent.parent
    return sorted(dirs, key=lambda path: path.as_posix())


def resolve_output_dir(arg):
    default = (ROOT / "dist").resolve()
    target = default if arg is None else Path(arg).resolve()
    if target != default and (target == ROOT or ROOT in target.parents):
        fail("release output directory must be outside the project tree, or use the default dist/ directory")
    target.mkdir(parents=True, exist_ok=True)
    return target


def stage(files, top, destination):
    base = destination / top
    for rel in files:
        target = base.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT.joinpath(*rel.parts), target)
    return base


def write_zip(path, base, files, dirs, top):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        info = zipfile.ZipInfo(top + "/", FIXED_DT)
        info.external_attr = (0o40755 << 16) | 0x10
        archive.writestr(info, b"")
        for rel in dirs:
            info = zipfile.ZipInfo(top + "/" + rel.as_posix() + "/", FIXED_DT)
            info.external_attr = (0o40755 << 16) | 0x10
            archive.writestr(info, b"")
        for rel in files:
            info = zipfile.ZipInfo(top + "/" + rel.as_posix(), FIXED_DT)
            info.external_attr = (0o100000 | file_mode(rel)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, base.joinpath(*rel.parts).read_bytes())


def add_dir(archive, name):
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    info.mtime = FIXED_TS
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    info.size = 0
    archive.addfile(info)


def write_tar(path, base, files, dirs, top):
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.GNU_FORMAT) as archive:
                add_dir(archive, top)
                for rel in dirs:
                    add_dir(archive, top + "/" + rel.as_posix())
                for rel in files:
                    data = base.joinpath(*rel.parts).read_bytes()
                    info = tarfile.TarInfo(top + "/" + rel.as_posix())
                    info.mode = file_mode(rel)
                    info.mtime = FIXED_TS
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive_contents(zip_path, tar_path, files, top):
    expected = {path.as_posix() for path in files}
    with zipfile.ZipFile(zip_path) as archive:
        actual = {name[len(top) + 1:] for name in archive.namelist()
                  if name.startswith(top + "/") and not name.endswith("/")}
        if actual != expected:
            fail("ZIP contents do not match PUBLIC_FILES.txt")
    with tarfile.open(tar_path, "r:gz") as archive:
        actual = {member.name[len(top) + 1:] for member in archive.getmembers()
                  if member.isfile() and member.name.startswith(top + "/")}
        if actual != expected:
            fail("TAR contents do not match PUBLIC_FILES.txt")


def main(argv):
    if len(argv) > 2:
        fail("usage: release.py [output-directory]")
    version = read_version()
    files = collect_files()
    dirs = collect_dirs(files)
    out = resolve_output_dir(argv[1] if len(argv) == 2 else None)
    stem = "qyrenith-" + version
    zip_name, tar_name = stem + ".zip", stem + ".tar.gz"

    with tempfile.TemporaryDirectory(prefix="qyrenith-release-", dir=str(out)) as temp:
        work = Path(temp)
        base = stage(files, stem, work)
        zip_path, tar_path = work / zip_name, work / tar_name
        write_zip(zip_path, base, files, dirs, stem)
        write_tar(tar_path, base, files, dirs, stem)
        (work / (zip_name + ".sha256")).write_text(
            sha256_file(zip_path) + "  " + zip_name + "\n", encoding="utf-8")
        (work / (tar_name + ".sha256")).write_text(
            sha256_file(tar_path) + "  " + tar_name + "\n", encoding="utf-8")
        for name in (zip_name, tar_name, zip_name + ".sha256", tar_name + ".sha256"):
            (work / name).replace(out / name)

    print("zip: " + str(out / zip_name))
    print((out / (zip_name + ".sha256")).read_text(encoding="utf-8").strip())
    print("source: " + str(out / tar_name))
    print((out / (tar_name + ".sha256")).read_text(encoding="utf-8").strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

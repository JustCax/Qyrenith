#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cat "$ROOT/VERSION.txt")"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "invalid semantic version: $VERSION" >&2
  exit 2
fi
OUT="${1:-$ROOT/dist}"
if [[ "$OUT" == *.zip || "$OUT" == *.tar.gz ]]; then
  OUT_DIR="$(cd "$(dirname "$OUT")" && pwd)"
else
  OUT_DIR="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")"
fi
mkdir -p "$OUT_DIR"

# Keep release outputs outside the source snapshot. The default `dist/` is the
# only supported in-tree output location and is explicitly excluded below.
# Arbitrary in-tree output directories are rejected because a prior release
# placed there would otherwise become part of the next release input.
RSYNC_OUT_EXCLUDE=()
if [[ "$OUT_DIR" == "$ROOT" || ( "$OUT_DIR" == "$ROOT"/* && "$OUT_DIR" != "$ROOT/dist" ) ]]; then
  echo "release output directory must be outside the project tree, or use the default dist/ directory" >&2
  exit 2
fi
ZIP_NAME="qyrenith-${VERSION}.zip"
TAR_NAME="qyrenith-${VERSION}.tar.gz"
rm -f "$OUT_DIR/$ZIP_NAME" "$OUT_DIR/$ZIP_NAME.sha256" "$OUT_DIR/$TAR_NAME" "$OUT_DIR/$TAR_NAME.sha256"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/qyrenith-${VERSION}"
rsync -a --exclude='.git' --exclude='.qyrenith' --exclude='.backups' --exclude='dist' --exclude='__pycache__' --exclude='*.pyc' --exclude='*.tmp' --exclude='*.bak' --exclude='.pytest_cache' --exclude='target' --exclude='node_modules' --exclude='Cargo.lock' --exclude='.gradle' --exclude='build' --exclude='runs' "$ROOT/" "$TMP/qyrenith-${VERSION}/"
find "$TMP/qyrenith-${VERSION}" -exec touch -h -d '1980-01-01 00:00:00 UTC' {} +
(cd "$TMP" && TZ=UTC zip -X -qr "$OUT_DIR/$ZIP_NAME" "qyrenith-${VERSION}")
tar -I 'gzip -n' --sort=name --mtime='1980-01-01 00:00:00 UTC' --owner=0 --group=0 --numeric-owner -cf "$OUT_DIR/$TAR_NAME" -C "$TMP" "qyrenith-${VERSION}"
(cd "$OUT_DIR" && sha256sum "$ZIP_NAME") > "$OUT_DIR/$ZIP_NAME.sha256"
(cd "$OUT_DIR" && sha256sum "$TAR_NAME") > "$OUT_DIR/$TAR_NAME.sha256"
echo "zip: $OUT_DIR/$ZIP_NAME"
cat "$OUT_DIR/$ZIP_NAME.sha256"
echo "source: $OUT_DIR/$TAR_NAME"
cat "$OUT_DIR/$TAR_NAME.sha256"

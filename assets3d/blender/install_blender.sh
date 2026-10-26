#!/usr/bin/env bash
# Install a pinned, checksum-verified Blender LTS for headless rendering (no GUI, no GPU needed).
#   bash assets3d/blender/install_blender.sh            # installs into $AIZE_TOOLS (default ~/.aize-tools)
#   BLENDER=$AIZE_TOOLS/blender-4.5.9-linux-x64/blender  # then point the pipeline at it
#
# Why 4.5 LTS: stable Python API for the whole project lifetime (supported to mid-2027); the scripts use only
# the public bpy API (Cycles CPU, bmesh, glTF exporter).
set -euo pipefail
VERSION="${BLENDER_VERSION:-4.5.9}"
SERIES="${VERSION%.*}"
TOOLS="${AIZE_TOOLS:-$HOME/.aize-tools}"
# sha256 of blender-4.5.9-linux-x64.tar.xz as published on download.blender.org (verified when this file was written);
# for another version set BLENDER_VERSION and BLENDER_SHA256 (the download is always also checked against the published .sha256 file)
PINNED_SHA256="${BLENDER_SHA256:-dcdc3eca6c9825bb35a8033b689c053f3cb5a9b0cd2a61b2eac2a49436b4ad3d}"
[ "$VERSION" = "4.5.9" ] || PINNED_SHA256="${BLENDER_SHA256:-}"
URL="https://download.blender.org/release/Blender${SERIES}/blender-${VERSION}-linux-x64.tar.xz"
DEST="$TOOLS/blender-${VERSION}-linux-x64"
if [ -x "$DEST/blender" ]; then echo "already installed: $DEST/blender"; exit 0; fi
mkdir -p "$TOOLS/dl"; cd "$TOOLS/dl"
curl -fsSL --retry 3 -o "blender-${VERSION}.sha256" "https://download.blender.org/release/Blender${SERIES}/blender-${VERSION}.sha256"
if [ -t 2 ]; then PROG="--progress-bar"; else PROG="--silent --show-error"; fi     # no progress-bar flood in CI logs
curl -fL --retry 3 $PROG -o "blender-${VERSION}-linux-x64.tar.xz" "$URL"
want="$(grep "blender-${VERSION}-linux-x64.tar.xz" "blender-${VERSION}.sha256" | awk '{print $1}')"
have="$(sha256sum "blender-${VERSION}-linux-x64.tar.xz" | awk '{print $1}')"
[ -n "$want" ] && [ "$want" = "$have" ] || { echo "CHECKSUM MISMATCH (published $want, got $have)" >&2; exit 1; }
if [ -n "$PINNED_SHA256" ] && [ "$PINNED_SHA256" != "$have" ]; then echo "pinned checksum differs from download ($PINNED_SHA256 vs $have)" >&2; exit 1; fi
tar -xJf "blender-${VERSION}-linux-x64.tar.xz" -C "$TOOLS"
"$DEST/blender" --version | head -1
echo "installed: $DEST/blender   (sha256 $have)"

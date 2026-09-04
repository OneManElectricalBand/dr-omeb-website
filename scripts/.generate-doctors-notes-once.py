#!/usr/bin/env python3
"""One-time bootstrap for the native Doctor's Notes review branch."""
from __future__ import annotations

import base64
import gzip
import hashlib
from pathlib import Path

PARTS = [Path(f"scripts/.doctors-notes-payload-{index}.txt") for index in range(1, 6)]
EXPECTED_PAYLOAD_SHA256 = "994ce5736e6db3cf3d1d768120d60c18d87610961555d3781faa65730c2ae6b1"
EXPECTED_SOURCE_SHA256 = "689ac33c3c7991d4f7cac9aac6984a859af2057308e11cd6b20370992e15baf8"

missing = [str(path) for path in PARTS if not path.exists()]
if missing:
    raise SystemExit(f"Missing generator payload parts: {', '.join(missing)}")

payload = "".join(path.read_text(encoding="utf-8") for path in PARTS)
payload_sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
if payload_sha != EXPECTED_PAYLOAD_SHA256:
    raise SystemExit(f"Generator payload checksum mismatch: {payload_sha}")

source = gzip.decompress(base64.b64decode(payload))
source_sha = hashlib.sha256(source).hexdigest()
if source_sha != EXPECTED_SOURCE_SHA256:
    raise SystemExit(f"Generator source checksum mismatch: {source_sha}")

namespace = {"__name__": "__main__", "__file__": "generate_doctors_notes.py"}
exec(compile(source, "generate_doctors_notes.py", "exec"), namespace)

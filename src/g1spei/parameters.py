"""Portable parameter manifests and SHA-256 verification."""

import hashlib
import json
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported parameter manifest schema")
    for entry in manifest["files"]:
        path = (root / entry["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"Missing or unsafe parameter path: {entry['path']}")
        if path.stat().st_size != entry["bytes"]:
            raise ValueError(f"Parameter size mismatch: {path}")
    return manifest


def monthly_paths(root, month):
    manifest = load(root)
    selected = [f for f in manifest["files"] if f.get("month") in (None, month)]
    items = {f["role"]: Path(root) / f["path"] for f in selected}
    if len(items) != len(selected):
        raise ValueError("Duplicate parameter roles for selected month")
    needed = {
        "temperature_coarse_mean",
        "precipitation_coarse_mean",
        "precipitation_coarse_std",
        "temperature_fine_mean",
        "precipitation_fine_mean",
        "precipitation_fine_std",
        "heat_index",
        "gamma_alpha",
        "gamma_beta",
    }
    if set(items) != needed:
        raise ValueError(f"Parameter roles missing or duplicated; need {sorted(needed)}")
    if manifest.get("gamma_offset_mm") != 1000 or manifest.get("spei_clip") != 3.09:
        raise ValueError("This parameter release requires Gamma offset=1000 mm and SPEI clip=3.09")
    return manifest, items


def verify(root):
    manifest = load(root)
    for n, entry in enumerate(manifest["files"], 1):
        if sha256(Path(root) / entry["path"]) != entry["sha256"]:
            raise ValueError(f"Checksum mismatch: {entry['path']}")
        print(f"Verified {n}/{len(manifest['files'])}: {entry['path']}", flush=True)
    return {"verified_files": len(manifest["files"]), "parameter_version": manifest["version"]}

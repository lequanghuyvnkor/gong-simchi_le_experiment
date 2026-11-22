"""Inventory private cloud inputs without importing or executing their contents.

Python 3.10+, standard library only. JSON goes to stdout; exit 2 means missing
required input or an unsafe/unreadable entry. This is not a license check or a
benchmark validation. Do not publish the inventory without reviewing filenames.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path


GROUPS = {
    "benchmark": "beer_rossmann_archive",
    "presentation": "presentation",
    "supplement": "original_supplement",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect(root: Path, required: list[str]) -> dict:
    report = {
        "schema_version": 1,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "inputs_dir": str(root.absolute()),
        "purpose": "Read-only inventory; no source execution, copying or rights clearance",
        "required": required,
        "groups": {},
        "errors": [],
    }
    # Reject a symlink root or symlink ancestor before traversal.
    if any(p.is_symlink() for p in (root, *root.parents)):
        report["errors"].append("inputs-dir or its ancestor is a symlink")
        return report
    if root.exists() and not root.is_dir():
        report["errors"].append("inputs-dir is not a directory")
        return report
    for name, directory in GROUPS.items():
        folder = root / directory
        group = {"path": directory, "present": folder.is_dir(), "files": []}
        report["groups"][name] = group
        if folder.is_symlink():
            report["errors"].append(f"Refusing symlink: {directory}")
            continue
        if not folder.is_dir():
            if name in required:
                report["errors"].append(f"Missing directory: {folder}")
            continue

        def walk(current: Path) -> None:
            for path in sorted(current.iterdir()):
                relative = path.relative_to(root).as_posix()
                if path.is_symlink():
                    report["errors"].append(f"Refusing symlink: {relative}")
                elif path.is_dir():
                    walk(path)
                elif path.is_file():
                    before = path.stat()
                    checksum = sha256(path)
                    after = path.stat()
                    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                        report["errors"].append(f"File changed while reading: {relative}")
                    group["files"].append({
                        "path": relative, "bytes": after.st_size, "sha256": checksum,
                    })
                else:
                    report["errors"].append(f"Refusing non-regular entry: {relative}")

        try:
            walk(folder)
        except OSError as exc:
            report["errors"].append(f"Cannot read {directory}: {exc}")
        if name in required and not group["files"]:
            report["errors"].append(f"No regular files in: {folder}")
        if name == "benchmark" and name in required:
            layout = folder / "embedded_package" if (folder / "embedded_package").is_dir() else folder
            group["layout_root"] = layout.relative_to(root).as_posix()
            for subdirectory in ("work", "outputs"):
                if not (layout / subdirectory).is_dir():
                    report["errors"].append(f"Missing directory: {layout / subdirectory}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs-dir", type=Path, required=True)
    parser.add_argument("--require", choices=GROUPS, action="append",
                        help="Repeat for required groups; default: benchmark")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10 or newer is required")
    try:
        report = inspect(args.inputs_dir.absolute(), sorted(set(args.require or ["benchmark"])))
    except OSError as exc:
        parser.exit(2, f"Cannot inspect inputs: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

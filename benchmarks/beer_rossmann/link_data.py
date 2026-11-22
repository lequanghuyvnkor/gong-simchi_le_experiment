"""Verify and copy user-obtained datasets into a separate run directory."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

EXPECTED = {
    "beer": ("store_item_demand_train.csv", "84cd0e7e8f1d2bddfa0b5f184c64ea8ec9cca0878e35b0aae8c9b719db853a2d"),
    "rossmann": ("rossmann_train.csv", "608e4d8ff855465c1ff4f95874b9a35da40c6bedacd7d1f308fe37dba675a39e"),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--beer", type=Path, required=True)
    p.add_argument("--rossmann", type=Path, required=True)
    p.add_argument("--run-dir", type=Path, required=True)
    a = p.parse_args()
    root = a.run_dir.resolve()
    repo = Path(__file__).resolve().parents[2]
    if (root.is_relative_to(repo) and not root.is_relative_to(repo / "local_checks")) or "inputs" in root.parts:
        p.error("Choose a working directory outside inputs/ and tracked repository paths")
    sources = {}
    for name, (_, expected) in EXPECTED.items():
        source = getattr(a, name).resolve()
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != expected:
            p.error(f"SHA-256 mismatch for {name}: {actual}; expected {expected}")
        sources[name] = source
    out = root / "outputs/datasets"
    out.mkdir(parents=True, exist_ok=True)
    for name, source in sources.items():
        target = out / EXPECTED[name][0]
        if target.resolve() == source:
            p.error("Run data must be separate from original input")
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != EXPECTED[name][1]:
            p.error(f"Refusing to overwrite changed file: {target}")
        if not target.exists():
            shutil.copy2(source, target)
    print(json.dumps({k: str(out / v[0]) for k, v in EXPECTED.items()}, indent=2))


if __name__ == "__main__":
    main()

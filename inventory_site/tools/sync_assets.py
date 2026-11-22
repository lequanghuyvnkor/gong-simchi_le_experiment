"""Prepare the buildless Site from the repository's authoritative sources."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "inventory_site"
CORE_NAMES = ("model.py", "hql.py", "meta_hql.py", "experiment.py", "fql_model.py",
              "fql.py", "fql_experiment.py", "mimic_ql.py")


def main():
    destination = SITE / "dist/assets/python"
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name in CORE_NAMES:
        source = ROOT / "lost_sales_lab" / name
        shutil.copyfile(source, destination / name)
        manifest[name] = {"source": str(source.relative_to(ROOT)),
                          "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    (SITE / "core_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    resources = SITE / "dist/resources"
    resources.mkdir(parents=True, exist_ok=True)
    for source, name in (
        ("reports/experimental_presenter/experimental_presenter_playbook_vi.pdf", "presenter_playbook.pdf"),
        ("reports/experimental_presenter/stress_test_plan_vi.pdf", "stress_test_plan.pdf"),
        ("docs/stress_test_plan.md", "stress_test_plan.md"),
    ):
        shutil.copyfile(ROOT / source, resources / name)
    print("Synced 8 Python cores and 3 reading resources.")


if __name__ == "__main__":
    main()

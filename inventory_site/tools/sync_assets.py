"""Prepare the buildless Site from the repository's authoritative sources."""
import hashlib
import json
import shutil
import html
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

import markdown

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "inventory_site"
CORE_NAMES = ("model.py", "hql.py", "meta_hql.py", "experiment.py", "fql_model.py",
              "fql.py", "fql_experiment.py", "mimic_ql.py")


def render_document(source, target, title):
    text = source.read_text(encoding="utf-8")
    if re.search(r"<(script|iframe|object|embed|form)\b",text,re.I):
        raise ValueError("Unexpected active HTML in authored Markdown")
    def link(match):
        label, uri = match.groups()
        parsed = urlsplit(uri)
        if parsed.scheme or uri.startswith("#"):
            return match.group(0)
        path = (source.parent / parsed.path).resolve().relative_to(ROOT)
        return "["+label+"](https://github.com/lequanghuyvnkor/gong-simchi_le_experiment/blob/main/"+path.as_posix()+("#"+parsed.fragment if parsed.fragment else "")+")"
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",link,text)
    body = markdown.markdown(text,extensions=["tables","fenced_code","toc"])
    body = body.replace('<a href=', '<a target="_blank" rel="noreferrer noopener" href=')
    css = "body{font:16px/1.8 system-ui,sans-serif;color:#203d53;max-width:1000px;padding:25px 32px;margin:auto}h1{font-size:1.9rem;line-height:1.3}h2{margin-top:2.5rem;font-size:1.35rem}h3{font-size:1.1rem;margin-top:2rem}a{color:#0879ad}table{display:block;overflow-x:auto;border-collapse:collapse;max-width:100%;font-size:.9rem}td,th{padding:10px 12px;border:1px solid #d6e3eb;min-width:125px;vertical-align:top}th{background:#eef5f8}blockquote{border-left:3px solid #18a4bc;margin:20px 0;padding:1px 20px;background:#f1f8fa}pre{overflow:auto;background:#edf4f8;padding:16px;border-radius:8px}code{font-family:ui-monospace,monospace;font-size:.9em}li{margin-bottom:8px}@media(max-width:600px){body{padding:17px}h1{font-size:1.6rem}}"
    target.write_text('<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+css+'</style></head><body>'+body+'</body></html>\n',encoding="utf-8")


def write_zip(archive, files, extra):
    with ZipFile(archive,"w",ZIP_DEFLATED,compresslevel=9) as bundle:
        for name, content in sorted({**{n:p.read_bytes() for n,p in files.items()},**extra}.items()):
            info = ZipInfo(name, (2026,11,23,0,0,0))
            info.compress_type=ZIP_DEFLATED
            info.external_attr=0o100644<<16
            bundle.writestr(info,content)


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
        ("reports/experimental_presenter/experimental_presenter_playbook_vi.docx", "presenter_playbook.docx"),
        ("reports/experimental_presenter/stress_test_plan_vi.docx", "stress_test_plan.docx"),
        ("presentation/Gong_Simchi_2024_Academic_60min_v4_repo.pptx", "slides_v4.pptx"),
        ("presentation/Gong_Simchi_2024_Script_Tieng_Viet_60_phut_repo.docx", "script_vi.docx"),
        ("inventory_site/content/presentation.json", "presentation.json"),
        ("experiments/stress_tests/plan.json", "research_stress_plan.json"),
    ):
        shutil.copyfile(ROOT / source, resources / name)
    render_document(ROOT/"reports/experimental_presenter/playbook_vi.md",resources/"presenter_playbook.html","Hướng dẫn thuyết trình experimental")
    render_document(ROOT/"docs/stress_test_plan.md",resources/"stress_test_plan.html","Kế hoạch stress test nghiên cứu")
    files = subprocess.check_output(["git","ls-files","-z","lost_sales_lab"],cwd=ROOT).decode().split("\0")
    sources={n:ROOT/n for n in files if n and Path(n).suffix in (".py",".md",".txt",".toml",".ps1")}
    instructions="ỨNG DỤNG STREAMLIT — Python 3.10+\n\npython -m pip install -r lost_sales_lab/requirements.txt\npython -m streamlit run lost_sales_lab/app.py\n\nStreamlit có HQL, Meta-HQL, FQL; bản học Mimic nằm trên website/lõi, không có lựa chọn Streamlit riêng.\nNguồn: https://github.com/lequanghuyvnkor/gong-simchi_le_experiment\n"
    write_zip(resources/"streamlit_source.zip",sources,{"README_RUN.txt":instructions.encode("utf-8")})
    print("Synced Python cores, reading resources, presentation assets and downloadable Streamlit source.")


if __name__ == "__main__":
    main()

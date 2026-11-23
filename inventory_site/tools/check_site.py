"""Check distributable assets and exercise the four browser-adapter models."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "inventory_site"
DIST = SITE / "dist"
sys.path.insert(0, str(DIST / "assets/python"))
from lab_api import Lab, handle_json


def main():
    for name, item in json.loads((SITE / "core_manifest.json").read_text()).items():
        expected = item["sha256"]
        for source in (ROOT / item["source"], DIST / "assets/python" / name):
            assert hashlib.sha256(source.read_bytes()).hexdigest() == expected, source
    html = (DIST / "index.html").read_text()
    ids=re.findall(r'\bid="([^\"]+)"',html)
    assert len(ids)==len(set(ids)),"Duplicate static element IDs"
    for link in re.findall(r'(?:src|href)="(\./[^"#]+)', html):
        assert (DIST / link).exists(), link
    for name in ("app.js", "engine.worker.js", "hub.js", "stress.js"):
        subprocess.run(["node", "--check", str(DIST / name)], check=True)
    # The portal reader is an exact render of authored documents, with inert HTML.
    for name in ("presenter_playbook.html","stress_test_plan.html"):
        doc=(DIST/"resources"/name).read_text()
        assert 'lang="vi"' in doc and '<h1' in doc
        assert not re.search(r'<(?:script|object|embed)\b',doc,re.I)
    presentation=json.loads((DIST/"resources/presentation.json").read_text())
    assert {o["minutes"] for o in presentation["outlines"]} == {40,60}
    assert len(presentation["research_questions"]) == 3
    for outline in presentation["outlines"]:
        assert outline["segments"][0]["minute_start"] == 0
        assert outline["segments"][-1]["minute_end"] == outline["minutes"]
    def check_refs(value):
        if isinstance(value,dict):
            if "path" in value:
                path=ROOT/value["path"];assert path.is_file(),path
                if "pointer" in value:
                    result=json.loads(path.read_text())
                    for key in value["pointer"].strip('/').split('/'):
                        key=key.replace('~1','/').replace('~0','~')
                        result=result[int(key)] if isinstance(result,list) else result[key]
            for child in value.values():check_refs(child)
        elif isinstance(value,list):
            for child in value:check_refs(child)
    check_refs(presentation)
    for name,source in {
        "presenter_playbook.docx":"reports/experimental_presenter/experimental_presenter_playbook_vi.docx",
        "slides_v4.pptx":"presentation/Gong_Simchi_2024_Academic_60min_v4_repo.pptx",
        "script_vi.docx":"presentation/Gong_Simchi_2024_Script_Tieng_Viet_60_phut_repo.docx",
    }.items():
        assert (DIST/"resources"/name).read_bytes()==(ROOT/source).read_bytes(),name
    movies = json.loads((DIST / "media/videos_manifest.json").read_text())
    assert set(movies) == {"hql", "meta", "fql", "mimic"}
    for kind, metadata in movies.items():
        for name, digest in metadata["source_sha256"].items():
            assert hashlib.sha256((DIST / "assets/python" / name).read_bytes()).hexdigest() == digest, name
        video = DIST / "media" / (kind + ".mp4")
        trace = DIST / "media" / (kind + "_trace.json")
        assert hashlib.sha256(video.read_bytes()).hexdigest() == metadata["sha256"]
        assert hashlib.sha256(trace.read_bytes()).hexdigest() == metadata["trace_sha256"]
        streams = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(video)]))["streams"]
        assert len(streams) == 1 and streams[0]["codec_type"] == "video"
        assert (streams[0]["width"], streams[0]["height"]) == (1280, 720)
        assert abs(float(streams[0]["duration"]) - metadata["seconds"]) < .01
        trace_lab = Lab(kind, {"seed":metadata["seed"],"cycles":(metadata["days"]+2)//3})
        for expected in json.loads(trace.read_text()):
            opening = trace_lab.snapshot()["manual_opening"]
            actual = trace_lab.step(max(opening, 10) if kind in ("hql", "meta") else [2, 2])
            assert actual == {k:v for k,v in expected.items() if k != "video_virtual"}, (kind, actual["day"])
    totals = {}
    for kind in movies:
        lab = Lab(kind)
        while not lab.snapshot()["finished"]:
            before = lab.snapshot()["manual_opening"]
            snapshot = lab.step(max(before, 10) if kind in ("hql", "meta") else [2, 2])
            assert snapshot["day"] == len(snapshot["history"])
            assert snapshot["human"]["demand"] == snapshot["algorithm"]["demand"]
            json.dumps(snapshot, allow_nan=False)
        current = snapshot["day"]
        for phase in range(1, 7 if kind == "mimic" else 4):
            q = lab.q_detail(phase)
            if q.get("available_actions"):
                q = lab.q_detail(phase, q["available_actions"][0])
            if "new_q" in q:
                expected = (1-q["alpha"]) * q["old_q"] + q["alpha"] * (q["reward"]+q["bootstrap"])
                assert abs(q["new_q"]-expected) < 1e-10
        assert lab.snapshot()["day"] == current  # replay cannot learn
        totals[kind] = {"days":current,"human_cost":snapshot["sum_human"],"algorithm_cost":snapshot["sum_algorithm"]}
        try:
            lab.step(10 if kind in ("hql", "meta") else [0, 0])
        except ValueError:
            pass
        else:
            raise AssertionError("Completed run accepted another day")
    for invalid in (True, 4.5, "42", -1):
        try:
            Lab("hql", {"seed":invalid})
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid seed accepted")
    # The learner-only view and CSV must not reveal true demand/lost sales.
    handle_json(json.dumps({"op":"reset","kind":"hql","options":{"researcher":False}}))
    hidden = json.loads(handle_json('{"op":"step","action":10}'))
    assert hidden["algorithm"]["demand"] is None and hidden["algorithm"]["lost"] is None
    exported = json.loads(handle_json('{"op":"export"}'))["csv"]
    header = exported.splitlines()[0].lower()
    assert "nhu cầu" not in header and "mất bán" not in header
    handle_json('{"op":"select","kind":"fql"}')
    resumed = json.loads(handle_json('{"op":"select","kind":"hql"}'))
    assert resumed["day"] == 1 and not resumed["researcher"]
    print(json.dumps({"status":"passed","scope":"native Python adapter + assets; browser QA recorded separately", "models":totals},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()

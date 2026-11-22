"""Render original, silent system diagrams from real Python simulation traces.

Python 3.10+, numpy, matplotlib and an FFmpeg installation are required.
No paper figures, screenshots, narration or subtitle tracks are used.
"""
import argparse
import hashlib
import json
import sys
import platform
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "inventory_site/dist/assets/python"))
from lab_api import Lab

BG = "#071b36"
FG = "#edf5fa"
MUTED = "#a3b7cd"
CYAN = "#4ed6d0"
GOLD = "#f4bb67"
TITLES = {"hql": "HQL", "meta": "Meta-HQL", "fql": "FQL", "mimic": "Mimic-QL"}


def pair(value):
    return " / ".join(str(v) for v in value) if isinstance(value, (list, tuple)) else str(value)


def collect(kind, days):
    lab = Lab(kind, {"seed": 42, "cycles": (days + 2) // 3})
    frames = []
    for day in range(days):
        opening = lab.snapshot()["manual_opening"]
        lab.step(max(opening, 10) if kind in ("hql", "meta") else [2, 2])
        s = lab.snapshot()
        if kind == "mimic":
            match = lab.run.choices[-1]
            v = lab.run.virtual[-1]
            s["video_virtual"] = {"order": list(match.virtual_order), "net": list(v.closing.net),
                                  "pipeline": list(v.closing.pipeline)}
        frames.append(s)
    return frames


def node(ax, x, y, w, h, title, lines, active=False, color=CYAN):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.015,rounding_size=.018",
                               facecolor="#12344e" if active else "#0c263f",
                               edgecolor=color if active else "#31506b", linewidth=1.7))
    ax.text(x + .018, y + h - .045, title, color=color, fontsize=12, weight="bold", va="top")
    for i, line in enumerate(lines):
        ax.text(x + .018, y + h - .095 - i * .046, line, color=FG, fontsize=11, va="top")


def edge(ax, points, t, color=CYAN, dashed=False):
    for a, b in zip(points, points[1:]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, alpha=.4, lw=1.8,
                linestyle="--" if dashed else "-")
    a, b = points[-2:]
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, color=color, lw=1.3))
    lengths = [((b[0]-a[0])**2 + (b[1]-a[1])**2)**.5 for a, b in zip(points, points[1:])]
    remaining = (t % 1) * sum(lengths)
    for a, b, length in zip(points, points[1:], lengths):
        if remaining <= length:
            ratio = remaining / length if length else 0
            ax.add_patch(Circle((a[0] + (b[0]-a[0])*ratio, a[1] + (b[1]-a[1])*ratio),
                                .007, facecolor=color, edgecolor="none"))
            break
        remaining -= length


def draw(ax, kind, s, u):
    ax.clear(); ax.set(xlim=(0, 1), ylim=(0, 1)); ax.axis("off")
    a = s["algorithm"]; day = s["day"]
    ax.text(.035, .95, "INVENTORY LAB", color=CYAN, fontsize=11, weight="bold")
    title = TITLES[kind] + ("  /  teaching adaptation" if kind == "mimic" else "")
    ax.text(.035, .88, title, color=FG, fontsize=26, weight="bold")
    ax.text(.965, .94, "DAY %02d  /  H = 3" % day, color=FG, ha="right", fontsize=12)
    ax.text(.965, .89, "SEED 42  ·  MODEL UNITS", color=MUTED, ha="right", fontsize=10)
    full = kind in ("fql", "mimic")
    node(ax, .04, .56, .22, .20, "SUPPLIER", ["Order   " + pair(a["ordered"]),
         "Lead time   " + ("1 day" if full else "0 days")], u < .33)
    stock_lines = ["Stock   " + pair(a["remaining"])]
    stock_lines += ["Pipeline   " + pair(a["pipeline"])] if full else ["Sales   " + pair(a["sales"])]
    node(ax, .39, .56, .22, .20, "PHYSICAL STORE", stock_lines, .22 <= u < .65)
    node(ax, .74, .56, .22, .20, "CUSTOMERS", ["Demand   " + pair(a["demand"]),
         ("Backlog   " + pair(a["backlog"])) if full else ("Lost sales   " + str(a["lost"]))], .45 <= u < .8)
    edge(ax, [(.26,.66),(.39,.66)], u*1.8)
    edge(ax, [(.61,.66),(.74,.66)], u*1.8-.4)
    if kind == "meta":
        for i, arm in enumerate(s["arms"]):
            node(ax, .31 + i*.225, .20, .195, .205, "HQL %d" % arm["arm"],
                 ["Episodes   %d" % arm["episodes"], "Entry cap   %d" % arm["entry_cap"]],
                 arm["selected"], GOLD)
        ax.text(.04, .35, "META\nSCHEDULER", color=GOLD, weight="bold", fontsize=12, va="top")
        ax.text(.04, .23, s["status"].upper(), color=MUTED, fontsize=10)
        edge(ax, [(.85,.54),(.85,.46),(.63,.46),(.63,.42)], u*1.8, GOLD, True)
        edge(ax, [(.3,.3),(.15,.3),(.15,.54)], u*1.8-.5, GOLD, True)
        reset = "PHYSICAL INVENTORY  /  CONTINUOUS"
    elif kind == "mimic":
        v = s["video_virtual"]
        node(ax, .39, .17, .22, .24, "VIRTUAL FQL  /  J = 6",
             ["Order   " + pair(v["order"]), "Next net   " + pair(s["virtual"]["net"]),
              "Used phase   %d / 6" % ((day-1)%6+1)], u >= .65, GOLD)
        node(ax, .04, .17, .22, .24, "IP MATCHER",
             ["Request   " + pair(s["requested"]), "Actuator cap   2 / 2",
              "Limited   " + pair([int(v) for v in s["limited"]])], u < .33, GOLD)
        node(ax, .74, .17, .22, .24, "VIRTUAL CLOCK",
             ["H = 3   /   J = 6", "Reset   " + ("YES" if s["virtual_reset"] else "NO"),
              "Physical   continuous"], s["virtual_reset"], GOLD)
        edge(ax, [(.85,.54),(.85,.46),(.5,.46),(.5,.43)], u*1.8, GOLD, True)
        edge(ax, [(.38,.29),(.28,.29)], u*1.8-.5, GOLD, True)
        edge(ax, [(.15,.43),(.15,.54)], u*1.8-.9, GOLD, True)
        reset = "ONLY VIRTUAL STATE RESETS" if s["virtual_reset"] else "SHARED DEMAND  /  BOTH CLOCKS ADVANCE"
    else:
        node(ax, .36, .19, .28, .22, "FQL LEARNER" if full else "HQL LEARNER",
             ["Feedback   demand" if full else "Feedback   own sales",
              "Backward sweep   3 / 2 / 1" if full else "Simulate lower inventory",
              "Alpha   " + ("%.3f" % s["alpha"] if s["alpha"] else "pending")], u >= .65, GOLD)
        edge(ax, [(.85,.54),(.85,.3),(.66,.3)], u*1.8, GOLD, True)
        edge(ax, [(.34,.3),(.15,.3),(.15,.54)], u*1.8-.6, GOLD, True)
        reset = "EPISODE RESET" if day % 3 == 0 else "EPISODE PHASE %d / 3" % ((day-1)%3+1)
        if not full:
            ax.text(.76,.44,"SALES ONLY",color=GOLD,fontsize=10)
    ax.text(.035,.075,reset,color=CYAN,fontsize=11,weight="bold")
    update_label = "STAGE SWEEPS" if full else "Q UPDATES"
    ax.text(.965,.075,update_label+"   %d" % s["q_updates"],color=MUTED,fontsize=10,ha="right")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=24)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--models", nargs="+", default=list(TITLES), choices=list(TITLES))
    args = parser.parse_args()
    if not 1 <= args.days <= 60 or args.fps < 2:
        parser.error("days: 1–60; fps >= 2")
    out = ROOT / "inventory_site/dist/media"; out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for kind in args.models:
        snapshots = collect(kind, args.days)
        trace_path = out / (kind + "_trace.json")
        trace_path.write_text(json.dumps(snapshots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)
        fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        writer = FFMpegWriter(fps=args.fps, codec="libx264", bitrate=-1,
                             extra_args=["-crf","23","-pix_fmt","yuv420p","-movflags","+faststart"],
                             metadata={"title": TITLES[kind]+" system diagram", "artist":"Inventory Lab"})
        movie = out / (kind + ".mp4")
        with writer.saving(fig, str(movie), 100):
            for s in snapshots:
                for frame in range(args.fps):
                    draw(ax, kind, s, frame / args.fps)
                    writer.grab_frame(facecolor=BG)
        draw(ax, kind, snapshots[min(6,len(snapshots)-1)], .72)
        fig.savefig(out / (kind + ".png"), facecolor=BG, dpi=100)
        plt.close(fig)
        manifest[kind] = {"seed":42,"days":args.days,"fps":args.fps,"seconds":args.days,
                          "resolution":[1280,720],"audio":False,"subtitles":False,
                          "sha256":hashlib.sha256(movie.read_bytes()).hexdigest(),
                          "trace_sha256":hashlib.sha256(trace_path.read_bytes()).hexdigest(),
                          "scope":"declared teaching adaptation" if kind=="mimic" else "finite teaching model",
                          "python":platform.python_version(),"numpy":np.__version__,"matplotlib":matplotlib.__version__,
                          "source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in sorted((ROOT/"inventory_site/dist/assets/python").glob("*.py"))}}
        print(kind + ": " + str(movie.stat().st_size) + " bytes", flush=True)
    previous_path = out / "videos_manifest.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    previous.update(manifest)
    previous_path.write_text(json.dumps(previous, indent=2) + "\n")


if __name__ == "__main__":
    main()

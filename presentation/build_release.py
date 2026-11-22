"""Build the repository distribution from the private v4 originals.

Replaces third-party screenshots with project-authored text. It does not grant
rights to redistribute the original report, archive or presentation screenshots.
"""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.util import Pt

HERE = Path(__file__).resolve().parent
PPTX_NAME = "Gong_Simchi_2024_Academic_60min_v4_repo.pptx"
DOCX_NAME = "Gong_Simchi_2024_Script_Tieng_Viet_60_phut_repo.docx"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slides", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((HERE / "source_manifest.json").read_text())
    for suffix, path in [(".pptx", args.slides), (".docx", args.script)]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[suffix]["sha256"]:
            parser.error(f"Original {suffix} differs from the recorded v4 snapshot")
    output = args.output_dir.resolve()
    if output in (args.slides.parent.resolve(), args.script.parent.resolve()) or "inputs" in output.parts:
        parser.error("Keep generated distribution separate from originals")
    output.mkdir(parents=True, exist_ok=True)
    replacements = json.loads((HERE / "replacements.json").read_text())
    prs = Presentation(args.slides)
    removed = []
    for number, slide in enumerate(prs.slides, 1):
        for shape in list(slide.shapes):
            if shape.shape_type != 13:
                continue
            key = f"{number}:{shape.shape_id}"
            text = replacements[key]
            record = {"slide": number, "shape_id": shape.shape_id,
                      "source_image_sha256": hashlib.sha256(shape.image.blob).hexdigest()}
            box = slide.shapes.add_textbox(shape.left, shape.top, shape.width, shape.height)
            frame = box.text_frame
            frame.word_wrap = True
            frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            frame.margin_left = frame.margin_right = Pt(2)
            frame.margin_top = frame.margin_bottom = Pt(1)
            frame.text = text
            for paragraph in frame.paragraphs:
                paragraph.font.name = "Aptos"
                paragraph.font.size = Pt(12 if shape.height < 600000 else 16)
                paragraph.font.color.rgb = RGBColor.from_string("143D52")
            relationship = shape._element.blipFill.blip.rEmbed
            shape._element.getparent().remove(shape._element)
            slide.part.drop_rel(relationship)
            removed.append(record)
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.text = run.text.replace(
                        "Algorithm excerpts are screenshots from the supplied published PDF. Their notation, confidence terms and stopping-time update are preserved.",
                        "Project-authored summaries replace original screenshots. Read the cited Algorithms 1-2 for full notation, confidence rules and assumptions.")
                    run.text = run.text.replace("Appendix B: Original Algorithms", "Appendix B: Algorithm Summaries")
                    run.text = run.text.replace("Rates shown from the published abstract, suppressing other factors.", "Full model-specific statements are in the cited paper.")
                    if number == 2:
                        run.text = run.text.replace("Explain finite-horizon behavior", "Check benchmark and implementation fit")
                        run.text = run.text.replace("Assess incremental practical value", "Study confidence-bound sensitivity")
                        run.text = run.text.replace("Learning curves, cyclicity, action sets and handoff", "Matched dynamics, information, budgets and oracle")
                        run.text = run.text.replace("Adapted comparison, strong baseline and economic extensions", "Validation/test sweeps; candidate and arm diagnostics")
                        run.text = run.text.replace("RQ2 — Mechanism: how do learning horizon, cyclicity, running sets and handoff rules affect finite-horizon performance?", "RQ2 — Fit: are benchmarks, information sets and implementations matched to the question being tested?")
                        run.text = run.text.replace("RQ3 — Practical value: what remains after comparison with a strong seasonal baseline and incremental deployment cost?", "RQ3 — Sensitivity: how do confidence-bound coefficients affect cost, elimination and stability? This follow-up is proposed work.")
        if number == 2:
            table_edits = {
                "Explain finite-horizon behavior": "Check benchmark and implementation fit",
                "Assess incremental practical value": "Study confidence-bound sensitivity",
                "Learning curves, cyclicity, action sets and handoff": "Matched dynamics, information, budgets and oracle",
                "Adapted comparison, strong baseline and economic extensions": "Validation/test sweeps; candidate and arm diagnostics",
            }
            for shape in slide.shapes:
                if shape.has_table:
                    for row in shape.table.rows:
                        for cell in row.cells:
                            for paragraph in cell.text_frame.paragraphs:
                                for run in paragraph.runs:
                                    for before, after in table_edits.items():
                                        run.text = run.text.replace(before, after)
        if number == 38:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        for run in paragraph.runs:
                            run.text = run.text.replace(".work/replication_audit", "results/replication_audit/")
                            run.text = run.text.replace("outputs/gong_simchi_5_experiments/quick", "results/five_experiments/")
                            run.text = run.text.replace("luu_tru/bao_cao_beer_rossmann_srdqn_meta_hql_2026-11-16/outputs", "results/beer_rossmann/ and results/cfo/")
                            run.text = run.text.replace("Visual reference: Blue Yonder, The Results Are In: Technology Continues to Drive Enormous Value for Logistics Teams (2023).", "Repository distribution: original paper screenshots replaced by project-authored summaries. Numerical sources: presentation/evidence_map.md.")
    assert len(removed) == len(replacements) == 22
    pptx_path = output / PPTX_NAME
    prs.save(pptx_path)
    # Removed shapes must not leave copyrighted image blobs in the ZIP package.
    with ZipFile(pptx_path) as archive:
        assert not [name for name in archive.namelist() if name.startswith("ppt/media/")]
    doc = Document(args.script)
    for paragraph in doc.paragraphs:
        text = paragraph.text
        if text.startswith("Bước thứ hai là giải thích hành vi"):
            paragraph.text = "Câu hỏi thứ hai là benchmark và cài đặt có phù hợp hay không. Cần đối chiếu động lực tồn kho, thông tin được phép dùng, trạng thái đầu cuối, ngân sách học và định nghĩa oracle. Các đường học và cơ chế chuyển nhánh giúp kiểm tra lựa chọn triển khai; chúng chưa tự xác nhận một cận tối ưu."
        elif text.startswith("Bước thứ ba là đánh giá giá trị tăng thêm"):
            paragraph.text = "Câu hỏi thứ ba của hướng D là độ nhạy với hệ số confidence bound. Ta cần thử riêng cận hành động và cận bandit, chọn bằng validation, khóa rồi đánh giá test với seed ghép cặp. Sweep đầy đủ này là công việc đề xuất, chưa phải kết quả đã chạy; phần CFO phía sau vẫn chỉ là ví dụ giả định."
        else:
            for run in paragraph.runs:
                run.text = run.text.replace("ảnh công thức", "khối diễn giải công thức").replace("ảnh thuật toán", "khối tóm tắt thuật toán")
    doc.add_heading("Ghi chú bản phân phối repository", level=1)
    doc.add_paragraph("Bản v4 trong repository thay ảnh chụp từ bài báo bằng phần diễn giải tự soạn có dẫn nguồn. Nguyên bản PPTX/DOCX được giữ riêng trong inputs/. Script có lời thoại cho 31 slide chính; 7 slide cuối là phụ lục hỏi đáp. Lịch 60 phút là mục tiêu luyện tập, chưa phải thời gian đã đo.")
    doc.add_paragraph("Nguồn số liệu theo từng slide và phép tính: https://github.com/lequanghuyvnkor/gong-simchi_le_experiment/blob/main/presentation/evidence_map.md . Kết quả mô phỏng và audit có phạm vi khác nhau; số VND là giả định mẫu. Ba câu hỏi hướng D: mức tái lập, độ phù hợp benchmark/cài đặt, độ nhạy confidence bound.")
    docx_path = output / DOCX_NAME
    doc.save(docx_path)
    result = {"source": manifest, "removed_images": removed,
              "reason": "Third-party screenshot redistribution rights not established",
              "outputs": {path.name: {"bytes": path.stat().st_size,
                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in [pptx_path, docx_path]}}
    (output / "release_manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"slides": len(prs.slides), "removed_source_images": len(removed)}, indent=2))


if __name__ == "__main__":
    main()

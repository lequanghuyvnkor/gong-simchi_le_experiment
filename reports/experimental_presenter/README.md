# Hướng dẫn trình bày experimental và kế hoạch stress test

[Playbook tiếng Việt](playbook_vi.md) là bản chi tiết dành cho người phụ trách thực nghiệm: thông điệp chính, lộ trình khoảng 60 phút và phương án 40 phút, phân tầng bằng chứng, cách đọc kết quả, demo/dự phòng và câu hỏi phản biện. Tài liệu bám bộ slide v4 trong [presentation/](../../presentation/README.md); lịch nói là đề xuất luyện tập, chưa phải thời lượng đã đo.

- [DOCX có thể sửa](experimental_presenter_playbook_vi.docx) · [PDF để đọc/in](experimental_presenter_playbook_vi.pdf).
- [Kế hoạch stress test](../../docs/stress_test_plan.md) · [DOCX](stress_test_plan_vi.docx) · [PDF](stress_test_plan_vi.pdf).
- [Thiết kế máy đọc được](../../experiments/stress_tests/plan.json): 32 test ID dự kiến, có mức ưu tiên, seed/split, điều kiện dừng và tiêu chí chấp nhận. Đây chưa phải runner và chưa thực thi ma trận.
- [Nguồn các số liệu chính](source_refs.json) và [hồ sơ kiểm tra tài liệu](validation.json).

Các kết quả lưu trữ được dẫn về trạng thái cơ sở `5a91349`; thay đổi website về sau phải giữ phiên bản riêng. Mimic-QL trên website được mô tả là **Mimic-QL-inspired teaching adaptation**: hệ thực giữ tồn/nợ/pipeline, hệ FQL ảo reset, lệnh có hạn mức và diagnostics công khai. Nguồn primary là luận án MIT năm 2023, sớm hơn bài báo cuối. Kiểm tra bản dạy không chứng nhận replication công bố hay định lý. VND và chi phí hệ thống trong ví dụ CFO đều là giả định mẫu.

## Dựng lại tài liệu từ clone sạch

Python **3.10+** là bắt buộc; cài R không thay thế môi trường Python. Các lệnh dưới đây chạy từ thư mục gốc repo:

```bash
python --version
python -m venv .venv-presenter
source .venv-presenter/bin/activate
python -m pip install -r reports/experimental_presenter/requirements.txt
python reports/experimental_presenter/check_documents.py
python reports/experimental_presenter/build_documents.py --output-dir local_checks/presenter_docs
```

Trên Windows, kích hoạt bằng `.venv-presenter\Scripts\activate`. Không cần dữ liệu thô hoặc gói replication riêng để dựng hai DOCX; nguồn là Markdown và các kết quả nhỏ đã có trong repo. Bộ kiểm tra xác nhận liên kết cục bộ, giá trị nguồn, tính nhất quán cơ bản của kế hoạch; nó không chạy lại thí nghiệm.

Để xuất PDF, cài LibreOffice có hỗ trợ tiếng Việt rồi chạy:

```bash
soffice --headless --convert-to pdf --outdir local_checks/presenter_docs local_checks/presenter_docs/experimental_presenter_playbook_vi.docx local_checks/presenter_docs/stress_test_plan_vi.docx
```

Tên executable có thể khác theo hệ điều hành. Bản PDF phân phối được xuất bằng LibreOffice; phân trang có thể đổi theo phiên bản/font. Xem `validation.json` để biết đúng môi trường và phạm vi kiểm tra đã chạy. Không đưa output kiểm tra cục bộ, cache hoặc tài liệu gốc bên thứ ba vào Git.

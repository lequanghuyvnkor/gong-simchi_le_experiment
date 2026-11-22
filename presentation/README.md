# Đợt 5 — Slide v4, script tiếng Việt và hướng D

Đã nhận PPTX v4 và DOCX chủ dự án cung cấp. Bản gốc nằm nguyên trạng tại
`/workspace/inputs/presentation/`; checksum trong `source_manifest.json`.
Không có bản slide cũ được Git theo dõi để loại bỏ. Repo chỉ có một phiên bản
slide phân phối:

- `Gong_Simchi_2024_Academic_60min_v4_repo.pptx`: 38 slide, giữ biểu đồ/bảng của dự án.
- `Gong_Simchi_2024_Script_Tieng_Viet_60_phut_repo.docx`: lời thoại 31 slide chính,
  phụ lục nguồn và ghi chú cho bản phân phối; 7 slide phụ lục dùng khi hỏi đáp.
- [Định hướng D](../docs/research_direction_d.md): *Revisiting Meta-HQL:
  A Computational Replication and Sensitivity Study*, ba câu hỏi về tái lập,
  độ phù hợp benchmark/cài đặt và độ nhạy confidence bound.
- [Bảng dẫn nguồn](evidence_map.md): đủ 38 slide, liên kết kết quả/cấu hình,
  công thức suy ra, trang bài báo, ví dụ và thiết kế đề xuất.

## Quyền phân phối và khác biệt với bản gốc

PPTX gốc chứa 22 ảnh chụp công thức/thuật toán/bảng của bài báo. Chưa xác định
quyền phân phối, nên **không đưa nguyên bản PPTX hoặc các ảnh đó lên Git**.
Bản repo thay chúng bằng diễn giải/công thức tự soạn có dẫn nguồn; không giữ
blob ảnh nguồn trong gói PPTX. Biểu đồ native và bảng kết quả dự án được giữ.
`release_manifest.json` ghi từng ảnh bị thay, SHA-256 nguồn và tệp xuất.

Slide 2 và lời thoại tương ứng được chỉnh theo ba câu hỏi hướng D; appendix
nguồn trỏ đường dẫn repo hiện tại. Kịch bản có ghi chú về bản thay ảnh. Các kết
quả audit không được diễn giải thành kết luận về tính đúng của định lý. Sweep
confidence bound trên slide 36 là **đề xuất**, chưa phải kết quả thực nghiệm.
Tất cả số VND trên slide 22 là **giả định mẫu**, không phải tài chính doanh nghiệp.
Lịch 60 phút là mục tiêu luyện tập, chưa phải thời lượng được đo.

## Kiểm tra từ clone sạch

Python **3.10+**; NumPy, pandas, python-pptx, python-docx:

```bash
git clone https://github.com/lequanghuyvnkor/gong-simchi_le_experiment.git
cd gong-simchi_le_experiment
python --version
python -m pip install -r presentation/requirements.txt
python tools/check_research_brief.py
python presentation/check_evidence.py
```

Công cụ so toàn bộ **204 giá trị của 15 biểu đồ** với CSV/JSON trong repo;
kiểm tra hash artifact, 38 slide, 31 mục script và không còn ảnh nguồn.
Dung sai 0.00000051 do chart lưu sáu chữ số thập phân. Bảng/đoạn diễn giải
được dẫn nguồn từng slide trong `evidence_map.md`. Các cài đặt chỉ có trong
notebook INFORMS được dẫn tới nguồn đó, chưa được chạy lại trong phiên này.
Không coi việc khớp chart là xác minh mọi số của bài báo hay mọi định lý.

Đã xuất thử bằng LibreOffice, kiểm tra bố cục toàn bộ 38 slide và script 20
trang, không có trang trống. Đây là render trong môi trường cloud; font hoặc
bố cục có thể khác nhẹ ở PowerPoint. Chi tiết tại `cloud_validation.json`.

## Tạo lại bản phân phối từ nguyên bản riêng

Có thể tạo lại nếu có đúng hai tệp gốc với SHA-256 đã ghi:

```bash
python presentation/build_release.py --slides /path/to/Gong_Simchi_2024_Blue_Yonder_Academic_60min_v4.pptx --script /path/to/Gong_Simchi_2024_Script_Tieng_Viet_60_phut.docx --output-dir /tmp/gong-presentation
python presentation/check_evidence.py --directory /tmp/gong-presentation
```

Cần tệp gốc riêng cho bước dựng lại; clone sạch đã có sẵn bản phân phối để
đọc và kiểm tra. Việc công bố nguyên bản có ảnh bên thứ ba vẫn chờ bằng chứng
quyền phân phối. PDF báo cáo có ZIP dữ liệu nhúng được giữ ngoài Git.

# Đầu vào đã nhận trong cloud

Đã nhận bốn tệp chủ dự án gửi: PDF báo cáo, README nguồn, PPTX v4 và DOCX script.
Bản sao nguyên trạng nằm ngoài Git:

```text
/workspace/inputs/
  beer_rossmann_archive/
    README.md
    bao_cao_tong_hop_du_lieu_va_thuat_toan.pdf
    ma_du_lieu_va_ket_qua.zip           # trích từ PDF, giữ tên nhúng thực tế
    nguon_cong_thuc_OMML.docx           # trích từ PDF
    embedded_package/
      README.txt
      work/
      outputs/
  presentation/
    Gong_Simchi_2024_Blue_Yonder_Academic_60min_v4.pptx
    Gong_Simchi_2024_Script_Tieng_Viet_60_phut.docx
  received_manifest.json
```

Bốn tệp tải lên được so SHA-256 với bản sao `inputs/`; không chỉnh sửa chúng.
PDF có 41 trang và hai tệp nhúng; ZIP có 130 mục. Tên ZIP nhúng khác tên ZIP
rời được nêu trong README. Đã kiểm tra nội dung nhúng thực tế thay vì coi hai
tên là cùng một tệp. Checksum PDF/ZIP nằm tại
[provenance benchmark](../benchmarks/beer_rossmann/provenance.json);
checksum PPTX/DOCX gốc và bản phân phối nằm tại
[release manifest](../presentation/release_manifest.json).

Python 3.10+, thư viện chuẩn:

```bash
python tools/inspect_inputs.py --inputs-dir /workspace/inputs --require benchmark --require presentation
```

Đã giải nén sang `embedded_package/` mà không ghi đè tệp khác. Các chương trình
chạy lại dùng thư mục riêng, không ghi vào `inputs/`. Lệnh lấy lại ZIP từ PDF,
nối dữ liệu theo SHA-256 và giới hạn quyền phân phối ở
[README benchmark](../benchmarks/beer_rossmann/README.md).

Repo chỉ phân phối mã của dự án, metric chính sách, cấu hình, bảng tổng hợp,
báo cáo CFO bằng Markdown và slide/script bản repo. Không phân phối PDF/ZIP
chứa dữ liệu nhúng, CSV dữ liệu nguồn, đường cầu thực nghiệm hoặc ảnh chụp
của bài báo khi quyền chưa rõ. V4 gốc giữ riêng; bản công khai thay ảnh nguồn
bằng nội dung diễn giải tự soạn, có [bảng dẫn nguồn](../presentation/evidence_map.md).

Gói INFORMS chính thức **chưa được cung cấp trong cloud**. Audit hiện dùng
snapshot kết quả có sẵn; không gán nhãn là vừa tái chạy notebook gốc. Nếu cần
chạy lại, tải từ [Supplemental Material](https://pubsonline.informs.org/doi/suppl/10.1287/mnsc.2023.4947)
và theo [README audit](../replication_audit/README.md). Dữ liệu Rossmann trong
ZIP benchmark là snapshot khác với `rossman.csv` của gói INFORMS, có checksum
và cách chuẩn bị riêng; không thay lẫn hai tệp.

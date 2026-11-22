# Đợt 5 — Slide v4 và script tiếng Việt (chưa hoàn tất)

Chưa tìm thấy `inputs/presentation/` trong cloud ngày 2026-11-23. Chưa nhập được
slide v4 hay script tiếng Việt; chưa đối chiếu nội dung, con số và quyền sử
dụng hình/bảng trong các tệp đó. Không có slide cũ dạng PPT/PPTX/PDF được Git
theo dõi ở snapshot nền `c6ab1d8`, nên chưa có tệp slide trùng nào để loại bỏ.

Chủ dự án đã xác nhận PPTX v4 và DOCX script còn trên Windows. Tên tệp cụ thể,
đường dẫn nguồn và đích cloud ở [hướng dẫn chuyển đầu vào](../docs/input_handoff.md).

Phần độc lập đã có: [bản tổng hợp định hướng D](../docs/research_direction_d.md),
“Revisiting Meta-HQL: A Computational Replication and Sensitivity Study”, gồm
mô hình, ba câu hỏi nghiên cứu, bảng dẫn nguồn audit và công việc còn phải làm.
Các số được đối chiếu snapshot trong repo, không gắn nhãn là lần tái chạy mới.

## Kiểm tra từ clone sạch

Python **3.10+**, chỉ thư viện chuẩn; không cần R hoặc cài dependency để đối chiếu
tài liệu hiện có:

```bash
git clone https://github.com/lequanghuyvnkor/gong-simchi_le_experiment.git
cd gong-simchi_le_experiment
python --version
python tools/check_research_brief.py
python tools/inspect_inputs.py --inputs-dir /workspace/inputs --require presentation
```

Thay đường dẫn đầu vào bằng nơi lưu thực tế. Lệnh đối chiếu brief trả 0 khi
bảng khớp snapshot. Lệnh kiểm kê trả 2 khi thiếu slide/script; không coi đây
là xác minh slide thành công. `check_research_brief.py --print-table` chỉ in
bảng hiện tại từ JSON để hỗ trợ cập nhật có chủ đích, không tự sửa tài liệu.

Ngày 2026-11-23: đã chạy phần đối chiếu trên clone sạch áp diff, Python 3.12.14;
bảng audit và phép tính trong snapshot khớp. Thử sửa một số trong bản brief tạm
thì công cụ báo lỗi; khôi phục xong kiểm tra lại đạt. Các liên kết nội bộ trong
tài liệu mới tồn tại. Không chạy lại thí nghiệm hoặc gói replication gốc.

## Đầu vào và việc còn thiếu

Cần `inputs/presentation/` chứa đúng PPTX v4 và DOCX script với các tên trong
[bảng chuyển đầu vào](../docs/input_handoff.md); giữ nguyên các bản gốc ở đây. Khi tiếp nhận:

1. Kiểm kê SHA-256, xác định bản v4 và script tương ứng. Chỉ sao chép bản được
   phép phân phối sang `presentation/`; kiểm tra riêng hình/bảng bên thứ ba,
   nếu quyền chưa rõ thì ghi nguồn/lệnh tải thay vì công bố tệp đó.
2. Gắn từng con số với đường dẫn kết quả/cấu hình trong repo hoặc trang/bảng
   bài báo; với số suy ra, ghi công thức và nguồn. Các số Beer–Rossmann/CFO
   phải chờ kiểm tra đợt tương ứng. Lưu bảng ánh xạ theo trang slide và mục script.
3. Đối chiếu nội dung slide với script, ghi rõ thuật toán thích nghi, chi phí
   học/sau học và giả định CFO. Tách kết quả đã chạy khỏi giả thuyết hướng D;
   giữ giới hạn của audit, không biến nhận định mã nguồn thành kết luận định lý.
4. Kiểm tra hiển thị toàn bộ slide v4 và dấu tiếng Việt; loại bản slide cũ
   trùng nếu có trong bản phân phối, giữ lịch sử Git và nguyên bản `inputs/`.
   Chỉ đánh dấu đợt 5 hoàn tất khi slide và script đều được kiểm tra.

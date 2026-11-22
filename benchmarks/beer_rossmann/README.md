# Đợt 3 — Benchmark Beer–Rossmann (chưa hoàn tất)

Snapshot nền: `c6ab1d8`. Trong phiên cloud ngày 2026-11-23, không tìm thấy
`inputs/beer_rossmann_archive/` dưới `/workspace`, thư mục repo hoặc các thư mục
chia sẻ. Vì vậy chưa đọc được mã/kết quả gốc của benchmark, chưa nhập mã SRDQN-A
hay Meta-HQL-P, chưa xác minh kết quả chính và chưa chạy lại 18 điều kiện.
Thư mục này hiện chỉ có hướng dẫn tiếp nhận; không có benchmark thay thế.

Chủ dự án đã xác nhận archive còn trên máy Windows, chưa tải lên cloud.
Tên ZIP và README nguồn đã được ghi trong [hướng dẫn chuyển đầu vào](../../docs/input_handoff.md).

## Phần đã có và cách kiểm tra từ clone sạch

Python **3.10+**; công cụ kiểm kê chỉ dùng thư viện chuẩn, không cần R hay pip:

```bash
git clone https://github.com/lequanghuyvnkor/gong-simchi_le_experiment.git
cd gong-simchi_le_experiment
python --version
python tools/inspect_inputs.py --help
python tools/inspect_inputs.py --inputs-dir /workspace/inputs --require benchmark
```

Thay `/workspace/inputs` bằng đường dẫn riêng thực tế. Mã thoát **2** là thiếu
đầu vào hoặc không đọc an toàn được, **0** chỉ có nghĩa kiểm kê thành công.
JSON in ra danh sách tệp, kích thước, SHA-256 và phiên bản Python/hệ điều hành.
Nó không chạy mã trong archive, không sửa đầu vào, không chứng nhận quyền phân
phối, không so checksum với bản gốc và không xác nhận tính đúng của benchmark.
Không coi việc thử nhánh thiếu đầu vào là đã chạy benchmark thành công.

Có thể giữ kiểm kê riêng bằng chuyển hướng ra tệp **ngoài `inputs/`**:

```bash
mkdir -p local_checks
python tools/inspect_inputs.py --inputs-dir /workspace/inputs --require benchmark > local_checks/inputs_inventory.json
```

`inputs/`, `external_data/`, `local_checks/` ở gốc repo được bỏ qua bởi Git.
Kiểm kê cũng cần được xem lại trước khi công bố vì tên tệp có thể là thông tin riêng.

## Đầu vào cần bổ sung

```text
/workspace/inputs/beer_rossmann_archive/
    README*                 # hướng dẫn xuất xứ, cách chạy
    <tệp checksum gốc>       # giữ tên thực tế của archive
    work/                   # mã nguồn và cấu hình đã chạy
    outputs/                # kết quả, manifest, phiên bản phần mềm
```

Đây là cấu trúc được yêu cầu cung cấp, chưa phải danh sách tệp đã quan sát.
Chưa biết tên tệp bên trong; không thể đưa lệnh nối dữ liệu hay nguồn tải Beer
chính xác trước khi đọc README và mã chuẩn bị dữ liệu. Gói bổ sung chính thức
là đầu vào riêng, tùy chọn ở `inputs/original_supplement/`; cách tải và checksum
đã lưu nằm trong [hướng dẫn audit](../../replication_audit/README.md).

## Điều kiện để đóng gói và hoàn tất

1. Đọc toàn bộ mã, cấu hình và kết quả liên quan trong archive trước khi chọn
   tệp. Lập bảng xuất xứ/quyền phân phối cho từng nguồn dữ liệu, mã và hình.
   Quyền chưa rõ: giữ ngoài Git, ghi URL tải, SHA-256, cấu trúc và lệnh nối dữ liệu.
2. Giữ mã chuẩn bị dữ liệu, thiết kế điều kiện, baseline, cấu hình và mã hai
   bộ học mà quyền phân phối cho phép. Ghi **SRDQN-A thích nghi** và
   **Meta-HQL-P thích nghi cho một điểm tồn kho/một sản phẩm**, kèm từng thay đổi
   so với tài liệu gốc. Không gọi đây là lần chạy nguyên gốc hai thuật toán.
3. Tách khảo sát ban đầu khỏi benchmark chính **18 điều kiện** (con số mục tiêu
   do chủ dự án cung cấp, chưa được xác minh từ archive). Ghi riêng ngân sách
   học, cấu hình, biến thể, phiên bản phần mềm, nguồn dữ liệu và checksum.
4. Giữ nguyên seed, điều kiện và thiết kế ghép cặp. Mô tả đơn vị ghép cặp,
   cách sinh đường cầu chung, số lần lặp độc lập, công thức CI và quy tắc gộp
   điều kiện theo đúng mã thực tế; không suy ra CI bằng cách coi các ngày là
   những lần lặp độc lập. Không thay CI gốc bằng một công thức tự chọn.
5. Báo cáo riêng chi phí trong lúc học và chi phí của chính sách đóng băng sau
   học; nêu dữ liệu train/validation/test và cách tránh dùng test để chọn tham số.
6. Ghi lệnh cài dependencies Python thực tế, lệnh nối dữ liệu, chạy và kiểm tra
   các bảng kết quả chính từ clone sạch. Đối chiếu hàng theo điều kiện/seed,
   số liệu tổng hợp và CI trước khi đánh dấu hoàn tất.

Hiện chưa có kết quả Beer–Rossmann nào được xác minh trong repo. Các kết quả
notebook năm thí nghiệm, alpha và replication audit có sẵn là các nhánh riêng;
không dùng chúng để lấp kết quả benchmark bị thiếu.

## Kiểm tra phần chuẩn bị

Ngày 2026-11-23: chạy trên clone sạch áp bản diff chuẩn bị, Python 3.12.14,
không cài thêm dependency. `--help` chạy được; fixture tạm kiểm tra SHA-256,
nguồn không đổi, nhóm bắt buộc bị thiếu, nhiều nhóm hợp lệ, từ chối symlink
ở gốc/bên trong, FIFO và đường dẫn gốc là tệp. Đường dẫn cloud còn thiếu trả
mã 2 như dự kiến. Đây chỉ là kiểm tra công cụ tiếp nhận; chưa kiểm tra pipeline,
kết quả hoặc CI benchmark. Python 3.10 chưa được chạy trực tiếp trong phiên này.
